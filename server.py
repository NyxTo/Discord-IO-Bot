
class Server:
    def __init__(self, dft_pfx):
        self.prefix = dft_pfx
        self.nickname = "IO Bot"
        self.anc_chnl = None
        self.ctrl_role = None
        self.ptcp_role = None
        
        self.arity = -1
        self.tree = None
        
        self.players = set() # author
        self.queries = {} # author.id: [{args: , result: }]
        self.guesses = {} # author.id: [{args: , value: , result: , correct: }]
        self.submxns = {} # author.id: [{params: , tree: , correct: }]
        self.winners = set() # author.id
    

def setup(bot):
    bot.Server = Server
    if bot.is_ready():
        bot.servers = {guild.id: Server(bot.dft_pfx) for guild in bot.guilds}
