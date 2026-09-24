"""
Mehestan Mystery Case
Economy System — سیستم اقتصاد و پاداش
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
import uuid


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Transaction:
    transaction_id: str
    player_id: str
    amount: int
    transaction_type: str
    description: str
    balance_after: int
    created_at: str = field(default_factory=now_iso)
    metadata: Dict = field(default_factory=dict)

    def public_state(self) -> Dict:
        return {
            "id": self.transaction_id,
            "player_id": self.player_id,
            "amount": self.amount,
            "type": self.transaction_type,
            "description": self.description,
            "balance_after": self.balance_after,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


class EconomySystem:
    """
    سیستم اقتصاد مهستان.

    قوانین اصلی:
    - هر سرنخ پیش‌فرض: 300,000 تومان
    - موجودی هر بازیکن جداست
    - پرداخت باج از موجودی شخصی انجام می‌شود
    - تمام تغییرات موجودی ثبت می‌شوند
    """

    DEFAULT_CLUE_REWARD = 300_000

    TRANSACTION_TYPES = {
        "clue_reward",
        "case_reward",
        "bonus",
        "ransom_payment",
        "purchase",
        "penalty",
        "admin",
        "adjustment",
        "refund",
    }

    def __init__(self):

        self.balances: Dict[str, int] = {}

        self.transactions: List[Transaction] = []

        self.player_stats: Dict[str, Dict] = {}

    # ---------------------------------------------------------
    # Player
    # ---------------------------------------------------------

    def register_player(
        self,
        player_id: str,
        starting_balance: int = 0,
    ) -> int:

        if player_id not in self.balances:

            self.balances[player_id] = max(
                0,
                int(starting_balance),
            )

            self.player_stats[player_id] = {
                "clues_found": 0,
                "clue_rewards": 0,
                "case_rewards": 0,
                "ransom_paid": 0,
                "total_earned": 0,
                "total_spent": 0,
            }

        return self.balances[player_id]

    def remove_player(
        self,
        player_id: str,
    ):

        self.balances.pop(
            player_id,
            None,
        )

        self.player_stats.pop(
            player_id,
            None,
        )

    # ---------------------------------------------------------
    # Balance
    # ---------------------------------------------------------

    def get_balance(
        self,
        player_id: str,
    ) -> int:

        self.register_player(player_id)

        return self.balances[player_id]

    def set_balance(
        self,
        player_id: str,
        amount: int,
        description: str = "تنظیم موجودی",
    ) -> int:

        self.register_player(player_id)

        old_balance = self.balances[player_id]

        amount = max(
            0,
            int(amount),
        )

        difference = amount - old_balance

        self.balances[player_id] = amount

        if difference != 0:

            self._record_transaction(
                player_id=player_id,
                amount=difference,
                transaction_type="adjustment",
                description=description,
            )

        return amount

    # ---------------------------------------------------------
    # Add Money
    # ---------------------------------------------------------

    def add_money(
        self,
        player_id: str,
        amount: int,
        transaction_type: str = "bonus",
        description: str = "افزایش موجودی",
        metadata: Optional[Dict] = None,
    ) -> Dict:

        self.register_player(player_id)

        amount = int(amount)

        if amount <= 0:

            return {
                "success": False,
                "reason": "invalid_amount",
                "balance": self.balances[player_id],
            }

        if transaction_type not in self.TRANSACTION_TYPES:

            transaction_type = "bonus"

        self.balances[player_id] += amount

        stats = self.player_stats[player_id]

        stats["total_earned"] += amount

        if transaction_type == "clue_reward":
            stats["clue_rewards"] += amount

        elif transaction_type == "case_reward":
            stats["case_rewards"] += amount

        self._record_transaction(
            player_id=player_id,
            amount=amount,
            transaction_type=transaction_type,
            description=description,
            metadata=metadata,
        )

        return {
            "success": True,
            "amount": amount,
            "balance": self.balances[player_id],
        }

    # ---------------------------------------------------------
    # Spend Money
    # ---------------------------------------------------------

    def spend_money(
        self,
        player_id: str,
        amount: int,
        transaction_type: str = "purchase",
        description: str = "هزینه",
        metadata: Optional[Dict] = None,
    ) -> Dict:

        self.register_player(player_id)

        amount = int(amount)

        if amount <= 0:

            return {
                "success": False,
                "reason": "invalid_amount",
                "balance": self.balances[player_id],
            }

        if self.balances[player_id] < amount:

            return {
                "success": False,
                "reason": "insufficient_balance",
                "balance": self.balances[player_id],
            }

        if transaction_type not in self.TRANSACTION_TYPES:

            transaction_type = "purchase"

        self.balances[player_id] -= amount

        stats = self.player_stats[player_id]

        stats["total_spent"] += amount

        if transaction_type == "ransom_payment":
            stats["ransom_paid"] += amount

        self._record_transaction(
            player_id=player_id,
            amount=-amount,
            transaction_type=transaction_type,
            description=description,
            metadata=metadata,
        )

        return {
            "success": True,
            "amount": amount,
            "balance": self.balances[player_id],
        }

    # ---------------------------------------------------------
    # Clue Reward
    # ---------------------------------------------------------

    def reward_clue(
        self,
        player_id: str,
        clue_id: str,
        amount: int = DEFAULT_CLUE_REWARD,
        description: str = "پاداش کشف سرنخ",
    ) -> Dict:

        self.register_player(player_id)

        if amount <= 0:

            amount = self.DEFAULT_CLUE_REWARD

        result = self.add_money(
            player_id=player_id,
            amount=amount,
            transaction_type="clue_reward",
            description=description,
            metadata={
                "clue_id": clue_id,
            },
        )

        if result["success"]:

            self.player_stats[player_id][
                "clues_found"
            ] += 1

        return result

    # ---------------------------------------------------------
    # Case Reward
    # ---------------------------------------------------------

    def reward_case(
        self,
        player_id: str,
        amount: int,
        description: str = "پاداش پایان پرونده",
    ) -> Dict:

        return self.add_money(
            player_id=player_id,
            amount=amount,
            transaction_type="case_reward",
            description=description,
        )

    # ---------------------------------------------------------
    # Ransom
    # ---------------------------------------------------------

    def pay_ransom(
        self,
        player_id: str,
        amount: int,
        hostage_event_id: str,
    ) -> Dict:

        return self.spend_money(
            player_id=player_id,
            amount=amount,
            transaction_type="ransom_payment",
            description="پرداخت سهم باج گروگان",
            metadata={
                "hostage_event_id": hostage_event_id,
            },
        )

    # ---------------------------------------------------------
    # Refund
    # ---------------------------------------------------------

    def refund(
        self,
        player_id: str,
        amount: int,
        description: str = "بازگشت وجه",
        metadata: Optional[Dict] = None,
    ) -> Dict:

        return self.add_money(
            player_id=player_id,
            amount=amount,
            transaction_type="refund",
            description=description,
            metadata=metadata,
        )

    # ---------------------------------------------------------
    # Transactions
    # ---------------------------------------------------------

    def _record_transaction(
        self,
        player_id: str,
        amount: int,
        transaction_type: str,
        description: str,
        metadata: Optional[Dict] = None,
    ) -> Transaction:

        transaction = Transaction(
            transaction_id=f"tx_{uuid.uuid4().hex[:10]}",
            player_id=player_id,
            amount=amount,
            transaction_type=transaction_type,
            description=description,
            balance_after=self.balances[player_id],
            metadata=metadata or {},
        )

        self.transactions.append(transaction)

        if len(self.transactions) > 1000:

            self.transactions = self.transactions[-1000:]

        return transaction

    def get_transactions(
        self,
        player_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Transaction]:

        result = self.transactions

        if player_id:

            result = [
                tx
                for tx in result
                if tx.player_id == player_id
            ]

        return result[-limit:]

    # ---------------------------------------------------------
    # Stats
    # ---------------------------------------------------------

    def get_stats(
        self,
        player_id: str,
    ) -> Dict:

        self.register_player(player_id)

        return {
            **self.player_stats[player_id],
            "balance": self.balances[player_id],
        }

    # ---------------------------------------------------------
    # Leaderboard
    # ---------------------------------------------------------

    def leaderboard(self) -> List[Dict]:

        result = []

        for player_id, balance in self.balances.items():

            stats = self.player_stats.get(
                player_id,
                {},
            )

            result.append(
                {
                    "player_id": player_id,
                    "balance": balance,
                    "total_earned": stats.get(
                        "total_earned",
                        0,
                    ),
                    "clues_found": stats.get(
                        "clues_found",
                        0,
                    ),
                }
            )

        result.sort(
            key=lambda item: item["balance"],
            reverse=True,
        )

        return result

    # ---------------------------------------------------------
    # Public State
    # ---------------------------------------------------------

    def public_state(
        self,
        player_id: str,
    ) -> Dict:

        self.register_player(player_id)

        return {
            "player_id": player_id,
            "balance": self.get_balance(player_id),
            "stats": self.get_stats(player_id),
            "transactions": [
                tx.public_state()
                for tx in self.get_transactions(
                    player_id,
                    50,
                )
            ],
        }


def create_demo_economy() -> EconomySystem:

    economy = EconomySystem()

    players = [
        ("mehdi", 1_000_000),
        ("rastin", 1_000_000),
        ("amirali", 1_000_000),
        ("mahna", 1_000_000),
        ("fatemeh", 1_000_000),
    ]

    for player_id, balance in players:

        economy.register_player(
            player_id,
            balance,
        )

    economy.reward_clue(
        player_id="mehdi",
        clue_id="clue_victim_phone",
    )

    economy.reward_clue(
        player_id="rastin",
        clue_id="clue_cctv",
    )

    economy.pay_ransom(
        player_id="mehdi",
        amount=500_000,
        hostage_event_id="hostage_demo",
    )

    return economy


if __name__ == "__main__":

    economy = create_demo_economy()

    print("=== Mehestan Economy System ===")

    print(
        "Mehdi balance:",
        economy.get_balance("mehdi"),
    )

    print(
        "Mehdi stats:",
        economy.get_stats("mehdi"),
    )

    print(
        "Transactions:",
        len(economy.get_transactions("mehdi")),
    )
