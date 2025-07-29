from flask import Flask, request, jsonify
from binance_api import BinanceAPI
from position_manager import PositionManager
from config import Config
import threading
import time
import logging
import os

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
config = Config()

# TEST: Vérifier la configuration
logger.info(f"Configuration TESTNET: {config.TESTNET}")

try:
    binance = BinanceAPI(config.API_KEY, config.SECRET_KEY, testnet=config.TESTNET)
    logger.info(f"Binance API initialized successfully for {'TESTNET' if config.TESTNET else 'MAINNET'}")
    logger.info(f"Binance API URL: {binance.client.base_url}")
except Exception as e:
    logger.error(f"Failed to initialize BinanceAPI: {e}")
    raise e

# Initialisation du PositionManager
position_manager = PositionManager()
logger.info("PositionManager initialized")

# Démarrer les tâches périodiques
def start_periodic_tasks():
    def monitor_targets():
        while True:
            try:
                check_exit_conditions()
                monitor_pending_orders()
                position_manager.sync_with_exchange(binance)
            except Exception as e:
                logger.error(f"Periodic task error: {e}")
            time.sleep(60)
    
    thread = threading.Thread(target=monitor_targets, daemon=True)
    thread.start()
    logger.info("Periodic tasks started")

def check_exit_conditions():
    """Vérifier les conditions de sortie selon la stratégie TradingView"""
    for symbol in position_manager.get_symbols():
        try:
            positions = position_manager.get_positions(symbol)
            if not positions:
                continue
                
            current_price = binance.get_current_price(symbol)
            unrealized_profit = position_manager.get_unrealized_profit(symbol, current_price)
            avg_price = position_manager.calculate_avg_price(symbol)
            profit_target = avg_price * (1 + config.PROFIT_PERCENT / 100)
            
            logger.info(f"Exit check for {symbol}: "
                        f"Current: {current_price}, Target: {profit_target}, "
                        f"Unrealized P&L: {unrealized_profit}")
            
            # Condition exacte de TradingView
            if unrealized_profit > 0 and current_price >= profit_target:
                total_quantity = sum(p['quantity'] for p in positions)
                order = binance.place_market_order(
                    symbol=symbol,
                    side='SELL',
                    quantity=total_quantity
                )
                
                if order:
                    logger.info(f"Closed all positions for {symbol} at market price")
                    position_manager.remove_all_positions(symbol)
        except Exception as e:
            logger.error(f"Error in exit check for {symbol}: {e}")

def monitor_pending_orders():
    """Vérifier et mettre à jour les ordres en attente"""
    try:
        orders = position_manager.get_pending_orders()
        logger.info(f"Monitoring {len(orders)} pending orders")
        
        for order in orders:
            symbol = order['symbol']
            order_id = order['order_id']
            status = binance.get_order_status(symbol, order_id)
            logger.info(f"Order {order_id} status: {status}")
            
            if status == 'FILLED':
                position_manager.add_position(
                    symbol=symbol,
                    entry_price=order['price'],
                    quantity=order['quantity'],
                    order_id=order_id
                )
                position_manager.remove_pending_order(order_id)
            elif status in ['CANCELED', 'EXPIRED']:
                position_manager.remove_pending_order(order_id)
            elif status == 'NEW' and position_manager.is_order_old(order_id, minutes=5):
                binance.cancel_order(symbol, order_id)
                position_manager.remove_pending_order(order_id)
                
                # Recalculer le nouveau prix d'entrée
                last_entry = position_manager.get_last_entry_price(symbol) or binance.get_current_price(symbol)
                new_price = last_entry * (1 - config.BELOW_PERCENT / 100) * 0.998
                
                quantity = calculate_quantity(
                    price=new_price,
                    order_value=config.ORDER_VALUE,
                    min_movement=config.MIN_MOVEMENT,
                    decimals=config.ROUNDING
                )
                
                # Replacer l'ordre
                new_order = binance.place_limit_order(
                    symbol=symbol,
                    side='BUY',
                    quantity=quantity,
                    price=new_price
                )
                
                if new_order:
                    position_manager.add_pending_order(
                        symbol=symbol,
                        order_id=new_order['orderId'],
                        side='BUY',
                        price=new_price,
                        quantity=quantity
                    )
    except Exception as e:
        logger.error(f"Error in order monitoring: {e}")

def calculate_quantity(price, order_value, min_movement, decimals):
    """Calcule la quantité selon les règles de la stratégie"""
    try:
        raw_qty = order_value / price
        rounded = round(raw_qty, decimals)
        return rounded + min_movement if rounded >= raw_qty else rounded + (min_movement * 2)
    except Exception as e:
        logger.error(f"Quantity calculation error: {e}")
        return 0

def calculate_pir(symbol):
    """Calcul exact du PIR comme dans TradingView"""
    try:
        equity = binance.get_equity()
        net_profit = binance.get_net_profit()
        current_price = binance.get_current_price(symbol)
        min_qty = config.ORDER_VALUE / current_price
        pir = (equity + net_profit) / (min_qty * current_price)
        return pir
    except Exception as e:
        logger.error(f"Error in calculate_pir: {e}")
        return 0

def can_open_new_position(symbol):
    """Vérifie si on peut ouvrir une nouvelle position"""
    try:
        pir = calculate_pir(symbol)
        current_orders = len(position_manager.get_positions(symbol))
        max_orders = min(pir, config.MAX_ORDERS)
        
        logger.info(f"Can open new position for {symbol}: "
                   f"PIR: {pir}, Current orders: {current_orders}, "
                   f"Max allowed: {max_orders}")
        
        # Mode debug: désactiver la limite d'ordres
        if os.getenv('DISABLE_MAX_ORDERS_CHECK') == 'true':
            return True
            
        return current_orders < max_orders
    except Exception as e:
        logger.error(f"Error in can_open_new_position: {e}")
        return False

def is_in_trading_window():
    """Vérifie si on est dans la fenêtre temporelle"""
    try:
        if os.getenv('DISABLE_TIMEWINDOW') == 'true':
            return True
            
        now = time.time()
        start_time = config.get_start_timestamp()
        return now >= start_time
    except Exception as e:
        logger.error(f"Error in is_in_trading_window: {e}")
        return False

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        
        # Vérification de sécurité
        expected_token = os.getenv('WEBHOOK_TOKEN')
        if expected_token and data.get('token') != expected_token:
            logger.error("Invalid webhook token received")
            return jsonify({"status": "error", "message": "Invalid token"}), 401
        
        symbol = data.get('symbol', 'UNKNOWN').upper()
        action = data.get('action')
        logger.info(f"Received {action} signal for {symbol}: {data}")
        
        # Traitement des signaux d'achat
        if action == 'buy' and is_in_trading_window():
            signal_price = float(data['price'])
            last_entry = position_manager.get_last_entry_price(symbol)
            
            # Calcul du prochain prix d'entrée
            next_price = last_entry * (1 - config.BELOW_PERCENT / 100) if last_entry else signal_price
            
            logger.info(f"Buy signal conditions: "
                       f"Signal price: {signal_price}, "
                       f"Next entry: {next_price}, "
                       f"Can open: {can_open_new_position(symbol)}")
            
            # Condition exacte de TradingView
            if signal_price <= next_price and can_open_new_position(symbol):
                quantity = calculate_quantity(
                    price=next_price,
                    order_value=config.ORDER_VALUE,
                    min_movement=config.MIN_MOVEMENT,
                    decimals=config.ROUNDING
                )
                
                # Valider et placer l'ordre
                order = binance.place_limit_order(
                    symbol=symbol,
                    side='BUY',
                    quantity=quantity,
                    price=next_price
                )
                
                if order:
                    logger.info(f"Buy order placed: {order}")
                    position_manager.add_pending_order(
                        symbol=symbol,
                        order_id=order['orderId'],
                        side='BUY',
                        price=next_price,
                        quantity=quantity
                    )
                    return jsonify({"status": "success", "order_id": order['orderId']})
        
        # Traitement des signaux de vente
        elif action == 'sell':
            positions = position_manager.get_positions(symbol)
            if positions:
                current_price = binance.get_current_price(symbol)
                unrealized_profit = position_manager.get_unrealized_profit(symbol, current_price)
                
                # Condition exacte de TradingView
                if unrealized_profit > 0:
                    total_quantity = sum(p['quantity'] for p in positions)
                    order = binance.place_market_order(
                        symbol=symbol,
                        side='SELL',
                        quantity=total_quantity
                    )
                    
                    if order:
                        logger.info(f"Sold all positions via webhook: {order}")
                        position_manager.remove_all_positions(symbol)
                        return jsonify({"status": "sold", "quantity": total_quantity})
            else:
                logger.info(f"No positions to sell for {symbol}")
        
        return jsonify({"status": "ignored"})
    
    except Exception as e:
        logger.exception("Webhook processing failed")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    try:
        price = binance.get_current_price('BTCUSDT')
        positions = position_manager.get_positions('BTCUSDT')
        return jsonify({
            "status": "ok",
            "testnet": config.TESTNET,
            "btc_price": price,
            "open_positions": len(positions),
            "pending_orders": len(position_manager.get_pending_orders())
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    logger.info(f"Starting bot in {'TESTNET' if config.TESTNET else 'LIVE'} mode")
    
    # Synchronisation initiale
    position_manager.sync_with_exchange(binance)
    
    # Démarrer les tâches périodiques
    start_periodic_tasks()
    
    # Démarrer le serveur Flask
    app.run(host='0.0.0.0', port=5000, use_reloader=False)
