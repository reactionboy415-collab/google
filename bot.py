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
API_TOKEN = '8540275734:AAH7BYvbSkDa1shS_aDR4Zdy6xNFg_PZzis'
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
PROXY_STORAGE = {} # Key: URL, Value: {'uses': int, 'last_reset': datetime, 'status': str}
SCANNED_TOTAL = 0

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()

# --- ⚡ PROFESSIONAL PROXY ENGINE ---

async def test_proxy(p_url):
    try:
        scraper = cloudscraper.create_scraper()
        scraper.proxies = {"http": p_url, "https": p_url}
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, lambda: scraper.get("https://notegpt.io", timeout=6))
        if res.status_code == 200: return True
    except: pass
    return False

def get_smart_proxy():
    # Only pick proxies that are under the 4-use limit
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
        # 1. FETCH NEW PROXIES
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
        
        # 2. VALIDATE NEW PROXIES AND ADD TO STORAGE
        if temp_list:
            sample = random.sample(temp_list, min(len(temp_list), 40))
            for p in sample:
                if p not in PROXY_STORAGE:
                    is_working = await test_proxy(p)
                    if is_working:
                        PROXY_STORAGE[p] = {"uses": 0, "last_reset": datetime.now(), "status": "Online 🟢"}

        # 3. THE 24-HOUR RESET & PURGE LOGIC
        now = datetime.now()
        for p in list(PROXY_STORAGE.keys()):
            data = PROXY_STORAGE[p]
            if now - data["last_reset"] >= timedelta(hours=24):
                # Before resetting, check if it's still working
                still_working = await test_proxy(p)
                if still_working:
                    PROXY_STORAGE[p]["uses"] = 0
                    PROXY_STORAGE[p]["last_reset"] = now
                    PROXY_STORAGE[p]["status"] = "Online 🟢"
                else:
                    # If failed after 24h, remove it entirely
                    del PROXY_STORAGE[p]
        
        gc.collect()
        await asyncio.sleep(480) # Refresh cycle every 8 mins

# --- 🎼 CORE HANDLERS ---

@dp.message(F.text == "/stats")
async def cmd_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    active_count = len([p for p in PROXY_STORAGE if PROXY_STORAGE[p]['uses'] < 4])
    
    header = "*📊 INFINITY CORE SYSTEM REPORT*\n━━━━━━━━━━━━━━━━━━━━\n"
    header += f"📡 *Available Nodes:* `{active_count}` / `{len(PROXY_STORAGE)}` Total\n"
    header += f"🔍 *Pool Discovery:* `{SCANNED_TOTAL}`\n"
    header += f"🛠 *Engine:* `V15.5 Pro Hug Hug`\n\n"
    
    proxy_details = "*PROXY REGISTRY:*\n"
    for p, data in PROXY_STORAGE.items():
        clean_ip = p.replace('http://', '')
        status_label = "Limit Reached 🟡" if data['uses'] >= 4 else data['status']
        proxy_details += f"🔹 `{clean_ip}` | Usage: `{data['uses']}/4` | `{status_label}`\n"
    
    full_msg = header + proxy_details
    # Handle Telegram message limit
    if len(full_msg) > 4000:
        parts = [full_msg[i:i+4000] for i in range(0, len(full_msg), 4000)]
        for part in parts: await message.answer(part)
    else:
        await message.answer(full_msg)

@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    await message.answer("*🔱 Welcome to NoteGPT Infinity v15.5 🔱*\n\nProfessional AI Music Generation - Optimized and Fast.\n\n*Instructions:*\nJust send me a song topic or theme. I will generate professional lyrics and an MP3 track automatically.")

@dp.message(F.text & ~F.text.startswith('/'))
async def handle_music_generation(message: types.Message):
    topic = message.text
    proxy = get_smart_proxy()
    
    if not proxy:
        await message.answer("*⌛ System Congestion:* All active nodes have reached their daily `4/4` limit. Please wait for the 24h cycle reset.")
        return

    status_msg = await message.answer("*🎯 Initializing Infinity Core...*")
    
    try:
        # STEP 1: Lyrics Generation (Pollinations AI)
        lyrics_url = f"https://text.pollinations.ai/{requests.utils.quote(SYSTEM_PROMPT + topic)}"
        lyric_res = await asyncio.to_thread(requests.get, lyrics_url, timeout=25)
        raw_text = lyric_res.text.strip()

        # Regex Clipping for clean lyrics
        match = re.search(r"(\[Verse 1\].*)", raw_text, re.DOTALL | re.IGNORECASE)
        generated_text = match.group(1).strip() if match else raw_text.strip()
        generated_text = re.split(r"(Would you like|I hope this|Let me know)", generated_text, flags=re.IGNORECASE)[0].strip()

        await message.answer(f"*📜 PROFESSIONAL LYRICS GENERATED:*\n\n{generated_text[:3500]}")
        await status_msg.edit_text("*🎼 AI Studio is composing your track. Mode: 1 Minute Fixed...*")

        # STEP 2: NoteGPT Music
        scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'android'})
        scraper.proxies = {"http": proxy, "https": proxy}
        
        cookies = {'anonymous_user_id': f"anon_{uuid.uuid4().hex}"}
        headers = {'User-Agent': "Mozilla/5.0", 'Referer': 'https://notegpt.io/ai-music-generator'}
        
        # Duration is now fixed at 0 (1 minute)
        payload = {"prompt": f"Professional {topic}", "lyrics": generated_text, "duration": 0}
        
        res = await asyncio.to_thread(scraper.post, "https://notegpt.io/api/v2/music/generate", json=payload, cookies=cookies, headers=headers)
        data = res.json()
        
        if data.get("code") == 100000:
            cid = data["data"]["conversation_id"]
            for _ in range(45):
                await asyncio.sleep(10)
                s_res = await asyncio.to_thread(scraper.get, f"https://notegpt.io/api/v2/music/status?conversation_id={cid}", cookies=cookies)
                s_data = s_res.json().get("data", {})
                
                if s_data.get("status") == "success":
                    audio = await asyncio.to_thread(scraper.get, s_data.get("music_url"))
                    await message.answer_audio(
                        audio=BufferedInputFile(audio.content, filename=f"{topic[:10]}.mp3"),
                        caption=f"*🎁 Track Title:* {topic}\n*⚡ Node:* `{proxy.replace('http://', '')}`"
                    )
                    await status_msg.delete()
                    return
        else:
            PROXY_STORAGE[proxy]['status'] = "Failed 🔴"
            await status_msg.edit_text("*⚠️ Node Error:* Composition failed on this node. Please try one more time.")

    except Exception as e:
        PROXY_STORAGE[proxy]['status'] = "Error 🔴"
        await status_msg.edit_text("*⚠️ System Error:* Connection timed out. Please retry.")
    finally:
        gc.collect()

async def main():
    asyncio.create_task(refresh_proxies())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
