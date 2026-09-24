"""
Mehestan Mystery Case
Hostage System — سیستم گروگان‌گیری
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import uuid
import random


TEHRAN_OFFSET = timezone(timedelta(hours=3, minutes=30))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_timestamp() -> float:
    return datetime.now(timezone.utc).timestamp()


@dataclass
class HostageEvent:
    event_id: str
    hostage_player_id: str
    hostage_name: str
    location_id: str
    location_name: str
    status: str = "active"

    started_at: str = field(default_factory=now_iso)

    ransom_amount: int = 2_000_000
    ransom_deadline_seconds: int = 90
    total_event_seconds: int = 900

    ransom_paid: int = 0
    backup_requested: bool = False

    survival_status: str = "unknown"
    chat_locked: bool = True

    created_at: str = field(default_factory=now_iso)

    clues: List[Dict] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def remaining_event_seconds(self) -> int:
        elapsed = int(now_timestamp() - self._started_timestamp())

        return max(
            0,
            self.total_event_seconds - elapsed,
        )

    def remaining_ransom_seconds(self) -> int:
        elapsed = int(now_timestamp() - self._started_timestamp())

        return max(
            0,
            self.ransom_deadline_seconds - elapsed,
        )

    def _started_timestamp(self) -> float:
        try:
            return datetime.fromisoformat(
                self.started_at.replace("Z", "+00:00")
            ).timestamp()
        except Exception:
            return now_timestamp()

    def public_state(self) -> Dict:
        return {
            "id": self.event_id,
            "hostage_player_id": self.hostage_player_id,
            "hostage_name": self.hostage_name,
            "location_id": self.location_id,
            "location_name": self.location_name,
            "status": self.status,
            "started_at": self.started_at,
            "ransom_amount": self.ransom_amount,
            "ransom_paid": self.ransom_paid,
            "ransom_remaining": max(
                0,
                self.ransom_amount - self.ransom_paid,
            ),
            "ransom_deadline_seconds": self.ransom_deadline_seconds,
            "ransom_remaining_seconds": self.remaining_ransom_seconds(),
            "total_event_seconds": self.total_event_seconds,
            "event_remaining_seconds": self.remaining_event_seconds(),
            "backup_requested": self.backup_requested,
            "survival_status": self.survival_status,
            "chat_locked": self.chat_locked,
            "clues": self.clues,
            "metadata": self.metadata,
        }


class HostageSystem:
    """
    مدیریت گروگان‌گیری در پرونده مرموز.

    قوانین:
    - حداکثر ۳ رویداد در هر پرونده
    - هر بازیکن حداکثر ۲ بار
    - مدت کلی رویداد: ۱۵ دقیقه
    - مهلت باج: ۹۰ ثانیه
    - پرداخت باج از موجودی شخصی بازیکنان
    - گروگان تا پایان رویداد امکان ارسال پیام ندارد
    """

    MAX_HOSTAGE_EVENTS = 3
    MAX_TIMES_PER_PLAYER = 2

    EVENT_SECONDS = 15 * 60
    RANSOM_SECONDS = 90

    DEFAULT_RANSOM = 2_000_000

    def __init__(self, seed: Optional[int] = None):

        self.events: Dict[str, HostageEvent] = {}

        self.player_history: Dict[str, int] = {}

        self.current_event_id: Optional[str] = None

        self.money: Dict[str, int] = {}

        self.random = random.Random(seed)

    # ---------------------------------------------------------
    # Player Economy
    # ---------------------------------------------------------

    def register_player(
        self,
        player_id: str,
        starting_money: int = 0,
    ):

        if player_id not in self.money:
            self.money[player_id] = max(
                0,
                starting_money,
            )

        if player_id not in self.player_history:
            self.player_history[player_id] = 0

    def set_money(
        self,
        player_id: str,
        amount: int,
    ) -> int:

        self.register_player(player_id)

        self.money[player_id] = max(
            0,
            amount,
        )

        return self.money[player_id]

    def get_money(
        self,
        player_id: str,
    ) -> int:

        self.register_player(player_id)

        return self.money[player_id]

    # ---------------------------------------------------------
    # Eligibility
    # ---------------------------------------------------------

    def can_start_event(self) -> bool:

        completed_or_started = len(self.events)

        return (
            self.current_event_id is None
            and completed_or_started < self.MAX_HOSTAGE_EVENTS
        )

    def can_be_hostage(
        self,
        player_id: str,
    ) -> bool:

        self.register_player(player_id)

        return (
            self.player_history[player_id]
            < self.MAX_TIMES_PER_PLAYER
        )

    # ---------------------------------------------------------
    # Target Selection
    # ---------------------------------------------------------

    def select_target(
        self,
        player_ids: List[str],
        excluded_players: Optional[List[str]] = None,
    ) -> Optional[str]:

        excluded = set(excluded_players or [])

        candidates = []

        for player_id in player_ids:

            if player_id in excluded:
                continue

            if self.can_be_hostage(player_id):
                candidates.append(player_id)

        if not candidates:
            return None

        return self.random.choice(candidates)

    # ---------------------------------------------------------
    # Start Hostage Event
    # ---------------------------------------------------------

    def start_event(
        self,
        hostage_player_id: str,
        hostage_name: str,
        location_id: str,
        location_name: str,
        ransom_amount: int = DEFAULT_RANSOM,
        metadata: Optional[Dict] = None,
    ) -> Optional[HostageEvent]:

        if not self.can_start_event():
            return None

        if not self.can_be_hostage(
            hostage_player_id
        ):
            return None

        self.register_player(
            hostage_player_id
        )

        ransom_amount = max(
            0,
            ransom_amount,
        )

        event = HostageEvent(
            event_id=f"hostage_{uuid.uuid4().hex[:10]}",
            hostage_player_id=hostage_player_id,
            hostage_name=hostage_name,
            location_id=location_id,
            location_name=location_name,
            ransom_amount=ransom_amount,
            ransom_deadline_seconds=self.RANSOM_SECONDS,
            total_event_seconds=self.EVENT_SECONDS,
            metadata=metadata or {},
        )

        self.events[event.event_id] = event

        self.current_event_id = event.event_id

        self.player_history[hostage_player_id] += 1

        return event

    # ---------------------------------------------------------
    # Current Event
    # ---------------------------------------------------------

    def get_current_event(
        self,
    ) -> Optional[HostageEvent]:

        if not self.current_event_id:
            return None

        return self.events.get(
            self.current_event_id
        )

    # ---------------------------------------------------------
    # Ransom
    # ---------------------------------------------------------

    def contribute_ransom(
        self,
        event_id: str,
        player_id: str,
        amount: int,
    ) -> Dict:

        event = self.events.get(event_id)

        if not event:
            return {
                "success": False,
                "reason": "event_not_found",
            }

        if event.status != "active":
            return {
                "success": False,
                "reason": "event_not_active",
            }

        if player_id == event.hostage_player_id:
            return {
                "success": False,
                "reason": "hostage_cannot_pay",
            }

        if event.remaining_ransom_seconds() <= 0:
            return {
                "success": False,
                "reason": "ransom_deadline_expired",
            }

        self.register_player(player_id)

        amount = max(
            0,
            int(amount),
        )

        if amount <= 0:
            return {
                "success": False,
                "reason": "invalid_amount",
            }

        balance = self.money[player_id]

        if balance <= 0:
            return {
                "success": False,
                "reason": "insufficient_balance",
            }

        actual_amount = min(
            amount,
            balance,
            max(
                0,
                event.ransom_amount - event.ransom_paid,
            ),
        )

        if actual_amount <= 0:
            return {
                "success": False,
                "reason": "ransom_already_complete",
            }

        self.money[player_id] -= actual_amount

        event.ransom_paid += actual_amount

        if event.ransom_paid >= event.ransom_amount:

            self._release_hostage(
                event,
                reason="ransom_paid",
            )

        return {
            "success": True,
            "player_id": player_id,
            "paid": actual_amount,
            "player_balance": self.money[player_id],
            "ransom_paid": event.ransom_paid,
            "ransom_remaining": max(
                0,
                event.ransom_amount - event.ransom_paid,
            ),
            "event_status": event.status,
        }

    # ---------------------------------------------------------
    # Backup
    # ---------------------------------------------------------

    def request_backup(
        self,
        event_id: str,
        player_id: str,
    ) -> Dict:

        event = self.events.get(event_id)

        if not event:
            return {
                "success": False,
                "reason": "event_not_found",
            }

        if event.status != "active":
            return {
                "success": False,
                "reason": "event_not_active",
            }

        if player_id == event.hostage_player_id:
            return {
                "success": False,
                "reason": "hostage_cannot_request_backup",
            }

        if event.backup_requested:
            return {
                "success": False,
                "reason": "backup_already_requested",
            }

        event.backup_requested = True

        event.clues.append(
            {
                "type": "backup_request",
                "title": "ردی از نیروی کمکی",
                "description": (
                    "درخواست کمک ثبت شد، اما زمان رسیدن "
                    "نیروی کمکی تضمین‌شده نیست."
                ),
                "created_at": now_iso(),
            }
        )

        return {
            "success": True,
            "backup_requested": True,
        }

    # ---------------------------------------------------------
    # Clues
    # ---------------------------------------------------------

    def add_clue(
        self,
        event_id: str,
        title: str,
        description: str,
        clue_type: str = "general",
        metadata: Optional[Dict] = None,
    ) -> Optional[Dict]:

        event = self.events.get(event_id)

        if not event:
            return None

        clue = {
            "clue_id": f"hclue_{uuid.uuid4().hex[:10]}",
            "type": clue_type,
            "title": title,
            "description": description,
            "created_at": now_iso(),
            "metadata": metadata or {},
        }

        event.clues.append(clue)

        return clue

    def get_clues(
        self,
        event_id: str,
    ) -> List[Dict]:

        event = self.events.get(event_id)

        if not event:
            return []

        return event.clues

    # ---------------------------------------------------------
    # Resolution
    # ---------------------------------------------------------

    def resolve_expired_event(
        self,
        event_id: str,
    ) -> Optional[str]:

        event = self.events.get(event_id)

        if not event:
            return None

        if event.status != "active":
            return event.status

        if event.ransom_paid >= event.ransom_amount:
            self._release_hostage(
                event,
                reason="ransom_paid",
            )

            return event.status

        if event.remaining_event_seconds() <= 0:

            self._resolve_failure(
                event,
                reason="event_timeout",
            )

            return event.status

        if event.remaining_ransom_seconds() <= 0:
            self._handle_ransom_failure(event)

        return event.status

    def _handle_ransom_failure(
        self,
        event: HostageEvent,
    ):

        if event.backup_requested:

            roll = self.random.random()

            if roll < 0.65:

                self._release_hostage(
                    event,
                    reason="backup_success",
                )

            else:

                self._resolve_failure(
                    event,
                    reason="backup_failed",
                )

        else:

            # اگر باج پرداخت نشود و کمک هم درخواست نشده باشد،
            # رویداد به وضعیت خطرناک می‌رود ولی هنوز تا پایان
            # ۱۵ دقیقه فرصت برای تصمیم‌گیری باقی می‌ماند.

            event.status = "critical"

            event.clues.append(
                {
                    "type": "ransom_expired",
                    "title": "پایان مهلت باج",
                    "description": (
                        "مهلت پرداخت باج تمام شده است."
                    ),
                    "created_at": now_iso(),
                }
            )

    def resolve_backup(
        self,
        event_id: str,
        success: bool,
    ) -> Optional[str]:

        event = self.events.get(event_id)

        if not event:
            return None

        if event.status not in {
            "active",
            "critical",
        }:
            return event.status

        if success:

            self._release_hostage(
                event,
                reason="backup_success",
            )

        else:

            self._resolve_failure(
                event,
                reason="backup_failed",
            )

        return event.status

    # ---------------------------------------------------------
    # Hostage Survival
    # ---------------------------------------------------------

    def force_survival(
        self,
        event_id: str,
    ) -> bool:

        event = self.events.get(event_id)

        if not event:
            return False

        event.survival_status = "alive"

        return True

    def force_death(
        self,
        event_id: str,
    ) -> bool:

        event = self.events.get(event_id)

        if not event:
            return False

        event.survival_status = "dead"
        event.status = "failed"
        event.chat_locked = False

        if self.current_event_id == event_id:
            self.current_event_id = None

        return True

    def _release_hostage(
        self,
        event: HostageEvent,
        reason: str,
    ):

        event.status = "rescued"
        event.survival_status = "alive"
        event.chat_locked = False

        event.clues.append(
            {
                "type": "resolution",
                "title": "گروگان آزاد شد",
                "description": (
                    "گروگان با موفقیت نجات پیدا کرد."
                ),
                "reason": reason,
                "created_at": now_iso(),
            }
        )

        if self.current_event_id == event.event_id:
            self.current_event_id = None

    def _resolve_failure(
        self,
        event: HostageEvent,
        reason: str,
    ):

        event.status = "failed"

        # نتیجه نهایی بقا وابسته به نوع شکست است.
        if reason == "backup_failed":
            event.survival_status = "unknown"
        else:
            event.survival_status = "unknown"

        event.chat_locked = False

        event.clues.append(
            {
                "type": "resolution",
                "title": "سرنوشت نامعلوم",
                "description": (
                    "سرنوشت گروگان هنوز به‌طور کامل مشخص نیست."
                ),
                "reason": reason,
                "created_at": now_iso(),
            }
        )

        if self.current_event_id == event.event_id:
            self.current_event_id = None

    # ---------------------------------------------------------
    # Chat Lock
    # ---------------------------------------------------------

    def can_send_chat(
        self,
        player_id: str,
    ) -> bool:

        event = self.get_current_event()

        if not event:
            return True

        if event.status not in {
            "active",
            "critical",
        }:
            return True

        if player_id == event.hostage_player_id:
            return False

        return True

    def can_read_chat(
        self,
        player_id: str,
    ) -> bool:

        # گروگان می‌تواند پیام‌های قبلی را بخواند.
        return True

    # ---------------------------------------------------------
    # History
    # ---------------------------------------------------------

    def get_player_history(
        self,
        player_id: str,
    ) -> int:

        return self.player_history.get(
            player_id,
            0,
        )

    def get_events(
        self,
        limit: int = 50,
    ) -> List[HostageEvent]:

        return list(
            self.events.values()
        )[-limit:]

    # ---------------------------------------------------------
    # Public State
    # ---------------------------------------------------------

    def public_state(
        self,
        player_id: Optional[str] = None,
    ) -> Dict:

        current = self.get_current_event()

        state = {
            "active": current is not None,
            "current_event": None,
            "total_events": len(self.events),
            "max_events": self.MAX_HOSTAGE_EVENTS,
        }

        if current:

            event_state = current.public_state()

            if player_id != current.hostage_player_id:

                state["current_event"] = event_state

            else:

                # گروگان اطلاعات حساس تیم را نمی‌بیند،
                # ولی خودش می‌داند کجاست.
                state["current_event"] = {
                    "id": current.event_id,
                    "hostage_player_id": current.hostage_player_id,
                    "hostage_name": current.hostage_name,
                    "location_id": current.location_id,
                    "location_name": current.location_name,
                    "status": current.status,
                    "ransom_deadline_seconds": (
                        current.ransom_deadline_seconds
                    ),
                    "ransom_remaining_seconds": (
                        current.remaining_ransom_seconds()
                    ),
                    "event_remaining_seconds": (
                        current.remaining_event_seconds()
                    ),
                    "backup_requested": current.backup_requested,
                    "survival_status": current.survival_status,
                    "chat_locked": True,
                    "clues": current.clues,
                }

        return state


def create_demo_hostage_system() -> HostageSystem:

    hostage = HostageSystem(seed=313)

    players = [
        ("mehdi", 1_000_000),
        ("rastin", 800_000),
        ("amirali", 700_000),
        ("mahna", 900_000),
        ("fatemeh", 1_200_000),
    ]

    for player_id, money in players:
        hostage.register_player(
            player_id,
            money,
        )

    hostage.start_event(
        hostage_player_id="mahna",
        hostage_name="کارآگاه مهنا",
        location_id="central_hospital",
        location_name="بیمارستان مرکزی",
        ransom_amount=2_000_000,
    )

    return hostage


if __name__ == "__main__":

    system = create_demo_hostage_system()

    print("=== Mehestan Hostage System ===")

    event = system.get_current_event()

    if event:
        print("Hostage:", event.hostage_name)
        print("Location:", event.location_name)
        print("Ransom:", event.ransom_amount)
        print("Ransom remaining:", event.remaining_ransom_seconds())
        print("Chat locked:", event.chat_locked)
