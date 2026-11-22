"""البوت الرئيسي — بوت ألعاب ديسكورد شامل بواجهة رسومية."""
import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import discord
from discord import app_commands
from discord.ext import commands

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("gamebot")

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN غير موجود في ملف .env")

INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.members = True

class GameBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=INTENTS, help_command=None)

    async def setup_hook(self):
        await self.load_extension("cogs.games")
        await self.load_extension("cogs.general")
        await self.load_extension("cogs.aliases")
        try:
            synced = await self.tree.sync()
            log.info("تمت مزامنة %d امرًا", len(synced))
        except Exception as e:
            log.error("فشل مزامنة الأوامر: %s", e)

    async def on_ready(self):
        log.info("البوت متصل: %s (ID: %s)", self.user, self.user.id)
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.playing, name="🎮 ألعاب ديسكورد | /مساعدة")
        )

bot = GameBot()

if __name__ == "__main__":
    if not TOKEN:
        print("DISCORD_TOKEN مفقود")
        raise SystemExit(1)
    bot.run(TOKEN)
