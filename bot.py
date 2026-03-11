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
STAFF_EVIDENCE_CHANNEL = 1481206250623598725

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
"Chances of you getting with her","Chances similar to Arsenal bottling",
"Chances of streem marrying his hgs","Otis Khan has kidnapped the bot", "I forgot the question"
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
    print(f"Bot online as {bot.user}")

@bot.event
async def on_message(message):

    global count_number,last_counter

    if message.author.bot:
        return

    weekly_messages[message.author.id]+=1

    # AFK REMOVE
    if message.author.id in afk_users:
        del afk_users[message.author.id]
        await message.channel.send(
            f"{message.author.mention} is no longer AFK."
        )

    # AFK MENTION
    for user in message.mentions:
        if user.id in afk_users:
            await message.channel.send(
                f"{user.display_name} is AFK: {afk_users[user.id]}"
            )

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

    await ctx.send(embed=embed)

# ---------------- AFK ---------------- #

@bot.command()
async def afk(ctx, *, reason="AFK"):

    afk_users[ctx.author.id] = reason

    embed = discord.Embed(
        title="You're now AFK!",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Message",
        value=f"• {reason}",
        inline=False
    )

    embed.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar.url)

    await ctx.send(embed=embed)

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

    seconds=int(time.time()-start_time)
    uptime=str(timedelta(seconds=seconds))

    await ctx.send(f"Bot uptime: **{uptime}**")

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

    reply = random.choice(eightball_responses)

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

# ---------------- RUN ---------------- #

bot.run(TOKEN)