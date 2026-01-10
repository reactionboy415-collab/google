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
VERCEL_URL = "https://google-worker.vercel.app"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    await message.answer(
        "🔱 **SONGIFY INFINITY v14.5** 🔱\n\n"
        "**Multi-Language Engine:** [ENABLED] 🌍\n"
        "**Cloud Status:** [STABLE] ⚡\n\n"
        "Send me a topic in any language (English, Hindi, Spanish, etc.). "
        "I will detect the language and generate professional lyrics accordingly!"
    )

@dp.message(F.text)
async def handle_music(message: types.Message):
    topic = message.text
    msg = await message.answer("🎯 **Analyzing language and preparing instance...**")
    
    try:
        # Step 1: Dynamic Multilingual Lyrics Generation
        await msg.edit_text("✍️ **Composing lyrics in your preferred language...**")
        
        # New smarter prompt: Detects user intent and sets language accordingly
        prompt = (
            f"Write professional song lyrics for the topic: '{topic}'. "
            "INSTRUCTIONS: "
            "1. Detect the language of the topic and write lyrics in that SAME language. "
            "2. If the user asks in English, use English. "
            "3. If the user asks in Hindi, use ROMAN HINDI (Hinglish). "
            "4. For other languages, use their standard Roman/Latin script. "
            "Structure: [Verse 1], [Chorus], [Verse 2], [Bridge], [Outro]. "
            "Max 280 words. Plain text only."
        )
        
        lyric_res = requests.get(f"https://text.pollinations.ai/{quote(prompt)}", timeout=20)
        lyrics = lyric_res.text
        
        await message.answer(f"📝 **Lyrics for: {topic}**\n\n```\n{lyrics}\n```")

        # Step 2: Request Music Generation via Vercel
        await msg.edit_text("🎼 **Starting Music Synthesis...**")
        gen_req = requests.post(f"{VERCEL_URL}/generate", json={"topic": topic, "lyrics": lyrics}, timeout=25)
        data = gen_req.json()

        if data.get("code") == 100000:
            cid = data["data"]["conversation_id"]
            await msg.edit_text("🎼 **AI Studio is rendering your track...**")
            
            # Step 3: Polling Loop
            for i in range(60): 
                await asyncio.sleep(7)
                try:
                    status_res = requests.get(f"{VERCEL_URL}/status?cid={cid}", timeout=15)
                    s_data = status_res.json().get("data", {})
                    
                    if s_data.get("status") == "success":
                        await msg.edit_text("📥 **Rendering Finished! Sending file...**")
                        audio = requests.get(s_data.get("music_url"), timeout=60)
                        
                        await message.answer_audio(
                            audio=BufferedInputFile(audio_content=audio.content, filename=f"{topic[:10]}.mp3"),
                            caption=f"🎁 **Composition:** {topic}\n⚡ Global Multilingual Engine"
                        )
                        await msg.delete()
                        return
                    elif s_data.get("status") == "failed":
                        await msg.edit_text("❌ **Studio Error:** Generation failed.")
                        return
                except Exception as e:
                    logging.error(f"Polling error: {e}")
                    continue 
            
            await msg.edit_text("⏳ **Timeout:** The studio is taking too long. Please try again later.")
        else:
            await msg.edit_text(f"❌ **Engine Error:** {data.get('message', 'Server Busy')}")

    except Exception as e:
        logging.error(f"Global Error: {e}")
        await msg.edit_text("⚠️ **System Busy.** Instance reset initiated. Please resend the topic.")
    finally:
        gc.collect()

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
