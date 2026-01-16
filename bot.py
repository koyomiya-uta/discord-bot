import os
import discord
import asyncio
import aiohttp
import feedparser
import threading
import random
from flask import Flask

# =========================
# 環境変数
# =========================
TOKEN = os.environ["DISCORD_TOKEN"]
TWITCH_CLIENT_ID = os.environ["TWITCH_CLIENT_ID"]
TWITCH_CLIENT_SECRET = os.environ["TWITCH_CLIENT_SECRET"]

# =========================
# 設定
# =========================
TARGET_INVITE_CODE = "BvCXSBWC4J"
ROLE_ID = 1458833025017319515
LOG_CHANNEL_ID = 1071513357879873556

TWITCH_USERNAME = "koyomiya_uta"
TWITCH_NOTIFY_CHANNEL_ID = 1071513357879873556

YOUTUBE_CHANNEL_ID = "UCDmi8pYwLaXxnhg_GXTL0PQ"
YOUTUBE_NOTIFY_CHANNEL_ID = 1071513357879873556

# =========================
intents = discord.Intents.all()
client = discord.Client(intents=intents)
invite_cache = {}

# =========================
# Flask (Render用)
# =========================
app = Flask("")

@app.route("/")
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask).start()

# =========================
# Twitch
# =========================
twitch_token = None
twitch_live = False

async def get_twitch_token():
    global twitch_token
    url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": TWITCH_CLIENT_ID,
        "client_secret": TWITCH_CLIENT_SECRET,
        "grant_type": "client_credentials"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, params=params) as resp:
            data = await resp.json()
            twitch_token = data["access_token"]

async def check_twitch():
    global twitch_live

    if not twitch_token:
        await get_twitch_token()

    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {twitch_token}"
    }

    url = f"https://api.twitch.tv/helix/streams?user_login={TWITCH_USERNAME}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            data = await resp.json()

    channel = client.get_channel(TWITCH_NOTIFY_CHANNEL_ID)

    if data["data"]:
        if not twitch_live:
            twitch_live = True
            stream = data["data"][0]
            title = stream["title"]

            await channel.send(
                f"@視聴者\n"
                f"🟣 **Twitch配信開始！**\n"
                f"📺 {title}\n"
                f"https://twitch.tv/{TWITCH_USERNAME}"
            )
    else:
        twitch_live = False

async def twitch_loop():
    await client.wait_until_ready()
    while not client.is_closed():
        await check_twitch()
        await asyncio.sleep(60)

# =========================
# YouTube
# =========================
last_youtube_id = None
youtube_live = False

async def check_youtube():
    global last_youtube_id, youtube_live

    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={YOUTUBE_CHANNEL_ID}"
    feed = feedparser.parse(feed_url)

    youtube_live = False

    if not feed.entries:
        return

    latest = feed.entries[0]

    # 配信かどうか判定
    live_type = latest.get("yt_live_broadcast", "")

    if live_type != "live":
        return

    video_id = latest.yt_videoid
    youtube_live = True

    if video_id != last_youtube_id:
        last_youtube_id = video_id

        channel = client.get_channel(YOUTUBE_NOTIFY_CHANNEL_ID)
        if channel:
            await channel.send(
                f"@視聴者\n"
                f"🔴 **YouTube配信開始！**\n"
                f"📺 {latest.title}\n"
                f"https://youtube.com/watch?v={video_id}"
            )


async def youtube_loop():
    await client.wait_until_ready()
    while not client.is_closed():
        await check_youtube()
        await asyncio.sleep(60)

# =========================
# Presence
# =========================
async def presence_loop():
    await client.wait_until_ready()

    while not client.is_closed():
        if twitch_live:
            text = "🟣 Twitchで配信中！"
        elif youtube_live:
            text = "🔴 YouTubeで配信中！"
        else:
            text = "DMで会話ができるよ！"

        await client.change_presence(activity=discord.Game(name=text))
        await asyncio.sleep(60)

# =========================
# Discord Events
# =========================
@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

    for guild in client.guilds:
        invites = await guild.invites()
        invite_cache[guild.id] = {i.code: i.uses for i in invites}

    client.loop.create_task(twitch_loop())
    client.loop.create_task(youtube_loop())
    client.loop.create_task(presence_loop())

@client.event
async def on_member_join(member):
    guild = member.guild
    invites = await guild.invites()

    before = invite_cache.get(guild.id, {})
    after = {i.code: i.uses for i in invites}
    invite_cache[guild.id] = after

    used_invite_code = "不明"
    for code, uses in after.items():
        if code in before and uses > before[code]:
            used_invite_code = code
            break

    role_given = False
    if used_invite_code == TARGET_INVITE_CODE:
        role = guild.get_role(ROLE_ID)
        if role:
            await member.add_roles(role)
            role_given = True

    log_channel = guild.get_channel(LOG_CHANNEL_ID)
    embed = discord.Embed(title="📥 メンバー参加ログ", color=discord.Color.green())
    embed.add_field(name="ユーザー", value=member.mention, inline=False)
    embed.add_field(name="招待コード", value=used_invite_code, inline=False)
    embed.add_field(name="ロール", value="✅" if role_given else "❌", inline=False)
    await log_channel.send(embed=embed)

@client.event
async def on_message(message):
    if message.author.bot:
        return

    # DMのみ反応
    if message.guild is not None:
        return

    content = message.content.lower()

    replies = {
        "バナナ": [
            "わーいバナナバナナ( ᐛ )",
            "バナナ最高 🍌",
            "うほっ🦍",
        ],
        "ばなな": [
            "わーいバナナバナナ( ᐛ )",
            "ばなな最高 🍌",
            "うほっ🦍",
        ],
        "おはよう": [
            "おはよう！",
            "今日もがんばろー！",
            "おはよ〜🦊",
        ],
        "こんにちは": [
            "こんにちは〜！",
            "やっほー！",
            "お昼ご飯何にする？",
        ],
        "こんにちわ": [
            "こんにちわ〜！",
            "やっほー！",
            "お昼ご飯何にする？",
        ],
        "こんばんわ": [
            "こんばんわ～！",
            "晩御飯何にする？",
            "お腹すいた",
        ],
        "こんばんは": [
            "こんばんは～！",
            "晩御飯何にする？",
            "お腹すいた",
        ],
        "疲れた": [
            "お疲れさま 🍵",
            "無理しないでね",
            "少し休もうぜ",
            "いっぱい寝よう",
        ],
    }

    for key, reply_list in replies.items():
        if key in content:
            await message.channel.send(random.choice(reply_list))
            return
# =========================
client.run(TOKEN)
