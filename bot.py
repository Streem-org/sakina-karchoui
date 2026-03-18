import discord
from discord.ext import commands, tasks
import json
import random
import time
import datetime
import psutil
import pytz
import os
import asyncio
from collections import defaultdict
from PIL import Image, ImageDraw    
import requests
from io import BytesIO
import sys
from discord.ui import View, Button

TOKEN = os.getenv("TOKEN")
PREFIX = "."

MAIN_SERVER = 1469526303148609720

TIME_FILE = "times.json"
WEEKLY_FILE = "weekly.json"
BLACKLIST_FILE = "blacklist.json"
AUTOREACT_FILE = "autoreactions.json"

# ---------------- FILE SYSTEM ---------------- #

def load_json(file):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except:
        return {}

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

        

times = load_json(TIME_FILE)
weekly_data = load_json(WEEKLY_FILE)
blacklisted_users = load_json(BLACKLIST_FILE)
autoreactions = load_json(AUTOREACT_FILE)

weekly_messages = defaultdict(int)
afk_users = {}
afk_cooldown = {}
afk_mentions = {}

start_time = time.time()

eightball_responses = [
    "Yes",
    "No",
    "Ask again later",
    "It is certain",
    "Ok bro as u wish",
    "Not in the mood",
    "I forgot the question"
]

# ---------------- BOT ---------------- #
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None
)

# ---------------- READY ---------------- #

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    await bot.change_presence(
        status=discord.Status.idle,
        activity=discord.Game("Karchaoui Dominance")
    )
    await bot.tree.sync()
    print("Slash commands synced.")
    weekly_reset.start()

# ---------------- WEEKLY RESET ---------------- #

@tasks.loop(hours=168)
async def weekly_reset():
    global weekly_data
    weekly_data = {}
    weekly_messages.clear()
    save_json(WEEKLY_FILE, weekly_data)

# ---------------- AFK VIEW ---------------- #

class AFKReturnView(View):
    def __init__(self, mentions):
        super().__init__(timeout=60)
        self.mentions = mentions

    @discord.ui.button(label="Show Pings", style=discord.ButtonStyle.green)
    async def show_pings(self, interaction: discord.Interaction, button: Button):
        if not self.mentions:
            await interaction.response.send_message("No one mentioned you while AFK.", ephemeral=True)
            return

        text = "\n".join(self.mentions[:10])
        await interaction.response.send_message(f"📩 Mentions while AFK:\n{text}", ephemeral=True)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, button: Button):
        await interaction.message.delete()

# ---------------- MESSAGE EVENT ---------------- #

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if str(message.author.id) in blacklisted_users:
        return

    # WEEKLY TRACK
    weekly_messages[message.author.id] += 1
    weekly_data[str(message.author.id)] = weekly_messages[message.author.id]
    save_json(WEEKLY_FILE, weekly_data)

    # AFK REMOVE
    if message.author.id in afk_users:
        now = time.time()

        if message.author.id not in afk_cooldown or now - afk_cooldown[message.author.id] > 5:
            afk_users.pop(message.author.id)
            afk_cooldown[message.author.id] = now

            mentions = afk_mentions.pop(message.author.id, [])

            embed = discord.Embed(
                description="**Your AFK has been removed!**",
                color=message.author.color if message.author.color != discord.Color.default() else 0x2b2d31
            )

            view = AFKReturnView(mentions)
            await message.channel.send(embed=embed, view=view)

    # AFK MENTION
    for user in message.mentions:
        if user.id in afk_users and user != message.author:
            data = afk_users[user.id]
            duration = int(time.time() - data["since"])
            duration_str = str(datetime.timedelta(seconds=duration))

            afk_mentions.setdefault(user.id, [])
            afk_mentions[user.id].append(f"{message.author} in {message.channel.mention}")

            embed = discord.Embed(
                description=(
                    f"{user.mention} is currently AFK ({duration_str} ago)\n\n"
                    f"**Message:**\n{data['reason']}"
                ),
                color=user.color if hasattr(user, "color") and user.color != discord.Color.default() else 0x2b2d31
            )

            embed.set_thumbnail(url=user.display_avatar.url)
            await message.channel.send(embed=embed)

    # AUTOREACTION
    for phrase, emoji in autoreactions.items():
        if phrase in message.content.lower():
            try:
                await message.add_reaction(emoji)
            except:
                pass

    await bot.process_commands(message)

# ---------------- AFK COMMAND ---------------- #

@bot.hybrid_command()
async def afk(ctx, *, reason="AFK"):
    afk_users[ctx.author.id] = {
        "reason": reason,
        "since": int(time.time())
    }

    afk_mentions[ctx.author.id] = []

    embed = discord.Embed(
        description=(
            f"**You're now AFK!**\n\n"
            f"**Message:**\n"
            f"• {reason}"
        ),
        color=ctx.author.color if ctx.author.color != discord.Color.default() else 0x2b2d31
    )

    embed.set_author(
        name=str(ctx.author),
        icon_url=ctx.author.display_avatar.url
    )

    await ctx.send(embed=embed)

# ---------------- 8BALL ----------------

@bot.hybrid_command(name="8ball")
async def eightball(ctx, *, question):
    reply = random.choice(eightball_responses)

    if "are u gay" in question.lower():
        reply = "I may or may not be gay but you seem to be."

    embed = discord.Embed(title="Magic 8Ball", color=discord.Color.dark_purple())
    embed.add_field(name="Question", value=question, inline=False)
    embed.add_field(name="Answer", value=reply, inline=False)

    await ctx.send(embed=embed)

# ---------------- SAY ----------------

@bot.hybrid_command(name="say")
@commands.has_permissions(manage_messages=True)
async def say(ctx, *, message: str):
    try:
        await ctx.message.delete()
    except:
        pass
    await ctx.send(message)

# ---------------- UPTIME ----------------

@bot.hybrid_command(name="uptime")
async def uptime(ctx):
    now = int(time.time())

    bot_uptime_seconds = int(now - start_time)
    system_boot = int(psutil.boot_time())
    system_uptime_seconds = now - system_boot

    bot_time = str(datetime.timedelta(seconds=bot_uptime_seconds))
    system_time = str(datetime.timedelta(seconds=system_uptime_seconds))

    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    ping = round(bot.latency * 1000)

    embed = discord.Embed(
        description=(
            f"```ansi\n"
            f"\x1b[1;37mSYSTEM STATUS\x1b[0m\n\n"
            f"\x1b[1;30mBot Uptime   ::\x1b[0m {bot_time}\n"
            f"\x1b[1;30mSystem Uptime::\x1b[0m {system_time}\n"
            f"\x1b[1;30mPing         ::\x1b[0m {ping} ms\n"
            f"\x1b[1;30mCPU Usage    ::\x1b[0m {cpu}%\n"
            f"\x1b[1;30mRAM Usage    ::\x1b[0m {ram}%\n"
            f"\n\x1b[1;37mSTATUS: OPERATIONAL\x1b[0m"
            f"\n```"
        ),
        color=0x0d1117
    )

    embed.set_footer(
        text=f"{ctx.author}",
        icon_url=ctx.author.display_avatar.url
    )

    await ctx.reply(embed=embed)

# ---------------- AVATAR ----------------

@bot.hybrid_command(name="avatar")
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author

    embed = discord.Embed(
        title=f"{member.name}'s Avatar",
        color=discord.Color.blurple()
    )
    embed.set_image(url=member.display_avatar.url)

    await ctx.reply(embed=embed)

# ---------------- AUTOREACTION ----------------

@bot.hybrid_group(name="autoreaction", invoke_without_command=True)
async def autoreaction(ctx):
    embed = discord.Embed(
        title="Autoreaction Commands",
        description="""
.autoreaction add <phrase> <emoji>
.autoreaction remove <phrase>
.autoreaction list
""",
        color=discord.Color.blurple()
    )
    await ctx.reply(embed=embed)

@autoreaction.command(name="add")
@commands.has_permissions(manage_guild=True)
async def autoreaction_add(ctx, phrase: str, emoji: str):
    autoreactions[phrase.lower()] = emoji
    save_json(AUTOREACT_FILE, autoreactions)
    await ctx.reply(f"Added: {phrase} → {emoji}")

@autoreaction.command(name="remove")
async def autoreaction_remove(ctx, phrase: str):
    autoreactions.pop(phrase.lower(), None)
    save_json(AUTOREACT_FILE, autoreactions)
    await ctx.reply("Removed.")

@autoreaction.command(name="list")
async def autoreaction_list(ctx):
    if not autoreactions:
        return await ctx.reply("No autoreactions set.")

    text = "\n".join([f"{p} → {e}" for p, e in autoreactions.items()])

    embed = discord.Embed(
        title="Autoreaction List",
        description=text,
        color=discord.Color.blurple()
    )

    await ctx.reply(embed=embed)

# ---------------- TIME SYSTEM ----------------

@bot.hybrid_group(name="time", invoke_without_command=True)
async def time_cmd(ctx, member: discord.Member = None):
    member = member or ctx.author

    if str(member.id) not in times:
        return await ctx.send("❌ Timezone not set. Use .time set Asia/Kolkata")

    tz = pytz.timezone(times[str(member.id)])
    now = datetime.datetime.now(tz)

    embed = discord.Embed(title="🕒 Time Info", color=discord.Color.purple())
    embed.add_field(name="User", value=member.mention)
    embed.add_field(name="Time", value=now.strftime("%I:%M:%S %p"))
    embed.add_field(name="Date", value=now.strftime("%A, %d %B %Y"))
    embed.add_field(name="Timezone", value=times[str(member.id)])

    await ctx.send(embed=embed)

@time_cmd.command(name="set")
async def time_set(ctx, *, timezone: str):
    try:
        pytz.timezone(timezone)
    except:
        return await ctx.send("❌ Invalid timezone. Example: Asia/Kolkata")

    times[str(ctx.author.id)] = timezone
    save_json(TIME_FILE, times)

    await ctx.send(f"🌍 Timezone set to {timezone}")

# ---------------- HELP ----------------

@bot.hybrid_command(name="help")
async def help_command(ctx):
    embed = discord.Embed(
        title="⚡ Sakina Karchaoui Command Panel",
        description="**Prefix:** `.` | Slash commands also supported\n\nElegant. Fast. Unstoppable ⚡",
        color=0x1f6feb
    )

    embed.add_field(
        name="🛠️ Utility",
        value="""
.avatar
.uptime
.time
.time set <timezone>
""",
        inline=False
    )

    embed.add_field(
        name="🎮 Fun",
        value="""
.8ball <question>
.ship @user @user
""",
        inline=False
    )

    embed.add_field(
        name="🔒 Moderation",
        value="""
.say <message>
""",
        inline=False
    )

    embed.set_footer(
        text="Sakina Karchaoui • Advanced Utility Bot",
        icon_url=ctx.bot.user.display_avatar.url
    )

    embed.set_thumbnail(url=ctx.bot.user.display_avatar.url)

    await ctx.send(embed=embed)

# ---------------- SHIP ----------------

@bot.hybrid_command(name="ship")
async def ship(ctx, user1: discord.Member, user2: discord.Member):
    percent = random.randint(0, 100)

    ship_name = user1.name[:len(user1.name)//2] + user2.name[len(user2.name)//2:]

    if percent >= 80:
        emoji = "😍"
    elif percent >= 60:
        emoji = "😊"
    elif percent >= 40:
        emoji = "😐"
    else:
        emoji = "💀"

    bar = "█" * (percent // 10) + "░" * (10 - percent // 10)

    embed = discord.Embed(
        title=ship_name.lower(),
        description=f"`{bar}` **{percent}%**\n{emoji}",
        color=0x2b2d31
    )

    embed.set_thumbnail(url=user1.display_avatar.url)
    embed.set_image(url=user2.display_avatar.url)

    await ctx.send(embed=embed)

    # ---------------- PING ---------------- #
@bot.hybrid_command(name="ping")
async def ping(ctx):
    # WebSocket latency
    ws_latency = round(bot.latency * 1000)

    # Message send latency
    start = time.perf_counter()
    msg = await ctx.reply("🏓 Pong...")
    end = time.perf_counter()
    msg_latency = round((end - start) * 1000)

    # Status logic
    def get_status(ms):
        if ms < 80:
            return "🟢 Excellent"
        elif ms < 150:
            return "🟢 Good"
        elif ms < 250:
            return "🟡 Alright"
        elif ms < 400:
            return "🟠 Bad"
        else:
            return "🔴 Very Bad"

    ws_status = get_status(ws_latency)
    msg_status = get_status(msg_latency)

    embed = discord.Embed(
        title="🏓 Pong!",
        color=0x2b2d31
    )

    embed.add_field(
        name="Discord WS",
        value=f"{ws_status}\n`{ws_latency} ms`",
        inline=False
    )

    embed.add_field(
        name="Message Send",
        value=f"{msg_status}\n`{msg_latency} ms`",
        inline=False
    )

    embed.set_footer(
        text="Scale: Excellent | Good | Alright | Bad | Very Bad"
    )

    await msg.edit(content=None, embed=embed)

    
bot.run(TOKEN)