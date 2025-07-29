from binance.client import Client
import logging

class BinanceAPI:
    def __init__(self, api_key, api_secret, testnet=True):
        self.testnet = testnet
        self.client = Client(
            api_key=api_key,
            api_secret=api_secret,
            testnet=self.testnet
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Binance API initialized for {'TESTNET' if testnet else 'MAINNET'}")

    def place_limit_order(self, symbol, side, quantity, price):
        try:
            order = self.client.create_order(
                symbol=symbol,
                side=side.upper(),
                type=Client.ORDER_TYPE_LIMIT,
                timeInForce=Client.TIME_IN_FORCE_GTC,
                quantity=quantity,
                price=price
            )
            self.logger.info(f"Limit order placed: {symbol} {side} {quantity} @ {price}")
            return order
        except Exception as e:
            self.logger.error(f"Limit order failed: {e}")
            return None

    def place_market_order(self, symbol, side, quantity):
        try:
            order = self.client.create_order(
                symbol=symbol,
                side=side.upper(),
                type=Client.ORDER_TYPE_MARKET,
                quantity=quantity
            )
            self.logger.info(f"Market order placed: {symbol} {side} {quantity}")
            return order
        except Exception as e:
            self.logger.error(f"Market order failed: {e}")
            return None

    def get_order_status(self, symbol, order_id):
        try:
            order = self.client.get_order(symbol=symbol, orderId=order_id)
            return order['status']
        except Exception as e:
            self.logger.error(f"Order status check failed: {e}")
            return 'UNKNOWN'

    def cancel_order(self, symbol, order_id):
        try:
            result = self.client.cancel_order(symbol=symbol, orderId=order_id)
            self.logger.info(f"Order canceled: {order_id}")
            return True
        except Exception as e:
            self.logger.error(f"Order cancel failed: {e}")
            return False

    def get_current_price(self, symbol):
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            self.logger.error(f"Price check failed: {e}")
            return 0.0

    def get_equity(self):
        # Implémentation simplifiée pour l'exemple
        return 10000.0

    def get_net_profit(self):
        # Implémentation simplifiée pour l'exemple
        return 500.0

    def get_positions(self):
        # Implémentation simplifiée pour l'exemple
        return {}

    def get_open_orders(self):
        # Implémentation simplifiée pour l'exemple
        return []
