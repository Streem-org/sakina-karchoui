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
        status=discord.Status.dnd,
        activity=discord.Game("Karchaoui Dominance")
    )

    weekly_reset.start()
    bot.loop.create_task(terminal_commands())

# ---------------- TERMINAL ---------------- #

async def terminal_commands():
    await bot.wait_until_ready()
    while True:
        cmd = await asyncio.to_thread(input)

        if cmd.startswith("say"):
            parts = cmd.split(" ")
            channel_id = int(parts[1])
            message = " ".join(parts[2:])
            channel = bot.get_channel(channel_id)

            if channel:
                await channel.send(message)

# ---------------- WEEKLY RESET ---------------- #

@tasks.loop(hours=168)
async def weekly_reset():
    global weekly_data
    weekly_data = {}
    weekly_messages.clear()
    save_json(WEEKLY_FILE, weekly_data)

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
            data = afk_users.pop(message.author.id)
            afk_cooldown[message.author.id] = now

            duration = int(now - data["since"])
            duration_str = str(datetime.timedelta(seconds=duration))

            embed = discord.Embed(
                description=f"👋 Welcome back {message.author.mention}\nYou were AFK for **{duration_str}**",
                color=discord.Color.green()
            )
            await message.channel.send(embed=embed)

    # AFK MENTION
    for user in message.mentions:
        if user.id in afk_users:
            data = afk_users[user.id]
            duration = int(time.time() - data["since"])
            duration_str = str(datetime.timedelta(seconds=duration))

            embed = discord.Embed(
                description=f"💤 {user.mention} is AFK\n**Reason:** {data['reason']}\n**Since:** {duration_str} ago",
                color=discord.Color.orange()
            )
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

    embed = discord.Embed(
        description=f"💤 {ctx.author.mention} is now AFK\n**Reason:** {reason}",
        color=discord.Color.orange()
    )

    await ctx.send(embed=embed)

# ---------------- 8BALL ---------------- #

@bot.hybrid_command(name="8ball")
async def eightball(ctx, *, question):
    reply = random.choice(eightball_responses)

    if "are u gay" in question.lower():
        reply = "I may or may not be gay but you seem to be."

    embed = discord.Embed(title="Magic 8Ball", color=discord.Color.dark_purple())
    embed.add_field(name="Question", value=question, inline=False)
    embed.add_field(name="Answer", value=reply, inline=False)

    await ctx.send(embed=embed)

# ---------------- SAY ---------------- #

@bot.hybrid_command(name="say")
@commands.has_permissions(manage_messages=True)
async def say(ctx, *, message: str):
    await ctx.message.delete()
    await ctx.send(message)

# ---------------- UPTIME ---------------- #
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
        color=0x0d1117  # super dark
    )

    embed.set_footer(
        text=f"{ctx.author}",
        icon_url=ctx.author.display_avatar.url
    )

    await ctx.reply(embed=embed)

# ---------------- AVATAR ---------------- #

@bot.hybrid_command(name="avatar")
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author

    embed = discord.Embed(
        title=f"{member.name}'s Avatar",
        color=discord.Color.blurple()
    )
    embed.set_image(url=member.display_avatar.url)

    await ctx.reply(embed=embed)

# ---------------- AUTOREACTION ---------------- #

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

    text = ""
    for phrase, emoji in autoreactions.items():
        text += f"{phrase} → {emoji}\n"

    embed = discord.Embed(
        title="Autoreaction List",
        description=text,
        color=discord.Color.blurple()
    )

    await ctx.reply(embed=embed)

# ---------------- TIME SYSTEM ---------------- #

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
`.avatar` – View user avatar  
`.uptime` – Bot uptime  
`.time` – Check time  
`.time set <timezone>` – Set timezone  
`.afk <reason>` – Enable AFK  
""",
        inline=False
    )

    embed.add_field(
        name="🎮 Fun",
        value="""
`.8ball <question>` – Ask the magic ball  
`.ship @user @user` – Check compatibility  
""",
        inline=False
    )

    embed.add_field(
        name="🔒 Moderation",
        value="""
`.blacklist @user` – Block user  
`.unblacklist @user` – Remove blacklist  
`.reboot` – Restart bot  
""",
        inline=False
    )

    embed.set_footer(
        text="Sakina Karchaoui • Advanced Utility Bot",
        icon_url=ctx.bot.user.display_avatar.url
    )

    embed.set_thumbnail(url=ctx.bot.user.display_avatar.url)

    await ctx.send(embed=embed)

@bot.hybrid_command(name="ship")
async def ship(ctx, user1: discord.Member, user2: discord.Member):

    percent = random.randint(0, 100)

    # name merge
    ship_name = user1.name[:len(user1.name)//2] + user2.name[len(user2.name)//2:]

    # emoji
    if percent >= 80:
        emoji = "😍"
    elif percent >= 60:
        emoji = "😊"
    elif percent >= 40:
        emoji = "😐"
    else:
        emoji = "💀"

    # bar
    bar = "█" * (percent // 10) + "░" * (10 - percent // 10)

    embed = discord.Embed(
        title=ship_name.lower(),
        description=f"`{bar}` **{percent}%**\n{emoji}",
        color=0x2b2d31
    )

    embed.set_thumbnail(url=user1.display_avatar.url)
    embed.set_image(url=user2.display_avatar.url)

    await ctx.send(embed=embed)
@bot.command()
async def wrongchannel(ctx):
    # Only you can use this command
    if ctx.author.id != 1378768035187527795:
        return await ctx.send("❌ You cannot use this command!")

    # Make sure the command is a reply
    if not ctx.message.reference:
        return await ctx.send("⚠️ You must reply to a message to use this command!")

    # Get the message you replied to
    replied_message = ctx.message.reference.resolved
    if not replied_message:
        return await ctx.send("⚠️ Could not find the message you replied to!")

    # Delete your command message
    await ctx.message.delete()

    # Send the embed as a reply
    embed = discord.Embed(color=0x0d1117)
    embed.set_image(url="https://media.discordapp.net/attachments/1469526304398377253/1483397708042604587/Screenshot_20260317-150154.Photos.png?ex=69ba7145&is=69b91fc5&hm=1b5c666decb7d8a2321e97f3097a8b9a8ea580df05c0f64ee1e83345a0222f3c&=&format=webp&quality=lossless&width=612&height=656")  # Replace with your image URL
    await replied_message.reply(embed=embed)
# ---------------- RUN ---------------- #

bot.run(TOKEN)