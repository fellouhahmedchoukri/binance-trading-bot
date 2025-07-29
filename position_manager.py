import os
import logging
from binance.client import Client
from binance.exceptions import BinanceAPIException
from flask import current_app
from models import db, Position, Trade, Snapshot
import time

class PositionManager:
    def __init__(self, app, testnet=True):
        self.app = app
        self.testnet = testnet
        self.client = self.initialize_binance_client()
        logging.info("PositionManager initialized")

    def initialize_binance_client(self):
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_API_SECRET')
        client = Client(
            api_key=api_key,
            api_secret=api_secret,
            testnet=self.testnet
        )
        logging.info(f"Binance API initialized successfully for {'TESTNET' if self.testnet else 'PRODUCTION'}")
        logging.info(f"Binance API URL: {client.API_URL}")
        return client

    def execute_trade(self, symbol, side, quantity):
        try:
            # Créer un ordre
            order = self.client.create_order(
                symbol=symbol,
                side=side.upper(),
                type='MARKET',
                quantity=quantity
            )
            
            # Enregistrer le trade dans la base de données
            with self.app.app_context():
                trade = Trade(
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    price=float(order['fills'][0]['price']),
                    status=order['status']
                )
                db.session.add(trade)
                db.session.commit()
            
            logging.info(f"Trade executed: {side} {quantity} {symbol}")
            return order
        
        except BinanceAPIException as e:
            logging.error(f"Binance API error: {e.message}")
            raise
        except Exception as e:
            logging.error(f"Trade execution error: {str(e)}")
            raise

    def save_snapshot(self):
        try:
            # Récupérer les données nécessaires
            account = self.client.get_account()
            positions = Position.query.all()
            
            # Créer un snapshot
            snapshot = Snapshot(
                total_balance=float(account['totalWalletBalance']),
                available_balance=float(account['availableBalance']),
                positions_count=len(positions)
            )
            
            # Sauvegarder dans la base de données
            with self.app.app_context():
                db.session.add(snapshot)
                db.session.commit()
            
            logging.info("Snapshot saved successfully")
            
        except Exception as e:
            logging.error(f"Error saving snapshot: {str(e)}")
            with self.app.app_context():
                db.session.rollback()

    def monitor_pending_orders(self):
        try:
            # Récupérer les ordres en attente
            orders = self.client.get_open_orders()
            
            # Logique de surveillance
            for order in orders:
                # Votre logique de traitement des ordres en attente
                logging.info(f"Monitoring order: {order['symbol']} {order['side']} {order['quantity']}")
                
            logging.info(f"Monitoring {len(orders)} pending orders")
            
        except Exception as e:
            logging.error(f"Error monitoring orders: {str(e)}")
