import logging
import asyncio
import time
import random
import uuid
import cloudscraper
import requests
import gc
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# --- 🔑 UPDATED CREDENTIALS ---
API_TOKEN = '8540275734:AAHmEYYBLvaHt8VonUBqTyI5eu6o8-ROlQI'
ADMIN_ID = 7840042951

SUPABASE_URL = "https://vwmhbpgwhfwuwtattset.supabase.co/functions/v1/fetch-proxies"
SUPABASE_HEADERS = {
    "Authorization": "Bearer eyJhbGciOiJFUzI1NiIsImtpZCI6ImYyZTIyZWFhLTRhYjQtNDZhOC1hYzM3LTExYzA3YWQyNTgzNCIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL3Z3bWhicGd3aGZ3dXd0YXR0c2V0LnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI1ZmM0NTA3ZS00NTI2LTQ2OGItYjFkMi01YmVlOTZkNmQwMTEiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY3NDA0Nzg0LCJpYXQiOjE3Njc0MDExODQsImVtYWlsIjoiamhvbmRlb0BnbWFpbC5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7ImVtYWlsIjoiamhvbmRlb0BnbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiZnVsbF9uYW1lIjoiSm9obiBkb2UiLCJwaG9uZV92ZXJpZmllZCI6ZmFsc2UsInN1YiI6IjVmYzQ1MDdlLTQ1MjYtNDY4Yi1iMWQyLTViZWU5NmQ2ZDAxMSJ9LCJyb2xlIjoiYXV0aGVudG1jYXRlZCIsImFhbCI6ImFhbDEiLCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzY3NDA0Nzg0fV0sInNlc3Npb25faWQiOiI4MzkzYWU2Zi0zYTJlLTQ0ZDUtYjg1ZS1lYWEwMzQwNDdhYWEiLCJpc19hbm9ueW1vdXMiOmZhbHNlfQ.ijYObw_fffHDtEIw3PPKqDyDW6StUn3NkaofNcfTakA5KMCwuzmW6UQq2_mSxfu5PHejh1xUNLQWQCH6weidjQ",
    "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ3bWhicGd3aGZ3dXd0YXR0c2V0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjczMjc0NjYsImV4cCI6MjA4MjkwMzQ2Nn0.LSMD2P4whDzoIW4UCig0ly0j6UOxd5fHhIkUhywnmrg",
    "Content-Type": "application/json"
}

# --- PROXY POOL ---
PROXY_SOURCES = [
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=3000",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt"
]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

WORKING_PROXIES = []
SCANNED_TOTAL = 0
IS_READY = False

# --- UI COMPONENTS ---
main_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="🎵 Create Music"), KeyboardButton(text="📊 My Stats")],
    [KeyboardButton(text="⚙️ Help")]
], resize_keyboard=True)

# --- ⚡ ENGINE ---
async def test_proxy(p_url):
    try:
        scraper = cloudscraper.create_scraper()
        scraper.proxies = {"http": p_url, "https": p_url}
        res = await asyncio.to_thread(scraper.get, "https://notegpt.io", timeout=2)
        if res.status_code == 200: return p_url
    except: pass
    return None

async def refresh_proxies():
    global WORKING_PROXIES, SCANNED_TOTAL, IS_READY
    while True:
        temp_list = set()
        try:
            res = requests.get(SUPABASE_URL, headers=SUPABASE_HEADERS, timeout=10)
            if res.status_code == 200:
                data = res.json()
                for p in (data if isinstance(data, list) else data.get('proxies', [])):
                    if p.get('ip'): temp_list.add(f"http://{p['ip']}:{p['port']}")
        except: pass
        
        for src in PROXY_SOURCES:
            try:
                r = requests.get(src, timeout=5)
                for l in r.text.splitlines():
                    if ":" in l: temp_list.add(f"http://{l.strip()}")
            except: pass
        
        SCANNED_TOTAL = len(temp_list)
        if temp_list:
            sample = random.sample(list(temp_list), min(len(temp_list), 50))
            tasks = [test_proxy(p) for p in sample]
            verified = await asyncio.gather(*tasks)
            WORKING_PROXIES = [v for v in verified if v]
        
        IS_READY = len(WORKING_PROXIES) > 0
        gc.collect()
        await asyncio.sleep(300)

def get_progress_bar(percent):
    done = int(percent / 10)
    return f"[{'▬' * done}{'  ' * (10 - done)}] {percent}%"

# --- HANDLERS ---
@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    await message.answer(
        "🔱 **NOTEGPT MASTERPIECE ACTIVE** 🔱\n\n"
        "Bhai, naya token lag chuka hai aur bot ready hai.\n\n"
        "🎵 Music generate karne ke liye prompt bhejo ya button dabao!",
        reply_markup=main_kb, parse_mode="Markdown"
    )

@dp.message(F.text == "📊 My Stats")
async def cmd_stats(message: types.Message):
    status = "🟢 Ready" if IS_READY else "🟡 Warming Up"
    await message.answer(
        f"🛡️ **System Status:** `{status}`\n"
        f"🔍 Total Scanned: `{SCANNED_TOTAL}`\n"
        f"✅ Live Elite Proxies: `{len(WORKING_PROXIES)}`",
        parse_mode="Markdown"
    )

@dp.message(F.text == "🎵 Create Music")
async def request_music(message: types.Message):
    await message.answer("✍️ **Bhai, music ka topic ya prompt bhejo!**")

@dp.message(F.text == "⚙️ Help")
async def cmd_help(message: types.Message):
    await message.answer("Prompt bhejein -> Lyrics turant milenge -> Music background mein compose hoga.")

@dp.message(F.text)
async def handle_logic(message: types.Message):
    if message.text in ["🎵 Create Music", "📊 My Stats", "⚙️ Help"]: return
    if not IS_READY:
        await message.answer(f"⏳ **Warming up proxies...**\nChecking `{SCANNED_TOTAL}` IPs.")
        return

    topic = message.text
    msg = await message.answer(f"🚀 **Syncing with NoteGPT...**\n{get_progress_bar(10)}")
    
    proxy = random.choice(WORKING_PROXIES)
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'android'})
    scraper.proxies = {"http": proxy, "https": proxy}
    
    try:
        await asyncio.to_thread(scraper.get, "https://notegpt.io/ai-music-generator")
        cookies = scraper.cookies.get_dict()
        cookies['anonymous_user_id'] = f"anon_{uuid.uuid4().hex}"
        
        payload = {"prompt": topic, "lyrics": "", "duration": 0}
        headers = {'User-Agent': 'Mozilla/5.0...', 'X-Requested-With': 'XMLHttpRequest'}
        
        res = await asyncio.to_thread(scraper.post, "https://notegpt.io/api/v2/music/generate", json=payload, cookies=cookies, headers=headers)
        data = res.json()
        
        if data.get("code") == 100000:
            cid = data["data"]["conversation_id"]
            lyrics = data["data"].get("lyrics", "Lyrics generation in progress...")
            
            # 📝 Instant Lyrics
            await message.answer(f"📝 **Lyrics Generated:**\n\n{lyrics}")
            
            # 🎼 Music Polling
            for i in range(2, 12):
                prog = min(i * 9, 99)
                await msg.edit_text(f"🎼 **Composing Track...**\n{get_progress_bar(prog)}")
                await asyncio.sleep(8)
                
                status_res = await asyncio.to_thread(scraper.get, f"https://notegpt.io/api/v2/music/status?conversation_id={cid}", cookies=cookies)
                s_data = status_res.json().get("data", {})
                
                if s_data.get("status") == "success":
                    await msg.edit_text(f"📥 **Downloading...**\n{get_progress_bar(100)}")
                    audio = await asyncio.to_thread(scraper.get, s_data.get("music_url"))
                    await message.answer_audio(
                        audio=BufferedInputFile(audio.content, filename=f"Music.mp3"),
                        caption=f"✅ **Bypass Success!**\nTopic: {topic}"
                    )
                    await msg.delete(); return
        else:
            await msg.edit_text(f"❌ Error: {data.get('message')}")
    except Exception:
        await msg.edit_text("⚠️ Connection error. Try again!")
    finally: gc.collect()

async def main():
    asyncio.create_task(refresh_proxies())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
