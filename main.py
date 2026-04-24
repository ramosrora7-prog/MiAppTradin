import ccxt
import time
import os
import threading
import requests
import pandas as pd
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "OK" # Mantiene cron-job feliz

# --- CONFIGURACIÓN OPTIMIZADA PARA MÁS ALERTAS ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

SL_PERCENT = 0.008  
TP_PERCENT = 0.012  

last_alert_state = {'BTC/USDT': None, 'ETH/USDT': None, 'SOL/USDT': None, 'ZEC/USDT': None, 'XRP/USDT': None}
last_rsi_value = {'BTC/USDT': 50.0, 'ETH/USDT': 50.0, 'SOL/USDT': 50.0, 'ZEC/USDT': 50.0, 'XRP/USDT': 50.0}

def enviar_telegram(mensaje):
    if TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
        try: requests.post(url, json=payload)
        except: pass

def calcular_indicadores(precios):
    df = pd.DataFrame(precios, columns=['close'])
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0))
    loss = (-delta.where(delta < 0, 0))
    avg_gain = gain.ewm(alpha=1/14, min_periods=14).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    ema = df['close'].ewm(span=200, adjust=False).mean()
    return rsi.iloc[-1], ema.iloc[-1]

def trading_loop():
    print("Bot V3.3 (Más Alertas) Iniciado...", flush=True)
    enviar_telegram("🔥 *Bot Rocío V3.3 Activo*\nFiltros ajustados para detectar más oportunidades.")
    
    exchange = ccxt.mexc()
    watchlist = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ZEC/USDT', 'XRP/USDT']

    while True:
        try:
            for moneda in watchlist:
                bars = exchange.fetch_ohlcv(moneda, timeframe='5m', limit=250)
                precios = [b[4] for b in bars]
                precio_actual = precios[-1]
                rsi_actual, ema = calcular_indicadores(precios)
                rsi_previo = last_rsi_value[moneda]
                
                es_alcista = precio_actual > ema
                giro_rsi = rsi_actual - rsi_previo

                # --- COMPRA (Más sensible: RSI < 35 y Giro > 0.6) ---
                if rsi_actual < 35 and giro_rsi > 0.6 and es_alcista and last_alert_state[moneda] != 'long':
                    sl = precio_actual * (1 - SL_PERCENT)
                    tp = precio_actual * (1 + TP_PERCENT)
                    msg = (f"🔵 *SEÑAL DE COMPRA*\n"
                           f"🪙 *Moneda:* {moneda}\n"
                           f"📈 *Trend:* ALCISTA\n"
                           f"⚡ *Giro RSI:* +{giro_rsi:.2f}\n"
                           f"💵 *Entrada:* ${precio_actual:,.4f}")
                    enviar_telegram(msg)
                    last_alert_state[moneda] = 'long'

                # --- VENTA (Más sensible: RSI > 65 y Giro < -0.6) ---
                elif rsi_actual > 65 and giro_rsi < -0.6 and not es_alcista and last_alert_state[moneda] != 'short':
                    sl = precio_actual * (1 + SL_PERCENT)
                    tp = precio_actual * (1 - TP_PERCENT)
                    msg = (f"🔴 *SEÑAL DE VENTA*\n"
                           f"🪙 *Moneda:* {moneda}\n"
                           f"📉 *Trend:* BAJISTA\n"
                           f"⚡ *Giro RSI:* {giro_rsi:.2f}\n"
                           f"💵 *Entrada:* ${precio_actual:,.4f}")
                    enviar_telegram(msg)
                    last_alert_state[moneda] = 'short'
                
                # Reseteo más rápido para permitir nuevas señales pronto
                elif 42 < rsi_actual < 58:
                    last_alert_state[moneda] = None
                
                last_rsi_value[moneda] = rsi_actual
            time.sleep(60)
        except Exception as e:
            time.sleep(10)

if __name__ == "__main__":
    t = threading.Thread(target=trading_loop)
    t.daemon = True
    t.start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
