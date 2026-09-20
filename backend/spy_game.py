# -*- coding: utf-8 -*-

import random
import threading
import time
from dataclasses import dataclass, field


DISCUSSION_MIN = 10
DISCUSSION_MAX = 1800
VOTING_SECONDS = 10
MAX_PLAYERS = 5
MIN_PLAYERS = 3


@dataclass
class SpyPlayer:
    username: str
    role: str = ""
    connected: bool = True
    voted: bool = False


@dataclass
class SpyGame:
    game_id: str
    host: str
    players: dict = field(default_factory=dict)

    phase: str = "lobby"
    discussion_seconds: int = 120
    phase_ends_at: float = 0

    secret_word: str = ""
    spy_username: str = ""

    votes: dict = field(default_factory=dict)
    result: dict = field(default_factory=dict)

    lock: threading.Lock = field(default_factory=threading.Lock)

    def add_player(self, username):
        with self.lock:
            if self.phase != "lobby":
                return False, "بازی شروع شده است."

            if username in self.players:
                self.players[username].connected = True
                return True, "بازیکن دوباره متصل شد."

            if len(self.players) >= MAX_PLAYERS:
                return False, "ظرفیت بازی تکمیل است."

            self.players[username] = SpyPlayer(username=username)
            return True, "بازیکن اضافه شد."

    def remove_player(self, username):
        with self.lock:
            if username in self.players:
                self.players[username].connected = False

    def start(self, discussion_seconds, words):
        with self.lock:
            if self.host not in self.players:
                return False, "مدیر داخل بازی نیست."

            count = len(self.players)

            if count < MIN_PLAYERS:
                return False, f"حداقل {MIN_PLAYERS} بازیکن لازم است."

            if count > MAX_PLAYERS:
                return False, "تعداد بازیکنان بیش از حد مجاز است."

            try:
                discussion_seconds = int(discussion_seconds)
            except (TypeError, ValueError):
                return False, "زمان نامعتبر است."

            discussion_seconds = max(
                DISCUSSION_MIN,
                min(DISCUSSION_MAX, discussion_seconds)
            )

            usernames = list(self.players.keys())

            self.spy_username = random.choice(usernames)

            self.secret_word = random.choice(words)

            for username, player in self.players.items():
                player.role = (
                    "spy"
                    if username == self.spy_username
                    else "citizen"
                )
                player.voted = False

            self.discussion_seconds = discussion_seconds
            self.phase = "discussion"
            self.phase_ends_at = time.time() + discussion_seconds

            self.votes.clear()
            self.result.clear()

            return True, "بازی شروع شد."

    def cast_vote(self, voter, target):
        with self.lock:
            if self.phase != "voting":
                return False, "زمان رأی‌گیری نیست."

            if voter not in self.players:
                return False, "بازیکن معتبر نیست."

            if target not in self.players:
                return False, "بازیکن انتخاب‌شده وجود ندارد."

            if voter in self.votes:
                return False, "شما قبلاً رأی داده‌اید."

            if voter == target:
                return False, "نمی‌توانید به خودتان رأی بدهید."

            self.votes[voter] = target
            self.players[voter].voted = True

            return True, "رأی ثبت شد."

    def start_voting(self):
        with self.lock:
            if self.phase != "discussion":
                return False

            self.phase = "voting"
            self.phase_ends_at = time.time() + VOTING_SECONDS

            self.votes.clear()

            for player in self.players.values():
                player.voted = False

            return True

    def finish(self):
        with self.lock:
            if self.phase not in ("voting", "discussion"):
                return self.result

            counts = {}

            for target in self.votes.values():
                counts[target] = counts.get(target, 0) + 1

            if not counts:
                winner = "spy"
                eliminated = None

            else:
                highest = max(counts.values())

                candidates = [
                    username
                    for username, count in counts.items()
                    if count == highest
                ]

                if len(candidates) != 1:
                    winner = "spy"
                    eliminated = None
                else:
                    eliminated = candidates[0]

                    if eliminated == self.spy_username:
                        winner = "citizens"
                    else:
                        winner = "spy"

            self.result = {
                "winner": winner,
                "spy": self.spy_username,
                "eliminated": eliminated,
                "votes": dict(counts),
            }

            self.phase = "finished"
            self.phase_ends_at = 0

            return self.result

    def tick(self):
        with self.lock:
            if self.phase == "discussion":
                if time.time() >= self.phase_ends_at:
                    self.phase = "voting"
                    self.phase_ends_at = (
                        time.time() + VOTING_SECONDS
                    )

                    self.votes.clear()

                    for player in self.players.values():
                        player.voted = False

                    return "voting"

            elif self.phase == "voting":
                if time.time() >= self.phase_ends_at:
                    self.finish()
                    return "finished"

            return self.phase

    def public_state(self, username=None):
        with self.lock:
            remaining = 0

            if self.phase_ends_at:
                remaining = max(
                    0,
                    int(self.phase_ends_at - time.time())
                )

            players = []

            for player in self.players.values():
                players.append({
                    "username": player.username,
                    "connected": player.connected,
                    "voted": (
                        player.username in self.votes
                        if self.phase == "voting"
                        else False
                    ),
                })

            state = {
                "game_id": self.game_id,
                "phase": self.phase,
                "phase_ends_at": self.phase_ends_at,
                "remaining_seconds": remaining,
                "discussion_seconds": self.discussion_seconds,
                "voting_seconds": VOTING_SECONDS,
                "players": players,
            }

            if username in self.players:
                player = self.players[username]

                state["my_role"] = player.role

                if player.role == "citizen":
                    state["secret_word"] = self.secret_word
                else:
                    state["secret_word"] = None

            if self.phase == "finished":
                state["result"] = dict(self.result)

            return state


class SpyGameManager:

    def __init__(self):
        self.games = {}
        self.lock = threading.Lock()

    def create(self, game_id, host):
        with self.lock:
            game = SpyGame(
                game_id=game_id,
                host=host
            )

            self.games[game_id] = game

            return game

    def get(self, game_id):
        with self.lock:
            return self.games.get(game_id)

    def delete(self, game_id):
        with self.lock:
            self.games.pop(game_id, None)


SPY_WORDS = [
    "فرودگاه",
    "بیمارستان",
    "رستوران",
    "سینما",
    "مدرسه",
    "هتل",
    "استادیوم",
    "کتابخانه",
    "پارک",
    "موزه",
    "ایستگاه قطار",
    "فروشگاه",
    "دانشگاه",
    "آکواریوم",
    "کشتی",
    "قلعه",
    "آزمایشگاه",
    "بانک",
    "رادیو",
]


spy_manager = SpyGameManager()


def create_game(game_id, host):
    return spy_manager.create(game_id, host)


def get_game(game_id):
    return spy_manager.get(game_id)


def add_player(game_id, username):
    game = get_game(game_id)

    if not game:
        return False, "بازی پیدا نشد."

    return game.add_player(username)


def start_game(game_id, discussion_seconds):
    game = get_game(game_id)

    if not game:
        return False, "بازی پیدا نشد."

    return game.start(
        discussion_seconds,
        SPY_WORDS
    )


def vote(game_id, voter, target):
    game = get_game(game_id)

    if not game:
        return False, "بازی پیدا نشد."

    return game.cast_vote(
        voter,
        target
    )


def get_state(game_id, username=None):
    game = get_game(game_id)

    if not game:
        return None

    return game.public_state(username)


def tick_game(game_id):
    game = get_game(game_id)

    if not game:
        return None

    return game.tick()


def finish_game(game_id):
    game = get_game(game_id)

    if not game:
        return None

    return game.finish()


def remove_game(game_id):
    spy_manager.delete(game_id)
