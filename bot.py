import logging
import asyncio
import requests
import gc
from urllib.parse import quote
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BufferedInputFile

# --- 🔑 CREDENTIALS ---
API_TOKEN = '8540275734:AAHA5OKbwzhQfdmS_Y73ij9AmuQy-WG0mNM'
ADMIN_ID = 7840042951
# Your deployed Vercel URL
VERCEL_URL = "https://google-worker.vercel.app"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- 🎼 CORE LOGIC ---

@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    await message.answer(
        "🔱 **NOTEGPT INFINITY v13.0** 🔱\n\n"
        "**Status:** Vercel Serverless Engine [ACTIVE] ⚡\n\n"
        "Please enter a song topic. Our system will now generate lyrics and "
        "synthesize your track using dedicated cloud instances."
    )

@dp.message(F.text)
async def handle_music(message: types.Message):
    topic = message.text
    msg = await message.answer("🎯 **Initializing cloud instance for generation...**")
    
    try:
        # Step 1: Lyrics Generation (Hinglish/Roman priority)
        await msg.edit_text("✍️ **Composing professional lyrics...**")
        prompt = (
            f"Write professional lyrics for '{topic}'. If the song is in Hindi, "
            f"use ROMAN HINDI (Hinglish) only (e.g., 'Kahani suno'). "
            f"Structure: [Verse 1], [Chorus], [Verse 2], [Bridge], [Outro]. "
            f"Max 280 words. Plain text."
        )
        lyric_res = await asyncio.to_thread(requests.get, f"https://text.pollinations.ai/{quote(prompt)}", timeout=15)
        lyrics = lyric_res.text
        
        # Displaying lyrics in a copyable code block
        await message.answer(f"📝 **Generated Lyrics for: {topic}**\n\n```\n{lyrics}\n```")

        # Step 2: Triggering the Vercel Music Engine
        await msg.edit_text("🎼 **Vercel Engine: Processing audio synthesis...**")
        gen_payload = {"topic": topic, "lyrics": lyrics}
        gen_req = await asyncio.to_thread(requests.post, f"{VERCEL_URL}/generate", json=gen_payload, timeout=25)
        data = gen_req.json()

        if data.get("code") == 100000:
            cid = data["data"]["conversation_id"]
            await msg.edit_text("🎼 **Studio Rendering: Finalizing your track...**")
            
            # Step 3: Fast Polling via Vercel Worker
            for attempt in range(40):
                await asyncio.sleep(8)
                status_res = await asyncio.to_thread(requests.get, f"{VERCEL_URL}/status?cid={cid}", timeout=15)
                s_data = status_res.json().get("data", {})
                
                if s_data.get("status") == "success":
                    await msg.edit_text("📥 **Rendering complete. Sending file...**")
                    audio_url = s_data.get("music_url")
                    audio_content = await asyncio.to_thread(requests.get, audio_url, timeout=40)
                    
                    await message.answer_audio(
                        audio=BufferedInputFile(audio_content.content, filename=f"{topic[:10]}.mp3"),
                        caption=f"🎁 **Track:** {topic}\n⚡ High-Speed Vercel Delivery"
                    )
                    await msg.delete()
                    return
                
                elif s_data.get("status") == "failed":
                    await msg.edit_text("❌ **Synthesis Failed.** The AI engine encountered an error. Please try a different topic.")
                    return
        else:
            error_msg = data.get("message", "Unknown Server Error")
            await msg.edit_text(f"❌ **Engine Exception:** {error_msg}")

    except Exception as e:
        logging.error(f"System Error: {e}")
        await msg.edit_text("⚠️ **Connection Timeout.** The serverless instance is rebooting. Please resend your topic in a few moments.")
    finally:
        gc.collect()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
