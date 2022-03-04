import re
from tabulate import tabulate
from typing import Optional
from discord.ext.commands import command, check, dm_only, guild_only, Cog
import abstree, tools

NOT_CHSN = """You have not chosen a server to play in.
To choose one, use `{pfx}choose_server <server>` with the server ID/name, or `here` in the server.""" # inline
RUNNING = "There is {whether} game running in {what}."
NO_ANC = """This server has not set an announcement channel.
To set one, use `{pfx}announce_channel <channel>` with the channel ID/mention/name, or `here` in the channel.""" # inline
BEGUN = """{ptcp} A new game has begun, with a function on `{arity}` variable(s).
Use `{pfx}choose_server <server>` to play in this server, then DM me `{pfx}query`, `{pfx}guess`, or `{pfx}submit`.""" # inline
FINISH = """The current game in this server has finished.
Game points leaderboard:
```{lb}```"""
PRVD = """No {kind} identified.
Provide a {kind}{task}, using `{pfx}{cmd.name} {cmd.usage}`."""
INVLD_GV = """Invalid guess value `{gval}` identified.
Your guess value must be numeric only.""" # inline
EMOJI = {'tick': '\N{square root}', 'cross': 'X'} # u2714 heavy check mark, u2716 heavy multiplication x, u221A square root
PTS = {'query': 1, 'guess': {'correct': 0, 'wrong': 2}, 'submit': {'correct': 0, 'wrong': 1}}
VP_FMT = """Your past queries:
```{query_tbl}```
Your past guesses:
```{guess_tbl}```
Your past submissions:
```{sbmxn_tbl}```"""

class AskError(Exception):
    def __init__(self, msg):
        super().__init__(msg)
        self.msg = msg

class Game(Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @check(tools.has_ctrl)
    @command(aliases=["begin", "bg"], usage="(<parameter_list>) <expression>", brief="Begin a new game")
    async def begin_game(self, ctx, *, func: Optional[str]):
        server = self.bot.servers[ctx.guild.id]
        if server.anc_chnl is None:
            await ctx.send(NO_ANC.format(pfx=ctx.prefix))
            return
        if server.arity >= 0:
            await ctx.send(RUNNING.format(whether="already a", what="this server"))
            return
        if func is None:
            await ctx.send(PRVD.format(kind="function", task=" to begin a game", pfx=ctx.prefix, cmd=ctx.command))
            return
        try:
            params, _, server.tree = tools.resolve_func(func)
        except (tools.ResolveError, abstree.ParseError) as err:
            await ctx.send(err.msg)
            return
        server.arity = len(params)
        await server.anc_chnl.send(BEGUN.format(ptcp=server.ptcp_role.mention if server.ptcp_role else '', arity=server.arity, pfx=ctx.prefix))
    
    @check(tools.has_ctrl)
    @command(aliases=["finish", "fg"], brief="Finish the current game")
    async def finish_game(self, ctx):
        server = self.bot.servers[ctx.guild.id]
        if server.arity == -1:
            await ctx.send(RUNNING.format(whether="no", what="this server"))
            return
        server.arity = -1
        server.tree = None
        server.players = set()
        server.queries = {}
        server.guesses = {}
        server.submxns = {}
        server.winners = set()
        await server.anc_chnl.send(FINISH.format(lb=calc_lb(server)))
        
    @dm_only()
    @command(usage="(<argument_list>)", brief="Query a function value")
    async def query(self, ctx, *, kwari: Optional[str]):
        try:
            server = ask(self.bot, ctx.author, ctx.prefix, kwari, kind="query", task='', cmd=ctx.command)
        except AskError as err:
            await ctx.send(err.msg)
            return
        try:
            args, _ = tools.resolve_call(kwari, server.arity)
        except tools.ResolveError as err:
            await ctx.send(err.msg)
            return
        try:
            rslt = server.tree.eval_at(args)
        except abstree.EvalError as err:
            await ctx.send(err.msg)
            return
        server.players.add(ctx.author)
        entries = server.queries.setdefault(ctx.author.id, [])
        entries.append({'args': args, 'result': rslt})
        await ctx.send(f"Your query result is `{rslt}`.")
    
    @dm_only()
    @command(usage="(<argument_list>) <guess_value>", brief="Guess a function value")
    async def guess(self, ctx, *, gazz: Optional[str]):
        try:
            server = ask(self.bot, ctx.author, ctx.prefix, gazz, kind="guess", task='', cmd=ctx.command)
        except AskError as err:
            await ctx.send(err.msg)
            return
        try:
            args, gval = tools.resolve_call(gazz, server.arity)
        except tools.ResolveError as err:
            await ctx.send(err.msg)
            return
        if gval == '':
            await ctx.send(PRVD.format(kind="guess value", task='', pfx=ctx.prefix, cmd=ctx.command))
            return
        if abstree.NUM_RE.fullmatch(gval) is None:
            await ctx.send(INVLD_GV.format(gval=gval))
            return
        gval = float(gval)
        try:
            rslt = server.tree.eval_at(args)
        except abstree.EvalError as err:
            await ctx.send(err.msg)
            return
        server.players.add(ctx.author)
        correct = abstree.is_approx(gval, rslt)
        entries = server.guesses.setdefault(ctx.author.id, [])
        entries.append({'args': args, 'value': gval, 'result': rslt, 'correct': correct})
        await ctx.send(f"Your guess value of `{gval}` is {'correct!' if correct else 'wrong.'}")
    
    @dm_only()
    @command(usage="(<parameter_list>) <expression>", brief="Submit a function")
    async def submit(self, ctx, *, sbmxn: Optional[str]):
        try:
            server = ask(self.bot, ctx.author, ctx.prefix, sbmxn, kind="function", task='', cmd=ctx.command)
        except AskError as err:
            await ctx.send(err.msg)
            return
        try:
            params, expr, tree = tools.resolve_func(sbmxn, server.arity)
        except (tools.ResolveError, abstree.ParseError) as err:
            await ctx.send(err.msg)
            return
        server.players.add(ctx.author)
        correct = tree.is_ident(server.tree, server.arity)
        entries = server.submxns.setdefault(ctx.author.id, [])
        entries.append({'params': params, 'expr': expr, 'tree': tree, 'correct': correct})
        if correct:
            server.winners.add(ctx.author.id)
        await ctx.send(f"Your submission is {'correct, you win the game!' if correct else 'wrong.'}")
    
    
    @dm_only()
    @command(aliases=["past", "vp"], brief="List your past queries/guesses/submissions")
    async def view_past(self, ctx):
        guild = self.bot.choices.get(ctx.author.id)
        if guild is None:
            await ctx.send(NOT_CHSN.format(pfx=ctx.prefix))
            return
        server = self.bot.servers[guild.id]
        if server.arity == -1:
            await ctx.send(RUNNING.format(whether="no", what=f"your chosen server {tools.fmt_guild(guild)}"))
            return
        await ctx.send(VP_FMT.format(
            query_tbl=tabulate([(', '.join(map(str, entry['args'])), entry['result']) for entry in server.queries.get(ctx.author.id, [])], ["Arguments", "Result"], tools.TBL_FMT),
            guess_tbl=tabulate([(', '.join(map(str, entry['args'])), entry['value'], EMOJI['tick' if entry['correct'] else 'cross']) for entry in server.guesses.get(ctx.author.id, [])], ["Arguments", "Value", ''], tools.TBL_FMT),
            sbmxn_tbl=tabulate([(', '.join(entry['params']), entry['expr'], EMOJI['tick' if entry['correct'] else 'cross']) for entry in server.submxns.get(ctx.author.id, [])], ["Parameters", "Expression", ''], tools.TBL_FMT)))
    
    @check(tools.has_ctrl)
    @command(aliases=["lead", "lb"], brief="See the current game points leaderboard")
    async def leaderboard(self, ctx):
        server = self.bot.servers[ctx.guild.id]
        if server.arity == -1:
            await ctx.send(RUNNING.format(whether="no", what="this server"))
            return
        await ctx.send(tbl_lb(server))
    

def ask(bot, author, pfx, qsn, **kwargs):
    guild = bot.choices.get(author.id)
    if guild is None:
        raise AskError(NOT_CHSN.format(pfx=pfx))
    server = bot.servers[guild.id]
    if server.arity == -1:
        raise AskError(RUNNING.format(whether="no", what=f"your chosen server {tools.fmt_guild(guild)}"))
    if author.id in server.winners:
        raise AskError(f"You have already won the game in your chosen server {tools.fmt_guild(guild)}!")
    if qsn is None:
        raise AskError(PRVD.format(pfx=pfx, **kwargs))
    return server

def tbl_lb(server):
    lb = []
    for player in server.players:
        nq = len(server.queries.get(player.id, []))
        guesses = server.guesses.get(player.id, [])
        ngc = sum(entry['correct'] for entry in guesses)
        ngw = len(guesses) - ngc
        submxns = server.submxns.get(player.id, [])
        nsc = sum(entry['correct'] for entry in submxns)
        nsw = len(submxns) - nsc
        pts = (PTS['query'] * nq
             + PTS['guess']['correct'] * ngc
             + PTS['guess']['wrong'] * ngw
             + PTS['submit']['correct'] * nsc
             + PTS['submit']['wrong'] * nsw)
        lb.append((player, nq, f"{ngc} {EMOJI['tick']} / {ngw} {EMOJI['cross']}", f"{nsc} {EMOJI['tick']} / {nsw} {EMOJI['cross']}", pts))
    return tabulate(sorted(lb, key=lambda item: item[-1], reverse=True), ['', "Queries", "Guesses", "Submissions", "Points"], tools.TBL_FMT)

def setup(bot):
    from importlib import reload as reimport
    reimport(abstree)
    reimport(tools)
    bot.add_cog(Game(bot))