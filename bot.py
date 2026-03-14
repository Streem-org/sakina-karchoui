import os
import random
import json
import datetime
import asyncio
import time
import psutil
import pytz

from collections import defaultdict
from datetime import timedelta

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

# ---------------- ENV ---------------- #

load_dotenv()
TOKEN = os.getenv("TOKEN")

# ---------------- CONSTANTS ---------------- #

MAIN_SERVER = 1469526303148609720
COUNTING_CHANNEL = 1477918309696667800

TIME_FILE = "times.json"
WEEKLY_FILE = "weekly.json"
DUOS_FILE = "duos.json"
BLACKLIST_FILE = "blacklist.json"

# ---------------- FILE SYSTEM ---------------- #

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
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

for file in [TIME_FILE, WEEKLY_FILE, DUOS_FILE, BLACKLIST_FILE]:
    if not os.path.exists(file):
        safe_save(file, {})

# ---------------- DATA ---------------- #

afk_users = {}

weekly_messages = defaultdict(int)
weekly_data = safe_load(WEEKLY_FILE)

duos = safe_load(DUOS_FILE)
duo_requests = {}

times = safe_load(TIME_FILE)

blacklist = safe_load(BLACKLIST_FILE)
if isinstance(blacklist, dict):
    blacklist = []

count_number = 0
last_counter = None

start_time = time.time()

eightball_responses = [
"Yes","No","Ask again later","It is certain",
"Reply hazy try later","Not in the mood","I forgot the question"
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

# ---------------- TERMINAL CONTROL ---------------- #

async def terminal_listener():

    await bot.wait_until_ready()

    while not bot.is_closed():

        cmd = await asyncio.to_thread(input)

        if cmd.startswith("say"):

            try:
                parts = cmd.split()
                channel_id = int(parts[1])
                channel = bot.get_channel(channel_id)

                message_parts = []

                for p in parts[2:]:

                    if p.isdigit():
                        message_parts.append(f"<@{p}>")
                    else:
                        message_parts.append(p)

                message = " ".join(message_parts)

                await channel.send(message)

            except Exception as e:
                print("Terminal error:", e)

# ---------------- READY ---------------- #

@bot.event
async def on_ready():

    print(f"Logged in as {bot.user}")

    await bot.change_presence(
        status=discord.Status.dnd,
        activity=discord.Game("Training again")
    )

    if not weekly_reset.is_running():
        weekly_reset.start()

    bot.loop.create_task(terminal_listener())

# ---------------- WEEKLY RESET ---------------- #

@tasks.loop(hours=168)
async def weekly_reset():

    global weekly_data

    weekly_data = {}
    weekly_messages.clear()

    safe_save(WEEKLY_FILE, weekly_data)

# ---------------- MESSAGE EVENT ---------------- #

@bot.event
async def on_message(message):

    global count_number, last_counter

    if message.author.bot:
        return

    if message.author.id in blacklist:
        return

    weekly_messages[message.author.id] += 1
    weekly_data[str(message.author.id)] = weekly_messages[message.author.id]

    safe_save(WEEKLY_FILE, weekly_data)

    if message.channel.id == COUNTING_CHANNEL:

        try:
            num = int(message.content)
        except:
            await message.delete()
            return

        if num != count_number + 1:
            await message.delete()
            return

        if message.author.id == last_counter:
            await message.delete()
            return

        count_number = num
        last_counter = message.author.id

    await bot.process_commands(message)

# ---------------- HELP ---------------- #

@bot.command()
async def help(ctx):

    embed = discord.Embed(
        title="Jarvis Command Panel",
        description="Prefix: .",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Utility",
        value=".avatar\n.uptime\n.afk\n.time",
        inline=False
    )

    embed.add_field(
        name="Weekly",
        value=".wk\n.wk p @user",
        inline=False
    )

    embed.add_field(
        name="Fun",
        value=".8ball\n.ship\n.match\n.unmatch",
        inline=False
    )

    await ctx.send(embed=embed)

# ---------------- AFK ---------------- #

@bot.command()
async def afk(ctx, *, reason="AFK"):

    afk_users[ctx.author.id] = reason

    embed = discord.Embed(
        description=f"{ctx.author.mention} is now AFK",
        color=discord.Color.orange()
    )

    embed.add_field(name="Reason", value=reason)

    await ctx.send(embed=embed)

# ---------------- WEEKLY ---------------- #

@bot.command()
async def wk(ctx, sub=None, member: discord.Member=None):

    if ctx.guild.id != MAIN_SERVER:
        return

    if sub is None:

        sorted_data = sorted(
            weekly_data.items(),
            key=lambda x: x[1],
            reverse=True
        )

        desc = ""

        for i,(uid,msgs) in enumerate(sorted_data[:10],1):

            user = ctx.guild.get_member(int(uid))

            if user:
                desc += f"**{i}. {user.name}** — {msgs}\n"

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

# ---------------- TIME ---------------- #

@bot.command()
async def time(ctx, sub=None, *, value=None):

    if sub == "set":

        try:
            pytz.timezone(value)
        except:
            await ctx.send("Invalid timezone example: `.time set Asia/Kolkata`")
            return

        times[str(ctx.author.id)] = value
        safe_save(TIME_FILE, times)

        await ctx.send(f"Timezone set to **{value}**")
        return

    member = ctx.message.mentions[0] if ctx.message.mentions else ctx.author

    if str(member.id) not in times:
        await ctx.send(f"{member.mention} has not set timezone.")
        return

    tz = pytz.timezone(times[str(member.id)])
    now = datetime.datetime.now(tz)

    embed = discord.Embed(
        title=f"{member.display_name}'s Time",
        color=discord.Color.blurple()
    )

    embed.add_field(name="Time", value=now.strftime("%I:%M %p"))
    embed.add_field(name="Date", value=now.strftime("%d %B %Y"))
    embed.add_field(name="Timezone", value=times[str(member.id)])

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

# ---------------- UPTIME ---------------- #

@bot.command()
async def uptime(ctx):

    seconds = int(time.time() - start_time)

    embed = discord.Embed(
        title="Uptime",
        description=str(timedelta(seconds=seconds)),
        color=discord.Color.green()
    )

    await ctx.send(embed=embed)

# ---------------- 8BALL ---------------- #

@bot.command(name="8ball")
async def eightball(ctx, *, question):

    reply = random.choice(eightball_responses)

    if "are u gay" in question.lower():
        reply = "I may or may not be gay but you seem to be."

    embed = discord.Embed(title="Magic 8ball")

    embed.add_field(name="Question", value=question)
    embed.add_field(name="Answer", value=reply)

    await ctx.send(embed=embed)

# ---------------- SHIP ---------------- #

@bot.command()
async def ship(ctx, u1: discord.Member, u2: discord.Member):

    percent = random.randint(0,100)

    embed = discord.Embed(
        title="Ship",
        description=f"{u1.mention} ❤️ {u2.mention}\n{percent}% compatibility",
        color=discord.Color.pink()
    )

    await ctx.send(embed=embed)

# ---------------- BLACKLIST ---------------- #

@bot.command()
@commands.has_permissions(administrator=True)
async def blacklist(ctx, member: discord.Member):

    if member.id in blacklist:
        return

    blacklist.append(member.id)

    safe_save(BLACKLIST_FILE, blacklist)

    await ctx.send(f"{member.mention} blacklisted")

@bot.command()
@commands.has_permissions(administrator=True)
async def unblacklist(ctx, member: discord.Member):

    if member.id not in blacklist:
        return

    blacklist.remove(member.id)

    safe_save(BLACKLIST_FILE, blacklist)

    await ctx.send(f"{member.mention} removed from blacklist")

# ---------------- REBOOT ---------------- #

@bot.command()
@commands.is_owner()
async def reboot(ctx):

    await ctx.send("Rebooting...")
    os.execv(__file__, ["python"] + os.sys.argv)

# ---------------- RUN ---------------- #

bot.run(TOKEN)