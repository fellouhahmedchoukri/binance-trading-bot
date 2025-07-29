from app import db
from app.models import TradingSnapshot, TradeHistory
from datetime import datetime, timedelta

def save_snapshot(binance, position_manager):
    """Enregistre un instantané du portefeuille"""
    try:
        equity = binance.get_equity()
        net_profit = binance.get_net_profit()
        btc_price = binance.get_current_price('BTCUSDT')
        
        snapshot = TradingSnapshot(
            equity=equity,
            net_profit=net_profit,
            open_positions=len(position_manager.get_positions('BTCUSDT')),
            pending_orders=len(position_manager.get_pending_orders()),
            btc_price=btc_price
        )
        
        db.session.add(snapshot)
        db.session.commit()
        
        # Nettoyer les anciens snapshots (garder 7 jours)
        week_ago = datetime.utcnow() - timedelta(days=7)
        TradingSnapshot.query.filter(TradingSnapshot.timestamp < week_ago).delete()
        db.session.commit()
        
        return True
    except Exception as e:
        print(f"Error saving snapshot: {e}")
        return False

def log_trade(symbol, side, quantity, price, status):
    """Enregistre une transaction dans l'historique"""
    try:
        trade = TradeHistory(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            status=status
        )
        db.session.add(trade)
        db.session.commit()
        return True
    except Exception as e:
        print(f"Error logging trade: {e}")
        return False
