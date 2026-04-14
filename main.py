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
    return "Bot de Trading Rocío (MEXC + EMA 200) Activo 🚀"

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

SL_PERCENT = 0.015  # Stop Loss 1.5%
TP_PERCENT = 0.03   # Take Profit 3.0%

# Memoria para alertas
last_alert_state = {'BTC/USDT': None, 'ETH/USDT': None, 'SOL/USDT': None, 'ZEC/USDT': None, 'XRP/USDT': None}

def enviar_telegram(mensaje):
    if TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload)
        except Exception as e:
            print(f"Error Telegram: {e}")

def calcular_indicadores(precios, periodo_rsi=14, periodo_ema=200):
    df = pd.DataFrame(precios, columns=['close'])
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0))
    loss = (-delta.where(delta < 0, 0))
    avg_gain = gain.ewm(alpha=1/periodo_rsi, min_periods=periodo_rsi).mean()
    avg_loss = loss.ewm(alpha=1/periodo_rsi, min_periods=periodo_rsi).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    df['ema'] = df['close'].ewm(span=periodo_ema, adjust=False).mean()
    return df['rsi'].iloc[-1], df['ema'].iloc[-1]

def trading_loop():
    print("Iniciando análisis con MEXC (Sin restricciones regionales)...", flush=True)
    enviar_telegram("✅ *Bot Rocío Activo*\nConexión vía *MEXC* establecida. ¡Adiós a los errores rojos!")
    
    # CAMBIO DEFINITIVO: MEXC es más flexible con las ubicaciones de los servidores
    exchange = ccxt.mexc()
    
    watchlist = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ZEC/USDT', 'XRP/USDT']

    while True:
        try:
            for moneda in watchlist:
                # MEXC usa nombres simples para Spot
                bars = exchange.fetch_ohlcv(moneda, timeframe='5m', limit=300)
                precios = [b[4] for b in bars]
                precio_actual = precios[-1]
                
                rsi, ema = calcular_indicadores(precios)
                es_alcista = precio_actual > ema
                
                print(f"{moneda}: ${precio_actual} | RSI {rsi:.2f} | EMA {ema:.2f}", flush=True)

                if (rsi < 30 or (es_alcista and rsi > 55)) and last_alert_state[moneda] != 'long':
                    tipo = "LONG (Reversión)" if rsi < 30 else "LONG (Tendencia)"
                    sl = precio_actual * (1 - SL_PERCENT)
                    tp = precio_actual * (1 + TP_PERCENT)
                    msg = (f"🔵 *ALERTA DE {tipo}*\n🏆 Moneda: {moneda}\n📊 RSI: {rsi:.2f}\n💵 *Entrada:* ${precio_actual:,.2f}\n🚫 *SL:* ${sl:,.2f} | 🎯 *TP:* ${tp:,.2f}")
                    enviar_telegram(msg)
                    last_alert_state[moneda] = 'long'

                elif rsi > 70 and not es_alcista and last_alert_state[moneda] != 'short':
                    sl = precio_actual * (1 + SL_PERCENT)
                    tp = precio_actual * (1 - TP_PERCENT)
                    msg = (f"🔴 *AVISO DE SHORT*\n🏆 Moneda: {moneda}\n📉 RSI: {rsi:.2f}\n💵 *Entrada:* ${precio_actual:,.2f}\n🚫 *SL:* ${sl:,.2f} | 🎯 *TP:* ${tp:,.2f}")
                    enviar_telegram(msg)
                    last_alert_state[moneda] = 'short'
                
                elif 42 < rsi < 48:
                    last_alert_state[moneda] = None
            
            time.sleep(60)
        except Exception as e:
            print(f"Reintentando... Error: {e}", flush=True)
            time.sleep(10)

if __name__ == "__main__":
    t = threading.Thread(target=trading_loop)
    t.daemon = True
    t.start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
