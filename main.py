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

# ... [début du fichier] ...
app = Flask(__name__)
config = Config()

# TEST: Vérifier la configuration
print(f"Configuration TESTNET: {config.TESTNET}")

binance = BinanceAPI(config.API_KEY, config.SECRET_KEY, testnet=config.TESTNET)
# ... [suite du fichier] ...

# Initialisation du PositionManager dans le thread principal
position_manager = PositionManager()

# Démarrer les tâches périodiques
def start_periodic_tasks():
    def monitor_targets():
        while True:
            try:
                check_profit_targets()
                monitor_pending_orders()
            except Exception as e:
                logger.error(f"Periodic task error: {e}")
            time.sleep(60)
    
    thread = threading.Thread(target=monitor_targets, daemon=True)
    thread.start()

# ... [les autres fonctions restent inchangées] ...

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
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
                        order_status = binance.client.get_order(
                            symbol=symbol,
                            orderId=order['orderId']
                        )
                        logger.info(f"Testnet order status: {order_status}")
                    
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
