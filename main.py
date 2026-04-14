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
    return "Bot Rocío Híbrido (Cortas + Tendencias) Activo 🚀"

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# --- CONFIGURACIÓN DE SCALPING RÁPIDO ---
SL_PERCENT = 0.008  # Stop Loss corto (0.8%) para proteger capital
TP_PERCENT = 0.012  # Ganancia rápida (1.2%) para sumar de a poco

last_alert_state = {'BTC/USDT': None, 'ETH/USDT': None, 'SOL/USDT': None, 'ZEC/USDT': None, 'XRP/USDT': None}

def enviar_telegram(mensaje):
    if TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload)
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
    print("Bot Híbrido Iniciado...", flush=True)
    enviar_telegram("⚡ *Bot Rocío Modo Guerrero Activo*\nDetectando rebotes cortos y tendencias al mismo tiempo.")
    
    exchange = ccxt.mexc()
    watchlist = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ZEC/USDT', 'XRP/USDT']

    while True:
        try:
            for moneda in watchlist:
                bars = exchange.fetch_ohlcv(moneda, timeframe='5m', limit=250)
                precios = [b[4] for b in bars]
                precio_actual = precios[-1]
                rsi, ema = calcular_indicadores(precios)
                
                es_alcista = precio_actual > ema
                distancia_ema = ((precio_actual - ema) / ema) * 100

                # --- LÓGICA DE SEÑALES ---
                
                # LONG (RSI bajo)
                if rsi < 35 and last_alert_state[moneda] != 'long':
                    # Verifica si además es tendencia
                    contexto = "🔥 TENDENCIA + REBOTE" if es_alcista else "❄️ REBOTE (Contra tendencia)"
                    sl = precio_actual * (1 - SL_PERCENT)
                    tp = precio_actual * (1 + TP_PERCENT)
                    
                    msg = (f"🔵 *¡SEÑAL DE COMPRA!* ({moneda})\n"
                           f"━━━━━━━━━━━━━━━\n"
                           f"📢 *Tipo:* {contexto}\n"
                           f"📉 *RSI:* {rsi:.2f} | *EMA 200:* ${ema:,.2f}\n"
                           f"💵 *Entrada:* ${precio_actual:,.2f}\n"
                           f"🎯 *TP:* ${tp:,.2f} | 🛑 *SL:* ${sl:,.2f}")
                    enviar_telegram(msg)
                    last_alert_state[moneda] = 'long'

                # SHORT (RSI alto)
                elif rsi > 65 and last_alert_state[moneda] != 'short':
                    contexto = "🔥 TENDENCIA + CAÍDA" if not es_alcista else "❄️ CAÍDA (Contra tendencia)"
                    sl = precio_actual * (1 + SL_PERCENT)
                    tp = precio_actual * (1 - TP_PERCENT)
                    
                    msg = (f"🔴 *¡SEÑAL DE VENTA!* ({moneda})\n"
                           f"━━━━━━━━━━━━━━━\n"
                           f"📢 *Tipo:* {contexto}\n"
                           f"📈 *RSI:* {rsi:.2f} | *EMA 200:* ${ema:,.2f}\n"
                           f"💵 *Entrada:* ${precio_actual:,.2f}\n"
                           f"🎯 *TP:* ${tp:,.2f} | 🛑 *SL:* ${sl:,.2f}")
                    enviar_telegram(msg)
                    last_alert_state[moneda] = 'short'
                
                elif 42 < rsi < 48:
                    last_alert_state[moneda] = None
            
            time.sleep(60)
        except Exception as e:
            time.sleep(10)

if __name__ == "__main__":
    t = threading.Thread(target=trading_loop)
    t.daemon = True
    t.start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
