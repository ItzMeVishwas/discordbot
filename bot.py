import discord
from discord.ext import commands, tasks
import os
from keep_alive import keep_alive
from collections import defaultdict

# Intents setup (Make sure to enable "Presence", "Server Members", and "Voice States" intents in Discord Developer Portal)
intents = discord.Intents.default()
intents.presences = True  # Enables presence updates
intents.members = True  # Enables member updates
intents.voice_states = True  # Enables voice state updates

# Initialize bot
bot = commands.Bot(command_prefix="!", intents=intents)

# Replace with your Discord user ID (to receive notifications)
YOUR_USER_ID = 748964469039824937  # Change this to your actual Discord ID

# Dictionary to track streaming users and their points
stream_points = defaultdict(int)
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
            stream_points[member.id] = 0

@tasks.loop(seconds=60)
async def add_stream_points():
    """Adds 1 point per 60 seconds for users who are streaming."""
    for user_id in streaming_users:
        stream_points[user_id] += 1

@bot.command()
async def balance(ctx):
    """Check the user's stream points."""
    points = stream_points.get(ctx.author.id, 0)
    await ctx.send(f"💰 **{ctx.author.name}**, you have **{points}** stream points!")

# Keep the bot alive on Render
keep_alive()

# Run the bot
TOKEN = os.getenv("TOKEN")  # Uses the token stored in Render environment variables
bot.run(TOKEN)
