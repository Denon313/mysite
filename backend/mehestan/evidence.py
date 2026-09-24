"""
Mehestan Mystery Case
Evidence & Clue System
سیستم مدارک و شواهد پرونده مرموز — شهر مهستان
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo


TEHRAN_TZ = ZoneInfo("Asia/Tehran")


@dataclass
class Evidence:
    evidence_id: str
    title: str
    category: str
    description: str
    location_id: str
    discovered_by: Optional[str] = None

    # اعتبار مدرک
    reliability: str = "normal"

    # آیا مدرک محرمانه است؟
    confidential: bool = False

    # آیا هنوز بررسی نشده؟
    needs_analysis: bool = False

    # اطلاعات تکمیلی
    details: Dict = field(default_factory=dict)

    discovered_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.evidence_id,
            "title": self.title,
            "category": self.category,
            "description": self.description,
            "location_id": self.location_id,
            "discovered_by": self.discovered_by,
            "reliability": self.reliability,
            "confidential": self.confidential,
            "needs_analysis": self.needs_analysis,
            "details": self.details,
            "discovered_at": self.discovered_at,
        }


@dataclass
class Clue:
    clue_id: str
    title: str
    description: str

    # بعضی سرنخ‌ها مستقیماً به یک مدرک وصل هستند
    evidence_id: Optional[str] = None

    # ارزش مالی سرنخ
    reward: int = 300_000

    discovered_by: Optional[str] = None
    discovered_at: Optional[str] = None

    # سرنخ می‌تواند اعتبار متفاوتی داشته باشد
    reliability: str = "normal"

    def to_dict(self) -> dict:
        return {
            "id": self.clue_id,
            "title": self.title,
            "description": self.description,
            "evidence_id": self.evidence_id,
            "reward": self.reward,
            "discovered_by": self.discovered_by,
            "discovered_at": self.discovered_at,
            "reliability": self.reliability,
        }


class EvidenceSystem:
    """
    مدیریت مدارک، سرنخ‌ها و ارتباط بین آن‌ها.
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

    CATEGORIES = {
        "photo",
        "document",
        "phone",
        "medical",
        "fingerprint",
        "cctv",
        "object",
        "financial",
        "digital",
        "testimony",
        "other",
    }

    def __init__(self):
        self.evidence: Dict[str, Evidence] = {}
        self.clues: Dict[str, Clue] = {}

        self._load_default_evidence()

    # ---------------------------------------------------------
    # زمان
    # ---------------------------------------------------------

    @staticmethod
    def now() -> str:
        return datetime.now(TEHRAN_TZ).isoformat()

    # ---------------------------------------------------------
    # مدارک
    # ---------------------------------------------------------

    def add_evidence(
        self,
        evidence_id: str,
        title: str,
        category: str,
        description: str,
        location_id: str,
        discovered_by: Optional[str] = None,
        reliability: str = "normal",
        confidential: bool = False,
        needs_analysis: bool = False,
        details: Optional[dict] = None,
    ) -> Evidence:

        if evidence_id in self.evidence:
            raise ValueError("این شناسه مدرک قبلاً ثبت شده است.")

        if category not in self.CATEGORIES:
            category = "other"

        if reliability not in self.RELIABILITY_LEVELS:
            reliability = "normal"

        evidence = Evidence(
            evidence_id=evidence_id,
            title=title,
            category=category,
            description=description,
            location_id=location_id,
            discovered_by=discovered_by,
            reliability=reliability,
            confidential=confidential,
            needs_analysis=needs_analysis,
            details=details or {},
            discovered_at=self.now() if discovered_by else None,
        )

        self.evidence[evidence_id] = evidence
        return evidence

    def get_evidence(self, evidence_id: str) -> Optional[Evidence]:
        return self.evidence.get(evidence_id)

    def discover_evidence(
        self,
        evidence_id: str,
        player_id: str,
    ) -> Optional[Evidence]:

        evidence = self.get_evidence(evidence_id)

        if not evidence:
            return None

        if evidence.discovered_by is None:
            evidence.discovered_by = player_id
            evidence.discovered_at = self.now()

        return evidence

    def analyze_evidence(
        self,
        evidence_id: str,
        analysis: dict,
    ) -> Optional[Evidence]:

        evidence = self.get_evidence(evidence_id)

        if not evidence:
            return None

        evidence.details.update(analysis)
        evidence.needs_analysis = False

        return evidence

    # ---------------------------------------------------------
    # تغییر اعتبار مدرک
    # ---------------------------------------------------------

    def set_reliability(
        self,
        evidence_id: str,
        reliability: str,
    ) -> Optional[Evidence]:

        if reliability not in self.RELIABILITY_LEVELS:
            raise ValueError("سطح اعتبار نامعتبر است.")

        evidence = self.get_evidence(evidence_id)

        if not evidence:
            return None

        evidence.reliability = reliability
        return evidence

    # ---------------------------------------------------------
    # سرنخ‌ها
    # ---------------------------------------------------------

    def add_clue(
        self,
        clue_id: str,
        title: str,
        description: str,
        evidence_id: Optional[str] = None,
        reward: int = 300_000,
        reliability: str = "normal",
    ) -> Clue:

        if clue_id in self.clues:
            raise ValueError("این شناسه سرنخ قبلاً ثبت شده است.")

        if evidence_id and evidence_id not in self.evidence:
            raise ValueError("مدرک مربوط به این سرنخ وجود ندارد.")

        if reliability not in self.RELIABILITY_LEVELS:
            reliability = "normal"

        clue = Clue(
            clue_id=clue_id,
            title=title,
            description=description,
            evidence_id=evidence_id,
            reward=reward,
            reliability=reliability,
        )

        self.clues[clue_id] = clue
        return clue

    def get_clue(self, clue_id: str) -> Optional[Clue]:
        return self.clues.get(clue_id)

    def discover_clue(
        self,
        clue_id: str,
        player_id: str,
    ) -> Optional[Clue]:

        clue = self.get_clue(clue_id)

        if not clue:
            return None

        if clue.discovered_by is None:
            clue.discovered_by = player_id
            clue.discovered_at = self.now()

        return clue

    # ---------------------------------------------------------
    # جستجو
    # ---------------------------------------------------------

    def evidence_by_location(
        self,
        location_id: str,
    ) -> List[Evidence]:

        return [
            item
            for item in self.evidence.values()
            if item.location_id == location_id
        ]

    def evidence_by_category(
        self,
        category: str,
    ) -> List[Evidence]:

        return [
            item
            for item in self.evidence.values()
            if item.category == category
        ]

    def discovered_evidence(self) -> List[Evidence]:
        return [
            item
            for item in self.evidence.values()
            if item.discovered_by is not None
        ]

    def discovered_clues(self) -> List[Clue]:
        return [
            item
            for item in self.clues.values()
            if item.discovered_by is not None
        ]

    # ---------------------------------------------------------
    # ارتباط مدارک
    # ---------------------------------------------------------

    def related_evidence(
        self,
        evidence_id: str,
    ) -> List[Evidence]:

        target = self.get_evidence(evidence_id)

        if not target:
            return []

        related = []

        for item in self.evidence.values():
            if item.evidence_id == evidence_id:
                continue

            # ارتباط از طریق شناسه‌هایی که در details ذخیره شده
            related_ids = item.details.get("related_evidence", [])

            if evidence_id in related_ids:
                related.append(item)

        return related

    # ---------------------------------------------------------
    # وضعیت عمومی
    # ---------------------------------------------------------

    def public_state(self) -> dict:
        return {
            "evidence": [
                item.to_dict()
                for item in self.discovered_evidence()
                if not item.confidential
            ],
            "clues": [
                item.to_dict()
                for item in self.discovered_clues()
            ],
            "total_evidence": len(self.evidence),
            "total_clues": len(self.clues),
        }

    # ---------------------------------------------------------
    # مدارک اولیه پرونده
    # ---------------------------------------------------------

    def _load_default_evidence(self):

        self.add_evidence(
            evidence_id="ev_victim_phone",
            title="موبایل قربانی",
            category="phone",
            description="موبایل آرمان نیک‌فر که در صحنه پیدا شده است.",
            location_id="victim_home",
            needs_analysis=True,
            details={
                "owner_phone": "09389861648",
                "locked": True,
                "related_evidence": [],
            },
        )

        self.add_evidence(
            evidence_id="ev_blood_report",
            title="گزارش اولیه پزشکی قانونی",
            category="medical",
            description="گزارش اولیه وضعیت جسد قربانی.",
            location_id="hospital",
            confidential=True,
            needs_analysis=True,
            details={
                "cause_of_death": "نامشخص",
                "estimated_time": "نامشخص",
                "related_evidence": [],
            },
        )

        self.add_evidence(
            evidence_id="ev_photo",
            title="عکس مشکوک",
            category="photo",
            description="عکسی که در اتاق قربانی پیدا شده و بخشی از تصویر عمداً مخدوش است.",
            location_id="victim_home",
            needs_analysis=True,
            details={
                "faces_identified": [],
                "location_identified": False,
                "related_evidence": [],
            },
        )

        self.add_evidence(
            evidence_id="ev_bank_record",
            title="تراکنش بانکی مشکوک",
            category="financial",
            description="یک تراکنش غیرعادی در حساب قربانی.",
            location_id="central_bank",
            confidential=True,
            needs_analysis=True,
            details={
                "amount": None,
                "recipient": None,
                "related_evidence": [],
            },
        )

        self.add_evidence(
            evidence_id="ev_cctv_fragment",
            title="بخشی از فیلم دوربین",
            category="cctv",
            description="یک قطعه کوتاه از فیلم دوربین شهری.",
            location_id="central_square",
            needs_analysis=True,
            details={
                "timestamp": None,
                "vehicle_plate": None,
                "person_identified": None,
                "related_evidence": [],
            },
        )

        self.add_clue(
            clue_id="clue_victim_phone",
            title="شماره تلفن قربانی",
            description="شماره ثبت‌شده روی موبایل قربانی می‌تواند مسیر جستجوی هویت را باز کند.",
            evidence_id="ev_victim_phone",
        )

        self.add_clue(
            clue_id="clue_bank_transaction",
            title="ردپای مالی",
            description="یک تراکنش غیرعادی می‌تواند ارتباط مالی قربانی با فرد دیگری را مشخص کند.",
            evidence_id="ev_bank_record",
        )

        self.add_clue(
            clue_id="clue_cctv",
            title="ردپای دوربین",
            description="بخشی از فیلم دوربین ممکن است زمان یا مسیر حرکت یک فرد را مشخص کند.",
            evidence_id="ev_cctv_fragment",
        )


# نمونه موتور مستقل
evidence_system = EvidenceSystem()
