import ccxt
import time
import os
import threading
import requests
import pandas as pd
from flask import Flask

# Configuración de la aplicación Web para Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot de Trading Rocío (Bybit + EMA 200) Activo 🚀"

# Variables de entorno (Ya configuradas en tu Render)
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# --- CONFIGURACIÓN DE ESTRATEGIA ---
SL_PERCENT = 0.015  # Stop Loss 1.5%
TP_PERCENT = 0.03   # Take Profit 3.0%
EMA_TENDENCIA = 200 

# Memoria para evitar alertas repetitivas
last_alert_state = {'BTC/USDT': None, 'ETH/USDT': None, 'SOL/USDT': None, 'ZEC/USDT': None, 'XRP/USDT': None}

def enviar_telegram(mensaje):
    if TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
        try:
            response = requests.post(url, json=payload)
            if response.status_code != 200:
                print(f"Error Telegram: {response.text}")
        except Exception as e:
            print(f"Error conexión Telegram: {e}")

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
    
    # EMA 200
    df['ema'] = df['close'].ewm(span=periodo_ema, adjust=False).mean()
    
    return df['rsi'].iloc[-1], df['ema'].iloc[-1]

def trading_loop():
    print("Iniciando análisis con Filtro de Tendencia en Bybit...", flush=True)
    enviar_telegram("✅ *Bot Rocío Actualizado*\n\nConexión establecida vía *Bybit* para evitar bloqueos regionales.\nEstrategia: EMA 200 + RSI activa.")
    
    # CAMBIO CLAVE: Usamos Bybit para evitar el error 451 de Binance en USA
    exchange = ccxt.bybit({'options': {'defaultType': 'linear'}})
    
    watchlist = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ZEC/USDT', 'XRP/USDT']

    while True:
        try:
            for moneda in watchlist:
                # Obtenemos velas de Bybit
                bars = exchange.fetch_ohlcv(moneda, timeframe='5m', limit=300)
                precios = [b[4] for b in bars]
                precio_actual = precios[-1]
                
                rsi, ema = calcular_indicadores(precios)
                es_alcista = precio_actual > ema
                
                print(f"{moneda}: ${precio_actual} | RSI {rsi:.2f} | EMA {ema:.2f}", flush=True)

                # --- LÓGICA DE ESTRATEGIA ---

                # LONG: Sobreventa o tendencia fuerte
                if (rsi < 30 or (es_alcista and rsi > 55)) and last_alert_state[moneda] != 'long':
                    tipo = "LONG (Reversión)" if rsi < 30 else "LONG (Tendencia)"
                    sl = precio_actual * (1 - SL_PERCENT)
                    tp = precio_actual * (1 + TP_PERCENT)
                    
                    msg = (f"🔵 *ALERTA DE {tipo}*\n"
                           f"💰 Moneda: {moneda}\n"
                           f"📊 RSI: {rsi:.2f} | EMA 200: ${ema:,.2f}\n"
                           f"💵 *Entrada:* ${precio_actual:,.2f}\n"
                           f"🚫 *SL:* ${sl:,.2f} | 🎯 *TP:* ${tp:,.2f}")
                    enviar_telegram(msg)
                    last_alert_state[moneda] = 'long'

                # SHORT: Solo si el precio está por DEBAJO de la EMA 200
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
                
                # Resetear memoria
                elif 42 < rsi < 48:
                    last_alert_state[moneda] = None
            
            time.sleep(60)
        except Exception as e:
            print(f"Error en el ciclo: {e}", flush=True)
            time.sleep(10)

if __name__ == "__main__":
    # Hilo para el bot de trading
    t = threading.Thread(target=trading_loop)
    t.daemon = True
    t.start()
    
    # Iniciar servidor Flask para que Render/Cron-job lo vean activo
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
