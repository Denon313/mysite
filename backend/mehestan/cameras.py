"""
Mehestan Mystery Case
CCTV / Security Camera System
سیستم دوربین‌های مداربسته شهر مهستان
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
import uuid


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Camera:
    camera_id: str
    name: str
    location_id: str
    location_name: str
    status: str = "online"
    direction: str = "unknown"
    description: str = ""
    last_checked: str = field(default_factory=now_iso)
    disabled_until: Optional[str] = None
    metadata: Dict = field(default_factory=dict)

    def public_state(self) -> Dict:
        return {
            "id": self.camera_id,
            "name": self.name,
            "location_id": self.location_id,
            "location_name": self.location_name,
            "status": self.status,
            "direction": self.direction,
            "description": self.description,
            "last_checked": self.last_checked,
            "disabled_until": self.disabled_until,
            "metadata": self.metadata,
        }


@dataclass
class CameraFootage:
    footage_id: str
    camera_id: str
    title: str
    description: str
    started_at: str
    ended_at: str
    location_id: str
    reliability: str = "medium"
    available: bool = True
    corrupted: bool = False
    discovered: bool = False
    discovered_by: Optional[str] = None
    evidence_id: Optional[str] = None
    metadata: Dict = field(default_factory=dict)

    def public_state(self) -> Dict:
        return {
            "id": self.footage_id,
            "camera_id": self.camera_id,
            "title": self.title,
            "description": self.description,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "location_id": self.location_id,
            "reliability": self.reliability,
            "available": self.available,
            "corrupted": self.corrupted,
            "discovered": self.discovered,
            "discovered_by": self.discovered_by,
            "evidence_id": self.evidence_id,
            "metadata": self.metadata,
        }


class CameraSystem:
    """
    مدیریت دوربین‌های مداربسته مهستان.

    این ماژول مستقل است و بعداً می‌تواند به:
    - identity.py
    - evidence.py
    - timeline.py
    - hacker.py
    - hostage.py
    متصل شود.
    """

    VALID_STATUS = {
        "online",
        "checking",
        "offline",
        "hacked",
        "maintenance",
    }

    VALID_RELIABILITY = {
        "low",
        "medium",
        "high",
        "verified",
        "unknown",
    }

    def __init__(self):
        self.cameras: Dict[str, Camera] = {}
        self.footage: Dict[str, CameraFootage] = {}
        self.events: List[Dict] = []

        self._load_default_cameras()
        self._load_default_footage()

    # ---------------------------------------------------------
    # Cameras
    # ---------------------------------------------------------

    def add_camera(
        self,
        camera_id: str,
        name: str,
        location_id: str,
        location_name: str,
        direction: str = "unknown",
        description: str = "",
        metadata: Optional[Dict] = None,
    ) -> Camera:

        camera = Camera(
            camera_id=camera_id,
            name=name,
            location_id=location_id,
            location_name=location_name,
            direction=direction,
            description=description,
            metadata=metadata or {},
        )

        self.cameras[camera_id] = camera

        self._log_event(
            "camera_added",
            camera_id=camera_id,
        )

        return camera

    def get_camera(self, camera_id: str) -> Optional[Camera]:
        return self.cameras.get(camera_id)

    def list_cameras(
        self,
        location_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Camera]:

        result = list(self.cameras.values())

        if location_id:
            result = [
                camera
                for camera in result
                if camera.location_id == location_id
            ]

        if status:
            result = [
                camera
                for camera in result
                if camera.status == status
            ]

        return result

    def set_status(
        self,
        camera_id: str,
        status: str,
        reason: str = "",
    ) -> bool:

        if status not in self.VALID_STATUS:
            return False

        camera = self.get_camera(camera_id)

        if not camera:
            return False

        camera.status = status
        camera.last_checked = now_iso()

        self._log_event(
            "camera_status_changed",
            camera_id=camera_id,
            status=status,
            reason=reason,
        )

        return True

    def check_camera(self, camera_id: str) -> Optional[str]:
        camera = self.get_camera(camera_id)

        if not camera:
            return None

        camera.last_checked = now_iso()

        return camera.status

    def disable_camera(
        self,
        camera_id: str,
        reason: str = "unknown",
        disabled_until: Optional[str] = None,
    ) -> bool:

        camera = self.get_camera(camera_id)

        if not camera:
            return False

        camera.status = "offline"
        camera.disabled_until = disabled_until
        camera.last_checked = now_iso()

        self._log_event(
            "camera_disabled",
            camera_id=camera_id,
            reason=reason,
            disabled_until=disabled_until,
        )

        return True

    def restore_camera(self, camera_id: str) -> bool:

        camera = self.get_camera(camera_id)

        if not camera:
            return False

        camera.status = "online"
        camera.disabled_until = None
        camera.last_checked = now_iso()

        self._log_event(
            "camera_restored",
            camera_id=camera_id,
        )

        return True

    def hack_camera(
        self,
        camera_id: str,
        reason: str = "security breach",
    ) -> bool:

        camera = self.get_camera(camera_id)

        if not camera:
            return False

        camera.status = "hacked"
        camera.last_checked = now_iso()

        self._log_event(
            "camera_hacked",
            camera_id=camera_id,
            reason=reason,
        )

        return True

    # ---------------------------------------------------------
    # Footage
    # ---------------------------------------------------------

    def add_footage(
        self,
        camera_id: str,
        title: str,
        description: str,
        started_at: str,
        ended_at: str,
        location_id: Optional[str] = None,
        reliability: str = "medium",
        available: bool = True,
        corrupted: bool = False,
        evidence_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Optional[CameraFootage]:

        camera = self.get_camera(camera_id)

        if not camera:
            return None

        if reliability not in self.VALID_RELIABILITY:
            reliability = "unknown"

        footage = CameraFootage(
            footage_id=f"footage_{uuid.uuid4().hex[:10]}",
            camera_id=camera_id,
            title=title,
            description=description,
            started_at=started_at,
            ended_at=ended_at,
            location_id=location_id or camera.location_id,
            reliability=reliability,
            available=available,
            corrupted=corrupted,
            evidence_id=evidence_id,
            metadata=metadata or {},
        )

        self.footage[footage.footage_id] = footage

        self._log_event(
            "footage_added",
            footage_id=footage.footage_id,
            camera_id=camera_id,
        )

        return footage

    def get_footage(
        self,
        footage_id: str,
    ) -> Optional[CameraFootage]:

        return self.footage.get(footage_id)

    def get_footage_for_camera(
        self,
        camera_id: str,
    ) -> List[CameraFootage]:

        return [
            footage
            for footage in self.footage.values()
            if footage.camera_id == camera_id
        ]

    def get_footage_at_location(
        self,
        location_id: str,
    ) -> List[CameraFootage]:

        return [
            footage
            for footage in self.footage.values()
            if footage.location_id == location_id
        ]

    def discover_footage(
        self,
        footage_id: str,
        player_id: str,
    ) -> Optional[CameraFootage]:

        footage = self.get_footage(footage_id)

        if not footage:
            return None

        if not footage.available:
            return None

        footage.discovered = True
        footage.discovered_by = player_id

        self._log_event(
            "footage_discovered",
            footage_id=footage_id,
            player_id=player_id,
        )

        return footage

    def corrupt_footage(
        self,
        footage_id: str,
        reason: str = "data corruption",
    ) -> bool:

        footage = self.get_footage(footage_id)

        if not footage:
            return False

        footage.corrupted = True

        self._log_event(
            "footage_corrupted",
            footage_id=footage_id,
            reason=reason,
        )

        return True

    def restore_footage(
        self,
        footage_id: str,
    ) -> bool:

        footage = self.get_footage(footage_id)

        if not footage:
            return False

        footage.corrupted = False

        self._log_event(
            "footage_restored",
            footage_id=footage_id,
        )

        return True

    # ---------------------------------------------------------
    # Search
    # ---------------------------------------------------------

    def search_footage(
        self,
        query: str,
    ) -> List[CameraFootage]:

        query = (query or "").strip().lower()

        if not query:
            return []

        results = []

        for footage in self.footage.values():
            haystack = " ".join(
                [
                    footage.title,
                    footage.description,
                    footage.location_id,
                    footage.camera_id,
                ]
            ).lower()

            if query in haystack:
                results.append(footage)

        return results

    # ---------------------------------------------------------
    # Events
    # ---------------------------------------------------------

    def _log_event(
        self,
        event_type: str,
        **data,
    ):

        self.events.append(
            {
                "event_id": f"camera_event_{uuid.uuid4().hex[:10]}",
                "type": event_type,
                "created_at": now_iso(),
                "data": data,
            }
        )

        if len(self.events) > 300:
            self.events = self.events[-300:]

    def get_events(
        self,
        limit: int = 50,
    ) -> List[Dict]:

        return self.events[-limit:]

    # ---------------------------------------------------------
    # Public State
    # ---------------------------------------------------------

    def public_state(
        self,
        player_id: Optional[str] = None,
    ) -> Dict:

        return {
            "cameras": [
                camera.public_state()
                for camera in self.cameras.values()
            ],
            "footage": [
                footage.public_state()
                for footage in self.footage.values()
                if footage.discovered
                or player_id is None
            ],
        }

    # ---------------------------------------------------------
    # Default Cameras
    # ---------------------------------------------------------

    def _load_default_cameras(self):

        defaults = [
            (
                "cam_motahari_01",
                "دوربین خیابان مطهری",
                "motahari_street",
                "خیابان مطهری",
                "east",
            ),
            (
                "cam_amirkabir_01",
                "دوربین خیابان امیرکبیر",
                "amirkabir_street",
                "خیابان امیرکبیر",
                "north",
            ),
            (
                "cam_valiasr_01",
                "دوربین خیابان ولیعصر",
                "valiasr_street",
                "خیابان ولیعصر",
                "south",
            ),
            (
                "cam_hospital_01",
                "دوربین ورودی بیمارستان",
                "central_hospital",
                "بیمارستان مرکزی",
                "entrance",
            ),
            (
                "cam_hospital_02",
                "دوربین راهروی بیمارستان",
                "central_hospital",
                "بیمارستان مرکزی",
                "hallway",
            ),
            (
                "cam_station_01",
                "دوربین ایستگاه قطار",
                "train_station",
                "ایستگاه قطار",
                "platform",
            ),
            (
                "cam_square_01",
                "دوربین میدان مرکزی",
                "central_square",
                "میدان مرکزی مهستان",
                "west",
            ),
            (
                "cam_bank_01",
                "دوربین ورودی بانک",
                "central_bank",
                "بانک مرکزی",
                "entrance",
            ),
            (
                "cam_factory_01",
                "دوربین کارخانه متروکه",
                "abandoned_factory",
                "کارخانه متروکه",
                "yard",
            ),
            (
                "cam_hotel_01",
                "دوربین لابی هتل",
                "mehestan_hotel",
                "هتل مهستان",
                "lobby",
            ),
        ]

        for item in defaults:
            self.add_camera(
                camera_id=item[0],
                name=item[1],
                location_id=item[2],
                location_name=item[3],
                direction=item[4],
            )

    # ---------------------------------------------------------
    # Default Footage
    # ---------------------------------------------------------

    def _load_default_footage(self):

        self.add_footage(
            camera_id="cam_square_01",
            title="قطعه ناقص فیلم میدان مرکزی",
            description=(
                "در بخشی از فیلم، فردی با لباس تیره "
                "در نزدیکی میدان دیده می‌شود."
            ),
            started_at="2026-09-20T21:04:00+03:30",
            ended_at="2026-09-20T21:08:00+03:30",
            location_id="central_square",
            reliability="medium",
            available=True,
            corrupted=True,
            evidence_id="ev_cctv_fragment",
        )

        self.add_footage(
            camera_id="cam_hospital_01",
            title="ورود مشکوک به بیمارستان",
            description=(
                "شخصی در ساعت غیرعادی وارد ساختمان شده است."
            ),
            started_at="2026-09-20T22:13:00+03:30",
            ended_at="2026-09-20T22:17:00+03:30",
            location_id="central_hospital",
            reliability="medium",
            available=True,
            corrupted=False,
        )

        self.add_footage(
            camera_id="cam_bank_01",
            title="ورود فرد ناشناس به بانک",
            description=(
                "یک فرد ناشناس نزدیک زمان تراکنش مشکوک "
                "در محدوده بانک دیده شده است."
            ),
            started_at="2026-09-20T20:39:00+03:30",
            ended_at="2026-09-20T20:45:00+03:30",
            location_id="central_bank",
            reliability="low",
            available=True,
            corrupted=False,
        )

        self.add_footage(
            camera_id="cam_station_01",
            title="خروج عجولانه از ایستگاه",
            description=(
                "فردی پس از دریافت یک تماس تلفنی "
                "با عجله از محدوده ایستگاه خارج شده است."
            ),
            started_at="2026-09-20T21:22:00+03:30",
            ended_at="2026-09-20T21:26:00+03:30",
            location_id="train_station",
            reliability="high",
            available=True,
            corrupted=False,
        )


def create_demo_camera_system() -> CameraSystem:
    return CameraSystem()


if __name__ == "__main__":
    cameras = create_demo_camera_system()

    print("=== Mehestan Camera System ===")
    print("Cameras:", len(cameras.list_cameras()))
    print("Footage:", len(cameras.footage))

    cameras.hack_camera(
        "cam_square_01",
        reason="unknown security interference",
    )

    print(
        "Square camera status:",
        cameras.get_camera("cam_square_01").status,
    )
