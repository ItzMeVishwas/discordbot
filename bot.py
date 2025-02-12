import discord
from discord.ext import commands, tasks
import os
import json
import random
from keep_alive import keep_alive
from collections import defaultdict

# Intents setup
intents = discord.Intents.default()
intents.presences = True
intents.members = True
intents.voice_states = True

# Initialize bot
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

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
    add_stream_points.start()
    await bot.change_presence(activity=discord.Game(name="!truth | !dare | !wouldyourather"))

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
        streaming_users.add(member.id)
        await general_channel.send(f"🎥 **{member.name}** has started streaming! Stream point mode enabled!")

    elif before.self_stream is True and after.self_stream is False:
        if member.id in streaming_users:
            points = stream_points[str(member.id)]
            await general_channel.send(f"🎥 **{member.name}** has stopped streaming and gained **{points}** points!")
            streaming_users.remove(member.id)
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

# Truth or Dare & Would You Rather Questions
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
    "Would you rather have unlimited money or unlimited love?", "Would you rather always lose or never play?", "Would you rather be famous or be rich?",
    "Would you rather have a time machine or the ability to teleport?", "Would you rather date your best friend or a total stranger?", "Would you rather marry for love or money?",
    "Would you rather never be able to kiss again or never hug again?", "Would you rather have your dream job or your dream partner?", "Would you rather be single forever or always be in a relationship?",
]

@bot.command()
async def truth(ctx):
    await ctx.send(f"🧐 Truth: {random.choice(truth_questions)}")

@bot.command()
async def dare(ctx):
    await ctx.send(f"🔥 Dare: {random.choice(dare_questions)}")

@bot.command(name="wouldyourather")
async def would_you_rather(ctx):
    await ctx.send(f"🤔 Would You Rather: {random.choice(would_you_rather_questions)}")

keep_alive()
bot.run(os.getenv("TOKEN"))
