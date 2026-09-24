"""
Mehestan NPC System
سیستم شخصیت‌ها و NPCهای شهر مهستان
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
from zoneinfo import ZoneInfo


TEHRAN_TZ = ZoneInfo("Asia/Tehran")


@dataclass
class Relationship:
    target_id: str
    relation: str
    strength: int = 50
    secret: bool = False
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "target_id": self.target_id,
            "relation": self.relation,
            "strength": self.strength,
            "secret": self.secret,
            "description": self.description,
        }


@dataclass
class NPC:
    id: str
    first_name: str
    last_name: str
    age: int
    job: str
    phone: str

    home_location: str
    work_location: str

    personality: List[str] = field(default_factory=list)

    knows: List[str] = field(default_factory=list)
    does_not_know: List[str] = field(default_factory=list)

    secrets: List[str] = field(default_factory=list)

    lies: Dict[str, str] = field(default_factory=dict)

    relationships: List[Relationship] = field(default_factory=list)

    current_location: str = ""
    last_known_location: str = ""

    criminal_record: List[str] = field(default_factory=list)

    is_alive: bool = True

    # اطلاعاتی که عمداً از کارآگاه مخفی هستند
    confidential: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not self.current_location:
            self.current_location = self.home_location

        if not self.last_known_location:
            self.last_known_location = self.current_location

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def add_relationship(
        self,
        target_id: str,
        relation: str,
        strength: int = 50,
        secret: bool = False,
        description: str = "",
    ) -> None:

        self.relationships.append(
            Relationship(
                target_id=target_id,
                relation=relation,
                strength=strength,
                secret=secret,
                description=description,
            )
        )

    def knows_fact(self, fact: str) -> bool:
        return fact in self.knows

    def does_not_know_fact(self, fact: str) -> bool:
        return fact in self.does_not_know

    def has_secret(self, secret_id: str) -> bool:
        return secret_id in self.secrets

    def get_lie(self, topic: str) -> Optional[str]:
        return self.lies.get(topic)

    def to_public_dict(self) -> dict:
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "age": self.age,
            "job": self.job,
            "phone": self.phone,
            "home_location": self.home_location,
            "work_location": self.work_location,
            "current_location": self.current_location,
            "last_known_location": self.last_known_location,
            "is_alive": self.is_alive,
        }

    def to_private_dict(self) -> dict:
        data = self.to_public_dict()

        data.update(
            {
                "personality": list(self.personality),
                "knows": list(self.knows),
                "does_not_know": list(self.does_not_know),
                "secrets": list(self.secrets),
                "lies": dict(self.lies),
                "relationships": [
                    relationship.to_dict()
                    for relationship in self.relationships
                ],
                "criminal_record": list(self.criminal_record),
                "confidential": dict(self.confidential),
            }
        )

        return data


class MehestanNPCSystem:
    """
    مدیریت NPCهای مهستان.

    این سیستم فعلاً اطلاعات شخصیت‌ها را نگه می‌دارد.
    موتور گفت‌وگوی آزاد در dialogue.py به آن متصل خواهد شد.
    """

    def __init__(self):
        self.npcs: Dict[str, NPC] = {}
        self._load_default_npcs()

    # ---------------------------------------------------------
    # NPCهای اصلی پرونده اول
    # ---------------------------------------------------------

    def _load_default_npcs(self) -> None:

        victim = NPC(
            id="npc_victim_001",
            first_name="آرمان",
            last_name="نیک‌فر",
            age=38,
            job="مدیر شرکت بازرگانی",
            phone="09389861648",
            home_location="victim_home",
            work_location="city_hall",
            personality=[
                "دقیق",
                "کم‌حرف",
                "کنترل‌گر",
            ],
            knows=[
                "business_partner_conflict",
                "bank_transaction_001",
                "hotel_meeting_001",
            ],
            does_not_know=[
                "anonymous_sender_identity",
            ],
            secrets=[
                "secret_debt",
                "hidden_business_deal",
            ],
            relationships=[
                Relationship(
                    target_id="npc_reza_001",
                    relation="business_partner",
                    strength=75,
                    secret=False,
                    description="شریک تجاری",
                ),
                Relationship(
                    target_id="npc_sara_001",
                    relation="secret_relationship",
                    strength=80,
                    secret=True,
                    description="رابطه‌ای که از اطرافیان پنهان کرده بود",
                ),
            ],
            criminal_record=[],
            confidential={
                "financial_status": "بدهی قابل توجه",
                "private_meeting": "قرار محرمانه در هتل",
            },
        )

        reza = NPC(
            id="npc_reza_001",
            first_name="رضا",
            last_name="کاظمی",
            age=41,
            job="شریک تجاری",
            phone="09121234567",
            home_location="old_city",
            work_location="city_hall",
            personality=[
                "اجتماعی",
                "زودعصبانی",
                "باهوش",
            ],
            knows=[
                "victim_debt",
                "business_partner_conflict",
                "victim_last_meeting",
            ],
            does_not_know=[
                "secret_relationship",
            ],
            secrets=[
                "financial_problem",
            ],
            lies={
                "victim_argument": (
                    "من و آرمان آن شب هیچ بحثی با هم نداشتیم."
                ),
            },
            relationships=[
                Relationship(
                    target_id="npc_victim_001",
                    relation="business_partner",
                    strength=75,
                    description="شریک تجاری آرمان",
                ),
            ],
            criminal_record=[],
        )

        sara = NPC(
            id="npc_sara_001",
            first_name="سارا",
            last_name="مرادی",
            age=29,
            job="خبرنگار",
            phone="09351234567",
            home_location="hotel",
            work_location="newspaper",
            personality=[
                "کنجکاو",
                "باهوش",
                "محتاط",
            ],
            knows=[
                "victim_secret_meeting",
                "hotel_meeting_001",
            ],
            does_not_know=[
                "murder_method",
            ],
            secrets=[
                "secret_relationship",
                "private_source",
            ],
            lies={
                "relationship_with_victim": (
                    "من فقط برای کار با آرمان در ارتباط بودم."
                ),
            },
            relationships=[
                Relationship(
                    target_id="npc_victim_001",
                    relation="secret_relationship",
                    strength=80,
                    secret=True,
                    description="رابطه پنهانی",
                ),
            ],
            criminal_record=[],
        )

        farhad = NPC(
            id="npc_farhad_001",
            first_name="فرهاد",
            last_name="یوسفی",
            age=52,
            job="افسر پلیس",
            phone="09199876543",
            home_location="old_city",
            work_location="police_station",
            personality=[
                "جدی",
                "قانون‌مدار",
                "کم‌حرف",
            ],
            knows=[
                "victim_criminal_background",
                "police_report_001",
                "crime_scene_001",
            ],
            does_not_know=[
                "secret_relationship",
            ],
            secrets=[
                "old_case",
            ],
            relationships=[],
            criminal_record=[],
        )

        mina = NPC(
            id="npc_mina_001",
            first_name="مینا",
            last_name="رضایی",
            age=34,
            job="پزشک",
            phone="09211234567",
            home_location="hospital",
            work_location="hospital",
            personality=[
                "آرام",
                "دقیق",
                "ملاحظه‌کار",
            ],
            knows=[
                "victim_medical_history",
                "victim_last_visit",
            ],
            does_not_know=[
                "killer_identity",
                "murder_method",
            ],
            secrets=[
                "medical_record_access",
            ],
            relationships=[],
            criminal_record=[],
        )

        ali = NPC(
            id="npc_ali_001",
            first_name="علی",
            last_name="حیدری",
            age=27,
            job="کارمند پمپ بنزین",
            phone="09134567890",
            home_location="old_city",
            work_location="gas_station",
            personality=[
                "خجالتی",
                "دقیق",
                "مشاهده‌گر",
            ],
            knows=[
                "car_seen_at_gas_station",
                "license_plate_001",
            ],
            does_not_know=[
                "victim_identity",
            ],
            secrets=[
                "unreported_night_shift",
            ],
            relationships=[],
            criminal_record=[],
        )

        # ثبت روابط متقابل
        victim.add_relationship(
            "npc_reza_001",
            "business_partner",
            75,
        )

        victim.add_relationship(
            "npc_sara_001",
            "secret_relationship",
            80,
            secret=True,
        )

        reza.add_relationship(
            "npc_victim_001",
            "business_partner",
            75,
        )

        sara.add_relationship(
            "npc_victim_001",
            "secret_relationship",
            80,
            secret=True,
        )

        self.npcs = {
            victim.id: victim,
            reza.id: reza,
            sara.id: sara,
            farhad.id: farhad,
            mina.id: mina,
            ali.id: ali,
        }

    # ---------------------------------------------------------
    # دریافت NPC
    # ---------------------------------------------------------

    def get_npc(self, npc_id: str) -> Optional[NPC]:
        return self.npcs.get(npc_id)

    # ---------------------------------------------------------
    # جستجو با شماره تلفن
    # ---------------------------------------------------------

    def find_by_phone(self, phone: str) -> Optional[NPC]:

        normalized = phone.replace(" ", "").replace("-", "")

        for npc in self.npcs.values():
            if npc.phone == normalized:
                return npc

        return None

    # ---------------------------------------------------------
    # جستجو با نام
    # ---------------------------------------------------------

    def search_by_name(self, query: str) -> List[dict]:

        query = query.strip().lower()

        results = []

        for npc in self.npcs.values():

            full_name = npc.full_name.lower()

            if (
                query in npc.first_name.lower()
                or query in npc.last_name.lower()
                or query in full_name
            ):
                results.append(npc.to_public_dict())

        return results

    # ---------------------------------------------------------
    # جستجو بر اساس محل کار
    # ---------------------------------------------------------

    def find_by_workplace(self, location_id: str) -> List[dict]:

        return [
            npc.to_public_dict()
            for npc in self.npcs.values()
            if npc.work_location == location_id
        ]

    # ---------------------------------------------------------
    # جستجو بر اساس محل فعلی
    # ---------------------------------------------------------

    def find_at_location(self, location_id: str) -> List[dict]:

        return [
            npc.to_public_dict()
            for npc in self.npcs.values()
            if npc.current_location == location_id
            and npc.is_alive
        ]

    # ---------------------------------------------------------
    # تغییر مکان NPC
    # ---------------------------------------------------------

    def move_npc(
        self,
        npc_id: str,
        location_id: str,
    ) -> bool:

        npc = self.get_npc(npc_id)

        if npc is None:
            return False

        npc.current_location = location_id
        npc.last_known_location = location_id

        return True

    # ---------------------------------------------------------
    # روابط یک NPC
    # ---------------------------------------------------------

    def get_relationships(self, npc_id: str) -> List[dict]:

        npc = self.get_npc(npc_id)

        if npc is None:
            return []

        return [
            relationship.to_dict()
            for relationship in npc.relationships
        ]

    # ---------------------------------------------------------
    # بررسی دانسته NPC
    # ---------------------------------------------------------

    def npc_knows(self, npc_id: str, fact: str) -> bool:

        npc = self.get_npc(npc_id)

        if npc is None:
            return False

        return npc.knows_fact(fact)

    # ---------------------------------------------------------
    # دریافت دروغ مرتبط با موضوع
    # ---------------------------------------------------------

    def get_npc_lie(
        self,
        npc_id: str,
        topic: str,
    ) -> Optional[str]:

        npc = self.get_npc(npc_id)

        if npc is None:
            return None

        return npc.get_lie(topic)

    # ---------------------------------------------------------
    # افزودن NPC جدید
    # ---------------------------------------------------------

    def add_npc(self, npc: NPC) -> bool:

        if npc.id in self.npcs:
            return False

        self.npcs[npc.id] = npc
        return True

    # ---------------------------------------------------------
    # حذف NPC
    # ---------------------------------------------------------

    def remove_npc(self, npc_id: str) -> bool:

        if npc_id not in self.npcs:
            return False

        del self.npcs[npc_id]
        return True

    # ---------------------------------------------------------
    # لیست عمومی NPCها
    # ---------------------------------------------------------

    def public_list(self) -> List[dict]:

        return [
            npc.to_public_dict()
            for npc in self.npcs.values()
        ]

    # ---------------------------------------------------------
    # لیست داخلی برای موتور بازی
    # ---------------------------------------------------------

    def private_list(self) -> List[dict]:

        return [
            npc.to_private_dict()
            for npc in self.npcs.values()
        ]

    # ---------------------------------------------------------
    # تعداد NPCها
    # ---------------------------------------------------------

    def count(self) -> int:
        return len(self.npcs)


mehestan_npcs = MehestanNPCSystem()
