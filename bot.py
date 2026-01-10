import logging
import asyncio
import time
import random
import uuid
import cloudscraper
import requests
import gc
import re
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# --- 🔑 CREDENTIALS ---
API_TOKEN = '8540275734:AAHeIzIWDh53Gzsp6C-RIFzhQ4nfdQA-TS4'
ADMIN_ID = 7840042951

# SUPABASE CONFIG
SUPABASE_URL = "https://vwmhbpgwhfwuwtattset.supabase.co/functions/v1/fetch-proxies"
SUPABASE_HEADERS = {
    "Authorization": "Bearer eyJhbGciOiJFUzI1NiIsImtpZCI6ImYyZTIyZWFhLTRhYjQtNDZhOC1hYzM3LTExYzA3YWQyNTgzNCIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL3Z3bWhicGd3aGZ3dXd0YXR0c2V0LnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI1ZmM0NTA3ZS00NTI2LTQ2OGItYjFkMi01YmVlOTZkNmQwMTEiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY3NDA0Nzg0LCJpYXQiOjE3Njc0MDExODQsImVtYWlsIjoiamhvbmRlb0BnbWFpbC5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7ImVtYWlsIjoiamhvbmRlb0BnbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiZnVsbF9uYW1lIjoiSm9obiBkb2UiLCJwaG9uZV92ZXJpZmllZCI6ZmFsc2UsInN1YiI6IjVmYzQ1MDdlLTQ1MjYtNDY4Yi1iMWQyLTViZWU5NmQ2ZDAxMSJ9LCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImFhbCI6ImFhbDEiLCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzY3NDA0Nzg0fV0sInNlc3Npb25faWQiOiI4MzkzYWU2Zi0zYTJlLTQ0ZDUtYjg1ZS1lYWEwMzQwNDdhYWEiLCJpc19hbm9ueW1vdXMiOmZhbHNlfQ.ijYObw_fffHDtEIw3PPKqDyDW6StUn3NkaofNcfTakA5KMCwuzmW6UQq2_mSxfu5PHejh1xUNLQWQCH6weidjQ",
    "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ3bWhicGd3aGZ3dXd0YXR0c2V0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjczMjc0NjYsImV4cCI6MjA4MjkwMzQ2Nn0.LSMD2P4whDzoIW4UCig0ly0j6UOxd5fHhIkUhywnmrg",
    "Content-Type": "application/json"
}

SYSTEM_PROMPT = "STRICT INSTRUCTION: Output ONLY the lyrics. Start immediately with '[Verse 1]'. Minimum 300 words. Theme: "

PROXY_STORAGE = {} 
SCANNED_TOTAL = 0

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()

# --- ⚡ ENHANCED PROXY ENGINE ---

async def test_proxy(p_url):
    try:
        # Use a real session to test if the proxy hides the IP properly
        res = requests.get("https://notegpt.io", proxies={"http": p_url, "https": p_url}, timeout=5)
        return res.status_code == 200
    except:
        return False

def get_smart_proxy():
    available = [p for p, data in PROXY_STORAGE.items() if data['uses'] < 4 and "Online" in data['status']]
    if available:
        selected = random.choice(available)
        PROXY_STORAGE[selected]['uses'] += 1
        return selected
    return None

async def refresh_proxies():
    global SCANNED_TOTAL
    sources = ["https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt"]
    while True:
        temp_list = []
        try:
            r = requests.get(SUPABASE_URL, headers=SUPABASE_HEADERS, timeout=10)
            proxies = r.json() if isinstance(r.json(), list) else r.json().get('proxies', [])
            for p in proxies: temp_list.append(f"http://{p['ip']}:{p['port']}")
        except: pass
        
        SCANNED_TOTAL = len(temp_list)
        if temp_list:
            for p in random.sample(temp_list, min(len(temp_list), 30)):
                if p not in PROXY_STORAGE and await test_proxy(p):
                    PROXY_STORAGE[p] = {"uses": 0, "last_reset": datetime.now(), "status": "Online 🟢"}
        
        # 24H LIFECYCLE
        now = datetime.now()
        for p in list(PROXY_STORAGE.keys()):
            if now - PROXY_STORAGE[p]["last_reset"] >= timedelta(hours=24):
                if await test_proxy(p):
                    PROXY_STORAGE[p].update({"uses": 0, "last_reset": now})
                else: del PROXY_STORAGE[p]
        await asyncio.sleep(480)

# --- 🎼 CORE HANDLER ---

@dp.message(F.text == "/stats")
async def cmd_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    active = len([p for p, d in PROXY_STORAGE.items() if d['uses'] < 4])
    header = f"*📊 INFINITY CORE V16.5*\n━━━━━━━━━━━━━━━\n📡 *Active Pool:* `{active}`\n🔍 *Total Scanned:* `{SCANNED_TOTAL}`\n\n"
    details = "".join([f"🔹 `{p.split('//')[1]}` | `{d['uses']}/4` | `{d['status']}`\n" for p, d in PROXY_STORAGE.items()])
    await message.answer((header + details)[:4096])

@dp.message(F.text & ~F.text.startswith('/'))
async def handle_music_generation(message: types.Message):
    topic = message.text
    proxy = get_smart_proxy()
    
    if not proxy:
        await message.answer("*⌛ No clean nodes available.* Please try in 5 mins.")
        return

    status_msg = await message.answer("*🎯 Routing through Direct Proxy...*")
    
    try:
        # STEP 1: Lyrics
        ly_res = requests.get(f"https://text.pollinations.ai/{requests.utils.quote(SYSTEM_PROMPT + topic)}", timeout=20)
        lyrics = re.split(r"(Would you like|I hope this)", ly_res.text, flags=re.IGNORECASE)[0].strip()
        await message.answer(f"*📜 LYRICS:* \n\n{lyrics[:3000]}")

        # STEP 2: NoteGPT (DIRECT PROXY INJECTION)
        # We use cloudscraper but explicitly pass the proxy to the underlying session
        scraper = cloudscraper.create_scraper()
        proxies = {"http": proxy, "https": proxy}
        
        headers = {
            'User-Agent': "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
            'Accept': 'application/json, text/plain, */*',
            'Referer': 'https://notegpt.io/ai-music-generator',
            'Content-Type': 'application/json'
        }
        
        payload = {"prompt": f"Professional {topic}", "lyrics": lyrics, "duration": 0}
        
        # This forces the request to go directly through the proxy IP
        res = scraper.post("https://notegpt.io/api/v2/music/generate", 
                          json=payload, 
                          headers=headers, 
                          proxies=proxies, 
                          timeout=45)
        
        data = res.json()
        if data.get("code") == 100000:
            cid = data["data"]["conversation_id"]
            await status_msg.edit_text("*🎼 Composition in progress...*")
            for _ in range(30):
                await asyncio.sleep(10)
                s_res = scraper.get(f"https://notegpt.io/api/v2/music/status?conversation_id={cid}", proxies=proxies)
                s_data = s_res.json().get("data", {})
                if s_data.get("status") == "success":
                    audio = scraper.get(s_data["music_url"], proxies=proxies)
                    await message.answer_audio(BufferedInputFile(audio.content, filename="song.mp3"))
                    await status_msg.delete()
                    return
        else:
            # Handle Error 164003 (Bot Detected)
            PROXY_STORAGE[proxy]['status'] = f"Flagged ({data.get('code')}) 🚩"
            await status_msg.edit_text(f"❌ *Node Refused*\nCode: `{data.get('code')}`\nTry sending the topic again to use a fresh node.")

    except Exception as e:
        PROXY_STORAGE[proxy]['status'] = "Failed 🔴"
        await status_msg.edit_text(f"⚠️ *Connection Error*\n`{str(e)[:100]}`")
    finally:
        gc.collect()

async def main():
    asyncio.create_task(refresh_proxies())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
