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

# --- 🔑 UPDATED TOKEN ---
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

# --- 📊 LIVE METRICS ---
WORKING_PROXIES = []
SCANNED_POOL_SIZE = 0
TOTAL_TESTED_THIS_CYCLE = 0

main_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="🎵 Create Music"), KeyboardButton(text="📊 My Stats")],
    [KeyboardButton(text="⚙️ Help")]
], resize_keyboard=True)

# --- ⚡ HYPER-SPEED PROXY ENGINE ---
async def check_proxy_task(p_url):
    try:
        scraper = cloudscraper.create_scraper()
        res = await asyncio.to_thread(scraper.get, "https://notegpt.io", timeout=4)
        if res.status_code < 500:
            return p_url
    except: pass
    return None

async def proxy_engine():
    global WORKING_PROXIES, SCANNED_POOL_SIZE, TOTAL_TESTED_THIS_CYCLE
    while True:
        temp_pool = set()
        sources = [
            "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
            "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http",
            "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt"
        ]
        
        try: # Supabase
            r = requests.get(SUPABASE_URL, headers=SUPABASE_HEADERS, timeout=10)
            if r.status_code == 200:
                data = r.json()
                for p in (data if isinstance(data, list) else data.get('proxies', [])):
                    if p.get('ip'): temp_pool.add(f"http://{p['ip']}:{p['port']}")
        except: pass

        for s in sources:
            try:
                r = requests.get(s, timeout=5)
                for l in r.text.splitlines():
                    if ":" in l: temp_pool.add(f"http://{l.strip()}")
            except: pass

        SCANNED_POOL_SIZE = len(temp_pool)
        if temp_pool:
            test_list = random.sample(list(temp_pool), min(len(temp_pool), 600))
            TOTAL_TESTED_THIS_CYCLE = len(test_list)
            tasks = [check_proxy_task(p) for p in test_list]
            results = await asyncio.gather(*tasks)
            WORKING_PROXIES = [r for r in results if r]
        
        gc.collect()
        await asyncio.sleep(120)

def get_progress_bar(percent):
    done = int(percent / 10)
    return f"[{'▬' * done}{'  ' * (10 - done)}] {percent}%"

# --- 🎮 HANDLERS ---
@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    await message.answer("🎼 **NOTEGPT BEAST v18.5**\n\nNaya token active hai! Engine ready hai, music generate karein.", reply_markup=main_kb)

@dp.message(F.text == "📊 My Stats")
async def cmd_stats(message: types.Message):
    status = "🟢 ACTIVE" if WORKING_PROXIES else "🟡 SCANNING"
    msg = (
        f"🛡️ **System Status:** `{status}`\n"
        f"🔍 Pool Size: `{SCANNED_POOL_SIZE}`\n"
        f"🧪 Tested This Cycle: `{TOTAL_TESTED_THIS_CYCLE}`\n"
        f"✅ Working Elite: `{len(WORKING_PROXIES)}` 🔥"
    )
    await message.answer(msg)

@dp.message(F.text)
async def handle_music(message: types.Message):
    if message.text in ["🎵 Create Music", "📊 My Stats", "⚙️ Help"]:
        if message.text == "🎵 Create Music": await message.answer("Bhai, apna topic bhejo!")
        return

    if not WORKING_PROXIES:
        await message.answer("⏳ **Warming up Engine...** Proxy scan chal raha hai.")
        return

    msg = await message.answer(f"🚀 **Bypassing NoteGPT...**\n{get_progress_bar(10)}")
    
    # 3-Attempt Auto-Retry Logic
    for attempt in range(3):
        proxy = random.choice(WORKING_PROXIES)
        scraper = cloudscraper.create_scraper()
        scraper.proxies = {"http": proxy, "https": proxy}
        
        try:
            res = await asyncio.to_thread(scraper.post, "https://notegpt.io/api/v2/music/generate", 
                                          json={"prompt": message.text, "lyrics": "", "duration": 0}, timeout=20)
            data = res.json()
            if data.get("code") == 100000:
                cid = data["data"]["conversation_id"]
                await message.answer(f"📝 **Lyrics:**\n\n{data['data'].get('lyrics')}")
                
                for i in range(2, 12):
                    prog = min(i * 9, 99)
                    await msg.edit_text(f"🎼 **AI Studio Composing...**\n{get_progress_bar(prog)}")
                    await asyncio.sleep(8)
                    status_res = await asyncio.to_thread(scraper.get, f"https://notegpt.io/api/v2/music/status?conversation_id={cid}")
                    s_data = status_res.json().get("data", {})
                    if s_data.get("status") == "success":
                        audio = await asyncio.to_thread(scraper.get, s_data.get("music_url"))
                        await message.answer_audio(BufferedInputFile(audio.content, "song.mp3"), caption="🔥 Done!")
                        await msg.delete(); return
                break
        except: continue
    
    await msg.edit_text("❌ Sabhi attempts fail huye. Try again with a different prompt.")

async def main():
    asyncio.create_task(proxy_engine())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
