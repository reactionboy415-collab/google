import logging
import asyncio
import time
import random
import uuid
import cloudscraper
import requests
import gc
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BufferedInputFile

# --- 🔑 CREDENTIALS ---
API_TOKEN = '8540275734:AAFxrWrgYJgeD3YzrnU-y2wiwkZVpjEQyas'
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

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- ⚡ PROXY ENGINE ---

async def test_proxy(p_url):
    try:
        scraper = cloudscraper.create_scraper()
        scraper.proxies = {"http": p_url, "https": p_url}
        loop = asyncio.get_event_loop()
        # Fast 4s timeout to catch only the best proxies
        res = await loop.run_in_executor(None, lambda: scraper.get("https://notegpt.io", timeout=4))
        if res.status_code == 200:
            return p_url
    except:
        pass
    return None

async def refresh_proxies():
    global WORKING_PROXIES, SCANNED_TOTAL
    while True:
        temp_list = []
        logging.info("🔄 Syncing Proxies from Supabase...")
        
        try:
            response = requests.get(SUPABASE_URL, headers=SUPABASE_HEADERS, timeout=15)
            if response.status_code == 200:
                data = response.json()
                proxies = data if isinstance(data, list) else data.get('proxies', [])
                for p in proxies:
                    ip, port = p.get('ip'), p.get('port')
                    if ip and port: temp_list.append(f"http://{ip}:{port}")
        except Exception as e:
            logging.error(f"Supabase Error: {e}")

        # Safety Fallback GitHub
        try:
            r = requests.get("https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt", timeout=5)
            temp_list.extend([f"http://{l}" for l in r.text.splitlines() if ":" in l][:100])
        except: pass

        SCANNED_TOTAL = len(temp_list)
        
        if temp_list:
            # Batch of 40 to prevent RAM spikes on Render
            sample = random.sample(temp_list, min(len(temp_list), 40))
            tasks = [test_proxy(p) for p in sample]
            verified = await asyncio.gather(*tasks)
            WORKING_PROXIES = [v for v in verified if v]
        
        gc.collect() # Immediate RAM cleanup
        await asyncio.sleep(480) # Refresh every 8 mins

# --- 🎼 MUSIC CORE ---

@dp.message(F.text == "/stats")
async def cmd_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer(f"📊 **Render System Stats**\n\n✅ Live Proxies: `{len(WORKING_PROXIES)}` / 40\n🔍 Pool Size: `{SCANNED_TOTAL}`\n🛠 Supabase: `Connected 💎`")

@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    await message.answer("🔱 **NOTEGPT INFINITY v12.5** 🔱\n\nBhai, music ka topic bhejo. Main auto-proxy use karke gaana MP3 mein dunga!")

@dp.message(F.text)
async def handle_music(message: types.Message):
    if not WORKING_PROXIES:
        await message.answer("⌛ **System Warming Up...** Proxies test ho rahi hain, 20s baad try karein.")
        return

    topic = message.text
    msg = await message.answer("🎯 **Targeting Working Proxy...**")
    
    proxy = random.choice(WORKING_PROXIES)
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'android'})
    scraper.proxies = {"http": proxy, "https": proxy}
    
    try:
        # Step 1: Session Init
        await asyncio.to_thread(scraper.get, "https://notegpt.io/ai-music-generator")
        cookies = scraper.cookies.get_dict()
        cookies['anonymous_user_id'] = f"anon_{uuid.uuid4().hex}"
        
        headers = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36",
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://notegpt.io/ai-music-generator'
        }
        
        payload = {"prompt": f"Professional {topic}", "lyrics": f"[Verse]\n{topic} rhythm...", "duration": 0}
        
        # Step 2: Generation Request
        res = await asyncio.to_thread(scraper.post, "https://notegpt.io/api/v2/music/generate", json=payload, cookies=cookies, headers=headers)
        data = res.json()
        
        if data.get("code") == 100000:
            cid = data["data"]["conversation_id"]
            await msg.edit_text("🎼 **AI Studio is composing your track...**")
            
            # Step 3: Fast Polling
            for _ in range(45):
                await asyncio.sleep(10)
                status_res = await asyncio.to_thread(scraper.get, f"https://notegpt.io/api/v2/music/status?conversation_id={cid}", cookies=cookies)
                s_data = status_res.json().get("data", {})
                
                if s_data.get("status") == "success":
                    await msg.edit_text("📥 **Masterpiece ready! Sending file...**")
                    audio = await asyncio.to_thread(scraper.get, s_data.get("music_url"))
                    await message.answer_audio(
                        audio=BufferedInputFile(audio.content, filename=f"{topic[:10]}.mp3"),
                        caption=f"🎁 **Track:** {topic}\n⚡ Power by Supabase Elite Engine"
                    )
                    await msg.delete()
                    return
        else:
            await msg.edit_text(f"❌ **Server Rejected:** {data.get('message')}")
            
    except Exception:
        await msg.edit_text("⚠️ **Proxy Flicker!** Doosri proxy try ho rahi hai, please topic dobara bhejein.")
    finally:
        gc.collect()

async def main():
    asyncio.create_task(refresh_proxies())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())