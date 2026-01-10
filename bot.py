import logging
import asyncio
import requests
import random
import uuid
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BufferedInputFile

# --- 🔑 CREDENTIALS ---
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
        data = {
            "url": url,
            "method": method,
            "payload": payload,
            "cookies": cookies,
            "headers": headers
        }
        # Call Vercel and return the full response object
        return await asyncio.to_thread(requests.post, VERCEL_URL, json=data, timeout=40)

@dp.message(F.text)
async def handle_music(message: types.Message):
    engine = UnlimitedFireEngine()
    topic = message.text
    status_msg = await message.answer("🧪 **Step 1: Lyrics & Tunnel Sync...**")
    
    try:
        # Step 1: Lyrics
        lyric_prompt = f"Write professional lyrics for '{topic}'. Match the language of the topic. If Hindi, use Hinglish."
        lyric_res = requests.get(f"https://text.pollinations.ai/{requests.utils.quote(lyric_prompt)}", timeout=15)
        lyrics = lyric_res.text
        
        # Step 2: Generation via Tunnel
        await status_msg.edit_text("🔥 **Step 2: Ghost IP Composition...**")
        anon_id = str(uuid.uuid4())
        cookies = {'anonymous_user_id': anon_id, 'is_accepted_terms': '1'}
        payload = {
            "prompt": f"{topic} studio quality",
            "lyrics": lyrics[:2000],
            "duration": 0,
            "config": {"model": "sonic"}
        }

        # Passing through the Vercel IP Scraper
        res = await engine.tunnel_call("https://notegpt.io/api/v2/music/generate", payload=payload, cookies=cookies)
        
        # 🕵️ Send the "Scraped Proxy" IP to Admin
        scraped_ip = res.headers.get('X-Vercel-IP', 'Unknown')
        await bot.send_message(ADMIN_ID, f"📡 **Tunnel Active**\nTarget: NoteGPT\nScraped IP (Vercel): `{scraped_ip}`\nStatus: {res.status_code}")

        if res.status_code == 200:
            data = res.json()
            if data.get("code") == 100000:
                cid = data["data"]["conversation_id"]
                await status_msg.edit_text(f"🚀 **Composition Started!**\nCID: `{cid}`\nScraped IP: `{scraped_ip}`")
                
                # Step 3: Polling
                for _ in range(40):
                    await asyncio.sleep(10)
                    poll_res = await engine.tunnel_call(f"https://notegpt.io/api/v2/music/status?conversation_id={cid}", method="GET", cookies=cookies)
                    
                    if poll_res.status_code == 200:
                        s_data = poll_res.json().get("data", {})
                        if s_data.get("status") == "success":
                            await status_msg.edit_text("📥 **Track Ready! Downloading...**")
                            audio = requests.get(s_data.get("music_url")).content
                            await message.answer_audio(BufferedInputFile(audio, filename=f"{topic[:10]}.mp3"), 
                                                       caption=f"🎁 Track: {topic}\n⚡ IP: {scraped_ip}")
                            await status_msg.delete()
                            return
            else:
                await bot.send_message(ADMIN_ID, f"DEBUG FAILURE: {data}")
        else:
            await bot.send_message(ADMIN_ID, f"🛠 **BLOCK PAGE DETECTED**\nContent: {res.text[:500]}")
            await status_msg.edit_text("⚠️ **Engine Refreshed.** Try again in 5 seconds.")

    except Exception as e:
        await bot.send_message(ADMIN_ID, f"ERROR: {str(e)}")

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
