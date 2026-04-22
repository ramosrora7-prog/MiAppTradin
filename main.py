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
    return "Bot Rocío Híbrido (Mejorado - Entradas Certeras) Activo 🚀"

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# --- CONFIGURACIÓN DE SCALPING RÁPIDO ---
SL_PERCENT = 0.008  # Stop Loss (0.8%)
TP_PERCENT = 0.012  # Take Profit (1.2%)

# Diccionario para rastrear el estado y el RSI anterior
last_alert_state = {'BTC/USDT': None, 'ETH/USDT': None, 'SOL/USDT': None, 'ZEC/USDT': None, 'XRP/USDT': None}
last_rsi_value = {'BTC/USDT': 50.0, 'ETH/USDT': 50.0, 'SOL/USDT': 50.0, 'ZEC/USDT': 50.0, 'XRP/USDT': 50.0}

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
    print("Bot Híbrido Iniciado con Filtro de Giro...", flush=True)
    enviar_telegram("⚡ *Bot Rocío Modo Guerrero V2*\nFiltro de confirmación activado para evitar caídas falsas.")
    
    exchange = ccxt.mexc() # O el exchange que prefieras
    watchlist = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ZEC/USDT', 'XRP/USDT']

    while True:
        try:
            for moneda in watchlist:
                bars = exchange.fetch_ohlcv(moneda, timeframe='5m', limit=250)
                precios = [b[4] for b in bars]
                precio_actual = precios[-1]
                rsi_actual, ema = calcular_indicadores(precios)
                
                # Recuperamos el RSI de la vuelta anterior para comparar
                rsi_previo = last_rsi_value[moneda]
                es_alcista = precio_actual > ema

                # --- MEJORA: LÓGICA DE CONFIRMACIÓN DE GIRO ---
                
                # LONG: RSI estaba abajo ( < 35) Y AHORA está subiendo
                if rsi_actual < 35 and rsi_actual > rsi_previo and last_alert_state[moneda] != 'long':
                    contexto = "✅ REBOTE CONFIRMADO" if es_alcista else "⚠️ REBOTE (Contra tendencia)"
                    sl = precio_actual * (1 - SL_PERCENT)
                    tp = precio_actual * (1 + TP_PERCENT)
                    
                    msg = (f"🔵 *¡SEÑAL DE COMPRA!* ({moneda})\n"
                           f"━━━━━━━━━━━━━━━\n"
                           f"📢 *Confirmación:* RSI girando al alza ({rsi_previo:.1f} ➔ {rsi_actual:.1f})\n"
                           f"💵 *Entrada:* ${precio_actual:,.4f}\n"
                           f"🎯 *TP:* ${tp:,.4f} | 🛑 *SL:* ${sl:,.4f}")
                    enviar_telegram(msg)
                    last_alert_state[moneda] = 'long'

                # SHORT: RSI estaba arriba ( > 65) Y AHORA está bajando
                elif rsi_actual > 65 and rsi_actual < rsi_previo and last_alert_state[moneda] != 'short':
                    contexto = "✅ CAÍDA CONFIRMADA" if not es_alcista else "⚠️ CAÍDA (Contra tendencia)"
                    sl = precio_actual * (1 + SL_PERCENT)
                    tp = precio_actual * (1 - TP_PERCENT)
                    
                    msg = (f"🔴 *¡SEÑAL DE VENTA!* ({moneda})\n"
                           f"━━━━━━━━━━━━━━━\n"
                           f"📢 *Confirmación:* RSI girando a la baja ({rsi_previo:.1f} ➔ {rsi_actual:.1f})\n"
                           f"💵 *Entrada:* ${precio_actual:,.4f}\n"
                           f"🎯 *TP:* ${tp:,.4f} | 🛑 *SL:* ${sl:,.4f}")
                    enviar_telegram(msg)
                    last_alert_state[moneda] = 'short'
                
                # Resetear alertas cuando el RSI vuelve a zona neutral
                elif 45 < rsi_actual < 55:
                    last_alert_state[moneda] = None
                
                # Guardar el RSI actual para la próxima comparación
                last_rsi_value[moneda] = rsi_actual
            
            time.sleep(60)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    t = threading.Thread(target=trading_loop)
    t.daemon = True
    t.start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
                         
