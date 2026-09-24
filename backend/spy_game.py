# -*- coding: utf-8 -*-

import random
import re
import threading
import time
import uuid
from dataclasses import dataclass, field

from flask_socketio import join_room, leave_room


# ============================================================
# CONFIG
# ============================================================

MIN_PLAYERS = 1
MAX_PLAYERS = 5

VOTING_SECONDS = 10
SPY_GUESS_SECONDS = 30

MIN_DISCUSSION_SECONDS = 10
MAX_DISCUSSION_SECONDS = 3600

SPY_GAME_ROOM_PREFIX = "SPY:"


# ============================================================
# FALLBACK WORD BANK
# ============================================================

DEFAULT_WORDS = [
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


# ============================================================
# HELPERS
# ============================================================

def normalize(value):
    value = str(value or "").strip().lower()

    table = {
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

    for old, new in table.items():
        value = value.replace(old, new)

    value = re.sub(r"\s+", " ", value)

    return value.strip()


def compact(value):
    return normalize(value).replace(" ", "")


def make_game_id():
    return f"spy-{uuid.uuid4().hex[:12]}"


def now():
    return time.time()


def room_name(game_id):
    return f"{SPY_GAME_ROOM_PREFIX}{game_id}"


def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def get_word_bank():
    """
    تلاش می‌کند از بانک کلمات موجود پروژه استفاده کند.
    اگر API بانک کلمات در دسترس نبود، از بانک داخلی استفاده می‌شود.
    """

    try:
        import spy_word_bank

        candidates = [
            "get_active_words",
            "get_words",
            "active_words",
        ]

        for name in candidates:
            value = getattr(spy_word_bank, name, None)

            if callable(value):
                words = value()

                if isinstance(words, (list, tuple, set)):
                    words = [
                        str(x).strip()
                        for x in words
                        if str(x).strip()
                    ]

                    if words:
                        return words

            elif isinstance(value, (list, tuple, set)):
                words = [
                    str(x).strip()
                    for x in value
                    if str(x).strip()
                ]

                if words:
                    return words

    except Exception:
        pass

    return list(DEFAULT_WORDS)


def choose_word():
    words = get_word_bank()

    if not words:
        words = list(DEFAULT_WORDS)

    return random.choice(words)


def guess_matches(word, guess):
    word = normalize(word)
    guess = normalize(guess)

    if not word or not guess:
        return False

    if word == guess:
        return True

    if compact(word) == compact(guess):
        return True

    return False


# ============================================================
# PLAYER
# ============================================================

@dataclass
class SpyPlayer:
    username: str
    connected: bool = True
    role: str = ""
    vote: str = ""
    understood: bool = False


# ============================================================
# GAME
# ============================================================

@dataclass
class SpyGame:
    game_id: str
    host: str

    players: dict = field(default_factory=dict)

    phase: str = "lobby"

    discussion_seconds: int = 120
    phase_started_at: float = 0
    phase_ends_at: float = 0

    secret_word: str = ""
    spy_username: str = ""

    votes: dict = field(default_factory=dict)

    eliminated: str = ""

    result: dict = field(default_factory=dict)

    messages: list = field(default_factory=list)
    next_message_id: int = 1

    lock: threading.RLock = field(
        default_factory=threading.RLock
    )


# ============================================================
# ENGINE
# ============================================================

class SpyEngine:

    def __init__(self):
        self.games = {}
        self.active_game_id = None

        self.socketio = None

        self.user_sids = {}

        self._timer_thread = None
        self._timer_stop = threading.Event()

    # --------------------------------------------------------
    # SOCKET SETUP
    # --------------------------------------------------------

    def attach_socketio(self, socketio):
        self.socketio = socketio

        if self._timer_thread is None:
            self._timer_thread = threading.Thread(
                target=self._timer_loop,
                daemon=True
            )

            self._timer_thread.start()

    # --------------------------------------------------------
    # GAME ACCESS
    # --------------------------------------------------------

    def get_game(self, game_id=None):
        if not game_id:
            game_id = self.active_game_id

        if not game_id:
            return None

        return self.games.get(game_id)

    def get_or_create_game(self, game_id=None, host="mehdi"):
        game_id = game_id or self.active_game_id

        if game_id and game_id in self.games:
            return self.games[game_id]

        game_id = game_id or make_game_id()

        game = SpyGame(
            game_id=game_id,
            host=host or "mehdi"
        )

        self.games[game_id] = game
        self.active_game_id = game_id

        return game

    # --------------------------------------------------------
    # PLAYER MANAGEMENT
    # --------------------------------------------------------

    def add_player(self, game, username):
        username = str(username or "").strip().lower()

        if not username:
            return False, "نام کاربری نامعتبر است."

        with game.lock:

            if username in game.players:
                player = game.players[username]
                player.connected = True
                return True, None

            if len(game.players) >= MAX_PLAYERS:
                return False, "ظرفیت بازی تکمیل است."

            if game.phase != "lobby":
                return False, "این بازی شروع شده است."

            game.players[username] = SpyPlayer(
                username=username
            )

            return True, None

    def remove_player(self, game, username):
        username = str(username or "").strip().lower()

        with game.lock:

            player = game.players.get(username)

            if not player:
                return

            # بازی را خراب نمی‌کنیم؛ فقط Disconnect را ثبت می‌کنیم.
            player.connected = False

    def mark_disconnected(self, username):
        username = str(username or "").strip().lower()

        for game in list(self.games.values()):

            with game.lock:

                player = game.players.get(username)

                if player:
                    player.connected = False

    # --------------------------------------------------------
    # GAME START
    # --------------------------------------------------------

    def start_game(
        self,
        game,
        username,
        discussion_seconds
    ):
        username = str(username or "").strip().lower()

        if username != "mehdi":
            return False, "فقط مهدی می‌تواند بازی را شروع کند."

        with game.lock:

            if game.phase not in (
                "lobby",
                "duration_selection"
            ):
                return False, "بازی در حال اجراست."

            if not game.players:
                return False, "حداقل یک بازیکن لازم است."

            if len(game.players) > MAX_PLAYERS:
                return False, "تعداد بازیکن‌ها زیاد است."

            seconds = safe_int(
                discussion_seconds,
                120
            )

            seconds = max(
                MIN_DISCUSSION_SECONDS,
                min(
                    MAX_DISCUSSION_SECONDS,
                    seconds
                )
            )

            game.discussion_seconds = seconds

            game.secret_word = choose_word()

            usernames = list(game.players.keys())

            # نقش‌ها را از صفر تعیین می‌کنیم.
            for player in game.players.values():
                player.role = "citizen"
                player.vote = ""
                player.understood = False

            game.spy_username = random.choice(
                usernames
            )

            game.players[
                game.spy_username
            ].role = "spy"

            game.votes.clear()
            game.eliminated = ""
            game.result = {}

            game.phase = "discussion"

            game.phase_started_at = now()
            game.phase_ends_at = (
                game.phase_started_at
                + seconds
            )

            return True, None

    # --------------------------------------------------------
    # VOTING
    # --------------------------------------------------------

    def start_voting(self, game):

        with game.lock:

            if game.phase != "discussion":
                return False

            game.phase = "voting"

            game.phase_started_at = now()

            game.phase_ends_at = (
                game.phase_started_at
                + VOTING_SECONDS
            )

            game.votes.clear()

            for player in game.players.values():
                player.vote = ""

            return True

    def cast_vote(
        self,
        game,
        username,
        target
    ):
        username = str(username or "").strip().lower()
        target = str(target or "").strip().lower()

        with game.lock:

            if game.phase != "voting":
                return False, "زمان رأی‌گیری تمام شده است."

            if username not in game.players:
                return False, "بازیکن پیدا نشد."

            if target not in game.players:
                return False, "بازیکن انتخاب‌شده وجود ندارد."

            # رأی دادن به خود ممنوع است.
            if username == target:
                return False, "نمی‌توانی به خودت رأی بدهی."

            game.votes[username] = target

            game.players[
                username
            ].vote = target

            return True, None

    # --------------------------------------------------------
    # FINISH VOTING
    # --------------------------------------------------------

    def finish_voting(self, game):

        with game.lock:

            if game.phase != "voting":
                return

            active_players = [
                p.username
                for p in game.players.values()
            ]

            counts = {
                username: 0
                for username in active_players
            }

            for target in game.votes.values():

                if target in counts:
                    counts[target] += 1

            eliminated = None

            if counts:
                max_votes = max(
                    counts.values()
                )

                candidates = [
                    username
                    for username, count
                    in counts.items()
                    if count == max_votes
                ]

                if candidates:
                    eliminated = random.choice(
                        candidates
                    )

            game.eliminated = (
                eliminated or ""
            )

            # اگر هیچ رأیی وجود نداشته باشد،
            # جاسوس مستقیم برنده می‌شود.
            if not eliminated:
                self.finish_game(
                    game,
                    winner="spy",
                    reason="هیچ بازیکنی انتخاب نشد."
                )
                return

            if eliminated == game.spy_username:

                game.phase = "spy_guess"

                game.phase_started_at = now()

                game.phase_ends_at = (
                    game.phase_started_at
                    + SPY_GUESS_SECONDS
                )

                return

            self.finish_game(
                game,
                winner="spy",
                reason="شخص انتخاب‌شده جاسوس نبود."
            )

    # --------------------------------------------------------
    # SPY GUESS
    # --------------------------------------------------------

    def submit_spy_guess(
        self,
        game,
        username,
        guess
    ):
        username = str(username or "").strip().lower()
        guess = str(guess or "").strip()

        with game.lock:

            if game.phase != "spy_guess":
                return False, "زمان حدس زدن نیست."

            if username != game.spy_username:
                return False, "فقط جاسوس می‌تواند حدس بزند."

            if not guess:
                return False, "حدس خالی است."

            if guess_matches(
                game.secret_word,
                guess
            ):
                self.finish_game(
                    game,
                    winner="spy",
                    reason="جاسوس کلمه را درست حدس زد."
                )
            else:
                self.finish_game(
                    game,
                    winner="citizens",
                    reason="حدس جاسوس اشتباه بود."
                )

            return True, None

    # --------------------------------------------------------
    # FINISH
    # --------------------------------------------------------

    def finish_game(
        self,
        game,
        winner,
        reason
    ):

        with game.lock:

            game.phase = "finished"

            game.phase_started_at = now()
            game.phase_ends_at = 0

            game.result = {
                "winner": winner,
                "reason": reason,
                "spy": game.spy_username,
                "secret_word": game.secret_word,
                "eliminated": game.eliminated or None,
            }

    # --------------------------------------------------------
    # REPLAY
    # --------------------------------------------------------

    def replay(
        self,
        game,
        username
    ):
        username = str(username or "").strip().lower()

        if username != "mehdi":
            return False, "فقط مهدی می‌تواند بازی را دوباره شروع کند."

        with game.lock:

            game.phase = "lobby"

            game.discussion_seconds = 120

            game.phase_started_at = 0
            game.phase_ends_at = 0

            game.secret_word = ""
            game.spy_username = ""

            game.votes.clear()

            game.eliminated = ""

            game.result = {}

            for player in game.players.values():

                player.role = ""
                player.vote = ""
                player.understood = False

            return True, None

    # --------------------------------------------------------
    # CITIZEN UNDERSTOOD
    # --------------------------------------------------------

    def mark_understood(
        self,
        game,
        username
    ):
        username = str(username or "").strip().lower()

        with game.lock:

            player = game.players.get(username)

            if not player:
                return False, "بازیکن پیدا نشد."

            if game.phase != "discussion":
                return False, "در حال حاضر امکان ثبت این گزینه نیست."

            if player.role != "citizen":
                return False, "این گزینه برای شهروندهاست."

            player.understood = True

            return True, None

    # --------------------------------------------------------
    # CHAT
    # --------------------------------------------------------

    def add_chat_message(
        self,
        game,
        username,
        message,
        reply_to=None
    ):
        username = str(username or "").strip().lower()
        message = str(message or "").strip()

        with game.lock:

            if username not in game.players:
                return None, "بازیکن پیدا نشد."

            if not message:
                return None, "پیام خالی است."

            if len(message) > 1000:
                return None, "پیام بیش از حد طولانی است."

            if reply_to is not None:
                reply_to = safe_int(
                    reply_to,
                    0
                )

                if not any(
                    int(m["id"]) == reply_to
                    for m in game.messages
                ):
                    reply_to = None

            item = {
                "id": game.next_message_id,
                "username": username,
                "message": message,
                "reply_to": reply_to,
                "created_at": now(),
            }

            game.next_message_id += 1

            game.messages.append(item)

            # حداکثر 200 پیام اخیر
            if len(game.messages) > 200:
                game.messages = game.messages[-200:]

            return item, None

    def delete_chat_message(
        self,
        game,
        username,
        message_id
    ):
        username = str(username or "").strip().lower()

        message_id = safe_int(
            message_id,
            0
        )

        with game.lock:

            for index, message in enumerate(
                game.messages
            ):

                if int(message["id"]) != message_id:
                    continue

                if message["username"] != username:
                    return False, "فقط صاحب پیام می‌تواند آن را حذف کند."

                game.messages.pop(index)

                return True, None

            return False, "پیام پیدا نشد."

    # --------------------------------------------------------
    # PUBLIC STATE
    # --------------------------------------------------------

    def remaining_seconds(self, game):

        if not game.phase_ends_at:
            return 0

        return max(
            0,
            int(
                game.phase_ends_at
                - now()
            )
        )

    def public_state(
        self,
        game,
        username=None
    ):
        username = str(
            username or ""
        ).strip().lower()

        with game.lock:

            me = game.players.get(username)

            players = []

            for player in game.players.values():

                players.append({
                    "username": player.username,
                    "connected": player.connected,
                    "is_host": (
                        player.username
                        == game.host
                    ),
                    "understood": player.understood,
                })

            my_role = (
                me.role
                if me
                else ""
            )

            # مهم:
            # secret_word فقط برای citizen خود شخص ارسال می‌شود.
            secret_word = ""

            if (
                me
                and me.role == "citizen"
                and game.phase != "lobby"
            ):
                secret_word = game.secret_word

            can_understand = (
                bool(me)
                and me.role == "citizen"
                and game.phase == "discussion"
                and not me.understood
            )

            can_guess = (
                bool(me)
                and me.role == "spy"
                and game.phase == "spy_guess"
            )

            return {
                "success": True,

                "game_id": game.game_id,

                "host": game.host,

                "phase": game.phase,

                "players": players,

                "count": len(players),

                "my_role": my_role,

                "secret_word": secret_word,

                "can_understand": can_understand,

                "understood": (
                    me.understood
                    if me
                    else False
                ),

                "can_guess": can_guess,

                "discussion_seconds":
                    game.discussion_seconds,

                "remaining_seconds":
                    self.remaining_seconds(game),

                "voting_seconds":
                    VOTING_SECONDS,

                "spy_guess_seconds":
                    SPY_GUESS_SECONDS,

                "phase_ends_at":
                    game.phase_ends_at,

                "selected_vote":
                    (
                        game.votes.get(username)
                        if username
                        else None
                    ),

                "result":
                    (
                        game.result
                        if game.phase == "finished"
                        else None
                    ),
            }

    def lobby_state(self):
        game = self.get_game()

        if not game:
            return {
                "success": True,
                "game_id": None,
                "phase": "lobby",
                "players": [],
                "count": 0,
                "host": "mehdi",
                "remaining_seconds": 0,
            }

        return self.public_state(
            game,
            "mehdi"
        )

    # --------------------------------------------------------
    # BROADCAST
    # --------------------------------------------------------

    def emit_state(self, game):

        if not self.socketio:
            return

        # هر بازیکن state شخصی خودش را می‌گیرد.
        for player in list(game.players.values()):

            if not player.connected:
                continue

            sid = self.user_sids.get(
                player.username
            )

            if not sid:
                continue

            self.socketio.emit(
                "spy_state",
                self.public_state(
                    game,
                    player.username
                ),
                to=sid
            )

    def emit_tick(self, game):

        if not self.socketio:
            return

        remaining = self.remaining_seconds(
            game
        )

        for player in list(game.players.values()):

            if not player.connected:
                continue

            sid = self.user_sids.get(
                player.username
            )

            if not sid:
                continue

            payload = {
                "success": True,
                "game_id": game.game_id,
                "phase": game.phase,
                "remaining_seconds": remaining,
                "phase_ends_at": game.phase_ends_at,
            }

            self.socketio.emit(
                "spy_tick",
                payload,
                to=sid
            )

    def emit_voting_started(self, game):

        if not self.socketio:
            return

        for player in list(game.players.values()):

            if not player.connected:
                continue

            sid = self.user_sids.get(
                player.username
            )

            if not sid:
                continue

            payload = self.public_state(
                game,
                player.username
            )

            self.socketio.emit(
                "spy_voting_started",
                payload,
                to=sid
            )

    def emit_finished(self, game):

        if not self.socketio:
            return

        payload = dict(
            game.result or {}
        )

        payload["success"] = True
        payload["game_id"] = game.game_id
        payload["phase"] = "finished"

        for player in list(game.players.values()):

            sid = self.user_sids.get(
                player.username
            )

            if not sid:
                continue

            self.socketio.emit(
                "spy_finished",
                payload,
                to=sid
            )

    # --------------------------------------------------------
    # TIMER
    # --------------------------------------------------------

    def _timer_loop(self):

        while not self._timer_stop.is_set():

            try:
                self.tick_all()
            except Exception:
                pass

            self._timer_stop.wait(
                0.25
            )

    def tick_all(self):

        games = list(
            self.games.values()
        )

        for game in games:

            changed = False
            finished = False
            voting_started = False

            with game.lock:

                if game.phase not in (
                    "discussion",
                    "voting",
                    "spy_guess"
                ):
                    continue

                if not game.phase_ends_at:
                    continue

                if now() < game.phase_ends_at:
                    continue

                if game.phase == "discussion":

                    changed = self.start_voting(
                        game
                    )

                    voting_started = changed

                elif game.phase == "voting":

                    self.finish_voting(
                        game
                    )

                    changed = True

                elif game.phase == "spy_guess":

                    self.finish_game(
                        game,
                        winner="citizens",
                        reason="جاسوس در زمان مشخص حدس نزد."
                    )

                    changed = True
                    finished = True

            if voting_started:
                self.emit_voting_started(
                    game
                )

            if changed:
                self.emit_state(
                    game
                )

            if finished:
                self.emit_finished(
                    game
                )

            self.emit_tick(
                game
            )

    # --------------------------------------------------------
    # SOCKET REGISTRATION
    # --------------------------------------------------------

    def register_socket_handlers(
        self,
        socketio,
        get_socket_username=None
    ):
        self.attach_socketio(
            socketio
        )

        def current_username():
            if callable(
                get_socket_username
            ):
                try:
                    username = (
                        get_socket_username()
                    )

                    if username:
                        return str(
                            username
                        ).strip().lower()
                except Exception:
                    pass

            return None

        @socketio.on("spy_create")
        def spy_create(data=None):

            data = data or {}

            username = (
                str(
                    data.get("username")
                    or current_username()
                    or ""
                )
                .strip()
                .lower()
            )

            game_id = (
                data.get("game_id")
                or self.active_game_id
            )

            game = self.get_or_create_game(
                game_id=game_id,
                host="mehdi"
            )

            if username:
                ok, error = self.add_player(
                    game,
                    username
                )

                if not ok:
                    socketio.emit(
                        "spy_error",
                        {
                            "message": error
                        },
                        to=None
                    )
                    return

                self.user_sids[
                    username
                ] = __import__(
                    "flask"
                ).request.sid

                join_room(
                    room_name(game.game_id)
                )

            if username:
                socketio.emit(
                    "spy_created",
                    self.public_state(
                        game,
                        username
                    ),
                    to=__import__(
                        "flask"
                    ).request.sid
                )

        @socketio.on("spy_join")
        def spy_join(data=None):

            data = data or {}

            username = (
                str(
                    data.get("username")
                    or current_username()
                    or ""
                )
                .strip()
                .lower()
            )

            game_id = (
                data.get("game_id")
                or self.active_game_id
            )

            game = self.get_game(
                game_id
            )

            if not game:
                game = self.get_or_create_game(
                    game_id=game_id,
                    host="mehdi"
                )

            ok, error = self.add_player(
                game,
                username
            )

            if not ok:
                socketio.emit(
                    "spy_error",
                    {
                        "message": error
                    },
                    to=__import__(
                        "flask"
                    ).request.sid
                )
                return

            sid = __import__(
                "flask"
            ).request.sid

            self.user_sids[
                username
            ] = sid

            join_room(
                room_name(game.game_id)
            )

            socketio.emit(
                "spy_joined",
                self.public_state(
                    game,
                    username
                ),
                to=sid
            )

            self.emit_state(
                game
            )

        @socketio.on("spy_state")
        def spy_state(data=None):

            data = data or {}

            username = (
                str(
                    data.get("username")
                    or current_username()
                    or ""
                )
                .strip()
                .lower()
            )

            game = self.get_game(
                data.get("game_id")
            )

            if not game:
                return

            socketio.emit(
                "spy_state",
                self.public_state(
                    game,
                    username
                ),
                to=__import__(
                    "flask"
                ).request.sid
            )

        @socketio.on("spy_start")
        def spy_start(data=None):

            data = data or {}

            username = (
                str(
                    data.get("username")
                    or current_username()
                    or ""
                )
                .strip()
                .lower()
            )

            game = self.get_game(
                data.get("game_id")
            )

            if not game:
                socketio.emit(
                    "spy_error",
                    {
                        "message":
                            "بازی پیدا نشد."
                    },
                    to=__import__(
                        "flask"
                    ).request.sid
                )
                return

            seconds = data.get(
                "duration_seconds",
                data.get(
                    "discussion_seconds",
                    120
                )
            )

            ok, error = self.start_game(
                game,
                username,
                seconds
            )

            if not ok:
                socketio.emit(
                    "spy_error",
                    {
                        "message": error
                    },
                    to=__import__(
                        "flask"
                    ).request.sid
                )
                return

            self.emit_state(
                game
            )

            for player in game.players.values():

                sid = self.user_sids.get(
                    player.username
                )

                if sid:
                    socketio.emit(
                        "spy_started",
                        self.public_state(
                            game,
                            player.username
                        ),
                        to=sid
                    )

        @socketio.on("spy_vote")
        def spy_vote(data=None):

            data = data or {}

            username = (
                str(
                    data.get("username")
                    or current_username()
                    or ""
                )
                .strip()
                .lower()
            )

            target = (
                data.get("target")
                or data.get("target_username")
                or ""
            )

            target = str(
                target
            ).strip().lower()

            game = self.get_game(
                data.get("game_id")
            )

            if not game:
                return

            ok, error = self.cast_vote(
                game,
                username,
                target
            )

            if not ok:
                socketio.emit(
                    "spy_error",
                    {
                        "message": error
                    },
                    to=__import__(
                        "flask"
                    ).request.sid
                )
                return

            socketio.emit(
                "spy_vote",
                {
                    "success": True,
                    "username": username,
                    "target": target,
                },
                to=__import__(
                    "flask"
                ).request.sid
            )

        @socketio.on("spy_guess")
        def spy_guess(data=None):

            data = data or {}

            username = (
                str(
                    data.get("username")
                    or current_username()
                    or ""
                )
                .strip()
                .lower()
            )

            game = self.get_game(
                data.get("game_id")
            )

            if not game:
                return

            guess = str(
                data.get("guess")
                or ""
            ).strip()

            ok, error = self.submit_spy_guess(
                game,
                username,
                guess
            )

            if not ok:
                socketio.emit(
                    "spy_error",
                    {
                        "message": error
                    },
                    to=__import__(
                        "flask"
                    ).request.sid
                )
                return

            self.emit_state(
                game
            )

            self.emit_finished(
                game
            )

        @socketio.on("spy_understood")
        def spy_understood(data=None):

            data = data or {}

            username = (
                str(
                    data.get("username")
                    or current_username()
                    or ""
                )
                .strip()
                .lower()
            )

            game = self.get_game(
                data.get("game_id")
            )

            if not game:
                return

            ok, error = self.mark_understood(
                game,
                username
            )

            if not ok:
                socketio.emit(
                    "spy_error",
                    {
                        "message": error
                    },
                    to=__import__(
                        "flask"
                    ).request.sid
                )
                return

            self.emit_state(
                game
            )

        @socketio.on("spy_join_chat")
        def spy_join_chat(data=None):

            data = data or {}

            username = (
                str(
                    data.get("username")
                    or current_username()
                    or ""
                )
                .strip()
                .lower()
            )

            game = self.get_game(
                data.get("game_id")
            )

            if not game:
                return

            join_room(
                room_name(game.game_id)
            )

            self.user_sids[
                username
            ] = __import__(
                "flask"
            ).request.sid

        @socketio.on("spy_chat_history")
        def spy_chat_history(data=None):

            data = data or {}

            game = self.get_game(
                data.get("game_id")
            )

            if not game:
                return

            socketio.emit(
                "spy_chat_history",
                {
                    "messages":
                        list(game.messages)
                },
                to=__import__(
                    "flask"
                ).request.sid
            )

        @socketio.on("spy_chat")
        def spy_chat(data=None):

            data = data or {}

            username = (
                str(
                    data.get("username")
                    or current_username()
                    or ""
                )
                .strip()
                .lower()
            )

            game = self.get_game(
                data.get("game_id")
            )

            if not game:
                return

            message, error = self.add_chat_message(
                game,
                username,
                data.get("message"),
                data.get("reply_to")
            )

            if error:
                socketio.emit(
                    "spy_error",
                    {
                        "message": error
                    },
                    to=__import__(
                        "flask"
                    ).request.sid
                )
                return

            socketio.emit(
                "spy_chat",
                message,
                room=room_name(
                    game.game_id
                )
            )

        @socketio.on("spy_delete_chat")
        def spy_delete_chat(data=None):

            data = data or {}

            username = (
                str(
                    data.get("username")
                    or current_username()
                    or ""
                )
                .strip()
                .lower()
            )

            game = self.get_game(
                data.get("game_id")
            )

            if not game:
                return

            ok, error = self.delete_chat_message(
                game,
                username,
                data.get("message_id")
            )

            if not ok:
                socketio.emit(
                    "spy_error",
                    {
                        "message": error
                    },
                    to=__import__(
                        "flask"
                    ).request.sid
                )
                return

            socketio.emit(
                "spy_chat_deleted",
                {
                    "message_id":
                        safe_int(
                            data.get(
                                "message_id"
                            ),
                            0
                        )
                },
                room=room_name(
                    game.game_id
                )
            )

        @socketio.on("spy_replay")
        def spy_replay(data=None):

            data = data or {}

            username = (
                str(
                    data.get("username")
                    or current_username()
                    or ""
                )
                .strip()
                .lower()
            )

            game = self.get_game(
                data.get("game_id")
            )

            if not game:
                return

            ok, error = self.replay(
                game,
                username
            )

            if not ok:
                socketio.emit(
                    "spy_error",
                    {
                        "message": error
                    },
                    to=__import__(
                        "flask"
                    ).request.sid
                )
                return

            self.emit_state(
                game
            )

        @socketio.on("spy_leave")
        def spy_leave(data=None):

            data = data or {}

            username = (
                str(
                    data.get("username")
                    or current_username()
                    or ""
                )
                .strip()
                .lower()
            )

            game = self.get_game(
                data.get("game_id")
            )

            if not game:
                return

            # بازی در حال اجرا متوقف نمی‌شود.
            # فقط اتصال این بازیکن قطع‌شده ثبت می‌شود.
            self.mark_disconnected(
                username
            )

            sid = self.user_sids.get(
                username
            )

            if sid == __import__(
                "flask"
            ).request.sid:

                self.user_sids.pop(
                    username,
                    None
                )

            try:
                leave_room(
                    room_name(
                        game.game_id
                    )
                )
            except Exception:
                pass

            self.emit_state(
                game
            )

        @socketio.on("disconnect")
        def spy_disconnect():

            sid = __import__(
                "flask"
            ).request.sid

            username = None

            for user, user_sid in list(
                self.user_sids.items()
            ):
                if user_sid == sid:
                    username = user
                    break

            if username:
                self.mark_disconnected(
                    username
                )

                self.user_sids.pop(
                    username,
                    None
                )

                for game in list(
                    self.games.values()
                ):
                    if username in game.players:
                        self.emit_state(
                            game
                        )

    # --------------------------------------------------------
    # SHUTDOWN
    # --------------------------------------------------------

    def shutdown(self):
        self._timer_stop.set()


# ============================================================
# GLOBAL ENGINE
# ============================================================

spy_engine = SpyEngine()


# ============================================================
# COMPATIBILITY HELPERS
# ============================================================

def register_spy_socket(
    socketio,
    get_socket_username=None
):
    spy_engine.register_socket_handlers(
        socketio,
        get_socket_username
    )


def disconnect_spy_user(username):
    spy_engine.mark_disconnected(
        username
    )
