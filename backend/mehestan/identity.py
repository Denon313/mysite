"""
Mehestan Identity & Verification System
سیستم هویت و اعتبارسنجی شهر مهستان
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import re


@dataclass
class IdentityRecord:
    person_id: str
    first_name: str
    last_name: str
    phone: str

    age: Optional[int] = None
    job: str = ""

    address: str = ""
    current_location: str = ""

    criminal_record: List[str] = field(default_factory=list)
    license_plates: List[str] = field(default_factory=list)

    # اطلاعات قابل مشاهده برای عموم
    public_notes: List[str] = field(default_factory=list)

    # اطلاعات حساس که ممکن است قفل باشند
    confidential: Dict[str, str] = field(default_factory=dict)

    # وضعیت اعتبار اطلاعات
    phone_verified: bool = False
    identity_verified: bool = False

    # بعضی اطلاعات ممکن است قدیمی باشند
    outdated_fields: List[str] = field(default_factory=list)

    # بعضی اطلاعات ممکن است عمداً مخفی باشند
    blocked_fields: List[str] = field(default_factory=list)

    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def to_public_dict(self) -> dict:
        return {
            "person_id": self.person_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name(),
            "phone": self.phone,
            "age": self.age,
            "job": self.job,
            "address": self.address,
            "current_location": self.current_location,
            "criminal_record": list(self.criminal_record),
            "license_plates": list(self.license_plates),
            "public_notes": list(self.public_notes),
            "phone_verified": self.phone_verified,
            "identity_verified": self.identity_verified,
            "outdated_fields": list(self.outdated_fields),
            "blocked_fields": list(self.blocked_fields),
        }


@dataclass
class VerificationResult:
    success: bool
    query_type: str
    message: str
    confidence: int = 0
    records: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "query_type": self.query_type,
            "message": self.message,
            "confidence": self.confidence,
            "records": self.records,
        }


class IdentitySystem:
    """
    سیستم مرکزی شناسایی افراد.

    مسیرهای جست‌وجو:
    - شماره تلفن
    - نام
    - نام خانوادگی
    - پلاک
    - آدرس
    - محل فعلی
    - شناسه فرد
    """

    def __init__(self):
        self.records: Dict[str, IdentityRecord] = {}
        self._load_default_records()

    # =========================================================
    # نرمال‌سازی
    # =========================================================

    @staticmethod
    def normalize_phone(phone: str) -> str:
        """
        یکسان‌سازی شماره تلفن.
        """

        if not phone:
            return ""

        phone = str(phone).strip()

        # حذف فاصله و کاراکترهای اضافی
        phone = re.sub(r"[\s\-\(\)]", "", phone)

        # تبدیل +98 به 0
        if phone.startswith("+98"):
            phone = "0" + phone[3:]

        # تبدیل 0098 به 0
        if phone.startswith("0098"):
            phone = "0" + phone[4:]

        return phone

    @staticmethod
    def normalize_text(value: str) -> str:
        if not value:
            return ""

        return (
            str(value)
            .strip()
            .lower()
            .replace("ي", "ی")
            .replace("ك", "ک")
        )

    @staticmethod
    def normalize_plate(plate: str) -> str:
        if not plate:
            return ""

        return (
            str(plate)
            .strip()
            .replace(" ", "")
            .replace("-", "")
            .replace("ـ", "")
        )

    # =========================================================
    # داده‌های پیش‌فرض
    # =========================================================

    def _load_default_records(self) -> None:

        records = [

            IdentityRecord(
                person_id="npc_victim_001",
                first_name="آرمان",
                last_name="نیک‌فر",
                phone="09389861648",
                age=38,
                job="مدیر شرکت بازرگانی",
                address="خیابان ولیعصر، کوچه ۱۲",
                current_location="victim_home",
                criminal_record=[],
                license_plates=[
                    "م12-345-67",
                ],
                public_notes=[
                    "ساکن قدیمی مهستان",
                    "مدیر یک شرکت بازرگانی",
                ],
                confidential={
                    "financial_status": "بدهی قابل توجه",
                    "private_meeting": "قرار محرمانه در هتل",
                },
                phone_verified=True,
                identity_verified=True,
            ),

            IdentityRecord(
                person_id="npc_reza_001",
                first_name="رضا",
                last_name="کاظمی",
                phone="09121234567",
                age=41,
                job="شریک تجاری",
                address="بخش قدیمی شهر",
                current_location="old_city",
                criminal_record=[],
                license_plates=[
                    "ب45-821-13",
                ],
                public_notes=[
                    "شریک تجاری آرمان",
                ],
                confidential={
                    "financial_problem": "مشکلات مالی",
                },
                phone_verified=True,
                identity_verified=True,
            ),

            IdentityRecord(
                person_id="npc_sara_001",
                first_name="سارا",
                last_name="مرادی",
                phone="09351234567",
                age=29,
                job="خبرنگار",
                address="هتل مهستان",
                current_location="hotel",
                criminal_record=[],
                license_plates=[],
                public_notes=[
                    "خبرنگار روزنامه مهستان",
                ],
                confidential={
                    "private_source": "یک منبع ناشناس",
                    "relationship": "رابطه پنهانی با قربانی",
                },
                phone_verified=True,
                identity_verified=True,
            ),

            IdentityRecord(
                person_id="npc_farhad_001",
                first_name="فرهاد",
                last_name="یوسفی",
                phone="09199876543",
                age=52,
                job="افسر پلیس",
                address="بخش قدیمی شهر",
                current_location="police_station",
                criminal_record=[],
                license_plates=[
                    "پ77-441-21",
                ],
                public_notes=[
                    "افسر کلانتری مرکزی",
                ],
                confidential={
                    "old_case": "پرونده قدیمی و حل‌نشده",
                },
                phone_verified=True,
                identity_verified=True,
            ),

            IdentityRecord(
                person_id="npc_mina_001",
                first_name="مینا",
                last_name="رضایی",
                phone="09211234567",
                age=34,
                job="پزشک",
                address="بیمارستان مرکزی",
                current_location="hospital",
                criminal_record=[],
                license_plates=[],
                public_notes=[
                    "پزشک بیمارستان مرکزی",
                ],
                confidential={
                    "medical_access": "دسترسی به سوابق پزشکی",
                },
                phone_verified=True,
                identity_verified=True,
            ),

            IdentityRecord(
                person_id="npc_ali_001",
                first_name="علی",
                last_name="حیدری",
                phone="09134567890",
                age=27,
                job="کارمند پمپ بنزین",
                address="بخش قدیمی شهر",
                current_location="gas_station",
                criminal_record=[],
                license_plates=[],
                public_notes=[
                    "کارمند شیفت شب",
                ],
                confidential={
                    "unreported_shift": "یک شیفت ثبت‌نشده",
                },
                phone_verified=True,
                identity_verified=True,
            ),
        ]

        for record in records:
            self.records[record.person_id] = record

    # =========================================================
    # ثبت هویت جدید
    # =========================================================

    def add_record(self, record: IdentityRecord) -> bool:

        if record.person_id in self.records:
            return False

        self.records[record.person_id] = record
        return True

    # =========================================================
    # دریافت رکورد
    # =========================================================

    def get_record(
        self,
        person_id: str,
    ) -> Optional[IdentityRecord]:

        return self.records.get(person_id)

    # =========================================================
    # جستجو با شماره تلفن
    # =========================================================

    def search_phone(
        self,
        phone: str,
    ) -> VerificationResult:

        normalized = self.normalize_phone(phone)

        for record in self.records.values():

            if self.normalize_phone(record.phone) == normalized:

                return VerificationResult(
                    success=True,
                    query_type="phone",
                    message="شماره تلفن شناسایی شد.",
                    confidence=100,
                    records=[
                        record.to_public_dict()
                    ],
                )

        return VerificationResult(
            success=False,
            query_type="phone",
            message="شماره‌ای با این مشخصات پیدا نشد.",
            confidence=0,
        )

    # =========================================================
    # جستجو با نام
    # =========================================================

    def search_name(
        self,
        query: str,
    ) -> VerificationResult:

        normalized = self.normalize_text(query)

        matches = []

        for record in self.records.values():

            full_name = self.normalize_text(
                record.full_name()
            )

            if normalized in full_name:

                matches.append(
                    record.to_public_dict()
                )

        return VerificationResult(
            success=bool(matches),
            query_type="name",
            message=(
                "افراد مرتبط پیدا شدند."
                if matches
                else "فردی با این نام پیدا نشد."
            ),
            confidence=90 if matches else 0,
            records=matches,
        )

    # =========================================================
    # جستجو با پلاک
    # =========================================================

    def search_plate(
        self,
        plate: str,
    ) -> VerificationResult:

        normalized = self.normalize_plate(plate)

        matches = []

        for record in self.records.values():

            for record_plate in record.license_plates:

                if self.normalize_plate(record_plate) == normalized:

                    matches.append(
                        record.to_public_dict()
                    )

        return VerificationResult(
            success=bool(matches),
            query_type="license_plate",
            message=(
                "پلاک به یک فرد مرتبط شد."
                if matches
                else "پلاکی با این مشخصات پیدا نشد."
            ),
            confidence=100 if matches else 0,
            records=matches,
        )

    # =========================================================
    # جستجو با آدرس
    # =========================================================

    def search_address(
        self,
        address: str,
    ) -> VerificationResult:

        normalized = self.normalize_text(address)

        matches = []

        for record in self.records.values():

            record_address = self.normalize_text(
                record.address
            )

            if normalized in record_address:

                matches.append(
                    record.to_public_dict()
                )

        return VerificationResult(
            success=bool(matches),
            query_type="address",
            message=(
                "افراد مرتبط با این آدرس پیدا شدند."
                if matches
                else "موردی برای این آدرس پیدا نشد."
            ),
            confidence=85 if matches else 0,
            records=matches,
        )

    # =========================================================
    # جستجو بر اساس محل
    # =========================================================

    def search_location(
        self,
        location_id: str,
    ) -> VerificationResult:

        matches = []

        for record in self.records.values():

            if record.current_location == location_id:

                matches.append(
                    record.to_public_dict()
                )

        return VerificationResult(
            success=bool(matches),
            query_type="location",
            message=(
                "افراد حاضر در این مکان پیدا شدند."
                if matches
                else "فرد ثبت‌شده‌ای در این مکان پیدا نشد."
            ),
            confidence=80 if matches else 0,
            records=matches,
        )

    # =========================================================
    # بررسی اطلاعات محرمانه
    # =========================================================

    def get_confidential(
        self,
        person_id: str,
        field_name: str,
        access_level: str = "normal",
    ) -> VerificationResult:

        record = self.get_record(person_id)

        if record is None:

            return VerificationResult(
                success=False,
                query_type="confidential",
                message="هویت پیدا نشد.",
            )

        if field_name in record.blocked_fields:

            return VerificationResult(
                success=False,
                query_type="confidential",
                message="این اطلاعات مسدود شده است.",
                confidence=0,
            )

        if field_name not in record.confidential:

            return VerificationResult(
                success=False,
                query_type="confidential",
                message="اطلاعات محرمانه‌ای برای این مورد ثبت نشده.",
                confidence=0,
            )

        # سطح دسترسی فعلاً ساده است.
        if access_level not in (
            "normal",
            "police",
            "admin",
            "hacker",
        ):

            return VerificationResult(
                success=False,
                query_type="confidential",
                message="سطح دسترسی نامعتبر است.",
            )

        value = record.confidential[field_name]

        return VerificationResult(
            success=True,
            query_type="confidential",
            message="اطلاعات محرمانه بازیابی شد.",
            confidence=95,
            records=[
                {
                    "person_id": person_id,
                    "field": field_name,
                    "value": value,
                }
            ],
        )

    # =========================================================
    # تغییر وضعیت اطلاعات
    # =========================================================

    def mark_outdated(
        self,
        person_id: str,
        field_name: str,
    ) -> bool:

        record = self.get_record(person_id)

        if record is None:
            return False

        if field_name not in record.outdated_fields:

            record.outdated_fields.append(
                field_name
            )

        return True

    def block_field(
        self,
        person_id: str,
        field_name: str,
    ) -> bool:

        record = self.get_record(person_id)

        if record is None:
            return False

        if field_name not in record.blocked_fields:

            record.blocked_fields.append(
                field_name
            )

        return True

    # =========================================================
    # ثبت سابقه کیفری
    # =========================================================

    def add_criminal_record(
        self,
        person_id: str,
        record_text: str,
    ) -> bool:

        record = self.get_record(person_id)

        if record is None:
            return False

        if record_text not in record.criminal_record:

            record.criminal_record.append(
                record_text
            )

        return True

    # =========================================================
    # ثبت پلاک
    # =========================================================

    def add_license_plate(
        self,
        person_id: str,
        plate: str,
    ) -> bool:

        record = self.get_record(person_id)

        if record is None:
            return False

        normalized = self.normalize_plate(plate)

        if normalized not in [
            self.normalize_plate(item)
            for item in record.license_plates
        ]:

            record.license_plates.append(
                plate
            )

        return True

    # =========================================================
    # لیست عمومی
    # =========================================================

    def public_list(self) -> List[dict]:

        return [
            record.to_public_dict()
            for record in self.records.values()
        ]

    # =========================================================
    # تعداد افراد
    # =========================================================

    def count(self) -> int:
        return len(self.records)


identity_system = IdentitySystem()
