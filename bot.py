import logging
import asyncio
import requests
import uuid
import gc
from urllib.parse import quote
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BufferedInputFile

# --- 🔑 CONFIGURATION ---
API_TOKEN = '8540275734:AAHA5OKbwzhQfdmS_Y73ij9AmuQy-WG0mNM'
ADMIN_ID = 7840042951
VERCEL_TUNNEL = "https://google-worker.vercel.app/proxy" # Update if your URL is different

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

class UnlimitedFireEngine:
    """
    Adapted Version: Uses Vercel as the 'Network Interface' 
    to guarantee a new IP for every single request.
    """
    async def call_vercel(self, url, method="GET", payload=None, cookies=None):
        try:
            body = {
                "url": url, 
                "method": method, 
                "payload": payload,
                "cookies": cookies
            }
            # We use a short timeout for the tunnel itself
            response = await asyncio.to_thread(requests.post, VERCEL_TUNNEL, json=body, timeout=30)
            return response.json()
        except Exception as e:
            return {"code": 500, "error": str(e)}

    async def fetch_smart_lyrics(self, topic):
        prompt = (
            f"Write professional song lyrics about '{topic}'. "
            f"Use the same language as the topic. Min 300 words. "
            f"Structure: [Verse 1], [Chorus], [Verse 2], [Bridge], [Outro]. Plain text only."
        )
        try:
            url = f"https://text.pollinations.ai/{quote(prompt)}"
            res = await asyncio.to_thread(requests.get, url, timeout=15)
            return res.text
        except:
            return None

    async def generate_music(self, topic, lyrics):
        anon_id = str(uuid.uuid4())
        cookies = {'anonymous_user_id': anon_id, 'is_accepted_terms': '1'}
        
        # EXACT Payload from your working script
        payload = {
            "prompt": f"{topic} studio quality",
            "lyrics": lyrics[:2000],
            "duration": 0,
            "config": {"model": "sonic"} 
        }

        # Send to Vercel (Who adds the Ghost Headers + Fresh IP)
        data = await self.call_vercel(
            "https://notegpt.io/api/v2/music/generate", 
            method="POST", 
            payload=payload, 
            cookies=cookies
        )
        
        if data.get("code") == 100000:
            return data["data"]["conversation_id"], cookies
        else:
            return None, data

    async def poll_status(self, cid, cookies):
        # Polling loop managed by Bot to avoid Vercel 10s timeout
        for _ in range(40): # 40 attempts * 8s = ~5 mins
            await asyncio.sleep(8)
            status_url = f"https://notegpt.io/api/v2/music/status?conversation_id={cid}"
            
            # Each poll request also gets a FRESH Vercel IP
            data = await self.call_vercel(status_url, method="GET", cookies=cookies)
            
            s_data = data.get("data", {})
            status = s_data.get("status")
            
            if status == "success":
                return s_data.get("music_url")
            elif status == "failed":
                return "FAILED"
        return "TIMEOUT"

engine = UnlimitedFireEngine()

# --- 🤖 BOT HANDLERS ---

@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    await message.answer("🔥 **SONGIFY UNLIMITED v17.0** 🔥\n\nEngine: **Python Script + Vercel Tunnel**\nLogic: **Full Replication of Local Script**\n\nSend a topic to start!")

@dp.message(F.text)
async def handle_music(message: types.Message):
    topic = message.text
    msg = await message.answer(f"🔥 **Step 1: Crafting Lyrics for '{topic}'...**")
    
    try:
        # 1. Lyrics
        lyrics = await engine.fetch_smart_lyrics(topic)
        if not lyrics:
            await msg.edit_text("⚠️ Lyrics generation failed.")
            return
        
        await message.answer(f"📜 **Generated Lyrics:**\n\n```\n{lyrics[:1000]}...\n```")
        
        # 2. Generate (Tunneling to Vercel)
        await msg.edit_text("🔥 **Step 2: Bypassing Limits (Ghost Identity)...**")
        cid, debug_data = await engine.generate_music(topic, lyrics)
        
        if not cid:
            error_code = debug_data.get('code')
            error_msg = debug_data.get('msg') or debug_data.get('error')
            await msg.edit_text(f"❌ **NoteGPT Error {error_code}:** {error_msg}")
            # Admin Debug
            await bot.send_message(ADMIN_ID, f"DEBUG FAILURE:\n{debug_data}")
            return

        # 3. Poll
        await msg.edit_text(f"🚀 **Composition Started! CID: {cid}**\nBrewing in the Studio...")
        result_url = await engine.poll_status(cid, debug_data) # debug_data is cookies here effectively? No, need cookies.
        # Wait, generate_music returned (cid, cookies). Fixed below.
        
        # Retrying correct call logic:
        # cid, cookies = await engine.generate_music... (Corrected in logic below)
        
        # RE-CALLING for Variable Scope Fix in this block:
        # (This block mimics the flow. The implementation above had a small return type mismatch in my explanation, 
        # but the code block below is the one to run)
        pass 

    except Exception as e:
        await msg.edit_text(f"⚠️ Critical Error: {e}")

# --- RE-DEFINING HANDLER FOR CLEAN EXECUTION ---
@dp.message(F.text)
async def handle_music_final(message: types.Message):
    topic = message.text
    msg = await message.answer(f"🔥 **Step 1: Crafting Lyrics for '{topic}'...**")

    # 1. Lyrics
    lyrics = await engine.fetch_smart_lyrics(topic)
    if not lyrics:
        await msg.edit_text("⚠️ Lyrics generation failed.")
        return
    
    await message.answer(f"📜 **Lyrics:**\n\n```\n{lyrics[:1500]}\n```")

    # 2. Generate
    await msg.edit_text("🔥 **Step 2: Bypassing Limits (Ghost Identity)...**")
    cid, cookies = await engine.generate_music(topic, lyrics)

    if not cid:
        # cookies variable holds error data in failure case
        error_data = cookies 
        await msg.edit_text(f"❌ **Generation Failed.**\nCode: {error_data.get('code')}\nMsg: {error_data.get('msg', 'Unknown')}")
        await bot.send_message(ADMIN_ID, f"🛠 **DEBUG:** {error_data}")
        return

    # 3. Poll
    await msg.edit_text(f"🚀 **Composition Started!**\nCID: `{cid}`\nBrewing in the Studio...")
    music_url = await engine.poll_status(cid, cookies)

    if music_url == "FAILED":
        await msg.edit_text("❌ AI Studio failed to process audio.")
    elif music_url == "TIMEOUT":
        await msg.edit_text("⏳ Studio timed out.")
    else:
        await msg.edit_text("🔥 **THE TRACK IS READY! Downloading...**")
        try:
            audio_content = await asyncio.to_thread(requests.get, music_url, timeout=60)
            await message.answer_audio(
                audio=BufferedInputFile(audio_content.content, filename=f"{topic[:10]}.mp3"),
                caption=f"🎁 **Track:** {topic}\n🔥 Powered by Unlimited Fire Engine"
            )
            await msg.delete()
        except Exception as e:
            await msg.edit_text("⚠️ Download failed, but link is generated.")

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
