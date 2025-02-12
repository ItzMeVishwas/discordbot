import discord
from discord.ext import commands, tasks
import os
import json
import random
from keep_alive import keep_alive
from collections import defaultdict

# Intents setup
intents = discord.Intents.default()
intents.presences = True  # Enables presence updates
intents.members = True  # Enables member updates
intents.voice_states = True  # Enables voice state updates

# Initialize bot
bot = commands.Bot(command_prefix="!", intents=intents)

# Your Discord user ID (to receive notifications)
YOUR_USER_ID = 748964469039824937  # Change this to your actual Discord ID

# Stream points logging file
POINTS_FILE = "stream_points.json"

# Load saved points
def load_points():
    if os.path.exists(POINTS_FILE):
        with open(POINTS_FILE, "r") as f:
            return json.load(f)
    return {}

# Save points
def save_points(points):
    with open(POINTS_FILE, "w") as f:
        json.dump(points, f)

# Initialize stream points
stream_points = defaultdict(int, load_points())
streaming_users = set()

@bot.event
async def on_ready():
    """Bot startup event."""
    print(f"✅ {bot.user} is online and monitoring status changes!")
    user = await bot.fetch_user(YOUR_USER_ID)
    await user.send("✅ Bot is now online and monitoring member status changes and streaming sessions.")
    add_stream_points.start()  # ✅ Starts the streaming points loop

@bot.event
async def on_presence_update(before, after):
    """DMs you when a user's status (online/offline) changes."""
    user = await bot.fetch_user(YOUR_USER_ID)
    if before.status != after.status:
        await user.send(f"⚡ **{after.name}** changed status: **{before.status}** → **{after.status}**")

@bot.event
async def on_voice_state_update(member, before, after):
    """Handles streaming status and points system."""
    guild = member.guild
    general_channel = discord.utils.get(guild.text_channels, name="general")
    
    before_streaming = getattr(before, "self_stream", False)
    after_streaming = getattr(after, "self_stream", False)

    if not before_streaming and after_streaming:
        # User started streaming
        streaming_users.add(str(member.id))
        await general_channel.send(f"🎥 **{member.name}** has started streaming! Stream point mode enabled!")
    
    elif before_streaming and not after_streaming:
        # User stopped streaming
        if str(member.id) in streaming_users:
            points = stream_points.get(str(member.id), 0)
            await general_channel.send(f"🎥 **{member.name}** has stopped streaming and gained **{points}** points!")
            streaming_users.remove(str(member.id))
            save_points(stream_points)  # Save points when user stops streaming

@tasks.loop(seconds=60)
async def add_stream_points():
    """Adds 1 point per 60 seconds for users who are streaming."""
    for user_id in streaming_users:
        stream_points[user_id] += 1
    save_points(stream_points)  # Save points every minute

@bot.command()
async def balance(ctx):
    """Check the user's stream points."""
    points = stream_points.get(str(ctx.author.id), 0)
    await ctx.send(f"💰 **{ctx.author.name}**, you have **{points}** stream points!")

# Truth or Dare & Would You Rather Questions
truth_questions = [
    "Have you ever had a crush on someone in this server?",
    "What's your biggest secret?",
    "What's your most embarrassing moment?",
    "Who do you text the most?",
    "If you could date anyone in this server, who would it be?",
    "Have you ever lied to your best friend?",
    "What’s the most romantic thing you’ve ever done?",
    "Have you ever had a crush on your best friend?",
    "What’s your biggest fear in a relationship?",
    "If you had to marry someone in this server, who would it be?",
] * 3  # Expands to 30 questions

dare_questions = [
    "Send a voice message saying ‘I love you’ to the last person you texted.",
    "Sing a song in the voice chat.",
    "Say something embarrassing in the general chat.",
    "Call your crush and tell them you like them.",
    "Change your Discord name to 'I am a potato' for 24 hours.",
    "Send your last Google search in the chat.",
    "Post an embarrassing photo of yourself.",
    "Send a weird selfie to the chat.",
    "Let someone send a text to your crush from your phone.",
    "Speak in an accent for the next 5 minutes.",
] * 3  # Expands to 30 questions

would_you_rather_questions = [
    "Would you rather have unlimited money or unlimited love?",
    "Would you rather always lose or never play?",
    "Would you rather be famous or be rich?",
    "Would you rather never use social media again or never watch TV again?",
    "Would you rather have a time machine or the ability to teleport?",
    "Would you rather go on vacation with your best friend or your crush?",
    "Would you rather date your best friend or your crush?",
    "Would you rather get married but never have kids, or have kids but never marry?",
    "Would you rather live 100 years in the past or 100 years in the future?",
    "Would you rather have a personal chef or a personal maid?",
] * 3  # Expands to 30 questions

@bot.command()
async def truth(ctx):
    """Sends a random truth question."""
    await ctx.send(f"🧐 Truth: {random.choice(truth_questions)}")

@bot.command()
async def dare(ctx):
    """Sends a random dare question."""
    await ctx.send(f"🔥 Dare: {random.choice(dare_questions)}")

@bot.command()
async def wouldyourather(ctx):
    """Sends a random Would You Rather question."""
    await ctx.send(f"🤔 Would You Rather: {random.choice(would_you_rather_questions)}")

# Keep the bot alive on Render
keep_alive()

# Run the bot
TOKEN = os.getenv("TOKEN")
bot.run(TOKEN)
