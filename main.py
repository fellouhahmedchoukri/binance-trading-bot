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
except Exception as e:
    logger.error(f"Failed to initialize BinanceAPI: {e}")
    raise e

# Initialisation du PositionManager dans le thread principal
position_manager = PositionManager()
logger.info("PositionManager initialized")

# Démarrer les tâches périodiques
def start_periodic_tasks():
    def monitor_targets():
        while True:
            try:
                check_profit_targets()
                monitor_pending_orders()
            except Exception as e:
                logger.error(f"Periodic task error: {e}")
            time.sleep(60)  # Vérifier toutes les minutes
    
    thread = threading.Thread(target=monitor_targets, daemon=True)
    thread.start()
    logger.info("Periodic tasks started")

def check_profit_targets():
    """Vérifie si les positions atteignent le profit target"""
    for symbol in position_manager.get_symbols():
        try:
            current_price = binance.get_current_price(symbol)
            positions = position_manager.get_positions(symbol)
            
            if not positions:
                continue
                
            avg_price = position_manager.calculate_avg_price(symbol)
            profit_target = avg_price * (1 + config.PROFIT_PERCENT / 100)
            
            logger.info(f"Checking profit for {symbol}: "
                        f"Current: {current_price}, Target: {profit_target}")
            
            if current_price >= profit_target:
                total_quantity = sum(p['quantity'] for p in positions)
                
                # Fermer toute la position
                order = binance.place_limit_order(
                    symbol=symbol,
                    side='SELL',
                    quantity=total_quantity,
                    price=profit_target
                )
                
                if order:
                    logger.info(f"Closed all positions for {symbol} at {profit_target}")
                    position_manager.remove_all_positions(symbol)
        except Exception as e:
            logger.error(f"Error in profit check for {symbol}: {e}")

def monitor_pending_orders():
    """Vérifie et met à jour les ordres en attente"""
    try:
        orders = position_manager.get_pending_orders()
        logger.info(f"Monitoring {len(orders)} pending orders")
        
        for order in orders:
            symbol = order['symbol']
            order_id = order['order_id']
            
            # Vérifier l'état de l'ordre
            status = binance.get_order_status(symbol, order_id)
            logger.info(f"Order {order_id} status: {status}")
            
            if status == 'FILLED':
                # Ajouter à la position
                position_manager.add_position(
                    symbol=symbol,
                    entry_price=order['price'],
                    quantity=order['quantity'],
                    order_id=order_id
                )
                position_manager.remove_pending_order(order_id)
            elif status in ['CANCELED', 'EXPIRED']:
                position_manager.remove_pending_order(order_id)
            elif status == 'NEW':
                # Vérifier si l'ordre est trop ancien (>5min)
                if position_manager.is_order_old(order_id, minutes=5):
                    binance.cancel_order(symbol, order_id)
                    position_manager.remove_pending_order(order_id)
                    
                    # Recalculer nouveau prix d'entrée
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
    raw_qty = order_value / price
    rounded = round(raw_qty, decimals)
    return rounded + min_movement if rounded >= raw_qty else rounded + (min_movement * 2)

def can_open_new_position(symbol):
    """Vérifie si on peut ouvrir une nouvelle position"""
    try:
        equity = binance.get_equity()
        current_price = binance.get_current_price(symbol)
        min_qty = config.ORDER_VALUE / current_price
        pir = equity / (min_qty * current_price)
        current_orders = len(position_manager.get_positions(symbol))
        
        logger.info(f"Can open new position for {symbol}: "
                   f"Equity: {equity}, PIR: {pir}, "
                   f"Current orders: {current_orders}, Max orders: {config.MAX_ORDERS}")
        
        # Mode debug: désactiver la limite d'ordres
        if os.getenv('DISABLE_MAX_ORDERS_CHECK') == 'true':
            return True
            
        return current_orders < min(pir, config.MAX_ORDERS)
    except Exception as e:
        logger.error(f"Error in can_open_new_position: {e}")
        return False

def is_in_trading_window():
    """Vérifie si on est dans la fenêtre temporelle"""
    try:
        # Mode debug: désactiver la fenêtre temporelle
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
        data = request.jsonwebhook_token = os.getenv('WEBHOOK_TOKEN')
        if webhook_token:  # Seulement si le token est configuré
            if data.get('token') != webhook_token:
                logger.error("Invalid webhook token received")
                return jsonify({"status": "error", "message": "Invalid token"}), 401
        
        
        symbol = data.get('symbol', 'UNKNOWN')
        logger.info(f"Received signal: {data}")
        
        # Debug: log de la configuration
        logger.info(f"Config: ORDER_VALUE={config.ORDER_VALUE}, "
                   f"BELOW_PERCENT={config.BELOW_PERCENT}%, "
                   f"PROFIT_PERCENT={config.PROFIT_PERCENT}%")
        
        if data['action'] == 'buy' and is_in_trading_window():
            symbol = data['symbol']
            signal_price = float(data['price'])
            
            last_entry = position_manager.get_last_entry_price(symbol)
            
            # Debug: log des informations critiques
            logger.info(f"Strategy check for {symbol}:")
            logger.info(f"- Trading window active: {is_in_trading_window()}")
            logger.info(f"- Last entry price: {last_entry}")
            logger.info(f"- Can open new position: {can_open_new_position(symbol)}")
            
            if last_entry is None:
                next_price = signal_price
                logger.info(f"- First position, using signal price: {next_price}")
            else:
                next_price = last_entry * (1 - config.BELOW_PERCENT / 100)
                logger.info(f"- Existing position, next entry price: {next_price}")
            
            logger.info(f"- Signal price: {signal_price} vs Next entry price: {next_price}")
            
            if signal_price <= next_price and can_open_new_position(symbol):
                quantity = calculate_quantity(
                    price=next_price,
                    order_value=config.ORDER_VALUE,
                    min_movement=config.MIN_MOVEMENT,
                    decimals=config.ROUNDING
                )
                
                # Valider l'ordre
                quantity, price = binance.validate_order(symbol, quantity, next_price)
                
                # Placer l'ordre limite
                order = binance.place_limit_order(
                    symbol=symbol,
                    side='BUY',
                    quantity=quantity,
                    price=price
                )
                
                if order:
                    logger.info(f"Order placed successfully: {order}")
                    position_manager.add_pending_order(
                        symbol=symbol,
                        order_id=order['orderId'],
                        side='BUY',
                        price=price,
                        quantity=quantity
                    )
                    
                    # TEST: Vérifier l'ordre sur Binance
                    if config.TESTNET:
                        try:
                            order_status = binance.client.get_order(
                                symbol=symbol,
                                orderId=order['orderId']
                            )
                            logger.info(f"Testnet order status: {order_status}")
                        except Exception as e:
                            logger.error(f"Failed to get order status: {e}")
                    
                    return jsonify({"status": "success", "order_id": order['orderId']})
        
        return jsonify({"status": "ignored"})
    
    except Exception as e:
        logger.exception("Webhook processing failed")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    # Vérifier la connexion à Binance
    try:
        price = binance.get_current_price('BTCUSDT')
        return jsonify({
            "status": "ok",
            "message": "Bot is running",
            "testnet_mode": config.TESTNET,
            "btc_price": price
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    # Test initial
    logger.info(f"Starting application in {'TESTNET' if config.TESTNET else 'MAINNET'} mode")
    logger.info(f"Binance API URL: {binance.client.API_URL}")
    
    # Vérifier la connexion
    try:
        btc_price = binance.get_current_price('BTCUSDT')
        logger.info(f"BTC/USDT price: {btc_price}")
        
        # Vérifier le solde USDT
        balance = binance.client.get_asset_balance(asset='USDT')
        logger.info(f"USDT Balance: {balance}")
    except Exception as e:
        logger.error(f"Initial connection failed: {e}")
    
    start_periodic_tasks()
    app.run(host='0.0.0.0', port=5000)
