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

# --- 🔑 FULL CREDENTIALS ---
API_TOKEN = '8540275734:AAHmEYYBLvaHt8VonUBqTyI5eu6o8-ROlQI'
ADMIN_ID = 7840042951

SUPABASE_URL = "https://vwmhbpgwhfwuwtattset.supabase.co/functions/v1/fetch-proxies"
SUPABASE_HEADERS = {
    "Authorization": "Bearer eyJhbGciOiJFUzI1NiIsImtpZCI6ImYyZTIyZWFhLTRhYjQtNDZhOC1hYzM3LTExYzA3YWQyNTgzNCIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL3Z3bWhicGd3aGZ3dXd0YXR0c2V0LnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI1ZmM0NTA3ZS00NTI2LTQ2OGItYjFkMi01YmVlOTZkNmQwMTEiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY3NDA0Nzg0LCJpYXQiOjE3Njc0MDExODQsImVtYWlsIjoiamhvbmRlb0BnbWFpbC5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7ImVtYWlsIjoiamhvbmRlb0BnbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiZnVsbF9uYW1lIjoiSm9obiBkb2UiLCJwaG9uZV92ZXJpZmllZCI6ZmFsc2UsInN1YiI6IjVmYzQ1MDdlLTQ1MjYtNDY4Yi1iMWQyLTViZWU5NmQ2ZDAxMSJ9LCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImFhbCI6ImFhbDEiLCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzY3NDA0Nzg0fV0sInNlc3Npb25faWQiOiI4MzkzYWU2Zi0zYTJlLTQ0ZDUtYjg1ZS1lYWEwMzQwNDdhYWEiLCJpc19hbm9ueW1vdXMiOmZhbHNlfQ.ijYObw_fffHDtEIw3PPKqDyDW6StUn3NkaofNcfTakA5KMCwuzmW6UQq2_mSxfu5PHejh1xUNLQWQCH6weidjQ",
    "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ3bWhicGd3aGZ3dXd0YXR0c2V0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjczMjc0NjYsImV4cCI6MjA4MjkwMzQ2Nn0.LSMD2P4whDzoIW4UCig0ly0j6UOxd5fHhIkUhywnmrg",
    "Content-Type": "application/json"
}

# --- 🛰️ MASSIVE PROXY SOURCES ---
PROXY_SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt",
    "https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/master/http.txt",
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000"
]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# STATE
WORKING_PROXIES = []
SCANNED_TOTAL = 0
LAST_REFRESH = "Never"

# UI
main_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="🎵 Create Music"), KeyboardButton(text="📊 My Stats")],
    [KeyboardButton(text="⚙️ Help")]
], resize_keyboard=True)

# --- 🚀 ULTRA AGGRESSIVE ENGINE ---

async def test_proxy_aggressive(p_url):
    """Deep check for NoteGPT SSL Bypass"""
    try:
        scraper = cloudscraper.create_scraper()
        scraper.proxies = {"http": p_url, "https": p_url}
        # Testing against API endpoint directly is faster and more accurate
        res = await asyncio.to_thread(scraper.get, "https://notegpt.io/api/v2/music/generate", timeout=4)
        # NoteGPT returns 405 for GET on API, which means it's ALIVE!
        if res.status_code in [200, 405]:
            return p_url
    except:
        pass
    return None

async def refresh_engine():
    global WORKING_PROXIES, SCANNED_TOTAL, LAST_REFRESH
    while True:
        temp_pool = set()
        
        # 1. Fetch Supabase (Elite Source)
        try:
            res = requests.get(SUPABASE_URL, headers=SUPABASE_HEADERS, timeout=10)
            if res.status_code == 200:
                data = res.json()
                for p in (data if isinstance(data, list) else data.get('proxies', [])):
                    if p.get('ip'): temp_pool.add(f"http://{p['ip']}:{p['port']}")
        except: pass

        # 2. Fetch Massive GitHub Sources
        for src in PROXY_SOURCES:
            try:
                r = requests.get(src, timeout=5)
                if r.status_code == 200:
                    for line in r.text.splitlines():
                        if ":" in line: temp_pool.add(f"http://{line.strip()}")
            except: pass

        SCANNED_TOTAL = len(temp_pool)
        
        # 3. Ultra Parallel Testing (High Load but Fast)
        if temp_pool:
            # Check 500 at a time
            test_list = random.sample(list(temp_pool), min(len(temp_pool), 500))
            tasks = [test_proxy_aggressive(p) for p in test_list]
            results = await asyncio.gather(*tasks)
            new_verified = [r for r in results if r]
            
            # Save only the freshest 30 working proxies
            WORKING_PROXIES = list(set(new_verified))[:30]
            if WORKING_PROXIES:
                LAST_REFRESH = time.strftime("%H:%M:%S")

        gc.collect()
        await asyncio.sleep(180) # Refresh every 3 mins

def get_progress_bar(percent):
    done = int(percent / 10)
    return f"[{'▬' * done}{'  ' * (10 - done)}] {percent}%"

# --- 🎮 HANDLERS ---

@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    await message.answer("🔥 **NOTEGPT GOD MODE v16.0** 🔥\n\nBhai, bot ab 500 proxies ek saath scan kar raha hai. Unlimited music bypass ON hai!", reply_markup=main_kb)

@dp.message(F.text == "📊 My Stats")
async def cmd_stats(message: types.Message):
    status = "🟢 FIRE" if WORKING_PROXIES else "🔴 SCANNING"
    await message.answer(
        f"🛡️ **System Status:** `{status}`\n"
        f"🔍 IPs Scanned: `{SCANNED_TOTAL}`\n"
        f"✅ Live Elite: `{len(WORKING_PROXIES)}` 🔥\n"
        f"🕒 Last Update: `{LAST_REFRESH}`"
    )

@dp.message(F.text == "🎵 Create Music")
async def request_music(message: types.Message):
    await message.answer("✍️ **Bhai, music topic bhejo!** (v16.0 Ultra Speed)")

@dp.message(F.text)
async def handle_logic(message: types.Message):
    if message.text in ["🎵 Create Music", "📊 My Stats", "⚙️ Help"]: return
    
    if not WORKING_PROXIES:
        await message.answer(f"⏳ **Aggressive Scan in Progress...**\nChecked `{SCANNED_TOTAL}` proxies. 20s ruko.")
        return

    topic = message.text
    msg = await message.answer(f"🚀 **Powering up Elite Proxy...**\n{get_progress_bar(10)}")
    
    # Selection
    proxy = random.choice(WORKING_PROXIES)
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'android'})
    scraper.proxies = {"http": proxy, "https": proxy}
    
    try:
        await asyncio.to_thread(scraper.get, "https://notegpt.io/ai-music-generator")
        cookies = scraper.cookies.get_dict()
        cookies['anonymous_user_id'] = f"anon_{uuid.uuid4().hex}"
        
        payload = {"prompt": f"Mastered quality {topic}", "lyrics": "", "duration": 0}
        headers = {'User-Agent': 'Mozilla/5.0...', 'X-Requested-With': 'XMLHttpRequest'}
        
        res = await asyncio.to_thread(scraper.post, "https://notegpt.io/api/v2/music/generate", json=payload, cookies=cookies, headers=headers)
        data = res.json()
        
        if data.get("code") == 100000:
            cid = data["data"]["conversation_id"]
            lyrics = data["data"].get("lyrics", "Generating...")
            
            # 📝 Instant Lyrics
            await message.answer(f"📝 **Lyrics Generated:**\n\n{lyrics}")
            
            # 🎼 Polling
            for i in range(2, 12):
                prog = min(i * 9, 99)
                await msg.edit_text(f"🎼 **Composing v16.0 Beast Mode...**\n{get_progress_bar(prog)}")
                await asyncio.sleep(8)
                
                status_res = await asyncio.to_thread(scraper.get, f"https://notegpt.io/api/v2/music/status?conversation_id={cid}", cookies=cookies)
                s_data = status_res.json().get("data", {})
                
                if s_data.get("status") == "success":
                    await msg.edit_text(f"📥 **Downloading Masterpiece...**\n{get_progress_bar(100)}")
                    audio = await asyncio.to_thread(scraper.get, s_data.get("music_url"))
                    await message.answer_audio(
                        audio=BufferedInputFile(audio.content, filename=f"Fire.mp3"),
                        caption=f"🔥 **Topic:** {topic}\n⚡ NoteGPT Beast Mode Bypass"
                    )
                    await msg.delete(); return
        else:
            await msg.edit_text(f"❌ Error: {data.get('message')}")
    except Exception:
        await msg.edit_text("⚠️ Connection lost. Retrying with naya proxy...")
    finally: gc.collect()

async def main():
    asyncio.create_task(refresh_engine())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
