FROM python:3.11-slim

LABEL maintainer="BTC Signal Bot"
LABEL description="Profissional BTC Trading Signal Bot — BTC/EUR, BTC/USD, BTC/USDC"

RUN apt-get update && apt-get install -y gcc libfreetype6-dev libpng-dev fonts-dejavu-core && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/logs

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TZ=UTC

CMD ["python", "main.py"]
