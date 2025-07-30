import os
import time

class Config:
    def __init__(self):
        self.TESTNET = os.getenv('TESTNET', 'True') == 'True'
        self.API_KEY = os.getenv('BINANCE_API_KEY', '')
        self.SECRET_KEY = os.getenv('BINANCE_API_SECRET', '')
        self.PROFIT_PERCENT = float(os.getenv('PROFIT_PERCENT', '1.5'))
        self.BELOW_PERCENT = float(os.getenv('BELOW_PERCENT', '0.5'))
        self.ORDER_VALUE = float(os.getenv('ORDER_VALUE', '100'))
        self.MIN_MOVEMENT = float(os.getenv('MIN_MOVEMENT', '0.0001'))
        self.ROUNDING = int(os.getenv('ROUNDING', '4'))
        self.MAX_ORDERS = int(os.getenv('MAX_ORDERS', '5'))
        
    def get_start_timestamp(self):
        # Implémentation simplifiée
        return time.time() - 3600  # 1 heure dans le passé
