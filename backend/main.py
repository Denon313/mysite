# -*- coding: utf-8 -*-

import os
import sqlite3
import uuid
import time
import secrets
from pathlib import Path
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    request,
    jsonify,
    send_from_directory
)

from flask_cors import CORS
from flask_socketio import (
    SocketIO,
    emit,
    join_room,
    leave_room
)


# ========================================================= # CONFIG
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = BASE_DIR / "database.db"

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 5000))

ADMIN_PASSWORD = os.environ.get(
    "ADMIN_PASSWORD",
    "Mahdi1646"
)

FRONTEND_ORIGINS = [
    item.strip()
    for item in os.environ.get(
        "FRONTEND_ORIGINS",
        "https://denon313.github.io,http://localhost:8000,http://127.0.0.1:8000"
    ).split(",")
    if item.strip()
]

MAIN_ROOM = "GAME_ROOM"

MAX_PLAYERS = 5

MAX_CHAT_MESSAGES = 200

ALLOWED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif"
}


# ========================================================= # FIXED PLAYERS
# =========================================================

PLAYERS = {
    "mehdi": {
        "username": "mehdi",
        "display_name": "مهدی",
        "role": "admin",
        "emoji": "👑"
    },

    "rastin": {
        "username": "rastin",
        "display_name": "راستین",
        "role": "player",
        "emoji": "🎮"
    },

    "amirali": {
        "username": "amirali",
        "display_name": "امیرعلی",
        "role": "player",
        "emoji": "🎮"
    },

    "mahna": {
        "username": "mahna",
        "display_name": "مهنا",
        "role": "player",
        "emoji": "🎮"
    },

    "fatemeh": {
        "username": "fatemeh",
        "display_name": "فاطمه",
        "role": "player",
        "emoji": "🎮"
    }
}


# ========================================================= # FLASK
# =========================================================

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    secrets.token_hex(32)
)

app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024


CORS(
    app,
    resources={
        r"/api/*": {
            "origins": FRONTEND_ORIGINS
        }
    }
)


socketio = SocketIO(
    app,
    cors_allowed_origins=FRONTEND_ORIGINS,
    async_mode="threading"
)


# ========================================================= # DATABASE
# =========================================================

def get_db():

    conn = sqlite3.connect(
        DB_PATH,
        timeout=20
    )

    conn.row_factory = sqlite3.Row

    return conn


def init_db():

    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS players (
            username TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            avatar_url TEXT DEFAULT '',
            role TEXT DEFAULT 'player',
            blocked INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            display_name TEXT DEFAULT '',
            message TEXT DEFAULT '',
            is_image INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS scenarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_type TEXT NOT NULL,
            title TEXT NOT NULL,
            data TEXT DEFAULT '{}',
            enabled INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            icon TEXT DEFAULT '🎮',
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id TEXT PRIMARY KEY,
            game_type TEXT DEFAULT '',
            status TEXT DEFAULT 'waiting',
            state TEXT DEFAULT '{}',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    for username, player in PLAYERS.items():

        existing = conn.execute(
            "SELECT username FROM players WHERE username = ?",
            (username,)
        ).fetchone()

        if existing is None:

            conn.execute(
                """
                INSERT INTO players
                (
                    username,
                    display_name,
                    role
                )
                VALUES (?, ?, ?)
                """,
                (
                    username,
                    player["display_name"],
                    player["role"]
                )
            )

    conn.execute(
        """
        INSERT OR IGNORE INTO rooms
        (
            id,
            game_type,
            status
        )
        VALUES (?, '', 'waiting')
        """,
        (MAIN_ROOM,)
    )

    conn.commit()
    conn.close()


init_db()


# ========================================================= # RUNTIME STATE
# =========================================================

connected_users = {}

user_sids = {}

admin_sessions = set()

chat_cache = []

active_games = {}

# =========================================================
# SPY GAME ENGINE
# =========================================================

SPY_DEFAULT_WORDS = [
    ("سینما", "فیلم"),
    ("بیمارستان", "دکتر"),
    ("فرودگاه", "هواپیما"),
    ("رستوران", "غذا"),
    ("مدرسه", "معلم"),
    ("استخر", "شنا"),
    ("کتابخانه", "کتاب"),
    ("پارک", "تاب"),
    ("هتل", "اتاق"),
    ("فوتبال", "استادیوم"),
    ("عروسی", "داماد"),
    ("آشپزخانه", "اجاق"),
    ("پلیس", "بازداشتگاه"),
    ("ساحل", "دریا"),
    ("باغ وحش", "شیر"),
]


def create_spy_game(game_id, players, host):
    if len(players) < 3 or len(players) > 5:
        raise ValueError("بازی جاسوس به ۳ تا ۵ بازیکن نیاز دارد.")

    common_word, spy_hint = random.choice(SPY_DEFAULT_WORDS)
    spy_username = random.choice(players)

    player_states = {}

    for username in players:
        if username == spy_username:
            player_states[username] = {
                "username": username,
                "role": "spy",
                "word": None,
                "hint": spy_hint,
                "vote": None,
            }
        else:
            player_states[username] = {
                "username": username,
                "role": "citizen",
                "word": common_word,
                "hint": None,
                "vote": None,
            }

    active_games[game_id] = {
        "id": game_id,
        "game_type": "spy",
        "host": host,
        "players": players,
        "phase": "discussion",
        "started_at": time.time(),
        "discussion_seconds": 120,
        "voting_seconds": 10,
        "phase_ends_at": time.time() + 120,
        "votes": {},
        "vote_locked": False,
        "result": None,
        "spy_username": spy_username,
        "common_word": common_word,
        "spy_hint": spy_hint,
        "player_states": player_states,
    }

    return active_games[game_id]


def get_spy_private_state(game, username):
    player = game.get("player_states", {}).get(username)

    if not player:
        return None

    if player["role"] == "spy":
        return {
            "username": username,
            "role": "spy",
            "word": None,
            "hint": player.get("hint"),
        }

    return {
        "username": username,
        "role": "citizen",
        "word": player.get("word"),
        "hint": None,
    }


def get_spy_public_state(game):
    return {
        "game_id": game["id"],
        "game_type": "spy",
        "phase": game["phase"],
        "players": game["players"],
        "phase_ends_at": game["phase_ends_at"],
        "discussion_seconds": game["discussion_seconds"],
        "voting_seconds": game["voting_seconds"],
        "vote_locked": game["vote_locked"],
        "result": game.get("result"),
    }


def start_spy_voting(game):
    game["phase"] = "voting"
    game["vote_locked"] = False
    game["votes"] = {}
    game["phase_ends_at"] = (
        time.time() + game["voting_seconds"]
    )


def submit_spy_vote(game, voter, target):
    if game["phase"] != "voting":
        return False, "الان زمان رأی‌گیری نیست."

    if game["vote_locked"]:
        return False, "رأی‌گیری بسته شده است."

    if voter not in game["players"]:
        return False, "بازیکن معتبر نیست."

    if target not in game["players"]:
        return False, "هدف رأی معتبر نیست."

    if voter == target:
        return False, "نمی‌توانید به خودتان رأی بدهید."

    game["votes"][voter] = target

    return True, "رأی ثبت شد."


def finish_spy_voting(game):
    if game["vote_locked"]:
        return game.get("result")

    game["vote_locked"] = True

    vote_counts = {}

    for target in game["votes"].values():
        vote_counts[target] = (
            vote_counts.get(target, 0) + 1
        )

    max_votes = 0
    eliminated = None
    tied = False

    for player in game["players"]:
        count = vote_counts.get(player, 0)

        if count > max_votes:
            max_votes = count
            eliminated = player
            tied = False

        elif count == max_votes and count > 0:
            tied = True

    if tied:
        eliminated = None

    spy_username = game["spy_username"]

    if eliminated is None:
        winner = "spy"
    elif eliminated == spy_username:
        winner = "citizens"
    else:
        winner = "spy"

    game["phase"] = "finished"

    game["result"] = {
        "winner": winner,
        "spy": spy_username,
        "eliminated": eliminated,
        "vote_counts": vote_counts,
        "total_votes": len(game["votes"]),
        "common_word": game["common_word"],
        "spy_hint": game["spy_hint"],
    }

    return game["result"]



# ========================================================= # HELPERS
# =========================================================

def now():

    return datetime.utcnow().isoformat()


def player_exists(username):

    return username in PLAYERS


def get_player(username):

    if not player_exists(username):
        return None

    conn = get_db()

    row = conn.execute(
        """
        SELECT
            username,
            display_name,
            avatar_url,
            role,
            blocked
        FROM players
        WHERE username = ?
        """,
        (username,)
    ).fetchone()

    conn.close()

    if row is None:
        return None

    return dict(row)


def player_public(username):

    base = PLAYERS.get(username)

    if not base:
        return None

    player = get_player(username)

    if not player:
        player = {
            **base,
            "avatar_url": "",
            "blocked": 0
        }

    status = connected_users.get(
        username,
        "offline"
    )

    return {
        "username": username,
        "display_name":
            player.get(
                "display_name",
                base["display_name"]
            ),
        "avatar_url":
            player.get(
                "avatar_url",
                ""
            ),
        "role":
            player.get(
                "role",
                base["role"]
            ),
        "status": status,
        "blocked":
            bool(
                player.get(
                    "blocked",
                    0
                )
            )
    }


def all_players():

    return [
        player_public(username)
        for username in PLAYERS
    ]


def add_activity(
    icon,
    title,
    description=""
):

    conn = get_db()

    conn.execute(
        """
        INSERT INTO activities
        (
            icon,
            title,
            description
        )
        VALUES (?, ?, ?)
        """,
        (
            icon,
            title,
            description
        )
    )

    conn.commit()
    conn.close()


def get_recent_activities():

    conn = get_db()

    rows = conn.execute(
        """
        SELECT
            id,
            icon,
            title,
            description,
            created_at
        FROM activities
        ORDER BY id DESC
        LIMIT 30
        """
    ).fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


def get_chat_history():

    conn = get_db()

    rows = conn.execute(
        """
        SELECT
            id,
            username,
            display_name,
            message,
            is_image,
            created_at
        FROM chat_messages
        ORDER BY id DESC
        LIMIT ?
        """,
        (MAX_CHAT_MESSAGES,)
    ).fetchall()

    conn.close()

    result = [
        {
            "id": row["id"],
            "username": row["username"],
            "display_name": row["display_name"],
            "message": row["message"],
            "is_image":
                bool(row["is_image"]),
            "created_at": row["created_at"]
        }
        for row in rows
    ]

    result.reverse()

    return result


def save_chat_message(
    username,
    message,
    is_image=False
):

    player = get_player(username)

    display_name = (
        player["display_name"]
        if player
        else PLAYERS.get(
            username,
            {}
        ).get(
            "display_name",
            username
        )
    )

    conn = get_db()

    cursor = conn.execute(
        """
        INSERT INTO chat_messages
        (
            username,
            display_name,
            message,
            is_image
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            username,
            display_name,
            message,
            int(is_image)
        )
    )

    conn.commit()

    message_id = cursor.lastrowid

    conn.close()

    return {
        "id": message_id,
        "username": username,
        "display_name": display_name,
        "message": message,
        "is_image": bool(is_image),
        "created_at": now()
    }


def admin_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        token = request.headers.get(
            "X-Admin-Token",
            ""
        )

        if not token:
            return jsonify({
                "success": False,
                "error":
                    "دسترسی مدیر لازم است."
            }), 401

        if token not in admin_sessions:
            return jsonify({
                "success": False,
                "error":
                    "نشست مدیر معتبر نیست."
            }), 401

        return function(
            *args,
            **kwargs
        )

    return wrapper


def json_body():

    try:
        return request.get_json(
            silent=True
        ) or {}

    except Exception:
        return {}


def valid_username(username):

    return (
        isinstance(username, str)
        and username in PLAYERS
    )


def room_players():

    connected_usernames = {
        info.get("username")
        for info in user_sids.values()
        if isinstance(info, dict) and info.get("username")
    }

    return [
        player_public(username)
        for username in PLAYERS
        if username in connected_usernames
    ]


# ========================================================= # BASIC ROUTES
# =========================================================

@app.route("/")
def home():

    return jsonify({
        "success": True,
        "name": "Game Room Backend",
        "status": "online",
        "room": MAIN_ROOM
    })


@app.route("/health")
def health():

    return jsonify({
        "success": True,
        "status": "ok",
        "service": "game-room"
    })


# ========================================================= # LOGIN
# =========================================================

@app.post("/api/game/login")
def game_login():

    data = json_body()

    username = data.get(
        "username",
        ""
    ).strip()

    password = data.get(
        "password",
        ""
    )

    if not valid_username(username):

        return jsonify({
            "success": False,
            "error":
                "کاربر معتبر نیست."
        }), 401

    player = get_player(username)

    if not player:

        return jsonify({
            "success": False,
            "error":
                "کاربر پیدا نشد."
        }), 404

    if player["blocked"]:

        return jsonify({
            "success": False,
            "error":
                "این کاربر مسدود شده است."
        }), 403

    if username == "mehdi":

        if password != ADMIN_PASSWORD:

            return jsonify({
                "success": False,
                "error":
                    "رمز مدیریت اشتباه است."
            }), 401

        token = secrets.token_urlsafe(
            48
        )

        admin_sessions.add(token)

        return jsonify({
            "success": True,
            "username": username,
            "role": "admin",
            "admin_token": token
        })

    return jsonify({
        "success": True,
        "username": username,
        "role": player["role"]
    })


# ========================================================= # PROFILE
# =========================================================

@app.get("/api/game/profile/<username>")
def get_profile(username):

    if not valid_username(username):

        return jsonify({
            "error":
                "کاربر پیدا نشد."
        }), 404

    player = player_public(username)

    return jsonify(player)


@app.post("/api/game/profile/<username>")
def update_profile(username):

    if not valid_username(username):

        return jsonify({
            "error":
                "کاربر پیدا نشد."
        }), 404

    data = json_body()

    display_name = str(
        data.get(
            "display_name",
            ""
        )
    ).strip()

    if not display_name:

        return jsonify({
            "error":
                "نام نمایشی الزامی است."
        }), 400

    if len(display_name) > 30:

        return jsonify({
            "error":
                "نام نمایشی خیلی طولانی است."
        }), 400

    conn = get_db()

    conn.execute(
        """
        UPDATE players
        SET
            display_name = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE username = ?
        """,
        (
            display_name,
            username
        )
    )

    conn.commit()
    conn.close()

    player = player_public(username)

    socketio.emit(
        "game_profile_update",
        player,
        room=MAIN_ROOM
    )

    return jsonify(player)


@app.post(
    "/api/game/profile/<username>/avatar"
)
def upload_avatar(username):

    if not valid_username(username):

        return jsonify({
            "error":
                "کاربر پیدا نشد."
        }), 404

    if "avatar" not in request.files:

        return jsonify({
            "error":
                "تصویر ارسال نشده."
        }), 400

    file = request.files["avatar"]

    if not file.filename:

        return jsonify({
            "error":
                "فایل انتخاب نشده."
        }), 400

    extension = Path(
        file.filename
    ).suffix.lower()

    if extension not in ALLOWED_IMAGE_EXTENSIONS:

        return jsonify({
            "error":
                "فرمت تصویر مجاز نیست."
        }), 400

    filename = (
        f"profile_{username}_"
        f"{uuid.uuid4().hex}"
        f"{extension}"
    )

    file.save(
        UPLOAD_DIR / filename
    )

    url = (
        f"/uploads/{filename}"
    )

    conn = get_db()

    conn.execute(
        """
        UPDATE players
        SET
            avatar_url = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE username = ?
        """,
        (
            url,
            username
        )
    )

    conn.commit()
    conn.close()

    player = player_public(username)

    socketio.emit(
        "game_profile_update",
        player,
        room=MAIN_ROOM
    )

    return jsonify({
        "success": True,
        "avatar_url": url
    })


# ========================================================= # UPLOADS
# =========================================================

@app.get("/uploads/<path:filename>")
def uploaded_file(filename):

    return send_from_directory(
        UPLOAD_DIR,
        filename
    )


# ========================================================= # PLAYERS
# =========================================================

@app.get("/api/game/players")
def players():

    return jsonify({
        "players": all_players()
    })


# ========================================================= # ACTIVITIES
# =========================================================

@app.get("/api/game/activity")
def activities():

    return jsonify({
        "activities":
            get_recent_activities()
    })


# ========================================================= # CHAT
# =========================================================

@app.post("/api/game/chat/upload")
def chat_upload():

    username = request.form.get(
        "username",
        ""
    ).strip()

    if not valid_username(username):

        return jsonify({
            "error":
                "کاربر معتبر نیست."
        }), 401

    if "image" not in request.files:

        return jsonify({
            "error":
                "تصویر ارسال نشده."
        }), 400

    file = request.files["image"]

    if not file.filename:

        return jsonify({
            "error":
                "فایل انتخاب نشده."
        }), 400

    extension = Path(
        file.filename
    ).suffix.lower()

    if extension not in ALLOWED_IMAGE_EXTENSIONS:

        return jsonify({
            "error":
                "فرمت تصویر مجاز نیست."
        }), 400

    filename = (
        f"chat_{uuid.uuid4().hex}"
        f"{extension}"
    )

    file.save(
        UPLOAD_DIR / filename
    )

    return jsonify({
        "success": True,
        "url":
            f"/uploads/{filename}"
    })


# ========================================================= # ROOMS
# =========================================================

@app.get("/api/game/room")
def get_room():

    conn = get_db()

    row = conn.execute(
        """
        SELECT *
        FROM rooms
        WHERE id = ?
        """,
        (MAIN_ROOM,)
    ).fetchone()

    conn.close()

    if not row:

        return jsonify({
            "id": MAIN_ROOM,
            "game_type": "",
            "status": "waiting",
            "players": room_players()
        })

    return jsonify({
        "id": row["id"],
        "game_type": row["game_type"],
        "status": row["status"],
        "players": room_players()
    })


# ========================================================= # ADMIN DASHBOARD
# =========================================================

@app.get(
    "/api/game/admin/dashboard"
)
@admin_required
def admin_dashboard():

    online_count = sum(
        1
        for status
        in connected_users.values()
        if status == "online"
    )

    weak_count = sum(
        1
        for status
        in connected_users.values()
        if status == "weak"
    )

    return jsonify({
        "success": True,
        "online_count":
            online_count,
        "weak_count":
            weak_count,
        "offline_count":
            MAX_PLAYERS -
            online_count -
            weak_count,
        "active_rooms": 1,
        "games_running":
            len(active_games),
        "players":
            all_players()
    })


@app.post(
    "/api/game/admin/block/<username>"
)
@admin_required
def block_player(username):

    if not valid_username(username):

        return jsonify({
            "error":
                "کاربر پیدا نشد."
        }), 404

    if username == "mehdi":

        return jsonify({
            "error":
                "مدیر قابل مسدود کردن نیست."
        }), 400

    conn = get_db()

    conn.execute(
        """
        UPDATE players
        SET blocked = 1
        WHERE username = ?
        """,
        (username,)
    )

    conn.commit()
    conn.close()

    socketio.emit(
        "game_status_update",
        {
            "username": username,
            "status": "offline",
            "blocked": True
        },
        room=MAIN_ROOM
    )

    return jsonify({
        "success": True
    })


@app.post(
    "/api/game/admin/unblock/<username>"
)
@admin_required
def unblock_player(username):

    if not valid_username(username):

        return jsonify({
            "error":
                "کاربر پیدا نشد."
        }), 404

    conn = get_db()

    conn.execute(
        """
        UPDATE players
        SET blocked = 0
        WHERE username = ?
        """,
        (username,)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "success": True
    })


# ========================================================= # SCENARIOS
# =========================================================

@app.get("/api/game/scenarios")
def get_scenarios():

    game_type = request.args.get(
        "game_type",
        ""
    ).strip()

    conn = get_db()

    if game_type:

        rows = conn.execute(
            """
            SELECT *
            FROM scenarios
            WHERE game_type = ?
            AND enabled = 1
            ORDER BY id DESC
            """,
            (game_type,)
        ).fetchall()

    else:

        rows = conn.execute(
            """
            SELECT *
            FROM scenarios
            WHERE enabled = 1
            ORDER BY id DESC
            """
        ).fetchall()

    conn.close()

    result = [
        dict(row)
        for row in rows
    ]

    return jsonify({
        "scenarios": result
    })


@app.post("/api/game/admin/scenarios")
@admin_required
def add_scenario():

    data = json_body()

    game_type = str(
        data.get(
            "game_type",
            ""
        )
    ).strip()

    title = str(
        data.get(
            "title",
            ""
        )
    ).strip()

    scenario_data = data.get(
        "data",
        {}
    )

    if not game_type or not title:

        return jsonify({
            "error":
                "نوع بازی و عنوان الزامی است."
        }), 400

    import json

    conn = get_db()

    cursor = conn.execute(
        """
        INSERT INTO scenarios
        (
            game_type,
            title,
            data,
            enabled
        )
        VALUES (?, ?, ?, 1)
        """,
        (
            game_type,
            title,
            json.dumps(
                scenario_data,
                ensure_ascii=False
            )
        )
    )

    conn.commit()

    scenario_id = cursor.lastrowid

    conn.close()

    return jsonify({
        "success": True,
        "id": scenario_id
    })


# ========================================================= # GAME MANAGEMENT
# =========================================================

VALID_GAMES = {
    "spy",
    "mystery",
    "forbidden"
}


@app.post("/api/game/start")
def start_game():
    data = json_body()

    username = str(data.get("username", "")).strip()
    game_type = str(data.get("game_type", "")).strip()

    if not valid_username(username):
        return jsonify({
            "error": "کاربر معتبر نیست."
        }), 401

    if game_type not in VALID_GAMES:
        return jsonify({
            "error": "بازی معتبر نیست."
        }), 400

    # فقط مدیر اجازه شروع بازی را دارد
    if username != "Mahdi":
        return jsonify({
            "error": "فقط مدیر می‌تواند بازی را شروع کند."
        }), 403

    if game_type == "spy":
        min_players = 3
        max_players = 5
    elif game_type == "mystery":
        min_players = 2
        max_players = 5
    else:
        min_players = 4
        max_players = 4

    players = [
        p["username"]
        for p in room_players()
    ]

    current_players = len(players)

    if current_players < min_players:
        return jsonify({
            "error":
                f"برای شروع حداقل {min_players} بازیکن لازم است."
        }), 400

    if current_players > max_players:
        return jsonify({
            "error":
                f"حداکثر {max_players} بازیکن مجاز است."
        }), 400

    game_id = uuid.uuid4().hex

    if game_type == "spy":
        active_games[game_id] = create_spy_game(
            game_id,
            players,
            username
        )

        start_spy_server_timer(game_id)

    else:
        active_games[game_id] = {
            "id": game_id,
            "game_type": game_type,
            "host": username,
            "players": players,
            "phase": "waiting",
            "started_at": time.time()
        }

    conn = get_db()

    conn.execute(
        """
        UPDATE rooms
        SET
            game_type = ?,
            status = 'playing',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            game_type,
            MAIN_ROOM
        )
    )

    conn.commit()
    conn.close()

    add_activity(
        "🎮",
        "بازی جدید شروع شد",
        f"{game_type}"
    )

    socketio.emit(
        "game_started",
        {
            "game_id": game_id,
            "game_type": game_type,
            "players": active_games[game_id]["players"]
        },
        room=MAIN_ROOM
    )

    return jsonify({
        "success": True,
        "game_id": game_id,
        "game_type": game_type,
        "players": players
    })


# ========================================================= # SOCKET.IO
# =========================================================

@socketio.on("connect")
def socket_connect():

    print(
        "Socket connected:",
        request.sid
    )


@socketio.on("disconnect")
def socket_disconnect():

    sid = request.sid

    info = user_sids.pop(
            sid,
            None
        )

    if not info:
        return

    username = info["username"]

    if username in connected_users:

        connected_users.pop(
            username,
            None
        )

    leave_room(
        MAIN_ROOM
    )

    socketio.emit(
        "game_status_update",
        {
            "username": username,
            "status": "offline"
        },
        room=MAIN_ROOM
    )

    socketio.emit(
        "game_players_update",
        {
            "players":
                all_players()
        },
        room=MAIN_ROOM
    )



# =========================================================
# SPY PRIVATE ROLE EVENT
# =========================================================

def send_spy_private_role(game_id, username, sid=None):
    game = active_games.get(game_id)

    if not game:
        return False

    if game.get("game_type") != "spy":
        return False

    private_state = get_spy_private_state(
        game,
        username
    )

    if not private_state:
        return False

    target_sid = sid

    if not target_sid:
        for socket_id, user in user_sids.items():
            if user == username:
                target_sid = socket_id
                break

    if not target_sid:
        return False

    socketio.emit(
        "spy_private_role",
        private_state,
        to=target_sid
    )

    return True


@socketio.on("spy_request_role")
def spy_request_role(data):
    data = data or {}

    username = data.get(
        "username",
        ""
    )

    game_id = data.get(
        "game_id",
        ""
    )

    if not valid_username(username):
        return

    if not game_id:
        return

    game = active_games.get(game_id)

    if not game:
        return

    if game.get("game_type") != "spy":
        return

    if username not in game.get(
        "players",
        []
    ):
        return

    send_spy_private_role(
        game_id,
        username,
        request.sid
    )



# =========================================================
# SPY VOTING SOCKET EVENTS
# =========================================================


# =========================================================
# SPY SERVER TIMER
# =========================================================

def spy_timer_loop(game_id):
    while True:
        time.sleep(0.5)

        game = active_games.get(game_id)

        if not game:
            return

        game_type = game.get("game_type")
        phase = game.get("phase")

        if game_type != "spy":
            return

        if phase == "finished":
            return

        now = time.time()
        end_time = game.get(
            "phase_ends_at",
            0
        )

        if now < end_time:
            continue

        if phase == "discussion":
            start_spy_voting(game)

            socketio.emit(
                "spy_voting_started",
                get_spy_public_state(game),
                room=MAIN_ROOM
            )

            continue

        if phase == "voting":
            result = finish_spy_voting(game)

            socketio.emit(
                "spy_game_finished",
                result,
                room=MAIN_ROOM
            )

            socketio.emit(
                "spy_game_state",
                get_spy_public_state(game),
                room=MAIN_ROOM
            )

            return


def start_spy_server_timer(game_id):
    socketio.start_background_task(
        spy_timer_loop,
        game_id
    )


def broadcast_spy_public_state(game_id):
    game = active_games.get(game_id)

    if not game:
        return

    socketio.emit(
        "spy_game_state",
        get_spy_public_state(game),
        room=MAIN_ROOM
    )


def finish_spy_game_if_needed(game_id):
    game = active_games.get(game_id)

    if not game:
        return

    if game.get("game_type") != "spy":
        return

    if game.get("phase") == "discussion":
        if time.time() >= game.get(
            "phase_ends_at",
            0
        ):
            start_spy_voting(game)
            broadcast_spy_public_state(game)

    elif game.get("phase") == "voting":
        if time.time() >= game.get(
            "phase_ends_at",
            0
        ):
            result = finish_spy_voting(game)

            socketio.emit(
                "spy_game_finished",
                result,
                room=MAIN_ROOM
            )

            broadcast_spy_public_state(game)


@socketio.on("spy_start_voting")
def spy_start_voting(data):
    data = data or {}

    game_id = data.get(
        "game_id",
        ""
    )

    username = data.get(
        "username",
        ""
    )

    if not valid_username(username):
        return

    game = active_games.get(game_id)

    if not game:
        return

    if game.get("game_type") != "spy":
        return

    if username not in game.get(
        "players",
        []
    ):
        return

    if game.get("phase") != "discussion":
        return

    start_spy_voting(game)

    socketio.emit(
        "spy_voting_started",
        get_spy_public_state(game),
        room=MAIN_ROOM
    )


@socketio.on("spy_vote")
def spy_vote(data):
    data = data or {}

    game_id = data.get(
        "game_id",
        ""
    )

    voter = data.get(
        "voter",
        ""
    )

    target = data.get(
        "target",
        ""
    )

    if not valid_username(voter):
        return

    game = active_games.get(game_id)

    if not game:
        return

    if game.get("game_type") != "spy":
        return

    if game.get("phase") != "voting":
        return

    success, message = submit_spy_vote(
        game,
        voter,
        target
    )

    socketio.emit(
        "spy_vote_status",
        {
            "success": success,
            "message": message,
            "voter": voter
        },
        to=request.sid
    )

    if not success:
        return

    total_players = len(
        game.get("players", [])
    )

    total_votes = len(
        game.get("votes", {})
    )

    if total_votes >= total_players:
        result = finish_spy_voting(game)

        socketio.emit(
            "spy_game_finished",
            result,
            room=MAIN_ROOM
        )

        broadcast_spy_public_state(game)


@socketio.on("spy_get_state")
def spy_get_state(data):
    data = data or {}

    game_id = data.get(
        "game_id",
        ""
    )

    username = data.get(
        "username",
        ""
    )

    if not valid_username(username):
        return

    game = active_games.get(game_id)

    if not game:
        return

    if game.get("game_type") != "spy":
        return

    finish_spy_game_if_needed(
        game_id
    )

    game = active_games.get(game_id)

    if not game:
        return

    socketio.emit(
        "spy_game_state",
        get_spy_public_state(game),
        to=request.sid
    )

    send_spy_private_role(
        game_id,
        username,
        request.sid
    )


@socketio.on("game_join")
def socket_join(data):

    data = data or {}

    username = str(
        data.get(
            "username",
            ""
        )
    ).strip()

    if not valid_username(username):

        emit(
            "game_join_error",
            {
                "error":
                    "کاربر معتبر نیست."
            }
        )

        return

    player = get_player(username)

    if not player:

        emit(
            "game_join_error",
            {
                "error":
                    "کاربر پیدا نشد."
            }
        )

        return

    if player["blocked"]:

        emit(
            "game_join_error",
            {
                "error":
                    "حساب شما مسدود شده است."
            }
        )

        return

    if (
        username not in user_sids
        and len(user_sids) >= MAX_PLAYERS
    ):

        emit(
            "game_join_error",
            {
                "error":
                    "اتاق پر است."
            }
        )

        return

    user_sids[request.sid] = {
        "username": username
    }

    connected_users[
        username
    ] = "online"

    join_room(
        MAIN_ROOM
    )

    player_data = player_public(
            username
        )

    emit(
        "game_joined",
        {
            "player":
                player_data,

            "players":
                all_players(),

            "messages":
                get_chat_history()
        }
    )

    socketio.emit(
        "game_status_update",
        {
            "username": username,
            "status": "online"
        },
        room=MAIN_ROOM
    )

    socketio.emit(
        "game_players_update",
        {
            "players":
                all_players()
        },
        room=MAIN_ROOM
    )

    add_activity(
        "🟢",
        f"{player_data['display_name']} وارد شد",
        "به Game Room پیوست."
    )


@socketio.on("game_heartbeat")
def socket_heartbeat(data):

    info = user_sids.get(
            request.sid
        )

    if not info:
        return

    username = info["username"]

    connected_users[
        username
    ] = "online"


@socketio.on("game_profile_update")
def socket_profile_update(data):

    data = data or {}

    username = data.get(
        "username"
    )

    if not valid_username(username):
        return

    player = player_public(
        username
    )

    socketio.emit(
        "game_profile_update",
        player,
        room=MAIN_ROOM
    )


@socketio.on("game_chat_history")
def socket_chat_history():

    emit(
        "game_chat_history",
        {
            "messages":
                get_chat_history()
        }
    )


@socketio.on("game_chat")
def socket_chat(data):

    data = data or {}

    info = user_sids.get(
            request.sid
        )

    if not info:
        return

    username = info["username"]

    message = str(
        data.get(
            "message",
            ""
        )
    ).strip()

    if not message:
        return

    if len(message) > 500:

        emit(
            "game_chat_error",
            {
                "error":
                    "پیام خیلی طولانی است."
            }
        )

        return

    saved = save_chat_message(
            username,
            message,
            False
        )

    socketio.emit(
        "game_chat_message",
        saved,
        room=MAIN_ROOM
    )


@socketio.on("game_chat_image")
def socket_chat_image(data):

    data = data or {}

    info = user_sids.get(
            request.sid
        )

    if not info:
        return

    username = info["username"]

    image_url = str(
        data.get(
            "image_url",
            ""
        )
    ).strip()

    if not image_url:
        return

    saved = save_chat_message(
            username,
            image_url,
            True
        )

    socketio.emit(
        "game_chat_message",
        saved,
        room=MAIN_ROOM
    )


@socketio.on("game_status_update")
def socket_status_update(data):

    data = data or {}

    info = user_sids.get(
            request.sid
        )

    if not info:
        return

    username = info["username"]

    status = data.get(
        "status",
        "online"
    )

    if status not in {
        "online",
        "weak",
        "offline"
    }:
        status = "online"

    connected_users[
        username
    ] = status

    socketio.emit(
        "game_status_update",
        {
            "username": username,
            "status": status
        },
        room=MAIN_ROOM
    )


@socketio.on("game_open")
def socket_game_open(data):

    data = data or {}

    username = data.get(
        "username"
    )

    game_type = data.get(
        "game_type"
    )

    if game_type not in VALID_GAMES:
        return

    emit(
        "game_state_update",
        {
            "game_type": game_type,
            "game_state": {
                "phase": "waiting",
                "message":
                    "بازی در حال آماده‌سازی است."
            }
        }
    )


@socketio.on("game_leave")
def socket_game_leave(data):

    emit(
        "game_system_message",
        {
            "message":
                "از بازی خارج شدی."
        }
    )


# ========================================================= # ERROR HANDLERS
# =========================================================

@app.errorhandler(413)
def file_too_large(error):

    return jsonify({
        "error":
            "حجم فایل بیش از حد مجاز است."
    }), 413


@app.errorhandler(404)
def not_found(error):

    return jsonify({
        "success": False,
        "error":
            "مسیر موردنظر پیدا نشد."
    }), 404


@app.errorhandler(500)
def internal_error(error):

    return jsonify({
        "success": False,
        "error":
            "خطای داخلی سرور."
    }), 500


# ========================================================= # RUN
# =========================================================

if __name__ == "__main__":

    print("=" * 50)
    print("GAME ROOM BACKEND")
    print("=" * 50)
    print(
        f"Room: {MAIN_ROOM}"
    )
    print(
        f"Port: {PORT}"
    )
    print(
        f"Database: {DB_PATH}"
    )
    print("=" * 50)

    socketio.run(
        app,
        host=HOST,
        port=PORT,
        allow_unsafe_werkzeug=True
    )
