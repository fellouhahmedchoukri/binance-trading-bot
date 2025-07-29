import os
from datetime import datetime

class Config:
    def __init__(self):
        # Binance API
        self.API_KEY = os.getenv('BINANCE_API_KEY', 'your_api_key')
        self.SECRET_KEY = os.getenv('BINANCE_SECRET_KEY', 'your_secret_key')
        
        # Strategy parameters (éditables)
        self.ORDER_VALUE = float(os.getenv('ORDER_VALUE', 10.0))  # en USDT
        self.MIN_MOVEMENT = float(os.getenv('MIN_MOVEMENT', 0.00001))
        self.ROUNDING = int(os.getenv('ROUNDING', 5))
        self.BELOW_PERCENT = float(os.getenv('BELOW_PERCENT', 0.5))
        self.PROFIT_PERCENT = float(os.getenv('PROFIT_PERCENT', 2.0))
        self.MAX_ORDERS = int(os.getenv('MAX_ORDERS', 10))
        self.INITIAL_CAPITAL = float(os.getenv('INITIAL_CAPITAL', 500.0))
        self.COMMISSION = float(os.getenv('COMMISSION', 0.1))  # en %
        
        # Time parameters
        self.FROM_MIN = int(os.getenv('FROM_MIN', 0))
        self.FROM_HOUR = int(os.getenv('FROM_HOUR', 0))
        self.FROM_DAY = int(os.getenv('FROM_DAY', 1))
        self.FROM_MONTH = int(os.getenv('FROM_MONTH', 1))
        self.FROM_YEAR = int(os.getenv('FROM_YEAR', 2000))
    
    def get_start_timestamp(self):
        return datetime(
            year=self.FROM_YEAR,
            month=self.FROM_MONTH,
            day=self.FROM_DAY,
            hour=self.FROM_HOUR,
            minute=self.FROM_MIN
        ).timestamp()
