import logging
import asyncio
import time
import random
import uuid
import cloudscraper
import requests
import gc
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BufferedInputFile

# --- 🔑 FULL CREDENTIALS ---
API_TOKEN = '8540275734:AAF_EApz2YKtarq_2pUwwLrW4_W_aQL5mNU'
ADMIN_ID = 7840042951

SUPABASE_URL = "https://vwmhbpgwhfwuwtattset.supabase.co/functions/v1/fetch-proxies"
SUPABASE_HEADERS = {
    "Authorization": "Bearer eyJhbGciOiJFUzI1NiIsImtpZCI6ImYyZTIyZWFhLTRhYjQtNDZhOC1hYzM3LTExYzA3YWQyNTgzNCIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL3Z3bWhicGd3aGZ3dXd0YXR0c2V0LnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI1ZmM0NTA3ZS00NTI2LTQ2OGItYjFkMi01YmVlOTZkNmQwMTEiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY3NDA0Nzg0LCJpYXQiOjE3Njc0MDExODQsImVtYWlsIjoiamhvbmRlb0BnbWFpbC5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7ImVtYWlsIjoiamhvbmRlb0BnbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiZnVsbF9uYW1lIjoiSm9obiBkb2UiLCJwaG9uZV92ZXJpZmllZCI6ZmFsc2UsInN1YiI6IjVmYzQ1MDdlLTQ1MjYtNDY4Yi1iMWQyLTViZWU5NmQ2ZDAxMSJ9LCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImFhbCI6ImFhbDEiLCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzY3NDA0Nzg0fV0sInNlc3Npb25faWQiOiI4MzkzYWU2Zi0zYTJlLTQ0ZDUtYjg1ZS1lYWEwMzQwNDdhYWEiLCJpc19hbm9ueW1vdXMiOmZhbHNlfQ.ijYObw_fffHDtEIw3PPKqDyDW6StUn3NkaofNcfTakA5KMCwuzmW6UQq2_mSxfu5PHejh1xUNLQWQCH6weidjQ",
    "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ3bWhicGd3aGZ3dXd0YXR0c2V0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjczMjc0NjYsImV4cCI6MjA4MjkwMzQ2Nn0.LSMD2P4whDzoIW4UCig0ly0j6UOxd5fHhIkUhywnmrg",
    "Content-Type": "application/json"
}

PROXY_SOURCES = [
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=5000"
]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

WORKING_PROXIES = []
SCANNED_TOTAL = 0

async def test_proxy(p_url):
    try:
        scraper = cloudscraper.create_scraper()
        scraper.proxies = {"http": p_url, "https": p_url}
        res = await asyncio.to_thread(scraper.get, "https://notegpt.io", timeout=3)
        if res.status_code == 200: return p_url
    except: pass
    return None

async def refresh_proxies():
    global WORKING_PROXIES, SCANNED_TOTAL
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
            sample = random.sample(list(temp_list), min(len(temp_list), 40))
            tasks = [test_proxy(p) for p in sample]
            verified = await asyncio.gather(*tasks)
            WORKING_PROXIES = [v for v in verified if v]
        gc.collect()
        await asyncio.sleep(300)

def get_progress_bar(percent):
    done = int(percent / 10)
    return f"[{'▬' * done}{'  ' * (10 - done)}] {percent}%"

@dp.message(F.text == "/stats")
async def cmd_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer(f"🚀 **V14 Engine Stats**\n\n✅ Live: `{len(WORKING_PROXIES)}` / 40\n🔍 Pool: `{SCANNED_TOTAL}`\n💎 Supabase: `Active`")

@dp.message(F.text)
async def handle_music(message: types.Message):
    if not WORKING_PROXIES:
        await message.answer("⏳ Warming up proxies...")
        return

    topic = message.text
    msg = await message.answer(f"🎸 **Initiating AI Studio...**\n{get_progress_bar(10)}")
    
    proxy = random.choice(WORKING_PROXIES)
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'android'})
    scraper.proxies = {"http": proxy, "https": proxy}
    
    try:
        await asyncio.to_thread(scraper.get, "https://notegpt.io/ai-music-generator")
        cookies = scraper.cookies.get_dict()
        cookies['anonymous_user_id'] = f"anon_{uuid.uuid4().hex}"
        
        # Step 1: Generate Lyrics & Music Request
        payload = {"prompt": topic, "lyrics": "", "duration": 0} # Empty lyrics lets AI generate them
        headers = {'User-Agent': 'Mozilla/5.0...', 'X-Requested-With': 'XMLHttpRequest'}
        
        res = await asyncio.to_thread(scraper.post, "https://notegpt.io/api/v2/music/generate", json=payload, cookies=cookies, headers=headers)
        data = res.json()
        
        if data.get("code") == 100000:
            cid = data["data"]["conversation_id"]
            lyrics = data["data"].get("lyrics", "Lyrics generation in progress...")
            
            # --- INSTANT LYRICS DELIVERY ---
            await message.answer(f"📝 **Lyrics Generated:**\n\n{lyrics}")
            
            # --- PROGRESS POLLING FOR MUSIC ---
            for i in range(2, 12):
                progress = min(i * 9, 99)
                await msg.edit_text(f"🎼 **Composing Music...**\n{get_progress_bar(progress)}\n\n*Lyrics sent above!*")
                await asyncio.sleep(8)
                
                status_res = await asyncio.to_thread(scraper.get, f"https://notegpt.io/api/v2/music/status?conversation_id={cid}", cookies=cookies)
                s_data = status_res.json().get("data", {})
                
                if s_data.get("status") == "success":
                    await msg.edit_text(f"📥 **Downloading Track...**\n{get_progress_bar(100)}")
                    audio = await asyncio.to_thread(scraper.get, s_data.get("music_url"))
                    await message.answer_audio(
                        audio=BufferedInputFile(audio.content, filename=f"Music.mp3"),
                        caption=f"🔥 **Music Finished!**\nTopic: {topic}"
                    )
                    await msg.delete(); return
        else:
            await msg.edit_text(f"❌ Error: {data.get('message')}")
    except Exception as e:
        await msg.edit_text(f"⚠️ Connection Flicker. Try again!")
    finally: gc.collect()

async def main():
    asyncio.create_task(refresh_proxies())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
