import discord
from discord.ext import commands, tasks
import os
from keep_alive import keep_alive

# Intents setup (Make sure to enable "Presence", "Server Members", and "Voice States" intents)
intents = discord.Intents.default()
intents.presences = True  # Detects online/offline status
intents.members = True  # Detects new members
intents.voice_states = True  # Detects voice chat activity (streaming)

# Initialize bot
bot = commands.Bot(command_prefix="!", intents=intents)

# Replace with your Discord user ID (for notifications)
YOUR_USER_ID = 748964469039824937  # Change to your actual ID

# Dictionary to store user points
user_points = {}

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online and monitoring status changes!")
    user = await bot.fetch_user(YOUR_USER_ID)
    await user.send("✅ Bot is now online and tracking status & streaming points.")
    
@bot.event
async def on_presence_update(before, after):
    """Announces when someone changes their online/offline status."""
    if before.status != after.status:
        guild = after.guild
        channel = discord.utils.get(guild.text_channels, name="general")  # Adjust if needed
        if channel:
            await channel.send(f"⚡ **{after.name}** changed status: **{before.status}** → **{after.status}**")

@bot.event
async def on_voice_state_update(member, before, after):
    """Detects when a user starts/stops streaming and announces it."""
    guild = member.guild
    channel = discord.utils.get(guild.text_channels, name="general")  # Adjust if needed

    # Check if the user started streaming
    if not before.self_stream and after.self_stream:
        if channel:
            await channel.send(f"🎥 **{member.name}** started streaming! Stream Pointing is Enabled! 🚀")
        start_tracking_streaming(member.id)

    # Check if the user stopped streaming
    elif before.self_stream and not after.self_stream:
        stop_tracking_streaming(member.id)

# Function to track points while streaming
streaming_users = {}

def start_tracking_streaming(user_id):
    """Start tracking a user's stream time for points."""
    if user_id not in streaming_users:
        streaming_users[user_id] = 0
        give_stream_points.start(user_id)

def stop_tracking_streaming(user_id):
    """Stop tracking a user's stream time."""
    if user_id in streaming_users:
        streaming_users.pop(user_id)

@tasks.loop(seconds=60)
async def give_stream_points(user_id):
    """Gives 1 point per 60 seconds of streaming."""
    if user_id in streaming_users:
        streaming_users[user_id] += 1
        user_points[user_id] = user_points.get(user_id, 0) + 1

@bot.command()
async def balance(ctx):
    """Allows users to check their streaming points."""
    user_id = ctx.author.id
    points = user_points.get(user_id, 0)
    await ctx.send(f"💰 **{ctx.author.name}**, you have **{points} points** from streaming!")

# Keep the bot alive on Render
keep_alive()

# Run the bot
TOKEN = os.getenv("TOKEN")  # Uses the token stored in Render environment variables
bot.run(TOKEN)
