import os
import time
from datetime import datetime

class Config:
    def __init__(self):
        self.API_KEY = os.getenv('BINANCE_API_KEY', '')
        self.SECRET_KEY = os.getenv('BINANCE_SECRET_KEY', '')
        self.TESTNET = os.getenv('TESTNET', 'true').lower() == 'true'
        self.ORDER_VALUE = float(os.getenv('ORDER_VALUE', 10.0))
        self.BELOW_PERCENT = float(os.getenv('BELOW_PERCENT', 0.5))
        self.PROFIT_PERCENT = float(os.getenv('PROFIT_PERCENT', 2.0))
        self.MAX_ORDERS = int(os.getenv('MAX_ORDERS', 10))
        self.MIN_MOVEMENT = float(os.getenv('MIN_MOVEMENT', 0.00001))
        self.ROUNDING = int(os.getenv('ROUNDING', 5))
        
        # Configuration de la fenêtre temporelle
        self.START_HOUR = int(os.getenv('START_HOUR', 0))
        self.START_MINUTE = int(os.getenv('START_MINUTE', 0))

    def get_start_timestamp(self):
        """Obtenir le timestamp de début pour aujourd'hui"""
        now = datetime.now()
        start_time = datetime(now.year, now.month, now.day, self.START_HOUR, self.START_MINUTE)
        return time.mktime(start_time.timetuple())
