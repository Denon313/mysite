# -*- coding: utf-8 -*-

"""
Game Room - Spy Game Engine
Server Authoritative Spy Game

مراحل بازی:
lobby
starting
discussion
voting
vote_result
spy_guess
finished
"""

import random
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from flask_socketio import join_room, leave_room, emit


# ============================================================
# CONFIG
# ============================================================

MIN_PLAYERS = 3
MAX_PLAYERS = 5

DEFAULT_DISCUSSION_SECONDS = 120
MIN_DISCUSSION_SECONDS = 10
MAX_DISCUSSION_SECONDS = 1800

VOTING_SECONDS = 10
STARTING_SECONDS = 3

MAX_CHAT_MESSAGE_LENGTH = 1000


# ============================================================
# WORD BANK
# ============================================================

# فعلاً موتور بازی مستقل از دیتابیس کلمات است.
# بعداً پنل ادمین را به بانک دیتابیس وصل می‌کنیم.
WORD_BANK = [
    {
        "word": "فرودگاه",
        "aliases": ["مطار", "airport", "فرودگاه بین المللی"],
    },
    {
        "word": "بیمارستان",
        "aliases": ["شفاخانه", "hospital", "درمانگاه"],
    },
    {
        "word": "رستوران",
        "aliases": ["غذاخوری", "restaurant", "مطعم"],
    },
    {
        "word": "سینما",
        "aliases": ["cinema", "فیلم", "سالن سینما"],
    },
    {
        "word": "مدرسه",
        "aliases": ["دبیرستان", "school", "مدرسه تحصیلی"],
    },
    {
        "word": "هتل",
        "aliases": ["hotel", "مهمانسرا"],
    },
    {
        "word": "استادیوم",
        "aliases": ["ورزشگاه", "stadium", "ورزشگاه فوتبال"],
    },
    {
        "word": "کتابخانه",
        "aliases": ["library", "کتاب خانه"],
    },
    {
        "word": "پارک",
        "aliases": ["بوستان", "park"],
    },
    {
        "word": "موزه",
        "aliases": ["museum"],
    },
    {
        "word": "ایستگاه قطار",
        "aliases": ["راه آهن", "راه‌آهن", "قطار", "train station"],
    },
    {
        "word": "فروشگاه",
        "aliases": ["مغازه", "shop", "store", "مارکت"],
    },
    {
        "word": "دانشگاه",
        "aliases": ["university", "دانشکده"],
    },
    {
        "word": "آکواریوم",
        "aliases": ["aquarium"],
    },
    {
        "word": "کشتی",
        "aliases": ["ناو", "ship", "boat"],
    },
    {
        "word": "قلعه",
        "aliases": ["castle", "دژ"],
    },
    {
        "word": "آزمایشگاه",
        "aliases": ["lab", "laboratory"],
    },
    {
        "word": "بانک",
        "aliases": ["bank"],
    },
    {
        "word": "رادیو",
        "aliases": ["radio"],
    },
    {
        "word": "کفگیر",
        "aliases": [
            "کف گیر",
            "کفگیر آشپزی",
            "ابزار آشپزی",
            "قاشق آشپزی",
            "ملاقه",
            "ملاقه آشپزی",
        ],
    },
    {
        "word": "موبایل",
        "aliases": ["گوشی", "گوشی موبایل", "تلفن همراه", "phone", "smartphone"],
    },
    {
        "word": "تلویزیون",
        "aliases": ["tv", "television", "تلویزیون خانگی"],
    },
    {
        "word": "یخچال",
        "aliases": ["refrigerator", "فریزر"],
    },
    {
        "word": "ماشین",
        "aliases": ["خودرو", "اتومبیل", "car", "ماشین سواری"],
    },
    {
        "word": "موتورسیکلت",
        "aliases": ["موتور", "موتورسیکلت", "motorcycle"],
    },
    {
        "word": "دوچرخه",
        "aliases": ["bicycle", "bike"],
    },
    {
        "word": "هواپیما",
        "aliases": ["plane", "airplane", "طیاره"],
    },
    {
        "word": "اتوبوس",
        "aliases": ["bus"],
    },
    {
        "word": "مترو",
        "aliases": ["metro", "قطار شهری"],
    },
    {
        "word": "تاکسی",
        "aliases": ["taxi"],
    },
    {
        "word": "پمپ بنزین",
        "aliases": ["جایگاه سوخت", "بنزین", "gas station"],
    },
    {
        "word": "سوپرمارکت",
        "aliases": ["سوپر", "مارکت", "supermarket"],
    },
    {
        "word": "نانوایی",
        "aliases": ["نانوا", "نان فروشی", "bakery"],
    },
    {
        "word": "کافی شاپ",
        "aliases": ["کافه", "کافی‌شاپ", "coffee shop", "coffee"],
    },
    {
        "word": "کتاب",
        "aliases": ["book"],
    },
    {
        "word": "دفتر",
        "aliases": ["دفتر کار", "office"],
    },
    {
        "word": "کلاس",
        "aliases": ["class", "کلاس درس"],
    },
    {
        "word": "زمین فوتبال",
        "aliases": ["فوتبال", "زمین بازی", "football field"],
    },
    {
        "word": "استخر",
        "aliases": ["pool", "شنا"],
    },
    {
        "word": "ساحل",
        "aliases": ["دریا", "کنار دریا", "beach"],
    },
    {
        "word": "جنگل",
        "aliases": ["forest"],
    },
    {
        "word": "کوه",
        "aliases": ["mountain"],
    },
    {
        "word": "جزیره",
        "aliases": ["island"],
    },
    {
        "word": "بیابان",
        "aliases": ["کویر", "desert"],
    },
    {
        "word": "هوا",
        "aliases": ["آب و هوا", "weather"],
    },
    {
        "word": "باران",
        "aliases": ["rain"],
    },
    {
        "word": "برف",
        "aliases": ["snow"],
    },
    {
        "word": "چتر",
        "aliases": ["umbrella"],
    },
    {
        "word": "کفش",
        "aliases": ["shoe", "کتانی"],
    },
    {
        "word": "لباس",
        "aliases": ["clothes", "پوشاک"],
    },
    {
        "word": "کلاه",
        "aliases": ["hat", "cap"],
    },
    {
        "word": "عینک",
        "aliases": ["glasses"],
    },
    {
        "word": "ساعت",
        "aliases": ["watch", "clock"],
    },
    {
        "word": "کیف",
        "aliases": ["bag"],
    },
    {
        "word": "چمدان",
        "aliases": ["suitcase", "بار سفر"],
    },
    {
        "word": "آشپزخانه",
        "aliases": ["kitchen"],
    },
    {
        "word": "حمام",
        "aliases": ["bathroom", "دوش"],
    },
    {
        "word": "اتاق خواب",
        "aliases": ["خواب", "bedroom"],
    },
    {
        "word": "میز",
        "aliases": ["table"],
    },
    {
        "word": "صندلی",
        "aliases": ["chair"],
    },
    {
        "word": "تخت خواب",
        "aliases": ["تخت", "bed"],
    },
    {
        "word": "چراغ",
        "aliases": ["لامپ", "light", "lamp"],
    },
    {
        "word": "پنجره",
        "aliases": ["window"],
    },
    {
        "word": "در",
        "aliases": ["درب", "door"],
    },
    {
        "word": "کلید",
        "aliases": ["key"],
    },
    {
        "word": "قفل",
        "aliases": ["lock"],
    },
    {
        "word": "تلفن",
        "aliases": ["phone", "telephone"],
    },
    {
        "word": "کامپیوتر",
        "aliases": ["رایانه", "computer", "pc"],
    },
    {
        "word": "لپ تاپ",
        "aliases": ["لپ‌تاپ", "laptop", "notebook"],
    },
    {
        "word": "کیبورد",
        "aliases": ["صفحه کلید", "keyboard"],
    },
    {
        "word": "ماوس",
        "aliases": ["mouse"],
    },
    {
        "word": "کنسول بازی",
        "aliases": ["پلی استیشن", "xbox", "playstation", "کنسول"],
    },
    {
        "word": "دسته بازی",
        "aliases": ["کنترلر", "controller", "gamepad"],
    },
    {
        "word": "بازی",
        "aliases": ["game", "گیم"],
    },
    {
        "word": "فیلم",
        "aliases": ["movie", "film"],
    },
    {
        "word": "سریال",
        "aliases": ["series", "tv series"],
    },
    {
        "word": "موسیقی",
        "aliases": ["music"],
    },
    {
        "word": "گیتار",
        "aliases": ["guitar"],
    },
    {
        "word": "پیانو",
        "aliases": ["piano"],
    },
    {
        "word": "میکروفون",
        "aliases": ["microphone", "mic"],
    },
    {
        "word": "دوربین",
        "aliases": ["camera"],
    },
    {
        "word": "عکس",
        "aliases": ["تصویر", "photo", "picture"],
    },
    {
        "word": "آتش نشانی",
        "aliases": ["آتش‌نشانی", "fire station", "آتشنشانی"],
    },
    {
        "word": "پلیس",
        "aliases": ["police", "کلانتری"],
    },
    {
        "word": "دادگاه",
        "aliases": ["court"],
    },
    {
        "word": "زندان",
        "aliases": ["prison", "بازداشتگاه"],
    },
    {
        "word": "داروخانه",
        "aliases": ["pharmacy"],
    },
    {
        "word": "دندانپزشکی",
        "aliases": ["دندان پزشکی", "dentist"],
    },
    {
        "word": "آرایشگاه",
        "aliases": ["سالن زیبایی", "barbershop"],
    },
    {
        "word": "باشگاه",
        "aliases": ["gym", "ورزشگاه"],
    },
    {
        "word": "پارکینگ",
        "aliases": ["parking", "جای پارک"],
    },
    {
        "word": "رستوران فست فود",
        "aliases": ["فست فود", "fast food"],
    },
    {
        "word": "پیتزا",
        "aliases": ["pizza"],
    },
    {
        "word": "همبرگر",
        "aliases": ["burger", "hamburger"],
    },
    {
        "word": "بستنی",
        "aliases": ["ice cream"],
    },
    {
        "word": "کیک",
        "aliases": ["cake"],
    },
    {
        "word": "شکلات",
        "aliases": ["chocolate"],
    },
    {
        "word": "قهوه",
        "aliases": ["coffee"],
    },
    {
        "word": "چای",
        "aliases": ["tea"],
    },
    {
        "word": "نوشابه",
        "aliases": ["soft drink", "soda"],
    },
    {
        "word": "آب",
        "aliases": ["water"],
    },
    {
        "word": "پاییز",
        "aliases": ["autumn", "fall"],
    },
    {
        "word": "تابستان",
        "aliases": ["summer"],
    },
    {
        "word": "زمستان",
        "aliases": ["winter"],
    },
    {
        "word": "بهار",
        "aliases": ["spring"],
    },
]


# ============================================================
# TEXT NORMALIZATION
# ============================================================

CHAR_MAP = str.maketrans(
    {
        "ي": "ی",
        "ى": "ی",
        "ك": "ک",
        "ۀ": "ه",
        "ة": "ه",
        "ؤ": "و",
        "إ": "ا",
        "أ": "ا",
        "ٱ": "ا",
        "ـ": "",
        "‌": " ",
        "‍": " ",
    }
)


def normalize_text(value) -> str:
    if value is None:
        return ""

    value = str(value).strip().lower()
    value = value.translate(CHAR_MAP)

    value = re.sub(r"[\u064B-\u065F\u0670]", "", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def compact_text(value) -> str:
    return re.sub(r"\s+", "", normalize_text(value))


# ============================================================
# GUESS MATCHING
# ============================================================

def levenshtein_distance(a: str, b: str) -> int:
    """
    فاصله Levenshtein ساده برای جلوگیری از وابستگی اضافه.
    """

    a = compact_text(a)
    b = compact_text(b)

    if a == b:
        return 0

    if not a:
        return len(b)

    if not b:
        return len(a)

    if len(a) > len(b):
        a, b = b, a

    previous = list(range(len(a) + 1))

    for j, char_b in enumerate(b, 1):
        current = [j]

        for i, char_a in enumerate(a, 1):
            insert_cost = current[i - 1] + 1
            delete_cost = previous[i] + 1
            replace_cost = previous[i - 1] + (char_a != char_b)

            current.append(
                min(insert_cost, delete_cost, replace_cost)
            )

        previous = current

    return previous[-1]


def similarity_ratio(a: str, b: str) -> float:
    a = compact_text(a)
    b = compact_text(b)

    if not a or not b:
        return 0.0

    distance = levenshtein_distance(a, b)
    maximum = max(len(a), len(b))

    if maximum == 0:
        return 1.0

    return 1.0 - (distance / maximum)


def guess_matches(secret_word: str, guess: str, aliases=None) -> bool:
    """
    تشخیص حدس جاسوس.

    ترتیب بررسی:
    1. دقیق
    2. بدون فاصله
    3. alias
    4. شباهت تایپی
    """

    secret = normalize_text(secret_word)
    value = normalize_text(guess)

    if not secret or not value:
        return False

    if secret == value:
        return True

    if compact_text(secret) == compact_text(value):
        return True

    aliases = aliases or []

    for alias in aliases:
        if value == normalize_text(alias):
            return True

        if compact_text(value) == compact_text(alias):
            return True

    # حدس‌های خیلی کوتاه را fuzzy نمی‌کنیم
    if len(compact_text(value)) >= 4:
        ratio = similarity_ratio(secret, value)

        # برای کلمات کوتاه‌تر سخت‌گیرتر هستیم
        if len(compact_text(secret)) <= 5:
            return ratio >= 0.82

        return ratio >= 0.72

    return False


def choose_secret_word():
    items = None

    if _get_spy_words_callback is not None:
        try:
            items = _get_spy_words_callback()
        except Exception:
            items = None

    if items:
        item = random.choice(items)
        return {
            "word": item["word"],
            "aliases": list(item.get("aliases", [])),
        }

    # پشتیبان موقت؛ اگر دیتابیس خالی یا در دسترس نباشد
    item = random.choice(WORD_BANK)
    return {
        "word": item["word"],
        "aliases": list(item.get("aliases", [])),
    }


# ============================================================
# PLAYER
# ============================================================

@dataclass
class SpyPlayer:
    username: str
    role: str = ""
    connected: bool = True
    vote: Optional[str] = None
    joined_at: float = field(default_factory=time.time)


# ============================================================
# GAME
# ============================================================

@dataclass
class SpyGame:
    game_id: str
    host: str

    players: dict = field(default_factory=dict)

    phase: str = "lobby"

    discussion_seconds: int = DEFAULT_DISCUSSION_SECONDS

    phase_started_at: float = 0
    phase_ends_at: float = 0

    secret_word: str = ""
    secret_aliases: list = field(default_factory=list)

    spy_username: str = ""

    votes: dict = field(default_factory=dict)

    result: dict = field(default_factory=dict)

    created_at: float = field(default_factory=time.time)

    lock: object = field(
        default_factory=threading.RLock,
        repr=False
    )

    timer_thread: object = field(
        default=None,
        repr=False
    )

    timer_stop: bool = False


# ============================================================
# GLOBAL GAME STORAGE
# ============================================================

_games = {}
_games_lock = threading.RLock()

# بازیکنان حاضر در لابی اصلی Spy
spy_lobby_players = []

# callbackهایی که main.py در صورت نیاز تنظیم می‌کند
_socketio = None
_save_chat_callback = None
_get_chat_history_callback = None
_get_socket_username_callback = None
_get_spy_words_callback = None


# ============================================================
# LOBBY
# ============================================================

def get_lobby_players():
    with _games_lock:
        return list(spy_lobby_players)


def add_lobby_player(username):
    username = normalize_text(username)

    if not username:
        return False

    with _games_lock:
        if username in spy_lobby_players:
            return True

        if len(spy_lobby_players) >= MAX_PLAYERS:
            return False

        spy_lobby_players.append(username)

    broadcast_spy_lobby()

    return True


def remove_lobby_player(username):
    username = normalize_text(username)

    with _games_lock:
        if username in spy_lobby_players:
            spy_lobby_players.remove(username)

    broadcast_spy_lobby()


def clear_lobby():
    with _games_lock:
        spy_lobby_players.clear()

    broadcast_spy_lobby()


def broadcast_spy_lobby():
    if _socketio is None:
        return

    try:
        _socketio.emit(
            "spy_lobby",
            {
                "players": get_lobby_players(),
                "count": len(get_lobby_players()),
                "min_players": MIN_PLAYERS,
                "max_players": MAX_PLAYERS,
            },
            room="GAME_ROOM",
        )
    except Exception:
        pass


# ============================================================
# GAME CREATION
# ============================================================

def create_spy_game(
    game_id,
    players,
    host,
    discussion_seconds=DEFAULT_DISCUSSION_SECONDS,
):
    players = list(dict.fromkeys(players))

    if len(players) < MIN_PLAYERS:
        raise ValueError(
            f"حداقل {MIN_PLAYERS} بازیکن لازم است."
        )

    if len(players) > MAX_PLAYERS:
        raise ValueError(
            f"حداکثر {MAX_PLAYERS} بازیکن مجاز است."
        )

    discussion_seconds = int(discussion_seconds)

    discussion_seconds = max(
        MIN_DISCUSSION_SECONDS,
        min(
            MAX_DISCUSSION_SECONDS,
            discussion_seconds,
        ),
    )

    game = SpyGame(
        game_id=game_id,
        host=host,
        discussion_seconds=discussion_seconds,
    )

    for username in players:
        game.players[username] = SpyPlayer(
            username=username,
            role="",
            connected=True,
        )

    with _games_lock:
        _games[game_id] = game

    return game


def get_spy_game(game_id):
    with _games_lock:
        return _games.get(game_id)


def remove_spy_game(game_id):
    with _games_lock:
        game = _games.pop(game_id, None)

    if game:
        game.timer_stop = True

    return game


# ============================================================
# PLAYER MANAGEMENT
# ============================================================

def add_spy_player(game_id, username):
    game = get_spy_game(game_id)

    if not game:
        return False, "بازی پیدا نشد."

    username = normalize_text(username)

    with game.lock:
        if username in game.players:
            game.players[username].connected = True
            return True, None

        if game.phase != "lobby":
            return False, "بازی شروع شده است."

        if len(game.players) >= MAX_PLAYERS:
            return False, "ظرفیت بازی تکمیل است."

        game.players[username] = SpyPlayer(
            username=username,
            connected=True,
        )

    return True, None


def mark_player_connected(game_id, username, connected=True):
    game = get_spy_game(game_id)

    if not game:
        return

    username = normalize_text(username)

    with game.lock:
        player = game.players.get(username)

        if player:
            player.connected = connected


def remove_spy_player(game_id, username):
    game = get_spy_game(game_id)

    if not game:
        return

    username = normalize_text(username)

    with game.lock:
        if game.phase != "lobby":
            if username in game.players:
                game.players[username].connected = False
            return

        game.players.pop(username, None)


# ============================================================
# GAME START
# ============================================================

def start_spy_game(game_id):
    game = get_spy_game(game_id)

    if not game:
        raise ValueError("بازی پیدا نشد.")

    with game.lock:
        if game.phase != "lobby":
            raise ValueError("این بازی قبلاً شروع شده است.")

        connected = [
            player
            for player in game.players.values()
            if player.connected
        ]

        if len(connected) < MIN_PLAYERS:
            raise ValueError(
                f"برای شروع حداقل {MIN_PLAYERS} بازیکن آنلاین لازم است."
            )

        if len(connected) > MAX_PLAYERS:
            raise ValueError(
                f"حداکثر {MAX_PLAYERS} بازیکن مجاز است."
            )

        # انتخاب کلمه روی سرور
        selected = choose_secret_word()

        game.secret_word = selected["word"]
        game.secret_aliases = selected["aliases"]

        # انتخاب جاسوس روی سرور
        spy = random.choice(connected)

        game.spy_username = spy.username

        for player in connected:
            player.vote = None

            if player.username == spy.username:
                player.role = "spy"
            else:
                player.role = "citizen"

        game.votes.clear()
        game.result.clear()

        game.phase = "discussion"

        game.phase_started_at = time.time()

        game.phase_ends_at = (
            game.phase_started_at
            + game.discussion_seconds
        )

    return game


# ============================================================
# PHASE MANAGEMENT
# ============================================================

def start_spy_server_timer(game_id):
    game = get_spy_game(game_id)

    if not game:
        return False

    with game.lock:
        if (
            game.timer_thread
            and game.timer_thread.is_alive()
        ):
            return True

        game.timer_stop = False

        thread = threading.Thread(
            target=_timer_worker,
            args=(game_id,),
            daemon=True,
        )

        game.timer_thread = thread

        thread.start()

    return True


def _timer_worker(game_id):
    while True:
        game = get_spy_game(game_id)

        if not game:
            return

        with game.lock:
            if game.timer_stop:
                return

            phase = game.phase
            ends_at = game.phase_ends_at

        now = time.time()

        if phase == "discussion":
            if now >= ends_at:
                try:
                    start_spy_voting(game_id)
                except Exception:
                    return

                continue

        elif phase == "voting":
            if now >= ends_at:
                try:
                    finish_spy_voting(game_id)
                except Exception:
                    return

                continue

        elif phase in ("finished", "lobby"):
            return

        remaining = max(0, int(ends_at - now))

        _emit_state(game_id)

        if _socketio:
            try:
                _socketio.emit(
                    "spy_tick",
                    {
                        "game_id": game_id,
                        "phase": phase,
                        "remaining": remaining,
                    },
                    room=f"spy:{game_id}",
                )
            except Exception:
                pass

        time.sleep(0.5)


def start_spy_voting(game_id):
    game = get_spy_game(game_id)

    if not game:
        raise ValueError("بازی پیدا نشد.")

    with game.lock:
        if game.phase != "discussion":
            return game

        game.phase = "voting"

        game.phase_started_at = time.time()

        game.phase_ends_at = (
            game.phase_started_at
            + VOTING_SECONDS
        )

        game.votes.clear()

        for player in game.players.values():
            player.vote = None

    _emit_state(game_id)

    if _socketio:
        _socketio.emit(
            "spy_voting_started",
            {
                "game_id": game_id,
                "seconds": VOTING_SECONDS,
            },
            room=f"spy:{game_id}",
        )

    return game


# ============================================================
# VOTING
# ============================================================

def cast_spy_vote(game_id, username, target_username):
    game = get_spy_game(game_id)

    if not game:
        raise ValueError("بازی پیدا نشد.")

    username = normalize_text(username)
    target_username = normalize_text(target_username)

    with game.lock:
        if game.phase != "voting":
            raise ValueError("زمان رأی‌گیری نیست.")

        voter = game.players.get(username)
        target = game.players.get(target_username)

        if not voter:
            raise ValueError("بازیکن پیدا نشد.")

        if not target:
            raise ValueError("بازیکن انتخاب‌شده پیدا نشد.")

        if not voter.connected:
            raise ValueError("بازیکن آفلاین است.")

        if username == target_username:
            raise ValueError("نمی‌توانی به خودت رأی بدهی.")

        # فقط آخرین رأی مهم است.
        old_target = game.votes.get(username)

        if old_target:
            # حذف رأی قبلی در شمارش نهایی
            pass

        game.votes[username] = target_username
        voter.vote = target_username

    _emit_state(game_id)

    return True


def count_votes(game):
    counts = {}

    for target in game.votes.values():
        counts[target] = counts.get(target, 0) + 1

    return counts


def finish_spy_voting(game_id):
    game = get_spy_game(game_id)

    if not game:
        raise ValueError("بازی پیدا نشد.")

    with game.lock:
        if game.phase != "voting":
            return game

        vote_counts = count_votes(game)

        # ========================================================
        # بدون رأی → برد مستقیم جاسوس
        # ========================================================

        if not vote_counts:
            game.phase = "finished"
            game.phase_started_at = time.time()
            game.phase_ends_at = 0

            game.result = {
                "winner": "spy",
                "reason": "no_votes",
                "spy": game.spy_username,
                "secret_word": game.secret_word,
                "eliminated": None,
                "vote_counts": {},
            }

        else:
            maximum = max(vote_counts.values())

            leaders = [
                username
                for username, count in vote_counts.items()
                if count == maximum
            ]

            # ====================================================
            # تساوی → برد مستقیم جاسوس
            # ====================================================

            if len(leaders) != 1:
                game.phase = "finished"
                game.phase_started_at = time.time()
                game.phase_ends_at = 0

                game.result = {
                    "winner": "spy",
                    "reason": "tie",
                    "spy": game.spy_username,
                    "secret_word": game.secret_word,
                    "eliminated": None,
                    "vote_counts": vote_counts,
                }

            else:
                eliminated = leaders[0]

                # ================================================
                # جاسوس پیدا شد → جاسوس فرصت حدس کلمه دارد
                # ================================================

                if eliminated == game.spy_username:
                    game.phase = "spy_guess"
                    game.phase_started_at = time.time()
                    game.phase_ends_at = 0

                    game.result = {
                        "winner": "citizens_pending_guess",
                        "reason": "spy_found",
                        "spy": game.spy_username,
                        "secret_word": game.secret_word,
                        "eliminated": eliminated,
                        "vote_counts": vote_counts,
                    }

                # ================================================
                # شهروند حذف شد → برد جاسوس
                # ================================================

                else:
                    game.phase = "finished"
                    game.phase_started_at = time.time()
                    game.phase_ends_at = 0

                    game.result = {
                        "winner": "spy",
                        "reason": "citizen_eliminated",
                        "spy": game.spy_username,
                        "secret_word": game.secret_word,
                        "eliminated": eliminated,
                        "vote_counts": vote_counts,
                    }

        _emit_state(game_id)
        return game


# ============================================================
# SPY GUESS
# ============================================================

def submit_spy_guess(game_id, username, guess):
    game = get_spy_game(game_id)

    if not game:
        raise ValueError("بازی پیدا نشد.")

    username = normalize_text(username)
    guess = str(guess or "").strip()

    if not guess:
        raise ValueError("حدس نمی‌تواند خالی باشد.")

    if len(guess) > 200:
        raise ValueError("حدس بیش از حد طولانی است.")

    with game.lock:
        if game.phase != "spy_guess":
            raise ValueError("الان زمان حدس جاسوس نیست.")

        if username != game.spy_username:
            raise ValueError("فقط جاسوس می‌تواند حدس بزند.")

        correct = guess_matches(
            game.secret_word,
            guess,
            game.secret_aliases,
        )

        game.phase = "finished"

        game.phase_started_at = time.time()
        game.phase_ends_at = 0

        previous_winner = game.result.get(
            "winner",
            "spy",
        )

        if correct:
            winner = "spy"
            reason = "spy_correct_guess"
        else:
            winner = "citizens"
            reason = "spy_wrong_guess"

        game.result.update(
            {
                "winner": winner,
                "reason": reason,
                "spy": game.spy_username,
                "secret_word": game.secret_word,
                "spy_guess": guess,
                "spy_guess_correct": correct,
                "previous_winner": previous_winner,
            }
        )

    _emit_state(game_id)

    if _socketio:
        _socketio.emit(
            "spy_finished",
            {
                "game_id": game_id,
            },
            room=f"spy:{game_id}",
        )

    return game


# ============================================================
# DISCONNECT / RECONNECT
# ============================================================

def disconnect_spy_player(game_id, username):
    mark_player_connected(
        game_id,
        username,
        False,
    )

    _emit_state(game_id)


def reconnect_spy_player(game_id, username):
    mark_player_connected(
        game_id,
        username,
        True,
    )

    _emit_state(game_id)


# ============================================================
# PUBLIC STATE
# ============================================================

def public_spy_state(game_id, username=None):
    game = get_spy_game(game_id)

    if not game:
        return None

    username = normalize_text(username)

    with game.lock:
        current = game.players.get(username)

        players = []

        for player in game.players.values():
            players.append(
                {
                    "username": player.username,
                    "connected": bool(player.connected),
                    "is_host": player.username == game.host,
                    "voted": player.vote is not None,
                }
            )

        now = time.time()

        if game.phase in ("discussion", "voting"):
            remaining = max(
                0,
                int(game.phase_ends_at - now),
            )
        else:
            remaining = 0

        state = {
            "game_id": game.game_id,
            "phase": game.phase,
            "host": game.host,
            "players": players,
            "count": len(players),
            "min_players": MIN_PLAYERS,
            "max_players": MAX_PLAYERS,
            "discussion_seconds": game.discussion_seconds,
            "remaining": remaining,
            "my_role": (
                current.role
                if current
                else None
            ),
            "my_vote": (
                current.vote
                if current
                else None
            ),
            "can_guess": (
                current is not None
                and username == game.spy_username
                and game.phase == "spy_guess"
            ),
        }

        # فقط شهروندها در زمان بازی کلمه را می‌بینند.
        if (
            current
            and current.role == "citizen"
            and game.phase != "lobby"
        ):
            state["secret_word"] = game.secret_word

        # جاسوس هرگز کلمه را در state عمومی نمی‌گیرد.
        if game.phase == "finished":
            state["result"] = dict(game.result)

        return state


# ============================================================
# SOCKET HELPERS
# ============================================================

def _emit_state(game_id):
    if _socketio is None:
        return

    game = get_spy_game(game_id)

    if not game:
        return

    with game.lock:
        usernames = list(game.players.keys())

    for username in usernames:
        try:
            state = public_spy_state(
                game_id,
                username,
            )

            _socketio.emit(
                "spy_state",
                state,
                room=f"spy_user:{username}",
            )
        except Exception:
            pass

    # state عمومی برای کل اتاق
    try:
        _socketio.emit(
            "spy_state_update",
            {
                "game_id": game_id,
            },
            room=f"spy:{game_id}",
        )
    except Exception:
        pass


def _error(message):
    return {
        "ok": False,
        "error": str(message),
    }


# ============================================================
# SOCKET.IO
# ============================================================

def get_authenticated_socket_username():
    """نام کاربری واقعی متصل به همین Socket را برمی‌گرداند."""
    if _get_socket_username_callback is None:
        return None

    try:
        username = _get_socket_username_callback()
        return normalize_text(username) if username else None
    except Exception:
        return None



def register_spy_socket(
    socketio,
    save_chat_callback=None,
    get_chat_history_callback=None,
    get_socket_username_callback=None,
    get_spy_words_callback=None,
):
    """
    ثبت تمام eventهای بازی Spy.
    """

    global _socketio
    global _save_chat_callback
    global _get_chat_history_callback
    global _get_socket_username_callback
    global _get_spy_words_callback

    _socketio = socketio
    _save_chat_callback = save_chat_callback
    _get_chat_history_callback = get_chat_history_callback
    _get_socket_username_callback = get_socket_username_callback
    _get_spy_words_callback = get_spy_words_callback

    @socketio.on("spy_create")
    def handle_spy_create(data):
        data = data or {}

        game_id = str(
            data.get("game_id")
            or "spy-main-room"
        ).strip()

        username = get_authenticated_socket_username()

        if not username:
            emit(
                "spy_error",
                _error("نشست کاربر معتبر نیست."),
            )
            return

        join_room(f"spy:{game_id}")
        join_room(f"spy_user:{username}")

        game = get_spy_game(game_id)

        if game:
            reconnect_spy_player(
                game_id,
                username,
            )

        emit(
            "spy_created",
            {
                "ok": True,
                "game_id": game_id,
            },
        )


    @socketio.on("spy_join")
    def handle_spy_join(data):
        data = data or {}

        game_id = str(
            data.get("game_id")
            or "spy-main-room"
        ).strip()

        username = get_authenticated_socket_username()

        if not username:
            emit(
                "spy_error",
                _error("نشست کاربر معتبر نیست."),
            )
            return

        game = get_spy_game(game_id)

        if not game:
            try:
                add_lobby_player(username)

                join_room(f"spy:{game_id}")
                join_room(f"spy_user:{username}")

                emit(
                    "spy_joined",
                    {
                        "ok": True,
                        "game_id": game_id,
                        "phase": "lobby",
                    },
                )

                return

            except Exception as exc:
                emit(
                    "spy_error",
                    _error(exc),
                )
                return

        ok, error = add_spy_player(
            game_id,
            username,
        )

        if not ok:
            emit(
                "spy_error",
                _error(error),
            )
            return

        reconnect_spy_player(
            game_id,
            username,
        )

        join_room(f"spy:{game_id}")
        join_room(f"spy_user:{username}")

        emit(
            "spy_joined",
            {
                "ok": True,
                "game_id": game_id,
            },
        )

        state = public_spy_state(
            game_id,
            username,
        )

        emit(
            "spy_state",
            state,
        )


    @socketio.on("spy_leave")
    def handle_spy_leave(data):
        data = data or {}

        game_id = str(
            data.get("game_id")
            or "spy-main-room"
        ).strip()

        username = get_authenticated_socket_username()

        if not username:
            emit(
                "spy_error",
                _error("نشست کاربر معتبر نیست."),
            )
            return

        game = get_spy_game(game_id)

        if game:
            disconnect_spy_player(
                game_id,
                username,
            )

        remove_lobby_player(username)

        leave_room(f"spy:{game_id}")
        leave_room(f"spy_user:{username}")


    @socketio.on("spy_state")
    def handle_spy_state(data):
        data = data or {}

        game_id = str(
            data.get("game_id")
            or "spy-main-room"
        ).strip()

        username = get_authenticated_socket_username()

        if not username:
            emit(
                "spy_error",
                _error("نشست کاربر معتبر نیست."),
            )
            return

        game = get_spy_game(game_id)

        if not game:
            lobby_players = get_lobby_players()

            emit(
                "spy_state",
                {
                    "game_id": game_id,
                    "phase": "lobby",
                    "players": [
                        {
                            "username": p,
                            "connected": True,
                            "is_host": (
                                i == 0
                            ),
                            "voted": False,
                        }
                        for i, p in enumerate(
                            lobby_players
                        )
                    ],
                    "count": len(
                        lobby_players
                    ),
                    "min_players": MIN_PLAYERS,
                    "max_players": MAX_PLAYERS,
                    "remaining": 0,
                    "my_role": None,
                    "my_vote": None,
                    "can_guess": False,
                },
            )
            return

        state = public_spy_state(
            game_id,
            username,
        )

        emit(
            "spy_state",
            state,
        )

    @socketio.on("spy_start")
    def handle_spy_start(data):
        data = data or {}

        game_id = str(
            data.get("game_id")
            or "spy-main-room"
        ).strip()

        username = get_authenticated_socket_username()

        if not username:
            emit(
                "spy_error",
                _error("نشست کاربر معتبر نیست."),
            )
            return

        try:
            discussion_seconds = int(
                data.get(
                    "discussion_seconds",
                    DEFAULT_DISCUSSION_SECONDS,
                )
            )
        except (TypeError, ValueError):
            discussion_seconds = DEFAULT_DISCUSSION_SECONDS

        discussion_seconds = max(
            MIN_DISCUSSION_SECONDS,
            min(
                MAX_DISCUSSION_SECONDS,
                discussion_seconds,
            ),
        )

        game = get_spy_game(game_id)

        if not game:
            players = get_lobby_players()

            if len(players) < MIN_PLAYERS:
                emit(
                    "spy_error",
                    _error(
                        f"حداقل {MIN_PLAYERS} بازیکن لازم است."
                    ),
                )
                return

            if username != players[0]:
                emit(
                    "spy_error",
                    _error(
                        "فقط میزبان می‌تواند بازی را شروع کند."
                    ),
                )
                return

            try:
                game = create_spy_game(
                    game_id,
                    players,
                    username,
                    discussion_seconds,
                )
            except Exception as exc:
                emit(
                    "spy_error",
                    _error(exc),
                )
                return

            clear_lobby()

        else:
            if username != game.host:
                emit(
                    "spy_error",
                    _error(
                        "فقط میزبان می‌تواند بازی را شروع کند."
                    ),
                )
                return

            with game.lock:
                game.discussion_seconds = discussion_seconds

        try:
            start_spy_game(game_id)
            start_spy_server_timer(game_id)

        except Exception as exc:
            emit(
                "spy_error",
                _error(exc),
            )
            return

        socketio.emit(
            "spy_started",
            {
                "game_id": game_id,
            },
            room=f"spy:{game_id}",
        )

        _emit_state(game_id)

    @socketio.on("spy_vote")
    def handle_spy_vote(data):
        data = data or {}

        game_id = str(
            data.get("game_id")
            or ""
        ).strip()

        target = normalize_text(
            data.get("target")
        )

        username = get_authenticated_socket_username()

        if not username:
            emit(
                "spy_error",
                _error("نشست کاربر معتبر نیست."),
            )
            return

        if not game_id or not target:
            emit(
                "spy_error",
                _error("اطلاعات رأی ناقص است."),
            )
            return

        try:
            cast_spy_vote(
                game_id,
                username,
                target,
            )

            emit(
                "spy_vote",
                {
                    "ok": True,
                    "target": target,
                },
            )

        except Exception as exc:
            emit(
                "spy_error",
                _error(exc),
            )

    @socketio.on("spy_guess")
    def handle_spy_guess(data):
        data = data or {}

        game_id = str(
            data.get("game_id")
            or ""
        ).strip()

        guess = str(
            data.get("guess")
            or ""
        ).strip()

        username = get_authenticated_socket_username()

        if not username:
            emit(
                "spy_error",
                _error("نشست کاربر معتبر نیست."),
            )
            return

        if not game_id or not guess:
            emit(
                "spy_error",
                _error("حدس کلمه خالی است."),
            )
            return

        try:
            game = submit_spy_guess(
                game_id,
                username,
                guess,
            )

            emit(
                "spy_guess_result",
                {
                    "ok": True,
                    "correct": bool(
                        game.result.get(
                            "spy_guess_correct"
                        )
                    ),
                },
            )

        except Exception as exc:
            emit(
                "spy_error",
                _error(exc),
            )

    # --------------------------------------------------------
    # CHAT
    # --------------------------------------------------------

    @socketio.on("spy_join_chat")
    def handle_spy_join_chat(data):
        data = data or {}

        game_id = str(
            data.get("game_id")
            or ""
        ).strip()

        username = get_authenticated_socket_username()

        if not game_id or not username:
            emit(
                "spy_error",
                _error("نشست کاربر معتبر نیست."),
            )
            return

        game = get_spy_game(game_id)

        if not game:
            emit(
                "spy_error",
                _error("بازی پیدا نشد."),
            )
            return

        with game.lock:
            if username not in game.players:
                emit(
                    "spy_error",
                    _error("بازیکن عضو این بازی نیست."),
                )
                return

        join_room(f"spy_chat:{game_id}")

        emit(
            "spy_chat_joined",
            {
                "game_id": game_id,
                "username": username,
            },
        )


    @socketio.on("spy_chat_history")
    def handle_spy_chat_history(data):
        data = data or {}

        game_id = str(
            data.get("game_id")
            or ""
        ).strip()

        username = get_authenticated_socket_username()

        if not game_id or not username:
            emit(
                "spy_error",
                _error("نشست کاربر معتبر نیست."),
            )
            return

        game = get_spy_game(game_id)

        if not game:
            emit(
                "spy_error",
                _error("بازی پیدا نشد."),
            )
            return

        with game.lock:
            if username not in game.players:
                emit(
                    "spy_error",
                    _error("بازیکن عضو این بازی نیست."),
                )
                return

        history = []

        if _get_chat_history_callback:
            try:
                history = (
                    _get_chat_history_callback(game_id)
                    or []
                )
            except Exception:
                history = []

        emit(
            "spy_chat_history",
            {
                "game_id": game_id,
                "messages": history,
            },
        )


    @socketio.on("spy_chat")
    def handle_spy_chat(data):
        data = data or {}

        game_id = str(
            data.get("game_id")
            or ""
        ).strip()

        username = get_authenticated_socket_username()

        message = str(
            data.get("message")
            or ""
        ).strip()

        reply_to = data.get("reply_to")

        if not game_id or not username:
            emit(
                "spy_error",
                _error("نشست کاربر معتبر نیست."),
            )
            return

        if not message:
            return

        if len(message) > MAX_CHAT_MESSAGE_LENGTH:
            emit(
                "spy_error",
                _error(
                    f"حداکثر طول پیام {MAX_CHAT_MESSAGE_LENGTH} کاراکتر است."
                ),
            )
            return

        game = get_spy_game(game_id)

        if not game:
            emit(
                "spy_error",
                _error("بازی پیدا نشد."),
            )
            return

        with game.lock:
            if game.phase == "finished":
                emit(
                    "spy_error",
                    _error("بازی تمام شده است."),
                )
                return

            if username not in game.players:
                emit(
                    "spy_error",
                    _error("بازیکن عضو این بازی نیست."),
                )
                return

        saved = None

        if _save_chat_callback:
            try:
                saved = _save_chat_callback(
                    username=username,
                    message=message,
                    is_image=False,
                    game_id=game_id,
                    reply_to=reply_to,
                )
            except TypeError:
                try:
                    saved = _save_chat_callback(
                        username,
                        message,
                        False,
                        game_id,
                        reply_to,
                    )
                except Exception:
                    saved = None
            except Exception:
                saved = None

        payload = {
            "game_id": game_id,
            "username": username,
            "message": message,
            "is_image": False,
            "reply_to": reply_to,
            "created_at": (
                saved.get("created_at")
                if isinstance(saved, dict)
                else time.time()
            ),
        }

        socketio.emit(
            "spy_chat",
            payload,
            room=f"spy_chat:{game_id}",
        )

    return True


# ============================================================
# LEGACY COMPATIBILITY
# ============================================================

# نام‌های قدیمی برای جلوگیری از شکستن کدهای قبلی پروژه

create_game = create_spy_game
get_game = get_spy_game
start_game = start_spy_game
start_voting = start_spy_voting
cast_vote = cast_spy_vote
finish_game = finish_spy_voting
submit_guess = submit_spy_guess
disconnect_player = disconnect_spy_player
tick_game = lambda game_id: _emit_state(game_id)


# ============================================================
# END
# ============================================================
