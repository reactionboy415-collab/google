import logging
import asyncio
import requests
import uuid
import gc
from urllib.parse import quote
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BufferedInputFile

# --- 🔑 CREDENTIALS ---
API_TOKEN = '8540275734:AAHA5OKbwzhQfdmS_Y73ij9AmuQy-WG0mNM'
ADMIN_ID = 7840042951
VERCEL_TUNNEL = "https://google-worker.vercel.app/proxy"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

async def call_engine(url, method="POST", payload=None):
    """Routes the request through Vercel for IP rotation"""
    try:
        data = {"url": url, "method": method, "payload": payload}
        response = requests.post(VERCEL_TUNNEL, json=data, timeout=30)
        return response.json()
    except Exception as e:
        return {"error": str(e), "code": 500}

@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    await message.answer("🚀 **SONGIFY UNLIMITED v16.0** 🚀\n\nEngine: **Vercel Ghost-Tunnel**\nStatus: **Stable**\n\nEnter any topic to generate high-quality audio.")

@dp.message(F.text)
async def handle_music(message: types.Message):
    topic = message.text
    msg = await message.answer("🔥 **Step 1: Crafting Lyrics...**")
    
    try:
        # Step 1: Lyrics (Same as your script)
        prompt = (f"Write professional song lyrics about '{topic}'. Use the same language as the topic. "
                  f"Min 300 words. Structure: [Verse 1], [Chorus], [Verse 2], [Bridge], [Outro]. Plain text.")
        lyric_res = requests.get(f"https://text.pollinations.ai/{quote(prompt)}", timeout=20)
        lyrics = lyric_res.text
        await message.answer(f"📝 **Lyrics:**\n\n```\n{lyrics[:3500]}\n```")

        # Step 2: Generate Music through Vercel Tunnel
        await msg.edit_text("🔥 **Step 2: Bypassing Limits (Ghost Identity)...**")
        gen_payload = {
            "prompt": f"{topic} studio quality",
            "lyrics": lyrics[:2000],
            "duration": 0,
            "config": {"model": "sonic"}
        }
        
        gen_data = await call_engine("https://notegpt.io/api/v2/music/generate", "POST", gen_payload)

        if gen_data.get("code") == 100000:
            cid = gen_data["data"]["conversation_id"]
            await msg.edit_text(f"🚀 **Composition Started!**\nStudio Rendering (Approx 60s)...")
            
            # Step 3: Polling Status (Admin Debugging included)
            for i in range(40):
                await asyncio.sleep(10)
                status_url = f"https://notegpt.io/api/v2/music/status?conversation_id={cid}"
                status_data = await call_engine(status_url, "GET")
                
                res_data = status_data.get("data", {})
                status = res_data.get("status")
                
                if status == "success":
                    await msg.edit_text("📥 **THE TRACK IS READY! Downloading...**")
                    audio_url = res_data.get("music_url")
                    audio_content = requests.get(audio_url, timeout=60).content
                    
                    await message.answer_audio(
                        audio=BufferedInputFile(audio_content, filename=f"{topic[:15]}.mp3"),
                        caption=f"🎁 **Topic:** {topic}\n⚡ Unlimited Fire Engine"
                    )
                    await msg.delete()
                    return
                elif status == "failed":
                    await msg.edit_text("❌ AI Studio failed to process audio.")
                    return
        else:
            # Handle error code 164001 or others
            error_code = gen_data.get("code")
            await msg.edit_text(f"❌ **NoteGPT Error {error_code}**\nEngine reset required.")
            await bot.send_message(ADMIN_ID, f"DEBUG Error {error_code}: {gen_data}")

    except Exception as e:
        logging.error(f"Engine Error: {e}")
        await msg.edit_text("⚠️ **Connection Timeout.** Instance is refreshing.")
    finally:
        gc.collect()

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
