"""
Mehestan Mystery Case
NPC Dialogue System
سیستم گفت‌وگوی هوشمند NPCهای شهر مهستان
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo


TEHRAN_TZ = ZoneInfo("Asia/Tehran")


@dataclass
class DialogueContext:
    """
    اطلاعاتی که NPC اجازه دارد بر اساس آن پاسخ بدهد.
    """

    npc_id: str

    knowledge: List[str] = field(default_factory=list)
    unknown: List[str] = field(default_factory=list)
    secrets: List[str] = field(default_factory=list)
    lies: List[str] = field(default_factory=list)

    personality: str = "normal"
    mood: str = "neutral"

    # اطلاعاتی که NPC نباید فاش کند
    confidential: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "npc_id": self.npc_id,
            "knowledge": self.knowledge,
            "unknown": self.unknown,
            "secrets": self.secrets,
            "lies": self.lies,
            "personality": self.personality,
            "mood": self.mood,
            "confidential": self.confidential,
        }


@dataclass
class DialogueMessage:
    message_id: str
    npc_id: str
    player_id: str
    question: str
    answer: str

    timestamp: str

    # اطلاعاتی برای موتور بازی
    used_knowledge: List[str] = field(default_factory=list)
    used_lie: Optional[str] = None
    revealed_secret: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.message_id,
            "npc_id": self.npc_id,
            "player_id": self.player_id,
            "question": self.question,
            "answer": self.answer,
            "timestamp": self.timestamp,
            "used_knowledge": self.used_knowledge,
            "used_lie": self.used_lie,
            "revealed_secret": self.revealed_secret,
        }


class DialogueSystem:
    """
    موتور اصلی گفت‌وگوی NPCها.

    این سیستم فعلاً مستقل از سرویس AI است.
    بعداً می‌توان یک AI provider به آن متصل کرد.
    """

    def __init__(self):
        self.contexts: Dict[str, DialogueContext] = {}
        self.history: Dict[str, List[DialogueMessage]] = {}

        self._load_default_contexts()

    # ---------------------------------------------------------
    # زمان
    # ---------------------------------------------------------

    @staticmethod
    def now() -> str:
        return datetime.now(TEHRAN_TZ).isoformat()

    # ---------------------------------------------------------
    # ثبت NPC
    # ---------------------------------------------------------

    def register_npc(
        self,
        npc_id: str,
        knowledge: Optional[List[str]] = None,
        unknown: Optional[List[str]] = None,
        secrets: Optional[List[str]] = None,
        lies: Optional[List[str]] = None,
        personality: str = "normal",
        mood: str = "neutral",
        confidential: Optional[List[str]] = None,
    ) -> DialogueContext:

        context = DialogueContext(
            npc_id=npc_id,
            knowledge=knowledge or [],
            unknown=unknown or [],
            secrets=secrets or [],
            lies=lies or [],
            personality=personality,
            mood=mood,
            confidential=confidential or [],
        )

        self.contexts[npc_id] = context
        self.history.setdefault(npc_id, [])

        return context

    # ---------------------------------------------------------
    # دریافت کانتکست
    # ---------------------------------------------------------

    def get_context(
        self,
        npc_id: str,
    ) -> Optional[DialogueContext]:

        return self.contexts.get(npc_id)

    # ---------------------------------------------------------
    # تشخیص موضوع سؤال
    # ---------------------------------------------------------

    @staticmethod
    def detect_topics(question: str) -> List[str]:

        text = question.strip().lower()

        topics = []

        keywords = {
            "time": [
                "ساعت",
                "کی",
                "چه زمانی",
                "دیشب",
                "امروز",
                "دیروز",
            ],
            "location": [
                "کجا",
                "محل",
                "مکان",
                "بود",
                "رفتی",
                "رفته",
            ],
            "person": [
                "کی",
                "چه کسی",
                "آدم",
                "مرد",
                "زن",
                "شخص",
            ],
            "victim": [
                "قربانی",
                "آرمان",
                "نیک‌فر",
                "نیکفر",
            ],
            "money": [
                "پول",
                "بانک",
                "حساب",
                "تراکنش",
            ],
            "relationship": [
                "رابطه",
                "دوست",
                "همسر",
                "فامیل",
                "آشنا",
                "دشمن",
            ],
            "phone": [
                "شماره",
                "موبایل",
                "تلفن",
                "پیام",
            ],
        }

        for topic, words in keywords.items():

            if any(word in text for word in words):
                topics.append(topic)

        return list(dict.fromkeys(topics))

    # ---------------------------------------------------------
    # پیدا کردن اطلاعات مرتبط
    # ---------------------------------------------------------

    def relevant_knowledge(
        self,
        npc_id: str,
        question: str,
    ) -> List[str]:

        context = self.get_context(npc_id)

        if not context:
            return []

        topics = self.detect_topics(question)

        if not topics:
            return context.knowledge[:3]

        result = []

        for item in context.knowledge:

            item_text = item.lower()

            # اطلاعات عمومی
            if any(
                topic_word in item_text
                for topic_word in [
                    "ساعت",
                    "دیشب",
                    "امروز",
                    "کجا",
                    "بار",
                    "خانه",
                    "بیمارستان",
                    "بانک",
                    "آرمان",
                    "قربانی",
                    "پول",
                    "شماره",
                    "موبایل",
                ]
            ):
                result.append(item)

        return result[:6]

    # ---------------------------------------------------------
    # تشخیص اینکه NPC چیزی نمی‌داند
    # ---------------------------------------------------------

    def does_not_know(
        self,
        npc_id: str,
        question: str,
    ) -> bool:

        context = self.get_context(npc_id)

        if not context:
            return True

        text = question.lower()

        for unknown_item in context.unknown:

            if unknown_item.lower() in text:
                return True

        return False

    # ---------------------------------------------------------
    # دروغ مناسب
    # ---------------------------------------------------------

    def find_lie(
        self,
        npc_id: str,
        question: str,
    ) -> Optional[str]:

        context = self.get_context(npc_id)

        if not context:
            return None

        text = question.lower()

        for lie in context.lies:

            if any(
                keyword in text
                for keyword in [
                    "کجا",
                    "ساعت",
                    "دیشب",
                    "قربانی",
                    "آرمان",
                    "پول",
                    "بانک",
                    "رابطه",
                ]
            ):
                return lie

        return None

    # ---------------------------------------------------------
    # راز
    # ---------------------------------------------------------

    def possible_secret(
        self,
        npc_id: str,
        question: str,
    ) -> Optional[str]:

        context = self.get_context(npc_id)

        if not context:
            return None

        text = question.lower()

        secret_words = [
            "راز",
            "واقعیت",
            "حقیقت",
            "چی رو پنهان",
            "چیزی رو مخفی",
            "دروغ",
        ]

        if any(word in text for word in secret_words):

            if context.secrets:
                return context.secrets[0]

        return None

    # ---------------------------------------------------------
    # پاسخ پایه بدون AI
    # ---------------------------------------------------------

    def generate_fallback_answer(
        self,
        npc_id: str,
        question: str,
    ) -> tuple[str, List[str], Optional[str], Optional[str]]:

        context = self.get_context(npc_id)

        if not context:
            return (
                "متأسفم، چیزی درباره این موضوع نمی‌دانم.",
                [],
                None,
                None,
            )

        if self.does_not_know(npc_id, question):

            return (
                "در مورد این موضوع چیزی نمی‌دونم.",
                [],
                None,
                None,
            )

        lie = self.find_lie(
            npc_id,
            question,
        )

        if lie:

            return (
                lie,
                [],
                lie,
                None,
            )

        secret = self.possible_secret(
            npc_id,
            question,
        )

        if secret:

            return (
                "یه چیزهایی هست که ترجیح می‌دم فعلاً درباره‌ش حرف نزنم.",
                [],
                None,
                secret,
            )

        knowledge = self.relevant_knowledge(
            npc_id,
            question,
        )

        if knowledge:

            answer = knowledge[0]

            return (
                answer,
                knowledge,
                None,
                None,
            )

        return (
            "نمی‌دونم. من چیزی درباره این موضوع ندیدم.",
            [],
            None,
            None,
        )

    # ---------------------------------------------------------
    # ثبت مکالمه
    # ---------------------------------------------------------

    def ask(
        self,
        npc_id: str,
        player_id: str,
        question: str,
        answer: Optional[str] = None,
    ) -> DialogueMessage:

        if not question.strip():
            raise ValueError("سؤال نمی‌تواند خالی باشد.")

        if answer is None:

            (
                answer,
                used_knowledge,
                used_lie,
                revealed_secret,
            ) = self.generate_fallback_answer(
                npc_id,
                question,
            )

        else:

            used_knowledge = []
            used_lie = None
            revealed_secret = None

        message_id = (
            f"dlg-{npc_id}-"
            f"{len(self.history.get(npc_id, [])) + 1}"
        )

        message = DialogueMessage(
            message_id=message_id,
            npc_id=npc_id,
            player_id=player_id,
            question=question,
            answer=answer,
            timestamp=self.now(),
            used_knowledge=used_knowledge,
            used_lie=used_lie,
            revealed_secret=revealed_secret,
        )

        self.history.setdefault(
            npc_id,
            [],
        ).append(message)

        return message

    # ---------------------------------------------------------
    # تاریخچه
    # ---------------------------------------------------------

    def get_history(
        self,
        npc_id: str,
        limit: int = 30,
    ) -> List[DialogueMessage]:

        history = self.history.get(
            npc_id,
            [],
        )

        return history[-limit:]

    # ---------------------------------------------------------
    # وضعیت عمومی
    # ---------------------------------------------------------

    def public_state(
        self,
        npc_id: str,
    ) -> dict:

        context = self.get_context(npc_id)

        if not context:
            return {}

        return {
            "npc_id": npc_id,
            "personality": context.personality,
            "mood": context.mood,
            "conversation": [
                message.to_dict()
                for message in self.get_history(npc_id)
            ],
        }

    # ---------------------------------------------------------
    # NPCهای اولیه
    # ---------------------------------------------------------

    def _load_default_contexts(self):

        self.register_npc(
            npc_id="arman_nikfar",
            knowledge=[
                "آرمان نیک‌فر صاحب یک شرکت حمل‌ونقل کوچک بود.",
                "آرمان در هفته‌های اخیر چند بار به بانک مرکزی رفته بود.",
            ],
            unknown=[
                "اتفاقی که بعد از ساعت 21:30 رخ داده است.",
            ],
            secrets=[
                "آرمان قبل از مرگ با فردی ناشناس در ارتباط بوده است.",
            ],
            personality="serious",
            mood="dead",
        )

        self.register_npc(
            npc_id="reza_kazemi",
            knowledge=[
                "رضا کاظمی شب حادثه مدتی در بار مرکزی بوده است.",
                "رضا آرمان را از طریق کار می‌شناخت.",
                "رضا می‌داند آرمان اخیراً نگران یک بدهی مالی بوده است.",
            ],
            unknown=[
                "اتفاقات داخل خانه آرمان.",
            ],
            secrets=[
                "رضا درباره مقدار بدهی واقعی آرمان اطلاعات بیشتری دارد.",
            ],
            personality="defensive",
            mood="nervous",
        )

        self.register_npc(
            npc_id="sara_moradi",
            knowledge=[
                "سارا مرادی در بیمارستان مرکزی کار می‌کند.",
                "سارا آرمان را چند بار در بیمارستان دیده بود.",
            ],
            unknown=[
                "حرکت افراد در میدان مرکزی.",
            ],
            secrets=[
                "سارا یک پیام مهم از آرمان دریافت کرده بود.",
            ],
            personality="calm",
            mood="neutral",
        )

        self.register_npc(
            npc_id="farhad_yousefi",
            knowledge=[
                "فرهاد یوسفی راننده تاکسی است.",
                "فرهاد شب حادثه در چند نقطه شهر مسافر جابه‌جا کرده است.",
            ],
            unknown=[
                "اتفاقات داخل خانه قربانی.",
            ],
            secrets=[
                "فرهاد یک مسافر ناشناس را نزدیک خانه آرمان پیاده کرده است.",
            ],
            personality="talkative",
            mood="uneasy",
        )

        self.register_npc(
            npc_id="mina_rezaei",
            knowledge=[
                "مینا رضایی خبرنگار روزنامه مهستان است.",
                "مینا درباره زندگی کاری آرمان تحقیق کرده بود.",
            ],
            unknown=[
                "جزئیات تراکنش‌های بانکی قربانی.",
            ],
            secrets=[
                "مینا یک فایل صوتی از آرمان در اختیار دارد.",
            ],
            personality="curious",
            mood="focused",
        )


# موتور مستقل دیالوگ
dialogue_system = DialogueSystem()
