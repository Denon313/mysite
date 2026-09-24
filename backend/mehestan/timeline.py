"""
Mehestan Mystery Case
Timeline System
سیستم خط زمانی پرونده مرموز — شهر مهستان
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo


TEHRAN_TZ = ZoneInfo("Asia/Tehran")


@dataclass
class TimelineEvent:
    event_id: str
    title: str
    description: str

    # زمان دقیق رویداد
    date: str
    time: str

    # مکان
    location_id: Optional[str] = None

    # افراد مرتبط
    people: List[str] = field(default_factory=list)

    # منبع اطلاعات
    source_type: str = "unknown"
    source_id: Optional[str] = None

    # میزان اطمینان
    reliability: str = "normal"

    # آیا بازیکن این رویداد را کشف کرده؟
    discovered: bool = False

    # اطلاعات تکمیلی
    details: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.event_id,
            "title": self.title,
            "description": self.description,
            "date": self.date,
            "time": self.time,
            "location_id": self.location_id,
            "people": self.people,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "reliability": self.reliability,
            "discovered": self.discovered,
            "details": self.details,
        }


class TimelineSystem:
    """
    مدیریت خط زمانی پرونده.

    هدف:
    - ثبت اتفاقات
    - مرتب‌سازی زمانی
    - بررسی تناقض‌ها
    - اتصال افراد به رویدادها
    - اتصال رویدادها به مدارک
    """

    RELIABILITY_LEVELS = {
        "unknown",
        "low",
        "normal",
        "high",
        "confirmed",
        "false",
        "outdated",
    }

    SOURCE_TYPES = {
        "npc",
        "evidence",
        "cctv",
        "phone",
        "document",
        "system",
        "player",
        "unknown",
    }

    def __init__(self):
        self.events: Dict[str, TimelineEvent] = {}

        self._load_default_events()

    # ---------------------------------------------------------
    # زمان
    # ---------------------------------------------------------

    @staticmethod
    def now() -> str:
        return datetime.now(TEHRAN_TZ).isoformat()

    @staticmethod
    def time_to_minutes(time_value: str) -> int:
        """
        تبدیل HH:MM به دقیقه از ابتدای روز.
        """

        try:
            hour, minute = time_value.split(":")
            return int(hour) * 60 + int(minute)
        except (ValueError, AttributeError):
            raise ValueError("فرمت زمان باید HH:MM باشد.")

    # ---------------------------------------------------------
    # ثبت رویداد
    # ---------------------------------------------------------

    def add_event(
        self,
        event_id: str,
        title: str,
        description: str,
        date: str,
        time: str,
        location_id: Optional[str] = None,
        people: Optional[List[str]] = None,
        source_type: str = "unknown",
        source_id: Optional[str] = None,
        reliability: str = "normal",
        discovered: bool = False,
        details: Optional[dict] = None,
    ) -> TimelineEvent:

        if event_id in self.events:
            raise ValueError("این شناسه رویداد قبلاً ثبت شده است.")

        self.time_to_minutes(time)

        if source_type not in self.SOURCE_TYPES:
            source_type = "unknown"

        if reliability not in self.RELIABILITY_LEVELS:
            reliability = "normal"

        event = TimelineEvent(
            event_id=event_id,
            title=title,
            description=description,
            date=date,
            time=time,
            location_id=location_id,
            people=people or [],
            source_type=source_type,
            source_id=source_id,
            reliability=reliability,
            discovered=discovered,
            details=details or {},
        )

        self.events[event_id] = event
        return event

    # ---------------------------------------------------------
    # دریافت رویداد
    # ---------------------------------------------------------

    def get_event(
        self,
        event_id: str,
    ) -> Optional[TimelineEvent]:

        return self.events.get(event_id)

    # ---------------------------------------------------------
    # کشف رویداد
    # ---------------------------------------------------------

    def discover_event(
        self,
        event_id: str,
    ) -> Optional[TimelineEvent]:

        event = self.get_event(event_id)

        if not event:
            return None

        event.discovered = True
        return event

    # ---------------------------------------------------------
    # تغییر اعتبار
    # ---------------------------------------------------------

    def set_reliability(
        self,
        event_id: str,
        reliability: str,
    ) -> Optional[TimelineEvent]:

        if reliability not in self.RELIABILITY_LEVELS:
            raise ValueError("سطح اعتبار نامعتبر است.")

        event = self.get_event(event_id)

        if not event:
            return None

        event.reliability = reliability
        return event

    # ---------------------------------------------------------
    # مرتب‌سازی زمانی
    # ---------------------------------------------------------

    def sorted_events(
        self,
        discovered_only: bool = False,
    ) -> List[TimelineEvent]:

        events = list(self.events.values())

        if discovered_only:
            events = [
                event
                for event in events
                if event.discovered
            ]

        return sorted(
            events,
            key=lambda event: (
                event.date,
                self.time_to_minutes(event.time),
            ),
        )

    # ---------------------------------------------------------
    # رویدادهای یک شخص
    # ---------------------------------------------------------

    def events_for_person(
        self,
        person_id: str,
        discovered_only: bool = False,
    ) -> List[TimelineEvent]:

        events = [
            event
            for event in self.events.values()
            if person_id in event.people
        ]

        if discovered_only:
            events = [
                event
                for event in events
                if event.discovered
            ]

        return sorted(
            events,
            key=lambda event: (
                event.date,
                self.time_to_minutes(event.time),
            ),
        )

    # ---------------------------------------------------------
    # رویدادهای یک مکان
    # ---------------------------------------------------------

    def events_at_location(
        self,
        location_id: str,
        discovered_only: bool = False,
    ) -> List[TimelineEvent]:

        events = [
            event
            for event in self.events.values()
            if event.location_id == location_id
        ]

        if discovered_only:
            events = [
                event
                for event in events
                if event.discovered
            ]

        return sorted(
            events,
            key=lambda event: (
                event.date,
                self.time_to_minutes(event.time),
            ),
        )

    # ---------------------------------------------------------
    # پیدا کردن تناقض‌های زمانی
    # ---------------------------------------------------------

    def find_time_conflicts(
        self,
        person_id: str,
        tolerance_minutes: int = 0,
    ) -> List[dict]:

        events = self.events_for_person(person_id)

        conflicts = []

        for index, first in enumerate(events):

            first_minute = self.time_to_minutes(first.time)

            for second in events[index + 1:]:

                if first.date != second.date:
                    continue

                second_minute = self.time_to_minutes(second.time)

                difference = abs(
                    second_minute - first_minute
                )

                if difference <= tolerance_minutes:
                    continue

                # اگر دو مکان متفاوت در فاصله بسیار کوتاه ثبت شده باشند
                if (
                    first.location_id
                    and second.location_id
                    and first.location_id != second.location_id
                    and difference <= 30
                ):
                    conflicts.append(
                        {
                            "person_id": person_id,
                            "first_event": first.event_id,
                            "second_event": second.event_id,
                            "difference_minutes": difference,
                            "first_location": first.location_id,
                            "second_location": second.location_id,
                            "type": "impossible_travel",
                        }
                    )

        return conflicts

    # ---------------------------------------------------------
    # جستجو بر اساس بازه زمانی
    # ---------------------------------------------------------

    def events_between(
        self,
        date: str,
        start_time: str,
        end_time: str,
        discovered_only: bool = False,
    ) -> List[TimelineEvent]:

        start = self.time_to_minutes(start_time)
        end = self.time_to_minutes(end_time)

        result = []

        for event in self.events.values():

            if event.date != date:
                continue

            if discovered_only and not event.discovered:
                continue

            current = self.time_to_minutes(event.time)

            if start <= current <= end:
                result.append(event)

        return sorted(
            result,
            key=lambda event: self.time_to_minutes(event.time),
        )

    # ---------------------------------------------------------
    # وضعیت عمومی
    # ---------------------------------------------------------

    def public_state(self) -> dict:

        discovered = [
            event
            for event in self.events.values()
            if event.discovered
        ]

        return {
            "events": [
                event.to_dict()
                for event in self.sorted_events(
                    discovered_only=True
                )
            ],
            "total_events": len(self.events),
            "discovered_events": len(discovered),
        }

    # ---------------------------------------------------------
    # رویدادهای اولیه پرونده
    # ---------------------------------------------------------

    def _load_default_events(self):

        self.add_event(
            event_id="tl_last_known_victim",
            title="آخرین مشاهده قربانی",
            description="قربانی برای آخرین بار در محدوده خانه خود دیده شده است.",
            date="2026-09-20",
            time="20:10",
            location_id="victim_home",
            people=["arman_nikfar"],
            source_type="npc",
            reliability="normal",
            discovered=False,
        )

        self.add_event(
            event_id="tl_unknown_transaction",
            title="تراکنش مشکوک",
            description="یک تراکنش غیرعادی در حساب قربانی ثبت شده است.",
            date="2026-09-20",
            time="20:42",
            location_id="central_bank",
            people=["arman_nikfar"],
            source_type="document",
            source_id="ev_bank_record",
            reliability="high",
            discovered=False,
        )

        self.add_event(
            event_id="tl_cctv_fragment",
            title="حرکت مشکوک در دوربین",
            description="دوربین شهری حرکت فردی ناشناس را ثبت کرده است.",
            date="2026-09-20",
            time="21:05",
            location_id="central_square",
            source_type="cctv",
            source_id="ev_cctv_fragment",
            reliability="high",
            discovered=False,
        )

        self.add_event(
            event_id="tl_phone_last_activity",
            title="آخرین فعالیت موبایل قربانی",
            description="آخرین فعالیت ثبت‌شده روی موبایل قربانی.",
            date="2026-09-20",
            time="21:17",
            location_id="victim_home",
            people=["arman_nikfar"],
            source_type="phone",
            source_id="ev_victim_phone",
            reliability="high",
            discovered=False,
        )


# موتور مستقل Timeline
timeline_system = TimelineSystem()
