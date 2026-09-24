"""
Mehestan Mystery Case
Multiplayer System — سیستم چندنفره
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
import uuid


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class PlayerPresence:
    player_id: str
    name: str
    title: str = "کارآگاه"

    status: str = "offline"
    location_id: Optional[str] = None
    location_name: Optional[str] = None

    is_hostage: bool = False
    can_send_chat: bool = True

    last_seen: str = field(default_factory=now_iso)

    metadata: Dict = field(default_factory=dict)

    def public_state(self) -> Dict:
        return {
            "player_id": self.player_id,
            "name": self.name,
            "title": self.title,
            "status": self.status,
            "location_id": self.location_id,
            "location_name": self.location_name,
            "is_hostage": self.is_hostage,
            "can_send_chat": self.can_send_chat,
            "last_seen": self.last_seen,
            "metadata": self.metadata,
        }


@dataclass
class SharedDiscovery:
    discovery_id: str
    sender_id: str
    sender_name: str

    discovery_type: str
    reference_id: str

    title: str
    description: str

    shared_at: str = field(default_factory=now_iso)

    metadata: Dict = field(default_factory=dict)

    def public_state(self) -> Dict:
        return {
            "id": self.discovery_id,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "type": self.discovery_type,
            "reference_id": self.reference_id,
            "title": self.title,
            "description": self.description,
            "shared_at": self.shared_at,
            "metadata": self.metadata,
        }


class MultiplayerSystem:
    """
    مدیریت بازیکنان و اطلاعات مشترک پرونده.

    حداکثر ۵ بازیکن.
    """

    MAX_PLAYERS = 5

    VALID_STATUS = {
        "online",
        "weak",
        "offline",
        "hostage",
    }

    def __init__(self):

        self.players: Dict[str, PlayerPresence] = {}

        self.discoveries: List[SharedDiscovery] = []

        self.team_events: List[Dict] = []

        self.location_history: Dict[str, List[Dict]] = {}

    # ---------------------------------------------------------
    # Players
    # ---------------------------------------------------------

    def add_player(
        self,
        player_id: str,
        name: str,
        title: str = "کارآگاه",
    ) -> Optional[PlayerPresence]:

        if not player_id:
            return None

        if player_id in self.players:
            return self.players[player_id]

        if len(self.players) >= self.MAX_PLAYERS:
            return None

        player = PlayerPresence(
            player_id=player_id,
            name=name,
            title=title,
            status="online",
        )

        self.players[player_id] = player

        self.location_history[player_id] = []

        self._team_event(
            "player_joined",
            {
                "player_id": player_id,
                "name": name,
            },
        )

        return player

    def remove_player(
        self,
        player_id: str,
    ) -> bool:

        if player_id not in self.players:
            return False

        player = self.players[player_id]

        player.status = "offline"
        player.last_seen = now_iso()

        self._team_event(
            "player_left",
            {
                "player_id": player_id,
                "name": player.name,
            },
        )

        return True

    def get_player(
        self,
        player_id: str,
    ) -> Optional[PlayerPresence]:

        return self.players.get(player_id)

    def list_players(self) -> List[PlayerPresence]:

        return list(self.players.values())

    # ---------------------------------------------------------
    # Presence
    # ---------------------------------------------------------

    def set_status(
        self,
        player_id: str,
        status: str,
    ) -> bool:

        if status not in self.VALID_STATUS:
            return False

        player = self.get_player(player_id)

        if not player:
            return False

        player.status = status
        player.last_seen = now_iso()

        if status == "hostage":
            player.is_hostage = True
            player.can_send_chat = False

        elif status in {
            "online",
            "weak",
            "offline",
        }:
            if status != "offline":
                player.is_hostage = False

            player.can_send_chat = not player.is_hostage

        self._team_event(
            "player_status_changed",
            {
                "player_id": player_id,
                "status": status,
            },
        )

        return True

    def mark_online(
        self,
        player_id: str,
    ) -> bool:

        return self.set_status(
            player_id,
            "online",
        )

    def mark_weak(
        self,
        player_id: str,
    ) -> bool:

        return self.set_status(
            player_id,
            "weak",
        )

    def mark_offline(
        self,
        player_id: str,
    ) -> bool:

        return self.set_status(
            player_id,
            "offline",
        )

    # ---------------------------------------------------------
    # Location
    # ---------------------------------------------------------

    def update_location(
        self,
        player_id: str,
        location_id: str,
        location_name: str,
    ) -> bool:

        player = self.get_player(player_id)

        if not player:
            return False

        previous_location = player.location_id

        player.location_id = location_id
        player.location_name = location_name
        player.last_seen = now_iso()

        history_item = {
            "location_id": location_id,
            "location_name": location_name,
            "previous_location_id": previous_location,
            "timestamp": now_iso(),
        }

        self.location_history.setdefault(
            player_id,
            [],
        ).append(history_item)

        if len(self.location_history[player_id]) > 100:
            self.location_history[player_id] = (
                self.location_history[player_id][-100:]
            )

        self._team_event(
            "player_moved",
            {
                "player_id": player_id,
                "location_id": location_id,
                "location_name": location_name,
            },
        )

        return True

    def get_location_history(
        self,
        player_id: str,
        limit: int = 50,
    ) -> List[Dict]:

        return self.location_history.get(
            player_id,
            [],
        )[-limit:]

    def players_at_location(
        self,
        location_id: str,
    ) -> List[PlayerPresence]:

        return [
            player
            for player in self.players.values()
            if player.location_id == location_id
        ]

    # ---------------------------------------------------------
    # Hostage
    # ---------------------------------------------------------

    def set_hostage(
        self,
        player_id: str,
        hostage: bool,
    ) -> bool:

        player = self.get_player(player_id)

        if not player:
            return False

        player.is_hostage = hostage

        if hostage:
            player.status = "hostage"
            player.can_send_chat = False

        else:
            if player.status == "hostage":
                player.status = "online"

            player.can_send_chat = True

        player.last_seen = now_iso()

        self._team_event(
            "hostage_status_changed",
            {
                "player_id": player_id,
                "is_hostage": hostage,
            },
        )

        return True

    # ---------------------------------------------------------
    # Shared Discoveries
    # ---------------------------------------------------------

    def share_discovery(
        self,
        sender_id: str,
        discovery_type: str,
        reference_id: str,
        title: str,
        description: str,
        metadata: Optional[Dict] = None,
    ) -> Optional[SharedDiscovery]:

        sender = self.get_player(sender_id)

        if not sender:
            return None

        if not sender.can_send_chat:
            return None

        discovery = SharedDiscovery(
            discovery_id=f"share_{uuid.uuid4().hex[:10]}",
            sender_id=sender_id,
            sender_name=sender.name,
            discovery_type=discovery_type,
            reference_id=reference_id,
            title=title,
            description=description,
            metadata=metadata or {},
        )

        self.discoveries.append(discovery)

        if len(self.discoveries) > 500:
            self.discoveries = self.discoveries[-500:]

        self._team_event(
            "discovery_shared",
            {
                "discovery_id": discovery.discovery_id,
                "sender_id": sender_id,
                "title": title,
            },
        )

        return discovery

    def get_shared_discoveries(
        self,
        limit: int = 100,
    ) -> List[SharedDiscovery]:

        return self.discoveries[-limit:]

    def get_player_shared_discoveries(
        self,
        player_id: str,
        limit: int = 100,
    ) -> List[SharedDiscovery]:

        result = [
            item
            for item in self.discoveries
            if item.sender_id == player_id
        ]

        return result[-limit:]

    # ---------------------------------------------------------
    # Team Events
    # ---------------------------------------------------------

    def _team_event(
        self,
        event_type: str,
        data: Optional[Dict] = None,
    ):

        self.team_events.append(
            {
                "event_id": f"team_{uuid.uuid4().hex[:10]}",
                "type": event_type,
                "created_at": now_iso(),
                "data": data or {},
            }
        )

        if len(self.team_events) > 500:
            self.team_events = self.team_events[-500:]

    def get_team_events(
        self,
        limit: int = 100,
    ) -> List[Dict]:

        return self.team_events[-limit:]

    # ---------------------------------------------------------
    # Team Queries
    # ---------------------------------------------------------

    def online_players(self) -> List[PlayerPresence]:

        return [
            player
            for player in self.players.values()
            if player.status in {
                "online",
                "weak",
                "hostage",
            }
        ]

    def active_player_count(self) -> int:

        return len(self.online_players())

    def can_start_case(self) -> bool:

        return self.active_player_count() >= 2

    def can_join_case(self) -> bool:

        return len(self.players) < self.MAX_PLAYERS

    # ---------------------------------------------------------
    # Public State
    # ---------------------------------------------------------

    def public_state(
        self,
        player_id: Optional[str] = None,
    ) -> Dict:

        return {
            "max_players": self.MAX_PLAYERS,
            "player_count": len(self.players),
            "active_player_count": self.active_player_count(),

            "players": [
                player.public_state()
                for player in self.players.values()
            ],

            "shared_discoveries": [
                discovery.public_state()
                for discovery in self.get_shared_discoveries()
            ],

            "recent_events": self.get_team_events(50),

            "current_player": (
                self.get_player(player_id).public_state()
                if player_id and self.get_player(player_id)
                else None
            ),
        }


def create_demo_multiplayer() -> MultiplayerSystem:

    multiplayer = MultiplayerSystem()

    players = [
        ("mehdi", "مهدی"),
        ("rastin", "راستین"),
        ("amirali", "امیرعلی"),
        ("mahna", "مهنا"),
        ("fatemeh", "فاطمه"),
    ]

    for player_id, name in players:

        multiplayer.add_player(
            player_id=player_id,
            name=name,
            title="کارآگاه",
        )

    multiplayer.update_location(
        "mehdi",
        "victim_home",
        "خانه قربانی",
    )

    multiplayer.update_location(
        "rastin",
        "central_hospital",
        "بیمارستان مرکزی",
    )

    multiplayer.update_location(
        "amirali",
        "central_bank",
        "بانک مرکزی",
    )

    multiplayer.update_location(
        "mahna",
        "central_square",
        "میدان مرکزی مهستان",
    )

    multiplayer.update_location(
        "fatemeh",
        "police_station",
        "کلانتری مرکزی",
    )

    multiplayer.mark_weak("mahna")

    multiplayer.share_discovery(
        sender_id="mehdi",
        discovery_type="evidence",
        reference_id="ev_victim_phone",
        title="موبایل قربانی",
        description="یک موبایل مشکوک در خانه قربانی پیدا شد.",
    )

    return multiplayer


if __name__ == "__main__":

    multiplayer = create_demo_multiplayer()

    print("=== Mehestan Multiplayer System ===")

    print(
        "Players:",
        len(multiplayer.players),
    )

    print(
        "Active:",
        multiplayer.active_player_count(),
    )

    print(
        "Can start:",
        multiplayer.can_start_case(),
    )

    print(
        "Shared discoveries:",
        len(multiplayer.discoveries),
    )
