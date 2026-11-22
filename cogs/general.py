"""أوامر عامة ومساعدة."""
import discord
from discord import app_commands
from discord.ext import commands

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="مساعدة", description="عرض قائمة الألعاب والأوامر")
    async def help_cmd(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎮 بوت الألعاب — قائمة الأوامر",
            description="اختر لعبة وابدأ بالضغط على الأمر.",
            color=0x5865F2,
        )
        games = [
            ("🔢 تخمين الرقم", "/تخمين_رقم", "خمّن الرقم السري بين 1 و 100."),
            ("🪨 حجر ورقة مقص", "/حجر_ورقة_مقص", "اللعبة الكلاسيكية، لاعب واحد ضد البوت."),
            ("🎯 شنق", "/شنق", "خمّن الكلمة قبل نفاد محاولاتك (6)."),
            ("❓ أسئلة ثقافية", "/أسئلة", "سؤال واحد من بين أسئلة ثقافية، اختيار من 4."),
            ("❌⭕ XO", "/xo", "تيك تاك تو، لاعبان (استخدم الأمر بقيمة الخصم)."),
            ("🪙 رمي العملة", "/عملة", "وجه أو كتابة."),
            ("🎲 رمي النرد", "/نرد", "رمي نرد أو أكثر، عددًا وجوانبًا مخصصين."),
            ("🎱 كرة 8", "/كرة8", "اسأل الكرة الإجابة على سؤالك."),
            ("🎰 سلوت", "/سلوت", "آلة حظ ثلاثية، جاكبوت يوجد."),
            ("📝 خلط كلمات", "/خلط", "أدخل الكلمة المخلوطة لترتّب الحروف."),
            ("🧮 تحدي رياضي", "/رياضيات", "أكمل النتيجة بسرعة."),
            ("⬆️⬇️ أعلى أو أقل", "/أعلى_أقل", "خمّن الرقم التالي أعلى أو أقل."),
            ("🃏 بلاك جاك", "/بلاك_جاك", "لعبة 21 ضد البوت."),
            ("🎡 روليت أوروبي", "/روليت", "عجلة وطاولة رهان — 13 نوع رهان."),
            ("🔫 روليت روسي", "/روسي", "لعبة حظ آمنة — 6 حجرات."),
            ("✖️ جدول الضرب", "/ضرب", "اختبار جدول الضرب المفرد."),
            ("⏱️ تحدي التفاعل", "/تفاعل", "قيّس سرعة تفاعلك، انتظر اللون الأخضر."),
            ("🧠 لعبة الذاكرة", "/ذاكرة", "اعثر على الثنائيات بين الرموز."),
            ("🎵 سيمن", "/سيمن", "تذكر النغمات وأعد السلسلة."),
            ("😄 تخمين الإيموجي", "/تخمين_إيموجي", "خمّن الكلمة من الرمز."),
            ("🃏 تحدي الورق", "/ورق", "تخمين قوة الورقة (رتبة الورق)."),
            ("🔢 متسلسل", "/متسلسل", "خمّن العدد التالي في المتسلسل."),
            ("🧩 لغز", "/لغز", "حل لغز ألغاز بسيطة."),
        ]
        for name, cmd, desc in games:
            embed.add_field(name=f"{name} `{cmd}`", value=desc, inline=False)
        embed.add_field(name="🔤 علياس إضافة `/علياس_اضافة`", value="إضافة اسم نصي بديل لأمر سلاش (مثال: `!xo`).", inline=False)
        embed.add_field(name="🗑️ علياس حذف `/علياس_حذف`", value="حذف اسم نصي بديل.", inline=False)
        embed.add_field(name="📋 علياس قائمة `/علياس_قائمة`", value="عرض كل الأسماء البديلة النصية.", inline=False)
        embed.set_footer(text="بوت الألعاب • استخدم !الاسم لتشغيل بديل نصي")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="ping", description="فحص استجابة البوت")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"🏓 بونغ! الاستجابة: {latency} مللي ثانية.", ephemeral=True)

    @app_commands.command(name="info", description="معلومات عن البوت")
    async def info(self, interaction: discord.Interaction):
        embed = discord.Embed(title="ℹ️ معلومات البوت", color=0x5865F2)
        embed.add_field(name="المكتبة", value="discord.py 2.7", inline=True)
        embed.add_field(name="اللغة", value="العربية الفصحى", inline=True)
        embed.add_field(name="عدد الخوادم", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="الألعاب", value="22+ لعبة", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(General(bot))
