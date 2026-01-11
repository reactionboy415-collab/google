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
    def get_fresh_identity(self):
        fake_ip = f"{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}"
        anon_id = str(uuid.uuid4())
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'X-Forwarded-For': fake_ip,
            'Origin': 'https://notegpt.io',
            'Referer': 'https://notegpt.io/ai-music-generator',
            'X-Requested-With': 'XMLHttpRequest'
        }
        cookies = {'anonymous_user_id': anon_id, 'is_accepted_terms': '1'}
        return headers, cookies

    async def start_via_tunnel(self, payload):
        headers, cookies = self.get_fresh_identity()
        force_fresh_path = uuid.uuid4().hex
        data = {
            "url": "https://notegpt.io/api/v2/music/generate",
            "method": "POST",
            "payload": payload,
            "cookies": cookies,
            "headers": headers
        }
        target = f"{VERCEL_URL}/{force_fresh_path}?t={time.time()}"
        # Using a longer timeout to account for Vercel spin-up
        return await asyncio.to_thread(requests.post, target, json=data, timeout=45), cookies

    async def poll_locally(self, cid, cookies):
        url = f"https://notegpt.io/api/v2/music/status?conversation_id={cid}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        return await asyncio.to_thread(requests.get, url, headers=headers, cookies=cookies, timeout=15)

engine = HybridEngine()

async def safe_edit(message: types.Message, text: str):
    try:
        await message.edit_text(f"{text}\n\n🕒 {time.strftime('%H:%M:%S')}")
    except: pass

@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    welcome_text = (
        "✨ Welcome to Songify AI Assistant ✨\n\n"
        "Transform your creative ideas into music instantly.\n\n"
        "🚀 Send your prompt below to start."
    )
    await message.answer(welcome_text)

@dp.message(F.text)
async def handle_music(message: types.Message):
    if message.text.startswith("/"): return
    
    user_info = f"User: {message.from_user.full_name} (@{message.from_user.username})"
    topic = message.text
    status_msg = await message.answer("✍️ Drafting lyrics...")
    
    try:
        # 1. LYRICS GENERATION
        p = f"Write song lyrics about '{topic}'. Transliterated Hindi/English characters. [Verse], [Chorus]."
        ly_url = f"https://text.pollinations.ai/{quote(p)}?model=openai&cache=false"
        lyrics = (await asyncio.to_thread(requests.get, ly_url)).text
        await message.answer(f"📜 Lyrics:\n\n{lyrics[:3500]}")

        # 2. START STUDIO
        await safe_edit(status_msg, "🚀 Rotating identity & bypassing limits...")
        payload = {"prompt": f"{topic} studio quality", "lyrics": lyrics[:2000], "duration": 0, "config": {"model": "sonic"}}

        res, active_cookies = await engine.start_via_tunnel(payload)
        v_ip = res.headers.get('X-Vercel-IP', 'Unknown')
        v_reg = res.headers.get('X-Vercel-Region', 'Unknown')
        
        try:
            data = res.json()
            ng_code = data.get("code")
            ng_msg = data.get("msg", "No message")
        except:
            data = {}
            ng_code = "PARSE_ERROR"
            ng_msg = res.text[:100]

        # --- ADMIN LOG (START ATTEMPT) ---
        log_text = (
            f"🛠 **ADMIN LOG: GENERATION ATTEMPT**\n"
            f"👤 {user_info}\n"
            f"🌐 IP: `{v_ip}` | Region: `{v_reg}`\n"
            f"📊 Code: `{ng_code}`\n"
            f"💬 Msg: {ng_msg}\n"
            f"📝 Topic: {topic[:100]}"
        )
        await bot.send_message(ADMIN_ID, log_text)

        if ng_code == 100000:
            cid = data["data"]["conversation_id"]
            
            # 3. FAST POLLING
            for i in range(1, 120):
                await asyncio.sleep(8)
                await safe_edit(status_msg, f"⏳ Studio Rendering audio... {i*8}s")
                
                p_res = await engine.poll_locally(cid, active_cookies)
                p_data = p_res.json()
                s_data = p_data.get("data", {})
                status = s_data.get("status")
                
                if status == "success":
                    audio_url = s_data.get("music_url")
                    audio = (await asyncio.to_thread(requests.get, audio_url)).content
                    await message.answer_audio(BufferedInputFile(audio, filename="track.mp3"), caption=f"🎵 {topic}")
                    await status_msg.delete()
                    
                    # --- ADMIN LOG (SUCCESS) ---
                    await bot.send_message(ADMIN_ID, f"✅ **SUCCESSFUL RENDER**\nTopic: {topic[:50]}\nCID: `{cid}`")
                    return
                
                elif status == "failed":
                    await safe_edit(status_msg, "❌ Studio failed to render audio.")
                    await bot.send_message(ADMIN_ID, f"⚠️ **RENDER FAILED**\nTopic: {topic[:50]}\nCID: `{cid}`")
                    return
        else:
            await safe_edit(status_msg, f"❌ Studio Busy (Error {ng_code}). Please try again.")

    except Exception as e:
        error_msg = (
            f"❌ **CRITICAL SYSTEM ERROR**\n"
            f"👤 {user_info}\n"
            f"⚠️ Error: `{str(e)}`"
        )
        await bot.send_message(ADMIN_ID, error_msg)
        await safe_edit(status_msg, "❌ A technical error occurred. Admin has been notified.")

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
