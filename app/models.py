from datetime import datetime
from main import db

class Snapshot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    total_balance = db.Column(db.Float)
    available_balance = db.Column(db.Float)
    positions_count = db.Column(db.Integer)

class Trade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    symbol = db.Column(db.String(20))
    side = db.Column(db.String(10))
    quantity = db.Column(db.Float)
    price = db.Column(db.Float)
    status = db.Column(db.String(20))

class Position(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20))
    entry_price = db.Column(db.Float)
    quantity = db.Column(db.Float)
    side = db.Column(db.String(10))
    status = db.Column(db.String(20), default='OPEN')
