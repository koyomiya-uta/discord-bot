import discord
import os

TOKEN = os.environ["DISCORD_TOKEN"]

TARGET_INVITE_CODE = "BvCXSBWC4J"      # 招待コードのみ
ROLE_ID = 1458833025017319515          # 付与するロール
LOG_CHANNEL_ID = 1071513357879873556    # ログ送信先チャンネルID

intents = discord.Intents.all()
client = discord.Client(intents=intents)

invite_cache = {}

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

    await client.change_presence(
        activity=discord.Game(name="DMで「バナナ」って送ってみてね")
    )

    # 招待リンクの使用回数をキャッシュ
    for guild in client.guilds:
        invites = await guild.invites()
        invite_cache[guild.id] = {i.code: i.uses for i in invites}

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

    # ログ送信
    log_channel = guild.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(
            title="📥 メンバー参加ログ",
            color=discord.Color.green()
        )
        embed.add_field(name="ユーザー", value=f"{member} ({member.mention})", inline=False)
        embed.add_field(name="使用招待コード", value=used_invite_code, inline=False)
        embed.add_field(
            name="ロール付与",
            value="✅ 付与済み" if role_given else "❌ なし",
            inline=False
        )
        embed.set_footer(text=f"User ID: {member.id}")

        await log_channel.send(embed=embed)

@client.event
async def on_message(message):
    if message.author.bot:
        return

    # DMのみ反応
    if message.guild is not None:
        return

    if message.content.startswith(("バナナ", "ばなな")):
        await message.channel.send("わーいバナナバナナ( ᐛ )")

client.run(TOKEN)
