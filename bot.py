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

# --- 📜 SYSTEM PROMPT ---
SYSTEM_PROMPT = (
    "STRICT INSTRUCTION: Output ONLY the lyrics. Start immediately with '[Verse 1]'. "
    "Do not include any conversational text, warnings, or introductions. "
    "Minimum 300 words. Theme: "
)

# --- GLOBAL STATE ---
PROXY_STORAGE = {} 
SCANNED_TOTAL = 0

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()

# --- ⚡ PROFESSIONAL PROXY ENGINE & LIFECYCLE ---

async def test_proxy(p_url):
    try:
        scraper = cloudscraper.create_scraper()
        scraper.proxies = {"http": p_url, "https": p_url}
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, lambda: scraper.get("https://notegpt.io", timeout=6))
        return res.status_code == 200
    except:
        return False

def get_smart_proxy():
    # Only pick nodes that are under 4/4 uses and not in active error state
    available = [p for p, data in PROXY_STORAGE.items() if data['uses'] < 4 and "Online" in data['status']]
    if available:
        selected = random.choice(available)
        PROXY_STORAGE[selected]['uses'] += 1
        return selected
    return None

async def refresh_proxies():
    global SCANNED_TOTAL
    sources = [
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
        "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000"
    ]
    while True:
        temp_list = []
        try:
            response = requests.get(SUPABASE_URL, headers=SUPABASE_HEADERS, timeout=10)
            if response.status_code == 200:
                data = response.json()
                proxies = data if isinstance(data, list) else data.get('proxies', [])
                for p in proxies:
                    ip, port = p.get('ip'), p.get('port')
                    if ip and port: temp_list.append(f"http://{ip}:{port}")
        except: pass
        for src in sources:
            try:
                r = requests.get(src, timeout=5)
                temp_list.extend([f"http://{l}" for l in r.text.splitlines() if ":" in l][:50])
            except: pass
        
        SCANNED_TOTAL = len(temp_list)
        if temp_list:
            sample = random.sample(temp_list, min(len(temp_list), 40))
            for p in sample:
                if p not in PROXY_STORAGE:
                    if await test_proxy(p):
                        PROXY_STORAGE[p] = {"uses": 0, "last_reset": datetime.now(), "status": "Online 🟢"}
        
        # 24H RESET & LIFECYCLE CHECK
        now = datetime.now()
        for p in list(PROXY_STORAGE.keys()):
            data = PROXY_STORAGE[p]
            if now - data["last_reset"] >= timedelta(hours=24):
                if await test_proxy(p):
                    PROXY_STORAGE[p]["uses"] = 0
                    PROXY_STORAGE[p]["last_reset"] = now
                    PROXY_STORAGE[p]["status"] = "Online 🟢"
                else:
                    del PROXY_STORAGE[p] # Purge dead proxies
        
        gc.collect()
        await asyncio.sleep(480)

# --- 🎼 CORE HANDLERS ---

@dp.message(F.text == "/stats")
async def cmd_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    active = len([p for p, d in PROXY_STORAGE.items() if d['uses'] < 4])
    header = f"*📊 INFINITY CORE REPORT*\n━━━━━━━━━━━━━━━\n📡 *Nodes:* `{active}/{len(PROXY_STORAGE)}` Available\n🔍 *Discovery:* `{SCANNED_TOTAL}`\n\n"
    details = "*REGISTRY:*\n"
    for p, d in PROXY_STORAGE.items():
        details += f"🔹 `{p.replace('http://','')}` | `{d['uses']}/4` | `{d['status']}`\n"
    await message.answer((header + details)[:4096])

@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    await message.answer("*🔱 Welcome to NoteGPT Infinity v16.0 🔱*\n\nSend a song topic to begin. Fixed Duration: 1 Min.")

@dp.message(F.text & ~F.text.startswith('/'))
async def handle_music_generation(message: types.Message):
    topic = message.text
    proxy = get_smart_proxy()
    
    if not proxy:
        await message.answer("*⌛ System Congestion:* All nodes at `4/4` limit. Please wait.")
        return

    status_msg = await message.answer("*🎯 Connecting to Engine...*")
    
    try:
        # STEP 1: Lyrics
        ly_url = f"https://text.pollinations.ai/{requests.utils.quote(SYSTEM_PROMPT + topic)}"
        ly_res = await asyncio.to_thread(requests.get, ly_url, timeout=25)
        raw_ly = ly_res.text.strip()
        match = re.search(r"(\[Verse 1\].*)", raw_ly, re.DOTALL | re.IGNORECASE)
        lyrics = match.group(1).strip() if match else raw_ly
        lyrics = re.split(r"(Would you like|I hope this)", lyrics, flags=re.IGNORECASE)[0].strip()

        await message.answer(f"*📜 LYRICS GENERATED:*\n\n{lyrics[:3500]}")
        await status_msg.edit_text("*🎼 Composing Track (Mode: 1 Min)...*")

        # STEP 2: NoteGPT Music (DEBUG ENABLED)
        scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'android'})
        scraper.proxies = {"http": proxy, "https": proxy}
        
        payload = {"prompt": f"Professional {topic}", "lyrics": lyrics, "duration": 0}
        headers = {'User-Agent': "Mozilla/5.0", 'Referer': 'https://notegpt.io/ai-music-generator'}
        
        # POST Request
        res = await asyncio.to_thread(scraper.post, "https://notegpt.io/api/v2/music/generate", json=payload, headers=headers, timeout=45)
        
        if res.status_code != 200:
            PROXY_STORAGE[proxy]['status'] = f"HTTP {res.status_code} 🔴"
            await status_msg.edit_text(f"❌ *Node Rejected*\n*Status:* `{res.status_code}`\n*Error:* `{res.text[:100]}`")
            return

        data = res.json()
        if data.get("code") == 100000:
            cid = data["data"]["conversation_id"]
            for _ in range(40):
                await asyncio.sleep(10)
                s_res = await asyncio.to_thread(scraper.get, f"https://notegpt.io/api/v2/music/status?conversation_id={cid}")
                s_data = s_res.json().get("data", {})
                if s_data.get("status") == "success":
                    audio = await asyncio.to_thread(scraper.get, s_data.get("music_url"))
                    await message.answer_audio(BufferedInputFile(audio.content, filename="song.mp3"), caption=f"*⚡ Node:* `{proxy.split('//')[1]}`")
                    await status_msg.delete()
                    return
        else:
            PROXY_STORAGE[proxy]['status'] = "Logic Err 🔴"
            await status_msg.edit_text(f"⚠️ *NoteGPT Error*\n*Code:* `{data.get('code')}`\n*Msg:* `{data.get('msg')}`")

    except Exception as e:
        PROXY_STORAGE[proxy]['status'] = "Timeout 🔴"
        await status_msg.edit_text(f"⚠️ *Technical Error*\n`{str(e)[:200]}`")
    finally:
        gc.collect()

async def main():
    asyncio.create_task(refresh_proxies())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
