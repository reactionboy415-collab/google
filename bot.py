import logging
import asyncio
import random
import cloudscraper
import requests
import gc
import re
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BufferedInputFile
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

# Improved System Prompt for better AI autonomy
SYSTEM_PROMPT = "You are a professional lyricist. Generate ONLY the lyrics in the language requested or appropriate for the theme. Start immediately with '[Verse 1]'. No markdown, minimum 300 words. Theme: "

PROXY_STORAGE = {} 
SCANNED_TOTAL = 0

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()

# --- ⚡ ADVANCED PROXY & BYPASS ENGINE ---

async def test_proxy(p_url):
    """Tests if proxy can specifically reach NoteGPT without being blocked immediately."""
    try:
        # Using a direct scraper for testing to simulate real request
        tester = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
        res = tester.get("https://notegpt.io/ai-music-generator", proxies={"http": p_url, "https": p_url}, timeout=7)
        return res.status_code == 200
    except:
        return False

def get_smart_proxy():
    available = [p for p, data in PROXY_STORAGE.items() if data['uses'] < 3 and "Online" in data['status']]
    if available:
        selected = random.choice(available)
        PROXY_STORAGE[selected]['uses'] += 1
        return selected
    return None

async def refresh_proxies():
    global SCANNED_TOTAL
    while True:
        temp_list = []
        try:
            r = requests.get(SUPABASE_URL, headers=SUPABASE_HEADERS, timeout=10)
            proxies = r.json() if isinstance(r.json(), list) else r.json().get('proxies', [])
            for p in proxies: temp_list.append(f"http://{p['ip']}:{p['port']}")
        except Exception as e:
            logging.error(f"Supabase Fetch Error: {e}")
        
        SCANNED_TOTAL = len(temp_list)
        if temp_list:
            # Test a batch of proxies for NoteGPT compatibility
            sampled = random.sample(temp_list, min(len(temp_list), 40))
            for p in sampled:
                if p not in PROXY_STORAGE:
                    if await test_proxy(p):
                        PROXY_STORAGE[p] = {"uses": 0, "last_reset": datetime.now(), "status": "Online 🟢"}
        
        # Cleanup old/dead proxies
        now = datetime.now()
        for p in list(PROXY_STORAGE.keys()):
            if now - PROXY_STORAGE[p]["last_reset"] >= timedelta(hours=6): # 6H lifecycle for better quality
                del PROXY_STORAGE[p]
        
        await asyncio.sleep(300)

# --- 🎼 CORE HANDLER ---

@dp.message(F.text & ~F.text.startswith('/'))
async def handle_music_generation(message: types.Message):
    topic = message.text
    proxy = get_smart_proxy()
    
    if not proxy:
        await message.answer("*⌛ Refining Proxy Pool...* Please try in 2 minutes.")
        return

    status_msg = await message.answer(f"*📡 Connected via Node:* `{proxy.split('//')[1][:15]}...`")
    
    try:
        # STEP 1: Lyrics Generation (Pollinations)
        ly_res = requests.get(f"https://text.pollinations.ai/{requests.utils.quote(SYSTEM_PROMPT + topic)}", timeout=25)
        lyrics = re.split(r"(Would you like|I hope this|Note:)", ly_res.text, flags=re.IGNORECASE)[0].strip()
        
        # STEP 2: NoteGPT Call with Fingerprint Bypass
        # We simulate a modern Chrome browser on Windows
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )
        
        proxies = {"http": proxy, "https": proxy}
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Origin': 'https://notegpt.io',
            'Referer': 'https://notegpt.io/ai-music-generator',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        payload = {
            "prompt": f"Professional Studio Quality, {topic}", 
            "lyrics": lyrics, 
            "duration": 0
        }
        
        await status_msg.edit_text("*🎹 Injecting Payload...*")
        
        res = scraper.post("https://notegpt.io/api/v2/music/generate", 
                          json=payload, headers=headers, proxies=proxies, timeout=50)
        
        data = res.json()
        
        if data.get("code") == 100000:
            cid = data["data"]["conversation_id"]
            await status_msg.edit_text("*🎼 Processing Audio (30-60s)...*")
            
            for _ in range(40): # Increased polling range
                await asyncio.sleep(10)
                s_res = scraper.get(f"https://notegpt.io/api/v2/music/status?conversation_id={cid}", 
                                   headers=headers, proxies=proxies)
                s_data = s_res.json().get("data", {})
                
                if s_data.get("status") == "success":
                    audio_url = s_data["music_url"]
                    audio = scraper.get(audio_url, proxies=proxies)
                    await message.answer_audio(
                        BufferedInputFile(audio.content, filename=f"{topic[:20]}.mp3"),
                        caption=f"✅ *Generated successfully!*\n\nNode: `{proxy.split('//')[1]}`"
                    )
                    await status_msg.delete()
                    return
                elif s_data.get("status") == "failed":
                    break
        else:
            # Handle Error 164003 or 164001
            PROXY_STORAGE[proxy]['status'] = f"Dead ({data.get('code')}) 🛑"
            await status_msg.edit_text(f"❌ *Node Refused* (Code: `{data.get('code')}`)\nRetrying with another node...")
            # Optional: Recursive call to retry once
            
    except Exception as e:
        PROXY_STORAGE[proxy]['status'] = "Failed 🔴"
        await status_msg.edit_text(f"⚠️ *Node Error:* `{str(e)[:50]}`")
    finally:
        gc.collect()

async def main():
    asyncio.create_task(refresh_proxies())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
