import logging
import asyncio
import random
import cloudscraper
import requests
import gc
import re
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BufferedInputFile
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties

# --- 🔑 CREDENTIALS ---
API_TOKEN = '8540275734:AAHeIzIWDh53Gzsp6C-RIFzhQ4nfdQA-TS4'
ADMIN_ID = 7840042951

# SUPABASE CONFIG (Proxy Source)
SUPABASE_URL = "https://vwmhbpgwhfwuwtattset.supabase.co/functions/v1/fetch-proxies"
SUPABASE_HEADERS = {
    "Authorization": "Bearer eyJhbGciOiJFUzI1NiIsImtpZCI6ImYyZTIyZWFhLTRhYjQtNDZhOC1hYzM3LTExYzA3YWQyNTgzNCIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL3Z3bWhicGd3aGZ3dXd0YXR0c2V0LnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI1ZmM0NTA3ZS00NTI2LTQ2OGItYjFkMi01YmVlOTZkNmQwMTEiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY3NDA0Nzg0LCJpYXQiOjE3Njc0MDExODQsImVtYWlsIjoiamhvbmRlb0BnbWFpbC5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7ImVtYWlsIjoiamhvbmRlb0BnbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiZnVsbF9uYW1lIjoiSm9obiBkb2UiLCJwaG9uZV92ZXJpZmllZCI6ZmFsc2UsInN1YiI6IjVmYzQ1MDdlLTQ1MjYtNDY4Yi1iMWQyLTViZWU5NmQ2ZDAxMSJ9LCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImFhbCI6ImFhbDEiLCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzY3NDA0Nzg0fV0sInNlc3Npb25faWQiOiI4MzkzYWU2Zi0zYTJlLTQ0ZDUtYjg1ZS1lYWEwMzQwNDdhYWEiLCJpc19hbm9ueW1vdXMiOmZhbHNlfQ.ijYObw_fffHDtEIw3PPKqDyDW6StUn3NkaofNcfTakA5KMCwuzmW6UQq2_mSxfu5PHejh1xUNLQWQCH6weidjQ",
    "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ3bWhicGd3aGZ3dXd0YXR0c2V0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjczMjc0NjYsImV4cCI6MjA4MjkwMzQ2Nn0.LSMD2P4whDzoIW4UCig0ly0j6UOxd5fHhIkUhywnmrg",
    "Content-Type": "application/json"
}

SYSTEM_PROMPT = "Generate ONLY song lyrics. [Verse 1] start. No markdown. Min 350 words. Theme: "

PROXY_STORAGE = {} 
SCANNED_TOTAL = 0

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()

# --- ⚡ SMART PROXY ENGINE ---

async def test_node(p_url):
    try:
        res = requests.get("https://notegpt.io", proxies={"http": p_url, "https": p_url}, timeout=5)
        return res.status_code == 200
    except: return False

async def refresh_pool():
    global SCANNED_TOTAL
    while True:
        try:
            r = requests.get(SUPABASE_URL, headers=SUPABASE_HEADERS, timeout=10)
            proxies = r.json() if isinstance(r.json(), list) else r.json().get('proxies', [])
            SCANNED_TOTAL = len(proxies)
            for p in random.sample(proxies, min(len(proxies), 40)):
                p_url = f"http://{p['ip']}:{p['port']}"
                if p_url not in PROXY_STORAGE and await test_node(p_url):
                    PROXY_STORAGE[p_url] = {"uses": 0, "status": "Online 🟢"}
        except: pass
        for p in list(PROXY_STORAGE.keys()):
            if PROXY_STORAGE[p]['uses'] >= 3: del PROXY_STORAGE[p]
        await asyncio.sleep(120)

def get_node():
    available = [p for p, d in PROXY_STORAGE.items() if "Online" in d['status']]
    return random.choice(available) if available else None

# --- 🎼 LOGIC HANDLERS ---

async def generate_music_logic(topic, lyrics, message, status_msg, attempt=1):
    if attempt > 3:
        await status_msg.edit_text("❌ *All nodes failed.* Try again in 5 mins.")
        return

    proxy = get_node()
    if not proxy:
        await asyncio.sleep(5)
        return await generate_music_logic(topic, lyrics, message, status_msg, attempt)

    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    proxies = {"http": proxy, "https": proxy}
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        'Referer': 'https://notegpt.io/ai-music-generator',
        'Origin': 'https://notegpt.io'
    }

    try:
        await status_msg.edit_text(f"🚀 *Attempt {attempt}:* Using `{proxy.split('//')[1][:12]}...`")
        res = scraper.post("https://notegpt.io/api/v2/music/generate", 
                          json={"prompt": f"Studio, {topic}", "lyrics": lyrics, "duration": 0},
                          headers=headers, proxies=proxies, timeout=25)
        
        data = res.json()
        if data.get("code") == 100000:
            cid = data["data"]["conversation_id"]
            await status_msg.edit_text("🎼 *Composing your song...*")
            for _ in range(40):
                await asyncio.sleep(10)
                s_res = scraper.get(f"https://notegpt.io/api/v2/music/status?conversation_id={cid}", headers=headers, proxies=proxies)
                s_data = s_res.json().get("data", {})
                if s_data.get("status") == "success":
                    audio_res = scraper.get(s_data["music_url"], proxies=proxies)
                    await message.answer_audio(BufferedInputFile(audio_res.content, filename="song.mp3"), caption="✅ *Done!*")
                    await status_msg.delete()
                    return
        else:
            PROXY_STORAGE[proxy]['status'] = "Blocked 🚩"
            await generate_music_logic(topic, lyrics, message, status_msg, attempt + 1)
    except:
        if proxy in PROXY_STORAGE: del PROXY_STORAGE[proxy]
        await generate_music_logic(topic, lyrics, message, status_msg, attempt + 1)

# --- 🤖 BOT COMMANDS ---

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("👋 *Infinity AI Music Bot Ready!*\nJust send me a topic to start.")

@dp.message(Command("stats"))
async def stats(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    active = len([p for p in PROXY_STORAGE])
    await message.answer(f"📊 Nodes: `{active}` | Scanned: `{SCANNED_TOTAL}`")

@dp.message(F.text & ~F.text.startswith('/'))
async def handle(message: types.Message):
    topic = message.text
    status = await message.answer("📝 *Generating Lyrics...*")
    try:
        ly = requests.get(f"https://text.pollinations.ai/{requests.utils.quote(SYSTEM_PROMPT + topic)}", timeout=15).text
        await generate_music_logic(topic, ly, message, status)
    except: await status.edit_text("⚠️ Lyrics Error.")

async def main():
    asyncio.create_task(refresh_pool())
    print("✅ Bot is Online!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
