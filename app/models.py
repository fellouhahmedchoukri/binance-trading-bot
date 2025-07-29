from app import db
from datetime import datetime

class TradingSnapshot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    equity = db.Column(db.Float)
    net_profit = db.Column(db.Float)
    open_positions = db.Column(db.Integer)
    pending_orders = db.Column(db.Integer)
    btc_price = db.Column(db.Float)
    
    def __repr__(self):
        return f'<Snapshot {self.timestamp}>'

class TradeHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    symbol = db.Column(db.String(10))
    side = db.Column(db.String(10))
    quantity = db.Column(db.Float)
    price = db.Column(db.Float)
    status = db.Column(db.String(20))
    
    def __repr__(self):
        return f'<Trade {self.symbol} {self.side} {self.quantity}>'
