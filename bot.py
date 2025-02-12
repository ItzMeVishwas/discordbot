import discord
from discord.ext import commands
import os
from keep_alive import keep_alive

# Intents setup (Make sure to enable "Presence" and "Server Members" intents in the Discord Developer Portal)
intents = discord.Intents.default()
intents.presences = True  # Enables presence updates
intents.members = True  # Enables member updates

# Initialize bot
bot = commands.Bot(command_prefix="!", intents=intents)

# Replace with your Discord user ID (to receive notifications)
YOUR_USER_ID = 748964469039824937  # Change this to your actual Discord ID

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online and monitoring status changes!")
    user = await bot.fetch_user(YOUR_USER_ID)
    await user.send("✅ Bot is now online and monitoring member status changes.")

@bot.event
async def on_presence_update(before, after):
    """Notifies when a user's status (online/offline) changes."""
    user = await bot.fetch_user(YOUR_USER_ID)

    if before.status != after.status:  # Check if the status changed
        await user.send(f"⚡ **{after.name}** changed status: **{before.status}** → **{after.status}**")

# Keep the bot alive on Render
keep_alive()

# Run the bot
TOKEN = os.getenv("TOKEN")  # Uses the token stored in Render environment variables
bot.run(TOKEN)
