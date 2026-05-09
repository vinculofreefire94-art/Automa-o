FROM python:3.11-slim

LABEL maintainer="BTC Signal Bot"
LABEL description="Profissional BTC Trading Signal Bot — BTC/EUR, BTC/USD, BTC/USDC"

# Sistema
RUN apt-get update && apt-get install -y gcc git libfreetype6-dev libpng-dev fonts-dejavu-core && rm -rf /var/lib/apt/lists/*


WORKDIR /app

# Dependências Python
COPY requirements.txt .
RUN pip install https://github.com/twopirllc/pandas-ta/archive/refs/heads/development.zip


# Código
COPY . .

# Cria pasta de logs
RUN mkdir -p /app/logs

# Variáveis de ambiente (override via .env ou docker-compose)
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TZ=UTC

CMD ["python", "main.py"]
