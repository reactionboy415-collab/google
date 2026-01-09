import logging
import asyncio
import time
import random
import uuid
import cloudscraper
import requests
import gc
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BufferedInputFile, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# --- 🔑 CREDENTIALS ---
API_TOKEN = '8540275734:AAHlcAsFnCUfkQEIyCjkxW3Gn6bOeo6ZD-w'
ADMIN_ID = 7840042951

SUPABASE_URL = "https://vwmhbpgwhfwuwtattset.supabase.co/functions/v1/fetch-proxies"
SUPABASE_HEADERS = {
    "Authorization": "Bearer eyJhbGciOiJFUzI1NiIsImtpZCI6ImYyZTIyZWFhLTRhYjQtNDZhOC1hYzM3LTExYzA3YWQyNTgzNCIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL3Z3bWhicGd3aGZ3dXd0YXR0c2V0LnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI1ZmM0NTA3ZS00NTI2LTQ2OGItYjFkMi01YmVlOTZkNmQwMTEiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY3NDA0Nzg0LCJpYXQiOjE3Njc0MDExODQsImVtYWlsIjoiamhvbmRlb0BnbWFpbC5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7ImVtYWlsIjoiamhvbmRlb0BnbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiZnVsbF9uYW1lIjoiSm9obiBkb2UiLCJwaG9uZV92ZXJpZmllZCI6ZmFsc2UsInN1YiI6IjVmYzQ1MDdlLTQ1MjYtNDY4Yi1iMWQyLTViZWU5NmQ2ZDAxMSJ9LCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImFhbCI6ImFhbDEiLCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzY3NDA0Nzg0fV0sInNlc3Npb25faWQiOiI4MzkzYWU2Zi0zYTJlLTQ0ZDUtYjg1ZS1lYWEwMzQwNDdhYWEiLCJpc19hbm9ueW1vdXMiOmZhbHNlfQ.ijYObw_fffHDtEIw3PPKqDyDW6StUn3NkaofNcfTakA5KMCwuzmW6UQq2_mSxfu5PHejh1xUNLQWQCH6weidjQ",
    "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ3bWhicGd3aGZ3dXd0YXR0c2V0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjczMjc0NjYsImV4cCI6MjA4MjkwMzQ2Nn0.LSMD2P4whDzoIW4UCig0ly0j6UOxd5fHhIkUhywnmrg",
    "Content-Type": "application/json"
}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- 📊 LIVE STATE ---
WORKING_PROXIES = []
SCANNED_POOL = 0
TESTED_LAST = 0

# --- ⌨️ KEYBOARDS ---
def get_main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🎵 Create Music"), KeyboardButton(text="📊 My Stats")],
        [KeyboardButton(text="⚙️ Help")]
    ], resize_keyboard=True)

# --- 🚀 PROXY ENGINE ---
async def check_proxy(p_url):
    try:
        scraper = cloudscraper.create_scraper()
        res = await asyncio.to_thread(scraper.get, "https://notegpt.io", timeout=4)
        if res.status_code < 500: return p_url
    except: pass
    return None

async def refresh_loop():
    global WORKING_PROXIES, SCANNED_POOL, TESTED_LAST
    while True:
        pool = set()
        # Fetching sources...
        try:
            r = requests.get(SUPABASE_URL, headers=SUPABASE_HEADERS, timeout=10)
            if r.status_code == 200:
                for p in r.json(): pool.add(f"http://{p['ip']}:{p['port']}")
        except: pass
        
        sources = ["https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt", "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http"]
        for s in sources:
            try:
                lines = requests.get(s, timeout=5).text.splitlines()
                for l in lines: 
                    if ":" in l: pool.add(f"http://{l.strip()}")
            except: pass

        SCANNED_POOL = len(pool)
        if pool:
            sample = random.sample(list(pool), min(len(pool), 500))
            TESTED_LAST = len(sample)
            tasks = [check_proxy(p) for p in sample]
            results = await asyncio.gather(*tasks)
            WORKING_PROXIES = [r for r in results if r]
        
        gc.collect()
        await asyncio.sleep(120)

# --- 🎮 HANDLERS ---
@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    await message.answer(
        "🔱 **NOTEGPT MASTERPIECE v19.0**\n\nBhai, buttons fix kar diye hain. Niche keyboard use karein 👇",
        reply_markup=get_main_kb()
    )

@dp.message(F.text == "📊 My Stats")
async def cmd_stats(message: types.Message):
    status = "🟢 FIRE" if WORKING_PROXIES else "🟡 SCANNING"
    await message.answer(
        f"🛡️ **System Status:** `{status}`\n"
        f"🔍 Pool: `{SCANNED_POOL}`\n"
        f"🧪 Tested: `{TESTED_LAST}`\n"
        f"✅ Live: `{len(WORKING_PROXIES)}`",
        reply_markup=get_main_kb()
    )

@dp.message(F.text == "🎵 Create Music")
async def cmd_create(message: types.Message):
    await message.answer("✍️ **Bhai, music topic bhejo!**\nExample: *Sad Hindi Song*", reply_markup=get_main_kb())

@dp.message(F.text == "⚙️ Help")
async def cmd_help(message: types.Message):
    await message.answer("Bhai simple hai: Topic bhejo -> Lyrics lo -> Music ka wait karo!", reply_markup=get_main_kb())

@dp.message()
async def handle_all(message: types.Message):
    # Ignore keyboard commands if they somehow fall through
    if message.text in ["🎵 Create Music", "📊 My Stats", "⚙️ Help"]: return

    if not WORKING_PROXIES:
        await message.answer("⏳ **Proxy check chal raha hai...** 10-15s ruko.")
        return

    topic = message.text
    status_msg = await message.answer("🚀 **Processing Request...**")
    
    # Bypass Logic...
    proxy = random.choice(WORKING_PROXIES)
    scraper = cloudscraper.create_scraper()
    scraper.proxies = {"http": proxy, "https": proxy}
    
    try:
        res = await asyncio.to_thread(scraper.post, "https://notegpt.io/api/v2/music/generate", 
                                      json={"prompt": topic, "lyrics": "", "duration": 0}, timeout=20)
        data = res.json()
        if data.get("code") == 100000:
            cid = data["data"]["conversation_id"]
            await message.answer(f"📝 **Lyrics:**\n\n{data['data'].get('lyrics')}")
            
            # Polling Logic
            for i in range(12):
                await asyncio.sleep(8)
                s_res = await asyncio.to_thread(scraper.get, f"https://notegpt.io/api/v2/music/status?conversation_id={cid}")
                s_data = s_res.json().get("data", {})
                if s_data.get("status") == "success":
                    audio = await asyncio.to_thread(scraper.get, s_data.get("music_url"))
                    await message.answer_audio(BufferedInputFile(audio.content, "music.mp3"), caption=f"✅ Done: {topic}")
                    await status_msg.delete(); return
        else:
            await status_msg.edit_text(f"❌ API Error: {data.get('message')}")
    except:
        await status_msg.edit_text("⚠️ Retry karo bhai!")

async def main():
    asyncio.create_task(refresh_loop())
    # skip_updates=True purane atke huye button clicks ko clear kar dega
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
