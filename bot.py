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
TWITCH_NOTIFY_CHANNEL_ID = 1276391580512550912

YOUTUBE_CHANNEL_ID = "UCDmi8pYwLaXxnhg_GXTL0PQ"
YOUTUBE_NOTIFY_CHANNEL_ID = 1276391580512550912

MENTION_ROLE_ID = 1026874804470558802

JOIN_ENABLED = False

# =========================
intents = discord.Intents.all()

class MyClient(discord.Client):
    def __init__(self, *, intents):
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)

client = MyClient(intents=intents)
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
    mention = f"<@&{MENTION_ROLE_ID}>"

    if data["data"]:
        if not twitch_live:
            twitch_live = True
            stream = data["data"][0]
            title = stream["title"]

            join_text = "👥 参加型：ON" if JOIN_ENABLED else "👥 参加型：OFF"

            text = f"""{mention}
🟣 **Twitch配信開始！**

📺 **{title}**

{join_text}

🔗 https://twitch.tv/{TWITCH_USERNAME}
"""

            await channel.send(content=text, allowed_mentions=discord.AllowedMentions(roles=True))
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
    video_id = latest.yt_videoid
    link = latest.link

    if "/live" not in link:
        return

    youtube_live = True

    if video_id != last_youtube_id:
        last_youtube_id = video_id

        channel = client.get_channel(YOUTUBE_NOTIFY_CHANNEL_ID)
        mention = f"<@&{MENTION_ROLE_ID}>"

        join_text = "👥 参加型：ON" if JOIN_ENABLED else "👥 参加型：OFF"

        text = f"""{mention}
🔴 **YouTube配信開始！**

📺 **{latest.title}**

{join_text}

🔗 https://youtube.com/watch?v={video_id}
"""

        if channel:
            await channel.send(content=text, allowed_mentions=discord.AllowedMentions(roles=True))

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
# Slash Command
# =========================
@client.tree.command(name="join", description="参加型のON / OFF")
@discord.app_commands.describe(mode="on または off")
async def join(interaction: discord.Interaction, mode: str):
    global JOIN_ENABLED

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 管理者のみ使用できます。", ephemeral=True)
        return

    if mode.lower() == "on":
        JOIN_ENABLED = True
        await interaction.response.send_message("✅ 参加型を **ON** にしました。")

    elif mode.lower() == "off":
        JOIN_ENABLED = False
        await interaction.response.send_message("❌ 参加型を **OFF** にしました。")

    else:
        await interaction.response.send_message("on か off を指定してください。", ephemeral=True)

# =========================
# Discord Events
# =========================
@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

    await client.tree.sync()

    for guild in client.guilds:
        invites = await guild.invites()
        invite_cache[guild.id] = {i.code: i.uses for i in invites}

    client.loop.create_task(twitch_loop())
    client.loop.create_task(youtube_loop())
    client.loop.create_task(presence_loop())

@client.event
async def on_message(message):
    if message.author.bot or message.guild is not None:
        return

    content = message.content.lower()

    replies = {
        "バナナ": ["わーいバナナバナナ( ᐛ )", "バナナ最高 🍌", "うほっ🦍"],
        "おはよう": ["おはよう！", "今日もがんばろー！", "おはよ〜🦊"],
        "疲れた": ["お疲れさま 🍵", "無理しないでね", "少し休もうぜ"],
    }

    for key, reply_list in replies.items():
        if key in content:
            await message.channel.send(random.choice(reply_list))
            return

# =========================
client.run(TOKEN)
