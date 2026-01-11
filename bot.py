import asyncio
import requests
import random
import uuid
import time
from urllib.parse import quote
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BufferedInputFile

# --- 🔑 CONFIG ---
API_TOKEN = '8540275734:AAHA5OKbwzhQfdmS_Y73ij9AmuQy-WG0mNM'
ADMIN_ID = 7840042951
# Using the .app domain with a random prefix
BASE_URL = "google-worker.vercel.app" 

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

class HybridEngine:
    async def start_via_tunnel(self, payload):
        # INTERNAL IDENTITY ROTATION
        anon_id = str(uuid.uuid4())
        fake_addr = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
        
        headers = {
            'X-Forwarded-For': fake_addr,
            'User-Agent': f"Mozilla/5.0 (Linux; Android 10; SM-G960F) AppleWebKit/537.36 Chrome/{random.randint(80,120)}.0.0.0 Mobile Safari/537.36",
            'Origin': 'https://notegpt.io',
            'Referer': 'https://notegpt.io/ai-music-generator'
        }
        cookies = {'anonymous_user_id': anon_id, 'is_accepted_terms': '1'}
        
        # ROUTE SHIFTING (Hidden from user)
        target_api = f"https://{BASE_URL}/api/{uuid.uuid4().hex[:8]}"
        
        data = {
            "url": "https://notegpt.io/api/v2/music/generate",
            "payload": payload,
            "cookies": cookies,
            "headers": headers
        }
        
        return await asyncio.to_thread(requests.post, target_api, json=data, timeout=45), cookies

    async def poll_locally(self, cid, cookies):
        url = f"https://notegpt.io/api/v2/music/status?conversation_id={cid}"
        return await asyncio.to_thread(requests.get, url, cookies=cookies, timeout=15)

engine = HybridEngine()

@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    welcome_text = (
        "✨ Welcome to Songify AI Assistant ✨\n\n"
        "Transform your creative ideas into studio-quality music instantly.\n\n"
        "🎼 How to use:\n"
        "Simply send me a topic, a mood, or a detailed prompt.\n\n"
        "🚀 Let's start creating! Send your prompt below."
    )
    await message.answer(welcome_text)

@dp.message(F.text)
async def handle_music(message: types.Message):
    if message.text.startswith("/"): return
    
    topic = message.text
    status_msg = await message.answer("✍️ Drafting lyrics...")
    
    try:
        # LYRICS GENERATION
        ly_p = f"Professional lyrics about {topic}. Transliterated Hindi. [Verse], [Chorus]."
        ly_res = requests.get(f"https://text.pollinations.ai/{quote(ly_p)}?cache=false")
        lyrics = ly_res.text
        await message.answer(f"📜 Lyrics:\n\n{lyrics[:3000]}")

        # START STUDIO (User sees clean messages)
        await status_msg.edit_text("🚀 Initializing Studio Session...")
        payload = {"prompt": f"{topic} high quality", "lyrics": lyrics[:2000], "duration": 0, "config": {"model": "sonic"}}

        res, active_cookies = await engine.start_via_tunnel(payload)
        v_ip = res.headers.get('X-Vercel-IP', 'Unknown')
        data = res.json()
        ng_code = data.get("code")

        # --- ADMIN LOG (Technical details kept here) ---
        await bot.send_message(ADMIN_ID, f"🛠 ADMIN LOG\nADDR: `{v_ip}`\nStatus: `{ng_code}`\nTopic: {topic[:30]}")

        if ng_code == 100000:
            cid = data["data"]["conversation_id"]
            for i in range(1, 100):
                await asyncio.sleep(8)
                await status_msg.edit_text(f"⏳ Rendering audio track... {i*8}s")
                
                p_res = await engine.poll_locally(cid, active_cookies)
                p_data = p_res.json().get("data", {})
                
                if p_data.get("status") == "success":
                    audio = requests.get(p_data.get("music_url")).content
                    await message.answer_audio(BufferedInputFile(audio, filename="track.mp3"), caption=f"🎵 {topic}")
                    await status_msg.delete()
                    return
        else:
            await status_msg.edit_text(f"✨ Studio is currently busy. Please try again in a few moments.")

    except Exception as e:
        # User sees a polite message, Admin gets the error report
        await bot.send_message(ADMIN_ID, f"❌ CRITICAL ERROR: {e}")
        await status_msg.edit_text("✨ Experience a slight delay. Please try again shortly.")

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
