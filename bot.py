import logging
import asyncio
import requests
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

async def send_debug(error_msg):
    """Sends raw server logs directly to Admin"""
    try:
        await bot.send_message(ADMIN_ID, f"🛠 **DEBUG LOG:**\n\n`{error_msg}`")
    except: pass

@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    await message.answer("🔱 **SONGIFY INFINITY v15.0** 🔱\n\nAdmin Debugging: [ON] ✅\nCloud Instance: [READY] ⚡")

@dp.message(F.text)
async def handle_music(message: types.Message):
    topic = message.text
    msg = await message.answer("🎯 **Instance connection in progress...**")
    
    try:
        # Step 1: Lyrics
        prompt = f"Write professional lyrics for '{topic}'. If Hindi, use Hinglish. Structure: [Verse 1], [Chorus], [Verse 2], [Bridge], [Outro]."
        lyric_res = requests.get(f"https://text.pollinations.ai/{quote(prompt)}", timeout=15)
        lyrics = lyric_res.text
        await message.answer(f"📝 **Lyrics for: {topic}**\n\n```\n{lyrics}\n```")

        # Step 2: Request Music
        await msg.edit_text("🎼 **Triggering NoteGPT via Vercel...**")
        response = requests.post(f"{VERCEL_URL}/generate", json={"topic": topic, "lyrics": lyrics}, timeout=25)
        debug_data = response.json()

        # Check if NoteGPT accepted the request
        if debug_data.get("status_code") == 200 and debug_data.get("json", {}).get("code") == 100000:
            cid = debug_data["json"]["data"]["conversation_id"]
            await msg.edit_text("🎼 **Studio Rendering...**")
            
            for i in range(50): 
                await asyncio.sleep(8)
                status_res = requests.get(f"{VERCEL_URL}/status?cid={cid}", timeout=10)
                s_data = status_res.json().get("data", {})
                
                if s_data.get("status") == "success":
                    await msg.edit_text("📥 **Sending high-quality MP3...**")
                    audio = requests.get(s_data.get("music_url"), timeout=60)
                    await message.answer_audio(
                        audio=BufferedInputFile(audio.content, filename=f"{topic[:10]}.mp3"),
                        caption=f"🎁 **Track:** {topic}\n⚡ Unlimited Cloud Mode"
                    )
                    await msg.delete()
                    return
        else:
            # SEND DEBUG TO ADMIN
            await send_debug(f"Topic: {topic}\nResponse: {debug_data}")
            await msg.edit_text("⚠️ **System Busy.** The engine encountered a block. Admin has been notified.")

    except Exception as e:
        await send_debug(f"CRITICAL ERROR: {str(e)}")
        await msg.edit_text("⚠️ **Connection Timeout.** Re-attempting in a few moments...")

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
