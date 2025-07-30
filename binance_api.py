from binance.client import Client
import logging

class BinanceAPI:
    def __init__(self, api_key, api_secret, testnet=True):
        self.testnet = testnet
        
        # Configuration de l'URL en fonction du mode
        self.api_url = "https://testnet.binance.vision" if testnet else "https://api.binance.com"
        
        # Initialisation du client Binance
        self.client = Client(
            api_key=api_key,
            api_secret=api_secret,
            testnet=self.testnet
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Binance API initialized for {'TESTNET' if testnet else 'MAINNET'}")

    # ... (le reste des méthodes inchangé)
