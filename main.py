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
    return "OK" # Mantenemos la conexión estable con cron-job

# --- CONFIGURACIÓN HÍBRIDA (ALERTAS CONSTANTES) ---
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
    print("Bot V3.5 Híbrido Iniciado...", flush=True)
    enviar_telegram("🚀 *Bot Rocío V3.5 Híbrido Activo*\nDetectando tendencias y operaciones cortas 24/7.")
    
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
                
                giro_rsi = rsi_actual - rsi_previo
                es_alcista = precio_actual > ema
                
                # --- LÓGICA DE ALERTA ---
                # Compra: RSI bajo (< 38) y subiendo (+0.4)
                if rsi_actual < 38 and giro_rsi > 0.4 and last_alert_state[moneda] != 'long':
                    tipo = "🟢 FAVOR DE TENDENCIA" if es_alcista else "⚠️ CONTRA TENDENCIA (Corta)"
                    msg = (f"🔵 *NUEVA COMPRA*\n"
                           f"━━━━━━━━━━━━━━━\n"
                           f"🪙 *Moneda:* {moneda}\n"
                           f"📊 *Tipo:* {tipo}\n"
                           f"📈 *Trend:* {'ALCISTA' if es_alcista else 'BAJISTA'}\n"
                           f"💵 *Entrada:* ${precio_actual:,.4f}\n"
                           f"🎯 *TP:* ${precio_actual*(1+TP_PERCENT):,.4f}\n"
                           f"🛑 *SL:* ${precio_actual*(1-SL_PERCENT):,.4f}")
                    enviar_telegram(msg)
                    last_alert_state[moneda] = 'long'

                # Venta: RSI alto (> 62) y bajando (-0.4)
                elif rsi_actual > 62 and giro_rsi < -0.4 and last_alert_state[moneda] != 'short':
                    tipo = "🟢 FAVOR DE TENDENCIA" if not es_alcista else "⚠️ CONTRA TENDENCIA (Corta)"
                    msg = (f"🔴 *NUEVA VENTA*\n"
                           f"━━━━━━━━━━━━━━━\n"
                           f"🪙 *Moneda:* {moneda}\n"
                           f"📊 *Tipo:* {tipo}\n"
                           f"📉 *Trend:* {'ALCISTA' if es_alcista else 'BAJISTA'}\n"
                           f"💵 *Entrada:* ${precio_actual:,.4f}\n"
                           f"🎯 *TP:* ${precio_actual*(1-TP_PERCENT):,.4f}\n"
                           f"🛑 *SL:* ${precio_actual*(1+SL_PERCENT):,.4f}")
                    enviar_telegram(msg)
                    last_alert_state[moneda] = 'short'
                
                elif 45 < rsi_actual < 55:
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
