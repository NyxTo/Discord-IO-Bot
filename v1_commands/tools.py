import re
from tabulate import TableFormat, Line, DataRow
from abstree import AST, NUM_RE, IDTF_RE

SEP_RE = re.compile(r'\s*,\s*|\s+')
WRAP = """The list of {kind}s must be wrapped in parentheses `()`."""
LEN_MUS = """`{len}` {kind}(s) identified.
The number of {kind}s must be exactly `{arity}`, the same as the game function."""
EMPTY = """Empty {kind} identified at index `{i}`.
The {kind}s must be {fmt} only, and must be comma- and/or whitespace-separated."""
INVLD = """Invalid {kind} `{thing}` identified at index `{i}`.
The {kind}s must be {fmt} only, and must be comma- and/or whitespace-separated."""
DUPL = """Duplicate {kind} `{thing}` identified at indices `{j}` and `{i}`.
The {kind}s must be unique, and must be comma- and/or whitespace-separated."""

fmt_guild = lambda guild: f"`{guild.name} ({guild.id})`"
fmt_role = lambda role: f"`@{role.name} ({role.id})`"

TBL_FMT = TableFormat(
    lineabove=None,
    linebelowheader=Line('', '-', '+', ''),
    linebetweenrows=None,
    linebelow=None,
    headerrow=DataRow('', '|', ''),
    datarow=DataRow('', '|', ''),
    padding=1,
    with_header_hide=None)

def has_ctrl(ctx):
    if ctx.guild is None:
        return False
    server = ctx.bot.servers[ctx.guild.id]
    return (server.ctrl_role in ctx.author.roles) if server.ctrl_role else ctx.channel.permissions_for(ctx.author).manage_guild

class ResolveError(Exception):
    def __init__(self, msg):
        super().__init__(msg)
        self.msg = msg

def resolve_call(call, arity):
    brack = call.find(')')
    if call[0] != '(' or brack == -1:
        raise ResolveError(WRAP.format(kind="argument"))
    args = SEP_RE.split(call[1:brack].strip())
    if args == ['']: args = []
    if len(args) != arity:
        raise ResolveError(LEN_MUS.format(kind="argument", len=len(args), arity=arity))
    for i, arg in enumerate(args):
        if arg == '':
            raise ResolveError(EMPTY.format(kind="argument", i=i, fmt="numeric"))
        if NUM_RE.fullmatch(arg) is None:
            raise ResolveError(INVLD.format(kind="argument", thing=arg, i=i, fmt="numeric"))
    return list(map(float, args)), call[brack + 1:].strip()

def resolve_func(func, arity=-1):
    brack = func.find(')')
    if func[0] != '(' or brack == -1:
        raise ResolveError(WRAP.format(kind="parameter"))
    params = SEP_RE.split(func[1:brack].strip())
    if params == ['']: params = []
    if arity >= 0 and len(params) != arity:
        raise ResolveError(LEN_MUS.format(kind="parameter", len=len(params), arity=arity))
    idcs = {}
    for i, param in enumerate(params):
        if param == '':
            raise ResolveError(EMPTY.format(kind="parameter", i=i, fmt="alphabetical"))
        if IDTF_RE.fullmatch(param) is None:
            raise ResolveError(INVLD.format(kind="parameter", thing=param, i=i, fmt="alphabetical"))
        if param in idcs:
            raise ResolveError(DUPL.format(kind="parameter", thing=param, j=idcs[param], i=i))
        idcs[param] = i
    expr = func[brack + 1:].strip()
    return params, expr, AST.from_expr(idcs, expr)
