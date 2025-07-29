FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Commande de test mise à jour
RUN python -c "from position_manager import PositionManager; pm = PositionManager(); print('PositionManager initialized successfully')"

CMD ["python", "main.py"]
