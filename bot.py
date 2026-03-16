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

TOKEN = os.getenv("TOKEN")

PREFIX = "."
MAIN_SERVER = 1469526303148609720

TIME_FILE = "times.json"
WEEKLY_FILE = "weekly.json"
BLACKLIST_FILE = "blacklist.json"
AUTOREACT_FILE = "autoreactions.json"

ALLOWED_SERVERS = [
1469526303148609720,
1386245608184090795,
1479551809080135763
]

GENERAL_CHANNEL = 1469526304738119940
HOST_ROLE = 1481903901656481812


# ---------------- FILE SYSTEM ---------------- #

def load_json(file):
    try:
        with open(file,"r") as f:
            return json.load(f)
    except:
        return {}

def save_json(file,data):
    with open(file,"w") as f:
        json.dump(data,f,indent=4)

times = load_json(TIME_FILE)
weekly_data = load_json(WEEKLY_FILE)
blacklisted_users = load_json(BLACKLIST_FILE)
autoreactions = load_json(AUTOREACT_FILE)

weekly_messages = defaultdict(int)
afk_users = {}

start_time = time.time()

eightball_responses = [
"Yes","No","Ask again later","It is certain",
"Ok bro as u wish","Not in the mood","I forgot the question"
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


# ---------------- SERVER WHITELIST ---------------- #

@bot.event
async def on_guild_join(guild):

    if guild.id not in ALLOWED_SERVERS:
        await guild.leave()


@bot.event
async def on_ready():

    for guild in bot.guilds:
        if guild.id not in ALLOWED_SERVERS:
            await guild.leave()

    print(f"Logged in as {bot.user}")

    await bot.change_presence(
        status=discord.Status.dnd,
        activity=discord.Game("Training again")
    )

    weekly_reset.start()
    bot.loop.create_task(terminal_commands())



# ---------------- WEEKLY RESET ---------------- #

@tasks.loop(hours=168)
async def weekly_reset():

    global weekly_data

    weekly_data = {}
    weekly_messages.clear()

    save_json(WEEKLY_FILE,weekly_data)


# ---------------- MESSAGE EVENT ---------------- #

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if str(message.author.id) in blacklisted_users:
        return

    weekly_messages[message.author.id]+=1
    weekly_data[str(message.author.id)] = weekly_messages[message.author.id]

    save_json(WEEKLY_FILE,weekly_data)

    if message.author.id in afk_users:

        del afk_users[message.author.id]

        embed = discord.Embed(
        title="AFK Removed",
        description=f"{message.author.mention} is no longer AFK",
        color=discord.Color.green()
        )

        await message.channel.send(embed=embed)

    for user in message.mentions:

        if user.id in afk_users:

            embed = discord.Embed(
            title="User AFK",
            description=f"{user.mention} is AFK\nReason: {afk_users[user.id]}",
            color=discord.Color.orange()
            )

            await message.channel.send(embed=embed)

    # AUTOREACTIONS
    for phrase,emoji in autoreactions.items():

        if phrase in message.content.lower():

            try:
                await message.add_reaction(emoji)
            except:
                pass

    await bot.process_commands(message)


# ---------------- HELP ---------------- #

@bot.hybrid_command()
async def help(ctx):

    embed = discord.Embed(
    title="Otis Khan Command Panel",
    description="Prefix: `.`  |  Slash supported",
    color=discord.Color.dark_green()
    )

    embed.add_field(
    name="Utility",
    value="""
`.avatar` - View User Avatar
`.uptime` - Bot Uptime Status
`.time` - View your time
`.time set` - Set your timezone
`.afk` - Enable AFK
`.roleinfo`- View a specific role detail
`.serverinfo`- View server detail
""",
    inline=False
    )

    embed.add_field(
    name="Fun",
    value="""
`.8ball`- Ask the bot random ahh questions (may lead to bot give some egoistic reply)
`.ship` - Make some random couples
`.choose`- Choose between options coz Otis Khan is wise
""",
    inline=False
    )

    embed.add_field(
    name="Server",
    value="""
`.wk`- Weekly Leaderboard
`.wk p`- View how nolifer are you
""",
    inline=False
    )

    embed.add_field(
    name="Admin",
    value="""
`.blacklist`
`.unblacklist`
`.say`
`.roledrop`
`.autoreaction add`
""",
    inline=False
    )

    await ctx.reply(embed=embed)


# ---------------- AUTOREACTION COMMANDS ---------------- #

@bot.hybrid_group(name="autoreaction",invoke_without_command=True)
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
async def autoreaction_add(ctx,phrase:str,emoji:str):

    autoreactions[phrase.lower()] = emoji
    save_json(AUTOREACT_FILE,autoreactions)

    embed = discord.Embed(
    title="Autoreaction Added",
    description=f"`{phrase}` → {emoji}",
    color=discord.Color.green()
    )

    await ctx.reply(embed=embed)


@autoreaction.command(name="remove")
async def autoreaction_remove(ctx,phrase:str):

    autoreactions.pop(phrase.lower(),None)
    save_json(AUTOREACT_FILE,autoreactions)

    embed = discord.Embed(
    title="Autoreaction Removed",
    color=discord.Color.red()
    )

    await ctx.reply(embed=embed)


@autoreaction.command(name="list")
async def autoreaction_list(ctx):

    if not autoreactions:
        return await ctx.reply("No autoreactions set.")

    text=""

    for phrase,emoji in autoreactions.items():
        text += f"`{phrase}` → {emoji}\n"

    embed = discord.Embed(
    title="Autoreaction List",
    description=text,
    color=discord.Color.blurple()
    )

    await ctx.reply(embed=embed)


# ---------------- UPTIME ---------------- #

@bot.hybrid_command(name="uptime")
async def uptime(ctx):

    now = int(time.time())

    bot_uptime_seconds = int(time.time() - start_time)
    bot_reboot_time = now - bot_uptime_seconds

    system_boot = int(psutil.boot_time())
    system_uptime_seconds = now - system_boot

    bot_uptime = str(datetime.timedelta(seconds=bot_uptime_seconds))
    system_uptime = str(datetime.timedelta(seconds=system_uptime_seconds))

    embed = discord.Embed(
    title="Uptime Information",
    color=discord.Color.dark_teal()
    )

    embed.description = (
    f"**I was last rebooted <t:{bot_reboot_time}:R>.**\n\n"
    f"**Bot Uptime**\n{bot_uptime}\n"
    f"• <t:{bot_reboot_time}:f>\n\n"
    f"**System Uptime**\n{system_uptime}\n"
    f"• <t:{system_boot}:f>"
    )

    await ctx.reply(embed=embed)


# ---------------- AVATAR ---------------- #

@bot.hybrid_command()
async def avatar(ctx,member:discord.Member=None):

    member = member or ctx.author

    embed = discord.Embed(
    title=f"{member.name}'s Avatar",
    color=discord.Color.blurple()
    )

    embed.set_image(url=member.display_avatar.url)

    await ctx.reply(embed=embed)


# ---------------- SAY ---------------- #

@bot.hybrid_command()
@commands.has_permissions(manage_messages=True)
async def say(ctx,*,message:str):

    await ctx.message.delete()

    channel = bot.get_channel(GENERAL_CHANNEL)

    if channel:
        await channel.send(message)

@bot.hybrid_command(name="roleinfo")
async def roleinfo(ctx, role: discord.Role):

    embed = discord.Embed(
        title=f"Role Info - {role.name}",
        color=role.color if role.color != discord.Color.default() else discord.Color.blurple()
    )

    embed.add_field(name="Role Name", value=role.name, inline=True)
    embed.add_field(name="Role ID", value=role.id, inline=True)
    embed.add_field(name="Members", value=len(role.members), inline=True)

    embed.add_field(
        name="Created On",
        value=role.created_at.strftime("%d %B %Y"),
        inline=False
    )

    embed.set_footer(text=f"Requested by {ctx.author}")

    await ctx.reply(embed=embed)

@bot.hybrid_command(name="serverinfo")
async def serverinfo(ctx):

    guild = ctx.guild

    embed = discord.Embed(
        title=f"{guild.name} Server Info",
        color=discord.Color.gold()
    )

    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)

    embed.add_field(name="Server Name", value=guild.name, inline=True)
    embed.add_field(name="Server ID", value=guild.id, inline=True)
    embed.add_field(name="Owner", value=guild.owner, inline=True)

    embed.add_field(name="Members", value=guild.member_count, inline=True)
    embed.add_field(name="Roles", value=len(guild.roles), inline=True)
    embed.add_field(name="Channels", value=len(guild.channels), inline=True)

    embed.add_field(
        name="Created On",
        value=guild.created_at.strftime("%d %B %Y"),
        inline=False
    )

    embed.set_footer(text=f"Requested by {ctx.author}")

    await ctx.reply(embed=embed)


bot.run(TOKEN)