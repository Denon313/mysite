"""
Mehestan Mystery Case
Central Game Orchestrator
پرونده مرموز — شهر مهستان
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class MehestanGame:
    """
    لایه مرکزی هماهنگ‌کننده تمام سیستم‌های بازی مهستان.

    این فایل عمداً مستقل طراحی شده تا فعلاً هیچ‌کدام از
    فایل‌های سالم قبلی بازنویسی یا تغییر داده نشوند.
    """

    GAME_ID = "mehestan-main"
    GAME_TITLE = "پرونده مرموز — شهر مهستان"
    CITY_NAME = "مهستان"

    def __init__(self):
        # هسته اصلی بازی
        from .engine import MehestanEngine

        # سیستم‌های بازی
        from .city import MehestanCity
        from .npcs import MehestanNPCSystem
        from .identity import IdentitySystem
        from .evidence import EvidenceSystem
        from .timeline import TimelineSystem
        from .dialogue import DialogueSystem
        from .mobile import MobileSystem
        from .cameras import CameraSystem
        from .hacker import HackerSystem
        from .hostage import HostageSystem
        from .economy import EconomySystem
        from .multiplayer import MultiplayerSystem

        self.engine = MehestanEngine()

        self.city = MehestanCity()
        self.npcs = MehestanNPCSystem()
        self.identity = IdentitySystem()
        self.evidence = EvidenceSystem()
        self.timeline = TimelineSystem()
        self.dialogue = DialogueSystem()
        self.mobile = MobileSystem()
        self.cameras = CameraSystem()
        self.hacker = HackerSystem()
        self.hostage = HostageSystem()
        self.economy = EconomySystem()
        self.multiplayer = MultiplayerSystem()

        self.case_id: Optional[str] = None

    # =========================================================
    # ابزارهای داخلی
    # =========================================================

    @staticmethod
    def _safe_call(
        obj: Any,
        method_name: str,
        *args,
        default=None,
        **kwargs
    ):
        """
        اجرای امن متد سیستم‌ها.

        اگر یک سیستم هنوز متد موردنظر را نداشته باشد،
        کل بازی به خاطر آن متوقف نمی‌شود.
        """
        method = getattr(obj, method_name, None)

        if not callable(method):
            return default

        try:
            return method(*args, **kwargs)
        except Exception:
            return default

    # =========================================================
    # Case
    # =========================================================

    def create_case(
        self,
        case_id: str = "mehestan-case-001",
        title: str = "پرونده مرموز — شهر مهستان",
        description: str = (
            "پرونده‌ای مرموز در شهر مهستان آغاز شده است."
        ),
    ):
        """ساخت پرونده جدید."""

        self.case_id = case_id

        return self.engine.create_case(
            case_id=case_id,
            title=title,
            description=description,
        )

    def get_case(self):
        """دریافت وضعیت داخلی پرونده."""

        if not self.case_id:
            return None

        return self.engine.get_case(self.case_id)

    # =========================================================
    # Players
    # =========================================================

    def add_player(
        self,
        username: str,
        display_name: str,
    ):
        """ورود کارآگاه به پرونده."""

        if not self.case_id:
            self.create_case()

        result = self.engine.add_player(
            self.case_id,
            username,
            display_name,
        )

        # ثبت در سیستم موبایل
        self._safe_call(
            self.mobile,
            "register_player",
            username,
            display_name,
        )

        # ثبت در Multiplayer
        self._safe_call(
            self.multiplayer,
            "add_player",
            username,
            display_name,
        )

        return result

    def remove_player(self, username: str):
        """خروج کارآگاه."""

        if not self.case_id:
            return False

        result = self.engine.remove_player(
            self.case_id,
            username,
        )

        self._safe_call(
            self.mobile,
            "remove_player",
            username,
        )

        self._safe_call(
            self.multiplayer,
            "remove_player",
            username,
        )

        return result

    # =========================================================
    # شروع پرونده
    # =========================================================

    def start_case(self):
        """
        شروع پرونده.

        بعد از این مرحله بازی وارد صفحه سناریو می‌شود.
        """

        if not self.case_id:
            self.create_case()

        result = self.engine.start_case(self.case_id)

        # اعلام رویداد به موبایل
        self._safe_call(
            self.mobile,
            "notify_story_event",
            "پرونده مهستان آغاز شد.",
        )

        return result

    def continue_from_scenario(self):
        """
        دکمه «▶ ادامه» سناریو.
        بازیکنان از صفحه داستان وارد شهر می‌شوند.
        """

        if not self.case_id:
            return False

        result = self.engine.continue_from_scenario(
            self.case_id
        )

        return result

    # =========================================================
    # Movement / City
    # =========================================================

    def move_player(
        self,
        username: str,
        location_id: str,
    ):
        """حرکت کارآگاه به یک مکان."""

        if not self.case_id:
            return False

        result = self.engine.move_player(
            self.case_id,
            username,
            location_id,
        )

        # ثبت موقعیت در Multiplayer
        location_name = location_id

        location = self._safe_call(
            self.city,
            "get_location",
            location_id,
            default=None,
        )

        if location is not None:
            location_name = getattr(
                location,
                "name",
                location_id,
            )

        self._safe_call(
            self.multiplayer,
            "update_location",
            username,
            location_id,
            location_name,
        )

        return result

    def get_city_state(self):
        """وضعیت عمومی شهر."""

        return self._safe_call(
            self.city,
            "public_state",
            default={},
        )

    # =========================================================
    # Evidence
    # =========================================================

    def discover_evidence(
        self,
        username: str,
        evidence_id: str,
    ):
        """کشف مدرک."""

        if not self.case_id:
            return None

        result = self.engine.discover_evidence(
            self.case_id,
            username,
            evidence_id,
        )

        self._safe_call(
            self.evidence,
            "discover_evidence",
            evidence_id,
            username,
        )

        self._safe_call(
            self.multiplayer,
            "share_discovery",
            username,
            "evidence",
            evidence_id,
        )

        return result

    def discover_clue(
        self,
        username: str,
        clue_id: str,
    ):
        """کشف سرنخ."""

        if not self.case_id:
            return None

        result = self.engine.discover_clue(
            self.case_id,
            username,
            clue_id,
        )

        self._safe_call(
            self.evidence,
            "discover_clue",
            clue_id,
            username,
        )

        return result

    # =========================================================
    # Identity
    # =========================================================

    def search_identity(
        self,
        query: str,
        access_level: str = "public",
    ):
        """جست‌وجوی هویت با تلفن، نام، پلاک و..."""

        return self._safe_call(
            self.identity,
            "search",
            query,
            access_level=access_level,
            default=[],
        )

    def verify_identity(
        self,
        query: str,
        access_level: str = "public",
    ):
        """بررسی هویت."""

        return self._safe_call(
            self.identity,
            "verify",
            query,
            access_level=access_level,
            default=None,
        )

    # =========================================================
    # NPC / Dialogue
    # =========================================================

    def ask_npc(
        self,
        username: str,
        npc_id: str,
        question: str,
    ):
        """
        پرسش آزاد از شخصیت.

        پاسخ از سیستم Dialogue می‌آید.
        """

        result = self._safe_call(
            self.dialogue,
            "ask",
            npc_id,
            question,
            username,
            default=None,
        )

        # اگر متد با امضای متفاوت باشد، نسخه دوم
        # را امتحان می‌کنیم.
        if result is None:
            result = self._safe_call(
                self.dialogue,
                "ask",
                npc_id,
                question,
                default=None,
            )

        return result

    def get_npc(self, npc_id: str):
        """دریافت اطلاعات شخصیت."""

        return self._safe_call(
            self.npcs,
            "get_npc",
            npc_id,
            default=None,
        )

    # =========================================================
    # Timeline
    # =========================================================

    def get_timeline(self):
        """دریافت خط زمانی پرونده."""

        return self._safe_call(
            self.timeline,
            "public_state",
            default={},
        )

    # =========================================================
    # Mobile
    # =========================================================

    def send_group_message(
        self,
        username: str,
        message: str,
    ):
        """ارسال پیام به گروه."""

        result = self._safe_call(
            self.mobile,
            "send_group_message",
            username,
            message,
            default=None,
        )

        return result

    def get_group_messages(self):
        """دریافت چت گروه."""

        return self._safe_call(
            self.mobile,
            "get_group_messages",
            default=[],
        )

    def get_notifications(
        self,
        username: str,
    ):
        """دریافت نوتیفیکیشن‌های بازیکن."""

        return self._safe_call(
            self.mobile,
            "get_notifications",
            username,
            default=[],
        )

    def mark_notifications_read(
        self,
        username: str,
    ):
        """خوانده‌شدن نوتیفیکیشن‌ها."""

        result = self._safe_call(
            self.mobile,
            "mark_all_read",
            username,
            default=False,
        )

        return result

    # =========================================================
    # CCTV
    # =========================================================

    def get_cameras(self):
        """وضعیت دوربین‌های شهر."""

        return self._safe_call(
            self.cameras,
            "public_state",
            default={},
        )

    def get_camera_footage(
        self,
        camera_id: str,
    ):
        """دریافت فیلم‌های یک دوربین."""

        return self._safe_call(
            self.cameras,
            "get_footage",
            camera_id,
            default=[],
        )

    # =========================================================
    # Hacker
    # =========================================================

    def get_hacker_state(self):
        """وضعیت مخفی سیستم هکر."""

        return self._safe_call(
            self.hacker,
            "public_state",
            default={},
        )

    def trigger_hacker_event(
        self,
        event_type: str,
        target: Optional[str] = None,
    ):
        """اجرای رویداد هکری."""

        result = self._safe_call(
            self.hacker,
            event_type,
            target,
            default=None,
        )

        return result

    # =========================================================
    # Hostage
    # =========================================================

    def start_hostage_event(
        self,
        target_username: str,
        location_id: str,
        ransom: int = 2_000_000,
    ):
        """شروع گروگان‌گیری."""

        result = self._safe_call(
            self.hostage,
            "start_event",
            target_username,
            location_id,
            ransom,
            default=None,
        )

        # قفل چت بازیکن
        self._safe_call(
            self.multiplayer,
            "set_hostage",
            target_username,
            True,
        )

        if self.case_id:
            self.engine.set_hostage(
                self.case_id,
                target_username,
                True,
            )

        return result

    def contribute_ransom(
        self,
        username: str,
        amount: int,
    ):
        """پرداخت بخشی از باج توسط یک بازیکن."""

        return self._safe_call(
            self.hostage,
            "contribute_ransom",
            username,
            amount,
            default=None,
        )

    def request_backup(
        self,
        username: str,
    ):
        """درخواست کمک اضطراری."""

        return self._safe_call(
            self.hostage,
            "request_backup",
            username,
            default=None,
        )

    def get_hostage_state(self):
        """وضعیت گروگان‌گیری."""

        return self._safe_call(
            self.hostage,
            "public_state",
            default={},
        )

    # =========================================================
    # Economy
    # =========================================================

    def get_balance(self, username: str):
        """موجودی بازیکن."""

        return self._safe_call(
            self.economy,
            "get_balance",
            username,
            default=0,
        )

    def reward_clue(
        self,
        username: str,
        clue_id: str,
        amount: int = 300_000,
    ):
        """پاداش کشف سرنخ."""

        return self._safe_call(
            self.economy,
            "reward_clue",
            username,
            clue_id,
            amount,
            default=None,
        )

    # =========================================================
    # Multiplayer
    # =========================================================

    def set_player_status(
        self,
        username: str,
        status: str,
    ):
        """online / weak / offline / hostage"""

        return self._safe_call(
            self.multiplayer,
            "set_status",
            username,
            status,
            default=False,
        )

    def get_players(self):
        """لیست بازیکنان و وضعیت آنلاین."""

        return self._safe_call(
            self.multiplayer,
            "public_state",
            default={},
        )

    def share_discovery(
        self,
        username: str,
        discovery_type: str,
        reference_id: str,
        title: str = "",
        description: str = "",
    ):
        """اشتراک‌گذاری دستی مدرک یا سرنخ با تیم."""

        return self._safe_call(
            self.multiplayer,
            "share_discovery",
            username,
            discovery_type,
            reference_id,
            title=title,
            description=description,
            default=None,
        )

    # =========================================================
    # Complete State
    # =========================================================

    def public_state(self):
        """
        وضعیت کامل قابل نمایش برای رابط کاربری.

        اطلاعات محرمانه عمداً اینجا قرار نمی‌گیرند.
        """

        return {
            "game": {
                "id": self.GAME_ID,
                "title": self.GAME_TITLE,
                "city": self.CITY_NAME,
            },

            "case": (
                self._safe_call(
                    self.engine,
                    "get_public_state",
                    self.case_id,
                    default={},
                )
                if self.case_id
                else {}
            ),

            "city": self.get_city_state(),

            "players": self.get_players(),

            "timeline": self.get_timeline(),

            "cameras": self.get_cameras(),

            "hostage": self.get_hostage_state(),

            "hacker": self.get_hacker_state(),

            "mobile": {
                "messages": self.get_group_messages(),
            },

            "systems": {
                "identity": True,
                "evidence": True,
                "timeline": True,
                "dialogue": True,
                "mobile": True,
                "cameras": True,
                "hacker": True,
                "hostage": True,
                "economy": True,
                "multiplayer": True,
            },
        }

    def player_state(self, username: str):
        """
        وضعیت مخصوص یک بازیکن.

        اطلاعات محرمانه فقط برای همان بازیکن
        در لایه بالاتر قابل اضافه‌شدن است.
        """

        if not self.case_id:
            return {}

        state = self._safe_call(
            self.engine,
            "get_player_state",
            self.case_id,
            username,
            default={},
        )

        if not isinstance(state, dict):
            state = {}

        state["mobile"] = {
            "notifications": self.get_notifications(username),
            "group_messages": self.get_group_messages(),
        }

        state["economy"] = {
            "balance": self.get_balance(username),
        }

        return state


# =============================================================
# Singleton
# =============================================================

mehestan_game = MehestanGame()
