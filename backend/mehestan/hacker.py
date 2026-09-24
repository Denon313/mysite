"""
Mehestan Mystery Case
Hacker System — سیستم هکر
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
import uuid
import random


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class HackerEvent:
    event_id: str
    event_type: str
    title: str
    message: str
    target: Optional[str] = None
    severity: str = "normal"
    created_at: str = field(default_factory=now_iso)
    resolved: bool = False
    metadata: Dict = field(default_factory=dict)

    def public_state(self) -> Dict:
        return {
            "id": self.event_id,
            "type": self.event_type,
            "title": self.title,
            "message": self.message,
            "target": self.target,
            "severity": self.severity,
            "created_at": self.created_at,
            "resolved": self.resolved,
            "metadata": self.metadata,
        }


@dataclass
class HackerState:
    active: bool = False
    threat_level: int = 0
    identity_system_compromised: bool = False
    cameras_compromised: bool = False
    anonymous_messages_enabled: bool = False
    kidnapping_enabled: bool = False
    trace_progress: int = 0
    discovered: bool = False
    current_phase: str = "silent"

    def public_state(self) -> Dict:
        return {
            "active": self.active,
            "threat_level": self.threat_level,
            "identity_system_compromised": self.identity_system_compromised,
            "cameras_compromised": self.cameras_compromised,
            "anonymous_messages_enabled": self.anonymous_messages_enabled,
            "kidnapping_enabled": self.kidnapping_enabled,
            "trace_progress": self.trace_progress,
            "discovered": self.discovered,
            "current_phase": self.current_phase,
        }


class HackerSystem:
    """
    هکر یک خط داستانی مستقل در پرونده است.

    هکر لزوماً قاتل نیست.
    """

    MAX_THREAT = 100
    MAX_TRACE = 100

    def __init__(self, seed: Optional[int] = None):
        self.state = HackerState()
        self.events: List[HackerEvent] = []
        self.anonymous_messages: List[Dict] = []
        self.security_failures: List[Dict] = []
        self.player_targets: Dict[str, int] = {}

        self.random = random.Random(seed)

    # ---------------------------------------------------------
    # Activation / Story
    # ---------------------------------------------------------

    def activate(self, phase: str = "early") -> HackerState:

        self.state.active = True
        self.state.current_phase = phase

        if phase == "early":
            self.state.threat_level = max(
                self.state.threat_level,
                10,
            )

        self._event(
            event_type="hacker_activated",
            title="فعالیت ناشناس",
            message=(
                "یک فعالیت غیرعادی در شبکه مهستان شناسایی شد."
            ),
            severity="normal",
        )

        return self.state

    def advance_phase(self, phase: str):

        self.state.current_phase = phase

        phases = {
            "silent": 0,
            "early": 10,
            "interference": 30,
            "attack": 60,
            "major": 80,
            "final": 100,
        }

        self.state.threat_level = max(
            self.state.threat_level,
            phases.get(phase, 0),
        )

        if phase in {
            "interference",
            "attack",
            "major",
            "final",
        }:
            self.state.active = True

    # ---------------------------------------------------------
    # Security Failures
    # ---------------------------------------------------------

    def trigger_failed_login(
        self,
        target: str = "identity_system",
    ) -> HackerEvent:

        failure = {
            "failure_id": f"fail_{uuid.uuid4().hex[:10]}",
            "target": target,
            "created_at": now_iso(),
            "code": "CY-047",
        }

        self.security_failures.append(failure)

        self.state.active = True
        self.state.threat_level = min(
            self.MAX_THREAT,
            self.state.threat_level + 8,
        )

        return self._event(
            event_type="failed_login",
            title="ورود ناموفق",
            message="ورود ناموفق به یک بخش محافظت‌شده ثبت شد.",
            target=target,
            severity="warning",
            metadata={
                "error_code": "CY-047",
                "failure_id": failure["failure_id"],
            },
        )

    def trigger_system_glitch(
        self,
        target: str,
        duration_seconds: int = 8,
    ) -> HackerEvent:

        self.state.active = True
        self.state.threat_level = min(
            self.MAX_THREAT,
            self.state.threat_level + 5,
        )

        return self._event(
            event_type="system_glitch",
            title="اختلال موقت سیستم",
            message=(
                f"سیستم برای حدود {duration_seconds} ثانیه "
                "پاسخ عادی نمی‌دهد."
            ),
            target=target,
            severity="warning",
            metadata={
                "duration_seconds": duration_seconds,
            },
        )

    # ---------------------------------------------------------
    # Identity System
    # ---------------------------------------------------------

    def compromise_identity_system(
        self,
        duration_seconds: int = 180,
    ) -> HackerEvent:

        self.state.identity_system_compromised = True
        self.state.active = True
        self.state.current_phase = "attack"

        self.state.threat_level = min(
            self.MAX_THREAT,
            self.state.threat_level + 20,
        )

        return self._event(
            event_type="identity_compromise",
            title="حمله به سیستم اعتبارسنجی",
            message=(
                "سیستم اعتبارسنجی شهر مورد حمله قرار گرفته است."
            ),
            target="identity_system",
            severity="critical",
            metadata={
                "duration_seconds": duration_seconds,
            },
        )

    def restore_identity_system(self) -> bool:

        self.state.identity_system_compromised = False

        self._event(
            event_type="identity_restored",
            title="بازیابی سیستم",
            message="سیستم اعتبارسنجی دوباره در دسترس قرار گرفت.",
            target="identity_system",
            severity="normal",
        )

        return True

    # ---------------------------------------------------------
    # Cameras
    # ---------------------------------------------------------

    def compromise_camera(
        self,
        camera_id: str,
        duration_seconds: int = 60,
    ) -> HackerEvent:

        self.state.cameras_compromised = True
        self.state.active = True

        self.state.threat_level = min(
            self.MAX_THREAT,
            self.state.threat_level + 10,
        )

        return self._event(
            event_type="camera_compromise",
            title="اختلال دوربین",
            message=(
                "یک دوربین مداربسته از دسترس خارج شد."
            ),
            target=camera_id,
            severity="high",
            metadata={
                "duration_seconds": duration_seconds,
            },
        )

    def restore_cameras(self) -> bool:

        self.state.cameras_compromised = False

        self._event(
            event_type="cameras_restored",
            title="بازگشت دوربین‌ها",
            message="ارتباط دوربین‌ها دوباره برقرار شد.",
            severity="normal",
        )

        return True

    # ---------------------------------------------------------
    # Anonymous Messages
    # ---------------------------------------------------------

    def enable_anonymous_messages(self):

        self.state.anonymous_messages_enabled = True

    def disable_anonymous_messages(self):

        self.state.anonymous_messages_enabled = False

    def send_anonymous_message(
        self,
        target_player_id: str,
        message: str,
        title: str = "پیام ناشناس",
    ) -> Optional[Dict]:

        if not self.state.anonymous_messages_enabled:
            return None

        message = (message or "").strip()

        if not message:
            return None

        item = {
            "message_id": f"anon_{uuid.uuid4().hex[:10]}",
            "target_player_id": target_player_id,
            "title": title,
            "message": message,
            "created_at": now_iso(),
        }

        self.anonymous_messages.append(item)

        self.player_targets[target_player_id] = (
            self.player_targets.get(target_player_id, 0) + 1
        )

        self._event(
            event_type="anonymous_message",
            title=title,
            message=message,
            target=target_player_id,
            severity="high",
        )

        return item

    def get_messages_for_player(
        self,
        player_id: str,
    ) -> List[Dict]:

        return [
            item
            for item in self.anonymous_messages
            if item["target_player_id"] == player_id
        ]

    # ---------------------------------------------------------
    # Kidnapping
    # ---------------------------------------------------------

    def enable_kidnapping(self):

        self.state.kidnapping_enabled = True
        self.state.active = True

    def disable_kidnapping(self):

        self.state.kidnapping_enabled = False

    def can_trigger_kidnapping(self) -> bool:

        return (
            self.state.active
            and self.state.kidnapping_enabled
            and self.state.threat_level >= 60
        )

    def select_kidnap_target(
        self,
        player_ids: List[str],
        excluded_players: Optional[List[str]] = None,
    ) -> Optional[str]:

        if not self.can_trigger_kidnapping():
            return None

        excluded = set(excluded_players or [])

        candidates = [
            player_id
            for player_id in player_ids
            if player_id not in excluded
        ]

        if not candidates:
            return None

        return self.random.choice(candidates)

    # ---------------------------------------------------------
    # Trace Hacker
    # ---------------------------------------------------------

    def add_trace_progress(
        self,
        amount: int,
    ) -> int:

        amount = max(0, amount)

        self.state.trace_progress = min(
            self.MAX_TRACE,
            self.state.trace_progress + amount,
        )

        if self.state.trace_progress >= 100:
            self.state.discovered = True
            self.state.current_phase = "final"

        return self.state.trace_progress

    def trace_with_clue(
        self,
        clue_type: str,
    ) -> int:

        rewards = {
            "digital": 20,
            "phone": 15,
            "camera": 15,
            "identity": 20,
            "financial": 10,
            "anonymous_message": 12,
            "timeline": 8,
        }

        amount = rewards.get(clue_type, 5)

        return self.add_trace_progress(amount)

    # ---------------------------------------------------------
    # Threat
    # ---------------------------------------------------------

    def increase_threat(
        self,
        amount: int,
    ) -> int:

        self.state.threat_level = min(
            self.MAX_THREAT,
            self.state.threat_level + max(0, amount),
        )

        return self.state.threat_level

    def decrease_threat(
        self,
        amount: int,
    ) -> int:

        self.state.threat_level = max(
            0,
            self.state.threat_level - max(0, amount),
        )

        return self.state.threat_level

    # ---------------------------------------------------------
    # Event Helper
    # ---------------------------------------------------------

    def _event(
        self,
        event_type: str,
        title: str,
        message: str,
        target: Optional[str] = None,
        severity: str = "normal",
        metadata: Optional[Dict] = None,
    ) -> HackerEvent:

        event = HackerEvent(
            event_id=f"hacker_{uuid.uuid4().hex[:10]}",
            event_type=event_type,
            title=title,
            message=message,
            target=target,
            severity=severity,
            metadata=metadata or {},
        )

        self.events.append(event)

        if len(self.events) > 300:
            self.events = self.events[-300:]

        return event

    def get_events(
        self,
        limit: int = 50,
    ) -> List[HackerEvent]:

        return self.events[-limit:]

    # ---------------------------------------------------------
    # Public State
    # ---------------------------------------------------------

    def public_state(self) -> Dict:

        return {
            "state": self.state.public_state(),
            "recent_events": [
                event.public_state()
                for event in self.get_events(30)
            ],
        }


def create_demo_hacker_system() -> HackerSystem:

    hacker = HackerSystem(seed=313)

    hacker.activate("early")

    hacker.trigger_failed_login(
        "identity_system",
    )

    hacker.enable_anonymous_messages()

    hacker.send_anonymous_message(
        "mehdi",
        "بعضی چیزها رو بهتره دنبال نکنی.",
    )

    return hacker


if __name__ == "__main__":

    hacker = create_demo_hacker_system()

    print("=== Mehestan Hacker System ===")
    print("Active:", hacker.state.active)
    print("Threat:", hacker.state.threat_level)
    print("Trace:", hacker.state.trace_progress)
    print("Events:", len(hacker.events))
