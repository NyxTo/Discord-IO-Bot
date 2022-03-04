import json
from discord import Intents
from discord.ext.commands import command, is_owner, Bot, DefaultHelpCommand

async def cmd_pfx(bot, msg):
    guild = msg.guild or bot.choices.get(msg.author.id)
    if guild:
        return bot.servers[guild.id].prefix
    return bot.dft_pfx

class IOBot(Bot):
    def __init__(self, data):
        intents = Intents.none()
        for reqd in data['intents']:
            setattr(intents, reqd, True)
        super().__init__(cmd_pfx, DefaultHelpCommand(sort_commands=False), intents=intents)
        self.dft_pfx = data['prefix']
        self.choices = {}
        for xtsn in data['extensions']:
            self.load_extension(xtsn)
    
    async def on_ready(self):
        self.servers = {guild.id: self.Server(self.dft_pfx) for guild in self.guilds}
        await self.user.edit(username=f"IO Bot [{self.dft_pfx}]")
        print('ready')
    
    async def on_guild_join(self, guild):
        self.servers[guild.id] = self.Server(self.dft_pfx)
    
    async def on_guild_remove(self, guild):
        self.servers.pop(guild.id)
    

if __name__ == '__main__':
    with open("data.json", 'r') as file:
        data = json.load(file)
    IOBot(data).run(token)