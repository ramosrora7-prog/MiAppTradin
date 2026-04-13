import ccxt
import time
import telebot
from flask import Flask
from threading import Thread

# --- SERVIDOR PARA EVITAR QUE RENDER SE DUERMA ---
app = Flask('')
@app.route('/')
def home(): return "Bot de Rocío online 🚀"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# --- CONFIGURACIÓN ---
TOKEN = '8671878451:AAGdKKp87BNWDPjxVPBc8VFJexVEpa8-vQw' 
MI_ID_CHAT = '6800692912' 
bot = telebot.TeleBot(TOKEN)
exchange = ccxt.binance()
watchlist = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']

# Variables fijas para la nube
capital = 100.0
meta_total = 100.0
dias = 5
meta_diaria = meta_total / dias
riesgo_usd = capital * 0.01
palanca = 15

def enviar_mensaje(texto):
    try:
        bot.send_message(MI_ID_CHAT, texto, parse_mode='Markdown')
    except: pass

def calcular_rsi_simple(precios, periodo=14):
    if len(precios) < periodo: return 50
    ganancias = [max(0, precios[i] - precios[i-1]) for i in range(1, len(precios))]
    perdidas = [max(0, precios[i-1] - precios[i]) for i in range(1, len(precios))]
    avg_g = sum(ganancias[-periodo:]) / periodo
    avg_p = sum(perdidas[-periodo:]) / periodo
    if avg_p == 0: return 100
    return 100 - (100 / (1 + (avg_g / avg_p)))

# --- INICIO ---
keep_alive() 
enviar_mensaje(f"🚀 *¡BOT EN LA NUBE ACTIVADO!*\n"
               f"---------------------------\n"
               f"💰 Capital: ${capital}\n"
               f"🎯 Meta Diaria: ${meta_diaria:.2f}\n"
               f"📈 Palanca: {palanca}x")

while True:
    try:
        for moneda in watchlist:
            bars = exchange.fetch_ohlcv(moneda, timeframe='5m', limit=34)
            precios = [b[4] for b in bars]
            precio_actual = precios[-1]
            rsi = calcular_rsi_simple(precios)
            
            tp_long = precio_actual * 1.015
            sl_long = precio_actual * 0.985
            tp_short = precio_actual * 0.985
            sl_short = precio_actual * 1.015
            ganancia_estimada = (riesgo_usd * palanca)

            if rsi < 30:
                aviso = (f"🟢 *AVISO DE COMPRA* ({moneda})\n"
                         f"📈 *Apalancamiento: {palanca}x*\n"
                         f"---------------------------\n"
                         f"📉 RSI: {rsi:.2f}\n"
                         f"💵 Entrada: ${precio_actual:,.2f}\n"
                         f"🚫 *Stop Loss:* ${sl_long:,.2f}\n"
                         f"🎯 *Take Profit:* ${tp_long:,.2f}\n"
                         f"---------------------------\n"
                         f"💰 *Ganancia Estimada:* ${ganancia_estimada:.2f}")
                enviar_mensaje(aviso)
                
            elif rsi > 70:
                aviso = (f"🔴 *AVISO DE VENTA* ({moneda})\n"
                         f"📈 *Apalancamiento: {palanca}x*\n"
                         f"---------------------------\n"
                         f"📈 RSI: {rsi:.2f}\n"
                         f"💵 Entrada: ${precio_actual:,.2f}\n"
                         f"🚫 *Stop Loss:* ${sl_short:,.2f}\n"
                         f"🎯 *Take Profit:* ${tp_short:,.2f}\n"
                         f"---------------------------\n"
                         f"💰 *Ganancia Estimada:* ${ganancia_estimada:.2f}")
                enviar_mensaje(aviso)

        time.sleep(60)
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(10)