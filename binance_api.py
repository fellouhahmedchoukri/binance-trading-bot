from binance.spot import Spot
from binance.error import ClientError
import time

class BinanceAPI:
    def __init__(self, api_key, secret_key, testnet=False):
        self.testnet = testnet
        base_url = "https://testnet.binance.vision" if testnet else "https://api.binance.com"
        self.client = Spot(api_key=api_key, api_secret=secret_key, base_url=base_url)
        self.exchange_info = {}
        self.last_sync = 0
        self.refresh_exchange_info()

    def refresh_exchange_info(self):
        """Actualiser les informations d'échange toutes les 10 minutes"""
        if time.time() - self.last_sync > 600:
            self.exchange_info = self.client.exchange_info()
            self.last_sync = time.time()

    def get_symbol_info(self, symbol):
        """Obtenir les règles spécifiques au symbole"""
        self.refresh_exchange_info()
        for s in self.exchange_info['symbols']:
            if s['symbol'] == symbol:
                return s
        return None

    def get_current_price(self, symbol):
        """Prix actuel du marché"""
        ticker = self.client.ticker_price(symbol)
        return float(ticker['price'])

    def get_equity(self):
        """Solde total du compte en USDT"""
        balances = self.client.account()['balances']
        # CORRECTION: Parenthèse manquante ajoutée ici
        usdt_balance = next(
            (float(b['free']) + float(b['locked']) for b in balances if b['asset'] == 'USDT'
        ), 0.0)
        return usdt_balance

    def get_net_profit(self):
        """Profit net total (implémentation simplifiée)"""
        trades = self.client.my_trades(symbol='BTCUSDT', limit=1000)
        total_profit = 0.0
        for trade in trades:
            if 'realizedPnl' in trade:
                total_profit += float(trade['realizedPnl'])
        return total_profit

    def get_open_positions(self, symbol):
        """Positions ouvertes réelles depuis Binance"""
        positions = []
        orders = self.client.get_orders(symbol=symbol, limit=100)
        
        for order in orders:
            if order['status'] == 'FILLED' and order['side'] == 'BUY':
                positions.append({
                    'symbol': symbol,
                    'entry_price': float(order['price']),
                    'quantity': float(order['executedQty']),
                    'order_id': order['orderId']
                })
        return positions

    def place_limit_order(self, symbol, side, quantity, price):
        """Passer un ordre limite avec validation des règles"""
        symbol_info = self.get_symbol_info(symbol)
        if not symbol_info:
            return None

        # Validation du prix
        price_filter = next(f for f in symbol_info['filters'] if f['filterType'] == 'PRICE_FILTER')
        tick_size = float(price_filter['tickSize'])
        price = round(price / tick_size) * tick_size

        # Validation de la quantité
        lot_size = next(f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE')
        min_qty = float(lot_size['minQty'])
        step_size = float(lot_size['stepSize'])
        quantity = max(min_qty, quantity)
        quantity = round(quantity / step_size) * step_size

        try:
            order = self.client.new_order(
                symbol=symbol,
                side=side,
                type='LIMIT',
                timeInForce='GTC',
                quantity=quantity,
                price=price
            )
            return order
        except ClientError as e:
            print(f"Order placement failed: {e.error_message}")
            return None

    def place_market_order(self, symbol, side, quantity):
        """Passer un ordre au marché"""
        symbol_info = self.get_symbol_info(symbol)
        if not symbol_info:
            return None

        # Validation de la quantité
        lot_size = next(f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE')
        min_qty = float(lot_size['minQty'])
        step_size = float(lot_size['stepSize'])
        quantity = max(min_qty, quantity)
        quantity = round(quantity / step_size) * step_size

        try:
            order = self.client.new_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=quantity
            )
            return order
        except ClientError as e:
            print(f"Market order failed: {e.error_message}")
            return None

    def get_order_status(self, symbol, order_id):
        """Statut d'un ordre spécifique"""
        try:
            order = self.client.get_order(symbol=symbol, orderId=order_id)
            return order['status']
        except ClientError:
            return 'UNKNOWN'

    def cancel_order(self, symbol, order_id):
        """Annuler un ordre"""
        try:
            self.client.cancel_order(symbol=symbol, orderId=order_id)
            return True
        except ClientError:
            return False

    def close_all_positions(self, symbol):
        """Fermer toutes les positions pour un symbole"""
        positions = self.get_open_positions(symbol)
        if not positions:
            return False
            
        total_quantity = sum(p['quantity'] for p in positions)
        return self.place_market_order(symbol, 'SELL', total_quantity)
