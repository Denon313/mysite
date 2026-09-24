"""
Mehestan City System
سیستم شهر مهستان
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo
from datetime import datetime


TEHRAN_TZ = ZoneInfo("Asia/Tehran")


@dataclass
class Location:
    id: str
    name: str
    category: str
    description: str

    # مختصات منطقی برای نقشه.
    # بعداً به مختصات واقعی سه‌بعدی وصل می‌شوند.
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    # ساعت فعالیت
    opens_at: int = 0
    closes_at: int = 24

    # قابلیت‌های مکان
    accessible_at_night: bool = True
    has_cctv: bool = False
    has_npcs: bool = True
    searchable: bool = True

    tags: List[str] = field(default_factory=list)

    def is_open(self, hour: Optional[int] = None) -> bool:
        """
        بررسی باز بودن مکان بر اساس ساعت ایران.
        """

        if hour is None:
            hour = datetime.now(TEHRAN_TZ).hour

        if self.opens_at == 0 and self.closes_at == 24:
            return True

        if self.opens_at < self.closes_at:
            return self.opens_at <= hour < self.closes_at

        # مکان‌هایی که از شب وارد روز بعد می‌شوند.
        return hour >= self.opens_at or hour < self.closes_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "position": {
                "x": self.x,
                "y": self.y,
                "z": self.z,
            },
            "opens_at": self.opens_at,
            "closes_at": self.closes_at,
            "open": self.is_open(),
            "accessible_at_night": self.accessible_at_night,
            "has_cctv": self.has_cctv,
            "has_npcs": self.has_npcs,
            "searchable": self.searchable,
            "tags": list(self.tags),
        }


class MehestanCity:
    """
    مدیریت شهر مهستان.

    این کلاس بعداً می‌تواند به:
    - نقشه سه‌بعدی
    - NPCها
    - دوربین‌ها
    - سیستم سفر
    - آب‌وهوا
    - ترافیک
    - روز و شب
    متصل شود.
    """

    CITY_ID = "mehestan"
    CITY_NAME = "مهستان"

    def __init__(self):
        self.locations: Dict[str, Location] = {}
        self._load_default_locations()

    # ---------------------------------------------------------
    # مکان‌های پیش‌فرض
    # ---------------------------------------------------------

    def _load_default_locations(self) -> None:

        locations = [

            Location(
                id="city_hall",
                name="شهرداری مهستان",
                category="government",
                description=(
                    "ساختمان مرکزی شهرداری؛ محل نگهداری بخشی از "
                    "سوابق شهری و مجوزها."
                ),
                x=0,
                y=0,
                z=0,
                opens_at=8,
                closes_at=16,
                accessible_at_night=False,
                has_cctv=True,
                tags=["سوابق", "مجوز", "دولت"],
            ),

            Location(
                id="police_station",
                name="کلانتری مرکزی",
                category="police",
                description=(
                    "مرکز اصلی پلیس شهر؛ محل پرونده‌های قضایی، "
                    "گزارش‌های حادثه و سوابق مجرمان."
                ),
                x=12,
                y=0,
                z=4,
                opens_at=0,
                closes_at=24,
                accessible_at_night=True,
                has_cctv=True,
                tags=["پلیس", "پرونده", "مجرمان"],
            ),

            Location(
                id="hospital",
                name="بیمارستان مرکزی",
                category="medical",
                description=(
                    "بیمارستان اصلی مهستان؛ یکی از مهم‌ترین "
                    "مکان‌های پرونده."
                ),
                x=25,
                y=0,
                z=8,
                opens_at=0,
                closes_at=24,
                accessible_at_night=True,
                has_cctv=True,
                tags=["پزشکی", "بیمار", "سوابق پزشکی"],
            ),

            Location(
                id="victim_home",
                name="خانه قربانی",
                category="residence",
                description=(
                    "محل زندگی قربانی؛ احتمال وجود مدارک، "
                    "اسناد شخصی و سرنخ‌های مهم."
                ),
                x=-15,
                y=0,
                z=10,
                opens_at=0,
                closes_at=24,
                accessible_at_night=True,
                has_cctv=False,
                tags=["قربانی", "مدارک", "خانه"],
            ),

            Location(
                id="central_bar",
                name="بار مرکزی",
                category="entertainment",
                description=(
                    "پاتوق شبانه شهر؛ بسیاری از NPCها اطلاعات "
                    "غیررسمی درباره شهر دارند."
                ),
                x=18,
                y=0,
                z=-12,
                opens_at=17,
                closes_at=4,
                accessible_at_night=True,
                has_cctv=True,
                tags=["شب", "شاهد", "شایعه"],
            ),

            Location(
                id="bank",
                name="بانک مرکزی",
                category="financial",
                description=(
                    "بانک اصلی شهر؛ اطلاعات تراکنش‌ها و "
                    "دسترسی‌های مالی ممکن است در پرونده مهم باشند."
                ),
                x=35,
                y=0,
                z=-3,
                opens_at=8,
                closes_at=15,
                accessible_at_night=False,
                has_cctv=True,
                tags=["بانک", "تراکنش", "دوربین"],
            ),

            Location(
                id="train_station",
                name="ایستگاه قطار",
                category="transport",
                description=(
                    "ایستگاه اصلی قطار مهستان؛ رفت‌وآمد افراد "
                    "و زمان خروج از شهر قابل بررسی است."
                ),
                x=45,
                y=0,
                z=15,
                opens_at=0,
                closes_at=24,
                accessible_at_night=True,
                has_cctv=True,
                tags=["قطار", "سفر", "مسافر"],
            ),

            Location(
                id="gas_station",
                name="پمپ بنزین شبانه‌روزی",
                category="service",
                description=(
                    "پمپ بنزین حاشیه شهر؛ دوربین‌ها و کارکنان "
                    "ممکن است شاهد رفت‌وآمدها باشند."
                ),
                x=-35,
                y=0,
                z=18,
                opens_at=0,
                closes_at=24,
                accessible_at_night=True,
                has_cctv=True,
                tags=["ماشین", "دوربین", "پلاک"],
            ),

            Location(
                id="abandoned_factory",
                name="کارخانه متروکه",
                category="industrial",
                description=(
                    "ساختمان صنعتی متروکه در حاشیه شهر؛ "
                    "ورود به آن می‌تواند خطرناک باشد."
                ),
                x=-48,
                y=0,
                z=-25,
                opens_at=0,
                closes_at=24,
                accessible_at_night=True,
                has_cctv=False,
                tags=["متروکه", "خطر", "مخفیگاه"],
            ),

            Location(
                id="old_park",
                name="پارک قدیمی",
                category="park",
                description=(
                    "پارک قدیمی شهر؛ محل رفت‌وآمد شبانه و "
                    "گاهی محل قرارهای مخفی."
                ),
                x=-5,
                y=0,
                z=-30,
                opens_at=0,
                closes_at=24,
                accessible_at_night=True,
                has_cctv=True,
                tags=["پارک", "شاهد", "قرار"],
            ),

            Location(
                id="newspaper",
                name="روزنامه مهستان",
                category="media",
                description=(
                    "دفتر روزنامه شهر؛ اخبار قدیمی و اطلاعات "
                    "درباره افراد مشهور شهر در اینجا پیدا می‌شود."
                ),
                x=8,
                y=0,
                z=20,
                opens_at=9,
                closes_at=18,
                accessible_at_night=False,
                has_cctv=True,
                tags=["خبر", "روزنامه", "آرشیو"],
            ),

            Location(
                id="hotel",
                name="هتل مهستان",
                category="hotel",
                description=(
                    "هتل بزرگ شهر؛ ثبت ورود و خروج مهمانان "
                    "می‌تواند در تحقیقات استفاده شود."
                ),
                x=30,
                y=0,
                z=28,
                opens_at=0,
                closes_at=24,
                accessible_at_night=True,
                has_cctv=True,
                tags=["هتل", "مهمان", "ثبت ورود"],
            ),

            Location(
                id="old_city",
                name="بخش قدیمی شهر",
                category="district",
                description=(
                    "کوچه‌های قدیمی و ساختمان‌های فرسوده "
                    "که رازهای زیادی در خود دارند."
                ),
                x=-25,
                y=0,
                z=-5,
                opens_at=0,
                closes_at=24,
                accessible_at_night=True,
                has_cctv=False,
                tags=["قدیمی", "کوچه", "راز"],
            ),

            Location(
                id="main_square",
                name="میدان مرکزی مهستان",
                category="public",
                description=(
                    "قلب شهر و یکی از شلوغ‌ترین نقاط مهستان."
                ),
                x=0,
                y=0,
                z=0,
                opens_at=0,
                closes_at=24,
                accessible_at_night=True,
                has_cctv=True,
                tags=["مرکز شهر", "جمعیت", "دوربین"],
            ),
        ]

        for location in locations:
            self.locations[location.id] = location

    # ---------------------------------------------------------
    # دریافت مکان
    # ---------------------------------------------------------

    def get_location(self, location_id: str) -> Optional[Location]:
        return self.locations.get(location_id)

    # ---------------------------------------------------------
    # لیست همه مکان‌ها
    # ---------------------------------------------------------

    def all_locations(self) -> List[dict]:
        return [
            location.to_dict()
            for location in self.locations.values()
        ]

    # ---------------------------------------------------------
    # مکان‌های باز
    # ---------------------------------------------------------

    def open_locations(self) -> List[dict]:
        return [
            location.to_dict()
            for location in self.locations.values()
            if location.is_open()
        ]

    # ---------------------------------------------------------
    # مکان‌های دارای دوربین
    # ---------------------------------------------------------

    def cctv_locations(self) -> List[dict]:
        return [
            location.to_dict()
            for location in self.locations.values()
            if location.has_cctv
        ]

    # ---------------------------------------------------------
    # مکان‌های قابل جست‌وجو
    # ---------------------------------------------------------

    def searchable_locations(self) -> List[dict]:
        return [
            location.to_dict()
            for location in self.locations.values()
            if location.searchable
        ]

    # ---------------------------------------------------------
    # افزودن مکان جدید
    # ---------------------------------------------------------

    def add_location(self, location: Location) -> bool:

        if location.id in self.locations:
            return False

        self.locations[location.id] = location
        return True

    # ---------------------------------------------------------
    # حذف مکان
    # ---------------------------------------------------------

    def remove_location(self, location_id: str) -> bool:

        if location_id not in self.locations:
            return False

        del self.locations[location_id]
        return True

    # ---------------------------------------------------------
    # اطلاعات شهر
    # ---------------------------------------------------------

    def city_info(self) -> dict:

        now = datetime.now(TEHRAN_TZ)

        return {
            "id": self.CITY_ID,
            "name": self.CITY_NAME,
            "timezone": "Asia/Tehran",
            "local_time": now.isoformat(),
            "hour": now.hour,
            "is_night": now.hour >= 20 or now.hour < 6,
            "location_count": len(self.locations),
        }


mehestan_city = MehestanCity()
