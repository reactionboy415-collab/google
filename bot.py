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

# Optimized System Prompt for word count and structure
SYSTEM_PROMPT = (
    "You are a professional songwriter. Generate ONLY the song lyrics. "
    "Start immediately with [Verse 1]. Minimum 350 words. No chatty text or markdown. "
    "Theme: "
)

PROXY_STORAGE = {} 
SCANNED_TOTAL = 0

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()

# --- ⚡ SMART PROXY ENGINE ---

async def test_node(p_url):
    """Specific test for NoteGPT availability."""
    try:
        res = requests.get("https://notegpt.io/ai-music-generator", 
                          proxies={"http": p_url, "https": p_url}, timeout=5)
        return res.status_code == 200
    except:
        return False

async def refresh_pool():
    """Background task to keep proxies fresh every 120 seconds."""
    global SCANNED_TOTAL
    while True:
        try:
            r = requests.get(SUPABASE_URL, headers=SUPABASE_HEADERS, timeout=10)
            proxies = r.json() if isinstance(r.json(), list) else r.json().get('proxies', [])
            SCANNED_TOTAL = len(proxies)
            
            # Select and test a fresh batch
            for p in random.sample(proxies, min(len(proxies), 40)):
                p_url = f"http://{p['ip']}:{p['port']}"
                if p_url not in PROXY_STORAGE:
                    if await test_node(p_url):
                        PROXY_STORAGE[p_url] = {"uses": 0, "status": "Online 🟢"}
        except Exception as e:
            logging.error(f"Pool Refresh Error: {e}")
        
        # Cleanup: Remove nodes with too many uses
        for p in list(PROXY_STORAGE.keys()):
            if PROXY_STORAGE[p]['uses'] >= 3:
                del PROXY_STORAGE[p]
                
        await asyncio.sleep(120)

def get_best_node():
    available = [p for p, d in PROXY_STORAGE.items() if "Online" in d['status']]
    if available:
        node = random.choice(available)
        PROXY_STORAGE[node]['uses'] += 1
        return node
    return None

# --- 🎼 CORE MUSIC GENERATION ---

async def generate_music_logic(topic, lyrics, message, status_msg, attempt=1):
    if attempt > 3:
        await status_msg.edit_text("❌ *All attempts failed.* NoteGPT is heavily limiting right now. Try later.")
        return

    proxy = get_best_node()
    if not proxy:
        await status_msg.edit_text("⌛ *Waiting for fresh nodes...* (30s)")
        await asyncio.sleep(10)
        return await generate_music_logic(topic, lyrics, message, status_msg, attempt)

    # Browser Simulation for Fingerprint Bypass
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
    )
    
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://notegpt.io/ai-music-generator',
        'Origin': 'https://notegpt.io',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin'
    }

    try:
        await status_msg.edit_text(f"🚀 *Attempt {attempt}:* Injecting via `{proxy.split('//')[1][:12]}...`")
        
        payload = {
            "prompt": f"Professional High-Fidelity Studio, {topic}", 
            "lyrics": lyrics, 
            "duration": 0
        }
        
        # 1. GENERATE REQUEST
        res = scraper.post("https://notegpt.io/api/v2/music/generate", 
                          json=payload, headers=headers, 
                          proxies={"http": proxy, "https": proxy}, timeout=25)
        
        data = res.json()
        
        if data.get("code") == 100000:
            cid = data["data"]["conversation_id"]
            await status_msg.edit_text("🎼 *Payload accepted! Composing...*")
            
            # 2. STATUS POLLING
            for _ in range(45): # Max 7.5 mins polling
                await asyncio.sleep(10)
                s_res = scraper.get(f"https://notegpt.io/api/v2/music/status?conversation_id={cid}", 
                                   headers=headers, proxies={"http": proxy, "https": proxy}, timeout=15)
                s_data = s_res.json().get("data", {})
                
                if s_data.get("status") == "success":
                    audio_res = scraper.get(s_data["music_url"], proxies={"http": proxy, "https": proxy})
                    await message.answer_audio(
                        BufferedInputFile(audio_res.content, filename=f"infinity_{cid[:5]}.mp3"),
                        caption=f"✅ *Success!*\n\nNode: `{proxy.split('//')[1]}`"
                    )
                    await status_msg.delete()
                    return
                elif s_data.get("status") == "failed":
                    break
        else:
            # Handle 164003 or other blocks
            PROXY_STORAGE[proxy]['status'] = f"Blocked ({data.get('code', 'Err')}) 🚩"
            await generate_music_logic(topic, lyrics, message, status_msg, attempt + 1)

    except Exception as e:
        if proxy in PROXY_STORAGE: del PROXY_STORAGE[proxy]
        logging.error(f"Node Exception: {e}")
        await generate_music_logic(topic, lyrics, message, status_msg, attempt + 1)

# --- 🛠️ HANDLERS ---

@dp.message(F.text == "/stats")
async def cmd_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    active = len([p for p, d in PROXY_STORAGE.items() if "Online" in d['status']])
    await message.answer(f"📊 *Infinity Core Stats*\n━━━━━━━━━━━━━━━\n📡 Active Nodes: `{active}`\n🔍 Total Scanned: `{SCANNED_TOTAL}`")

@dp.message(F.text & ~F.text.startswith('/'))
async def handle_request(message: types.Message):
    topic = message.text
    status_msg = await message.answer("📝 *Crafting professional lyrics...*")
    
    try:
        # Step 1: Get high-quality lyrics
        ly_res = requests.get(f"https://text.pollinations.ai/{requests.utils.quote(SYSTEM_PROMPT + topic)}", timeout=20)
        lyrics = ly_res.text.strip()
        
        # Step 2: Start Music Engine with Retry
        await generate_music_logic(topic, lyrics, message, status_msg)
    except Exception as e:
        await status_msg.edit_text(f"⚠️ *System Error:* `{str(e)[:50]}`")

async def main():
    # Start proxy refresher task
    asyncio.create_task(refresh_pool())
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    finally:
        gc.collect()
