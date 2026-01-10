import logging
import asyncio
import requests
import random
import uuid
import time
from urllib.parse import quote
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BufferedInputFile
from aiogram.exceptions import TelegramBadRequest

# --- 🔑 CONFIGURATION ---
API_TOKEN = '8540275734:AAHA5OKbwzhQfdmS_Y73ij9AmuQy-WG0mNM'
ADMIN_ID = 7840042951
VERCEL_URL = "https://google-worker.vercel.app/api" 

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

class UnlimitedFireEngine:
    def get_ghost_headers(self):
        fake_ip = f"{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}"
        return {
            'User-Agent': "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            'X-Forwarded-For': fake_ip,
            'Origin': 'https://notegpt.io',
            'Referer': 'https://notegpt.io/ai-music-generator',
            'X-Requested-With': 'XMLHttpRequest'
        }

    async def tunnel_call(self, url, method="POST", payload=None, cookies=None):
        headers = self.get_ghost_headers()
        rid = f"{uuid.uuid4().hex[:8]}"
        data = {"url": url, "method": method, "payload": payload, "cookies": cookies, "headers": headers}
        target = f"{VERCEL_URL}?rotate={rid}&ts={time.time()}"
        return await asyncio.to_thread(requests.post, target, json=data, timeout=50)

engine = UnlimitedFireEngine()

async def safe_edit(message: types.Message, text: str):
    """Ensures message updates are always unique to avoid Telegram's 'not modified' error."""
    try:
        # Adding a dynamic timestamp/clock makes every edit unique
        unique_text = f"{text}\n\n`Last Update: {time.strftime('%H:%M:%S')}`"
        await message.edit_text(unique_text)
    except TelegramBadRequest:
        pass 

@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    await message.answer("🎵 **Songify AI Active**\nSend me a topic and I will write the lyrics and compose the music!")

@dp.message(F.text)
async def handle_music(message: types.Message):
    if message.text.startswith("/"): return
    
    topic = message.text
    # Initial interaction
    temp_msg = await message.answer("🔍 **Searching for inspiration...**")
    
    try:
        # 1. GENERATE LYRICS FIRST
        await temp_msg.edit_text("✍️ **Writing professional lyrics...**")
        p = f"Write professional song lyrics about '{topic}'. Structure: [Verse], [Chorus], [Outro]. Match language of prompt."
        l_res = await asyncio.to_thread(requests.get, f"https://text.pollinations.ai/{quote(p)}", timeout=15)
        lyrics = l_res.text

        # 🚀 INSTANTLY GIVE LYRICS TO USER
        await message.answer(f"📝 **Lyrics for:** {topic}\n\n{lyrics}")
        
        # 2. START THE STUDIO (NoteGPT)
        await temp_msg.edit_text("🎸 **Lyrics ready! Sending to the recording studio...**")
        
        anon_id = str(uuid.uuid4())
        cookies = {'anonymous_user_id': anon_id, 'is_accepted_terms': '1'}
        payload = {
            "prompt": f"{topic} studio quality, high fidelity",
            "lyrics": lyrics[:2000],
            "duration": 0,
            "config": {"model": "sonic"}
        }

        res = await engine.tunnel_call("https://notegpt.io/api/v2/music/generate", payload=payload, cookies=cookies)
        
        # --- ADMIN DEBUG LOGGING ---
        scraped_ip = res.headers.get('X-Vercel-IP', 'Unknown')
        try:
            res_json = res.json()
            ng_code = res_json.get("code")
        except:
            ng_code = "PARSE_ERROR"

        await bot.send_message(ADMIN_ID, f"🛠 **ADMIN LOG**\nIP: `{scraped_ip}`\nNoteGPT Code: `{ng_code}`")

        if res.status_code == 200 and ng_code == 100000:
            cid = res_json["data"]["conversation_id"]
            
            # 3. POLLING (AUDIO GENERATION)
            for i in range(1, 60):
                await asyncio.sleep(8)
                
                # Visual Loading Elements
                frames = ["🌑", "🌒", "🌓", "🌔", "🌕"]
                frame = frames[i % len(frames)]
                bar = "🟩" * (i // 6) + "⬜" * (max(0, 8 - (i // 6)))
                
                await safe_edit(temp_msg, f"{frame} **Studio rendering audio...**\n`{bar}`")
                
                p_res = await engine.tunnel_call(f"https://notegpt.io/api/v2/music/status?conversation_id={cid}", method="GET", cookies=cookies)
                
                if p_res.status_code == 200:
                    s_data = p_res.json().get("data", {})
                    if s_data.get("status") == "success":
                        await temp_msg.edit_text("✅ **Track Completed!**")
                        audio_url = s_data.get("music_url")
                        audio_bytes = await asyncio.to_thread(requests.get, audio_url)
                        
                        await message.answer_audio(
                            audio=BufferedInputFile(audio_bytes.content, filename=f"{topic[:10]}.mp3"),
                            caption=f"🎵 **Track:** {topic}\n✨ *Created via Songify AI Engine*"
                        )
                        await temp_msg.delete()
                        return
                    elif s_data.get("status") == "failed":
                        await temp_msg.edit_text("❌ **Studio Error:** Rendering failed.")
                        return
        else:
            await temp_msg.edit_text("❌ **Studio is busy.** Please try again in 30s.")

    except Exception as e:
        await bot.send_message(ADMIN_ID, f"❌ **CRITICAL ERROR:** {str(e)}")
        await temp_msg.edit_text("❌ **Something went wrong.** Please try again.")

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
