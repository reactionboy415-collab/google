import logging
import asyncio
import requests
import random
import uuid
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BufferedInputFile

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
        data = {"url": url, "method": method, "payload": payload, "cookies": cookies, "headers": headers}
        return await asyncio.to_thread(requests.post, VERCEL_URL, json=data, timeout=45)

@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    welcome_text = (
        "🎵 **Welcome to Songify AI** 🎵\n\n"
        "I can transform your ideas into professional studio-quality music.\n\n"
        "⌨️ **Just send me a topic or prompt to begin.**"
    )
    await message.answer(welcome_text)

@dp.message(F.text)
async def handle_music(message: types.Message):
    if message.text.startswith("/"): return
    
    engine = UnlimitedFireEngine()
    topic = message.text
    # Professional user-facing message
    status_msg = await message.answer("✍️ **Writing lyrics for your masterpiece...**")
    
    try:
        # 1. Lyrics Generation
        lyric_prompt = f"Write professional song lyrics about '{topic}'. Structure with [Verse] and [Chorus]. Match the input language."
        lyric_res = requests.get(f"https://text.pollinations.ai/{requests.utils.quote(lyric_prompt)}", timeout=15)
        lyrics = lyric_res.text

        # 2. Music Generation (Silent Tunneling)
        await status_msg.edit_text("🎸 **Composing music in the studio...**")
        anon_id = str(uuid.uuid4())
        cookies = {'anonymous_user_id': anon_id, 'is_accepted_terms': '1'}
        payload = {
            "prompt": f"{topic} studio quality, high fidelity",
            "lyrics": lyrics[:2000],
            "duration": 0,
            "config": {"model": "sonic"}
        }

        res = await engine.tunnel_call("https://notegpt.io/api/v2/music/generate", payload=payload, cookies=cookies)
        
        # 🕵️ SILENT ADMIN LOGGING
        scraped_ip = res.headers.get('X-Vercel-IP', 'Unknown')
        log_text = f"🛠 **ADMIN LOG**\nUser: {message.from_user.full_name}\nTopic: {topic}\nIP: `{scraped_ip}`\nStatus: {res.status_code}"
        await bot.send_message(ADMIN_ID, log_text)

        if res.status_code == 200:
            data = res.json()
            if data.get("code") == 100000:
                cid = data["data"]["conversation_id"]
                
                # 3. Polling with professional updates
                for i in range(1, 41):
                    await asyncio.sleep(10)
                    # Visual progress for user
                    progress = "▓" * (i // 4) + "░" * (10 - (i // 4))
                    await status_msg.edit_text(f"🎼 **Processing your track...**\n`{progress}`")
                    
                    poll_res = await engine.tunnel_call(f"https://notegpt.io/api/v2/music/status?conversation_id={cid}", method="GET", cookies=cookies)
                    
                    if poll_res.status_code == 200:
                        s_data = poll_res.json().get("data", {})
                        if s_data.get("status") == "success":
                            await status_msg.edit_text("✨ **Finishing touches applied!**")
                            audio_url = s_data.get("music_url")
                            audio_content = requests.get(audio_url).content
                            
                            await message.answer_audio(
                                audio=BufferedInputFile(audio_content, filename=f"{topic[:15]}.mp3"),
                                caption=f"✅ **Generated successfully!**\n🎬 **Topic:** {topic}\n\nHope you like it!"
                            )
                            await status_msg.delete()
                            return
            else:
                await status_msg.edit_text("❌ **Sorry, the studio is currently busy.** Please try again in a moment.")
        else:
            await status_msg.edit_text("⚠️ **Connection hiccup.** Retrying your request...")

    except Exception as e:
        logging.error(f"Error: {e}")
        await status_msg.edit_text("❌ **An error occurred.** Please try a different prompt.")

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
