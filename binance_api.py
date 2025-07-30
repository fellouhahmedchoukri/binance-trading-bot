from binance.client import Client
import logging

class BinanceAPI:
    def __init__(self, api_key, api_secret, testnet=True):
        self.testnet = testnet
        self.api_url = "https://testnet.binance.vision" if testnet else "https://api.binance.com"
        
        self.client = Client(
            api_key=api_key,
            api_secret=api_secret,
            testnet=self.testnet
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Binance API initialized for {'TESTNET' if testnet else 'MAINNET'}")
        self.logger.info(f"Using API URL: {self.api_url}")

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
        try:
            account = self.client.get_account()
            return float(account['totalWalletBalance'])
        except Exception as e:
            self.logger.error(f"Error getting equity: {e}")
            return 0.0

    def get_net_profit(self):
        try:
            account = self.client.get_account()
            return float(account['totalUnrealizedProfit'])
        except Exception as e:
            self.logger.error(f"Error getting net profit: {e}")
            return 0.0

    def get_positions(self):
        try:
            positions = {}
            account = self.client.get_account()
            for balance in account['balances']:
                if float(balance['free']) > 0 or float(balance['locked']) > 0:
                    positions[balance['asset']] = {
                        'free': float(balance['free']),
                        'locked': float(balance['locked'])
                    }
            return positions
        except Exception as e:
            self.logger.error(f"Error getting positions: {e}")
            return {}

    def get_open_orders(self, symbol=None):
        try:
            if symbol:
                return self.client.get_open_orders(symbol=symbol)
            else:
                return self.client.get_open_orders()
        except Exception as e:
            self.logger.error(f"Error getting open orders: {e}")
            return []
