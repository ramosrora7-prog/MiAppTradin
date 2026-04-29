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

# --- CONFIGURACIÓN MATEMÁTICA V4.1 ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Gestión de riesgo estricta para cuenta de $25
SL_PERCENT = 0.008  
TP_PERCENT = 0.012  

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
    print("🤖 Modo Matemática Pura V4.1...", flush=True)
    enviar_telegram("📊 *V4.1: SISTEMA MATEMÁTICO ACTIVO*\nConexión estable. Vigilando 6 activos en 5m.")
    
    exchange = ccxt.mexc({'timeout': 30000, 'enableRateLimit': True})

    while True:
        try:
            for moneda in watchlist:
                bars = exchange.fetch_ohlcv(moneda, timeframe='5m', limit=150)
                precios = [b[4] for b in bars]
                precio_actual = precios[-1]
                rsi_actual, ema = calcular_indicadores(precios)
                rsi_previo = last_rsi_value[moneda]
                
                giro_rsi = rsi_actual - rsi_previo
                es_alcista = precio_actual > ema
                
                # --- LÓGICA MATEMÁTICA SIN EMOCIONES ---
                # COMPRA: RSI bajo con giro fuerte de recuperación
                if rsi_actual < 44 and giro_rsi > 0.25 and last_alert_state[moneda] != 'long':
                    estado = "🛡️ FAVOR DE TENDENCIA" if es_alcista else "⚠️ REBOTE CORTO"
                    msg = (f"🔵 *SEÑAL DE COMPRA*\n"
                           f"━━━━━━━━━━━━━━━\n"
                           f"🪙 *Moneda:* {moneda}\n"
                           f"📊 *Tipo:* {estado}\n"
                           f"💵 *Entrada:* ${precio_actual:,.4f}\n"
                           f"🎯 *TP:* ${precio_actual*(1+TP_PERCENT):,.4f}\n"
                           f"🛑 *SL:* ${precio_actual*(1-SL_PERCENT):,.4f}")
                    enviar_telegram(msg)
                    last_alert_state[moneda] = 'long'

                # VENTA: RSI alto con giro de agotamiento
                elif rsi_actual > 56 and giro_rsi < -0.25 and last_alert_state[moneda] != 'short':
                    estado = "🛡️ FAVOR DE TENDENCIA" if not es_alcista else "⚠️ REBOTE CORTO"
                    msg = (f"🔴 *SEÑAL DE VENTA*\n"
                           f"━━━━━━━━━━━━━━━\n"
                           f"🪙 *Moneda:* {moneda}\n"
                           f"📊 *Tipo:* {estado}\n"
                           f"💵 *Entrada:* ${precio_actual:,.4f}\n"
                           f"🎯 *TP:* ${precio_actual*(1-TP_PERCENT):,.4f}\n"
                           f"🛑 *SL:* ${precio_actual*(1+SL_PERCENT):,.4f}")
                    enviar_telegram(msg)
                    last_alert_state[moneda] = 'short'
                
                elif 48 < rsi_actual < 52:
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
