import discord
from discord.ext import commands, tasks
import os
import json
import random
import datetime
from keep_alive import keep_alive
from collections import defaultdict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord_bot')

# Enable all necessary intents
intents = discord.Intents.default()
intents.message_content = True  # Ensures the bot can read messages
intents.presences = True
intents.members = True
intents.voice_states = True

# Initialize bot with command prefix
bot = commands.Bot(command_prefix="!", intents=intents)

# Your Discord user ID (to receive notifications)
YOUR_USER_ID = 748964469039824937  # Change this to your actual Discord ID

# File to store stream points
POINTS_FILE = "stream_points.json"

# Load saved points from file
def load_points():
    if os.path.exists(POINTS_FILE):
        try:
            with open(POINTS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Error loading points: %s", e)
            return {}
    return {}

# Save points to file
def save_points(points):
    try:
        with open(POINTS_FILE, "w") as f:
            json.dump(points, f)
    except Exception as e:
        logger.error("Error saving points: %s", e)

# Initialize stream points (stored as string keys mapping to integers)
stream_points = defaultdict(int, load_points())
# Track users who are currently streaming (set of user IDs)
streaming_users = set()
# Track the lifetime points each user had at the moment they started streaming
session_start_points = {}

@bot.event
async def on_ready():
    """Bot startup event."""
    logger.info("✅ %s is online and ready!", bot.user)
    try:
        user = await bot.fetch_user(YOUR_USER_ID)
        await user.send("✅ Bot is now online and monitoring member status changes and streaming sessions.")
    except Exception as e:
        logger.error("Error sending startup DM: %s", e)
    
    # Record the launch time for uptime calculations
    bot.launch_time = datetime.datetime.utcnow()
    
    # Announce in each server's 'general' channel that new code is updated
    for guild in bot.guilds:
        general_channel = discord.utils.get(guild.text_channels, name="general")
        if general_channel:
            try:
                await general_channel.send("New code module updated")
            except Exception as e:
                logger.error("Could not send update message in %s: %s", guild.name, e)
        else:
            logger.warning("No 'general' channel found in guild: %s", guild.name)
    
    add_stream_points.start()  # Start loop for awarding stream points
    await bot.change_presence(activity=discord.Game(name="Hehe haha ing"))

@bot.event
async def on_presence_update(before, after):
    """DMs you when a user's status changes."""
    if before.status != after.status:
        try:
            user = await bot.fetch_user(YOUR_USER_ID)
            await user.send(f"⚡ **{after.name}** changed status: **{before.status}** → **{after.status}**")
        except Exception as e:
            logger.error("Error sending presence update DM: %s", e)

@bot.event
async def on_voice_state_update(member, before, after):
    """Handles streaming status and points system."""
    guild = member.guild
    # Attempt to get the 'general' text channel; log a warning if not found
    general_channel = discord.utils.get(guild.text_channels, name="general")
    if general_channel is None:
        logger.warning("General channel not found in guild '%s'. Skipping stream notification.", guild.name)
        return

    # User starts streaming
    if not before.self_stream and after.self_stream:
        streaming_users.add(member.id)
        # Record the lifetime points at the start of this streaming session
        session_start_points[member.id] = stream_points.get(str(member.id), 0)
        await general_channel.send(f"🎥 **{member.name}** has started streaming! Stream point mode enabled!")
    
    # User stops streaming
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
    """Adds 1 point per 60 seconds for users who are streaming."""
    for user_id in streaming_users:
        stream_points[str(user_id)] += 1
    save_points(stream_points)

@bot.command()
async def balance(ctx):
    """Check the user's stream points."""
    points = int(stream_points.get(str(ctx.author.id), 0))
    await ctx.send(f"💰 **{ctx.author.name}**, you have **{points}** stream points!")

# Fun commands: Truth, Dare & Would You Rather questions
truth_questions = [
    "Have you ever had a crush on someone in this server?", "What's your biggest secret?", "Have you ever cheated on a test?",
    "What's your most embarrassing moment?", "If you could date anyone in this server, who would it be?", "What’s the most romantic thing you’ve ever done?",
    "What’s the most awkward date you’ve been on?", "Have you ever had a crush on your best friend?", "What’s your biggest fear in a relationship?",
    "What’s the most embarrassing thing your parents have caught you doing?", "Have you ever had a dream about someone in this server?", "Do you believe in love at first sight?",
    "Have you ever been rejected by someone you liked?", "What’s your worst habit?", "Who do you text the most?", "Have you ever lied to your best friend?",
    "What’s the weirdest thing you’ve ever Googled?", "If you could change one thing about yourself, what would it be?", "What’s the worst lie you’ve ever told?",
    "What’s the funniest thing that’s ever happened on a date?", "If you had to kiss one person in this server, who would it be?", "Have you ever fallen in love at first sight?",
    "What’s the worst date you’ve ever been on?", "Do you have a secret crush on someone here?", "Have you ever gotten into a relationship just because you were lonely?",
    "What’s something romantic you’ve done that failed?", "Have you ever had a relationship last less than a week?", "Have you ever been caught stalking someone on social media?",
    "What’s the most romantic song you’ve ever dedicated to someone?", "Have you ever written a love letter?"
]

dare_questions = [
    "Send a voice message saying ‘I love you’ to the last person you texted.", "Sing a song in the voice chat.", "Say something embarrassing in the general chat.",
    "Call your crush and tell them you like them.", "Let someone in the server write your status for the next hour.", "Change your Discord name to 'I am a potato' for 24 hours.",
    "Send your last Google search in the chat.", "Say a tongue twister 5 times fast.", "Do 10 push-ups and send a video proof.", "Send a message to your ex saying ‘I miss you’.",
    "Post an embarrassing photo of yourself.", "Send a weird selfie to the chat.", "Speak in an accent for the next 5 minutes.", "Change your profile picture to something ridiculous.",
    "Tell the group your weirdest habit.", "Send a screenshot of your recent messages with your crush.", "Post a picture of your feet in the chat.", "Write a love letter to someone in the server.",
    "Pretend to be a monkey for the next 3 messages.", "Let someone control your Discord for 5 minutes.", "Tell a joke and if no one laughs, do another dare.", "Post the first picture in your camera roll.",
    "Act like a couple with the person to your right for 10 minutes.", "Send a DM to your crush saying 'You + Me = ❤️'."
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
    "Would you rather be the richest person in the world or the smartest?"
]

@bot.command()
async def truth(ctx):
    """Responds with a random truth question."""
    await ctx.send(f"🧐 Truth: {random.choice(truth_questions)}")

@bot.command()
async def dare(ctx):
    """Responds with a random dare question."""
    await ctx.send(f"🔥 Dare: {random.choice(dare_questions)}")

@bot.command(name="wouldyourather")
async def would_you_rather(ctx):
    """Responds with a random 'Would You Rather' question."""
    await ctx.send(f"🤔 Would You Rather: {random.choice(would_you_rather_questions)}")

# Added Purge Command:
@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    """
    Deletes the specified number of messages above the command message.
    
    Example: !purge 5 deletes the five messages sent before the command.
    """
    if amount < 1:
        await ctx.send("Please specify a number greater than 0.")
        return

    messages_to_delete = []
    # Fetch messages before the command message
    async for message in ctx.channel.history(limit=amount, before=ctx.message):
        messages_to_delete.append(message)
    
    if messages_to_delete:
        try:
            await ctx.channel.delete_messages(messages_to_delete)
            # Send a temporary confirmation message
            await ctx.send(f"🧹 Purged {len(messages_to_delete)} messages.", delete_after=5)
        except discord.Forbidden:
            await ctx.send("I do not have permission to delete messages.")
        except discord.HTTPException as e:
            await ctx.send(f"Failed to delete messages: {e}")
    else:
        await ctx.send("No messages found to delete.")

# Additional Commands:

@bot.command()
async def ping(ctx):
    """Responds with the bot's latency."""
    latency = round(bot.latency * 1000)
    await ctx.send(f"Pong! Latency: {latency}ms")

@bot.command()
async def leaderboard(ctx):
    """Displays the top 5 users based on their stream points."""
    # Sort stream_points by points (highest first)
    sorted_points = sorted(stream_points.items(), key=lambda item: item[1], reverse=True)
    leaderboard_entries = sorted_points[:5]
    
    message = "🏆 **Leaderboard** 🏆\n"
    rank = 1
    for user_id, points in leaderboard_entries:
        try:
            user = await bot.fetch_user(int(user_id))
            message += f"{rank}. {user.name} - {points} points\n"
        except Exception as e:
            message += f"{rank}. Unknown user - {points} points\n"
        rank += 1
    await ctx.send(message)

@bot.command()
async def serverinfo(ctx):
    """Displays basic information about the server."""
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
    Checks the bot's latency and displays it with a pink-themed embed and extra info.
    This command can only be used in the channel named "latency" by an admin.
    """
    if ctx.channel.name != "latency":
        await ctx.send("This command can only be used in the 'latency' channel.")
        return

    now = datetime.datetime.utcnow()
    latency_ms = round(bot.latency * 1000)
    guild_count = len(bot.guilds)
    # Calculate uptime
    uptime_delta = now - bot.launch_time
    uptime_str = str(uptime_delta).split('.')[0]  # Remove microseconds

    # Generate a random "Bluedox Check" ping between 1 and 50ms
    bluedox_ping = random.randint(1, 50)

    embed = discord.Embed(
        title="Latency Check",
        description="Here is your pink latency info with extra details!",
        color=0xFF69B4,  # Hot pink color
        timestamp=now
    )
    embed.add_field(name="Websocket Latency", value=f"{latency_ms}ms", inline=False)
    embed.add_field(name="Server Count", value=f"I'm in {guild_count} servers.", inline=False)
    embed.add_field(name="Uptime", value=uptime_str, inline=False)
    # New field: Verify the user who invoked the command
    embed.add_field(name="User Verification", value=f"{ctx.author.name} - Access Granted", inline=False)
    embed.add_field(name="Bluedox Check", value=f"{bluedox_ping}ms", inline=False)
    embed.add_field(name="Note", value="Websocket latency is measured between the bot and Discord's servers. Lower values indicate a more responsive connection.", inline=False)
    embed.set_footer(text="Latency check provided by your friendly bot.")
    await ctx.send(embed=embed)

# Debugging: Process messages and log them (avoid spamming in production)
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return  # Ignore bot messages
    logger.debug("📩 Received message: %s", message.content)
    await bot.process_commands(message)

# Global error handler for commands - it now ignores CommandNotFound errors.
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    logger.error("Error in command '%s': %s", ctx.command, error)
    await ctx.send(f"⚠️ An error occurred: {str(error)}")

# Start the keep-alive server (used for Render and UptimeRobot integration)
keep_alive()

# Run the bot using the token from environment variables
bot.run(os.getenv("TOKEN"))
