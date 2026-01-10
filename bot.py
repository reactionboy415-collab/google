import logging
import asyncio
import time
import random
import uuid
import cloudscraper
import requests
import gc
import os
from urllib.parse import quote
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BufferedInputFile

# --- 🔑 CREDENTIALS ---
API_TOKEN = '8540275734:AAHA5OKbwzhQfdmS_Y73ij9AmuQy-WG0mNM'
ADMIN_ID = 7840042951

# SUPABASE CONFIG
SUPABASE_URL = "https://vwmhbpgwhfwuwtattset.supabase.co/functions/v1/fetch-proxies"
SUPABASE_HEADERS = {
    "Authorization": "Bearer eyJhbGciOiJFUzI1NiIsImtpZCI6ImYyZTIyZWFhLTRhYjQtNDZhOC1hYzM3LTExYzA3YWQyNTgzNCIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL3Z3bWhicGd3aGZ3dXd0YXR0c2V0LnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI1ZmM0NTA3ZS00NTI2LTQ2OGItYjFkMi01YmVlOTZkNmQwMTEiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY3NDA0Nzg0LCJpYXQiOjE3Njc0MDExODQsImVtYWlsIjoiamhvbmRlb0BnbWFpbC5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7ImVtYWlsIjoiamhvbmRlb0BnbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiZnVsbF9uYW1lIjoiSm9obiBkb2UiLCJwaG9uZV92ZXJpZmllZCI6ZmFsc2UsInN1YiI6IjVmYzQ1MDdlLTQ1MjYtNDY4Yi1iMWQyLTViZWU5NmQ2ZDAxMSJ9LCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImFhbCI6ImFhbDEiLCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzY3NDA0Nzg0fV0sInNlc3Npb25faWQiOiI4MzkzYWU2Zi0zYTJlLTQ0ZDUtYjg1ZS1lYWEwMzQwNDdhYWEiLCJpc19hbm9ueW1vdXMiOmZhbHNlfQ.ijYObw_fffHDtEIw3PPKqDyDW6StUn3NkaofNcfTakA5KMCwuzmW6UQq2_mSxfu5PHejh1xUNLQWQCH6weidjQ",
    "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ3bWhicGd3aGZ3dXd0YXR0c2V0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjczMjc0NjYsImV4cCI6MjA4MjkwMzQ2Nn0.LSMD2P4whDzoIW4UCig0ly0j6UOxd5fHhIkUhywnmrg",
    "Content-Type": "application/json"
}

# --- GLOBAL STATE ---
WORKING_PROXIES = []
SCANNED_TOTAL = 0
PROXY_USAGE = {}
VALIDATION_SEMAPHORE = asyncio.Semaphore(50) # Fast parallel testing

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- ⚡ HIGH-SPEED PROXY ENGINE ---

def clean_old_usage():
    now = time.time()
    for p in list(PROXY_USAGE.keys()):
        PROXY_USAGE[p] = [t for t in PROXY_USAGE[p] if now - t < 86400]
        if not PROXY_USAGE[p]:
            del PROXY_USAGE[p]

def get_available_proxy():
    clean_old_usage()
    available = [p for p in WORKING_PROXIES if len(PROXY_USAGE.get(p, [])) < 4]
    if not available: return None
    selected = random.choice(available)
    if selected not in PROXY_USAGE: PROXY_USAGE[selected] = []
    PROXY_USAGE[selected].append(time.time())
    return selected

async def test_proxy(p_url):
    """Filters only Superfast/Medium-Fast Proxies (Strict 2.5s Timeout)"""
    async with VALIDATION_SEMAPHORE:
        try:
            scraper = cloudscraper.create_scraper()
            scraper.proxies = {"http": p_url, "https": p_url}
            loop = asyncio.get_event_loop()
            # Reduced timeout to 2.5s to ensure ONLY fast proxies are selected
            res = await loop.run_in_executor(None, lambda: scraper.get("https://notegpt.io", timeout=2.5))
            if res.status_code == 200:
                return p_url
        except:
            pass
        return None

async def refresh_proxies():
    global WORKING_PROXIES, SCANNED_TOTAL
    while True:
        temp_list = set()
        logging.info("🚀 Rapid Proxy Sync Initiated...")
        
        # Source 1: Supabase
        try:
            response = requests.get(SUPABASE_URL, headers=SUPABASE_HEADERS, timeout=10)
            if response.status_code == 200:
                data = response.json()
                proxies = data if isinstance(data, list) else data.get('proxies', [])
                for p in proxies:
                    ip, port = p.get('ip'), p.get('port')
                    if ip and port: temp_list.add(f"http://{ip}:{port}")
        except: pass

        # Source 2 & 3: High-Speed Public Fallbacks
        fallback_urls = [
            "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt"
        ]
        for url in fallback_urls:
            try:
                r = requests.get(url, timeout=5)
                temp_list.update([f"http://{l}" for l in r.text.splitlines() if ":" in l])
            except: pass

        SCANNED_TOTAL = len(temp_list)
        
        if temp_list:
            # Test a large sample to find the fastest ones
            sample = random.sample(list(temp_list), min(len(temp_list), 150))
            tasks = [test_proxy(p) for p in sample]
            verified = await asyncio.gather(*tasks)
            # Update pool with only verified fast proxies
            WORKING_PROXIES = [v for v in verified if v]
            logging.info(f"✅ Fast Proxy Pool Updated: {len(WORKING_PROXIES)} active.")
        
        gc.collect()
        await asyncio.sleep(300) # Faster refresh (5 mins)

# --- 🎼 MUSIC CORE ---

@dp.message(F.text == "/stats")
async def cmd_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    clean_old_usage()
    await message.answer(f"📊 **System Performance Statistics**\n\n✅ Superfast Proxies: `{len(WORKING_PROXIES)}` / 150\n🔍 Total Scanned: `{SCANNED_TOTAL}`\n🛠 Mode: `ULTRA-SPEED ⚡`\n📈 Usage Limit: `4 req/24h`")

@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    await message.answer("🔱 **NOTEGPT INFINITY v12.5** 🔱\n\nPlease provide a song topic. I will use only high-speed proxy routes to process your request.")

@dp.message(F.text)
async def handle_music(message: types.Message):
    proxy = get_available_proxy()
    if not WORKING_PROXIES or not proxy:
        await message.answer("⌛ **Resources Optimizing.** The system is filtering for high-speed proxies. Please retry in a moment.")
        return

    topic = message.text
    msg = await message.answer("🎯 **Routing via High-Speed Proxy...**")
    
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'android'})
    scraper.proxies = {"http": proxy, "https": proxy}
    
    try:
        # Step 1: Session Init
        await asyncio.to_thread(scraper.get, "https://notegpt.io/ai-music-generator", timeout=5)
        cookies = scraper.cookies.get_dict()
        cookies['anonymous_user_id'] = f"anon_{uuid.uuid4().hex}"
        
        headers = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36",
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://notegpt.io/ai-music-generator'
        }
        
        # Step 2: Lyrics Generation
        await msg.edit_text("✍️ **Synthesizing High-Quality Lyrics...**")
        prompt = f"Write professional HINDI song lyrics about '{topic}'. Structure: [Verse 1], [Chorus], [Verse 2], [Bridge], [Outro]. Max 280 words. Strictly use HINDI language only. Plain text."
        url = f"https://text.pollinations.ai/{quote(prompt)}"
        
        lyric_res = await asyncio.to_thread(scraper.get, url, timeout=10)
        generated_lyrics = lyric_res.text

        await message.answer(f"📝 **Lyrics for: {topic}**\n\n```\n{generated_lyrics}\n```")
        
        # Step 3: Audio Synthesis
        payload = {"prompt": f"Professional {topic}", "lyrics": generated_lyrics, "duration": 0}
        await msg.edit_text("🎼 **Synthesizing Audio via Studio Engine...**")
        
        res = await asyncio.to_thread(scraper.post, "https://notegpt.io/api/v2/music/generate", json=payload, cookies=cookies, headers=headers, timeout=10)
        data = res.json()
        
        if data.get("code") == 100000:
            cid = data["data"]["conversation_id"]
            await msg.edit_text("🎼 **Rendering Track...**")
            
            for _ in range(45):
                await asyncio.sleep(8)
                status_res = await asyncio.to_thread(scraper.get, f"https://notegpt.io/api/v2/music/status?conversation_id={cid}", cookies=cookies, timeout=5)
                s_data = status_res.json().get("data", {})
                
                if s_data.get("status") == "success":
                    await msg.edit_text("📥 **Transmission in progress...**")
                    audio = await asyncio.to_thread(scraper.get, s_data.get("music_url"), timeout=15)
                    await message.answer_audio(
                        audio=BufferedInputFile(audio.content, filename=f"{topic[:10]}.mp3"),
                        caption=f"🎁 **Track:** {topic}\n⚡ High-Speed Engine Delivery"
                    )
                    await msg.delete()
                    return
        else:
            await msg.edit_text(f"❌ **NoteGPT Error:** {data.get('message')}")
            
    except Exception as e:
        logging.error(f"High-Speed Failure: {e}")
        await msg.edit_text("⚠️ **Path Timeout.** The assigned high-speed proxy lagged. Re-routing now. Please resend the topic.")
    finally:
        gc.collect()

async def main():
    asyncio.create_task(refresh_proxies())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
