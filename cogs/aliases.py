"""نظام الأسماء البديلة النصية لأوامر السلاش."""
from __future__ import annotations

import json
import os
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
ALIASES_FILE = os.path.join(DATA_DIR, "aliases.json")


def _ensure_data():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(ALIASES_FILE):
        with open(ALIASES_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)


def load_aliases() -> dict[str, str]:
    _ensure_data()
    try:
        with open(ALIASES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return {str(k).strip().lower(): str(v).strip() for k, v in data.items()}
    except Exception:
        pass
    return {}


def save_aliases(data: dict[str, str]) -> None:
    _ensure_data()
    with open(ALIASES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class FakeResponse:
    def __init__(self, message: discord.Message):
        self._message = message
        self._done = False

    async def send_message(self, content: Any = None, *, embed: discord.Embed = None, embeds: list[discord.Embed] = None, view: discord.ui.View = None, ephemeral: bool = False, file: discord.File = None, files: list[discord.File] = None, **kwargs):
        self._done = True
        send_kwargs = {}
        if content is not None:
            send_kwargs["content"] = content
        if embed is not None:
            send_kwargs["embed"] = embed
        if embeds is not None:
            send_kwargs["embeds"] = embeds
        if view is not None:
            send_kwargs["view"] = view
        if file is not None:
            send_kwargs["file"] = file
        if files is not None:
            send_kwargs["files"] = files
        return await self._message.channel.send(**send_kwargs)

    async def send_modal(self, modal: discord.ui.Modal):
        self._done = True
        name = getattr(modal, "title", "هذا الأمر")
        return await self._message.channel.send(f"ℹ️ {self._message.author.mention} الأمر **{name}** يحتاج نافذة إدخال، استخدم الأمر السلاش مباشرة.")

    async def defer(self, ephemeral: bool = False, thinking: bool = False):
        self._done = True
        if thinking:
            async with self._message.channel.typing():
                pass

    def is_done(self) -> bool:
        return self._done


class FakeFollowup:
    def __init__(self, message: discord.Message):
        self._message = message

    async def send(self, content: Any = None, *, embed: discord.Embed = None, view: discord.ui.View = None, ephemeral: bool = False, **kwargs):
        send_kwargs = {}
        if content is not None:
            send_kwargs["content"] = content
        if embed is not None:
            send_kwargs["embed"] = embed
        if view is not None:
            send_kwargs["view"] = view
        return await self._message.channel.send(**send_kwargs)


class FakeInteraction:
    def __init__(self, message: discord.Message, bot: commands.Bot):
        self.user = message.author
        self.guild = message.guild
        self.channel = message.channel
        self.client = bot
        self.created_at = message.created_at
        self.message = message
        self.response = FakeResponse(message)
        self.followup = FakeFollowup(message)
        self._original_response = None

    async def original_response(self):
        return self._original_response

    async def edit_original_response(self, **kwargs):
        return None


class Aliases(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.aliases = load_aliases()

    def _save(self):
        save_aliases(self.aliases)

    def _all_slash_names(self) -> list[str]:
        names = []
        for cmd in self.bot.tree.walk_commands():
            if isinstance(cmd, app_commands.Command):
                names.append(cmd.qualified_name)
        return sorted(set(names))

    async def alias_name_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        current = (current or "").lower()
        choices = [name for name in self.aliases.keys() if current in name][:25]
        return [app_commands.Choice(name=a, value=a) for a in choices]

    async def slash_cmd_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        current = (current or "").lower()
        names = [n for n in self._all_slash_names() if current in n.lower()][:25]
        return [app_commands.Choice(name=n, value=n) for n in names]

    @app_commands.command(name="علياس_اضافة", description="إضافة اسم نصي بديل لأمر سلاش")
    @app_commands.describe(الاسم="الاسم النصي (بدون بادئة، مثال: xo)", الامر="اسم أمر السلاش المستهدف")
    @app_commands.autocomplete(الامر=slash_cmd_autocomplete)
    async def alias_add(self, interaction: discord.Interaction, الاسم: str, الامر: str):
        if not interaction.user.guild_permissions.manage_guild and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ تحتاج صلاحية إدارة الخادم لإضافة الأسماء البديلة.", ephemeral=True)
            return
        alias = الاسم.strip().lower().lstrip("!/")
        target = الامر.strip().lstrip("/")
        if not alias or not target:
            await interaction.response.send_message("❌ الاسم أو الأمر غير صالح.", ephemeral=True)
            return
        if " " in alias:
            await interaction.response.send_message("❌ الاسم البديل يجب أن يكون كلمة واحدة.", ephemeral=True)
            return
        known = self._all_slash_names()
        if target not in known:
            await interaction.response.send_message(f"❌ أمر السلاش `/{target}` غير موجود. الأوامر المتاحة: {', '.join(f'`/{n}`' for n in known[:20])}{'...' if len(known)>20 else ''}", ephemeral=True)
            return
        self.aliases[alias] = target
        self._save()
        await interaction.response.send_message(f"✅ تم إضافة الاسم البديل: اكتب `!{alias}` لتنفيذ `/{target}`.", ephemeral=True)

    @app_commands.command(name="علياس_حذف", description="حذف اسم نصي بديل")
    @app_commands.describe(الاسم="الاسم النصي المراد حذفه")
    @app_commands.autocomplete(الاسم=alias_name_autocomplete)
    async def alias_remove(self, interaction: discord.Interaction, الاسم: str):
        if not interaction.user.guild_permissions.manage_guild and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ تحتاج صلاحية إدارة الخادم لحذف الأسماء البديلة.", ephemeral=True)
            return
        alias = الاسم.strip().lower().lstrip("!/")
        if alias not in self.aliases:
            await interaction.response.send_message(f"❌ الاسم البديل `!{alias}` غير موجود.", ephemeral=True)
            return
        target = self.aliases.pop(alias)
        self._save()
        await interaction.response.send_message(f"✅ تم حذف الاسم البديل `!{alias}` (كان يشير إلى `/{target}`).", ephemeral=True)

    @app_commands.command(name="علياس_قائمة", description="عرض الأسماء النصية البديلة")
    async def alias_list(self, interaction: discord.Interaction):
        if not self.aliases:
            await interaction.response.send_message("ℹ️ لا توجد أسماء بديلة حالياً. أضف واحدًا بـ `/علياس_اضافة`.", ephemeral=True)
            return
        lines = [f"`!{k}` → `/{v}`" for k, v in sorted(self.aliases.items())]
        embed = discord.Embed(title="🔤 الأسماء البديلة النصية", description="\n".join(lines), color=0x5865F2)
        embed.set_footer(text="اكتب البادئة ! متبوعة بالاسم البديل")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    def _resolve_target_command(self, target: str):
        # walk commands to find exact match
        for cmd in self.bot.tree.walk_commands():
            if isinstance(cmd, app_commands.Command) and cmd.qualified_name == target:
                return cmd
        return self.bot.tree.get_command(target)

    async def _invoke_alias(self, message: discord.Message, target: str, args: list[str]):
        cmd = self._resolve_target_command(target)
        if cmd is None:
            await message.channel.send(f"❌ الأمر السلاش `/{target}` غير موجود.")
            return
        # find cog/binding
        binding = cmd.binding
        fake = FakeInteraction(message, self.bot)
        try:
            # Build args based on command parameters (skip interaction)
            params = list(cmd.parameters)
            call_args = []
            for p in params:
                if not args:
                    # try default
                    if p.default is not discord.utils.MISSING:
                        call_args.append(p.default)
                    else:
                        # required param missing - give helpful message
                        await message.channel.send(f"ℹ️ الأمر `/{target}` يحتاج معامل: **{p.name}**. استخدم: `!{self._find_alias_for(target)} {' '.join(f'<{x.name}>' for x in params)}` أو استخدم الأمر السلاش مباشرة.")
                        return
                else:
                    raw = args.pop(0)
                    # type conversion best effort
                    ann = p.type
                    try:
                        if ann is discord.AppCommandOptionType.user or p._annotation is discord.Member or p._annotation is discord.User:
                            # try parse mention/id
                            member = None
                            raw_id = raw.strip("<@!> ")
                            if raw_id.isdigit():
                                member = message.guild.get_member(int(raw_id)) if message.guild else None
                            if member is None and message.guild:
                                member = message.guild.get_member_named(raw)
                            if member is None:
                                await message.channel.send(f"❌ لم أجد العضو `{raw}`.")
                                return
                            call_args.append(member)
                        elif ann is discord.AppCommandOptionType.integer or p._annotation is int:
                            call_args.append(int(raw))
                        elif ann is discord.AppCommandOptionType.number or p._annotation is float:
                            call_args.append(float(raw))
                        else:
                            # string - join remaining for last string param
                            if p == params[-1] and args:
                                call_args.append(raw + " " + " ".join(args))
                                args.clear()
                            else:
                                call_args.append(raw)
                    except Exception:
                        call_args.append(raw)
            if binding is not None:
                await cmd.callback(binding, fake, *call_args)
            else:
                await cmd.callback(fake, *call_args)
        except Exception as e:
            await message.channel.send(f"❌ حدث خطأ أثناء تنفيذ `/{target}`: {e}")

    def _find_alias_for(self, target: str) -> str:
        for k, v in self.aliases.items():
            if v == target:
                return k
        return target

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        prefix = "!"
        content = message.content.strip()
        if not content.startswith(prefix):
            return
        body = content[len(prefix):].strip()
        if not body:
            return
        parts = body.split()
        name = parts[0].lower()
        args = parts[1:]
        target = self.aliases.get(name)
        if not target:
            return
        await self._invoke_alias(message, target, args)


async def setup(bot: commands.Bot):
    await bot.add_cog(Aliases(bot))
