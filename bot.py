import logging
import asyncio
import time
import random
import uuid
import cloudscraper
import requests
import gc
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BufferedInputFile, ReplyKeyboardMarkup, KeyboardButton

# --- 🔑 UPDATED CREDENTIALS ---
API_TOKEN = '8540275734:AAHmEYYBLvaHt8VonUBqTyI5eu6o8-ROlQI'
ADMIN_ID = 7840042951

SUPABASE_URL = "https://vwmhbpgwhfwuwtattset.supabase.co/functions/v1/fetch-proxies"
SUPABASE_HEADERS = {
    "Authorization": "Bearer eyJhbGciOiJFUzI1NiIsImtpZCI6ImYyZTIyZWFhLTRhYjQtNDZhOC1hYzM3LTExYzA3YWQyNTgzNCIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL3Z3bWhicGd3aGZ3dXd0YXR0c2V0LnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI1ZmM0NTA3ZS00NTI2LTQ2OGItYjFkMi01YmVlOTZkNmQwMTEiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY3NDA0Nzg0LCJpYXQiOjE3Njc0MDExODQsImVtYWlsIjoiamhvbmRlb0BnbWFpbC5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7ImVtYWlsIjoiamhvbmRlb0BnbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiZnVsbF9uYW1lIjoiSm9obiBkb2UiLCJwaG9uZV92ZXJpZmllZCI6ZmFsc2UsInN1YiI6IjVmYzQ1MDdlLTQ1MjYtNDY4Yi1iMWQyLTViZWU5NmQ2ZDAxMSJ9LCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImFhbCI6ImFhbDEiLCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzY3NDA0Nzg0fV0sInNlc3Npb25faWQiOiI4MzkzYWU2Zi0zYTJlLTQ0ZDUtYjg1ZS1lYWEwMzQwNDdhYWEiLCJpc19hbm9ueW1vdXMiOmZhbHNlfQ.ijYObw_fffHDtEIw3PPKqDyDW6StUn3NkaofNcfTakA5KMCwuzmW6UQq2_mSxfu5PHejh1xUNLQWQCH6weidjQ",
    "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ3bWhicGd3aGZ3dXd0YXR0c2V0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjczMjc0NjYsImV4cCI6MjA4MjkwMzQ2Nn0.LSMD2P4whDzoIW4UCig0ly0j6UOxd5fHhIkUhywnmrg",
    "Content-Type": "application/json"
}

PROXY_SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=5000"
]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- STATE ---
WORKING_PROXIES = []
SCANNED_TOTAL = 0

main_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="🎵 Create Music"), KeyboardButton(text="📊 My Stats")],
    [KeyboardButton(text="⚙️ Help")]
], resize_keyboard=True)

# --- 🚀 PROXY LOGIC ---
async def test_proxy(p_url):
    try:
        scraper = cloudscraper.create_scraper()
        scraper.proxies = {"http": p_url, "https": p_url}
        res = await asyncio.to_thread(scraper.get, "https://notegpt.io/api/v2/music/generate", timeout=3)
        if res.status_code in [200, 405]: return p_url
    except: pass
    return None

async def refresh_engine():
    global WORKING_PROXIES, SCANNED_TOTAL
    while True:
        temp_pool = set()
        try:
            res = requests.get(SUPABASE_URL, headers=SUPABASE_HEADERS, timeout=10)
            if res.status_code == 200:
                data = res.json()
                for p in (data if isinstance(data, list) else data.get('proxies', [])):
                    if p.get('ip'): temp_pool.add(f"http://{p['ip']}:{p['port']}")
        except: pass
        for src in PROXY_SOURCES:
            try:
                r = requests.get(src, timeout=5)
                for line in r.text.splitlines():
                    if ":" in line: temp_pool.add(f"http://{line.strip()}")
            except: pass
        SCANNED_TOTAL = len(temp_pool)
        if temp_pool:
            sample = random.sample(list(temp_pool), min(len(temp_pool), 200)) # Ultra aggressive test
            tasks = [test_proxy(p) for p in sample]
            results = await asyncio.gather(*tasks)
            WORKING_PROXIES = [r for r in results if r][:30]
        gc.collect()
        await asyncio.sleep(200)

# --- 🎮 HANDLERS ---
@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    await message.answer("🔥 **NOTEGPT BEAST IS ALIVE!** 🔥\n\nBhai, bot start ho gaya hai. Music ke liye button dabao!", reply_markup=main_kb)

@dp.message(F.text == "📊 My Stats")
async def cmd_stats(message: types.Message):
    await message.answer(f"🛡️ Status: `🟢 Active`\n🔍 Scanned: `{SCANNED_TOTAL}`\n✅ Live: `{len(WORKING_PROXIES)}`")

@dp.message(F.text == "🎵 Create Music")
async def ask_topic(message: types.Message):
    await message.answer("✍️ **Apna topic bhejo bhai!**")

@dp.message(F.text)
async def handle_music(message: types.Message):
    if message.text in ["🎵 Create Music", "📊 My Stats", "⚙️ Help"]: return
    if not WORKING_PROXIES:
        await message.answer("⌛ Proxy scan chal raha hai, 15s ruko.")
        return
    
    msg = await message.answer("🚀 **Processing...**")
    proxy = random.choice(WORKING_PROXIES)
    scraper = cloudscraper.create_scraper()
    scraper.proxies = {"http": proxy, "https": proxy}
    
    try:
        # NoteGPT logic same as before...
        res = await asyncio.to_thread(scraper.post, "https://notegpt.io/api/v2/music/generate", 
                                      json={"prompt": message.text, "lyrics": "", "duration": 0}, timeout=15)
        data = res.json()
        if data.get("code") == 100000:
            cid = data["data"]["conversation_id"]
            await message.answer(f"📝 **Lyrics:**\n\n{data['data'].get('lyrics')}")
            # Polling and Delivery...
            await msg.edit_text("🎼 Composing...")
            await asyncio.sleep(20) # Simulating wait for now
            status_res = await asyncio.to_thread(scraper.get, f"https://notegpt.io/api/v2/music/status?conversation_id={cid}")
            s_url = status_res.json()["data"]["music_url"]
            audio = await asyncio.to_thread(scraper.get, s_url)
            await message.answer_audio(BufferedInputFile(audio.content, "song.mp3"), caption="Done! 🔥")
    except:
        await msg.edit_text("⚠️ Retry karo bhai!")

# --- 🛠️ STARTUP NOTIFICATION ---
async def on_startup():
    try:
        await bot.send_message(ADMIN_ID, "✅ **Bot is now Online & Polling!**\nAb /start karke check karo.")
    except: pass

async def main():
    asyncio.create_task(refresh_engine())
    await on_startup() # Send notification on start
    await dp.start_polling(bot, skip_updates=True) # skip_updates cleans old commands

if __name__ == "__main__":
    asyncio.run(main())
