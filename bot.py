import asyncio
import requests
import random
import uuid
import time
from urllib.parse import quote
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BufferedInputFile
from aiogram.exceptions import TelegramBadRequest

# --- 🔑 CONFIG ---
API_TOKEN = '8540275734:AAHA5OKbwzhQfdmS_Y73ij9AmuQy-WG0mNM'
ADMIN_ID = 7840042951
VERCEL_URL = "https://google-worker.vercel.app/api" 

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

class HybridEngine:
    def get_headers(self):
        return {
            'User-Agent': "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            'Origin': 'https://notegpt.io',
            'Referer': 'https://notegpt.io/ai-music-generator',
            'X-Requested-With': 'XMLHttpRequest'
        }

    async def start_via_tunnel(self, payload, cookies):
        """Forces Vercel IP rotation using unique paths."""
        headers = self.get_headers()
        # Unique path forces Vercel to spin up a fresh Lambda instance
        force_fresh_path = uuid.uuid4().hex
        data = {
            "url": "https://notegpt.io/api/v2/music/generate",
            "method": "POST",
            "payload": payload,
            "cookies": cookies,
            "headers": headers
        }
        target = f"{VERCEL_URL}/{force_fresh_path}?t={time.time()}"
        return await asyncio.to_thread(requests.post, target, json=data, timeout=35)

    async def poll_locally(self, cid, cookies):
        """Fast polling directly from bot server."""
        url = f"https://notegpt.io/api/v2/music/status?conversation_id={cid}"
        return await asyncio.to_thread(requests.get, url, headers=self.get_headers(), cookies=cookies, timeout=15)

engine = HybridEngine()

async def safe_edit(message: types.Message, text: str):
    try:
        await message.edit_text(f"{text}\n\n🕒 {time.strftime('%H:%M:%S')}")
    except: pass

@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    welcome_text = (
        "✨ Welcome to Songify AI Assistant ✨\n\n"
        "Transform your creative ideas into studio-quality music instantly. "
        "I can generate lyrics in any language (transliterated) and compose high-fidelity tracks for you.\n\n"
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
        # 1. GENERATE LYRICS (STRICT TRANSLITERATION)
        p = (
            f"Write professional song lyrics about '{topic}'. "
            "STRICT INSTRUCTION: Write ONLY in English/Latin characters (Transliteration). "
            "Structure: [Verse], [Chorus]. Plain text only. No JSON or reasoning."
        )
        ly_url = f"https://text.pollinations.ai/{quote(p)}?model=openai&cache=false"
        raw_output = (await asyncio.to_thread(requests.get, ly_url)).text
        
        # Filter reasoning
        lyrics = raw_output.split("\n")[-1] if "reasoning_content" in raw_output else raw_output
        if len(lyrics) < 20: lyrics = raw_output # Fallback
        
        await message.answer(f"📜 Lyrics:\n\n{lyrics[:3500]}")

        # 2. START STUDIO (VIA TUNNEL)
        await safe_edit(status_msg, "🚀 Bypassing limits & rotating IP...")
        anon_id = str(uuid.uuid4())
        cookies = {'anonymous_user_id': anon_id, 'is_accepted_terms': '1'}
        payload = {"prompt": f"{topic} studio quality", "lyrics": lyrics[:2000], "duration": 0, "config": {"model": "sonic"}}

        res = await engine.start_via_tunnel(payload, cookies)
        v_ip = res.headers.get('X-Vercel-IP', 'Unknown')
        v_reg = res.headers.get('X-Vercel-Region', 'Unknown')
        data = res.json()

        if data.get("code") == 100000:
            cid = data["data"]["conversation_id"]
            await bot.send_message(ADMIN_ID, f"✅ SUCCESS\nIP: {v_ip}\nRegion: {v_reg}\nCID: {cid}")
            
            # 3. FAST POLLING
            start_time = time.time()
            for i in range(1, 120):
                await asyncio.sleep(8)
                elapsed = int(time.time() - start_time)
                await safe_edit(status_msg, f"⏳ Studio Rendering...\n`{'▓'*(i//6)}` {elapsed}s")
                
                p_res = await engine.poll_locally(cid, cookies)
                s_data = p_res.json().get("data", {})
                
                if s_data.get("status") == "success":
                    await status_msg.edit_text("✨ Finalizing...")
                    audio = (await asyncio.to_thread(requests.get, s_data.get("music_url"))).content
                    await message.answer_audio(BufferedInputFile(audio, filename="track.mp3"), caption=f"🎵 {topic}")
                    await status_msg.delete()
                    return
        else:
            await safe_edit(status_msg, f"❌ Error {data.get('code')}: {data.get('msg')}")

    except Exception as e:
        await bot.send_message(ADMIN_ID, f"❌ ERROR: {e}")
        await safe_edit(status_msg, "❌ Something went wrong.")

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
