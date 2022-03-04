from typing import Optional, Union, Literal
from discord import Guild, TextChannel, Role
from discord.ext.commands import command, check, dm_only, guild_only, Cog
import tools

CUR_SET = """The server {kind} is currently set to: `{cur}`.
To change it, use `{pfx}{cmd.name} {cmd.usage}`."""
NOT_SET = """The server {kind} is currently not set.
To set it, use `{pfx}{cmd.name} {cmd.usage}`."""
NOW_SET = "The server {kind} is now set to: {now}."
NOW_RMV = "The server {kind} is now removed."
HERE = "The `{pfx}{cmd.name} here` option must be used in a server only."
INVALID = "Invalid {kind} `{thing}` identified."
INVLD_SRV = """Invalid server `{nonguild}` identified.
To choose one, use `{pfx}{cmd.name} {cmd.usage}` with the server ID/name, or `here` in the server."""

CUR_SRV = """You have currently chosen the server: {guild}.
To choose one, use `{pfx}{cmd.name} {cmd.usage}` with the server ID/name, or `here` in the server."""
NOT_SRV = """You have currently not chosen a server.
To choose one, use `{pfx}{cmd.name} {cmd.usage}` with the server ID/name, or `here` in the server."""
NOW_SRV = "You have now chosen the server: {guild}."
CH_SET = """The server {kind} channel is currently set to: {chnl.mention}.
To change it, use `{pfx}{cmd.name} {cmd.usage}` with the channel ID/mention/name, or `here` in the channel."""
CH_NOT = """The server {kind} channel is currently not set.
To set it, use `{pfx}{cmd.name} {cmd.usage}` with the channel ID/mention/name, or `here` in the channel."""
ROL_SET = """The server {kind} channel is currently set to: {role}.
To change it, use `{pfx}{cmd.name} {cmd.usage}` with the channel ID/mention/name, or `none` to remove it."""
ROL_NOT = """The server {kind} channel is currently not set.
To set it, use `{pfx}{cmd.name} {cmd.usage}` with the channel ID/mention/name, or `none` to remove it."""

class Misc(Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @check(tools.has_ctrl)
    @command(aliases=["pfx"], usage="<prefix>", brief="Set the server prefix")
    async def prefix(self, ctx, pfx: Optional[str]):
        server = self.bot.servers[ctx.guild.id]
        if pfx is None:
            await ctx.send(CUR_SET.format(kind="prefix", cur=server.prefix, pfx=ctx.prefix, cmd=ctx.command))
            return
        server.prefix = pfx
        await ctx.guild.me.edit(nick=f"{server.nickname} [{pfx}]")
        await ctx.send(NOW_SET.format(kind="prefix", now=f'`{pfx}`'))
    
    @check(tools.has_ctrl)
    @command(aliases=["nick"], usage="<nickname>", brief="Set the bot nickname (excluding server prefix)")
    async def nickname(self, ctx, *, nick: Optional[str]):
        server = self.bot.servers[ctx.guild.id]
        if nick is None:
            await ctx.send(CUR_SET.format(kind="bot nickname (excluding server prefix)", cur=server.nickname, pfx=ctx.prefix, cmd=ctx.command))
            return
        server.nickname = nick
        await ctx.guild.me.edit(nick=f"{nick} [{server.prefix}]")
        await ctx.send(NOW_SET.format(kind="bot nickname", now=f'`{nick}`'))
    
    @command(aliases=["choose", "cs"], usage="<server>", brief="Choose a server to play in")
    async def choose_server(self, ctx, guild: Optional[Union[Guild, str]]):
        if guild is None:
            guild = self.bot.choices.get(ctx.author.id)
            if guild:
                await ctx.send(CUR_SRV.format(guild=tools.fmt_guild(guild), pfx=ctx.prefix, cmd=ctx.command))
            else:
                await ctx.send(NOT_SRV.format(pfx=ctx.prefix, cmd=ctx.command))
            return
        if guild == 'here':
            if ctx.guild is None:
                await ctx.send(HERE.format(pfx=ctx.prefix, cmd=ctx.command))
                return
            guild = ctx.guild
        elif isinstance(guild, str):
            await ctx.send(INVLD_SRV.format(nonguild=guild, pfx=ctx.prefix, cmd=ctx.command))
            return
        self.bot.choices[ctx.author.id] = guild
        await ctx.send(NOW_SRV.format(guild=tools.fmt_guild(guild)))
    
    @check(tools.has_ctrl)
    @command(aliases=["anc_chnl", "ac"], usage="<channel>", brief="Set the channel for game announcements")
    async def announce_channel(self, ctx, chnl: Optional[Union[TextChannel, str]]):
        server = self.bot.servers[ctx.guild.id]
        if chnl is None:
            if server.anc_chnl:
                await ctx.send(CH_SET.format(kind="announcement", chnl=server.anc_chnl, pfx=ctx.prefix, cmd=ctx.command))
            else:
                await ctx.send(CH_NOT.format(kind="announcement", pfx=ctx.prefix, cmd=ctx.command))
            return
        if chnl == 'here':
            chnl = ctx.channel
        elif isinstance(chnl, str):
            await ctx.send(INVALID.format(kind="announcement channel", thing=chnl))
            return
        server.anc_chnl = chnl
        await ctx.send(NOW_SET.format(kind="announcement channel", now=chnl.mention))
    
    @check(tools.has_ctrl)
    @command(aliases=["ctrl_role", "cr"], usage="<role>", brief="Set the role to control games")
    async def controller_role(self, ctx, role: Optional[Union[Role, str]]):
        server = self.bot.servers[ctx.guild.id]
        if role is None:
            if server.ctrl_role:
                await ctx.send(ROL_SET.format(role=tools.fmt_role(server.ctrl_role), pfx=ctx.prefix, cmd=ctx.command))
            else:
                await ctx.send(ROL_NOT.format(pfx=ctx.prefix, cmd=ctx.command))
            return
        if isinstance(role, Role):
            server.ctrl_role = role
            await ctx.send(NOW_SET.format(kind="controller role", now=tools.fmt_role(role)))
        elif role == 'none':
            server.ctrl_role = None
            await ctx.send(NOW_RMV.format(kind="controller role"))
        else: # str
            await ctx.send(INVALID.format(kind="controller role", thing=tools.fmt_role(role)))
    
    @check(tools.has_ctrl)
    @command(aliases=["ptcp_role", "pr"], usage="<role>", brief="Set the role to ping participants")
    async def participant_role(self, ctx, role: Optional[Union[Role, str]]):
        server = self.bot.servers[ctx.guild.id]
        if role is None:
            if server.ptcp_role:
                await ctx.send(CUR_PTCP.format(role=tools.fmt_role(server.ptcp_role), pfx=ctx.prefix, cmd=ctx.command))
            else:
                await ctx.send(NOT_PTCP.format(pfx=ctx.prefix, cmd=ctx.command))
            return
        if isinstance(role, Role):
            server.ptcp_role = role
            await ctx.send(NOW_SET.format(kind="participant role", now=tools.fmt_role(role)))
        elif role == 'none':
            server.ptcp_role = None
            await ctx.send(NOW_RMV.format(kind="participant role"))
        else: # str
            await ctx.send(INVALID.format(kind="participant role", thing=tools.fmt_role(role)))
    

def setup(bot):
    from importlib import reload as reimport
    reimport(tools)
    bot.add_cog(Misc(bot))