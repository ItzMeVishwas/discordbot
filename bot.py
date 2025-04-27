# bot.py

import os
import json
import logging
import datetime
import asyncio

import discord
from discord.ext import commands, tasks
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

YOUR_USER_ID = 748964469039824937  # Your Discord user ID
POINTS_FILE   = "stream_points.json"

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
    logger.info("✅ %s is online and ready!", bot.user)
    # Notify owner
    try:
        owner = await bot.fetch_user(YOUR_USER_ID)
        await owner.send("✅ **Bot is now online and operational.**")
    except Exception as e:
        logger.error("❌ Could not send startup DM: %s", e)
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
            await owner.send(embed=embed)
        except Exception as e:
            logger.error("❌ Presence DM failed: %s", e)

@bot.event
async def on_voice_state_update(member, before, after):
    # Stream start
    if not before.self_stream and after.self_stream:
        streaming_users.add(member.id)
        session_start_points[member.id] = stream_points.get(str(member.id), 0)
        channel = discord.utils.get(member.guild.text_channels, name="general")
        if channel:
            await channel.send(f"🎥 **{member.name}** has begun streaming. Earning points now!")
    # Stream stop
    elif before.self_stream and not after.self_stream and member.id in streaming_users:
        total   = stream_points.get(str(member.id), 0)
        started = session_start_points.get(member.id, total)
        earned  = total - started
        channel = discord.utils.get(member.guild.text_channels, name="general")
        if channel:
            embed = discord.Embed(
                title="🎉 Streaming Session Complete",
                description=(
                    f"**{member.name}** has finished streaming and earned **{earned}** points.\n"
                    f"• **Lifetime Total:** {total} points"
                ),
                color=0xFFD700,
                timestamp=datetime.datetime.utcnow()
            )
            await channel.send(embed=embed)
        streaming_users.discard(member.id)
        session_start_points.pop(member.id, None)
        save_points(stream_points)

# ─── Background Task ───────────────────────────────────────
@tasks.loop(seconds=60)
async def add_stream_points():
    for uid in streaming_users:
        stream_points[str(uid)] += 1
    save_points(stream_points)

# ─── Stream-Points Commands ────────────────────────────────
@bot.command(name="balance")
async def balance(ctx):
    pts = stream_points.get(str(ctx.author.id), 0)
    embed = discord.Embed(
        title="💰 Stream Points Balance",
        description=f"{ctx.author.mention}, you currently have **{pts}** points.",
        color=0x00CCFF
    )
    await ctx.send(embed=embed)

@bot.command(name="leaderboard")
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
            embed.add_field(name=f"{i}. {user.name}", value=f"{pts} points", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="transferpoints")
async def transferpoints(ctx):
    embed = discord.Embed(
        title="🔄 Transfer Points",
        description="Transferring your points to the official tracker...",
        color=0xCCCCCC
    )
    msg = await ctx.send(embed=embed)
    await asyncio.sleep(1)
    stream_points[str(ctx.author.id)] = 0
    save_points(stream_points)
    embed.title       = "✅ Transfer Complete"
    embed.description = "Your points have been reset to **0**."
    embed.color       = 0x00FF00
    await msg.edit(embed=embed)

# ─── Moderation Commands ───────────────────────────────────
@bot.command(name="purge")
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    if amount < 1:
        return await ctx.send("❌ Please specify a number greater than 0.")
    to_delete = [m async for m in ctx.channel.history(limit=amount, before=ctx.message)]
    if not to_delete:
        return await ctx.send("ℹ️ No messages found to delete.")
    try:
        await ctx.channel.delete_messages(to_delete)
        embed = discord.Embed(
            title="🧹 Purge Successful",
            description=f"Deleted **{len(to_delete)}** messages.",
            color=0xFF0000
        )
        await ctx.send(embed=embed, delete_after=5)
    except Exception as e:
        await ctx.send(f"❌ Purge failed: {e}")

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    try:
        await member.ban(reason=reason)
        embed = discord.Embed(
            title="🚫 Member Banned",
            description=f"**{member}** has been banned.\n• **Reason:** {reason}",
            color=0x990000
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Failed to ban {member}: {e}")

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    try:
        await member.kick(reason=reason)
        embed = discord.Embed(
            title="👢 Member Kicked",
            description=f"**{member}** has been kicked.\n• **Reason:** {reason}",
            color=0x996600
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Failed to kick {member}: {e}")

@bot.command(name="mute")
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        muted_role = await ctx.guild.create_role(name="Muted", reason="Auto-created for muting")
        for ch in ctx.guild.channels:
            await ch.set_permissions(muted_role, send_messages=False, speak=False, add_reactions=False)
    if muted_role in member.roles:
        return await ctx.send(f"ℹ️ {member.mention} is already muted.")
    await member.add_roles(muted_role, reason=reason)
    embed = discord.Embed(
        title="🔇 Member Muted",
        description=f"**{member}** has been muted.\n• **Reason:** {reason}",
        color=0x555555
    )
    await ctx.send(embed=embed)

@bot.command(name="unmute")
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role or muted_role not in member.roles:
        return await ctx.send(f"ℹ️ {member.mention} is not muted.")
    await member.remove_roles(muted_role)
    embed = discord.Embed(
        title="🔊 Member Unmuted",
        description=f"**{member}** has been unmuted.",
        color=0x00AAAA
    )
    await ctx.send(embed=embed)

# ─── Error Handling & Launch ───────────────────────────────
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    logger.error("❌ Error in '%s': %s", ctx.command, error)
    await ctx.send(f"⚠️ An error occurred: {error}")

keep_alive()
bot.run(os.getenv("TOKEN"))
