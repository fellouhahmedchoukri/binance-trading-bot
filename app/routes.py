from flask import render_template, jsonify
from app import app
from app.models import TradingSnapshot, TradeHistory
from datetime import datetime, timedelta

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/dashboard/data')
def dashboard_data():
    # Dernier snapshot
    snapshot = TradingSnapshot.query.order_by(TradingSnapshot.timestamp.desc()).first()
    
    # Positions ouvertes (exemple)
    positions = [
        {'symbol': 'BTCUSDT', 'quantity': 0.05, 'entry_price': 51000, 'current_price': 51200},
        {'symbol': 'ETHUSDT', 'quantity': 0.8, 'entry_price': 3200, 'current_price': 3250}
    ]
    
    # Ordres en attente
    orders = [
        {'symbol': 'BTCUSDT', 'side': 'BUY', 'quantity': 0.02, 'price': 50500},
        {'symbol': 'ETHUSDT', 'side': 'SELL', 'quantity': 0.5, 'price': 3300}
    ]
    
    # Historique des transactions (7 derniers jours)
    trades = TradeHistory.query.filter(
        TradeHistory.timestamp > datetime.utcnow() - timedelta(days=7)
    ).order_by(TradeHistory.timestamp.desc()).limit(50).all()
    
    # Historique des performances (7 derniers jours)
    history = TradingSnapshot.query.filter(
        TradingSnapshot.timestamp > datetime.utcnow() - timedelta(days=7)
    ).order_by(TradingSnapshot.timestamp.asc()).all()
    
    return jsonify({
        'snapshot': {
            'equity': snapshot.equity if snapshot else 0,
            'net_profit': snapshot.net_profit if snapshot else 0,
            'open_positions': snapshot.open_positions if snapshot else 0,
            'pending_orders': snapshot.pending_orders if snapshot else 0,
            'btc_price': snapshot.btc_price if snapshot else 0,
            'timestamp': snapshot.timestamp.isoformat() if snapshot else ''
        },
        'positions': positions,
        'orders': orders,
        'trades': [{
            'id': t.id,
            'timestamp': t.timestamp.isoformat(),
            'symbol': t.symbol,
            'side': t.side,
            'quantity': t.quantity,
            'price': t.price,
            'status': t.status
        } for t in trades],
        'history': [{
            'timestamp': h.timestamp.isoformat(),
            'equity': h.equity,
            'net_profit': h.net_profit
        } for h in history]
    })
