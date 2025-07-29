from binance.client import Client
from binance.exceptions import BinanceAPIException
import logging
import math

class BinanceAPI:
    def __init__(self, api_key, api_secret, testnet=True):
        """Initialise la connexion à l'API Binance.
        
        Args:
            api_key (str): Clé API Binance
            api_secret (str): Clé secrète Binance
            testnet (bool): Utiliser le testnet (True par défaut)
        """
        self.testnet = testnet
        self.logger = logging.getLogger(__name__)
        
        if testnet:
            self.logger.info("Initializing Binance TESTNET API")
            self.client = Client(api_key, api_secret, testnet=True)
        else:
            self.logger.info("Initializing Binance MAINNET API")
            self.client = Client(api_key, api_secret)
    
    def place_limit_order(self, symbol, side, quantity, price):
        try:
            order = self.client.create_order(
                symbol=symbol,
                side=side,
                type=Client.ORDER_TYPE_LIMIT,
                timeInForce=Client.TIME_IN_FORCE_GTC,
                quantity=self.format_quantity(symbol, quantity),
                price=self.format_price(symbol, price)
            )
            self.logger.info(f"Order placed: {order}")
            return order
        except BinanceAPIException as e:
            self.logger.error(f"Order failed: {e}")
            return None
    
    def cancel_order(self, symbol, order_id):
        try:
            result = self.client.cancel_order(symbol=symbol, orderId=order_id)
            self.logger.info(f"Order canceled: {result}")
            return result
        except BinanceAPIException as e:
            self.logger.error(f"Cancel failed: {e}")
            return None
    
    def get_order_status(self, symbol, order_id):
        try:
            order = self.client.get_order(symbol=symbol, orderId=order_id)
            return order['status']
        except BinanceAPIException as e:
            self.logger.error(f"Order status check failed: {e}")
            return 'UNKNOWN'
    
    def get_current_price(self, symbol):
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except BinanceAPIException as e:
            self.logger.error(f"Price check failed: {e}")
            return None
    
    def get_symbol_info(self, symbol):
        try:
            info = self.client.get_symbol_info(symbol)
            return info
        except BinanceAPIException as e:
            self.logger.error(f"Symbol info failed: {e}")
            return None
    
    def get_equity(self):
        try:
            balance = self.client.get_asset_balance(asset='USDT')
            return float(balance['free'])
        except BinanceAPIException as e:
            self.logger.error(f"Balance check failed: {e}")
            return 0.0
    
    def validate_order(self, symbol, quantity, price):
        """Valide les paramètres avec les règles Binance"""
        info = self.get_symbol_info(symbol)
        if not info:
            return quantity, price
        
        # Filtre de quantité
        lot_size = next(f for f in info['filters'] if f['filterType'] == 'LOT_SIZE')
        min_qty = float(lot_size['minQty'])
        max_qty = float(lot_size['maxQty'])
        step_size = float(lot_size['stepSize'])
        
        quantity = max(min_qty, min(quantity, max_qty))
        quantity = math.floor(quantity / step_size) * step_size
        quantity = round(quantity, 8)
        
        # Filtre de prix
        price_filter = next(f for f in info['filters'] if f['filterType'] == 'PRICE_FILTER')
        min_price = float(price_filter['minPrice'])
        max_price = float(price_filter['maxPrice'])
        tick_size = float(price_filter['tickSize'])
        
        price = max(min_price, min(price, max_price))
        price = math.floor(price / tick_size) * tick_size
        price = round(price, 8)
        
        return quantity, price
    
    def format_quantity(self, symbol, quantity):
        """Formate la quantité selon les règles du symbol"""
        info = self.get_symbol_info(symbol)
        if not info:
            return quantity
        
        lot_size = next(f for f in info['filters'] if f['filterType'] == 'LOT_SIZE')
        step_size = float(lot_size['stepSize'])
        precision = int(round(-math.log(step_size, 10), 0)
        return round(quantity, precision)
    
    def format_price(self, symbol, price):
        """Formate le prix selon les règles du symbol"""
        info = self.get_symbol_info(symbol)
        if not info:
            return price
        
        price_filter = next(f for f in info['filters'] if f['filterType'] == 'PRICE_FILTER')
        tick_size = float(price_filter['tickSize'])
        precision = int(round(-math.log(tick_size, 10), 0)
        return round(price, precision)
