"""
Mehestan Mystery Case Engine
موتور اصلی پرونده مرموز — شهر مهستان
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo
import random
import uuid


TEHRAN_TZ = ZoneInfo("Asia/Tehran")

GAME_ID = "mehestan-main"
GAME_TITLE = "پرونده مرموز — شهر مهستان"

MIN_PLAYERS = 2
MAX_PLAYERS = 5


@dataclass
class Player:
    username: str
    display_name: str
    joined_at: str = field(
        default_factory=lambda: datetime.now(TEHRAN_TZ).isoformat()
    )
    money: int = 0
    location: str = "شهرداری مهستان"
    hostage: bool = False
    can_chat: bool = True


@dataclass
class CaseState:
    case_id: str
    title: str
    city: str
    description: str
    started: bool = False
    phase: str = "lobby"
    created_at: str = field(
        default_factory=lambda: datetime.now(TEHRAN_TZ).isoformat()
    )
    players: Dict[str, Player] = field(default_factory=dict)
    discovered_evidence: List[str] = field(default_factory=list)
    discovered_clues: List[str] = field(default_factory=list)
    visited_locations: List[str] = field(default_factory=list)
    timeline_events: List[str] = field(default_factory=list)
    decisions: List[dict] = field(default_factory=list)
    unread_notifications: Dict[str, int] = field(default_factory=dict)


class MehestanEngine:
    """
    هسته مستقل بازی مهستان.

    فعلاً مسئول:
    - ساخت پرونده
    - مدیریت بازیکنان
    - شروع پرونده
    - جابه‌جایی بازیکن بین مکان‌ها
    - ثبت مدارک و سرنخ‌ها
    - نوتیفیکیشن
    - وضعیت اولیه بازی

    سیستم‌های تخصصی بعداً به فایل‌های جداگانه متصل می‌شوند.
    """

    def __init__(self):
        self.cases: Dict[str, CaseState] = {}

    # ---------------------------------------------------------
    # زمان
    # ---------------------------------------------------------

    @staticmethod
    def now() -> str:
        return datetime.now(TEHRAN_TZ).isoformat()

    # ---------------------------------------------------------
    # ساخت پرونده
    # ---------------------------------------------------------

    def create_case(
        self,
        title: str = "سایه‌ای در مهستان",
        description: str = (
            "پرونده‌ای مرموز در شهر مهستان آغاز شده است. "
            "جزئیات پرونده هنوز برای کارآگاهان فاش نشده."
        ),
    ) -> CaseState:

        case_id = f"case-{uuid.uuid4().hex[:10]}"

        case = CaseState(
            case_id=case_id,
            title=title,
            city="مهستان",
            description=description,
        )

        self.cases[case_id] = case
        return case

    # ---------------------------------------------------------
    # دریافت پرونده
    # ---------------------------------------------------------

    def get_case(self, case_id: str) -> Optional[CaseState]:
        return self.cases.get(case_id)

    # ---------------------------------------------------------
    # اضافه کردن بازیکن
    # ---------------------------------------------------------

    def add_player(
        self,
        case_id: str,
        username: str,
        display_name: Optional[str] = None,
    ) -> dict:

        case = self.get_case(case_id)

        if case is None:
            return {
                "success": False,
                "error": "پرونده پیدا نشد.",
            }

        if username in case.players:
            return {
                "success": True,
                "message": "بازیکن قبلاً وارد پرونده شده.",
                "player": self.player_to_dict(case.players[username]),
            }

        if len(case.players) >= MAX_PLAYERS:
            return {
                "success": False,
                "error": "ظرفیت پرونده تکمیل شده است.",
            }

        player = Player(
            username=username,
            display_name=display_name or username,
            money=0,
        )

        case.players[username] = player
        case.unread_notifications[username] = 0

        return {
            "success": True,
            "message": "کارآگاه وارد پرونده شد.",
            "player": self.player_to_dict(player),
        }

    # ---------------------------------------------------------
    # حذف بازیکن
    # ---------------------------------------------------------

    def remove_player(self, case_id: str, username: str) -> dict:

        case = self.get_case(case_id)

        if case is None:
            return {
                "success": False,
                "error": "پرونده پیدا نشد.",
            }

        if username not in case.players:
            return {
                "success": False,
                "error": "بازیکن در پرونده نیست.",
            }

        del case.players[username]
        case.unread_notifications.pop(username, None)

        return {
            "success": True,
            "message": "کارآگاه از پرونده خارج شد.",
        }

    # ---------------------------------------------------------
    # شروع پرونده
    # ---------------------------------------------------------

    def start_case(self, case_id: str) -> dict:

        case = self.get_case(case_id)

        if case is None:
            return {
                "success": False,
                "error": "پرونده پیدا نشد.",
            }

        player_count = len(case.players)

        if player_count < MIN_PLAYERS:
            return {
                "success": False,
                "error": f"برای شروع حداقل {MIN_PLAYERS} کارآگاه لازم است.",
            }

        if case.started:
            return {
                "success": True,
                "message": "پرونده قبلاً شروع شده است.",
                "state": self.get_public_state(case_id),
            }

        case.started = True
        case.phase = "scenario"

        case.timeline_events.append(
            "پرونده ایجاد شد و کارآگاهان برای بررسی حادثه فراخوانده شدند."
        )

        for username in case.players:
            self.notify(
                case_id,
                username,
                "پرونده جدیدی برای شما ثبت شده است.",
            )

        return {
            "success": True,
            "message": "پرونده آغاز شد.",
            "state": self.get_public_state(case_id),
        }

    # ---------------------------------------------------------
    # ادامه دادن از صفحه سناریو
    # ---------------------------------------------------------

    def continue_from_scenario(self, case_id: str) -> dict:

        case = self.get_case(case_id)

        if case is None:
            return {
                "success": False,
                "error": "پرونده پیدا نشد.",
            }

        if not case.started:
            return {
                "success": False,
                "error": "پرونده هنوز شروع نشده است.",
            }

        case.phase = "city"

        return {
            "success": True,
            "message": "کارآگاهان وارد شهر مهستان شدند.",
            "state": self.get_public_state(case_id),
        }

    # ---------------------------------------------------------
    # جابه‌جایی در شهر
    # ---------------------------------------------------------

    def move_player(
        self,
        case_id: str,
        username: str,
        location: str,
    ) -> dict:

        case = self.get_case(case_id)

        if case is None:
            return {
                "success": False,
                "error": "پرونده پیدا نشد.",
            }

        player = case.players.get(username)

        if player is None:
            return {
                "success": False,
                "error": "بازیکن پیدا نشد.",
            }

        player.location = location

        if location not in case.visited_locations:
            case.visited_locations.append(location)

        return {
            "success": True,
            "message": f"{player.display_name} وارد {location} شد.",
            "location": location,
        }

    # ---------------------------------------------------------
    # ثبت مدرک
    # ---------------------------------------------------------

    def discover_evidence(
        self,
        case_id: str,
        username: str,
        evidence_id: str,
    ) -> dict:

        case = self.get_case(case_id)

        if case is None:
            return {
                "success": False,
                "error": "پرونده پیدا نشد.",
            }

        if username not in case.players:
            return {
                "success": False,
                "error": "بازیکن پیدا نشد.",
            }

        if evidence_id in case.discovered_evidence:
            return {
                "success": True,
                "message": "این مدرک قبلاً کشف شده است.",
            }

        case.discovered_evidence.append(evidence_id)

        case.timeline_events.append(
            f"مدرک جدید کشف شد: {evidence_id}"
        )

        self.reward_player(
            case_id,
            username,
            300_000,
        )

        for other_username in case.players:
            if other_username != username:
                self.notify(
                    case_id,
                    other_username,
                    f"{case.players[username].display_name} یک مدرک جدید پیدا کرد.",
                )

        return {
            "success": True,
            "message": "مدرک با موفقیت ثبت شد.",
            "reward": 300_000,
            "evidence_id": evidence_id,
        }

    # ---------------------------------------------------------
    # ثبت سرنخ
    # ---------------------------------------------------------

    def discover_clue(
        self,
        case_id: str,
        username: str,
        clue_id: str,
    ) -> dict:

        case = self.get_case(case_id)

        if case is None:
            return {
                "success": False,
                "error": "پرونده پیدا نشد.",
            }

        if username not in case.players:
            return {
                "success": False,
                "error": "بازیکن پیدا نشد.",
            }

        if clue_id in case.discovered_clues:
            return {
                "success": True,
                "message": "این سرنخ قبلاً کشف شده است.",
            }

        case.discovered_clues.append(clue_id)

        self.reward_player(
            case_id,
            username,
            300_000,
        )

        return {
            "success": True,
            "message": "سرنخ ثبت شد.",
            "reward": 300_000,
            "clue_id": clue_id,
        }

    # ---------------------------------------------------------
    # پول
    # ---------------------------------------------------------

    def reward_player(
        self,
        case_id: str,
        username: str,
        amount: int,
    ) -> bool:

        case = self.get_case(case_id)

        if case is None:
            return False

        player = case.players.get(username)

        if player is None:
            return False

        player.money += amount
        return True

    def deduct_money(
        self,
        case_id: str,
        username: str,
        amount: int,
    ) -> dict:

        case = self.get_case(case_id)

        if case is None:
            return {
                "success": False,
                "error": "پرونده پیدا نشد.",
            }

        player = case.players.get(username)

        if player is None:
            return {
                "success": False,
                "error": "بازیکن پیدا نشد.",
            }

        if amount <= 0:
            return {
                "success": False,
                "error": "مبلغ نامعتبر است.",
            }

        if player.money < amount:
            return {
                "success": False,
                "error": "موجودی کافی نیست.",
                "balance": player.money,
            }

        player.money -= amount

        return {
            "success": True,
            "amount": amount,
            "balance": player.money,
        }

    # ---------------------------------------------------------
    # نوتیفیکیشن
    # ---------------------------------------------------------

    def notify(
        self,
        case_id: str,
        username: str,
        message: str,
    ) -> bool:

        case = self.get_case(case_id)

        if case is None:
            return False

        if username not in case.players:
            return False

        case.unread_notifications[username] = (
            case.unread_notifications.get(username, 0) + 1
        )

        return True

    def clear_notifications(
        self,
        case_id: str,
        username: str,
    ) -> dict:

        case = self.get_case(case_id)

        if case is None:
            return {
                "success": False,
                "error": "پرونده پیدا نشد.",
            }

        if username not in case.players:
            return {
                "success": False,
                "error": "بازیکن پیدا نشد.",
            }

        case.unread_notifications[username] = 0

        return {
            "success": True,
            "unread": 0,
        }

    # ---------------------------------------------------------
    # گروگان‌گیری
    # ---------------------------------------------------------

    def set_hostage(
        self,
        case_id: str,
        username: str,
        hostage: bool = True,
    ) -> dict:

        case = self.get_case(case_id)

        if case is None:
            return {
                "success": False,
                "error": "پرونده پیدا نشد.",
            }

        player = case.players.get(username)

        if player is None:
            return {
                "success": False,
                "error": "بازیکن پیدا نشد.",
            }

        player.hostage = hostage
        player.can_chat = not hostage

        return {
            "success": True,
            "hostage": hostage,
            "can_chat": player.can_chat,
        }

    # ---------------------------------------------------------
    # وضعیت عمومی بازی
    # ---------------------------------------------------------

    def get_public_state(self, case_id: str) -> Optional[dict]:

        case = self.get_case(case_id)

        if case is None:
            return None

        return {
            "game_id": GAME_ID,
            "game_title": GAME_TITLE,
            "case_id": case.case_id,
            "title": case.title,
            "city": case.city,
            "description": case.description,
            "started": case.started,
            "phase": case.phase,
            "created_at": case.created_at,
            "player_count": len(case.players),
            "max_players": MAX_PLAYERS,
            "players": [
                self.player_to_public_dict(player)
                for player in case.players.values()
            ],
            "visited_locations": list(case.visited_locations),
            "evidence_count": len(case.discovered_evidence),
            "clue_count": len(case.discovered_clues),
            "timeline_count": len(case.timeline_events),
        }

    # ---------------------------------------------------------
    # وضعیت خصوصی بازیکن
    # ---------------------------------------------------------

    def get_player_state(
        self,
        case_id: str,
        username: str,
    ) -> Optional[dict]:

        case = self.get_case(case_id)

        if case is None:
            return None

        player = case.players.get(username)

        if player is None:
            return None

        state = self.get_public_state(case_id)

        if state is None:
            return None

        state["my_player"] = self.player_to_dict(player)
        state["unread_notifications"] = case.unread_notifications.get(
            username,
            0,
        )

        return state

    # ---------------------------------------------------------
    # تبدیل بازیکن به JSON-safe
    # ---------------------------------------------------------

    @staticmethod
    def player_to_public_dict(player: Player) -> dict:

        return {
            "username": player.username,
            "display_name": player.display_name,
            "location": player.location,
            "hostage": player.hostage,
            "can_chat": player.can_chat,
        }

    @staticmethod
    def player_to_dict(player: Player) -> dict:

        return {
            "username": player.username,
            "display_name": player.display_name,
            "joined_at": player.joined_at,
            "money": player.money,
            "location": player.location,
            "hostage": player.hostage,
            "can_chat": player.can_chat,
        }


# -------------------------------------------------------------
# نمونه موتور
# -------------------------------------------------------------

mehestan_engine = MehestanEngine()


def create_demo_case() -> CaseState:
    """
    برای تست محلی موتور.
    هنوز به سایت اصلی متصل نشده.
    """

    case = mehestan_engine.create_case()

    mehestan_engine.add_player(
        case.case_id,
        "mehdi",
        "کارآگاه مهدی",
    )

    mehestan_engine.add_player(
        case.case_id,
        "rastin",
        "کارآگاه راستین",
    )

    return case
