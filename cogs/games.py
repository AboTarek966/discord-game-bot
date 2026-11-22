""" cog الألعاب — جميع الألعاب بواجهة رسومية (أزرار + استمارات)."""
import discord
from discord import app_commands, ui
from discord.ext import commands
import random
import asyncio
import time

from utils.helpers import (
    COLOR_PRIMARY, COLOR_SUCCESS, COLOR_DANGER, COLOR_WARNING, COLOR_INFO, COLOR_GOLD,
    EMOJI, HANGMAN_WORDS, TRIVIA_QUESTIONS, SCRAMBLE_WORDS, EIGHT_BALL_ANSWERS,
    HANGMAN_STAGES, SIMON_COLORS, EMOJI_WORDS, CARD_RANKS,
    random_choice, scramble_word, make_card, card_value, hand_value, format_hand,
)
from utils.roulette import (
    BETS, BET_KEYS, bet_numbers, number_emoji, wheel_file, table_file,
)

games_state = {}

RANK_ORDER = {"A": 14, "K": 13, "Q": 12, "J": 11, "10": 10, "9": 9, "8": 8, "7": 7, "6": 6, "5": 5, "4": 4, "3": 3, "2": 2}

def poker_rank(cards):
    vals = sorted([RANK_ORDER[c[0]] for c in cards], reverse=True)
    flush = len({c[1] for c in cards}) == 1
    rs = sorted(set(vals), reverse=True)
    straight = False
    if len(rs) == 5:
        if rs[0] - rs[4] == 4:
            straight = True
        elif rs == [14, 5, 4, 3, 2]:
            straight = True
    counts = {}
    for v in vals:
        counts[v] = counts.get(v, 0) + 1
    groups = sorted(counts.items(), key=lambda x: -x[1])
    if straight and flush:
        if max(vals) == 14:
            return 0
        return 1
    if groups[0][1] == 4:
        return 2
    if groups[0][1] == 3 and groups[1][1] == 2:
        return 3
    if flush:
        return 4
    if straight:
        return 5
    if groups[0][1] == 3:
        return 6
    if groups[0][1] == 2 and groups[1][1] == 2:
        return 7
    if groups[0][1] == 2:
        return 8
    return 9

def cards_str(cards):
    return " ".join(f"{c[0]}{c[1]}" for c in cards)

def norm(s):
    return (s or "").strip().lower()


class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="تخمين_رقم", description="خمّن الرقم السري بين 1 و 100")
    async def guess_number(self, interaction: discord.Interaction):
        secret = random.randint(1, 100)
        view = GuessNumberView(secret, attempts=0, max_attempts=7, owner_id=interaction.user.id)
        embed = discord.Embed(title="🔢 تخمين الرقم", description="اخترت رقمًا سريًا بين **1** و **100**.\nلديك **7** محاولات.", color=COLOR_PRIMARY)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="حجر_ورقة_مقص", description="العب حجر ورقة مقص")
    async def rps(self, interaction: discord.Interaction):
        view = RPSView(interaction.user.id)
        embed = discord.Embed(title="🪨📄✂️ حجر ورقة مقص", description="اختر أحد الخيارات:", color=COLOR_PRIMARY)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="شنق", description="لعبة الشنق — خمّن الكلمة")
    async def hangman(self, interaction: discord.Interaction):
        word = random_choice(HANGMAN_WORDS)
        view = HangmanView(word, owner_id=interaction.user.id)
        await interaction.response.send_message(embed=view.make_embed(), view=view)

    @app_commands.command(name="أسئلة", description="أسئلة ثقافية متعددة الخيارات")
    async def trivia(self, interaction: discord.Interaction):
        q = random_choice(TRIVIA_QUESTIONS)
        view = TriviaView(q, owner_id=interaction.user.id)
        await interaction.response.send_message(embed=view.make_embed(), view=view)

    @app_commands.command(name="xo", description="تيك تاك تو (2 لاعبين)")
    @app_commands.describe(خصم="الخصم")
    async def xo(self, interaction: discord.Interaction, خصم: discord.Member):
        if خصم.bot or خصم.id == interaction.user.id:
            await interaction.response.send_message("❌ اللاعب المخصص غير صالح.", ephemeral=True)
            return
        view = XOView(interaction.user, خصم)
        await interaction.response.send_message(embed=view.make_embed(), view=view)

    @app_commands.command(name="عملة", description="رمي عملة (وجه / كتابة)")
    async def coin(self, interaction: discord.Interaction):
        result = random.choice(["وجه", "كتابة"])
        await interaction.response.send_message(embed=discord.Embed(title="🪙 رمي العملة", description=f"النتيجة: **{result}** 🪙", color=COLOR_GOLD))

    @app_commands.command(name="نرد", description="رمي نرد أو أكثر")
    @app_commands.describe(عدد="عدد النرد (1-6)", جوانب="عدد الجوانب (افتراضي 6)")
    async def dice(self, interaction: discord.Interaction, عدد: int = 1, جوانب: int = 6):
        if عدد < 1 or عدد > 6 or جوانب < 2 or جوانب > 100:
            await interaction.response.send_message("❌ عدد النرد 1-6، الجوانب 2-100.", ephemeral=True)
            return
        rolls = [random.randint(1, جوانب) for _ in range(عدد)]
        embed = discord.Embed(title="🎲 رمي النرد", description=" ".join(f"`{r}`" for r in rolls), color=COLOR_PRIMARY)
        if عدد > 1:
            embed.add_field(name="المجموع", value=str(sum(rolls)), inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="كرة8", description="اسأل كرة 8 سؤالاً")
    async def eight_ball(self, interaction: discord.Interaction):
        await interaction.response.send_modal(EightBallModal())

    @app_commands.command(name="سلوت", description="آلة الحظ (سلوت)")
    async def slots(self, interaction: discord.Interaction):
        view = SlotsView(interaction.user.id)
        await interaction.response.send_message(embed=view.make_embed(None), view=view)

    @app_commands.command(name="خلط", description="رتّب الحروف لتكوين الكلمة")
    async def scramble(self, interaction: discord.Interaction):
        word = random_choice(SCRAMBLE_WORDS)
        scrambled = scramble_word(word)
        view = ScrambleView(word, scrambled, owner_id=interaction.user.id)
        await interaction.response.send_message(embed=view.make_embed(), view=view)

    @app_commands.command(name="رياضيات", description="حل مسألة رياضية بسرعة")
    async def math_challenge(self, interaction: discord.Interaction):
        a = random.randint(1, 50)
        b = random.randint(1, 50)
        op = random.choice(["+", "-", "*"])
        if op == "+":
            ans = a + b
        elif op == "-":
            if a < b:
                a, b = b, a
            ans = a - b
        else:
            a = random.randint(2, 12)
            b = random.randint(2, 12)
            ans = a * b
        view = MathView(f"{a} {op} {b}", ans=ans, owner_id=interaction.user.id)
        await interaction.response.send_message(embed=view.make_embed(), view=view)

    @app_commands.command(name="أعلى_أقل", description="خمّن إن كان الرقم التالي أعلى أو أقل")
    async def higher_lower(self, interaction: discord.Interaction):
        view = HigherLowerView(current=random.randint(1, 13), owner_id=interaction.user.id, score=0)
        await interaction.response.send_message(embed=view.make_embed(), view=view)

    @app_commands.command(name="بلاك_جاك", description="لعبة بلاك جاك (21)")
    async def blackjack(self, interaction: discord.Interaction):
        view = BlackjackView(interaction.user.id)
        await interaction.response.send_message(embed=view.make_embed(), view=view)

    @app_commands.command(name="روسي", description="روليت روسي (لعبة حظ آمنة)")
    async def russian(self, interaction: discord.Interaction):
        view = RussianView(interaction.user.id)
        await interaction.response.send_message(embed=view.make_embed(), view=view)

    @app_commands.command(name="روليت", description="روليت أوروبي — اختر رهانك ودوّر العجلة")
    async def roulette(self, interaction: discord.Interaction):
        view = RouletteView(interaction.user.id)
        embeds, files = view.payload(msg="اختر نوع الرهان وقيمة الرقاقة ثم اضغط **دوّر العجلة**.")
        await interaction.response.send_message(embeds=embeds, view=view, files=files)

    @app_commands.command(name="ضرب", description="اختبار جدول الضرب")
    async def mult_table(self, interaction: discord.Interaction):
        a = random.randint(2, 12)
        b = random.randint(2, 12)
        view = MultView(a=a, b=b, ans=a * b, owner_id=interaction.user.id)
        await interaction.response.send_message(embed=view.make_embed(), view=view)

    @app_commands.command(name="تفاعل", description="تحدي سرعة التفاعل — انتظر اللون الأخضر ثم انقر")
    async def reaction(self, interaction: discord.Interaction):
        view = ReactionView(interaction.user.id)
        await interaction.response.send_message(embed=view.make_embed(), view=view)
        view.msg_created = interaction.created_at

        async def en():
            await asyncio.sleep(random.uniform(1.5, 3.5))
            for c in view.children:
                if isinstance(c, ui.Button):
                    c.disabled = False
                    c.label = "🟢 انقر الآن!"
                    c.style = discord.ButtonStyle.success
                    c.emoji = "🟢"
            try:
                await interaction.edit_original_response(embed=view.make_embed(waiting=False), view=view)
            except Exception:
                pass

        asyncio.create_task(en())

    @app_commands.command(name="ذاكرة", description="لعبة الذاكرة — جد وجمع الثنائيات")
    async def memory(self, interaction: discord.Interaction):
        view = MemoryView(interaction.user.id)
        await interaction.response.send_message(embed=view.make_embed(), view=view)

    @app_commands.command(name="سيمن", description="لعبة سيمن — تذكر النغمات وأعد السلسلة")
    async def simon(self, interaction: discord.Interaction):
        view = SimonView(interaction.user.id)
        await interaction.response.send_message(embed=view.make_embed(), view=view)

    @app_commands.command(name="تخمين_إيموجي", description="تخمين الكلمة من الرمز")
    async def emoji_guess(self, interaction: discord.Interaction):
        emoji, word = random_choice(EMOJI_WORDS)
        games_state.setdefault(interaction.user.id, {})
        games_state[interaction.user.id]["emoji_score"] = games_state[interaction.user.id].get("emoji_score", 0) + 1
        await interaction.response.send_modal(EmojiGuessModal(emoji, word))

    @app_commands.command(name="ورق", description="تحدي قوة الورقة (رتبة الورق)")
    async def card_game(self, interaction: discord.Interaction):
        cards = [make_card() for _ in range(5)]
        rank_idx = poker_rank(cards)
        await interaction.response.send_modal(CardGuessModal(cards, rank_idx))

    @app_commands.command(name="متسلسل", description="خمّن العدد التالي في المتسلسل")
    async def sequence(self, interaction: discord.Interaction):
        a = random.randint(1, 20)
        d = random.randint(1, 10)
        n = random.randint(3, 6)
        view = SequenceView(a, d, n, interaction.user.id)
        await interaction.response.send_message(embed=view.make_embed(), view=view)

    @app_commands.command(name="لغز", description="لعبة الألغاز — اختار الإجابة الصحيحة")
    async def riddle(self, interaction: discord.Interaction):
        riddles = [
            {"q": "ما هو الشيء الذي كلما أكلته زاد عدده؟", "opts": ["حاجة؟", "أرض؟", "وقت؟", "علم؟"], "ans": 0},
            {"q": "أنا أبيض وأنظف ولا أخدم ولا آكل. ما أنا؟", "opts": ["السكين", "الماء", "الصوت", "الضوء"], "ans": 0},
            {"q": "ما هو الشيء الذي له أصول لكنه لا يبني؟", "opts": ["السكين", "الاسم", "العنوان", "المشهى"], "ans": 1},
            {"q": "اذهب نحو الشمال ثلاث مرات وستكون في نفس المكان. كيف؟", "opts": ["مشي مسافة قصيرة", "اتجاه الشمال دائماً", "اختر الاتجاه", "طير"], "ans": 1},
            {"q": "ما هو المملوك الذي يملك مالكه؟", "opts": ["الكلاب", "النهر", "المدرسة", "الوقت"], "ans": 1},
            {"q": "أعلى من كل شيء وما في كل شيء. ما أنا؟", "opts": ["السماء", "الهواء", "الكون", "الشمس"], "ans": 0},
        ]
        r = random_choice(riddles)
        view = RiddleView(r, interaction.user.id)
        await interaction.response.send_message(embed=view.make_embed(), view=view)


# ===================== Views =====================

class GuessNumberView(ui.View):
    def __init__(self, secret, attempts, max_attempts, owner_id):
        super().__init__(timeout=120)
        self.secret = secret
        self.attempts = attempts
        self.max_attempts = max_attempts
        self.owner_id = owner_id
        self.finished = False

    def make_embed(self, msg=None, guess=None):
        desc = f"المحاولات: {self.attempts}/{self.max_attempts}"
        if msg:
            desc = msg + "\n" + desc
        embed = discord.Embed(title="🔢 تخمين الرقم", description=desc, color=COLOR_PRIMARY)
        if guess is not None:
            embed.add_field(name="آخر تخمين", value=str(guess), inline=True)
        return embed

    @ui.button(label="تخمين", style=discord.ButtonStyle.primary, emoji="🔢")
    async def guess_btn(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ هذه ليست لعبتك.", ephemeral=True)
            return
        if self.finished:
            await interaction.response.send_message("❌ انتهت اللعبة.", ephemeral=True)
            return
        await interaction.response.send_modal(GuessModal(self))

    @ui.button(label="استسلام", style=discord.ButtonStyle.danger, emoji="🏳️")
    async def giveup(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ هذه ليست لعبتك.", ephemeral=True)
            return
        if self.finished:
            return
        self.finished = True
        for c in self.children:
            c.disabled = True
        await interaction.response.edit_message(embed=discord.Embed(title="🏳️ استسلام", description=f"الرقم السري كان **{self.secret}**.", color=COLOR_DANGER), view=self)


class GuessModal(ui.Modal, title="أدخل تخمينك"):
    guess_input = ui.TextInput(label="رقم (1-100)", placeholder="مثال: 50", required=True, max_length=3)

    def __init__(self, view):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        v = self.view
        try:
            g = int(self.guess_input.value)
        except ValueError:
            await interaction.response.send_message("❌ أدخل رقمًا صحيحًا.", ephemeral=True)
            return
        if g < 1 or g > 100:
            await interaction.response.send_message("❌ الرقم يجب أن يكون بين 1 و 100.", ephemeral=True)
            return
        v.attempts += 1
        if g == v.secret:
            v.finished = True
            for c in v.children:
                c.disabled = True
            await interaction.response.edit_message(embed=discord.Embed(title="🎉 فوز!", description=f"أصبت! الرقم كان **{v.secret}**.\nالمحاولات: {v.attempts}/{v.max_attempts}", color=COLOR_SUCCESS), view=v)
            return
        if v.attempts >= v.max_attempts:
            v.finished = True
            for c in v.children:
                c.disabled = True
            await interaction.response.edit_message(embed=discord.Embed(title="💀 خسارة", description=f"نفدت المحاولات! الرقم كان **{v.secret}**.", color=COLOR_DANGER), view=v)
            return
        hint = "📈 أعلى" if g < v.secret else "📉 أقل"
        await interaction.response.edit_message(embed=v.make_embed(msg=f"{hint}! (تخمينك: {g})"), view=v)


class RPSView(ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=60)
        self.owner_id = owner_id
        self.finished = False

    @ui.button(label="حجر", style=discord.ButtonStyle.secondary, emoji="🪨")
    async def rock(self, interaction, button):
        await self.play(interaction, "rock")

    @ui.button(label="ورقة", style=discord.ButtonStyle.secondary, emoji="📄")
    async def paper(self, interaction, button):
        await self.play(interaction, "paper")

    @ui.button(label="مقص", style=discord.ButtonStyle.secondary, emoji="✂️")
    async def scissors(self, interaction, button):
        await self.play(interaction, "scissors")

    async def play(self, interaction, choice):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ هذه ليست لعبتك.", ephemeral=True)
            return
        if self.finished:
            return
        self.finished = True
        for c in self.children:
            c.disabled = True
        bot_choice = random.choice(["rock", "paper", "scissors"])
        names = {"rock": "🪨 حجر", "paper": "📄 ورقة", "scissors": "✂️ مقص"}
        if choice == bot_choice:
            result = "تعادل 🤝"
            color = COLOR_WARNING
        elif (choice == "rock" and bot_choice == "scissors") or (choice == "paper" and bot_choice == "rock") or (choice == "scissors" and bot_choice == "paper"):
            result = "فزت! 🏆"
            color = COLOR_SUCCESS
        else:
            result = "خسرت! 💀"
            color = COLOR_DANGER
        embed = discord.Embed(title="🪨📄✂️ حجر ورقة مقص", color=color)
        embed.add_field(name="اختيارك", value=names[choice], inline=True)
        embed.add_field(name="اختيار البوت", value=names[bot_choice], inline=True)
        embed.add_field(name="النتيجة", value=result, inline=False)
        await interaction.response.edit_message(embed=embed, view=self)


class HangmanView(ui.View):
    def __init__(self, word, owner_id):
        super().__init__(timeout=300)
        self.word = word
        self.owner_id = owner_id
        self.guessed = set()
        self.wrong = 0
        self.max_wrong = 6
        self.finished = False
        self.add_item(HangmanLetterSelect(self))

    def make_embed(self):
        display = "".join(ch if ch in self.guessed or ch == " " else "_" for ch in self.word)
        color = COLOR_PRIMARY if not self.finished else (COLOR_SUCCESS if "_" not in display.replace(" ", "") else COLOR_DANGER)
        embed = discord.Embed(title="🎯 شنق", description=f"```\n{display}\n```", color=color)
        embed.add_field(name="المحاولات الخاطئة", value=f"{self.wrong}/{self.max_wrong}", inline=True)
        if self.finished:
            if "_" not in display.replace(" ", ""):
                embed.add_field(name="النتيجة", value="🎉 فوز! خمّنت الكلمة.", inline=False)
            else:
                embed.add_field(name="النتيجة", value=f"💀 خسارة! الكلمة كانت: **{self.word}**", inline=False)
        else:
            embed.add_field(name="الشكل", value=HANGMAN_STAGES[min(self.wrong, len(HANGMAN_STAGES) - 1)], inline=False)
        return embed

    async def handle_guess(self, interaction, letter):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ هذه ليست لعبتك.", ephemeral=True)
            return
        if self.finished:
            await interaction.response.send_message("❌ انتهت اللعبة.", ephemeral=True)
            return
        letter = letter.strip()
        if not letter or len(letter) != 1:
            await interaction.response.send_message("❌ أدخل حرفًا واحدًا.", ephemeral=True)
            return
        if letter in self.guessed:
            await interaction.response.send_message("⚠️ جرّبت هذا الحرف.", ephemeral=True)
            return
        self.guessed.add(letter)
        if letter not in self.word:
            self.wrong += 1
        remaining = [ch for ch in self.word if ch != " " and ch not in self.guessed]
        if not remaining or self.wrong >= self.max_wrong:
            self.finished = True
        for c in self.children:
            if isinstance(c, ui.Select):
                c.disabled = self.finished
        await interaction.response.edit_message(embed=self.make_embed(), view=self)


class HangmanLetterSelect(ui.Select):
    def __init__(self, view):
        options = []
        for ch in list("ابتثجحخدذرزسشصضطظعغفقكلمنهوي"):
            options.append(discord.SelectOption(label=ch, value=ch))
        for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            options.append(discord.SelectOption(label=ch, value=ch))
        super().__init__(placeholder="اختر حرفًا...", min_values=1, max_values=1, options=options[:25])
        self.hv = view

    async def callback(self, interaction: discord.Interaction):
        await self.hv.handle_guess(interaction, self.values[0])


class TriviaView(ui.View):
    def __init__(self, q, owner_id):
        super().__init__(timeout=60)
        self.q = q
        self.owner_id = owner_id
        self.answered = False
        self.finished = False
        for i, opt in enumerate(q["opts"]):
            btn = ui.Button(label=opt, style=discord.ButtonStyle.secondary, custom_id=f"trivia_{i}")
            btn.callback = self.make_callback(i)
            self.add_item(btn)

    def make_embed(self):
        embed = discord.Embed(title="❓ أسئلة ثقافية", description=self.q["q"], color=COLOR_PRIMARY)
        embed.set_footer(text="اختر إجابة (60 ثانية)")
        return embed

    def make_callback(self, idx):
        async def cb(interaction: discord.Interaction):
            if interaction.user.id != self.owner_id:
                await interaction.response.send_message("❌ هذه ليست لعبتك.", ephemeral=True)
                return
            if self.answered:
                await interaction.response.send_message("❌ تمت الإجابة بالفعل.", ephemeral=True)
                return
            self.answered = True
            self.finished = True
            for c in self.children:
                c.disabled = True
            correct = self.q["ans"]
            if idx == correct:
                color = COLOR_SUCCESS
                msg = "✅ إجابة صحيحة!"
            else:
                color = COLOR_DANGER
                msg = f"❌ خطأ! الإجابة الصحيحة: **{self.q['opts'][correct]}**"
            embed = discord.Embed(title="❓ نتيجة", description=f"{self.q['q']}\n\n{msg}", color=color)
            await interaction.response.edit_message(embed=embed, view=self)
        return cb


class XOView(ui.View):
    def __init__(self, p1, p2):
        super().__init__(timeout=300)
        self.p1 = p1
        self.p2 = p2
        self.board = [""] * 9
        self.turn = p1.id
        self.finished = False
        self.winner = None
        for i in range(9):
            btn = ui.Button(label="\u200b", style=discord.ButtonStyle.secondary, custom_id=f"xo_{i}", row=i // 3)
            btn.callback = self.make_callback(i)
            self.add_item(btn)

    def make_embed(self):
        turn_name = self.p1.display_name if self.turn == self.p1.id else self.p2.display_name
        if self.finished:
            title = "❌⭕ تعادل!" if self.winner is None else f"❌⭕ فاز {self.p1.display_name if self.winner == self.p1.id else self.p2.display_name}!"
            color = COLOR_SUCCESS if self.winner else COLOR_WARNING
        else:
            title = "❌⭕ XO — تيك تاك تو"
            color = COLOR_PRIMARY
        desc = f"**{self.p1.display_name}** (❌) مقابل **{self.p2.display_name}** (⭕)\n"
        if not self.finished:
            desc += f"دور: **{turn_name}**"
        embed = discord.Embed(title=title, description=desc, color=color)
        rows = []
        for r in range(3):
            cells = []
            for c in range(3):
                v = self.board[r * 3 + c]
                cells.append(v if v else "⬜")
            rows.append(" ".join(cells))
        embed.add_field(name="اللوحة", value="\n".join(rows), inline=False)
        return embed

    def check_winner(self):
        lines = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]
        for a, b, c in lines:
            if self.board[a] and self.board[a] == self.board[b] == self.board[c]:
                return self.board[a]
        if all(self.board):
            return "draw"
        return None

    def make_callback(self, idx):
        async def cb(interaction: discord.Interaction):
            if interaction.user.id not in (self.p1.id, self.p2.id):
                await interaction.response.send_message("❌ لست مشاركًا.", ephemeral=True)
                return
            if self.finished:
                await interaction.response.send_message("❌ انتهت اللعبة.", ephemeral=True)
                return
            if interaction.user.id != self.turn:
                await interaction.response.send_message("❌ ليس دورك.", ephemeral=True)
                return
            if self.board[idx]:
                await interaction.response.send_message("❌ مربع مشغول.", ephemeral=True)
                return
            mark = "❌" if self.turn == self.p1.id else "⭕"
            self.board[idx] = mark
            btn = self.children[idx]
            btn.label = mark
            btn.disabled = True
            btn.style = discord.ButtonStyle.success if mark == "❌" else discord.ButtonStyle.danger
            res = self.check_winner()
            if res == "draw":
                self.finished = True
                self.winner = None
            elif res:
                self.finished = True
                self.winner = self.p1.id if res == "❌" else self.p2.id
            else:
                self.turn = self.p2.id if self.turn == self.p1.id else self.p1.id
            if self.finished:
                for c in self.children:
                    c.disabled = True
            await interaction.response.edit_message(embed=self.make_embed(), view=self)
        return cb


class EightBallModal(ui.Modal, title="🎱 اسأل كرة 8"):
    question = ui.TextInput(label="سؤالك", placeholder="اسأل أي شيء...", required=True, max_length=200)

    async def on_submit(self, interaction: discord.Interaction):
        ans = random_choice(EIGHT_BALL_ANSWERS)
        embed = discord.Embed(title="🎱 كرة 8", description=f"سؤالك: **{self.question.value}**\n\nالإجابة: **{ans}**", color=COLOR_PRIMARY)
        await interaction.response.send_message(embed=embed)


class SlotsView(ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=60)
        self.owner_id = owner_id
        self.spinning = False
        self.symbols = ["🍒", "🍋", "🍊", "🍇", "⭐", "💎", "7️⃣"]

    def make_embed(self, result):
        if result is None:
            return discord.Embed(title="🎰 سلوت", description="اضغط «دور» لبدء اللعب.", color=COLOR_PRIMARY)
        a, b, c = result
        line = f"{a} | {b} | {c}"
        if a == b == c:
            msg, color = "🎉 جاكبوت! ثلاثة تطابقات!", COLOR_SUCCESS
        elif a == b or b == c or a == c:
            msg, color = "✨ فوز صغير! تطابقان.", COLOR_WARNING
        else:
            msg, color = "💀 لا فوز هذه المرة.", COLOR_DANGER
        return discord.Embed(title="🎰 سلوت", description=f"```\n{line}\n```\n{msg}", color=color)

    @ui.button(label="دور", style=discord.ButtonStyle.primary, emoji="🎰")
    async def spin(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ هذه ليست لعبتك.", ephemeral=True)
            return
        if self.spinning:
            return
        self.spinning = True
        button.disabled = True
        await interaction.response.edit_message(view=self)
        await asyncio.sleep(1.2)
        result = [random.choice(self.symbols) for _ in range(3)]
        self.spinning = False
        button.disabled = False
        await interaction.response.edit_message(embed=self.make_embed(result), view=self)


class ScrambleView(ui.View):
    def __init__(self, word, scrambled, owner_id):
        super().__init__(timeout=120)
        self.word = word
        self.scrambled = scrambled
        self.owner_id = owner_id
        self.finished = False

    def make_embed(self, msg=None):
        desc = f"الكلمة المخلوطة: **{self.scrambled}**\n"
        if msg:
            desc += msg + "\n"
        desc += "اضغط «أجب» وأدخل الكلمة."
        return discord.Embed(title="📝 خلط الكلمات", description=desc, color=COLOR_PRIMARY if not self.finished else COLOR_SUCCESS)

    @ui.button(label="أجب", style=discord.ButtonStyle.primary, emoji="📝")
    async def answer_btn(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ هذه ليست لعبتك.", ephemeral=True)
            return
        if self.finished:
            await interaction.response.send_message("❌ انتهت اللعبة.", ephemeral=True)
            return
        await interaction.response.send_modal(ScrambleModal(self))

    @ui.button(label="استسلام", style=discord.ButtonStyle.danger, emoji="🏳️")
    async def giveup(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ هذه ليست لعبتك.", ephemeral=True)
            return
        if self.finished:
            return
        self.finished = True
        for c in self.children:
            c.disabled = True
        await interaction.response.edit_message(embed=discord.Embed(title="🏳️ استسلام", description=f"الكلمة كانت: **{self.word}**", color=COLOR_DANGER), view=self)


class ScrambleModal(ui.Modal, title="أدخل الكلمة"):
    answer = ui.TextInput(label="الكلمة", placeholder="...", required=True, max_length=50)

    def __init__(self, view):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        v = self.view
        if norm(self.answer.value) == norm(v.word):
            v.finished = True
            for c in v.children:
                c.disabled = True
            await interaction.response.edit_message(embed=discord.Embed(title="🎉 فوز!", description=f"أصبت! الكلمة: **{v.word}**", color=COLOR_SUCCESS), view=v)
        else:
            await interaction.response.send_message(f"❌ خطأ! حاول مرة أخرى. (تلميح: {v.scrambled})", ephemeral=True)


class MathView(ui.View):
    def __init__(self, expr, ans, owner_id):
        super().__init__(timeout=60)
        self.expr = expr
        self.ans = ans
        self.owner_id = owner_id
        self.finished = False
        self.start_time = time.time()

    def make_embed(self, msg=None):
        desc = f"حل: **{self.expr} = ?**\n"
        if msg:
            desc += msg + "\n"
        desc += "اضغط «أجب» وأدخل النتيجة."
        return discord.Embed(title="🧮 تحدي رياضي", description=desc, color=COLOR_PRIMARY)

    @ui.button(label="أجب", style=discord.ButtonStyle.primary, emoji="🧮")
    async def answer_btn(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ هذه ليست لعبتك.", ephemeral=True)
            return
        if self.finished:
            await interaction.response.send_message("❌ انتهت اللعبة.", ephemeral=True)
            return
        await interaction.response.send_modal(MathModal(self))

    @ui.button(label="استسلام", style=discord.ButtonStyle.danger, emoji="🏳️")
    async def giveup(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ هذه ليست لعبتك.", ephemeral=True)
            return
        if self.finished:
            return
        self.finished = True
        for c in self.children:
            c.disabled = True
        await interaction.response.edit_message(embed=discord.Embed(title="🏳️ استسلام", description=f"الإجابة كانت: **{self.ans}**", color=COLOR_DANGER), view=self)


class MathModal(ui.Modal, title="أدخل النتيجة"):
    answer = ui.TextInput(label="النتيجة", placeholder="...", required=True, max_length=10)

    def __init__(self, view):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        v = self.view
        try:
            g = int(self.answer.value)
        except ValueError:
            await interaction.response.send_message("❌ أدخل رقمًا.", ephemeral=True)
            return
        elapsed = round(time.time() - v.start_time, 2)
        if g == v.ans:
            v.finished = True
            for c in v.children:
                c.disabled = True
            await interaction.response.edit_message(embed=discord.Embed(title="🎉 فوز!", description=f"أصبت! {v.expr} = **{v.ans}**\nالوقت: {elapsed} ثانية", color=COLOR_SUCCESS), view=v)
        else:
            await interaction.response.send_message(f"❌ خطأ! حاول مرة أخرى. (تلميح: {v.expr})", ephemeral=True)


class HigherLowerView(ui.View):
    def __init__(self, current, owner_id, score=0):
        super().__init__(timeout=120)
        self.current = current
        self.owner_id = owner_id
        self.score = score
        self.finished = False

    def make_embed(self, msg=None):
        desc = f"الرقم الحالي: **{self.current}**\nالنقاط: **{self.score}**\n"
        if msg:
            desc += msg + "\n"
        desc += "هل الرقم التالي أعلى أم أقل؟"
        return discord.Embed(title="⬆️⬇️ أعلى أو أقل", description=desc, color=COLOR_PRIMARY)

    @ui.button(label="أعلى", style=discord.ButtonStyle.success, emoji="⬆️")
    async def higher(self, interaction: discord.Interaction, button: ui.Button):
        await self.play(interaction, True)

    @ui.button(label="أقل", style=discord.ButtonStyle.danger, emoji="⬇️")
    async def lower(self, interaction: discord.Interaction, button: ui.Button):
        await self.play(interaction, False)

    @ui.button(label="استسلام", style=discord.ButtonStyle.secondary, emoji="🏳️")
    async def giveup(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ هذه ليست لعبتك.", ephemeral=True)
            return
        if self.finished:
            return
        self.finished = True
        for c in self.children:
            c.disabled = True
        await interaction.response.edit_message(embed=discord.Embed(title="🏳️ استسلام", description=f"النقاط النهائية: **{self.score}**", color=COLOR_WARNING), view=self)

    async def play(self, interaction: discord.Interaction, guess_higher: bool):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ هذه ليست لعبتك.", ephemeral=True)
            return
        if self.finished:
            return
        nxt = random.choice([x for x in range(1, 14) if x != self.current])
        correct = (nxt > self.current) == guess_higher
        if not correct:
            self.finished = True
            for c in self.children:
                c.disabled = True
            await interaction.response.edit_message(embed=discord.Embed(title="💀 خسارة!", description=f"كان الرقم **{nxt}**.\nالنقاط النهائية: **{self.score}**", color=COLOR_DANGER), view=self)
            return
        self.score += 1
        self.current = nxt
        await interaction.response.edit_message(embed=self.make_embed(msg=f"✅ صحيح! الجديد: **{nxt}**"), view=self)


class BlackjackView(ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=180)
        self.owner_id = owner_id
        self.player = [make_card(), make_card()]
        self.dealer = [make_card(), make_card()]
        self.finished = False

    def make_embed(self):
        pv = hand_value(self.player)
        dv = hand_value(self.dealer)
        color = COLOR_PRIMARY
        if self.finished:
            if pv > 21:
                msg, color = "💀 خسرت!", COLOR_DANGER
            elif dv > 21:
                msg, color = "🎉 فزت! الموزع خسر.", COLOR_SUCCESS
            elif pv > dv:
                msg, color = "🎉 فزت! أنت أعلى.", COLOR_SUCCESS
            elif pv < dv:
                msg, color = "💀 خسرت.", COLOR_DANGER
            else:
                msg, color = "🤝 تعادل.", COLOR_WARNING
        else:
            msg = "اختر: **اسحب** أو **قف**."
        desc = f"**يَدك:** {format_hand(self.player)} = **{pv}** 🂠\n"
        desc += f"**يَد الموزع:** {self.dealer[0][0]}{self.dealer[0][1]} 🂠 = **{hand_value([self.dealer[0]])}**"
        if self.finished and hand_value(self.dealer) <= 21:
            desc += f"\n{format_hand(self.dealer)} = **{dv}** 🂮"
        desc += f"\n\n{msg}"
        return discord.Embed(title="🃏 بلاك جاك (21)", description=desc, color=color)

    @ui.button(label="اسحب", style=discord.ButtonStyle.primary, emoji="🃏")
    async def hit(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ هذه ليست لعبتك.", ephemeral=True)
            return
        if self.finished:
            return
        self.player.append(make_card())
        pv = hand_value(self.player)
        if pv > 21 or pv == 21:
            self.finished = True
            for c in self.children:
                c.disabled = True
            await interaction.response.edit_message(embed=self.make_embed(), view=self)
            return
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @ui.button(label="قف", style=discord.ButtonStyle.secondary, emoji="✋")
    async def stand(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ هذه ليست لعبتك.", ephemeral=True)
            return
        if self.finished:
            return
        self.finished = True
        while hand_value(self.dealer) < 17:
            self.dealer.append(make_card())
        for c in self.children:
            c.disabled = True
        await interaction.response.edit_message(embed=self.make_embed(), view=self)


class RussianView(ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=120)
        self.owner_id = owner_id
        self.chamber = random.randint(1, 6)
        self.current = 1
        self.finished = False
        self.survived = 0

    def make_embed(self, msg=None):
        desc = "🔫 روليت روسي — 6 حجرات، واحدة حية. (لعبة حظ آمنة)."
        desc += f"\nالحجرات التي نجوت: **{self.survived}**\n"
        if msg:
            desc += msg + "\n"
        desc += "اضغط «اسحب الزناد»."
        return discord.Embed(title="🔫 روليت روسي", description=desc, color=COLOR_PRIMARY if not self.finished else COLOR_DANGER)

    @ui.button(label="اسحب الزناد", style=discord.ButtonStyle.danger, emoji="🔫")
    async def pull(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ هذه ليست لعبتك.", ephemeral=True)
            return
        if self.finished:
            return
        if self.current == self.chamber:
            self.finished = True
            for c in self.children:
                c.disabled = True
            await interaction.response.edit_message(embed=discord.Embed(title="💀 بانغ!", description=f"الحجرة **{self.chamber}** كانت حية!\nنجوت من **{self.survived}** حجرات.", color=COLOR_DANGER), view=self)
            return
        self.survived += 1
        self.current += 1
        if self.current > 6:
            self.chamber = random.randint(1, 6)
            self.current = 1
            await interaction.response.edit_message(embed=self.make_embed(msg="🎉 نجوت من جميع الحجرات! إعادة تعبئة..."), view=self)
        else:
            await interaction.response.edit_message(embed=self.make_embed(msg=f"😅 نجوت! (كانت الحجرة **{self.current - 1}**)"), view=self)

    @ui.button(label="استسلام", style=discord.ButtonStyle.secondary, emoji="🏳️")
    async def giveup(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ هذه ليست لعبتك.", ephemeral=True)
            return
        if self.finished:
            return
        self.finished = True
        for c in self.children:
            c.disabled = True
        await interaction.response.edit_message(embed=discord.Embed(title="🏳️ استسلام", description=f"نجوت من **{self.survived}** حجرات.", color=COLOR_WARNING), view=self)


# ── روليت أوروبي ────────────────────────────────────────────────────────
CHIP_VALUES = [10, 25, 50, 100, 250, 500]


def _bet_options(bet_key: str, bet_value) -> list:
    opts = []
    for key in BET_KEYS:
        b = BETS[key]
        desc = b["desc"]
        if key == "straight":
            desc = f"الرقم {bet_value}" if bet_value is not None else "اختر رقمًا (0-36)"
        opts.append(discord.SelectOption(
            label=b["label"], value=key, emoji=b["emoji"],
            description=desc, default=(key == bet_key),
        ))
    return opts


def _chip_options(chips: int) -> list:
    return [
        discord.SelectOption(label=f"{v} رقاقة", value=str(v), emoji="🪙", default=(v == chips))
        for v in CHIP_VALUES
    ]


class RouletteNumberModal(ui.Modal, title="رقم مباشر"):
    num_input = ui.TextInput(label="الرقم (0 إلى 36)", placeholder="مثال: 17", required=True, max_length=2)

    def __init__(self, view):
        super().__init__()
        self.rv = view

    async def on_submit(self, interaction: discord.Interaction):
        raw = (self.num_input.value or "").strip()
        if not raw.isdigit():
            await interaction.response.send_message("❌ أدخل رقمًا صحيحًا.", ephemeral=True)
            return
        n = int(raw)
        if n > 36:
            await interaction.response.send_message("❌ الرقم بين 0 و 36.", ephemeral=True)
            return
        self.rv.bet_key = "straight"
        self.rv.bet_value = n
        await self.rv.refresh(
            interaction,
            msg=f"🎯 الرهن: رقم مباشر **{n}** — العائد **35:1**",
            color=COLOR_INFO,
        )


class RouletteBetSelect(ui.Select):
    def __init__(self, view):
        super().__init__(
            placeholder="🎰 نوع الرهان...", min_values=1, max_values=1,
            options=_bet_options(view.bet_key, view.bet_value), row=0,
        )
        self.rv = view

    def sync(self):
        self.options = _bet_options(self.rv.bet_key, self.rv.bet_value)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.rv.owner_id:
            await interaction.response.send_message("❌ هذه ليست لعبتك.", ephemeral=True)
            return
        if self.rv.finished:
            await interaction.response.send_message("❌ انتهت الجولة — اضغط «رصيد جديد».", ephemeral=True)
            return
        key = self.values[0]
        if key == "straight":
            await interaction.response.send_modal(RouletteNumberModal(self.rv))
            return
        self.rv.bet_key = key
        self.rv.bet_value = None
        await self.rv.refresh(
            interaction,
            msg=f"🎯 الرهن: {BETS[key]['emoji']} **{BETS[key]['label']}** — {BETS[key]['desc']}",
            color=COLOR_INFO,
        )


class RouletteChipSelect(ui.Select):
    def __init__(self, view):
        super().__init__(
            placeholder="🪙 قيمة الرقاقة...", min_values=1, max_values=1,
            options=_chip_options(view.chips), row=1,
        )
        self.rv = view

    def sync(self):
        self.options = _chip_options(self.rv.chips)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.rv.owner_id:
            await interaction.response.send_message("❌ هذه ليست لعبتك.", ephemeral=True)
            return
        if self.rv.finished:
            await interaction.response.send_message("❌ انتهت الجولة — اضغط «رصيد جديد».", ephemeral=True)
            return
        self.rv.chips = int(self.values[0])
        await self.rv.refresh(interaction, msg=f"🪙 الرقاقة: **{self.rv.chips}**", color=COLOR_INFO)


class RouletteView(ui.View):
    CHIP_VALUES = CHIP_VALUES

    def __init__(self, owner_id):
        super().__init__(timeout=180)
        self.owner_id = owner_id
        self.bankroll = 1000
        self.chips = 50
        self.bet_key = "red"
        self.bet_value = None
        self.winner = None
        self.round_no = 0
        self.history = []
        self.finished = False
        self.result_msg = None
        self.result_color = COLOR_PRIMARY

        self.bet_select = RouletteBetSelect(self)
        self.chip_select = RouletteChipSelect(self)
        self.add_item(self.bet_select)
        self.add_item(self.chip_select)

    # ── بناء الرسالة ────────────────────────────────────────────────────
    def payload(self, msg: str | None = None):
        wbuf, wname = wheel_file(self.winner)
        tbuf, tname = table_file(self.bet_key, self.bet_value)

        bet = BETS[self.bet_key]
        label = f"{bet['emoji']} {bet['label']}"
        if self.bet_key == "straight":
            label = f"🎯 رقم مباشر — **{self.bet_value}**"

        hist = " ".join(f"{number_emoji(n)}{n}" for n in self.history[-8:]) or "—"

        e1 = discord.Embed(title="🎡 روليت أوروبي", color=self.result_color)
        lines = [
            f"**الرهان:** {label}   •   **العائد:** {bet['payout']}:1",
            f"**الرصيد:** 💰 {self.bankroll}   •   **الرقاقة:** 🪙 {self.chips}",
            f"**الجولة:** {self.round_no}   •   **آخر الفائزين:** {hist}",
            "",
            self.result_msg or "اختر نوع الرهان والرقاقات ثم اضغط **دوّر العجلة**.",
        ]
        e1.description = "\n".join(lines)
        e1.set_image(url=f"attachment://{wname}")
        e1.set_footer(text="روليت أوروبي — الجيب الأخضر 0 يأخذ كل الرهانات الخارجية")

        e2 = discord.Embed(title="🎲 طاولة الرهان", color=COLOR_GOLD)
        e2.description = (
            f"**الرهان الحالي:** {label}\n"
            f"{bet['desc']} — الأرقام التي يغطيها رهنك معلَّمة بإطار ذهبي."
        )
        e2.set_image(url=f"attachment://{tname}")

        files = [discord.File(wbuf, filename=wname), discord.File(tbuf, filename=tname)]
        return [e1, e2], files

    def _normalize_chips(self):
        if self.chips <= self.bankroll:
            return
        affordable = [v for v in CHIP_VALUES if v <= self.bankroll]
        if affordable:
            self.chips = max(affordable)

    async def refresh(self, interaction, msg: str | None = None, color: int | None = None):
        if msg is not None:
            self.result_msg = msg
            self.result_color = color or COLOR_PRIMARY
        self._normalize_chips()
        self.bet_select.sync()
        self.chip_select.sync()
        embeds, files = self.payload()
        await interaction.response.edit_message(embeds=embeds, attachments=files, view=self)

    def _guard(self, interaction) -> bool:
        if interaction.user.id != self.owner_id:
            return False
        if self.finished:
            return False
        return True

    # ── الأزرار ─────────────────────────────────────────────────────────
    @ui.button(label="دوّر العجلة", style=discord.ButtonStyle.primary, emoji="🎡", row=2)
    async def spin(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ هذه ليست لعبتك.", ephemeral=True)
            return
        if self.finished:
            await interaction.response.send_message("❌ انتهت الجولة — اضغط «رصيد جديد».", ephemeral=True)
            return
        if self.chips > self.bankroll:
            await interaction.response.send_message(f"❌ رصيدك لا يكفي ({self.bankroll}).", ephemeral=True)
            return

        self.bankroll -= self.chips
        self.winner = random.randint(0, 36)
        self.round_no += 1
        self.history.append(self.winner)
        self.history = self.history[-10:]

        covered = bet_numbers(self.bet_key, self.bet_value)
        if self.winner in covered:
            payout = self.chips * (1 + BETS[self.bet_key]["payout"])
            self.bankroll += payout
            self.result_msg = (
                f"✅ **فزت!** الكرة سقطت على {number_emoji(self.winner)} **{self.winner}**"
                f" — ربحت **+{payout}**."
            )
            self.result_color = COLOR_SUCCESS
        else:
            self.result_msg = (
                f"❌ **خسرت!** الكرة سقطت على {number_emoji(self.winner)} **{self.winner}**"
                f" — ذهبت الرقاقة **{self.chips}**."
            )
            self.result_color = COLOR_DANGER

        if self.bankroll <= 0:
            self.result_msg += "\n💸 نفدت رقاقاتك — اضغط **رصيد جديد**."

        await self.refresh(interaction)

    @ui.button(label="رصيد جديد", style=discord.ButtonStyle.success, emoji="💳", row=2)
    async def reset_bankroll(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ هذه ليست لعبتك.", ephemeral=True)
            return
        self.bankroll = 1000
        self.chips = 50
        self.bet_key = "red"
        self.bet_value = None
        self.winner = None
        self.round_no = 0
        self.history = []
        self.finished = False
        for c in self.children:
            c.disabled = False
        await self.refresh(interaction, msg="💳 **رصيد جديد:** 1000 رقاقة — حظًا سعيدًا!", color=COLOR_INFO)

    @ui.button(label="إنهاء الجولة", style=discord.ButtonStyle.secondary, emoji="🏁", row=2)
    async def end_game(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ هذه ليست لعبتك.", ephemeral=True)
            return
        self.finished = True
        for c in self.children:
            c.disabled = True
        await self.refresh(
            interaction,
            msg=f"🏁 **انتهت الجولة.** الرصيد النهائي: **{self.bankroll}** بعد {self.round_no} جولات.",
            color=COLOR_WARNING,
        )


class MultView(ui.View):
    def __init__(self, a, b, ans, owner_id):
        super().__init__(timeout=60)
        self.a = a
        self.b = b
        self.ans = ans
        self.owner_id = owner_id
        self.finished = False

    def make_embed(self, msg=None):
        desc = f"كم ناتج: **{self.a} × {self.b}** ?\n"
        if msg:
            desc += msg + "\n"
        desc += "اضغط «أجب»."
        return discord.Embed(title="✖️ جدول الضرب", description=desc, color=COLOR_PRIMARY)

    @ui.button(label="أجب", style=discord.ButtonStyle.primary, emoji="✖️")
    async def answer_btn(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ هذه ليست لعبتك.", ephemeral=True)
            return
        if self.finished:
            await interaction.response.send_message("❌ انتهت.", ephemeral=True)
            return
        await interaction.response.send_modal(MultModal(self))

    @ui.button(label="استسلام", style=discord.ButtonStyle.danger, emoji="🏳️")
    async def giveup(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ هذه ليست لعبتك.", ephemeral=True)
            return
        if self.finished:
            return
        self.finished = True
        for c in self.children:
            c.disabled = True
        await interaction.response.edit_message(embed=discord.Embed(title="🏳️ استسلام", description=f"الإجابة: **{self.ans}**", color=COLOR_DANGER), view=self)


class MultModal(ui.Modal, title="أدخل النتيجة"):
    answer = ui.TextInput(label="الناتج", placeholder="...", required=True, max_length=6)

    def __init__(self, view):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        v = self.view
        try:
            g = int(self.answer.value)
        except ValueError:
            await interaction.response.send_message("❌ أدخل رقمًا.", ephemeral=True)
            return
        if g == v.ans:
            v.finished = True
            for c in v.children:
                c.disabled = True
            await interaction.response.edit_message(embed=discord.Embed(title="🎉 فوز!", description=f"{v.a} × {v.b} = **{v.ans}**", color=COLOR_SUCCESS), view=v)
        else:
            await interaction.response.send_message("❌ خطأ! حاول مرة أخرى.", ephemeral=True)


# ============ NEW PRO-MAX GAMES ============

class ReactionView(ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=None)
        self.owner_id = owner_id
        self.finished = False
        self.msg_created = None

    def make_embed(self, waiting=True):
        desc = "انتظر، **سيصبح الزر أخضر**...\n\n⏳" if waiting else "انتهى التحدي!"
        return discord.Embed(title="⏱️ تحدي التفاعل", description=desc, color=COLOR_PRIMARY)

    @ui.button(label="⏳ انتظر...", style=discord.ButtonStyle.secondary, disabled=True)
    async def react(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.owner_id or self.finished:
            return
        elapsed = round((interaction.created_at - self.msg_created).total_seconds() * 1000, 2) if self.msg_created else 0
        self.finished = True
        for c in self.children:
            c.disabled = True
        verdict = "🔥 أسرع من الظبي!" if elapsed < 250 else ("👍 أدى جيداً!" if elapsed < 400 else "😅 حاول تدربك!")
        await interaction.response.edit_message(embed=discord.Embed(title="⏱️ نتيجة التفاعل", description=f"زمنك: **{elapsed}** مللي ثانية\n{verdict}", color=COLOR_SUCCESS), view=self)


class MemoryView(ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=180)
        self.owner_id = owner_id
        pairs = ["🍕", "🚀", "🐉", "🌹"]
        self.cards = pairs * 2
        random.shuffle(self.cards)
        self.revealed = [False] * len(self.cards)
        self.matched = [False] * len(self.cards)
        self.first_idx = None
        self.lock = False
        self.finished = False
        self.moves = 0
        for i in range(len(self.cards)):
            b = ui.Button(label="❓", style=discord.ButtonStyle.secondary, custom_id=f"mem_{i}", row=i // 4)
            b.callback = self.make_callback(i)
            self.add_item(b)

    def make_embed(self, msg=None):
        matched_pairs = sum(1 for m in self.matched if m) // 2
        desc = f"الثنائيات المكتشفة: **{matched_pairs}/4** | الحركات: **{self.moves}**"
        if msg:
            desc += f"\n{msg}"
        return discord.Embed(title="🧠 لعبة الذاكرة", description=desc, color=COLOR_SUCCESS if self.finished else COLOR_PRIMARY)

    def make_callback(self, idx):
        async def cb(interaction: discord.Interaction):
            if interaction.user.id != self.owner_id:
                await interaction.response.send_message("❌ هذه ليست لعبتك.", ephemeral=True)
                return
            if self.finished or self.lock or self.matched[idx] or self.revealed[idx]:
                await interaction.response.defer()
                return

            self.revealed[idx] = True
            btn = self.children[idx]
            btn.label = self.cards[idx]
            btn.style = discord.ButtonStyle.primary

            if self.first_idx is None:
                self.first_idx = idx
                await interaction.response.edit_message(embed=self.make_embed(), view=self)
                return

            self.moves += 1
            second_idx = idx
            first_idx = self.first_idx
            self.first_idx = None

            if self.cards[first_idx] == self.cards[second_idx]:
                self.matched[first_idx] = True
                self.matched[second_idx] = True
                for i in (first_idx, second_idx):
                    self.children[i].disabled = True
                    self.children[i].style = discord.ButtonStyle.success
                if all(self.matched):
                    self.finished = True
                    for c in self.children:
                        c.disabled = True
                    await interaction.response.edit_message(embed=self.make_embed("🎉 وجدت كل الثنائيات!"), view=self)
                else:
                    await interaction.response.edit_message(embed=self.make_embed("✅ تطابق!"), view=self)
                return

            self.lock = True
            await interaction.response.edit_message(embed=self.make_embed("❌ لا تطابق، جرّب مجددًا."), view=self)
            await asyncio.sleep(1.0)
            for i in (first_idx, second_idx):
                if not self.matched[i]:
                    self.revealed[i] = False
                    self.children[i].label = "❓"
                    self.children[i].style = discord.ButtonStyle.secondary
            self.lock = False
            try:
                await interaction.message.edit(embed=self.make_embed(), view=self)
            except Exception:
                pass
        return cb


class SimonView(ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=180)
        self.owner_id = owner_id
        self.sequence = [random.choice(SIMON_COLORS)]
        self.user_index = 0
        self.level = 1
        self.game_over = False
        for i, color in enumerate(SIMON_COLORS):
            b = ui.Button(label=color, style=discord.ButtonStyle.secondary, custom_id=f"simon_{i}", row=0)
            b.callback = self.make_callback(color)
            self.add_item(b)

    def make_embed(self, msg=None):
        seq = " ".join(self.sequence)
        desc = f"المستوى: **{self.level}**\nالسلسلة: {seq}"
        if msg:
            desc += f"\n{msg}"
        return discord.Embed(title="🎵 سيمن", description=desc, color=COLOR_DANGER if self.game_over else COLOR_PRIMARY)

    def make_callback(self, color):
        async def cb(interaction: discord.Interaction):
            if interaction.user.id != self.owner_id:
                await interaction.response.send_message("❌ هذه ليست لعبتك.", ephemeral=True)
                return
            if self.game_over:
                await interaction.response.defer()
                return
            expected = self.sequence[self.user_index]
            if color != expected:
                self.game_over = True
                for c in self.children:
                    if isinstance(c, ui.Button):
                        c.disabled = True
                await interaction.response.edit_message(embed=self.make_embed(f"💀 خطأ! انتهت عند المستوى **{self.level}**."), view=self)
                return
            self.user_index += 1
            if self.user_index >= len(self.sequence):
                self.level += 1
                self.sequence.append(random.choice(SIMON_COLORS))
                self.user_index = 0
                await interaction.response.edit_message(embed=self.make_embed("✅ صحيح! انتقل للمستوى التالي."), view=self)
                return
            await interaction.response.edit_message(embed=self.make_embed(f"✅ تابع... ({self.user_index}/{len(self.sequence)})"), view=self)
        return cb


class EmojiGuessModal(ui.Modal, title="😄 تخمين الكلمة"):
    answer = ui.TextInput(label="كلمتك", placeholder="اكتب الكلمة هنا...", required=True, max_length=30)

    def __init__(self, emoji, word):
        super().__init__()
        self.emoji = emoji
        self.word = word

    async def on_submit(self, interaction: discord.Interaction):
        guess = norm(self.answer.value)
        won = guess == norm(self.word)
        color = COLOR_SUCCESS if won else COLOR_DANGER
        await interaction.response.send_message(embed=discord.Embed(
            title="😄 نتيجة",
            description=f"الرمز: **{self.emoji}**\nالكلمة الصحيحة: **{self.word}**\nنتيجتك: **{'فوز!' if won else 'خسارة!'}**",
            color=color,
        ))


class CardGuessModal(ui.Modal, title="🃏 تخمين رتبة الورق"):
    answer = ui.TextInput(label="اسم الرتبة", placeholder="مثل: زوج / تجويف / ترتيب...", required=True, max_length=30)

    def __init__(self, cards, rank_idx):
        super().__init__()
        self.cards = cards
        self.rank_idx = rank_idx

    async def on_submit(self, interaction: discord.Interaction):
        guess = norm(self.answer.value)
        won = guess == norm(CARD_RANKS[self.rank_idx])
        color = COLOR_SUCCESS if won else COLOR_DANGER
        await interaction.response.send_message(embed=discord.Embed(
            title="🃏 نتيجة",
            description=f"الورق: **{cards_str(self.cards)}**\nالرتبة الحقيقية: **{CARD_RANKS[self.rank_idx]}**\nنتيجتك: **{'فوز!' if won else 'خسارة!'}**",
            color=color,
        ))


class SequenceView(ui.View):
    def __init__(self, a, d, n, owner_id):
        super().__init__(timeout=60)
        self.a = a
        self.d = d
        self.n = n
        self.owner_id = owner_id
        self.finished = False

    def make_embed(self, msg=None):
        terms = [self.a + i * self.d for i in range(self.n)]
        nxt = self.a + self.n * self.d
        desc = "الأرقام: " + " ، ".join(str(t) for t in terms) + f"\n\nكم العدد التالي؟"
        if msg:
            desc += "\n" + msg
        return discord.Embed(title="🔢 متسلسل أرقام", description=desc, color=COLOR_PRIMARY)

    @ui.button(label="أجب", style=discord.ButtonStyle.primary, emoji="🔢")
    async def answer_btn(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ هذه ليست لعبتك.", ephemeral=True)
            return
        if self.finished:
            await interaction.response.send_message("❌ انتهت اللعبة.", ephemeral=True)
            return
        await interaction.response.send_modal(SequenceModal(self))

    @ui.button(label="استسلام", style=discord.ButtonStyle.danger, emoji="🏳️")
    async def giveup(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ هذه ليست لعبتك.", ephemeral=True)
            return
        if self.finished:
            return
        self.finished = True
        for c in self.children:
            c.disabled = True
        await interaction.response.edit_message(embed=discord.Embed(title="🏳️ استسلام", description=f"الرقم التالي: **{self.a + self.n * self.d}**", color=COLOR_DANGER), view=self)


class SequenceModal(ui.Modal, title="🔢 أدخل العدد التالي"):
    answer = ui.TextInput(label="العدد", placeholder="...", required=True, max_length=10)

    def __init__(self, view):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        v = self.view
        try:
            g = int(self.answer.value)
        except ValueError:
            await interaction.response.send_message("❌ أدخل رقمًا.", ephemeral=True)
            return
        if g == v.a + v.n * v.d:
            v.finished = True
            for c in v.children:
                c.disabled = True
            await interaction.response.edit_message(embed=discord.Embed(title="🎉 فوز!", description=f"الرقم التالي: **{g}**", color=COLOR_SUCCESS), view=v)
        else:
            await interaction.response.send_message("❌ خطأ! حاول مرة أخرى.", ephemeral=True)


class RiddleView(ui.View):
    def __init__(self, r, owner_id):
        super().__init__(timeout=60)
        self.r = r
        self.owner_id = owner_id
        self.answered = False
        self.finished = False
        for i, opt in enumerate(r["opts"]):
            b = ui.Button(label=opt, style=discord.ButtonStyle.secondary, custom_id=f"riddle_{i}")
            b.callback = self.make_riddle_callback(i)
            self.add_item(b)

    def make_embed(self):
        return discord.Embed(title="🧩 لغز", description=f"{self.r['q']}\n\n— اختر إجابة", color=COLOR_PRIMARY)

    def make_riddle_callback(self, idx):
        async def cb(interaction: discord.Interaction):
            if interaction.user.id != self.owner_id:
                await interaction.response.send_message("❌ هذه ليست لعبتك.", ephemeral=True)
                return
            if self.answered:
                await interaction.response.send_message("❌ تمت الإجابة.", ephemeral=True)
                return
            self.answered = True
            self.finished = True
            for c in self.children:
                c.disabled = True
            won = idx == self.r["ans"]
            color = COLOR_SUCCESS if won else COLOR_DANGER
            msg = "✅ إجابة صحيحة!" if won else f"❌ خطأ! الإجابة: **{self.r['opts'][self.r['ans']]}**"
            await interaction.response.edit_message(embed=discord.Embed(title="❓ نتيجة اللغز", description=f"{self.r['q']}\n\n{msg}", color=color), view=self)
        return cb


async def setup(bot):
    await bot.add_cog(Games(bot))
