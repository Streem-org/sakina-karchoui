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
last_reboot = time.time()

def format_time(seconds):
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    return f"{days} days, {hours} hours, {minutes} minutes, {secs} seconds"


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
    guild_id = ctx.guild.id
    user_id = ctx.author.id

    afk_users.setdefault(guild_id, {})
    afk_mentions.setdefault(guild_id, {})

    afk_users[guild_id][user_id] = {
        "reason": reason,
        "since": int(time.time())
    }

    afk_mentions[guild_id][user_id] = []

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
@bot.command()
async def uptime(ctx):
    bot_uptime = time.time() - start_time
    system_uptime = time.time() - psutil.boot_time()

    embed = discord.Embed(
        title="Uptime Information",
        color=discord.Color.dark_grey()
    )

    embed.add_field(
        name="Bot Uptime",
        value=f"{format_time(bot_uptime)}\n• <t:{int(start_time)}:F>",
        inline=False
    )

    embed.add_field(
        name="System Uptime",
        value=f"{format_time(system_uptime)}\n• <t:{int(psutil.boot_time())}:F>",
        inline=False
    )

    embed.set_footer(text=f"Requested by {ctx.author}")

    await ctx.send(embed=embed)

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
    guild_id = str(ctx.guild.id)

    autoreactions.setdefault(guild_id, {})
    autoreactions[guild_id][phrase.lower()] = emoji

    save_json(AUTOREACT_FILE, autoreactions)
    await ctx.reply(f"Added: {phrase} → {emoji}")

@autoreaction.command(name="remove")
async def autoreaction_remove(ctx, phrase: str):
    guild_id = str(ctx.guild.id)

    if guild_id in autoreactions and phrase.lower() in autoreactions[guild_id]:
        autoreactions[guild_id].pop(phrase.lower())
        save_json(AUTOREACT_FILE, autoreactions)
        await ctx.reply("Removed.")
    else:
        await ctx.reply("⚠️ Not found.")

@autoreaction.command(name="list")
async def autoreaction_list(ctx):
    guild_id = str(ctx.guild.id)

    if guild_id not in autoreactions or not autoreactions[guild_id]:
        return await ctx.reply("No autoreactions set.")

    text = "\n".join([f"{p} → {e}" for p, e in autoreactions[guild_id].items()])

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

    # ---------------- TIME CULTURE ---------------- #
@time_cmd.command(name="culture")
async def time_culture(ctx, timezone: str = None):

    member = ctx.author

    if not timezone:
        if str(member.id) not in times:
            return await ctx.reply("❌ Set timezone first using `.time set <zone>`")
        timezone = times[str(member.id)]

    try:
        tz = pytz.timezone(timezone)
    except:
        return await ctx.reply("❌ Invalid timezone.")

    now = datetime.datetime.now(tz)
    hour = now.hour

    # -------- FUNNY CULTURE LOGIC -------- #

    # 🇮🇳 INDIA
    if "Kolkata" in timezone or "India" in timezone:
        if 6 <= hour < 10:
            culture = "☀️ Waking up + chai stronger than your life decisions."
        elif 10 <= hour < 17:
            culture = "🏫 Pretending to work while thinking about food."
        elif 17 <= hour < 20:
            culture = "☕ Evening chai break — legally required."
        else:
            culture = "🌙 Late night reels + overthinking everything."

    # 🇵🇰 PAKISTAN
    elif "Karachi" in timezone or "Pakistan" in timezone:
        if 6 <= hour < 10:
            culture = "☀️ Breakfast + planning to fix life (won’t happen)."
        elif 10 <= hour < 17:
            culture = "🏢 Work hours + random chai breaks."
        elif 17 <= hour < 21:
            culture = "🍵 Tea + gossip session unlocked."
        else:
            culture = "🌙 Late night vibes + existential crisis."

    # 🇺🇸 USA
    elif "America" in timezone:
        if 6 <= hour < 10:
            culture = "☕ Coffee carrying the entire personality."
        elif 10 <= hour < 17:
            culture = "💼 Work + checking phone every 2 minutes."
        elif 17 <= hour < 21:
            culture = "🍔 Gym (optional) + food (mandatory)."
        else:
            culture = "🌙 Gaming / Netflix / 'just one more episode'."

    # 🇬🇧 UK
    elif "London" in timezone:
        if 6 <= hour < 10:
            culture = "☕ Tea first, problems later."
        elif 10 <= hour < 17:
            culture = "🏢 Work + complaining about weather."
        elif 17 <= hour < 21:
            culture = "🍽️ Dinner + more tea (of course)."
        else:
            culture = "🌙 Quiet night + overthinking politely."

    # 🇫🇷 FRANCE
    elif "Paris" in timezone:
        if 6 <= hour < 10:
            culture = "🥐 Croissant + judging everything silently."
        elif 10 <= hour < 17:
            culture = "🏢 Work but make it aesthetic."
        elif 17 <= hour < 21:
            culture = "🍷 Wine + pretending life is a movie."
        else:
            culture = "🌙 Late night elegance (or just scrolling)."

    # 🇦🇪 UAE
    elif "Dubai" in timezone:
        if 6 <= hour < 10:
            culture = "☀️ Early grind + luxury mindset."
        elif 10 <= hour < 17:
            culture = "🏢 Work + checking expensive cars outside."
        elif 17 <= hour < 21:
            culture = "🌆 Mall trips + flex culture."
        else:
            culture = "🌙 Late night drives + vibes."

    # 🇯🇵 JAPAN
    elif "Tokyo" in timezone:
        if 6 <= hour < 10:
            culture = "🍙 Commute + silent train vibes."
        elif 10 <= hour < 18:
            culture = "🏢 Work mode: max discipline."
        elif 18 <= hour < 22:
            culture = "🍜 Ramen + anime + city lights."
        else:
            culture = "🌙 Quiet night + deep thoughts."

    # 🇦🇺 AUSTRALIA
    elif "Sydney" in timezone:
        if 6 <= hour < 10:
            culture = "🌅 Beach, coffee, and good vibes."
        elif 10 <= hour < 17:
            culture = "🏢 Work… kinda."
        elif 17 <= hour < 21:
            culture = "🍻 Chill time with friends."
        else:
            culture = "🌙 Sleep or random late chaos."

    # 🇩🇪 GERMANY
    elif "Berlin" in timezone:
        if 6 <= hour < 10:
            culture = "☀️ Efficient morning routine."
        elif 10 <= hour < 17:
            culture = "🏢 Productivity level: 100%."
        elif 17 <= hour < 21:
            culture = "🍺 Relax + structured fun."
        else:
            culture = "🌙 Quiet, organized night."

    # 🌍 DEFAULT
    else:
        if 6 <= hour < 12:
            culture = "☀️ Morning vibes + questionable decisions ahead."
        elif 12 <= hour < 18:
            culture = "🏢 Daytime productivity (or pretending)."
        elif 18 <= hour < 22:
            culture = "🌆 Relaxation + scrolling endlessly."
        else:
            culture = "🌙 Late night thoughts you didn't ask for."

    # -------- UTC FORMAT -------- #
    utc_offset = now.strftime('%z')
    utc_offset = f"UTC{utc_offset[:-2]}:{utc_offset[-2:]}" if utc_offset else "UTC"

    # -------- CLEAN EMBED -------- #
    embed = discord.Embed(
        description=(
            f"**Cultural Time Context — {timezone}**\n\n"
            f"**Current Time**\n"
            f"{now.strftime('%I:%M %p')} ({utc_offset})\n"
            f"{now.strftime('%A, %d %B %Y')}\n\n"
            f"**What's Happening Now**\n"
            f"{culture}\n\n"
            f"*Cultural notes are generalised — don’t take it personally 😭*"
        ),
        color=ctx.author.color if ctx.author.color != discord.Color.default() else 0x2b2d31
    )

    await ctx.reply(embed=embed)
    # ---------------- TIME COMPARE (USER BASED) ---------------- #
@time_cmd.command(name="compare")
async def time_compare(ctx, member: discord.Member = None):

    member = member or ctx.author

    # check both users have timezone
    if str(ctx.author.id) not in times:
        return await ctx.reply("❌ You haven't set your timezone. Use `.time set`")

    if str(member.id) not in times:
        return await ctx.reply(f"❌ {member.name} hasn't set their timezone.")

    tz1 = pytz.timezone(times[str(ctx.author.id)])
    tz2 = pytz.timezone(times[str(member.id)])

    now1 = datetime.datetime.now(tz1)
    now2 = datetime.datetime.now(tz2)

    # format UTC
    def format_utc(dt):
        offset = dt.strftime('%z')
        return f"UTC {offset[:3]}:{offset[3:]}" if offset else "UTC"

    # time difference
    diff = int((now1.utcoffset() - now2.utcoffset()).total_seconds() / 3600)

    if diff == 0:
        relation = "⇅ same time as you"
    elif diff > 0:
        relation = f"↑ {abs(diff)}h ahead of you"
    else:
        relation = f"↓ {abs(diff)}h behind you"

    embed = discord.Embed(
        description=(
            f"**Timezone Comparison**\n\n"

            f"**{ctx.author.display_name} (you)**\n"
            f"{now1.strftime('%H:%M')} ({format_utc(now1)})\n"
            f"{times[str(ctx.author.id)]}\n\n"

            f"**{member.display_name}**\n"
            f"{now2.strftime('%H:%M')} ({format_utc(now2)})\n"
            f"{times[str(member.id)]}\n"
            f"{relation}"
        ),
        color=ctx.author.color if ctx.author.color != discord.Color.default() else 0x2b2d31
    )

    await ctx.reply(embed=embed)
    # FIRST → CLASS
class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="Choose a category...",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label="Utility", emoji="🛠️"),
            discord.SelectOption(label="Fun", emoji="🎮"),
            discord.SelectOption(label="Moderation", emoji="🔒"),
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):

        choice = select.values[0]

        if choice == "Utility":
            embed = discord.Embed(
                title="🛠️ Utility Commands",
                description="""
`.avatar` – View avatar  
`.uptime` – Bot uptime  
`.time` – Check time  
`.time set` – Set timezone  
`.serverinfo` – Server info  
`.memberinfo` – Member info  
`.roleinfo` – Role info  
`.time culture` – Culture time  
`.time compare` – Compare time  
""",
                color=0x2b2d31
            )

        elif choice == "Fun":
            embed = discord.Embed(
                title="🎮 Fun Commands",
                description="""
`.8ball` – Ask questions  
`.ship` – Ship users  
`.choose` – Pick between options  
`.howhorny` – 💀  
""",
                color=0x2b2d31
            )

        elif choice == "Moderation":
            embed = discord.Embed(
                title="🔒 Moderation Commands",
                description="""
`.say` – Send message  
`.dm` – DM users  
`.ev p` – Evidence  
`.blacklist` – Block  
`.unblacklist` – Unblock  
`.reboot` – Restart  
`.shutdown` – Turn off  
""",
                color=0x2b2d31
            )

        await interaction.response.edit_message(embed=embed, view=self)


# SECOND → COMMAND
@bot.hybrid_command(name="help")
async def help_command(ctx):

    embed = discord.Embed(
        title="⚡ Sakina Karchaoui Command Panel",
        description="Select a category below 👇",
        color=0x1f6feb
    )

    embed.set_thumbnail(url=ctx.bot.user.display_avatar.url)

    await ctx.send(embed=embed, view=HelpView())

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

    # ---------------- AVATAR ---------------- #
# ---------------- AVATAR ---------------- #
@bot.hybrid_command(name="avatar")
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author

    embed = discord.Embed(
        color=member.color if member.color != discord.Color.default() else 0x2b2d31
    )

    # Title (Nickname)
    embed.title = f"Nickname: {member.display_name}"

    # Subtitle
    embed.description = f"**Avatar of {member.name}**"

    # Avatar image
    embed.set_image(url=member.display_avatar.url)

    # Footer with ID
    embed.set_footer(text=f"ID: {member.id}")

    await ctx.reply(embed=embed)
    # ---------------- REBOOT ---------------- #
# ---------------- REBOOT ---------------- #
@bot.hybrid_command(name="reboot")
async def reboot(ctx):

    if ctx.author.id != 1378768035187527795:
        return await ctx.reply("❌ You cannot use this command.")

    embed = discord.Embed(
        description="**Rebooting...**",
        color=ctx.author.color if ctx.author.color != discord.Color.default() else 0x2b2d31
    )

    embed.set_author(
        name=str(ctx.author),
        icon_url=ctx.author.display_avatar.url
    )

    await ctx.reply(embed=embed)

    await bot.close()
    os.execv(sys.executable, ['python'] + sys.argv)
# ---------------- DM ---------------- #
@bot.hybrid_command(name="dm")
async def dm(ctx, user: discord.User, *, message: str):

    # Dev only
    if ctx.author.id != 1378768035187527795:
        return await ctx.reply("❌ You cannot use this command.")

    try:
        await user.send(message)

        await ctx.reply(f"📩 Sent to {user.mention}")

    except:
        await ctx.reply("❌ Couldn't send DM (user may have DMs disabled).")

        # ---------------- CHOOSE ---------------- #
@bot.hybrid_command(name="choose")
async def choose(ctx, *, options: str):

    choices = [opt.strip() for opt in options.split(",") if opt.strip()]

    if len(choices) < 2:
        return await ctx.reply("❌ Give at least 2 options separated by commas.")

    result = random.choice(choices)

    embed = discord.Embed(
        description=(
            f"🎲 **Choice Made**\n\n"
            f"• {result}"
        ),
        color=ctx.author.color if ctx.author.color != discord.Color.default() else 0x2b2d31
    )

    embed.set_author(
        name=str(ctx.author),
        icon_url=ctx.author.display_avatar.url
    )

    await ctx.reply(embed=embed)
    # ---------------- MEMBER INFO ---------------- #
@bot.hybrid_command(name="memberinfo")
async def memberinfo(ctx, member: discord.Member = None):
    member = member or ctx.author

    embed = discord.Embed(
        title=str(member),
        color=member.color if member.color != discord.Color.default() else 0x2b2d31
    )

    embed.set_thumbnail(url=member.display_avatar.url)

    embed.add_field(name="ID", value=member.id, inline=False)
    embed.add_field(name="Joined Server", value=f"<t:{int(member.joined_at.timestamp())}:F>", inline=False)
    embed.add_field(name="Account Created", value=f"<t:{int(member.created_at.timestamp())}:F>", inline=False)

    roles = [role.mention for role in member.roles if role.name != "@everyone"]
    embed.add_field(name="Roles", value=", ".join(roles[:10]) if roles else "None", inline=False)

    embed.set_footer(text=f"Nickname: {member.display_name}")

    await ctx.reply(embed=embed)
    # ---------------- ROLE INFO ---------------- #
@bot.hybrid_command(name="roleinfo")
async def roleinfo(ctx, role: discord.Role):

    embed = discord.Embed(
        title=role.name,
        color=role.color if role.color != discord.Color.default() else 0x2b2d31
    )

    embed.add_field(name="ID", value=role.id, inline=False)
    embed.add_field(name="Members", value=len(role.members), inline=True)
    embed.add_field(name="Color", value=str(role.color), inline=True)
    embed.add_field(name="Created", value=f"<t:{int(role.created_at.timestamp())}:F>", inline=False)

    embed.add_field(name="Mentionable", value=role.mentionable, inline=True)
    embed.add_field(name="Hoisted", value=role.hoist, inline=True)

    embed.set_footer(text=f"Position: {role.position}")

    await ctx.reply(embed=embed)
    # ---------------- SERVER INFO ---------------- #
@bot.hybrid_command(name="serverinfo")
async def serverinfo(ctx):
    guild = ctx.guild

    embed = discord.Embed(
        title=guild.name,
        color=ctx.author.color if ctx.author.color != discord.Color.default() else 0x2b2d31
    )

    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)

    embed.add_field(name="Owner", value=guild.owner.mention, inline=True)
    embed.add_field(name="Members", value=guild.member_count, inline=True)
    embed.add_field(name="Created", value=f"<t:{int(guild.created_at.timestamp())}:F>", inline=False)

    embed.add_field(name="Channels", value=len(guild.channels), inline=True)
    embed.add_field(name="Roles", value=len(guild.roles), inline=True)

    embed.set_footer(text=f"ID: {guild.id}")

    await ctx.reply(embed=embed)
    from discord.ui import View, Button

# ---------------- EV ---------------- #
@bot.hybrid_command(name="ev")
async def ev(ctx, action: str):

    ROLE_ID = 1469526303580360821, 1469526303580360820, 1472523729006231703, 1469546698517778583, 1469546589444899050, 1469526303580360819, 1469526303580360818  # mod role (who can use command)
    EVIDENCE_CHANNEL_ID = 1481206250623598725  # evidence channel
    PING_ROLES = [111111111111111111, 222222222222222222]  # roles to ping

    # whitelist check
    if not any(role.id == ROLE_ID for role in ctx.author.roles):
        return await ctx.reply("❌ You are not authorized.")

    if action.lower() != "p":
        return

    # must be reply
    if not ctx.message.reference:
        return await ctx.reply("⚠️ Reply to a message to send evidence.")

    replied = ctx.message.reference.resolved
    if not replied:
        return await ctx.reply("⚠️ Couldn't fetch the message.")

    channel = bot.get_channel(EVIDENCE_CHANNEL_ID)

    # -------- EVIDENCE EMBED -------- #
    embed = discord.Embed(
        description=replied.content if replied.content else "",
        color=0x2b2d31
    )

    embed.set_author(
        name=str(replied.author),
        icon_url=replied.author.display_avatar.url
    )

    embed.add_field(
        name="Reported by",
        value=ctx.author.mention,
        inline=False
    )

    embed.add_field(
        name="Source",
        value=f"[Jump to message]({replied.jump_url})",
        inline=False
    )

    if replied.attachments:
        embed.set_image(url=replied.attachments[0].url)

    # role pings
    ping_text = " ".join(f"<@&{role_id}>" for role_id in PING_ROLES)

    sent_msg = await channel.send(content=ping_text, embed=embed)

    # -------- CONFIRMATION -------- #
    view = View()
    view.add_item(Button(label="Jump To Post", url=sent_msg.jump_url))

    confirm_embed = discord.Embed(
        description=f"**Evidence successfully posted.**\n\n{channel.mention}",
        color=ctx.author.color if ctx.author.color != discord.Color.default() else 0x2b2d31
    )

    await ctx.reply(embed=confirm_embed, view=view)

    # delete command message
    try:
        await ctx.message.delete()
    except:
        pass
# ---------------- HOWHORNY ---------------- #
@bot.hybrid_command(name="howhorny")
async def howhorny(ctx, member: discord.Member = None):
    member = member or ctx.author

    percent = random.randint(0, 100)

    # funny messages
    if percent >= 90:
        msg = "💀 Down horrendous"
    elif percent >= 70:
        msg = "😏 Chill bro..."
    elif percent >= 40:
        msg = "🙂 Slightly suspicious"
    else:
        msg = "😇 Innocent soul"

    embed = discord.Embed(
        description=(
            f"**{member.mention} is {percent}% horny**\n\n"
            f"{msg}"
        ),
        color=member.color if member.color != discord.Color.default() else 0x2b2d31
    )

    embed.set_author(
        name=str(ctx.author),
        icon_url=ctx.author.display_avatar.url
    )

    embed.set_thumbnail(url=member.display_avatar.url)

    await ctx.reply(embed=embed)

    # ---------------- SHUTDOWN ---------------- #
@bot.hybrid_command(name="shutdown")
async def shutdown(ctx):

    if ctx.author.id != 1378768035187527795:  # your ID
        return await ctx.reply("❌ You cannot use this command.")

    color = ctx.author.color if ctx.author.color != discord.Color.default() else 0x2b2d31

    embed = discord.Embed(
        title="🛑 Shutting Down",
        description="The bot is now going offline...",
        color=color
    )

    embed.set_footer(
        text=f"Shutdown requested by {ctx.author}",
        icon_url=ctx.author.display_avatar.url
    )

    await ctx.reply(embed=embed)

    await bot.close()

    # ---------------- UPDATES COMMAND ---------------- #

@bot.hybrid_command(name="updates")
async def updates(ctx):

    color = ctx.author.color if ctx.author.color != discord.Color.default() else 0x2b2d31

    embed = discord.Embed(
        title="🆕 Latest Updates",
        description="Here are the newest features added to the bot 🚀",
        color=color
    )

    embed.add_field(
        name="⚡ Version 2.0",
        value="""
🆕 Interactive Help Menu (Dropdown UI)  
🆕 `.time culture` (fun cultural system 🌍)  
🆕 `.time compare` (compare timezones)  
🆕 `.convert` (advanced currency converter 💱)  
🆕 Improved AFK system (better UI + tracking)  
🆕 Evidence system `.ev p`  
""",
        inline=False
    )

    embed.add_field(
        name="✨ Improvements",
        value="""
✔ Role-based embed colors  
✔ Cleaner UI across commands  
✔ Better uptime system  
✔ More stable autoreactions  
""",
        inline=False
    )

    embed.set_footer(
        text=f"Requested by {ctx.author}",
        icon_url=ctx.author.display_avatar.url
    )

    await ctx.send(embed=embed)
    OWNER_ID = 1378768035187527795  # your ID
LOG_CHANNEL_ID = 1484472574690852985 # optional (server log channel)


    # ---------------- ADVANCED CONVERT ---------------- #
@bot.hybrid_command(name="convert")
async def convert(ctx, amount: str, to_currency: str = "USD"):

    symbol_map = {
        "$": "USD",
        "₹": "INR",
        "€": "EUR",
        "£": "GBP",
        "¥": "JPY",
        "₩": "KRW",
        "₽": "RUB",
        "₺": "TRY",
        "₫": "VND",
        "₦": "NGN",
        "AED": "AED"
    }

    amount = amount.strip()

    # -------- AUTO DETECT -------- #
    from_currency = None

    for sym, code in symbol_map.items():
        if amount.startswith(sym):
            from_currency = code
            amount = amount.replace(sym, "")
            break

    # if no symbol → assume format: "100 INR"
    if not from_currency:
        parts = amount.split()

        if len(parts) == 2:
            amount, from_currency = parts
            from_currency = from_currency.upper()
        else:
            return await ctx.reply("❌ Format: `.convert 100 INR USD` or `.convert $100 EUR`")

    try:
        amount = float(amount)
    except:
        return await ctx.reply("❌ Invalid amount.")

    to_currency = to_currency.upper()

    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
        res = requests.get(url).json()

        if "rates" not in res or to_currency not in res["rates"]:
            return await ctx.reply("❌ Invalid currency code.")

        rate = res["rates"][to_currency]
        converted = amount * rate

    except:
        return await ctx.reply("❌ API error. Try again later.")

    # -------- EMBED -------- #
    embed = discord.Embed(
        title="💱 Currency Conversion",
        color=ctx.author.color if ctx.author.color != discord.Color.default() else 0x2b2d31
    )

    embed.add_field(
        name="From",
        value=f"{amount:.2f} {from_currency}",
        inline=True
    )

    embed.add_field(
        name="To",
        value=f"{converted:.2f} {to_currency}",
        inline=True
    )

    embed.add_field(
        name="Rate",
        value=f"1 {from_currency} = {rate:.4f} {to_currency}",
        inline=False
    )

    embed.set_footer(
        text=f"Requested by {ctx.author}",
        icon_url=ctx.author.display_avatar.url
    )

    await ctx.reply(embed=embed)

bot.run(TOKEN)