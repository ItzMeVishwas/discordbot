import discord
from discord.ext import commands, tasks
import os
import json
import random
import datetime
import asyncio
import requests
from keep_alive import keep_alive
from collections import defaultdict, deque
import logging

# Use yt_dlp instead of youtube_dl for more reliable downloads
import yt_dlp as youtube_dl
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord_bot')

# Enable necessary intents
intents = discord.Intents.default()
intents.message_content = True
intents.presences = True
intents.members = True
intents.voice_states = True

# Initialize bot
bot = commands.Bot(command_prefix="!", help_command=None, intents=intents)

YOUR_USER_ID = 748964469039824937
POINTS_FILE = "stream_points.json"

# --- Stream‑points persistence ---
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

# --- Music playback state ---
music_queues = {}    # guild_id -> deque of queries
current_track = {}   # guild_id -> title of currently playing track

# Spotify client (Client Credentials flow)
spotify = Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET")
    )
)

# yt-dlp & ffmpeg options
ytdl_format_options = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",  # bind to IPv4
    "nocheckcertificate": True,
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}
ffmpeg_options = {"options": "-vn"}
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.title = data.get("title")

    @classmethod
    async def from_query(cls, query, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None,
            lambda: ytdl.extract_info(query, download=not stream)
        )
        if "entries" in data:
            data = data["entries"][0]
        return cls(
            discord.FFmpegPCMAudio(data["url"], **ffmpeg_options),
            data=data
        )

# --- Question lists ---

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

# --- Events & background tasks ---

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
        channel = discord.utils.get(guild.text_channels, name="general")
        if channel:
            try:
                await channel.send("✨ **New code module updated.**")
            except Exception as e:
                logger.error("Could not send update message in %s: %s", guild.name, e)
        else:
            logger.warning("No 'general' channel in %s", guild.name)
    add_stream_points.start()
    await bot.change_presence(activity=discord.Game(name="Hehe haha ing"))

@bot.event
async def on_presence_update(before, after):
    if before.status != after.status:
        try:
            user = await bot.fetch_user(YOUR_USER_ID)
            await user.send(f"⚡ **{after.name}** changed status: **{before.status}** → **{after.status}**")
        except Exception as e:
            logger.error("Error sending presence DM: %s", e)

@bot.event
async def on_voice_state_update(member, before, after):
    channel = discord.utils.get(member.guild.text_channels, name="general")
    if not channel:
        return
    if not before.self_stream and after.self_stream:
        streaming_users.add(member.id)
        session_start_points[member.id] = stream_points.get(str(member.id), 0)
        await channel.send(f"🎥 **{member.name}** has started streaming! Stream point mode enabled!")
    elif before.self_stream and not after.self_stream and member.id in streaming_users:
        current = stream_points.get(str(member.id), 0)
        start = session_start_points.get(member.id, current)
        earned = current - start
        await channel.send(f"🎥 **{member.name}** stopped streaming, earned **{earned}** points (Total: **{current}**).")
        streaming_users.remove(member.id)
        session_start_points.pop(member.id, None)
        save_points(stream_points)

@tasks.loop(seconds=60)
async def add_stream_points():
    for uid in streaming_users:
        stream_points[str(uid)] += 1
    save_points(stream_points)

# --- Original commands ---

@bot.command()
async def balance(ctx):
    points = stream_points.get(str(ctx.author.id), 0)
    await ctx.send(f"💰 **{ctx.author.name}**, you have **{points}** stream points.")

@bot.command()
async def truth(ctx):
    """Random truth question."""
    await ctx.send(f"🧐 **Truth:** {random.choice(truth_questions)}")

@bot.command()
async def dare(ctx):
    """Random dare prompt."""
    await ctx.send(f"🔥 **Dare:** {random.choice(dare_questions)}")

@bot.command(name="wouldyourather")
async def would_you_rather(ctx):
    """Random Would You Rather question."""
    await ctx.send(f"🤔 **Would You Rather:** {random.choice(would_you_rather_questions)}")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    if amount < 1:
        return await ctx.send("Please specify a number greater than 0.")
    msgs = []
    async for m in ctx.channel.history(limit=amount, before=ctx.message):
        msgs.append(m)
    if msgs:
        try:
            await ctx.channel.delete_messages(msgs)
            await ctx.send(f"🧹 Purged {len(msgs)} messages.", delete_after=5)
        except discord.Forbidden:
            await ctx.send("I lack permissions to delete messages.")
        except discord.HTTPException as e:
            await ctx.send(f"Failed to delete messages: {e}")
    else:
        await ctx.send("No messages found to delete.")

@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Pong! Latency: {round(bot.latency*1000)}ms")

@bot.command()
async def leaderboard(ctx):
    top = sorted(stream_points.items(), key=lambda i: i[1], reverse=True)[:5]
    msg = "🏆 **Leaderboard** 🏆\n"
    for idx, (uid, pts) in enumerate(top, 1):
        user = await bot.fetch_user(int(uid))
        msg += f"**{idx}. {user.name}** — {pts} points\n"
    await ctx.send(msg)

@bot.command()
async def serverinfo(ctx):
    g = ctx.guild
    await ctx.send(
        f"**Server Name:** {g.name}\n"
        f"**Server ID:** {g.id}\n"
        f"**Member Count:** {g.member_count}\n"
        f"**Created At:** {g.created_at:%Y-%m-%d %H:%M:%S}\n"
        f"**Owner:** {g.owner}"
    )

@bot.command()
@commands.has_permissions(administrator=True)
async def latencycheck(ctx):
    if ctx.channel.name != "latency":
        return await ctx.send("Use this in #latency channel.")
    now = datetime.datetime.utcnow()
    uptime = now - bot.launch_time
    embed = discord.Embed(
        title="📊 Latency Report",
        description="Details below:", color=0x3498DB, timestamp=now
    )
    embed.add_field(name="Websocket Latency", value=f"{round(bot.latency*1000)}ms", inline=True)
    embed.add_field(name="Server Count", value=f"{len(bot.guilds)}", inline=True)
    embed.add_field(name="Uptime", value=str(uptime).split('.')[0], inline=False)
    embed.set_footer(text="Provided by your mahiru.")
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    try:
        await member.ban(reason=reason)
        await ctx.send(f"🚫 {member.mention} has been banned.")
    except Exception as e:
        await ctx.send(f"❌ Failed to ban: {e}")

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    try:
        await member.kick(reason=reason)
        await ctx.send(f"👢 {member.mention} has been kicked.")
    except Exception as e:
        await ctx.send(f"❌ Failed to kick: {e}")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member, *, reason=None):
    role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not role:
        role = await ctx.guild.create_role(name="Muted", reason="Mute role")
        for ch in ctx.guild.channels:
            await ch.set_permissions(role, send_messages=False, speak=False, add_reactions=False)
    if role in member.roles:
        return await ctx.send(f"{member.mention} is already muted.")
    await member.add_roles(role, reason=reason)
    await ctx.send(f"🔇 {member.mention} has been muted.")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    role = discord.utils.get(ctx.guild.roles, name="Muted")
    if role and role in member.roles:
        await member.remove_roles(role)
        await ctx.send(f"🔊 {member.mention} has been unmuted.")
    else:
        await ctx.send(f"{member.mention} is not muted.")

@bot.command()
async def coinflip(ctx):
    await ctx.send(f"🪙 The coin landed on **{random.choice(['Heads','Tails'])}**!")

@bot.command()
async def countmessage(ctx, *, query: str):
    msg = await ctx.send(f"🔎 Counting `' {query} '`…")
    cnt = 0
    async for m in ctx.channel.history(limit=None):
        if query.lower() in m.content.lower():
            cnt += 1
    comment = (
        "Wow!" if cnt<=10 else
        "Amazing!" if cnt<=100 else
        "Crazy!" if cnt<=150 else
        "Damn!" if cnt<=200 else
        "Legendary!"
    )
    await msg.edit(content=f"🔎 Found **{cnt}** occurrences of `{query}`. {comment}")

@bot.command()
async def transferpoints(ctx):
    await ctx.send("🔄 Transferring points…")
    await asyncio.sleep(2)
    stream_points[str(ctx.author.id)] = 0
    save_points(stream_points)
    await ctx.send("✅ Your points have been reset to 0.")

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="Available Commands", color=0x3498DB)
    cmds = [
        ("!balance", "Check your stream points."),
        ("!leaderboard", "Top 5 users by points."),
        ("!transferpoints", "Submit (reset) your points."),
        ("!truth", "Random truth question."),
        ("!dare", "Random dare prompt."),
        ("!wouldyourather", "Random Would You Rather question."),
        ("!coinflip", "Flip a coin."),
        ("!countmessage <text>", "Count occurrences in channel."),
        ("!purge <n>", "Delete n messages (Manage Messages)."),
        ("!ping", "Bot latency."),
        ("!serverinfo", "Basic server info."),
        ("!latencycheck", "Detailed latency (Admin/#latency)."),
        ("!ban @user [reason]", "Ban a user (Ban Members)."),
        ("!kick @user [reason]", "Kick a user (Kick Members)."),
        ("!mute @user [reason]", "Mute by role (Manage Roles)."),
        ("!unmute @user", "Unmute a user."),
        ("!join", "Bot joins your voice channel."),
        ("!leave", "Bot leaves voice channel."),
        ("!play <query|Spotify URL>", "Play music from YouTube or Spotify."),
        ("!skip", "Skip current track."),
        ("!pause", "Pause playback."),
        ("!resume", "Resume playback."),
        ("!current", "Show now playing."),
    ]
    for name, desc in cmds:
        embed.add_field(name=name, value=desc, inline=False)
    await ctx.send(embed=embed)

# --- Music helper functions & commands ---

async def ensure_queue(ctx):
    if ctx.guild.id not in music_queues:
        music_queues[ctx.guild.id] = deque()
        current_track[ctx.guild.id] = None

async def play_next(ctx):
    q = music_queues[ctx.guild.id]
    if not q:
        current_track[ctx.guild.id] = None
        return
    query = q.popleft()
    source = await YTDLSource.from_query(query, loop=bot.loop, stream=True)
    current_track[ctx.guild.id] = source.title
    vc = ctx.voice_client
    vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))

@bot.command()
async def join(ctx):
    if not ctx.author.voice or not ctx.author.voice.channel:
        return await ctx.send("You need to be in a voice channel first.")
    ch = ctx.author.voice.channel
    if ctx.voice_client:
        await ctx.voice_client.move_to(ch)
    else:
        await ch.connect()
    await ctx.send(f"🔗 Joined **{ch.name}**")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("🔌 Disconnected.")
    else:
        await ctx.send("I’m not in a voice channel.")

@bot.command()
async def play(ctx, *, query: str):
    await ensure_queue(ctx)
    if "open.spotify.com/playlist" in query:
        pid = query.split("/")[-1].split("?")[0]
        items = spotify.playlist_items(pid, fields="items.track.name,items.track.artists.name")["items"]
        if not items:
            return await ctx.send("No tracks in that playlist.")
        await ctx.send(f"🔁 Enqueuing {len(items)} tracks…")
        for it in items:
            t = it["track"]
            music_queues[ctx.guild.id].append(f"{t['name']} {t['artists'][0]['name']}")
    elif "open.spotify.com/track" in query:
        tid = query.split("/")[-1].split("?")[0]
        t = spotify.track(tid)
        music_queues[ctx.guild.id].append(f"{t['name']} {t['artists'][0]['name']}")
    else:
        music_queues[ctx.guild.id].append(query)

    if not ctx.voice_client:
        if not ctx.author.voice:
            return await ctx.send("Join a voice channel first.")
        await ctx.author.voice.channel.connect()

    vc = ctx.voice_client
    if not vc.is_playing():
        await ctx.send("▶️ Starting playback…")
        await play_next(ctx)
    else:
        pos = len(music_queues[ctx.guild.id])
        await ctx.send(f"➕ Added to queue (position {pos}).")

@bot.command()
async def skip(ctx):
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await ctx.send("⏭️ Skipped.")
    else:
        await ctx.send("Nothing is playing.")

@bot.command()
async def pause(ctx):
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.pause()
        await ctx.send("⏸️ Paused.")
    else:
        await ctx.send("Nothing to pause.")

@bot.command()
async def resume(ctx):
    vc = ctx.voice_client
    if vc and vc.is_paused():
        vc.resume()
        await ctx.send("▶️ Resumed.")
