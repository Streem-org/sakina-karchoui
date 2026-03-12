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
from discord.ui import View
import pytz
import psutil
import random

from PIL import Image, ImageDraw, ImageFont
import aiohttp
from io import BytesIO

bot_start_time = datetime.datetime.utcnow()

# ---------------- ENV ---------------- #

load_dotenv()
TOKEN = os.getenv("TOKEN")

CREATOR_ID = 1378768035187527795
COUNTING_CHANNEL = 1477918309696667800
STAFF_EVIDENCE_CHANNEL = 1481206250623598725
ROLEDROP_USERS = 1378768035187527795, 1214001826127421440

TIME_FILE = "times.json"

# ---------------- DATA ---------------- #

start_time = time.time()

afk_users = {}
weekly_messages = defaultdict(int)

count_number = 0
last_counter = None

duos = {}

eightball_responses = [
"Yes","No","Ask again later",
"It is certain","Reply hazy, try later",
"Not in the mood shut the fuck up", "I forgot the question"
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

# ---------------- FILE ---------------- #

if not os.path.exists(TIME_FILE):
    with open(TIME_FILE,"w") as f:
        json.dump({},f)

def load_times():
    with open(TIME_FILE,"r") as f:
        return json.load(f)

def save_times(data):
    with open(TIME_FILE,"w") as f:
        json.dump(data,f,indent=4)

# ---------------- EVENTS ---------------- #

@bot.event
async def on_ready():
    await bot.change_presence(
        status=discord.Status.dnd,
        activity=discord.Game(name="Jarvis protocols")
    )
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):

    global count_number,last_counter

    if message.author.bot:
        return

    weekly_messages[message.author.id]+=1



    # COUNTING
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

# ---------------- HELP ---------------- #

@bot.command()
async def help(ctx):

    embed = discord.Embed(
        title="Bot Commands",
        description="Prefix: `.`",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Utility",
        value="`.avatar`\n`.uptime`\n`.afk`",
        inline=False
    )

    embed.add_field(
        name="Time",
        value="`.time`\n`.timeset`\n`.timeremove`",
        inline=False
    )

    embed.add_field(
        name="Duo",
        value="`.match @user`\n`.us`\n`.unmatch`",
        inline=False
    )

    embed.add_field(
        name="Moderation",
        value="`.ev p` (reply message)",
        inline=False
    )
    embed.add_field(
        name="Fun",
        value="`.8ball`\n`.ship`\n`.choose`",
        inline=False
    )

    embed.add_field(
        name="Admin Only",
        value="`.blacklist`\n`.unblacklist`\n`.shutdown`",
        inline=False
    )

    await ctx.send(embed=embed)

# ---------------- AFK ---------------- #
import discord
from discord.ext import commands
from discord.ui import View

afk_users = {}
afk_pings = {}

class AFKReturnView(View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.button(label="Show Pings", style=discord.ButtonStyle.green)
    async def show_pings(self, interaction: discord.Interaction, button: discord.ui.Button):

        pings = afk_pings.get(self.user_id, [])

        if not pings:
            await interaction.response.send_message(
                "No one pinged you while you were AFK.",
                ephemeral=True
            )
        else:
            msg = "\n".join(pings[:10])
            await interaction.response.send_message(
                f"People who pinged you:\n{msg}",
                ephemeral=True
            )

    @discord.ui.button(label="Close", style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()


@bot.command()
async def afk(ctx, *, reason="AFK"):

    afk_users[ctx.author.id] = reason
    afk_pings[ctx.author.id] = []

    embed = discord.Embed(
        title="You're now AFK!",
        description=f"Reason: **{reason}**",
        color=discord.Color.blurple()
    )

    embed.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar.url)

    await ctx.send(embed=embed)


@bot.event
async def on_message(message):

    if message.author.bot:
        return

    # Remove AFK when user talks
    if message.author.id in afk_users:

        del afk_users[message.author.id]

        embed = discord.Embed(
            description="**Your AFK has been removed!**",
            color=discord.Color.red()
        )

        view = AFKReturnView(message.author.id)

        await message.channel.send(
            content=message.author.mention,
            embed=embed,
            view=view
        )

    # Detect mentions of AFK users
    for user in message.mentions:

        if user.id in afk_users:

            reason = afk_users[user.id]

            if user.id not in afk_pings:
                afk_pings[user.id] = []

            afk_pings[user.id].append(
                f"{message.author} in {message.channel.mention}"
            )

            embed = discord.Embed(
                description=f"{user.mention} is currently **AFK**",
                color=discord.Color.orange()
            )

            embed.add_field(
                name="Reason",
                value=reason,
                inline=False
            )

            await message.channel.send(embed=embed)

    await bot.process_commands(message)

# ---------------- TIME ---------------- #

@bot.command()
async def time(ctx):

    data = load_times()
    tz = data.get(str(ctx.author.id))

    if not tz:
        await ctx.send("Use `.timeset <timezone>` first.")
        return

    now=datetime.datetime.now(
        pytz.timezone(tz)
    ).strftime("%I:%M %p")

    await ctx.send(f"Your time: **{now}** ({tz})")

@bot.command()
async def timeset(ctx, timezone:str):

    try:
        pytz.timezone(timezone)
    except:
        await ctx.send("Invalid timezone.")
        return

    data = load_times()
    data[str(ctx.author.id)] = timezone
    save_times(data)

    await ctx.send(f"Timezone set to **{timezone}**")

@bot.command()
async def timeremove(ctx):

    data = load_times()
    data.pop(str(ctx.author.id),None)
    save_times(data)

    await ctx.send("Timezone removed.")

# ---------------- UTILITY ---------------- #



@bot.command()
async def uptime(ctx):

    now = datetime.datetime.utcnow()

    # Bot uptime
    bot_uptime = now - bot_start_time
    bot_days = bot_uptime.days
    bot_hours, remainder = divmod(bot_uptime.seconds, 3600)
    bot_minutes, bot_seconds = divmod(remainder, 60)

    # System uptime
    boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
    system_uptime = now - boot_time
    sys_days = system_uptime.days
    sys_hours, remainder = divmod(system_uptime.seconds, 3600)
    sys_minutes, sys_seconds = divmod(remainder, 60)

    embed = discord.Embed(
        title="Uptime Information",
        color=discord.Color.blurple()
    )

    embed.description = (
        f"I was last rebooted `{bot_days} days ago`\n\n"
        f"**Bot Uptime**\n"
        f"{bot_days} days, {bot_hours} hours, {bot_minutes} minutes, {bot_seconds} seconds\n"
        f"• {bot_start_time.strftime('%d %B %Y %I:%M %p')}\n\n"
        f"**System Uptime**\n"
        f"{sys_days} days, {sys_hours} hours, {sys_minutes} minutes, {sys_seconds} seconds\n"
        f"• {boot_time.strftime('%d %B %Y %I:%M %p')}"
    )

    embed.set_footer(
        text=f"Requested by {ctx.author}",
        icon_url=ctx.author.avatar.url
    )

    await ctx.send(embed=embed)

@bot.command()
async def avatar(ctx,member:discord.Member=None):

    member = member or ctx.author

    embed = discord.Embed(
        title=f"{member.name}'s Avatar",
        color=discord.Color.blurple()
    )

    embed.set_image(url=member.display_avatar.url)

    await ctx.send(embed=embed)

# ---------------- FUN ---------------- #

@bot.command(name="8ball")
async def eightball(ctx, *, question):
    question_lower = question.lower()

    reply = random.choice(eightball_responses)

    if "are you gay" in question_lower or "are u gay" in question_lower:
        reply = "I may or may not be gay, but you seem to be."

    embed = discord.Embed(
        title="Magic 8ball",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Question",
        value=question,
        inline=False
    )

    embed.add_field(
        name="Answer",
        value=reply,
        inline=False
    )

    embed.set_thumbnail(url="https://upload.wikimedia.org/wikipedia/commons/e/eb/Magic_eight_ball.png")

    await ctx.send(embed=embed)

# ---------------- EVIDENCE ---------------- #

@bot.group()
async def ev(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.message.delete()

@ev.command()
async def p(ctx):

    if not ctx.message.reference:
        await ctx.message.delete()
        return

    ref = ctx.message.reference
    msg = await ctx.channel.fetch_message(ref.message_id)

    staff_channel = bot.get_channel(STAFF_EVIDENCE_CHANNEL)

    embed = discord.Embed(
        description=f"**{msg.author}:**\n{msg.content}",
        color=discord.Color.dark_theme()
    )

    files=[]
    for a in msg.attachments:
        files.append(await a.to_file())

    await staff_channel.send(embed=embed,files=files)

    await ctx.message.delete()

# ---------------- MATCH SYSTEM ---------------- #

class MatchConfirm(discord.ui.View):

    def __init__(self, requester, target):
        super().__init__(timeout=60)
        self.requester=requester
        self.target=target

    @discord.ui.button(label="Match Creation Confirmed",style=discord.ButtonStyle.green)
    async def confirm(self,interaction:discord.Interaction,button:discord.ui.Button):

        if interaction.user!=self.target:
            await interaction.response.send_message(
                "Only the tagged user can confirm.",
                ephemeral=True
            )
            return

        duos[self.requester.id]=self.target.id
        duos[self.target.id]=self.requester.id

        embed=discord.Embed(
            title="Match Created",
            description=f"{self.requester.mention} 🤝 {self.target.mention}",
            color=discord.Color.green()
        )

        await interaction.response.edit_message(embed=embed,view=None)

@bot.command()
async def match(ctx,member:discord.Member):

    if member.bot:
        await ctx.send("You can't match bots.")
        return

    if member==ctx.author:
        await ctx.send("You can't match yourself.")
        return

    if ctx.author.id in duos:
        await ctx.send("You already have a duo.")
        return

    if member.id in duos:
        await ctx.send("That user already has a duo.")
        return

    embed=discord.Embed(
        title="Are you sure?",
        description=f"{ctx.author.mention}\n{member.mention}\n\nConfirm match creation.",
        color=discord.Color.blurple()
    )

    view=MatchConfirm(ctx.author,member)

    await ctx.send(embed=embed,view=view)

@bot.command()
async def us(ctx):

    if ctx.author.id not in duos:
        await ctx.send("You don't have a duo yet.")
        return

    partner_id=duos[ctx.author.id]
    partner=ctx.guild.get_member(partner_id)

    embed=discord.Embed(
        title="Duo Team",
        description=f"{ctx.author.mention} 🤝 {partner.mention}",
        color=discord.Color.blurple()
    )

    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    embed.set_image(url=partner.display_avatar.url)

    await ctx.send(embed=embed)

@bot.command()
async def unmatch(ctx):

    if ctx.author.id not in duos:
        await ctx.send("You don't have a duo.")
        return

    partner_id=duos[ctx.author.id]

    duos.pop(ctx.author.id,None)
    duos.pop(partner_id,None)

    partner=ctx.guild.get_member(partner_id)

    await ctx.send(
        f"{ctx.author.mention} and {partner.mention} are no longer matched."
    )
#------------- SHIP --------------#

@bot.command()
async def ship(ctx, member: discord.Member = None):

    user1 = ctx.author
    user2 = member or ctx.author

    if user1 == user2:
        await ctx.send("You need to ship with someone else.")
        return

    percent = random.randint(0,100)

    filled = int(percent / 10)
    bar = "█" * filled + "░" * (10 - filled)

    embed = discord.Embed(
        title=f"{user1.name} ❤️ {user2.name}",
        description=f"`{bar}` **{percent}%**",
        color=discord.Color.blurple()
    )

    embed.set_thumbnail(url=user1.display_avatar.url)
    embed.set_image(url=user2.display_avatar.url)

    embed.set_footer(
        text=ctx.guild.name,
        icon_url=ctx.guild.icon.url if ctx.guild.icon else None
    )

    await ctx.send(embed=embed)

    # ---------------- ROLE DROP ---------------- #

@bot.hybrid_command()
async def roledrop(ctx, role: discord.Role):

    if ctx.author.id not in ROLEDROP_USERS:
        await ctx.send("You cannot start a role drop.")
        return

    embed = discord.Embed(
        title="Role Drop",
        description=f"First person to send **any message** wins {role.mention}!",
        color=discord.Color.gold()
    )

    embed.set_footer(
        text=ctx.guild.name,
        icon_url=ctx.guild.icon.url if ctx.guild.icon else None
    )

    await ctx.send("@everyone")
    await ctx.send(embed=embed)

    def check(m):
        return (
            m.channel == ctx.channel
            and not m.author.bot
        )

    try:
        msg = await bot.wait_for("message", timeout=30, check=check)

        await msg.author.add_roles(role)

        win = discord.Embed(
            description=f"{msg.author.mention} won **{role.name}**!",
            color=discord.Color.green()
        )

        win.set_footer(text=ctx.guild.name)

        await ctx.send(embed=win)

    except:
        await ctx.send("No one claimed the role in time.")

# ---------------- RUN ---------------- #

bot.run(TOKEN)