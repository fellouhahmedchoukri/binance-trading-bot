import sqlite3
from datetime import datetime, timedelta
import threading
import logging

class PositionManager:
    def __init__(self, db_path='positions.db'):
        self.db_path = db_path
        self.local = threading.local()
        self.logger = logging.getLogger(__name__)
        self.initialize_db()
    
    def get_connection(self):
        """Retourne une connexion à la base de données pour le thread courant"""
        if not hasattr(self.local, 'conn') or not self.local.conn:
            self.local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.local.conn.execute("PRAGMA journal_mode=WAL")
        return self.local.conn
    
    def initialize_db(self):
        """Initialisation de la base de données dans le thread principal"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                entry_price REAL NOT NULL,
                quantity REAL NOT NULL,
                order_id TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pending_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                order_id TEXT NOT NULL UNIQUE,
                side TEXT NOT NULL,
                price REAL NOT NULL,
                quantity REAL NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    
    # Positions management
    def add_position(self, symbol, entry_price, quantity, order_id=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO positions (symbol, entry_price, quantity, order_id)
            VALUES (?, ?, ?, ?)
        ''', (symbol, entry_price, quantity, order_id))
        conn.commit()
    
    def get_positions(self, symbol):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, symbol, entry_price, quantity, order_id, timestamp
            FROM positions
            WHERE symbol = ?
        ''', (symbol,))
        return [{
            'id': row[0],
            'symbol': row[1],
            'entry_price': row[2],
            'quantity': row[3],
            'order_id': row[4],
            'timestamp': row[5]
        } for row in cursor.fetchall()]
    
    # ... (le reste des méthodes reste inchangé, mais utilise toujours get_connection())
    
    def __del__(self):
        """Ferme les connexions à la destruction"""
        if hasattr(self.local, 'conn') and self.local.conn:
            self.local.conn.close()
    
    def get_symbols(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT DISTINCT symbol FROM positions')
        return [row[0] for row in cursor.fetchall()]
    
    def get_last_entry_price(self, symbol):
        positions = self.get_positions(symbol)
        if not positions:
            return None
        return max(positions, key=lambda x: x['timestamp'])['entry_price']
    
    def calculate_avg_price(self, symbol):
        positions = self.get_positions(symbol)
        if not positions:
            return 0.0
        
        total_qty = sum(p['quantity'] for p in positions)
        total_value = sum(p['entry_price'] * p['quantity'] for p in positions)
        return total_value / total_qty
    
    def remove_position(self, position_id):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM positions WHERE id = ?', (position_id,))
        self.conn.commit()
    
    def remove_all_positions(self, symbol):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM positions WHERE symbol = ?', (symbol,))
        self.conn.commit()
    
    # Pending orders management
    def add_pending_order(self, symbol, order_id, side, price, quantity):
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO pending_orders (symbol, order_id, side, price, quantity)
                VALUES (?, ?, ?, ?, ?)
            ''', (symbol, order_id, side, price, quantity))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            self.logger.warning(f"Duplicate order ID: {order_id}")
            return False
    
    def get_pending_orders(self, symbol=None):
        cursor = self.conn.cursor()
        if symbol:
            cursor.execute('''
                SELECT id, symbol, order_id, side, price, quantity, created_at
                FROM pending_orders
                WHERE symbol = ?
            ''', (symbol,))
        else:
            cursor.execute('''
                SELECT id, symbol, order_id, side, price, quantity, created_at
                FROM pending_orders
            ''')
        
        return [{
            'id': row[0],
            'symbol': row[1],
            'order_id': row[2],
            'side': row[3],
            'price': row[4],
            'quantity': row[5],
            'created_at': row[6]
        } for row in cursor.fetchall()]
    
    def remove_pending_order(self, order_id):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM pending_orders WHERE order_id = ?', (order_id,))
        self.conn.commit()
    
    def is_order_old(self, order_id, minutes=5):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT created_at FROM pending_orders WHERE order_id = ?
        ''', (order_id,))
        result = cursor.fetchone()
        
        if not result:
            return False
        
        created_at = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
        return datetime.now() - created_at > timedelta(minutes=minutes)
    
    def __del__(self):
        self.conn.close()
