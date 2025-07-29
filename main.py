from flask import Flask, request, jsonify
from binance_api import BinanceAPI
from position_manager import PositionManager
from config import Config
import threading
import time
import logging

app = Flask(__name__)
config = Config()
binance = BinanceAPI(config.API_KEY, config.SECRET_KEY)
position_manager = PositionManager()
logger = logging.getLogger(__name__)

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

def check_profit_targets():
    """Vérifie si les positions atteignent le profit target"""
    for symbol in position_manager.get_symbols():
        current_price = binance.get_current_price(symbol)
        positions = position_manager.get_positions(symbol)
        
        if not positions:
            continue
            
        avg_price = position_manager.calculate_avg_price(symbol)
        profit_target = avg_price * (1 + config.PROFIT_PERCENT / 100)
        
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

def monitor_pending_orders():
    """Vérifie et met à jour les ordres en attente"""
    for order in position_manager.get_pending_orders():
        symbol = order['symbol']
        order_id = order['order_id']
        
        # Vérifier l'état de l'ordre
        status = binance.get_order_status(symbol, order_id)
        
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

def calculate_quantity(price, order_value, min_movement, decimals):
    """Calcule la quantité selon les règles de la stratégie"""
    raw_qty = order_value / price
    rounded = round(raw_qty, decimals)
    return rounded + min_movement if rounded >= raw_qty else rounded + (min_movement * 2)

def can_open_new_position(symbol):
    """Vérifie si on peut ouvrir une nouvelle position"""
    equity = binance.get_equity()
    current_price = binance.get_current_price(symbol)
    min_qty = config.ORDER_VALUE / current_price
    pir = equity / (min_qty * current_price)
    current_orders = len(position_manager.get_positions(symbol))
    return current_orders < min(pir, config.MAX_ORDERS)

def is_in_trading_window():
    """Vérifie si on est dans la fenêtre temporelle"""
    now = time.time()
    start_time = config.get_start_timestamp()
    return now >= start_time

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        logger.info(f"Received signal: {data}")
        
        if data['action'] == 'buy' and is_in_trading_window():
            symbol = data['symbol']
            signal_price = float(data['price'])
            
            last_entry = position_manager.get_last_entry_price(symbol)
            if last_entry is None:
                # Première position
                next_price = signal_price
            else:
                # Calculer le prochain prix d'entrée
                next_price = last_entry * (1 - config.BELOW_PERCENT / 100)
            
            if signal_price <= next_price and can_open_new_position(symbol):
                quantity = calculate_quantity(
                    price=next_price,
                    order_value=config.ORDER_VALUE,
                    min_movement=config.MIN_MOVEMENT,
                    decimals=config.ROUNDING
                )
                
                # Valider l'ordre avec Binance
                quantity, price = binance.validate_order(symbol, quantity, next_price)
                
                # Placer l'ordre limite
                order = binance.place_limit_order(
                    symbol=symbol,
                    side='BUY',
                    quantity=quantity,
                    price=price
                )
                
                if order:
                    position_manager.add_pending_order(
                        symbol=symbol,
                        order_id=order['orderId'],
                        side='BUY',
                        price=price,
                        quantity=quantity
                    )
                    return jsonify({"status": "success", "order_id": order['orderId']})
        
        return jsonify({"status": "ignored"})
    
    except Exception as e:
        logger.exception("Webhook processing failed")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    start_periodic_tasks()
    app.run(host='0.0.0.0', port=5000)
