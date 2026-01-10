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
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties # FIX IMPORT

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
PROXY_STORAGE = {} 
WORKING_PROXIES = []
SCANNED_TOTAL = 0

class MusicState(StatesGroup):
    waiting_for_duration = State()

logging.basicConfig(level=logging.INFO)
# UPDATED INITIALIZATION TO FIX TYPEERROR
bot = Bot(
    token=API_TOKEN, 
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)
dp = Dispatcher()

# --- ⚡ PROFESSIONAL PROXY ENGINE ---

async def test_proxy(p_url):
    try:
        scraper = cloudscraper.create_scraper()
        scraper.proxies = {"http": p_url, "https": p_url}
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, lambda: scraper.get("https://notegpt.io", timeout=5))
        if res.status_code == 200: return p_url
    except: pass
    return None

def get_smart_proxy():
    now = datetime.now()
    available = []
    for p in WORKING_PROXIES:
        data = PROXY_STORAGE.get(p)
        if data and data['uses'] < 4:
            available.append(p)
    
    if available:
        selected = random.choice(available)
        PROXY_STORAGE[selected]['uses'] += 1
        return selected
    return None

async def refresh_proxies():
    global WORKING_PROXIES, SCANNED_TOTAL
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
            sample = random.sample(temp_list, min(len(temp_list), 60))
            tasks = [test_proxy(p) for p in sample]
            verified = await asyncio.gather(*tasks)
            for p in [v for v in verified if v]:
                if p not in WORKING_PROXIES:
                    WORKING_PROXIES.append(p)
                    PROXY_STORAGE[p] = {"uses": 0, "last_reset": datetime.now(), "status": "Online 🟢"}
        
        now = datetime.now()
        for p in list(PROXY_STORAGE.keys()):
            if now - PROXY_STORAGE[p]["last_reset"] >= timedelta(hours=24):
                PROXY_STORAGE[p]["uses"] = 0
                PROXY_STORAGE[p]["last_reset"] = now
        gc.collect()
        await asyncio.sleep(480)

# --- 🎼 CORE HANDLERS ---

@dp.message(F.text == "/stats")
async def cmd_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    
    header = "*📊 INFINTY CORE SYSTEM REPORT*\n" # Removed ** to use standard Markdown
    header += "━━━━━━━━━━━━━━━━━━━━\n"
    header += f"📡 *Pool Status:* `{len(WORKING_PROXIES)}` Active Proxies\n"
    header += f"🔍 *Scanned Total:* `{SCANNED_TOTAL}`\n"
    header += f"🛠 *Supabase:* `Sync Active 💎`\n\n"
    
    proxy_details = "*PROXY REGISTRY:*\n"
    for p in WORKING_PROXIES:
        data = PROXY_STORAGE.get(p, {"uses": 0, "status": "Unknown"})
        clean_ip = p.replace("http://", "")
        proxy_details += f"🔹 `{clean_ip}` | Uses: `{data['uses']}/4` | `{data['status']}`\n"
    
    full_msg = header + proxy_details
    if len(full_msg) > 4000:
        for x in range(0, len(full_msg), 4000):
            await message.answer(full_msg[x:x+4000])
    else:
        await message.answer(full_msg)

@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    await message.answer("*🔱 Welcome to NoteGPT Infinity v13.0 🔱*\n\nProfessional AI Music Generation at your fingertips.\n\n*Instructions:*\nJust send me a song topic or theme, and I will generate professional lyrics followed by a high-quality MP3 track.")

@dp.message(F.text & ~F.text.startswith('/'))
async def ask_duration(message: types.Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="0 - 1 Minute", callback_data="dur_0")],
        [InlineKeyboardButton(text="1 - 2 Minute", callback_data="dur_1")],
        [InlineKeyboardButton(text="2 - 3 Minute", callback_data="dur_2")]
    ])
    await state.update_data(topic=message.text)
    await message.answer("*⏳ Select Composition Duration:*", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("dur_"))
async def handle_music_generation(callback: types.CallbackQuery, state: FSMContext):
    duration_val = int(callback.data.split("_")[1])
    user_data = await state.get_data()
    topic = user_data.get("topic")
    
    proxy = get_smart_proxy()
    if not proxy:
        await callback.message.edit_text("*⌛ System Busy:* All available proxies have reached their daily limit (4/4). Please try again after the 24h reset.")
        return

    status_msg = await callback.message.edit_text("*🎯 Connecting to High-Speed Node...*")
    
    try:
        lyrics_url = f"https://perplexity-api-gray.vercel.app/api/ask?prompt={SYSTEM_PROMPT}{topic}"
        lyric_res = await asyncio.to_thread(requests.get, lyrics_url, timeout=25)
        raw_text = lyric_res.json().get("answer", lyric_res.text)

        match = re.search(r"(\[Verse 1\].*)", raw_text, re.DOTALL | re.IGNORECASE)
        generated_text = match.group(1).strip() if match else raw_text.strip()
        generated_text = re.split(r"(Would you like|I hope this|Let me know)", generated_text, flags=re.IGNORECASE)[0].strip()

        await callback.message.answer(f"*📜 PROFESSIONAL LYRICS GENERATED:*\n\n{generated_text[:3500]}")
        await status_msg.edit_text("*🎼 AI Studio is composing your track. Please wait...*")

        scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'android'})
        scraper.proxies = {"http": proxy, "https": proxy}
        await asyncio.to_thread(scraper.get, "https://notegpt.io/ai-music-generator")
        
        cookies = scraper.cookies.get_dict()
        cookies['anonymous_user_id'] = f"anon_{uuid.uuid4().hex}"
        headers = {'User-Agent': "Mozilla/5.0", 'X-Requested-With': 'XMLHttpRequest', 'Referer': 'https://notegpt.io/ai-music-generator'}
        
        payload = {"prompt": f"Professional {topic}", "lyrics": generated_text, "duration": duration_val}
        
        res = await asyncio.to_thread(scraper.post, "https://notegpt.io/api/v2/music/generate", json=payload, cookies=cookies, headers=headers)
        data = res.json()
        
        if data.get("code") == 100000:
            cid = data["data"]["conversation_id"]
            for _ in range(45):
                await asyncio.sleep(10)
                s_res = await asyncio.to_thread(scraper.get, f"https://notegpt.io/api/v2/music/status?conversation_id={cid}", cookies=cookies)
                s_data = s_res.json().get("data", {})
                if s_data.get("status") == "success":
                    await status_msg.edit_text("*📥 Composition Complete! Uploading MP3...*")
                    audio = await asyncio.to_thread(scraper.get, s_data.get("music_url"))
                    await callback.message.answer_audio(
                        audio=BufferedInputFile(audio.content, filename=f"{topic[:10]}.mp3"),
                        caption=f"*🎁 Track Title:* {topic}\n*⚡ Engine:* Infinity Smart Node"
                    )
                    await status_msg.delete()
                    return
        else:
            if proxy in WORKING_PROXIES:
                PROXY_STORAGE[proxy]['status'] = "Failed 🔴"
                WORKING_PROXIES.remove(proxy)
            await status_msg.edit_text("*⚠️ Studio Error:* The selected node failed to respond. Retrying...")

    except Exception:
        if proxy in WORKING_PROXIES:
            PROXY_STORAGE[proxy]['status'] = "Error 🔴"
            WORKING_PROXIES.remove(proxy)
        await status_msg.edit_text("*⚠️ Technical Error:* Connection timed out. Please try again.")
    finally:
        gc.collect()
        await state.clear()

async def main():
    asyncio.create_task(refresh_proxies())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
