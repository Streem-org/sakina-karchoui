import os
import time
import random
import json
import datetime
from collections import defaultdict
from datetime import timedelta

import discord
from discord.ext import commands
from dotenv import load_dotenv
import pytz


# ---------------- ENV ---------------- #

load_dotenv()
TOKEN = os.getenv("TOKEN")

CREATOR_ID = 1378768035187527795
COUNTING_CHANNEL = 1477918309696667800
ROLE_DROP_CHANNEL = 1469526304738119940

TIME_FILE = "times.json"


# ---------------- DATA ---------------- #

start_time = time.time()

afk_users = {}
weekly_messages = defaultdict(int)

count_number = 0
last_counter = None

blacklisted_users = set()

eightball_responses = [
    "Yes", "No", "Maybe", "Definitely",
    "Absolutely not", "Ask again later",
    "Probably", "I don't think so",
    "Without a doubt", "Very likely"
]


# ---------------- BOT SETUP ---------------- #

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix=".",
    intents=intents,
    help_command=None
)


# ---------------- FILE SETUP ---------------- #

if not os.path.exists(TIME_FILE):
    with open(TIME_FILE, "w") as f:
        json.dump({}, f)


def load_times():
    with open(TIME_FILE, "r") as f:
        return json.load(f)


def save_times(data):
    with open(TIME_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ---------------- EMBED STYLE ---------------- #

def magic_embed(title, question=None, answer=None):

    embed = discord.Embed(
        title=title,
        color=discord.Color.blurple()
    )

    if question:
        embed.add_field(name="Info", value=question, inline=False)

    if answer:
        embed.add_field(name="Result", value=answer, inline=False)

    embed.set_footer(text="YILDIZ")
    embed.set_thumbnail(url=bot.user.display_avatar.url)

    return embed


# ---------------- EVENTS ---------------- #

@bot.event
async def on_ready():

    await bot.tree.sync()

    print(f"Bot online as {bot.user}")


@bot.event
async def on_message(message):

    global count_number, last_counter

    if message.author.bot:
        return

    if message.author.id in blacklisted_users:
        return

    weekly_messages[message.author.id] += 1

    # AFK REMOVE
    if message.author.id in afk_users:
        del afk_users[message.author.id]

        embed = magic_embed(
            "AFK Removed",
            f"{message.author.mention} is no longer AFK"
        )

        await message.channel.send(embed=embed)

    # AFK MENTION
    for user in message.mentions:

        if user.id in afk_users:

            embed = magic_embed(
                "AFK User",
                user.name,
                afk_users[user.id]
            )

            await message.channel.send(embed=embed)

    # COUNTING SYSTEM
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

    await bot.process_commands(message)


# ---------------- MODERATION ---------------- #

@bot.hybrid_command()
async def blacklist(ctx, user: discord.Member):

    if ctx.author.id != CREATOR_ID:
        return

    blacklisted_users.add(user.id)

    embed = magic_embed("Blacklist", "User Added", user.mention)
    await ctx.send(embed=embed)


@bot.hybrid_command()
async def unblacklist(ctx, user: discord.Member):

    if ctx.author.id != CREATOR_ID:
        return

    blacklisted_users.discard(user.id)

    embed = magic_embed("Blacklist", "User Removed", user.mention)
    await ctx.send(embed=embed)


# ---------------- AFK ---------------- #

@bot.hybrid_command()
async def afk(ctx, *, reason="AFK"):

    afk_users[ctx.author.id] = reason

    embed = magic_embed("AFK Status", "Reason", reason)
    await ctx.send(embed=embed)


# ---------------- UTILITY ---------------- #

@bot.hybrid_command()
async def avatar(ctx, member: discord.Member = None):

    member = member or ctx.author

    embed = magic_embed("Avatar", member.mention)
    embed.set_image(url=member.display_avatar.url)

    await ctx.send(embed=embed)


@bot.hybrid_command()
async def serverinfo(ctx):

    guild = ctx.guild

    embed = discord.Embed(
        title="Server Info",
        color=discord.Color.blurple()
    )

    embed.add_field(name="Name", value=guild.name)
    embed.add_field(name="Members", value=guild.member_count)
    embed.add_field(name="Owner", value=guild.owner)
    embed.add_field(name="Created", value=guild.created_at.date())

    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)

    await ctx.send(embed=embed)


@bot.hybrid_command()
async def uptime(ctx):

    seconds = int(time.time() - start_time)
    uptime = str(timedelta(seconds=seconds))

    embed = magic_embed("Bot Uptime", "Running Time", uptime)

    await ctx.send(embed=embed)


# ---------------- FUN ---------------- #

@bot.hybrid_command(name="8ball")
async def eightball(ctx, *, question):

    reply = random.choice(eightball_responses)

    embed = magic_embed("Magic 8Ball", question, reply)

    await ctx.send(embed=embed)


@bot.hybrid_command()
async def choose(ctx, *, options):

    choices = [o.strip() for o in options.split(",")]
    result = random.choice(choices)

    embed = magic_embed("Choice Picker", options, result)

    await ctx.send(embed=embed)


@bot.hybrid_command()
async def match(ctx, user1: discord.Member, user2: discord.Member):

    percent = random.randint(1, 100)

    embed = magic_embed(
        "Compatibility Match",
        f"{user1.name} ❤️ {user2.name}",
        f"{percent}%"
    )

    await ctx.send(embed=embed)


# ---------------- WEEKLY ---------------- #

@bot.hybrid_command()
async def weekly(ctx):

    top = sorted(
        weekly_messages.items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]

    embed = discord.Embed(
        title="Weekly Messages",
        color=discord.Color.blurple()
    )

    for uid, count in top:

        member = ctx.guild.get_member(uid)

        if member:
            embed.add_field(
                name=member.name,
                value=f"{count} messages",
                inline=False
            )

    await ctx.send(embed=embed)


# ---------------- ROLE DROP ---------------- #

@bot.hybrid_command()
async def roledrop(ctx):

    if ctx.author.id != CREATOR_ID:
        return

    if ctx.channel.id != ROLE_DROP_CHANNEL:
        return

    role_name = random.choice(["Cristiano Glazer", "Messi Glazer"])

    embed = magic_embed("Role Drop", "First to reply gets", role_name)

    msg = await ctx.send(embed=embed)

    def check(m):
        return m.reference and m.reference.message_id == msg.id

    try:
        reply = await bot.wait_for("message", timeout=60, check=check)
    except:
        await ctx.send("No one claimed the role.")
        return

    role = discord.utils.get(ctx.guild.roles, name=role_name)

    if role:
        await reply.author.add_roles(role)

        win = magic_embed("Winner", "User", reply.author.mention)

        await ctx.send(embed=win)


# ---------------- TIME SYSTEM ---------------- #

@bot.hybrid_group(invoke_without_command=True)
async def time(ctx, member: discord.Member = None):

    data = load_times()

    # If no member is provided, show the author's time
    member = member or ctx.author

    tz = data.get(str(member.id))

    if not tz:
        if member == ctx.author:
            await ctx.send("❌ You haven't set a timezone.\nUse `.time set <timezone>`")
        else:
            await ctx.send(f"❌ {member.display_name} hasn't set a timezone.")
        return

    now = datetime.datetime.now(
        pytz.timezone(tz)
    ).strftime("%H:%M")

    embed = discord.Embed(
        title=f"🕒 Time for {member.display_name}",
        description=f"`{now}` • {tz}",
        color=discord.Color.blurple()
    )

    await ctx.send(embed=embed)
# ---------------- HELP ---------------- #

@bot.hybrid_command()
async def help(ctx):

    embed = discord.Embed(
        title="Doctor Strange Utility Bot",
        description="Prefix: `.`",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Utility",
        value="avatar • serverinfo • uptime",
        inline=False
    )

    embed.add_field(
        name="Fun",
        value="8ball • choose • match",
        inline=False
    )

    embed.add_field(
        name="Tracking",
        value="weekly",
        inline=False
    )

    embed.add_field(
        name="Time",
        value="time • time set • time remove",
        inline=False
    )

    embed.add_field(
        name="Moderation",
        value="blacklist • unblacklist",
        inline=False
    )

    embed.set_footer(text="/YILDIZ Bot")

    await ctx.send(embed=embed)


    # ---------------- SHUTDOWN ---------------- #

@bot.command()
async def shutdown(ctx):

    if ctx.author.id != CREATOR_ID:
        return

    embed = discord.Embed(
        description="Shutting down... 👋🏼",
        color=discord.Color.red()
    )

    await ctx.send(embed=embed)

    await bot.close()


# ---------------- RUN ---------------- #

bot.run(TOKEN)