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
from discord import ui, ButtonStyle

TOKEN = os.getenv("TOKEN")

PREFIX = "."
MAIN_SERVER = 1469526303148609720

TIME_FILE = "times.json"
WEEKLY_FILE = "weekly.json"
BLACKLIST_FILE = "blacklist.json"

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

weekly_messages = defaultdict(int)
afk_users = {}

start_time = time.time()

eightball_responses = [
"Yes","No","Ask again later","It is certain",
"My Dev said no","Not in the mood","I forgot the question"
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

    await bot.tree.sync()

    await bot.change_presence(
        status=discord.Status.dnd,
        activity=discord.Game("Training again")
    )

    weekly_reset.start()
    bot.loop.create_task(terminal_commands())

# ---------------- TERMINAL COMMAND SYSTEM ---------------- #

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

    await bot.process_commands(message)

# ---------------- HELP ---------------- #
@bot.hybrid_command()
async def help(ctx):

    embed = discord.Embed(
        title="Otis Khan Command Panel",
        description="Prefix: `.`  |  Slash commands also supported",
        color=discord.Color.dark_green()
    )

    embed.add_field(
        name="🛠 Utility",
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
        name="📊 Server",
        value="""
`.wk` – Weekly leaderboard  
`.wk p @user` – Weekly stats
""",
        inline=False
    )

    embed.add_field(
        name="🔒 Moderation",
        value="""
`.blacklist @user` – Block user from commands  
`.unblacklist @user` – Remove blacklist  
`.reboot` – Restart bot
""",
        inline=False
    )

    embed.set_footer(text="Otis Khan • Advanced Utility Bot")

    await ctx.reply(embed=embed)
# ---------------- TIME ---------------- #

@bot.hybrid_command()
async def time(ctx,sub=None,*,value=None):

    if sub == "set":

        try:
            pytz.timezone(value)
        except:
            await ctx.send("Example: `.time set Asia/Kolkata`")
            return

        times[str(ctx.author.id)] = value
        save_json(TIME_FILE,times)

        embed = discord.Embed(
            title="Timezone Updated",
            description=f"Timezone set to **{value}**",
            color=discord.Color.orange()
        )

        await ctx.send(embed=embed)
        return

    member = ctx.message.mentions[0] if ctx.message.mentions else ctx.author

    if str(member.id) not in times:
        await ctx.send("Timezone not set.")
        return

    tz = pytz.timezone(times[str(member.id)])
    now = datetime.datetime.now(tz)

    embed = discord.Embed(
        title="User Time",
        color=discord.Color.purple()
    )

    embed.add_field(name="User",value=member.mention)
    embed.add_field(name="Time",value=now.strftime("%I:%M %p"))
    embed.add_field(name="Timezone",value=times[str(member.id)])

    await ctx.send(embed=embed)

# ---------------- WEEKLY ---------------- #

@bot.hybrid_command()
async def wk(ctx,sub=None,member:discord.Member=None):

    if ctx.guild.id != MAIN_SERVER:
        return

    if sub is None:

        sorted_data = sorted(
            weekly_data.items(),
            key=lambda x:x[1],
            reverse=True
        )

        text=""

        for i,(uid,msgs) in enumerate(sorted_data[:10],1):

            user = ctx.guild.get_member(int(uid))

            if user:
                text += f"**{i}. {user.name}** — {msgs} messages\n"

        embed = discord.Embed(
            title="Weekly Leaderboard",
            description=text,
            color=discord.Color.gold()
        )

        await ctx.send(embed=embed)

    elif sub == "p":

        member = member or ctx.author
        msgs = weekly_data.get(str(member.id),0)

        embed = discord.Embed(
            title="Weekly Stats",
            color=discord.Color.green()
        )

        embed.add_field(name="User",value=member.mention)
        embed.add_field(name="Messages",value=str(msgs))

        await ctx.send(embed=embed)

# ---------------- 8BALL ---------------- #

@bot.hybrid_command(name="8ball")
async def eightball(ctx, *, question):

    reply = random.choice(eightball_responses)

    if "are u gay" in question.lower():
        reply = "I may or may not be gay but you seem to be."

    embed = discord.Embed(
        title="Magic 8Ball",
        color=discord.Color.dark_purple()
    )

    embed.add_field(name="Question",value=question,inline=False)
    embed.add_field(name="Answer",value=reply,inline=False)

    await ctx.send(embed=embed)

# ---------------- SHIP ---------------- #

@bot.hybrid_command()
async def ship(ctx,u1:discord.Member,u2:discord.Member):

    percent = random.randint(0,100)

    embed = discord.Embed(
        title="Ship Result",
        color=discord.Color.red()
    )

    embed.add_field(
        name="Couple",
        value=f"{u1.mention} ❤️ {u2.mention}",
        inline=False
    )

    embed.add_field(
        name="Compatibility",
        value=f"{percent}%",
        inline=False
    )

    await ctx.send(embed=embed)

# ---------------- BLACKLIST ---------------- #

@bot.hybrid_command()
@commands.has_permissions(administrator=True)
async def blacklist(ctx,member:discord.Member):

    blacklisted_users[str(member.id)] = True
    save_json(BLACKLIST_FILE,blacklisted_users)

    embed = discord.Embed(
        title="User Blacklisted, Sounds like a skill issue",
        description=f"{member.mention} cannot use commands",
        color=discord.Color.red()
    )

    await ctx.send(embed=embed)

@bot.hybrid_command()
@commands.has_permissions(administrator=True)
async def unblacklist(ctx,member:discord.Member):

    blacklisted_users.pop(str(member.id),None)
    save_json(BLACKLIST_FILE,blacklisted_users)

    embed = discord.Embed(
        title="User Unblacklisted",
        description=f"{member.mention} can use commands again",
        color=discord.Color.green()
    )

    await ctx.send(embed=embed)

# ---------------- REBOOT ---------------- #

@bot.hybrid_command()
@commands.is_owner()
async def reboot(ctx):

    embed = discord.Embed(
        title="Rebooting",
        description="Bot restarting...",
        color=discord.Color.orange()
    )

    await ctx.send(embed=embed)

    os.execv(__file__,["python"]+os.sys.argv)
# ---------------- UPTIME ---------------- #
@bot.hybrid_command(name="uptime")
async def uptime(ctx):

    now = int(time.time())

    # bot uptime
    bot_uptime_seconds = int(time.time() - start_time)
    bot_reboot_time = now - bot_uptime_seconds

    # system uptime
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
        f"**Bot Uptime**\n"
        f"{bot_uptime}\n"
        f"• <t:{bot_reboot_time}:f>\n\n"
        f"**System Uptime**\n"
        f"{system_uptime}\n"
        f"• <t:{system_boot}:f>"
    )

    embed.set_footer(
        text=f"Requested by {ctx.author} • Today at {datetime.datetime.now().strftime('%I:%M %p')}"
    )

    await ctx.reply(embed=embed)
    # ---------------- CHOOSE ---------------- #
@bot.hybrid_command()
async def choose(ctx, *, options: str):

    choices = [c.strip() for c in options.split(",") if c.strip()]

    if len(choices) < 2:
        await ctx.reply("Provide choices separated by commas.\nExample: `.choose pizza, burger, pasta`")
        return

    choice = random.choice(choices)

    embed = discord.Embed(
        title="Otis Khan Decision Engine",
        description=f"I choose **{choice}**",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Choices",
        value=", ".join(choices),
        inline=False
    )

    await ctx.reply(embed=embed)

HOST_ROLE = 1481903901656481812  # hoster role (whitelisted)

@bot.hybrid_command(name="roledrop")
@commands.has_role(HOST_ROLE)
async def roledrop(ctx, role: discord.Role):

    # Prevent dropping the hoster role
    if role.id == HOST_ROLE:
        await ctx.reply("This role cannot be dropped.")
        return

    embed = discord.Embed(
        title="Role Drop",
        description=f"Reply to this message to claim {role.mention}",
        color=discord.Color.gold()
    )

    msg = await ctx.send("@everyone", embed=embed)

    def check(m):
        return (
            m.reference
            and m.reference.message_id == msg.id
            and m.author != bot.user
        )

    while True:
        try:
            reply = await bot.wait_for("message", timeout=120, check=check)

            await reply.author.add_roles(role)

            await reply.reply(
                embed=discord.Embed(
                    description=f"You received {role.mention}",
                    color=discord.Color.green()
                )
            )

        except:
            break





@bot.hybrid_command(name="avatar", description="View a user's avatar with options")
async def avatar(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author

    # Determine avatar URL (animated if possible)
    avatar_url = member.avatar.url

    embed = discord.Embed(
        title=f"{member.name}'s Avatar",
        description=f"[Click here to open full avatar]({avatar_url})",
        color=discord.Color.blurple()
    )
    embed.set_image(url=avatar_url)
    embed.set_footer(text="Otis Khan Bot System")

    # Buttons for avatar
    class AvatarButtons(ui.View):
        def __init__(self):
            super().__init__(timeout=None)  # buttons never timeout

        @ui.button(label="Open Avatar", style=ButtonStyle.link, url=avatar_url)
        async def open_avatar(self, interaction, button):
            pass  # link button doesn't need action

        @ui.button(label="Download PNG", style=ButtonStyle.secondary)
        async def download_png(self, interaction, button):
            await interaction.response.send_message(f"Here is the PNG version: {member.avatar.with_format('png').url}", ephemeral=True)

        @ui.button(label="Download JPEG", style=ButtonStyle.secondary)
        async def download_jpeg(self, interaction, button):
            await interaction.response.send_message(f"Here is the JPEG version: {member.avatar.with_format('jpeg').url}", ephemeral=True)

        @ui.button(label="Download WebP", style=ButtonStyle.secondary)
        async def download_webp(self, interaction, button):
            await interaction.response.send_message(f"Here is the WebP version: {member.avatar.with_format('webp').url}", ephemeral=True)

    await ctx.send(embed=embed, view=AvatarButtons())
bot.run(TOKEN)

