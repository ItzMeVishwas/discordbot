import discord
from discord.ext import commands, tasks
import os
import json
import random
from keep_alive import keep_alive
from collections import defaultdict

# Intents setup (Make sure to enable "Presence", "Server Members", and "Voice States" intents in Discord Developer Portal)
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
    return defaultdict(int)

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
    if before.status != after.status:
        user = await bot.fetch_user(YOUR_USER_ID)
        await user.send(f"⚡ **{after.name}** changed status: **{before.status}** → **{after.status}**")

@bot.event
async def on_voice_state_update(member, before, after):
    """Handles streaming status and points system."""
    guild = member.guild
    general_channel = discord.utils.get(guild.text_channels, name="general")
    
    if before.self_stream is False and after.self_stream is True:
        # User started streaming
        streaming_users.add(member.id)
        await general_channel.send(f"🎥 **{member.name}** has started streaming! Stream point mode enabled!")
    
    elif before.self_stream is True and after.self_stream is False:
        # User stopped streaming
        if member.id in streaming_users:
            points = stream_points[member.id]
            await general_channel.send(f"🎥 **{member.name}** has stopped streaming and gained **{points}** points!")
            streaming_users.remove(member.id)
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

# Truth, Dare, and Would You Rather Questions
truth_questions = [
    "Have you ever had a crush on someone in this server?",
    "What's your biggest secret?",
    "What's your most embarrassing moment?",
    "If you could date anyone in this server, who would it be?",
    "What’s the most romantic thing you’ve ever done?",
    "What’s the most awkward date you’ve been on?",
    "Have you ever had a crush on your best friend?",
    "What’s your biggest fear in a relationship?",
    "Have you ever had a dream about someone in this server?",
    "If you had to marry someone in this server, who would it be?",
    "Have you ever had a crush on a teacher?",
    "What’s the worst lie you’ve ever told?",
    "Have you ever been rejected by someone you liked?",
    "What’s one thing you love most about your best friend?",
    "What's your weirdest romantic fantasy?",
    "If you had to kiss one person in this server, who would it be?",
    "Have you ever flirted with someone just to make someone else jealous?",
    "Who was your first crush?",
    "Have you ever lied to your best friend?",
    "Would you rather marry your best friend or your crush?",
    "Have you ever sent a risky text and regretted it?",
    "What’s the most embarrassing thing you've said to your crush?",
    "If you had to be handcuffed to one person for a week, who would it be?",
    "Would you rather date someone funny or someone romantic?",
]

dare_questions = [
    "Send a voice message saying ‘I love you’ to the last person you texted.",
    "Sing a song in the voice chat.",
    "Say something embarrassing in the general chat.",
    "Call your crush and tell them you like them.",
    "Let someone in the server write your status for the next hour.",
    "Send a message to your ex saying ‘I miss you’.",
    "Post an embarrassing photo of yourself.",
    "Send your last Google search in the chat.",
    "Send a weird selfie to the chat.",
    "Tell the group your most embarrassing childhood story.",
    "Post the first picture in your camera roll.",
    "Say something really cheesy to someone in the server.",
    "Let someone pick a new nickname for you.",
    "Send a screenshot of your last DMs.",
    "Talk like a baby for the next 3 messages.",
    "Pretend to be a monkey for the next 3 messages.",
    "Write a love letter to someone in the server.",
    "Send a message to your crush saying 'You + Me = ❤️'.",
]

would_you_rather_questions = [
    "Would you rather have unlimited money or unlimited love?",
    "Would you rather always lose or never play?",
    "Would you rather go on vacation with your best friend or your crush?",
    "Would you rather be able to read minds or see the future?",
    "Would you rather never use social media again or never watch TV again?",
    "Would you rather kiss your best friend or your crush?",
    "Would you rather go on a romantic date with your crush or an adventure with your best friend?",
    "Would you rather be in a long-distance relationship or have to spend 24/7 together?",
    "Would you rather never fall in love or have your heart broken over and over?",
    "Would you rather find true love today or win the lottery next year?",
]

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
