import discord
from discord.ext import commands, tasks
import os
import json
import random
import datetime
import asyncio
import openai
from keep_alive import keep_alive  # Ensure this file is in your repository if used
from collections import defaultdict
import logging

# Set OpenAI API key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord_bot')

# Enable all necessary intents
intents = discord.Intents.default()
intents.message_content = True
intents.presences = True
intents.members = True
intents.voice_states = True

# Initialize bot with command prefix and disable default help command
bot = commands.Bot(command_prefix="!", help_command=None, intents=intents)

YOUR_USER_ID = 748964469039824937  # Replace with your actual Discord ID
POINTS_FILE = "stream_points.json"

def load_points():
    if os.path.exists(POINTS_FILE):
        try:
            with open(POINTS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Error loading points: %s", e)
            return {}
    return {}

def save_points(points):
    try:
        with open(POINTS_FILE, "w") as f:
            json.dump(points, f)
    except Exception as e:
        logger.error("Error saving points: %s", e)

stream_points = defaultdict(int, load_points())
streaming_users = set()
session_start_points = {}

# Expanded global question lists
truth_questions = [
    "Have you ever had a crush on someone in this server?",
    "What's your biggest secret?",
    "Have you ever cheated on a test?",
    "What's your most embarrassing moment?",
    "If you could date anyone in this server, who would it be?",
    "What’s the most romantic thing you’ve ever done?",
    "What’s the most awkward date you’ve been on?",
    "Have you ever had a crush on your best friend?",
    "What’s your biggest fear in a relationship?",
    "What’s the most embarrassing thing your parents have caught you doing?",
    "Have you ever had a dream about someone in this server?",
    "Do you believe in love at first sight?",
    "Have you ever been rejected by someone you liked?",
    "What’s your worst habit?",
    "Who do you text the most?",
    "Have you ever lied to your best friend?",
    "What’s the weirdest thing you’ve ever Googled?",
    "If you could change one thing about yourself, what would it be?",
    "What’s the worst lie you’ve ever told?",
    "What’s the funniest thing that’s ever happened on a date?",
    "If you had to kiss one person in this server, who would it be?",
    "Have you ever fallen in love at first sight?",
    "What’s the worst date you’ve ever been on?",
    "Do you have a secret crush on someone here?",
    "Have you ever gotten into a relationship just because you were lonely?",
    "What’s something romantic you’ve done that failed?",
    "Have you ever had a relationship last less than a week?",
    "Have you ever been caught stalking someone on social media?",
    "What’s the most romantic song you’ve ever dedicated to someone?",
    "Have you ever written a love letter?",
    "What is your biggest insecurity?",
    "What is the most embarrassing thing you've ever done in public?",
    "What is a secret you've never told anyone?",
    "What is the worst decision you've ever made?"
]

dare_questions = [
    "Send a voice message saying ‘I love you’ to the last person you texted.",
    "Sing a song in the voice chat.",
    "Say something embarrassing in the general chat.",
    "Call your crush and tell them you like them.",
    "Let someone in the server write your status for the next hour.",
    "Change your Discord name to 'I am a potato' for 24 hours.",
    "Send your last Google search in the chat.",
    "Say a tongue twister 5 times fast.",
    "Do 10 push-ups and send a video proof.",
    "Send a message to your ex saying ‘I miss you’.",
    "Post an embarrassing photo of yourself.",
    "Send a weird selfie to the chat.",
    "Speak in an accent for the next 5 minutes.",
    "Change your profile picture to something ridiculous.",
    "Tell the group your weirdest habit.",
    "Send a screenshot of your recent messages with your crush.",
    "Post a picture of your feet in the chat.",
    "Write a love letter to someone in the server.",
    "Pretend to be a monkey for the next 3 messages.",
    "Let someone control your Discord for 5 minutes.",
    "Tell a joke and if no one laughs, do another dare.",
    "Post the first picture in your camera roll.",
    "Act like a couple with the person to your right for 10 minutes.",
    "Send a DM to your crush saying 'You + Me = ❤️'.",
    "Wear your clothes backward for an hour.",
    "Change your nickname to something silly for 24 hours.",
    "Do your best impression of another server member."
]

would_you_rather_questions = [
    "Would you rather have unlimited money or unlimited love?",
    "Would you rather always lose or never play?",
    "Would you rather be famous or be rich?",
    "Would you rather have a time machine or the ability to teleport?",
    "Would you rather date your best friend or a total stranger?",
    "Would you rather marry for love or money?",
    "Would you rather never be able to kiss again or never hug again?",
    "Would you rather have your dream job or your dream partner?",
    "Would you rather be single forever or always be in a relationship?",
    "Would you rather live in the city or the countryside?",
    "Would you rather be the funniest person in the room or the smartest?",
    "Would you rather be able to speak all languages or talk to animals?",
    "Would you rather travel to the past or the future?",
    "Would you rather always be underdressed or overdressed?",
    "Would you rather have a rewind button or a pause button on your life?",
    "Would you rather live without music or without television?",
    "Would you rather have an unlimited international first class ticket or never have to pay for food at restaurants?",
    "Would you rather be able to control fire or water?",
    "Would you rather be feared by all or loved by all?",
    "Would you rather be the richest person in the world or the smartest?",
    "Would you rather have a pet dragon or be a dragon?",
    "Would you rather never be able to use the internet again or never be able to watch TV again?",
    "Would you rather always have to say everything on your mind or never speak again?",
    "Would you rather be stuck in an elevator with your ex or your boss?",
    "Would you rather have no one show up to your wedding or your funeral?",
    "Would you rather be able to fly or be invisible?",
    "Would you rather be constantly itchy or constantly sticky?",
    "Would you rather always know when someone is lying or always get away with lying?"
]

# Event: on_ready
@bot.event
async def on_ready():
    logger.info("✅ %s is online and ready!", bot.user)
    try:
        user = await bot.fetch_user(YOUR_USER_ID)
        await user.send("✅ Bot is now online and monitoring member status changes and streaming sessions.")
    except Exception as e:
        logger.error("Error sending startup DM: %s", e)
    bot.launch_time = datetime.datetime.utcnow()
    for guild in bot.guilds:
        general_channel = discord.utils.get(guild.text_channels, name="general")
        if general_channel:
            try:
                await general_channel.send("✨ **New code module updated.**")
            except Exception as e:
                logger.error("Could not send update message in %s: %s", guild.name, e)
        else:
            logger.warning("No 'general' channel found in guild: %s", guild.name)
    add_stream_points.start()
    await bot.change_presence(activity=discord.Game(name="Hehe haha ing"))

@bot.event
async def on_presence_update(before, after):
    if before.status != after.status:
        try:
            user = await bot.fetch_user(YOUR_USER_ID)
            await user.send(f"⚡ **{after.name}** changed status: **{before.status}** → **{after.status}**")
        except Exception as e:
            logger.error("Error sending presence update DM: %s", e)

@bot.event
async def on_voice_state_update(member, before, after):
    guild = member.guild
    general_channel = discord.utils.get(guild.text_channels, name="general")
    if general_channel is None:
        logger.warning("General channel not found in guild '%s'. Skipping stream notification.", guild.name)
        return
    if not before.self_stream and after.self_stream:
        streaming_users.add(member.id)
        session_start_points[member.id] = stream_points.get(str(member.id), 0)
        await general_channel.send(f"🎥 **{member.name}** has started streaming! Stream point mode enabled!")
    elif before.self_stream and not after.self_stream:
        if member.id in streaming_users:
            current_points = stream_points.get(str(member.id), 0)
            start_points = session_start_points.get(member.id, current_points)
            session_points = current_points - start_points
            await general_channel.send(
                f"🎥 **{member.name}** has stopped streaming and earned **{session_points}** points this session "
                f"(Lifetime total: **{current_points}** points)!"
            )
            streaming_users.remove(member.id)
            session_start_points.pop(member.id, None)
            save_points(stream_points)

@tasks.loop(seconds=60)
async def add_stream_points():
    for user_id in streaming_users:
        stream_points[str(user_id)] += 1
    save_points(stream_points)

@bot.command()
async def balance(ctx):
    points = int(stream_points.get(str(ctx.author.id), 0))
    await ctx.send(f"💰 **{ctx.author.name}**, you have **{points}** stream points.")

@bot.command()
async def truth(ctx):
    """Provides a random truth question."""
    await ctx.send(f"🧐 **Truth:** {random.choice(truth_questions)}")

@bot.command()
async def dare(ctx):
    """Provides a random dare question."""
    await ctx.send(f"🔥 **Dare:** {random.choice(dare_questions)}")

@bot.command(name="wouldyourather")
async def would_you_rather(ctx):
    """Provides a random 'Would You Rather' question."""
    await ctx.send(f"🤔 **Would You Rather:** {random.choice(would_you_rather_questions)}")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    """Deletes a specified number of messages above the command message."""
    if amount < 1:
        await ctx.send("Please specify a number greater than 0.")
        return
    messages_to_delete = []
    async for message in ctx.channel.history(limit=amount, before=ctx.message):
        messages_to_delete.append(message)
    if messages_to_delete:
        try:
            await ctx.channel.delete_messages(messages_to_delete)
            await ctx.send(f"🧹 **Purged {len(messages_to_delete)} messages.**", delete_after=5)
        except discord.Forbidden:
            await ctx.send("I do not have permission to delete messages.")
        except discord.HTTPException as e:
            await ctx.send(f"Failed to delete messages: {e}")
    else:
        await ctx.send("No messages found to delete.")

@bot.command()
async def ping(ctx):
    """Shows the bot's latency."""
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 **Pong! Latency:** {latency}ms")

@bot.command()
async def leaderboard(ctx):
    """Displays the top 5 users based on stream points."""
    sorted_points = sorted(stream_points.items(), key=lambda item: item[1], reverse=True)
    leaderboard_entries = sorted_points[:5]
    message = "🏆 **Leaderboard** 🏆\n"
    rank = 1
    for user_id, points in leaderboard_entries:
        try:
            user = await bot.fetch_user(int(user_id))
            message += f"**{rank}. {user.name}** — {points} points\n"
        except Exception as e:
            message += f"**{rank}. Unknown user** — {points} points\n"
        rank += 1
    await ctx.send(message)

@bot.command()
async def serverinfo(ctx):
    """Displays basic server information."""
    guild = ctx.guild
    message = (
        f"**Server Name:** {guild.name}\n"
        f"**Server ID:** {guild.id}\n"
        f"**Member Count:** {guild.member_count}\n"
        f"**Created At:** {guild.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"**Owner:** {guild.owner}"
    )
    await ctx.send(message)

@bot.command()
@commands.has_permissions(administrator=True)
async def latencycheck(ctx):
    """
    Provides a detailed latency report.
    *This command is restricted to the 'latency' channel and admin users only.*
    """
    if ctx.channel.name != "latency":
        await ctx.send("❌ This command can only be used in the **#latency** channel.")
        return
    now = datetime.datetime.utcnow()
    latency_ms = round(bot.latency * 1000)
    guild_count = len(bot.guilds)
    uptime_delta = now - bot.launch_time
    uptime_str = str(uptime_delta).split('.')[0]
    bluedox_ping = random.randint(1, 50)
    embed = discord.Embed(
        title="📊 Latency Report",
        description="Below are the detailed latency statistics:",
        color=0x3498DB,  # Deep blue for a formal look
        timestamp=now
    )
    embed.add_field(name="Websocket Latency", value=f"**{latency_ms}ms**", inline=True)
    embed.add_field(name="Server Count", value=f"**{guild_count} servers**", inline=True)
    embed.add_field(name="Uptime", value=f"**{uptime_str}**", inline=False)
    embed.add_field(name="User Verification", value=f"**{ctx.author.name}** — *Access Granted*", inline=False)
    embed.add_field(name="Bluedox Check", value=f"**{bluedox_ping}ms**", inline=True)
    embed.add_field(name="Note", value="Websocket latency is measured between the bot and Discord's servers.", inline=False)
    embed.set_footer(text="Latency report provided by your mahiru.")
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    """Bans a member from the server."""
    try:
        await member.ban(reason=reason)
        await ctx.send(f"🚫 **{member.mention}** has been banned. Reason: {reason if reason else 'No reason provided.'}")
    except Exception as e:
        await ctx.send(f"❌ Failed to ban {member.mention}: {e}")

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    """Kicks a member from the server."""
    try:
        await member.kick(reason=reason)
        await ctx.send(f"👢 **{member.mention}** has been kicked. Reason: {reason if reason else 'No reason provided.'}")
    except Exception as e:
        await ctx.send(f"❌ Failed to kick {member.mention}: {e}")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member, *, reason=None):
    """Mutes a member by assigning them the 'Muted' role."""
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        try:
            muted_role = await ctx.guild.create_role(name="Muted", reason="For muting members")
            for channel in ctx.guild.channels:
                await channel.set_permissions(muted_role, send_messages=False, speak=False, add_reactions=False)
        except Exception as e:
            await ctx.send(f"❌ Failed to create Muted role: {e}")
            return
    if muted_role in member.roles:
        await ctx.send(f"ℹ️ **{member.mention}** is already muted.")
        return
    try:
        await member.add_roles(muted_role, reason=reason)
        await ctx.send(f"🔇 **{member.mention}** has been muted. Reason: {reason if reason else 'No reason provided.'}")
    except Exception as e:
        await ctx.send(f"❌ Failed to mute {member.mention}: {e}")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    """Unmutes a member by removing the 'Muted' role."""
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        await ctx.send("ℹ️ There is no Muted role in this server.")
        return
    if muted_role not in member.roles:
        await ctx.send(f"ℹ️ **{member.mention}** is not muted.")
        return
    try:
        await member.remove_roles(muted_role)
        await ctx.send(f"🔊 **{member.mention}** has been unmuted.")
    except Exception as e:
        await ctx.send(f"❌ Failed to unmute {member.mention}: {e}")

@bot.command()
async def coinflip(ctx):
    """Flips a coin (50/50 chance of Heads or Tails)."""
    result = random.choice(["Heads", "Tails"])
    await ctx.send(f"🪙 The coin landed on **{result}**!")

@bot.command()
async def countmessage(ctx, *, query: str):
    """
    Counts how many times the given text appears in the channel.
    It sends a 'counting' message and then edits it with the final result.
    """
    initial_message = await ctx.send(f"🔎 Counting occurrences of **'{query}'** in this channel...")
    count = 0
    try:
        async for message in ctx.channel.history(limit=None):
            if query.lower() in message.content.lower():
                count += 1
    except Exception as e:
        logger.error("Error counting messages: %s", e)
        await initial_message.edit(content=f"❌ An error occurred while counting messages: {e}")
        return
    if count <= 10:
        comment = "Wow!"
    elif count <= 100:
        comment = "Amazing!"
    elif count <= 150:
        comment = "Crazy!"
    elif count <= 200:
        comment = "Damn!"
    else:
        comment = "Legendary!"
    await initial_message.edit(content=f"🔎 The text **'{query}'** was repeated **{count}** times in this channel. {comment}")

@bot.command()
async def transferpoints(ctx):
    """
    Transfers your stream points to official trackers.
    After the transfer, your points are reset to 0.
    """
    await ctx.send("🔄 Transferring points to official trackers...")
    await asyncio.sleep(2)
    stream_points[str(ctx.author.id)] = 0
    save_points(stream_points)
    await ctx.send("✅ Transfer complete. Your points have been reset to 0.")

@bot.command()
async def ask(ctx, *, question: str):
    """
    Ask a question and get an answer from AI.
    Ensure that your OPENAI_API_KEY is set in your environment variables.
    """
    await ctx.send("🤖 Thinking...")
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=question,
            max_tokens=150,
            temperature=0.7,
        )
        answer = response.choices[0].text.strip()
        await ctx.send(f"**Answer:** {answer}")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.command()
async def help(ctx):
    """Provides a list of all available commands with descriptions."""
    embed = discord.Embed(
        title="Available Commands",
        description="Below is a list of commands you can use. Please refer to the descriptions for details.",
        color=0x3498DB
    )
    embed.add_field(name="!balance", value="Check your stream points.", inline=False)
    embed.add_field(name="!truth", value="Receive a random truth question.", inline=False)
    embed.add_field(name="!dare", value="Receive a random dare question.", inline=False)
    embed.add_field(name="!wouldyourather", value="Receive a random 'Would You Rather' question.", inline=False)
    embed.add_field(name="!purge [amount]", value="Delete a specified number of messages above the command.", inline=False)
    embed.add_field(name="!ping", value="Display the bot's latency.", inline=False)
    embed.add_field(name="!leaderboard", value="Show the top 5 users based on stream points.", inline=False)
    embed.add_field(name="!serverinfo", value="Display basic server information.", inline=False)
    embed.add_field(name="!latencycheck", value="Show detailed latency info (Admin only; use in 'latency' channel).", inline=False)
    embed.add_field(name="!ban @member [reason]", value="Ban a member from the server.", inline=False)
    embed.add_field(name="!kick @member [reason]", value="Kick a member from the server.", inline=False)
    embed.add_field(name="!mute @member [reason]", value="Mute a member by assigning them the 'Muted' role.", inline=False)
    embed.add_field(name="!unmute @member", value="Unmute a member by removing the 'Muted' role.", inline=False)
    embed.add_field(name="!coinflip", value="Flip a coin (50/50 chance of Heads or Tails).", inline=False)
    embed.add_field(name="!countmessage [text]", value="Count how many times the specified text appears in the channel.", inline=False)
    embed.add_field(name="!transferpoints", value="Transfer your stream points to official trackers (resets your points).", inline=False)
    embed.add_field(name="!ask [question]", value="Ask a question and receive an AI-generated answer.", inline=False)
    embed.set_footer(text="Type the command as shown to interact with the bot. Provided by your mahiru.")
    await ctx.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    logger.debug("📩 Received message: %s", message.content)
    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    logger.error("Error in command '%s': %s", ctx.command, error)
    await ctx.send(f"⚠️ An error occurred: {str(error)}")

keep_alive()
bot.run(os.getenv("TOKEN"))
