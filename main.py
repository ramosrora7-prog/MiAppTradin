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
    return "OK"

# --- CONFIGURACIÓN CON ADA INCLUIDA ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

SL_PERCENT = 0.008  
TP_PERCENT = 0.012  

# Lista actualizada: Ahora vigilamos 6 monedas
watchlist = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'DOGE/USDT', 'ADA/USDT']
last_alert_state = {m: None for m in watchlist}
last_rsi_value = {m: 50.0 for m in watchlist}

def enviar_telegram(mensaje):
    if TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
        try: requests.post(url, json=payload, timeout=10)
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
    print("🚀 Iniciando V3.9.1 con ADA...", flush=True)
    enviar_telegram("✅ *Bot Rocío V3.9.1 Actualizado*\nMoneda agregada: *ADA/USDT*. Escaneando 6 activos.")
    
    exchange = ccxt.mexc({'timeout': 30000, 'enableRateLimit': True})

    while True:
        try:
            for moneda in watchlist:
                bars = exchange.fetch_ohlcv(moneda, timeframe='5m', limit=100)
                precios = [b[4] for b in bars]
                precio_actual = precios[-1]
                rsi_actual, ema = calcular_indicadores(precios)
                rsi_previo = last_rsi_value[moneda]
                
                giro_rsi = rsi_actual - rsi_previo
                es_alcista = precio_actual > ema
                
                # --- LÓGICA DE COMPRA ---
                if rsi_actual < 42 and giro_rsi > 0.2 and last_alert_state[moneda] != 'long':
                    msg = (f"🔵 *COMPRA DETECTADA*\n"
                           f"🪙 {moneda}\n"
                           f"📊 Trend: {'ALCISTA' if es_alcista else 'BAJISTA (Rebote)'}\n"
                           f"⚡ RSI: {rsi_actual:.1f}\n"
                           f"💵 Entrada: ${precio_actual:,.4f}\n"
                           f"🎯 TP: ${precio_actual*(1+TP_PERCENT):,.4f} | 🛑 SL: ${precio_actual*(1-SL_PERCENT):,.4f}")
                    enviar_telegram(msg)
                    last_alert_state[moneda] = 'long'

                # --- LÓGICA DE VENTA ---
                elif rsi_actual > 58 and giro_rsi < -0.2 and last_alert_state[moneda] != 'short':
                    msg = (f"🔴 *VENTA DETECTADA*\n"
                           f"🪙 {moneda}\n"
                           f"📊 Trend: {'BAJISTA' if not es_alcista else 'ALCISTA (Rebote)'}\n"
                           f"⚡ RSI: {rsi_actual:.1f}\n"
                           f"💵 Entrada: ${precio_actual:,.4f}\n"
                           f"🎯 TP: ${precio_actual*(1-TP_PERCENT):,.4f} | 🛑 SL: ${precio_actual*(1+SL_PERCENT):,.4f}")
                    enviar_telegram(msg)
                    last_alert_state[moneda] = 'short'
                
                elif 47 < rsi_actual < 53:
                    last_alert_state[moneda] = None
                
                last_rsi_value[moneda] = rsi_actual
            
            time.sleep(30)
        except Exception as e:
            time.sleep(20)

if __name__ == "__main__":
    t = threading.Thread(target=trading_loop)
    t.daemon = True
    t.start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
