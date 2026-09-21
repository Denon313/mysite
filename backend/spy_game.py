# -*- coding: utf-8 -*-

import random
import re
import threading
import time
from dataclasses import dataclass, field


DISCUSSION_MIN = 10
DISCUSSION_MAX = 1800
VOTING_SECONDS = 10
MIN_PLAYERS = 3
MAX_PLAYERS = 5


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
    "کفگیر",
]


WORD_ALIASES = {
    "کفگیر": [
        "ملاقه",
        "کف گیر",
        "کفگیر",
        "کفگیر آشپزی",
        "ابزار آشپزی",
        "قاشق آشپزی",
    ],
    "فرودگاه": [
        "هواپیما",
        "ترمینال",
        "فرود",
        "پرواز",
        "فرودگاه بین المللی",
    ],
    "بیمارستان": [
        "درمانگاه",
        "دکتر",
        "پزشک",
        "بیمار",
        "کلینیک",
        "درمان",
    ],
    "رستوران": [
        "غذاخوری",
        "غذا",
        "کافه",
        "رستوران داری",
    ],
    "سینما": [
        "فیلم",
        "سالن سینما",
        "فیلم سینمایی",
        "تماشا",
    ],
    "مدرسه": [
        "کلاس",
        "دانش آموز",
        "معلم",
    ],
    "هتل": [
        "مسافرخانه",
        "اقامتگاه",
        "اتاق",
        "مسافر",
    ],
    "استادیوم": [
        "ورزشگاه",
        "ورزش",
        "فوتبال",
        "زمین فوتبال",
    ],
    "کتابخانه": [
        "کتاب",
        "مطالعه",
        "کتاب خوانی",
    ],
    "پارک": [
        "بوستان",
        "فضای سبز",
        "باغ",
    ],
    "موزه": [
        "نمایشگاه",
        "آثار",
        "تاریخی",
        "تاریخ",
    ],
    "ایستگاه قطار": [
        "قطار",
        "راه آهن",
        "ریل",
        "ایستگاه",
    ],
    "فروشگاه": [
        "مغازه",
        "مارکت",
        "خرید",
        "فروش",
        "سوپرمارکت",
    ],
    "دانشگاه": [
        "دانشکده",
        "دانشجو",
        "استاد",
        "کلاس",
    ],
    "آکواریوم": [
        "ماهی",
        "آبزی",
        "آبزیان",
        "ماهی ها",
    ],
    "کشتی": [
        "ناو",
        "قایق",
        "دریا",
        "کشتی دریایی",
    ],
    "قلعه": [
        "دژ",
        "قصر",
        "حصار",
        "قلعه تاریخی",
    ],
    "آزمایشگاه": [
        "لابراتوار",
        "آزمایش",
        "پژوهش",
    ],
    "بانک": [
        "بانکداری",
        "پول",
        "حساب",
        "عابر بانک",
    ],
    "رادیو": [
        "صدا",
        "رادیویی",
        "موج",
    ],
}


def normalize_text(value):
    if value is None:
        return ""

    value = str(value).strip().lower()

    replacements = {
        "ي": "ی",
        "ى": "ی",
        "ك": "ک",
        "ۀ": "ه",
        "ة": "ه",
        "ؤ": "و",
        "إ": "ا",
        "أ": "ا",
        "ٱ": "ا",
        "\u200c": "",
        "\u200d": "",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    value = re.sub(r"\s+", " ", value)

    return value.strip()


def compact_text(value):
    return normalize_text(value).replace(" ", "")


def is_close_guess(secret_word, guess):
    secret = normalize_text(secret_word)
    guess = normalize_text(guess)

    if not secret or not guess:
        return False

    if secret == guess:
        return True

    if compact_text(secret) == compact_text(guess):
        return True

    aliases = WORD_ALIASES.get(secret, [])

    normalized_aliases = {
        normalize_text(item)
        for item in aliases
    }

    if guess in normalized_aliases:
        return True

    if compact_text(secret) in compact_text(guess):
        return True

    return False


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

    guess_pending: bool = False
    spy_guess: str = ""

    lock: threading.RLock = field(
        default_factory=threading.RLock
    )

    def add_player(self, username):
        username = str(username or "").strip()

        if not username:
            return False, "نام کاربری نامعتبر است."

        with self.lock:
            if self.phase != "lobby":
                if username in self.players:
                    self.players[username].connected = True
                    return True, "بازیکن دوباره متصل شد."

                return False, "بازی شروع شده است."

            if username in self.players:
                self.players[username].connected = True
                return True, "بازیکن دوباره متصل شد."

            if len(self.players) >= MAX_PLAYERS:
                return False, "ظرفیت بازی تکمیل است."

            self.players[username] = SpyPlayer(
                username=username
            )

            return True, "بازیکن اضافه شد."

    def disconnect_player(self, username):
        with self.lock:
            player = self.players.get(username)

            if player:
                player.connected = False

    def start(self, discussion_seconds):
        with self.lock:
            if self.phase != "lobby":
                return False, "بازی قبلاً شروع شده است."

            if self.host not in self.players:
                return False, "مدیر داخل بازی نیست."

            count = len(self.players)

            if count < MIN_PLAYERS:
                return False, f"حداقل {MIN_PLAYERS} بازیکن لازم است."

            if count > MAX_PLAYERS:
                return False, "تعداد بازیکنان بیش از حد مجاز است."

            try:
                discussion_seconds = int(
                    discussion_seconds
                )
            except (TypeError, ValueError):
                discussion_seconds = 120

            discussion_seconds = max(
                DISCUSSION_MIN,
                min(
                    DISCUSSION_MAX,
                    discussion_seconds
                )
            )

            usernames = list(self.players.keys())

            self.spy_username = random.choice(
                usernames
            )

            self.secret_word = random.choice(
                SPY_WORDS
            )

            for username, player in self.players.items():
                player.role = (
                    "spy"
                    if username == self.spy_username
                    else "citizen"
                )
                player.voted = False

            self.discussion_seconds = discussion_seconds
            self.phase = "discussion"
            self.phase_ends_at = (
                time.time() + discussion_seconds
            )

            self.votes.clear()
            self.result.clear()

            self.guess_pending = False
            self.spy_guess = ""

            return True, "بازی شروع شد."

    def start_voting(self):
        with self.lock:
            if self.phase != "discussion":
                return False

            self.phase = "voting"

            self.phase_ends_at = (
                time.time() + VOTING_SECONDS
            )

            self.votes.clear()

            for player in self.players.values():
                player.voted = False

            return True

    def cast_vote(self, voter, target):
        with self.lock:
            if self.phase != "voting":
                return False, "زمان رأی‌گیری نیست."

            if voter not in self.players:
                return False, "بازیکن معتبر نیست."

            if target not in self.players:
                return False, "بازیکن انتخاب‌شده وجود ندارد."

            if voter == target:
                return False, "نمی‌توانید به خودتان رأی بدهید."

            # رأی جدید جای رأی قبلی را می‌گیرد.
            self.votes[voter] = target
            self.players[voter].voted = True

            return True, "رأی شما ثبت شد."

    def submit_spy_guess(self, username, guess):
        with self.lock:
            if self.phase != "discussion":
                return False, "در این مرحله امکان حدس کلمه وجود ندارد."

            if username != self.spy_username:
                return False, "فقط جاسوس می‌تواند کلمه را حدس بزند."

            if self.guess_pending:
                return False, "حدس شما قبلاً ارسال شده است."

            guess = str(guess or "").strip()

            if not guess:
                return False, "لطفاً کلمه را وارد کنید."

            if len(guess) > 100:
                return False, "حدس واردشده بیش از حد طولانی است."

            self.spy_guess = guess
            self.guess_pending = True

            correct = is_close_guess(
                self.secret_word,
                guess
            )

            self.result = {
                "winner": (
                    "spy"
                    if correct
                    else "citizens"
                ),
                "reason": "spy_guess",
                "spy": self.spy_username,
                "secret_word": self.secret_word,
                "spy_guess": guess,
                "correct": correct,
            }

            # حدس جاسوس پایان قطعی بازی است.
            self.phase = "finished"
            self.phase_ends_at = 0

            return True, dict(self.result)

    def finish(self):
        with self.lock:
            if self.phase == "finished":
                return dict(self.result)

            if self.phase not in (
                "voting",
                "discussion"
            ):
                return dict(self.result)

            counts = {}

            for target in self.votes.values():
                counts[target] = (
                    counts.get(target, 0) + 1
                )

            if not counts:
                winner = "spy"
                eliminated = None

            else:
                highest = max(
                    counts.values()
                )

                candidates = [
                    username
                    for username, count
                    in counts.items()
                    if count == highest
                ]

                # تساوی = برد جاسوس
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
                "reason": "voting",
                "spy": self.spy_username,
                "eliminated": eliminated,
                "votes": dict(counts),
                "secret_word": self.secret_word,
            }

            self.phase = "finished"
            self.phase_ends_at = 0

            return dict(self.result)

    def tick(self):
        with self.lock:
            if self.phase == "discussion":
                if time.time() >= self.phase_ends_at:
                    self.start_voting()
                    return "voting"

                return "discussion"

            if self.phase == "voting":
                if time.time() >= self.phase_ends_at:
                    self.finish()
                    return "finished"

                return "voting"

            return self.phase

    def public_state(self, username=None):
        with self.lock:
            remaining = 0

            if self.phase_ends_at:
                remaining = max(
                    0,
                    int(
                        self.phase_ends_at
                        - time.time()
                    )
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
                "host": self.host,
                "phase": self.phase,
                "phase_ends_at": self.phase_ends_at,
                "remaining_seconds": remaining,
                "discussion_seconds": self.discussion_seconds,
                "voting_seconds": VOTING_SECONDS,
                "players": players,
                "guess_pending": self.guess_pending,
            }

            if username in self.players:
                player = self.players[username]

                state["my_role"] = player.role

                if player.role == "citizen":
                    state["secret_word"] = self.secret_word
                else:
                    state["secret_word"] = None

            if self.phase == "finished":
                state["result"] = dict(
                    self.result
                )

            return state


class SpyGameManager:
    def __init__(self):
        self.games = {}
        self.lock = threading.RLock()

    def create(self, game_id, host):
        with self.lock:
            existing = self.games.get(game_id)

            if existing:
                return existing

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
            self.games.pop(
                game_id,
                None
            )


spy_manager = SpyGameManager()


def create_game(game_id, host):
    return spy_manager.create(
        game_id,
        host
    )


def get_game(game_id):
    return spy_manager.get(
        game_id
    )


def add_player(game_id, username):
    game = get_game(game_id)

    if not game:
        return False, "بازی پیدا نشد."

    return game.add_player(
        username
    )


def start_game(game_id, discussion_seconds):
    game = get_game(game_id)

    if not game:
        return False, "بازی پیدا نشد."

    return game.start(
        discussion_seconds
    )


def vote(game_id, voter, target):
    game = get_game(game_id)

    if not game:
        return False, "بازی پیدا نشد."

    return game.cast_vote(
        voter,
        target
    )


def spy_guess(game_id, username, guess):
    game = get_game(game_id)

    if not game:
        return False, "بازی پیدا نشد."

    return game.submit_spy_guess(
        username,
        guess
    )


def get_state(game_id, username=None):
    game = get_game(game_id)

    if not game:
        return None

    return game.public_state(
        username
    )


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
    spy_manager.delete(
        game_id
    )
