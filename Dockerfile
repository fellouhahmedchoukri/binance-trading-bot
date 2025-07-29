FROM python:3.10-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y gcc

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Set environment variables
ENV FLASK_APP=main.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000

# Initialize database
RUN python -c "from position_manager import PositionManager; PositionManager()"

CMD ["flask", "run"]

# Dockerfile
# ...

# Initialize database
RUN python -c "from position_manager import PositionManager; pm = PositionManager(); pm.get_connection()"

CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
