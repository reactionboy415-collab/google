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
        # Random Rotation ID
        rid = f"{uuid.uuid4().hex[:6]}"
        data = {"url": url, "method": method, "payload": payload, "cookies": cookies, "headers": headers}
        # ?rotate= kills the Vercel warm-start stickiness
        target = f"{VERCEL_URL}?rotate={rid}&t={time.time()}"
        return await asyncio.to_thread(requests.post, target, json=data, timeout=55)

engine = UnlimitedFireEngine()

async def safe_edit(message: types.Message, text: str):
    try:
        # Adding a clock makes every message content unique for Telegram
        await message.edit_text(f"{text}\n\n🕒 `Update: {time.strftime('%H:%M:%S')}`")
    except TelegramBadRequest: pass

@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    await message.answer("🎵 **Songify AI Ready!**\nSend me a topic to start.")

@dp.message(F.text)
async def handle_music(message: types.Message):
    if message.text.startswith("/"): return
    
    topic = message.text
    status_msg = await message.answer("✍️ **Writing Lyrics...**")
    
    try:
        # 1. FETCH LYRICS
        p = f"Write professional song lyrics about '{topic}'. Structure: [Verse], [Chorus]. Plain text."
        l_res = requests.get(f"https://text.pollinations.ai/{quote(p)}", timeout=15)
        lyrics = l_res.text

        # 🚀 INSTANTLY GIVE LYRICS
        await message.answer(f"📜 **LYRICS GENERATED:**\n\n{lyrics}")
        await safe_edit(status_msg, "🎸 **Lyrics delivered! Starting Studio session...**")

        # 2. GENERATE MUSIC
        anon_id = str(uuid.uuid4())
        cookies = {'anonymous_user_id': anon_id, 'is_accepted_terms': '1'}
        payload = {"prompt": f"{topic} studio quality", "lyrics": lyrics[:2000], "duration": 0, "config": {"model": "sonic"}}

        res = await engine.tunnel_call("https://notegpt.io/api/v2/music/generate", payload=payload, cookies=cookies)
        
        # 🕵️ ADMIN IP LOG
        scraped_ip = res.headers.get('X-Vercel-IP', 'Unknown')
        res_json = res.json()
        ng_code = res_json.get("code")
        await bot.send_message(ADMIN_ID, f"🛠 **LOG**\nIP: `{scraped_ip}`\nCode: `{ng_code}`")

        if res.status_code == 200 and ng_code == 100000:
            cid = res_json["data"]["conversation_id"]
            
            # 3. POLLING (With 15 Min Timeout)
            for i in range(1, 91): # 90 attempts * 10s = 15 minutes
                await asyncio.sleep(10)
                
                # Visual Bar
                bar = "🟩" * (i // 9) + "⬜" * (max(0, 10 - (i // 9)))
                await safe_edit(status_msg, f"⏳ **Studio Rendering...**\n`{bar}`\n⏱ Time: {i*10}s")
                
                p_res = await engine.tunnel_call(f"https://notegpt.io/api/v2/music/status?conversation_id={cid}", method="GET", cookies=cookies)
                
                if p_res.status_code == 200:
                    s_data = p_res.json().get("data", {})
                    if s_data.get("status") == "success":
                        await status_msg.edit_text("✨ **Mixing complete! Sending file...**")
                        audio_url = s_data.get("music_url")
                        audio_bytes = requests.get(audio_url).content
                        
                        await message.answer_audio(
                            audio=BufferedInputFile(audio_bytes, filename=f"song.mp3"),
                            caption=f"🎵 **Topic:** {topic}\n✅ Generated successfully!"
                        )
                        await status_msg.delete()
                        return
        else:
            await safe_edit(status_msg, f"❌ **Error:** NoteGPT rejected request ({ng_code}). Try again in 1 min.")

    except Exception as e:
        await bot.send_message(ADMIN_ID, f"❌ **ERROR:** {str(e)}")
        await status_msg.edit_text("❌ Something went wrong. Try a shorter prompt.")

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
