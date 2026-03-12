import os
import random
import json
import datetime
from collections import defaultdict
import psutil
import time
from datetime import timedelta

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

# ---------------- ENV ---------------- #

load_dotenv()
TOKEN = os.getenv("TOKEN")
start_time = time.time()

COUNTING_CHANNEL = 1477918309696667800

TIME_FILE = "times.json"
WEEKLY_FILE = "weekly.json"
DUOS_FILE = "duos.json"

bot_start_time = datetime.datetime.utcnow()

# ---------------- SAFE FILE FUNCTIONS ---------------- #

def safe_load(file):
    try:
        with open(file, "r") as f:
            data = f.read().strip()
            if not data:
                return {}
            return json.loads(data)
    except:
        return {}

def safe_save(file, data):
    temp = file + ".tmp"
    with open(temp, "w") as f:
        json.dump(data, f, indent=4)
    os.replace(temp, file)

# ---------------- DATA ---------------- #

afk_users = {}

weekly_messages = defaultdict(int)
weekly_data = safe_load(WEEKLY_FILE)

duos = safe_load(DUOS_FILE)
duo_requests = {}

count_number = 0
last_counter = None

eightball_responses = [
"Yes",
"No",
"Ask again later",
"It is certain",
"Reply hazy, try later",
"Not in the mood shut the fuck up",
"I forgot the question"
]

# ---------------- BOT ---------------- #

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix=".",
    intents=intents,
    help_command=None
)

# ---------------- READY ---------------- #

@bot.event
async def on_ready():

    await bot.change_presence(
        status=discord.Status.dnd,
        activity=discord.Game(name="Jarvis protocols")
    )

    if not weekly_reset.is_running():
        weekly_reset.start()

    print(f"Logged in as {bot.user}")

# ---------------- WEEKLY RESET ---------------- #

@tasks.loop(hours=168)
async def weekly_reset():

    global weekly_data
    weekly_data = {}
    safe_save(WEEKLY_FILE, weekly_data)

# ---------------- MESSAGE EVENT ---------------- #

@bot.event
async def on_message(message):

    global count_number, last_counter

    if message.author.bot:
        return

    await bot.process_commands(message)

    weekly_messages[message.author.id] += 1
    weekly_data[str(message.author.id)] = weekly_messages[message.author.id]
    safe_save(WEEKLY_FILE, weekly_data)

    if message.author.id in afk_users:

        del afk_users[message.author.id]

        embed = discord.Embed(
            description="Your AFK has been removed.",
            color=discord.Color.red()
        )

        await message.channel.send(
            content=message.author.mention,
            embed=embed
        )

    for user in message.mentions:

        if user.id in afk_users:

            reason = afk_users[user.id]

            embed = discord.Embed(
                description=f"{user.mention} is currently AFK",
                color=discord.Color.orange()
            )

            embed.add_field(name="Reason", value=reason)

            await message.channel.send(embed=embed)

    if message.channel.id == COUNTING_CHANNEL:

        try:
            number = int(message.content)
        except:
            await message.delete()
            return

        if number != count_number + 1:
            await message.delete()
            return

        if last_counter == message.author.id:
            await message.delete()
            return

        count_number = number
        last_counter = message.author.id

# ---------------- HELP ---------------- #

@bot.command()
async def help(ctx):

    embed = discord.Embed(
        title="Jarvis Command Panel",
        description="Prefix: `.`",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Utility",
        value="`.avatar`\n`.uptime`\n`.afk`",
        inline=False
    )

    embed.add_field(
        name="Weekly",
        value="`.wk`\n`.wk p @user`",
        inline=False
    )

    embed.add_field(
        name="Fun",
        value="`.8ball`\n`.ship`\n`.match`\n`.duo`\n`.unmatch`",
        inline=False
    )

    embed.set_footer(
        text=f"Requested by {ctx.author}",
        icon_url=ctx.author.display_avatar.url
    )

    await ctx.send(embed=embed)

# ---------------- AFK ---------------- #

@bot.command()
async def afk(ctx, *, reason="AFK"):

    afk_users[ctx.author.id] = reason

    embed = discord.Embed(
        description=f"{ctx.author.mention} is now AFK.",
        color=discord.Color.orange()
    )

    embed.add_field(name="Reason", value=reason)

    await ctx.send(embed=embed)

# ---------------- WEEKLY ---------------- #

@bot.command()
async def wk(ctx, sub=None, member: discord.Member=None):

    if sub is None:

        if not weekly_data:
            await ctx.send("No weekly data yet.")
            return

        sorted_data = sorted(
            weekly_data.items(),
            key=lambda x: x[1],
            reverse=True
        )

        desc = ""

        for i,(user_id,points) in enumerate(sorted_data[:10],start=1):

            user = ctx.guild.get_member(int(user_id))

            if user:
                desc += f"**{i}. {user.name}** — {points} messages\n"

        embed = discord.Embed(
            title="Weekly Leaderboard",
            description=desc,
            color=discord.Color.gold()
        )

        await ctx.send(embed=embed)

    elif sub == "p":

        member = member or ctx.author
        points = weekly_data.get(str(member.id),0)

        embed = discord.Embed(
            title="Weekly Stats",
            description=f"{member.mention} sent **{points} messages** this week.",
            color=discord.Color.blurple()
        )

        await ctx.send(embed=embed)

# ---------------- UPTIME ---------------- #
@bot.command()
async def uptime(ctx):

    # Bot uptime
    bot_seconds = int(time.time() - start_time)
    bot_uptime = str(timedelta(seconds=bot_seconds))

    bot_started = datetime.datetime.fromtimestamp(
        start_time
    ).strftime("%d %B %Y %I:%M %p")

    # System uptime
    system_seconds = int(time.time() - psutil.boot_time())
    system_uptime = str(timedelta(seconds=system_seconds))

    system_started = datetime.datetime.fromtimestamp(
        psutil.boot_time()
    ).strftime("%d %B %Y %I:%M %p")

    embed = discord.Embed(
        title="Uptime Information",
        color=discord.Color.dark_theme()
    )

    embed.add_field(
        name="I was last rebooted",
        value="`0 days ago`",
        inline=False
    )

    embed.add_field(
        name="Bot Uptime",
        value=f"{bot_uptime}\n• {bot_started}",
        inline=False
    )

    embed.add_field(
        name="System Uptime",
        value=f"{system_uptime}\n• {system_started}",
        inline=False
    )

    embed.set_footer(
        text=f"Requested by {ctx.author}",
        icon_url=ctx.author.display_avatar.url
    )

    await ctx.send(embed=embed)
# ---------------- AVATAR ---------------- #

@bot.command()
async def avatar(ctx, member: discord.Member=None):

    member = member or ctx.author

    embed = discord.Embed(
        title=f"{member.name}'s Avatar",
        color=discord.Color.blurple()
    )

    embed.set_image(url=member.display_avatar.url)

    await ctx.send(embed=embed)

# ---------------- 8BALL ---------------- #

@bot.command(name="8ball")
async def eightball(ctx, *, question):

    reply = random.choice(eightball_responses)

    if "are u gay" in question.lower() or "are you gay" in question.lower():
        reply = "I may or may not be gay, but you seem to be."

    embed = discord.Embed(title="Magic 8ball")

    embed.add_field(name="Question", value=question, inline=False)
    embed.add_field(name="Answer", value=reply, inline=False)

    await ctx.send(embed=embed)

# ---------------- SHIP ---------------- #

@bot.command()
async def ship(ctx, member: discord.Member):

    percent = random.randint(0,100)

    filled = int(percent/10)
    bar = "█"*filled + "░"*(10-filled)

    embed = discord.Embed(
        title=f"{ctx.author.name} ❤️ {member.name}",
        description=f"`{bar}` {percent}%",
        color=discord.Color.blurple()
    )

    await ctx.send(embed=embed)

# ---------------- DUO SYSTEM ---------------- #

@bot.command()
async def match(ctx, member: discord.Member):

    if str(ctx.author.id) in duos:
        await ctx.send("You already have a duo.")
        return

    duo_requests[member.id] = ctx.author.id

    embed = discord.Embed(
        title="Duo Request",
        description=f"{ctx.author.mention} wants to duo with {member.mention}",
        color=discord.Color.blurple()
    )

    embed.set_thumbnail(url=ctx.author.display_avatar.url)

    embed.add_field(
        name="Accept",
        value=f"{member.mention} type `.accept`",
        inline=False
    )

    await ctx.send(embed=embed)

@bot.command()
async def accept(ctx):

    if ctx.author.id not in duo_requests:
        await ctx.send("No duo request.")
        return

    requester = duo_requests[ctx.author.id]

    duos[str(ctx.author.id)] = str(requester)
    duos[str(requester)] = str(ctx.author.id)

    safe_save(DUOS_FILE, duos)

    del duo_requests[ctx.author.id]

    embed = discord.Embed(
        title="Duo Created ❤️",
        description=f"<@{requester}> ❤️ {ctx.author.mention}",
        color=discord.Color.green()
    )

    await ctx.send(embed=embed)

@bot.command()
async def duo(ctx):

    if str(ctx.author.id) not in duos:
        await ctx.send("You don't have a duo.")
        return

    partner = ctx.guild.get_member(int(duos[str(ctx.author.id)]))

    embed = discord.Embed(
        title="Your Duo",
        description=f"{ctx.author.mention} ❤️ {partner.mention}",
        color=discord.Color.blurple()
    )

    embed.set_thumbnail(url=partner.display_avatar.url)

    await ctx.send(embed=embed)

@bot.command()
async def unmatch(ctx):

    if str(ctx.author.id) not in duos:
        await ctx.send("You don't have a duo.")
        return

    partner = duos[str(ctx.author.id)]

    duos.pop(str(ctx.author.id),None)
    duos.pop(str(partner),None)

    safe_save(DUOS_FILE,duos)

    await ctx.send("💔 Duo removed.")

# ---------------- RUN ---------------- #

bot.run(TOKEN)