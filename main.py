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
    return "Bot Rocío V3 (Filtro de Tendencia Profesional) Activo 🚀"

# --- CONFIGURACIÓN ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

SL_PERCENT = 0.008  # Stop Loss (0.8%)
TP_PERCENT = 0.012  # Take Profit (1.2%)

# Diccionarios de seguimiento
last_alert_state = {'BTC/USDT': None, 'ETH/USDT': None, 'SOL/USDT': None, 'ZEC/USDT': None, 'XRP/USDT': None}
last_rsi_value = {'BTC/USDT': 50.0, 'ETH/USDT': 50.0, 'SOL/USDT': 50.0, 'ZEC/USDT': 50.0, 'XRP/USDT': 50.0}

def enviar_telegram(mensaje):
    if TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload)
        except:
            pass

def calcular_indicadores(precios):
    df = pd.DataFrame(precios, columns=['close'])
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0))
    loss = (-delta.where(delta < 0, 0))
    avg_gain = gain.ewm(alpha=1/14, min_periods=14).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    # EMA 200 para tendencia
    ema = df['close'].ewm(span=200, adjust=False).mean()
    return rsi.iloc[-1], ema.iloc[-1]

def trading_loop():
    print("Bot V3 Iniciado...", flush=True)
    enviar_telegram("🎯 *Bot Rocío V3 Activo*\nAhora solo opero a favor de la tendencia (EMA 200) y con rebotes confirmados.")
    
    # Conexión a MEXC (Puedes cambiar a bingx si prefieres, pero MEXC es muy estable para ccxt)
    exchange = ccxt.mexc()
    watchlist = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ZEC/USDT', 'XRP/USDT']

    while True:
        try:
            for moneda in watchlist:
                # Obtenemos velas de 5 minutos
                bars = exchange.fetch_ohlcv(moneda, timeframe='5m', limit=250)
                precios = [b[4] for b in bars]
                precio_actual = precios[-1]
                
                rsi_actual, ema = calcular_indicadores(precios)
                rsi_previo = last_rsi_value[moneda]
                
                es_alcista = precio_actual > ema
                giro_rsi = rsi_actual - rsi_previo

                # --- LÓGICA DE COMPRA (LONG) ---
                # 1. RSI en sobreventa (< 30)
                # 2. El RSI ya está subiendo (giro > 1.0)
                # 3. El precio está SOBRE la EMA 200 (Tendencia alcista)
                if rsi_actual < 30 and giro_rsi > 1.0 and es_alcista and last_alert_state[moneda] != 'long':
                    sl = precio_actual * (1 - SL_PERCENT)
                    tp = precio_actual * (1 + TP_PERCENT)
                    
                    msg = (f"🔵 *COMPRA (Tendencia Alcista)*\n"
                           f"━━━━━━━━━━━━━━━\n"
                           f"🪙 *Moneda:* {moneda}\n"
                           f"📈 *Giro RSI:* +{giro_rsi:.1f} puntos\n"
                           f"💵 *Entrada:* ${precio_actual:,.4f}\n"
                           f"🎯 *TP:* ${tp:,.4f} | 🛑 *SL:* ${sl:,.4f}")
                    enviar_telegram(msg)
                    last_alert_state[moneda] = 'long'

                # --- LÓGICA DE VENTA (SHORT) ---
                # 1. RSI en sobrecompra (> 70)
                # 2. El RSI ya está bajando (giro < -1.0)
                # 3. El precio está BAJO la EMA 200 (Tendencia bajista)
                elif rsi_actual > 70 and giro_rsi < -1.0 and not es_alcista and last_alert_state[moneda] != 'short':
                    sl = precio_actual * (1 + SL_PERCENT)
                    tp = precio_actual * (1 - TP_PERCENT)
                    
                    msg = (f"🔴 *VENTA (Tendencia Bajista)*\n"
                           f"━━━━━━━━━━━━━━━\n"
                           f"🪙 *Moneda:* {moneda}\n"
                           f"📉 *Giro RSI:* {giro_rsi:.1f} puntos\n"
                           f"💵 *Entrada:* ${precio_actual:,.4f}\n"
                           f"🎯 *TP:* ${tp:,.4f} | 🛑 *SL:* ${sl:,.4f}")
                    enviar_telegram(msg)
                    last_alert_state[moneda] = 'short'
                
                # Resetear estado cuando el RSI vuelve a una zona neutral
                elif 40 < rsi_actual < 60:
                    last_alert_state[moneda] = None
                
                # Guardamos el valor actual para la siguiente comparación
                last_rsi_value[moneda] = rsi_actual
            
            # Esperar 60 segundos para la próxima revisión
            time.sleep(60)
            
        except Exception as e:
            print(f"Error en el loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    # Hilo para el bot de trading
    t = threading.Thread(target=trading_loop)
    t.daemon = True
    t.start()
    
    # Servidor Flask para Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
