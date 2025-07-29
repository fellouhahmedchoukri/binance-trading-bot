import os
import logging
from binance.client import Client
from binance.exceptions import BinanceAPIException
from flask import current_app
from models import TradingSnapshot, TradeHistory  # Modifié l'import
import time

class PositionManager:
    def __init__(self):
        self.positions = {}  # symbol: list of positions
        self.pending_orders = {}  # order_id: order
        self.logger = logging.getLogger(__name__)
        self.logger.info("PositionManager initialized (in-memory)")

    def sync_with_exchange(self, binance):
        """Synchronise les positions et ordres avec l'échange"""
        try:
            # Récupérer les positions ouvertes
            positions = binance.get_positions()
            for symbol, pos in positions.items():
                self.positions[symbol] = pos
            
            # Récupérer les ordres en attente
            orders = binance.get_open_orders()
            for order in orders:
                self.pending_orders[order['orderId']] = order
            
            self.logger.info(f"Synchronized: {len(self.positions)} positions, {len(self.pending_orders)} orders")
            return True
        except Exception as e:
            self.logger.error(f"Sync error: {e}")
            return False

    def add_position(self, symbol, entry_price, quantity, order_id):
        """Ajoute une position ouverte"""
        if symbol not in self.positions:
            self.positions[symbol] = []
        self.positions[symbol].append({
            'entry_price': entry_price,
            'quantity': quantity,
            'order_id': order_id,
            'timestamp': time.time()
        })

    def remove_position(self, symbol, position_id):
        """Supprime une position par son identifiant"""
        if symbol in self.positions:
            self.positions[symbol] = [p for p in self.positions[symbol] if p['id'] != position_id]

    def remove_all_positions(self, symbol):
        """Supprime toutes les positions pour un symbole"""
        if symbol in self.positions:
            del self.positions[symbol]

    def get_positions(self, symbol):
        """Retourne les positions pour un symbole"""
        return self.positions.get(symbol, [])

    def get_symbols(self):
        """Retourne la liste des symboles ayant des positions"""
        return list(self.positions.keys())

    def add_pending_order(self, symbol, order_id, side, price, quantity):
        """Ajoute un ordre en attente"""
        self.pending_orders[order_id] = {
            'symbol': symbol,
            'side': side,
            'price': price,
            'quantity': quantity,
            'timestamp': time.time()
        }

    def remove_pending_order(self, order_id):
        """Supprime un ordre en attente"""
        if order_id in self.pending_orders:
            del self.pending_orders[order_id]

    def get_pending_orders(self):
        """Retourne tous les ordres en attente"""
        return list(self.pending_orders.values())

    def is_order_old(self, order_id, minutes=5):
        """Vérifie si un ordre est ancien (plus de X minutes)"""
        if order_id not in self.pending_orders:
            return False
        order = self.pending_orders[order_id]
        return time.time() - order['timestamp'] > minutes * 60

    def get_last_entry_price(self, symbol):
        """Obtient le dernier prix d'entrée pour un symbole"""
        positions = self.get_positions(symbol)
        if not positions:
            return None
        return positions[-1]['entry_price']

    def calculate_avg_price(self, symbol):
        """Calcule le prix moyen d'entrée pour un symbole"""
        positions = self.get_positions(symbol)
        if not positions:
            return 0
        total_cost = sum(p['entry_price'] * p['quantity'] for p in positions)
        total_quantity = sum(p['quantity'] for p in positions)
        return total_cost / total_quantity

    def get_unrealized_profit(self, symbol, current_price):
        """Calcule le profit non réalisé pour un symbole"""
        positions = self.get_positions(symbol)
        if not positions:
            return 0
        total_value = 0
        total_cost = 0
        for p in positions:
            total_cost += p['entry_price'] * p['quantity']
            total_value += current_price * p['quantity']
        return total_value - total_cost
