# -*- coding: utf-8 -*-

from flask_socketio import join_room, leave_room
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


WORDS = [
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


ALIASES = {
    "کفگیر": ["ملاقه", "کف گیر", "کفگیر آشپزی", "ابزار آشپزی", "قاشق آشپزی"],
    "فرودگاه": ["هواپیما", "ترمینال", "فرود", "پرواز"],
    "بیمارستان": ["درمانگاه", "دکتر", "پزشک", "بیمار", "کلینیک"],
    "رستوران": ["غذاخوری", "غذا", "کافه"],
    "سینما": ["فیلم", "سالن سینما", "فیلم سینمایی", "تماشا"],
    "مدرسه": ["کلاس", "دانش آموز", "معلم"],
    "هتل": ["مسافرخانه", "اقامتگاه", "اتاق", "مسافر"],
    "استادیوم": ["ورزشگاه", "ورزش", "فوتبال", "زمین فوتبال"],
    "کتابخانه": ["کتاب", "مطالعه", "کتاب خوانی"],
    "پارک": ["بوستان", "فضای سبز", "باغ"],
    "موزه": ["نمایشگاه", "آثار", "تاریخی", "تاریخ"],
    "ایستگاه قطار": ["قطار", "راه آهن", "ریل", "ایستگاه"],
    "فروشگاه": ["مغازه", "مارکت", "خرید", "فروش", "سوپرمارکت"],
    "دانشگاه": ["دانشکده", "دانشجو", "استاد", "کلاس"],
    "آکواریوم": ["ماهی", "آبزی", "آبزیان"],
    "کشتی": ["ناو", "قایق", "دریا", "کشتی دریایی"],
    "قلعه": ["دژ", "قصر", "حصار", "قلعه تاریخی"],
    "آزمایشگاه": ["لابراتوار", "آزمایش", "پژوهش"],
    "بانک": ["بانکداری", "پول", "حساب", "عابر بانک"],
    "رادیو": ["صدا", "رادیویی", "موج"],
}


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


def guess_matches(word, guess):
    word = normalize(word)
    guess = normalize(guess)

    if not word or not guess:
        return False

    if word == guess:
        return True

    if compact(word) == compact(guess):
        return True

    aliases = {
        normalize(x)
        for x in ALIASES.get(word, [])
    }

    if guess in aliases:
        return True

    return False


@dataclass
class Player:
    username: str
    role: str = ""
    connected: bool = True
    vote: str = ""


@dataclass
class Game:
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

    lock: threading.RLock = field(
        default_factory=threading.RLock
    )


_games = {}
_games_lock = threading.RLock()


def create_game(game_id, host):
    game_id = str(game_id or "").strip()
    host = str(host or "").strip()

    if not game_id or not host:
        return None

    with _games_lock:
        game = _games.get(game_id)

        if game is None:
            game = Game(game_id=game_id, host=host)
            _games[game_id] = game

        return game


def get_game(game_id):
    with _games_lock:
        return _games.get(str(game_id or "").strip())


def remove_game(game_id):
    with _games_lock:
        _games.pop(str(game_id or "").strip(), None)


def add_player(game_id, username):
    game = get_game(game_id)

    if not game:
        return False, "بازی پیدا نشد."

    username = str(username or "").strip()

    if not username:
        return False, "نام کاربری نامعتبر است."

    with game.lock:
        if game.phase != "lobby":
            return False, "بازی شروع شده است."

        if username not in game.players:
            if len(game.players) >= MAX_PLAYERS:
                return False, "ظرفیت بازی تکمیل است."

            game.players[username] = Player(
                username=username
            )
        else:
            game.players[username].connected = True

        return True, "بازیکن وارد شد."


def start_game(game_id, discussion_seconds):
    game = get_game(game_id)

    if not game:
        return False, "بازی پیدا نشد."

    try:
        seconds = int(discussion_seconds)
    except Exception:
        seconds = 120

    seconds = max(
        DISCUSSION_MIN,
        min(DISCUSSION_MAX, seconds)
    )

    with game.lock:
        if game.phase != "lobby":
            return False, "بازی قبلاً شروع شده است."

        connected = [
            p for p in game.players.values()
            if p.connected
        ]

        if len(connected) < MIN_PLAYERS:
            return False, f"حداقل {MIN_PLAYERS} بازیکن لازم است."

        game.discussion_seconds = seconds
        game.secret_word = random.choice(WORDS)
        game.spy_username = random.choice(
            [p.username for p in connected]
        )

        for player in connected:
            player.role = (
                "spy"
                if player.username == game.spy_username
                else "citizen"
            )
            player.vote = ""

        game.votes.clear()
        game.result.clear()
        game.phase = "discussion"
        game.phase_ends_at = time.time() + seconds

        return True, "بازی شروع شد."


def start_voting(game_id):
    game = get_game(game_id)

    if not game:
        return False, None

    with game.lock:
        if game.phase != "discussion":
            return False, None

        game.phase = "voting"
        game.phase_ends_at = time.time() + VOTING_SECONDS

        for player in game.players.values():
            player.vote = ""

        game.votes.clear()

        return True, game


def cast_vote(game_id, username, target):
    game = get_game(game_id)

    if not game:
        return False, "بازی پیدا نشد."

    username = str(username or "").strip()
    target = str(target or "").strip()

    with game.lock:
        if game.phase != "voting":
            return False, "زمان رأی‌گیری تمام شده است."

        if username not in game.players:
            return False, "بازیکن پیدا نشد."

        if target not in game.players:
            return False, "بازیکن موردنظر پیدا نشد."

        if username == target:
            return False, "نمی‌توانی به خودت رأی بدهی."

        game.votes[username] = target
        game.players[username].vote = target

        return True, "رأی ثبت شد."


def finish_game(game_id):
    game = get_game(game_id)

    if not game:
        return None

    with game.lock:
        if game.phase == "finished":
            return game.result

        counts = {}

        for target in game.votes.values():
            counts[target] = counts.get(target, 0) + 1

        if not counts:
            winner = "spy"
            reason = "هیچ رأیی ثبت نشد."
            eliminated = None
        else:
            highest = max(counts.values())
            leaders = [
                name
                for name, count in counts.items()
                if count == highest
            ]

            if len(leaders) != 1:
                winner = "spy"
                reason = "رأی‌گیری مساوی شد."
                eliminated = None
            else:
                eliminated = leaders[0]

                if eliminated == game.spy_username:
                    winner = "citizens"
                    reason = "شهروندها جاسوس را پیدا کردند."
                else:
                    winner = "spy"
                    reason = "شهروندها یک فرد بی‌گناه را انتخاب کردند."

        game.phase = "finished"
        game.phase_ends_at = 0

        game.result = {
            "winner": winner,
            "reason": reason,
            "spy": game.spy_username,
            "secret_word": game.secret_word,
            "eliminated": eliminated,
            "vote_counts": counts,
        }

        return game.result


def submit_spy_guess(game_id, username, guess):
    game = get_game(game_id)

    if not game:
        return False, "بازی پیدا نشد."

    username = str(username or "").strip()

    with game.lock:
        if game.phase not in ("discussion", "voting"):
            return False, "بازی فعال نیست."

        if username != game.spy_username:
            return False, "فقط جاسوس می‌تواند حدس بزند."

        guess = str(guess or "").strip()

        if not guess:
            return False, "حدس را وارد کن."

        correct = guess_matches(
            game.secret_word,
            guess
        )

        game.phase = "finished"
        game.phase_ends_at = 0

        game.result = {
            "winner": "spy" if correct else "citizens",
            "reason": (
                "جاسوس کلمه را درست حدس زد."
                if correct
                else "جاسوس کلمه را اشتباه حدس زد."
            ),
            "spy": game.spy_username,
            "secret_word": game.secret_word,
            "guess": guess,
            "guess_correct": correct,
            "eliminated": None,
            "vote_counts": {},
        }

        return True, game.result


def disconnect_player(game_id, username):
    game = get_game(game_id)

    if not game:
        return

    with game.lock:
        player = game.players.get(username)

        if player:
            player.connected = False


def tick_game(game_id):
    game = get_game(game_id)

    if not game:
        return None

    with game.lock:
        if game.phase not in ("discussion", "voting"):
            return {
                "phase": game.phase,
                "remaining_seconds": 0,
                "result": game.result,
            }

        remaining = max(
            0,
            int(game.phase_ends_at - time.time())
        )

        if remaining <= 0:
            if game.phase == "discussion":
                game.phase = "voting"
                game.phase_ends_at = (
                    time.time() + VOTING_SECONDS
                )

                for player in game.players.values():
                    player.vote = ""

                game.votes.clear()

                return {
                    "phase": "voting",
                    "remaining_seconds": VOTING_SECONDS,
                    "voting_started": True,
                }

            result = finish_game(game_id)

            return {
                "phase": "finished",
                "remaining_seconds": 0,
                "result": result,
            }

        return {
            "phase": game.phase,
            "remaining_seconds": remaining,
        }


def public_state(game_id, username):
    game = get_game(game_id)

    if not game:
        return None

    with game.lock:
        me = game.players.get(username)

        if not me:
            return None

        players = []

        for player in game.players.values():
            players.append({
                "username": player.username,
                "connected": player.connected,
                "is_host": player.username == game.host,
                "voted": (
                    player.username in game.votes
                ),
            })

        data = {
            "game_id": game.game_id,
            "host": game.host,
            "phase": game.phase,
            "players": players,
            "count": len(game.players),
            "min_players": MIN_PLAYERS,
            "max_players": MAX_PLAYERS,
            "discussion_seconds": game.discussion_seconds,
            "remaining_seconds": (
                max(
                    0,
                    int(game.phase_ends_at - time.time())
                )
                if game.phase_ends_at
                else 0
            ),
            "my_role": me.role,
            "my_vote": me.vote,
            "can_guess": (
                me.username == game.spy_username
                and game.phase in ("discussion", "voting")
            ),
        }

        if me.role == "citizen" and game.phase != "lobby":
            data["secret_word"] = game.secret_word

        if game.phase == "finished":
            data["result"] = game.result

        return data


# ============================================================
# SOCKET.IO
# ============================================================

def register_spy_socket(
    socketio,
    save_chat_callback=None,
    get_chat_history_callback=None,
):
    from flask import request

    def room_name(game_id):
        return "spy:" + str(game_id)

    def emit_state(game_id):
        game = get_game(game_id)

        if not game:
            return

        for player in list(game.players.values()):
            if not player.connected:
                continue

            state = public_state(
                game_id,
                player.username
            )

            if state:
                socketio.emit(
                    "spy_state",
                    state,
                    to=room_name(game_id)
                )

    def timer_worker(game_id):
        while True:
            time.sleep(1)

            game = get_game(game_id)

            if not game:
                return

            with game.lock:
                phase = game.phase

            if phase == "finished":
                return

            tick = tick_game(game_id)

            if not tick:
                return

            socketio.emit(
                "spy_tick",
                {
                    "game_id": game_id,
                    **tick,
                },
                room=room_name(game_id)
            )

            if tick.get("voting_started"):
                socketio.emit(
                    "spy_voting_started",
                    {
                        "game_id": game_id,
                        "phase": "voting",
                        "remaining_seconds": VOTING_SECONDS,
                    },
                    room=room_name(game_id)
                )
                emit_state(game_id)

            if tick.get("phase") == "finished":
                socketio.emit(
                    "spy_finished",
                    {
                        "game_id": game_id,
                        **(
                            tick.get("result")
                            or {}
                        ),
                    },
                    room=room_name(game_id)
                )
                return

    @socketio.on("spy_create")
    def spy_create(data):
        data = data or {}

        game_id = str(
            data.get("game_id")
            or "spy-main-room"
        ).strip()

        username = str(
            data.get("username")
            or ""
        ).strip()

        if not username:
            socketio.emit(
                "spy_error",
                {"message": "نام کاربری نامعتبر است."},
                to=request.sid
            )
            return

        game = create_game(
            game_id,
            username
        )

        if game:
            socketio.emit(
                "spy_created",
                public_state(
                    game_id,
                    username
                ) or {
                    "game_id": game_id,
                    "host": game.host,
                    "phase": game.phase,
                    "players": [],
                },
                to=request.sid
            )

    @socketio.on("spy_join")
    def spy_join(data):
        data = data or {}

        game_id = str(
            data.get("game_id")
            or ""
        ).strip()

        username = str(
            data.get("username")
            or ""
        ).strip()

        game = get_game(game_id)

        if not game:
            game = create_game(
                game_id,
                username
            )

        ok, message = add_player(
            game_id,
            username
        )

        if not ok:
            socketio.emit(
                "spy_error",
                {"message": message},
                to=request.sid
            )
            return

        join_room(
            room_name(game_id)
        )

        state = public_state(
            game_id,
            username
        )

        socketio.emit(
            "spy_joined",
            state,
            to=request.sid
        )

        emit_state(game_id)

    @socketio.on("spy_state")
    def spy_state(data):
        data = data or {}

        game_id = str(
            data.get("game_id")
            or ""
        ).strip()

        username = str(
            data.get("username")
            or ""
        ).strip()

        state = public_state(
            game_id,
            username
        )

        if state:
            socketio.emit(
                "spy_state",
                state,
                to=request.sid
            )

    @socketio.on("spy_start")
    def spy_start(data):
        data = data or {}

        game_id = str(
            data.get("game_id")
            or ""
        ).strip()

        username = str(
            data.get("username")
            or ""
        ).strip()

        game = get_game(game_id)

        if not game:
            socketio.emit(
                "spy_error",
                {"message": "بازی پیدا نشد."},
                to=request.sid
            )
            return

        if username != game.host:
            socketio.emit(
                "spy_error",
                {"message": "فقط سازنده بازی می‌تواند شروع کند."},
                to=request.sid
            )
            return

        ok, message = start_game(
            game_id,
            data.get(
                "discussion_seconds",
                120
            )
        )

        if not ok:
            socketio.emit(
                "spy_error",
                {"message": message},
                to=request.sid
            )
            return

        socketio.emit(
            "spy_started",
            {
                "game_id": game_id,
                "phase": "discussion",
            },
            room=room_name(game_id)
        )

        emit_state(game_id)

        threading.Thread(
            target=timer_worker,
            args=(game_id,),
            daemon=True
        ).start()

    @socketio.on("spy_vote")
    def spy_vote(data):
        data = data or {}

        game_id = str(
            data.get("game_id")
            or ""
        ).strip()

        username = str(
            data.get("username")
            or ""
        ).strip()

        target = str(
            data.get("target")
            or ""
        ).strip()

        ok, message = cast_vote(
            game_id,
            username,
            target
        )

        if not ok:
            socketio.emit(
                "spy_error",
                {"message": message},
                to=request.sid
            )
            return

        socketio.emit(
            "spy_vote",
            {
                "game_id": game_id,
                "username": username,
                "target": target,
            },
            room=room_name(game_id)
        )

        emit_state(game_id)

    @socketio.on("spy_guess")
    def spy_guess(data):
        data = data or {}

        game_id = str(
            data.get("game_id")
            or ""
        ).strip()

        username = str(
            data.get("username")
            or ""
        ).strip()

        guess = str(
            data.get("guess")
            or ""
        ).strip()

        ok, result = submit_spy_guess(
            game_id,
            username,
            guess
        )

        if not ok:
            socketio.emit(
                "spy_error",
                {"message": result},
                to=request.sid
            )
            return

        socketio.emit(
            "spy_finished",
            {
                "game_id": game_id,
                **result,
            },
            room=room_name(game_id)
        )

        emit_state(game_id)

    @socketio.on("spy_join_chat")
    def spy_join_chat(data):
        data = data or {}

        game_id = str(
            data.get("game_id")
            or ""
        ).strip()

        if game_id:
            join_room(
                room_name(game_id)
            )

    @socketio.on("spy_chat_history")
    def spy_chat_history(data):
        data = data or {}

        game_id = str(
            data.get("game_id")
            or ""
        ).strip()

        if not get_chat_history_callback:
            socketio.emit(
                "spy_chat_history",
                {"messages": []},
                to=request.sid
            )
            return

        try:
            messages = get_chat_history_callback(
                game_id=game_id
            )
        except TypeError:
            messages = get_chat_history_callback(
                game_id
            )
        except Exception:
            messages = []

        socketio.emit(
            "spy_chat_history",
            {
                "messages": messages or []
            },
            to=request.sid
        )

    @socketio.on("spy_chat")
    def spy_chat(data):
        data = data or {}

        game_id = str(
            data.get("game_id")
            or ""
        ).strip()

        username = str(
            data.get("username")
            or ""
        ).strip()

        message = str(
            data.get("message")
            or ""
        ).strip()

        reply_to = data.get("reply_to")

        if not game_id or not username or not message:
            return

        game = get_game(game_id)

        if game and game.phase == "finished":
            socketio.emit(
                "spy_error",
                {"message": "چت بازی بعد از پایان بسته شد."},
                to=request.sid
            )
            return

        saved = None

        if save_chat_callback:
            try:
                saved = save_chat_callback(
                    username=username,
                    message=message,
                    is_image=False,
                    game_id=game_id,
                    reply_to=reply_to,
                )
            except TypeError:
                try:
                    saved = save_chat_callback(
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
            "id": (
                saved.get("id")
                if isinstance(saved, dict)
                else None
            ),
            "username": username,
            "message": message,
            "game_id": game_id,
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
            room=room_name(game_id)
        )

    @socketio.on("spy_leave")
    def spy_leave(data):
        data = data or {}

        game_id = str(
            data.get("game_id")
            or ""
        ).strip()

        username = str(
            data.get("username")
            or ""
        ).strip()

        if game_id:
            disconnect_player(
                game_id,
                username
            )

            emit_state(game_id)

            try:
                leave_room(
                    room_name(game_id)
                )
            except Exception:
                pass

    @socketio.on("disconnect")
    def spy_disconnect():
        # Socket disconnect cannot reliably identify
        # the player without session state, so the
        # frontend sends spy_leave explicitly.
        pass
