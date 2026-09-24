"""
Mehestan Mystery Case
Mobile System — سیستم موبایل کارآگاه

Features:
- Notifications
- Group messages
- Unread badge
- Private/system/hacker/NPC notifications
- Read/mark-as-read
- Shared team chat
- Player-specific notification state
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
import uuid


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Notification:
    notification_id: str
    player_id: str
    title: str
    message: str
    notification_type: str = "system"
    read: bool = False
    created_at: str = field(default_factory=now_iso)
    priority: str = "normal"
    metadata: Dict = field(default_factory=dict)

    def public_state(self) -> Dict:
        return {
            "id": self.notification_id,
            "title": self.title,
            "message": self.message,
            "type": self.notification_type,
            "read": self.read,
            "created_at": self.created_at,
            "priority": self.priority,
            "metadata": self.metadata,
        }


@dataclass
class GroupMessage:
    message_id: str
    sender_id: str
    sender_name: str
    message: str
    created_at: str = field(default_factory=now_iso)
    message_type: str = "chat"
    metadata: Dict = field(default_factory=dict)

    def public_state(self) -> Dict:
        return {
            "id": self.message_id,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "message": self.message,
            "created_at": self.created_at,
            "type": self.message_type,
            "metadata": self.metadata,
        }


class MobileSystem:
    """
    سیستم موبایل داخل پرونده مرموز.

    این کلاس فعلاً مستقل است و به Flask/SocketIO وابسته نیست.
    بعداً main.py می‌تواند API و Socket Eventهای آن را به این سیستم وصل کند.
    """

    MAX_MESSAGES = 200
    MAX_NOTIFICATIONS = 100

    def __init__(self):
        self.notifications: Dict[str, List[Notification]] = {}
        self.group_messages: List[GroupMessage] = []
        self.muted_players: set = set()

    # ---------------------------------------------------------
    # Player
    # ---------------------------------------------------------

    def register_player(self, player_id: str):
        if not player_id:
            return

        if player_id not in self.notifications:
            self.notifications[player_id] = []

    def remove_player(self, player_id: str):
        self.notifications.pop(player_id, None)
        self.muted_players.discard(player_id)

    # ---------------------------------------------------------
    # Notifications
    # ---------------------------------------------------------

    def send_notification(
        self,
        player_id: str,
        title: str,
        message: str,
        notification_type: str = "system",
        priority: str = "normal",
        metadata: Optional[Dict] = None,
    ) -> Optional[Notification]:

        if not player_id:
            return None

        self.register_player(player_id)

        notification = Notification(
            notification_id=f"notif_{uuid.uuid4().hex[:10]}",
            player_id=player_id,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            metadata=metadata or {},
        )

        self.notifications[player_id].append(notification)

        if len(self.notifications[player_id]) > self.MAX_NOTIFICATIONS:
            self.notifications[player_id] = (
                self.notifications[player_id][-self.MAX_NOTIFICATIONS:]
            )

        return notification

    def send_to_players(
        self,
        player_ids: List[str],
        title: str,
        message: str,
        notification_type: str = "system",
        priority: str = "normal",
        metadata: Optional[Dict] = None,
    ) -> List[Notification]:

        result = []

        for player_id in player_ids:
            notification = self.send_notification(
                player_id=player_id,
                title=title,
                message=message,
                notification_type=notification_type,
                priority=priority,
                metadata=metadata,
            )

            if notification:
                result.append(notification)

        return result

    def get_notifications(
        self,
        player_id: str,
        unread_only: bool = False,
        limit: int = 50,
    ) -> List[Notification]:

        self.register_player(player_id)

        items = self.notifications.get(player_id, [])

        if unread_only:
            items = [item for item in items if not item.read]

        return items[-limit:]

    def unread_count(self, player_id: str) -> int:
        self.register_player(player_id)

        return sum(
            1
            for item in self.notifications[player_id]
            if not item.read
        )

    def mark_read(
        self,
        player_id: str,
        notification_id: str,
    ) -> bool:

        self.register_player(player_id)

        for item in self.notifications[player_id]:
            if item.notification_id == notification_id:
                item.read = True
                return True

        return False

    def mark_all_read(self, player_id: str) -> int:
        self.register_player(player_id)

        count = 0

        for item in self.notifications[player_id]:
            if not item.read:
                item.read = True
                count += 1

        return count

    def clear_notifications(self, player_id: str):
        self.notifications[player_id] = []

    # ---------------------------------------------------------
    # Group Chat
    # ---------------------------------------------------------

    def send_group_message(
        self,
        sender_id: str,
        sender_name: str,
        message: str,
        message_type: str = "chat",
        metadata: Optional[Dict] = None,
        player_ids: Optional[List[str]] = None,
    ) -> Optional[GroupMessage]:

        message = (message or "").strip()

        if not sender_id or not message:
            return None

        # بازیکن‌هایی که در player_ids هستند می‌توانند دریافت‌کننده باشند.
        # اگر لیست داده نشود، فقط پیام گروه ثبت می‌شود.
        if player_ids:
            allowed = set(player_ids)

            if sender_id not in allowed:
                return None

        group_message = GroupMessage(
            message_id=f"msg_{uuid.uuid4().hex[:10]}",
            sender_id=sender_id,
            sender_name=sender_name or "کارآگاه",
            message=message,
            message_type=message_type,
            metadata=metadata or {},
        )

        self.group_messages.append(group_message)

        if len(self.group_messages) > self.MAX_MESSAGES:
            self.group_messages = self.group_messages[-self.MAX_MESSAGES:]

        return group_message

    def get_group_messages(
        self,
        limit: int = 100,
    ) -> List[GroupMessage]:

        return self.group_messages[-limit:]

    def clear_group_chat(self):
        self.group_messages = []

    # ---------------------------------------------------------
    # Convenience Notifications
    # ---------------------------------------------------------

    def notify_new_group_message(
        self,
        player_ids: List[str],
        sender_id: str,
        sender_name: str,
        message: str,
    ) -> List[Notification]:

        recipients = [
            player_id
            for player_id in player_ids
            if player_id != sender_id
        ]

        return self.send_to_players(
            player_ids=recipients,
            title=f"پیام جدید از {sender_name}",
            message=message,
            notification_type="group_message",
            priority="normal",
        )

    def notify_npc_message(
        self,
        player_id: str,
        npc_name: str,
        message: str,
    ) -> Optional[Notification]:

        return self.send_notification(
            player_id=player_id,
            title=f"پیام از {npc_name}",
            message=message,
            notification_type="npc",
            priority="normal",
        )

    def notify_anonymous_message(
        self,
        player_id: str,
        message: str,
    ) -> Optional[Notification]:

        return self.send_notification(
            player_id=player_id,
            title="پیام ناشناس",
            message=message,
            notification_type="anonymous",
            priority="high",
        )

    def notify_hacker(
        self,
        player_id: str,
        message: str,
    ) -> Optional[Notification]:

        return self.send_notification(
            player_id=player_id,
            title="هشدار امنیتی",
            message=message,
            notification_type="hacker",
            priority="critical",
        )

    def notify_story_event(
        self,
        player_id: str,
        title: str,
        message: str,
    ) -> Optional[Notification]:

        return self.send_notification(
            player_id=player_id,
            title=title,
            message=message,
            notification_type="story",
            priority="high",
        )

    def notify_hostage(
        self,
        player_id: str,
        hostage_name: str,
        location: str,
    ) -> Optional[Notification]:

        return self.send_notification(
            player_id=player_id,
            title="🔴 هشدار گروگان‌گیری",
            message=f"{hostage_name} گروگان گرفته شد — مکان: {location}",
            notification_type="hostage",
            priority="critical",
            metadata={
                "hostage_name": hostage_name,
                "location": location,
            },
        )

    # ---------------------------------------------------------
    # Mute
    # ---------------------------------------------------------

    def mute_player(self, player_id: str):
        self.muted_players.add(player_id)

    def unmute_player(self, player_id: str):
        self.muted_players.discard(player_id)

    def is_muted(self, player_id: str) -> bool:
        return player_id in self.muted_players

    # ---------------------------------------------------------
    # Public State
    # ---------------------------------------------------------

    def public_state(self, player_id: str) -> Dict:

        self.register_player(player_id)

        notifications = self.get_notifications(
            player_id=player_id,
            limit=50,
        )

        return {
            "phone": {
                "notifications": [
                    item.public_state()
                    for item in notifications
                ],
                "unread_count": self.unread_count(player_id),
            },
            "group_chat": [
                item.public_state()
                for item in self.get_group_messages()
            ],
            "muted": self.is_muted(player_id),
        }


# -------------------------------------------------------------
# Demo / Local Test
# -------------------------------------------------------------

def create_demo_mobile_system() -> MobileSystem:
    mobile = MobileSystem()

    players = [
        "mehdi",
        "rastin",
        "amirali",
        "mahna",
        "fatemeh",
    ]

    for player_id in players:
        mobile.register_player(player_id)

    mobile.send_notification(
        player_id="mehdi",
        title="پرونده جدید",
        message="پرونده شهر مهستان آماده بررسی است.",
        notification_type="story",
        priority="high",
    )

    mobile.send_notification(
        player_id="mahna",
        title="پیام ناشناس",
        message="فکر می‌کنی واقعاً می‌دونی چه اتفاقی افتاده؟",
        notification_type="anonymous",
        priority="high",
    )

    mobile.send_group_message(
        sender_id="mehdi",
        sender_name="کارآگاه مهدی",
        message="من میرم سمت خانه قربانی.",
    )

    mobile.send_group_message(
        sender_id="rastin",
        sender_name="کارآگاه راستین",
        message="من بیمارستان رو بررسی می‌کنم.",
    )

    return mobile


if __name__ == "__main__":
    demo = create_demo_mobile_system()

    print("=== Mehestan Mobile System ===")
    print("Unread:", demo.unread_count("mehdi"))
    print("Messages:", len(demo.get_group_messages()))
    print("State:", demo.public_state("mehdi"))
