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
    return "Bot de Trading Rocío (EMA 200 + RSI) en Línea 📈"

# Usamos TUS datos que ya están en Render
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# --- CONFIGURACIÓN DE ESTRATEGIA ---
SL_PERCENT = 0.015  # Stop Loss al 1.5%
TP_PERCENT = 0.03   # Take Profit al 3%
EMA_TENDENCIA = 200 

# Memoria para no repetir alertas
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
    
    # RSI Wilder
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0))
    loss = (-delta.where(delta < 0, 0))
    avg_gain = gain.ewm(alpha=1/periodo_rsi, min_periods=periodo_rsi).mean()
    avg_loss = loss.ewm(alpha=1/periodo_rsi, min_periods=periodo_rsi).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # EMA 200 (El filtro de tendencia)
    df['ema'] = df['close'].ewm(span=periodo_ema, adjust=False).mean()
    
    return df['rsi'].iloc[-1], df['ema'].iloc[-1]

def trading_loop():
    print("Iniciando análisis con Filtro de Tendencia...", flush=True)
    enviar_telegram("✅ *Bot Rocío Actualizado*\nEstrategia: EMA 200 + RSI activada.")
    
    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    # Ajusté tu watchlist con tus monedas favoritas
    watchlist = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ZEC/USDT', 'XRP/USDT']

    while True:
        try:
            for moneda in watchlist:
                # Pedimos 300 velas para que la EMA 200 sea exacta
                bars = exchange.fetch_ohlcv(moneda, timeframe='5m', limit=300)
                precios = [b[4] for b in bars]
                precio_actual = precios[-1]
                
                rsi, ema = calcular_indicadores(precios)
                es_alcista = precio_actual > ema
                
                print(f"{moneda}: ${precio_actual} | RSI {rsi:.2f} | EMA {ema:.2f}", flush=True)

                # --- LÓGICA DE ENTRADA ---

                # COMPRA (LONG): Si está en sobreventa O si es tendencia alcista y toma fuerza
                if (rsi < 30 or (es_alcista and rsi > 55)) and last_alert_state[moneda] != 'long':
                    tipo = "LONG (Reversión)" if rsi < 30 else "LONG (Tendencia)"
                    sl = precio_actual * (1 - SL_PERCENT)
                    tp = precio_actual * (1 + TP_PERCENT)
                    
                    msg = (f"🔵 *ALERTA DE {tipo}*\n"
                           f"💰 Moneda: {moneda}\n"
                           f"📈 RSI: {rsi:.2f} | EMA 200: ${ema:,.2f}\n"
                           f"💵 *Entrada:* ${precio_actual:,.2f}\n"
                           f"🚫 *SL:* ${sl:,.2f} | 🎯 *TP:* ${tp:,.2f}")
                    enviar_telegram(msg)
                    last_alert_state[moneda] = 'long'

                # VENTA (SHORT): Solo si el precio está por debajo de la EMA 200 (tendencia bajista)
                elif rsi > 70 and not es_alcista and last_alert_state[moneda] != 'short':
                    sl = precio_actual * (1 + SL_PERCENT)
                    tp = precio_actual * (1 - TP_PERCENT)
                    
                    msg = (f"🔴 *AVISO DE SHORT*\n"
                           f"💰 Moneda: {moneda}\n"
                           f"📉 RSI: {rsi:.2f} | EMA 200: ${ema:,.2f}\n"
                           f"💵 *Entrada:* ${precio_actual:,.2f}\n"
                           f"🚫 *SL:* ${sl:,.2f} | 🎯 *TP:* ${tp:,.2f}")
                    enviar_telegram(msg)
                    last_alert_state[moneda] = 'short'
                
                # Resetear para permitir nuevas alertas
                elif 40 < rsi < 50:
                    last_alert_state[moneda] = None
            
            time.sleep(60) # Espera 1 minuto entre revisiones
        except Exception as e:
            print(f"Error: {e}", flush=True)
            time.sleep(10)

if __name__ == "__main__":
    t = threading.Thread(target=trading_loop)
    t.daemon = True
    t.start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
