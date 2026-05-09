# 🤖 BTC Signal Bot

> **Bot profissional de sinais de trading** para Bitcoin em pares EUR, USD e USDC.  
> Análise técnica multi-indicador com envio automático de ordens para Telegram — gráficos nível elite.

---

## ✨ Funcionalidades

| Feature | Detalhe |
|---|---|
| 📊 **Pares** | BTC/EUR · BTC/USDT · BTC/USDC |
| ⏱️ **Timeframes** | 1H · 4H · 1D (análise multi-TF) |
| 🧠 **Indicadores** | RSI · MACD · EMA 9/21/50/200 · BB · Stochastic · ATR · OBV · Volume |
| 🕯️ **Padrões** | Hammer · Engulfing · Marubozu · Doji · Shooting Star |
| 📐 **Risk Mgmt** | TP e SL dinâmicos via ATR · Ratio R/R automático |
| 📈 **Gráfico** | Dark terminal · 4 painéis · Candles · EMAs · BB · MACD · RSI · Volume |
| 📡 **Telegram** | Sinal formatado + gráfico PNG · Emojis profissionais · Score e força |
| 🔄 **Scheduler** | Scan automático configurável (padrão: 15min) |
| 🐳 **Deploy** | Docker · Docker Compose · GitHub Actions CI/CD |

---

## 🚀 Instalação Rápida

### Opção 1 — Python direto

```bash
git clone https://github.com/SEU_USER/btc-signal-bot
cd btc-signal-bot
pip install -r requirements.txt
cp .env.example .env
# edita .env com as tuas chaves
python main.py
```

### Opção 2 — Docker (recomendado)

```bash
cp .env.example .env
# edita .env
docker-compose up -d
```

---

## ⚙️ Configuração (`.env`)

```env
TELEGRAM_BOT_TOKEN=7123456789:AAF...
TELEGRAM_CHAT_ID=-1001234567890
TELEGRAM_ADMIN_ID=123456789

PAIRS=BTC/USDT,BTC/EUR,BTC/USDC
TIMEFRAMES=1h,4h,1d
SCAN_INTERVAL_MINUTES=15
MIN_SIGNAL_STRENGTH=2
SEND_ALL_SIGNALS=true
```

### Como criar o bot Telegram

1. Fala com `@BotFather` no Telegram
2. `/newbot` → segue as instruções → copia o token
3. Adiciona o bot ao teu canal/grupo
4. Pega o Chat ID: `https://api.telegram.org/bot<TOKEN>/getUpdates`

---

## 📊 Exemplo de Sinal

```
🔔 SINAL DE COMPRA DETECTADO
━━━━━━━━━━━━━━━━━━━━━━━━━━━

🟢 COMPRA  📈
🚀 Força: ULTRA FORTE  [▓▓▓▓]

Par        ₿ • USDT
Timeframe  4 Horas
Preço      $67,420.00

📊 Score de Confiança
█████████░  92/100

🏗️ Contexto de Mercado
  📈 Tendência D1:  BULLISH
  📈 Tendência 4H:  BULLISH
  🚀 Fase:          MARKUP

📈 Indicadores
  RSI    28.4  ✅ Sobrevendido
  MACD   ↑ Bullish  Bullish Cross
  EMA    BULLISH
  Stoch  K:  18  D:  22
  ATR    2.31%  (Normal volatilidade)
  Vol    2.4x  📊↑
  BB     8%  ← Banda inferior

🎯 Razões do Sinal
   ├─ ✦ RSI sobrevendido (28.4)
   ├─ ✦ MACD cruzamento bullish 🔀
   ├─ ✦ EMAs em stack bullish perfeito
   ├─ ✦ Preço na banda inferior de BB
   └─ ✦ Hammer detectado

╔══════════════════════════╗
║  💰 ENTRADA     $67,420.00  ║
║  🎯 TAKE PROFIT $68,800.00  ║
║  🛡️ STOP LOSS   $66,730.00  ║
║  📐 RISCO/RET          2.00x  ║
╚══════════════════════════╝
```

---

## 🏗️ Estrutura do Projeto

```
btc-signal-bot/
├── main.py                    # Orquestrador principal
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── core/
│   ├── config.py              # Configuração centralizada
│   ├── fetcher.py             # Busca dados via ccxt (Binance)
│   └── analyzer.py            # Motor de análise técnica
├── charts/
│   └── generator.py           # Gráfico elite dark theme
├── telegram/
│   └── sender.py              # Formatter + Sender Telegram
└── .github/
    └── workflows/
        └── deploy.yml         # CI/CD GitHub Actions
```

---

## 📐 Lógica de Sinais

O bot **não depende de um score mínimo alto** para agir. Em vez disso:

1. Cada indicador contribui com pontos independentes (sem threshold rígido)
2. O sinal é gerado mal uma oportunidade seja identificada
3. A **força** (1-4) ajuda a filtrar — mas `SEND_ALL_SIGNALS=true` envia tudo
4. Anti-duplicata: mesmo sinal no mesmo par → refractory de 2h

### Pesos dos Indicadores

| Indicador | Peso (pts) |
|---|---|
| RSI extremo | 15 |
| MACD cross | 20 |
| EMA Stack | 18 |
| Bollinger Band | 12 |
| Stochastic cross | 15 |
| Suporte/Resistência | 10 |
| Candlestick Pattern | 12 |
| Volume alto | 8 |
| OBV trend | 8 |

---

## 🛡️ Aviso Legal

> Este bot é apenas para fins **educativos e informativos**.  
> Não constitui aconselhamento financeiro.  
> Trading de criptomoedas envolve risco substancial de perda.  
> Usa sempre gestão de risco adequada.

---

## 📜 Licença

MIT — livre para usar, modificar e distribuir.
