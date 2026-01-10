import logging
import asyncio
import requests
import uuid
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

async def call_vercel(url, method="POST", payload=None):
    try:
        data = {"url": url, "method": method, "payload": payload}
        # Use asyncio.to_thread for blocking requests
        response = await asyncio.to_thread(requests.post, VERCEL_TUNNEL, json=data, timeout=30)
        return response.json()
    except Exception as e:
        return {"code": 500, "error": str(e)}

@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    await message.answer("🔱 **SONGIFY INFINITY v18.0** 🔱\n\nEngine: **Fire-Engine + Ghost Tunnel**\nAdmin Debug: [ENABLED] ✅")

@dp.message(F.text)
async def handle_music(message: types.Message):
    topic = message.text
    msg = await message.answer("🎯 **Step 1: Analyzing language & generating lyrics...**")
    
    try:
        # Step 1: Lyrics (Strict language matching)
        prompt = (f"Write professional song lyrics about '{topic}'. "
                  f"Detect the language of the topic and write in that same language. "
                  f"If Hindi, use Hinglish. Structure: [Verse 1], [Chorus], [Verse 2], [Bridge], [Outro].")
        lyric_res = requests.get(f"https://text.pollinations.ai/{quote(prompt)}", timeout=20)
        lyrics = lyric_res.text
        await message.answer(f"📝 **Lyrics for: {topic}**\n\n```\n{lyrics[:3000]}\n```")

        # Step 2: Music Generation (Using your optimized payload)
        await msg.edit_text("🔥 **Step 2: Sending request via Ghost IP...**")
        payload = {
            "prompt": f"{topic} studio quality",
            "lyrics": lyrics[:2000],
            "duration": 0,
            "config": {"model": "sonic"}
        }
        
        gen_data = await call_vercel("https://notegpt.io/api/v2/music/generate", "POST", payload)

        # ADMIN DEBUGGING
        if gen_data.get("code") == 999:
            debug_info = f"❌ **DEBUG FAILURE**\nStatus: {gen_data.get('status_code')}\nBody Snippet: `{gen_data.get('raw_html')}`"
            await bot.send_message(ADMIN_ID, debug_info[:4000])
            await msg.edit_text("⚠️ **IP Blocked.** NoteGPT is challenging the connection. Admin has the logs.")
            return

        if gen_data.get("code") == 100000:
            cid = gen_data["data"]["conversation_id"]
            await msg.edit_text("🎼 **Studio Rendering (Wait 40-60s)...**")
            
            # Step 3: Long Polling
            for i in range(45):
                await asyncio.sleep(10)
                status_data = await call_vercel(f"https://notegpt.io/api/v2/music/status?conversation_id={cid}", "GET")
                
                res_data = status_data.get("data", {})
                if res_data.get("status") == "success":
                    await msg.edit_text("📥 **Music Ready! Downloading...**")
                    audio_url = res_data.get("music_url")
                    audio_bytes = requests.get(audio_url, timeout=60).content
                    
                    await message.answer_audio(
                        audio=BufferedInputFile(audio_bytes, filename=f"{topic[:10]}.mp3"),
                        caption=f"🎁 **Track:** {topic}\n⚡ Unlimited Fire Engine"
                    )
                    await msg.delete()
                    return
        else:
            await bot.send_message(ADMIN_ID, f"❌ **ENGINE ERROR:** {gen_data}")
            await msg.edit_text(f"❌ **Error {gen_data.get('code')}:** {gen_data.get('msg', 'Server Busy')}")

    except Exception as e:
        await bot.send_message(ADMIN_ID, f"❗ **CRITICAL:** {str(e)}")
        await msg.edit_text("⚠️ **System Timeout.** Re-syncing instance...")

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
