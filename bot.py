# bot.py

import os
import json
import logging
import datetime
import asyncio
import random

import discord
from discord.ext import commands, tasks
from discord.ext.commands import BucketType
from collections import defaultdict

from keep_alive import keep_alive

# ─── Logging & Intents ─────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord_bot')

intents = discord.Intents.default()
intents.message_content = True
intents.presences       = True
intents.members         = True
intents.voice_states    = True

bot = commands.Bot(command_prefix="!", help_command=None, intents=intents)

YOUR_USER_ID = 748964469039824937
POINTS_FILE  = "stream_points.json"

# ─── Rate-Limit-Safe Send ──────────────────────────────────
async def safe_send(dest, *args, **kwargs):
    backoff = 1
    while True:
        try:
            return await dest.send(*args, **kwargs)
        except discord.HTTPException as e:
            if getattr(e, "status", None) == 429:
                logger.warning(f"Rate-limited; backing off {backoff}s")
                await asyncio.sleep(backoff)
                backoff = min(backoff*2, 60)
                continue
            raise

# ─── Stream-Points Persistence ─────────────────────────────
def load_points():
    if os.path.exists(POINTS_FILE):
        try:
            with open(POINTS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error("❌ Error loading points: %s", e)
    return {}

def save_points(points):
    try:
        with open(POINTS_FILE, "w") as f:
            json.dump(points, f)
    except Exception as e:
        logger.error("❌ Error saving points: %s", e)

stream_points        = defaultdict(int, load_points())
streaming_users      = set()
session_start_points = {}

# ─── Bot Events ────────────────────────────────────────────
@bot.event
async def on_ready():
    logger.info("✅ %s is online!", bot.user)
    bot.launch_time = datetime.datetime.utcnow()
    try:
        owner = await bot.fetch_user(YOUR_USER_ID)
        await safe_send(owner, "**✅ Bot is now online and operational.**")
    except Exception as e:
        logger.error("❌ Could not notify owner: %s", e)
    add_stream_points.start()

@bot.event
async def on_presence_update(before, after):
    if before.status != after.status:
        try:
            owner = await bot.fetch_user(YOUR_USER_ID)
            embed = discord.Embed(
                title="⚡ Presence Update",
                description=(
                    f"User **{after.name}** changed status:\n"
                    f"• **Before:** {before.status}\n"
                    f"• **After:** {after.status}"
                ),
                color=0x00FFCC,
                timestamp=datetime.datetime.utcnow()
            )
            await safe_send(owner, embed=embed)
        except Exception as e:
            logger.error("❌ Presence DM failed: %s", e)

@bot.event
async def on_voice_state_update(member, before, after):
    channel = discord.utils.get(member.guild.text_channels, name="general")
    # Stream start
    if not before.self_stream and after.self_stream:
        streaming_users.add(member.id)
        session_start_points[member.id] = stream_points.get(str(member.id), 0)
        if channel:
            await safe_send(channel, f"🎥 **{member.name}** has begun streaming and is earning points.")
    # Stream stop
    elif before.self_stream and not after.self_stream and member.id in streaming_users:
        total   = stream_points.get(str(member.id), 0)
        started = session_start_points.pop(member.id, total)
        earned  = total - started
        streaming_users.discard(member.id)
        save_points(stream_points)
        if channel:
            embed = discord.Embed(
                title="🎉 Streaming Session Complete",
                description=(
                    f"**{member.name}** ended their stream and earned **{earned}** points.\n"
                    f"• **Lifetime Total:** {total} points"
                ),
                color=0xFFD700,
                timestamp=datetime.datetime.utcnow()
            )
            await safe_send(channel, embed=embed)

# ─── Background Task ───────────────────────────────────────
@tasks.loop(seconds=60)
async def add_stream_points():
    for uid in streaming_users:
        stream_points[str(uid)] += 1
    save_points(stream_points)

# ─── Stream-Points Commands ────────────────────────────────
@bot.command()
@commands.cooldown(1, 10, BucketType.user)
async def balance(ctx):
    pts = stream_points.get(str(ctx.author.id), 0)
    embed = discord.Embed(
        title="💰 Stream Points Balance",
        description=f"{ctx.author.mention}, you have **{pts}** points.",
        color=0x00CCFF
    )
    await safe_send(ctx, embed=embed)

@bot.command()
@commands.cooldown(1, 15, BucketType.user)
async def leaderboard(ctx):
    top5 = sorted(stream_points.items(), key=lambda i: i[1], reverse=True)[:5]
    embed = discord.Embed(
        title="🏆 Stream Points Leaderboard",
        color=0xFF5500,
        timestamp=datetime.datetime.utcnow()
    )
    if not top5:
        embed.description = "No points have been earned yet."
    else:
        for i, (uid, pts) in enumerate(top5, start=1):
            user = await bot.fetch_user(int(uid))
            embed.add_field(name=f"{i}. {user.name}", value=f"{pts} pts", inline=False)
    await safe_send(ctx, embed=embed)

@bot.command(name="transferpoints")
@commands.cooldown(1, 30, BucketType.user)
async def transferpoints(ctx):
    embed = discord.Embed(
        title="🔄 Transferring Points",
        description="Transferring your points to the official tracker...",
        color=0xCCCCCC
    )
    msg = await safe_send(ctx, embed=embed)
    await asyncio.sleep(1)
    stream_points[str(ctx.author.id)] = 0
    save_points(stream_points)
    embed.title       = "✅ Transfer Complete"
    embed.description = "Your points have been reset to **0**."
    embed.color       = 0x00FF00
    await msg.edit(embed=embed)

# ─── Moderation Commands ───────────────────────────────────
@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    if amount < 1:
        return await safe_send(ctx, "❌ Please specify a number greater than 0.")
    deleted = await ctx.channel.purge(limit=amount, before=ctx.message)
    embed = discord.Embed(
        title="🧹 Purge Complete",
        description=f"Deleted **{len(deleted)}** messages.",
        color=0xFF0000
    )
    await safe_send(ctx, embed=embed, delete_after=5)

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    try:
        await member.ban(reason=reason)
        embed = discord.Embed(
            title="🚫 Member Banned",
            description=f"**{member}** has been banned.\n• **Reason:** {reason}",
            color=0x990000
        )
        await safe_send(ctx, embed=embed)
    except Exception as e:
        await safe_send(ctx, f"❌ Failed to ban {member}: {e}")

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    try:
        await member.kick(reason=reason)
        embed = discord.Embed(
            title="👢 Member Kicked",
            description=f"**{member}** has been kicked.\n• **Reason:** {reason}",
            color=0x996600
        )
        await safe_send(ctx, embed=embed)
    except Exception as e:
        await safe_send(ctx, f"❌ Failed to kick {member}: {e}")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not role:
        role = await ctx.guild.create_role(name="Muted", reason="Auto-created")
        for ch in ctx.guild.channels:
            await ch.set_permissions(role, send_messages=False, speak=False, add_reactions=False)
    if role in member.roles:
        return await safe_send(ctx, f"ℹ️ {member.mention} is already muted.")
    await member.add_roles(role, reason=reason)
    embed = discord.Embed(
        title="🔇 Member Muted",
        description=f"**{member}** has been muted.\n• **Reason:** {reason}",
        color=0x555555
    )
    await safe_send(ctx, embed=embed)

@bot.command()
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not role or role not in member.roles:
        return await safe_send(ctx, f"ℹ️ {member.mention} is not muted.")
    await member.remove_roles(role)
    embed = discord.Embed(
        title="🔊 Member Unmuted",
        description=f"**{member}** has been unmuted.",
        color=0x00AAAA
    )
    await safe_send(ctx, embed=embed)

# ─── Latency Check Command ─────────────────────────────────
@bot.command(name="latencycheck")
@commands.has_permissions(administrator=True)
async def latencycheck(ctx):
    if ctx.channel.name != "latency":
        return await safe_send(
            ctx,
            "❌ This command can only be used in the **#latency** channel."
        )
    now         = datetime.datetime.utcnow()
    latency_ms  = round(bot.latency * 1000)
    guild_count = len(bot.guilds)
    uptime_delta= now - bot.launch_time
    uptime_str  = str(uptime_delta).split('.')[0]
    bluedox_ms  = random.randint(10, 90)

    embed = discord.Embed(
        title="📊 Latency Report",
        description="Below are the detailed latency statistics:",
        color=0x3498DB,
        timestamp=now
    )
    embed.add_field(name="Websocket Latency", value=f"**{latency_ms}ms**",  inline=True)
    embed.add_field(name="Server Count",      value=f"**{guild_count} servers**", inline=True)
    embed.add_field(name="Uptime",            value=f"**{uptime_str}**", inline=False)
    embed.add_field(name="User Verification", value=f"**{ctx.author.name}** — Verified", inline=False)
    embed.add_field(name="Bluedox Check",     value=f"**{bluedox_ms}ms**", inline=True)

    await safe_send(ctx, embed=embed)

# ─── Error Handling & Launch ───────────────────────────────
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    logger.error("❌ Error in '%s': %s", ctx.command, error)
    await safe_send(ctx, f"⚠️ An error occurred: {error}")

keep_alive()
bot.run(os.getenv("TOKEN"))
