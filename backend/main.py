# -*- coding: utf-8 -*-

import os
import sqlite3
import uuid
import time
import traceback
import secrets
import random
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
    conn.execute("PRAGMA foreign_keys = ON")

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

    chat_columns = {
        row["name"]
        for row in conn.execute(
            "PRAGMA table_info(chat_messages)"
        ).fetchall()
    }

    if "game_id" not in chat_columns:
        conn.execute(
            "ALTER TABLE chat_messages ADD COLUMN game_id TEXT DEFAULT NULL"
        )

    if "reply_to" not in chat_columns:
        conn.execute(
            "ALTER TABLE chat_messages ADD COLUMN reply_to INTEGER DEFAULT NULL"
        )

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

    # ========================================================
    # SPY WORD BANK
    # ========================================================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS spy_words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL UNIQUE,
            enabled INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS spy_word_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word_id INTEGER NOT NULL,
            alias TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(word_id, alias),
            FOREIGN KEY(word_id)
                REFERENCES spy_words(id)
                ON DELETE CASCADE
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
# ========================================================= # HELPERS
# =========================================================

def now():

    return datetime.utcnow().isoformat()


def player_exists(username):

    return username in PLAYERS


def get_active_spy_words():
    conn = get_db()

    rows = conn.execute(
        """
        SELECT id, word
        FROM spy_words
        WHERE enabled = 1
        ORDER BY id ASC
        """
    ).fetchall()

    result = []

    for row in rows:
        aliases = conn.execute(
            """
            SELECT alias
            FROM spy_word_aliases
            WHERE word_id = ?
            ORDER BY id ASC
            """,
            (row["id"],)
        ).fetchall()

        result.append(
            {
                "word": row["word"],
                "aliases": [
                    alias["alias"]
                    for alias in aliases
                ],
            }
        )

    conn.close()

    return result


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


def get_chat_history(game_id=None):

    conn = get_db()

    if game_id:
        rows = conn.execute(
            """
            SELECT
                id,
                username,
                display_name,
                message,
                is_image,
                game_id,
                reply_to,
                created_at
            FROM chat_messages
            WHERE game_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (game_id, MAX_CHAT_MESSAGES)
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT
                id,
                username,
                display_name,
                message,
                is_image,
                game_id,
                reply_to,
                created_at
            FROM chat_messages
            WHERE game_id IS NULL
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
            "is_image": bool(row["is_image"]),
            "game_id": row["game_id"],
            "reply_to": row["reply_to"],
            "created_at": row["created_at"]
        }
        for row in rows
    ]

    result.reverse()
    return result


def save_chat_message(
    username,
    message,
    is_image=False,
    game_id=None,
    reply_to=None
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
            is_image,
            game_id,
            reply_to
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            username,
            display_name,
            message,
            int(is_image),
            game_id,
            reply_to
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
        "game_id": game_id,
        "reply_to": reply_to,
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


# =========================================================
# SPY WORD BANK - ADMIN: LIST
# =========================================================

@app.get("/api/game/admin/spy-words")
@admin_required
def admin_list_spy_words():
    conn = get_db()

    rows = conn.execute(
        """
        SELECT
            id,
            word,
            enabled,
            created_at,
            updated_at
        FROM spy_words
        ORDER BY id ASC
        """
    ).fetchall()

    result = []

    for row in rows:
        aliases = conn.execute(
            """
            SELECT alias
            FROM spy_word_aliases
            WHERE word_id = ?
            ORDER BY id ASC
            """,
            (row["id"],)
        ).fetchall()

        result.append({
            "id": row["id"],
            "word": row["word"],
            "enabled": bool(row["enabled"]),
            "aliases": [item["alias"] for item in aliases],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        })

    conn.close()

    return jsonify({
        "success": True,
        "words": result,
        "count": len(result),
    })


# =========================================================
# SPY WORD BANK - ADMIN: ADD
# =========================================================

@app.post("/api/game/admin/spy-words")
@admin_required
def admin_add_spy_word():
    data = json_body()

    word = str(data.get("word", "")).strip()
    aliases = data.get("aliases", [])

    if not word:
        return jsonify({
            "success": False,
            "error": "کلمه الزامی است."
        }), 400

    if not isinstance(aliases, list):
        return jsonify({
            "success": False,
            "error": "aliases باید به صورت لیست باشد."
        }), 400

    cleaned_aliases = []
    for alias in aliases:
        alias = str(alias).strip()
        if alias and alias not in cleaned_aliases:
            cleaned_aliases.append(alias)

    conn = get_db()

    try:
        cursor = conn.execute(
            """
            INSERT INTO spy_words (word, enabled, updated_at)
            VALUES (?, 1, CURRENT_TIMESTAMP)
            """,
            (word,)
        )

        word_id = cursor.lastrowid

        for alias in cleaned_aliases:
            conn.execute(
                """
                INSERT INTO spy_word_aliases (word_id, alias)
                VALUES (?, ?)
                """,
                (word_id, alias)
            )

        conn.commit()

    except sqlite3.IntegrityError:
        conn.rollback()
        conn.close()

        return jsonify({
            "success": False,
            "error": "این کلمه قبلاً وجود دارد."
        }), 409

    conn.close()

    return jsonify({
        "success": True,
        "id": word_id,
        "word": word,
        "aliases": cleaned_aliases
    }), 201


# =========================================================
# SPY WORD BANK - ADMIN: EDIT
# =========================================================

@app.put("/api/game/admin/spy-words/<int:word_id>")
@admin_required
def admin_edit_spy_word(word_id):
    data = json_body()

    word = str(data.get("word", "")).strip()
    aliases = data.get("aliases", [])
    enabled = data.get("enabled", 1)

    if not word:
        return jsonify({
            "success": False,
            "error": "کلمه الزامی است."
        }), 400

    if not isinstance(aliases, list):
        return jsonify({
            "success": False,
            "error": "aliases باید به صورت لیست باشد."
        }), 400

    cleaned_aliases = []
    for alias in aliases:
        alias = str(alias).strip()
        if alias and alias not in cleaned_aliases:
            cleaned_aliases.append(alias)

    enabled = 1 if bool(enabled) else 0

    conn = get_db()

    existing = conn.execute(
        """
        SELECT id
        FROM spy_words
        WHERE id = ?
        """,
        (word_id,)
    ).fetchone()

    if not existing:
        conn.close()
        return jsonify({
            "success": False,
            "error": "کلمه پیدا نشد."
        }), 404

    try:
        conn.execute(
            """
            UPDATE spy_words
            SET word = ?,
                enabled = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (word, enabled, word_id)
        )

        conn.execute(
            """
            DELETE FROM spy_word_aliases
            WHERE word_id = ?
            """,
            (word_id,)
        )

        for alias in cleaned_aliases:
            conn.execute(
                """
                INSERT INTO spy_word_aliases (word_id, alias)
                VALUES (?, ?)
                """,
                (word_id, alias)
            )

        conn.commit()

    except sqlite3.IntegrityError:
        conn.rollback()
        conn.close()

        return jsonify({
            "success": False,
            "error": "این کلمه قبلاً وجود دارد."
        }), 409

    conn.close()

    return jsonify({
        "success": True,
        "id": word_id,
        "word": word,
        "enabled": bool(enabled),
        "aliases": cleaned_aliases
    })


# =========================================================
# SPY WORD BANK - ADMIN: DELETE
# =========================================================

@app.delete("/api/game/admin/spy-words/<int:word_id>")
@admin_required
def admin_delete_spy_word(word_id):
    conn = get_db()

    existing = conn.execute(
        """
        SELECT id, word
        FROM spy_words
        WHERE id = ?
        """,
        (word_id,)
    ).fetchone()

    if not existing:
        conn.close()
        return jsonify({
            "success": False,
            "error": "کلمه پیدا نشد."
        }), 404

    conn.execute(
        """
        DELETE FROM spy_words
        WHERE id = ?
        """,
        (word_id,)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "deleted_id": word_id,
        "word": existing["word"]
    })


# =========================================================
# SPY WORD BANK - ADMIN: TOGGLE
# =========================================================

@app.patch("/api/game/admin/spy-words/<int:word_id>/toggle")
@admin_required
def admin_toggle_spy_word(word_id):
    conn = get_db()

    existing = conn.execute(
        """
        SELECT id, word, enabled
        FROM spy_words
        WHERE id = ?
        """,
        (word_id,)
    ).fetchone()

    if not existing:
        conn.close()
        return jsonify({
            "success": False,
            "error": "کلمه پیدا نشد."
        }), 404

    new_enabled = 0 if existing["enabled"] else 1

    conn.execute(
        """
        UPDATE spy_words
        SET enabled = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (new_enabled, word_id)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "id": word_id,
        "word": existing["word"],
        "enabled": bool(new_enabled)
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


@app.get("/api/game/spy-lobby-debug")
def spy_lobby_debug():
    state = spy_engine.lobby_state()
    return jsonify({
        "success": True,
        "players": state.get("players", []),
        "count": state.get("count", 0),
        "host": state.get("host"),
        "connected_users": list(connected_users.keys())
    })


@app.post("/api/game/start")
def start_game():
    try:
        return _start_game_debug()
    except Exception as error:
        print(
            "START GAME ERROR:",
            repr(error),
            flush=True
        )
        traceback.print_exc()

        return jsonify({
            "error": "START_GAME_DEBUG_ERROR",
            "exception": repr(error),
            "traceback": traceback.format_exc()
        }), 500


def _start_game_debug():
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

    # ========================================================
    # MYSTERY / FORBIDDEN
    # ========================================================

    # فعلاً قوانین قبلی این دو بازی حفظ می‌شود:
    # فقط مدیر اجازه شروع دارد.
    if PLAYERS.get(username, {}).get("role") != "admin":
        return jsonify({
            "error": "فقط مدیر می‌تواند بازی را شروع کند."
        }), 403

    if game_type == "mystery":
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
            "players": players
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

    # اگر کاربر هنوز با Socket دیگری وصل است،
    # فعلاً او را Offline نکن.
    still_connected = any(
        item.get("username") == username
        for item in user_sids.values()
    )

    if not still_connected:

        # اطلاع به موتور جدید Spy برای مدیریت disconnect/reconnect
        try:
            disconnect_spy_user(username)
        except Exception as exc:
            print(
                "Spy disconnect error:",
                username,
                exc,
            )

        if username in connected_users:
            connected_users.pop(
                username,
                None
            )

        socketio.emit(
            "game_status_update",
            {
                "username": username,
                "status": "offline"
            },
            room=MAIN_ROOM
        )

    leave_room(
        MAIN_ROOM
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
def socket_chat_history(data=None):
    data = data or {}

    info = user_sids.get(request.sid)
    if not info:
        return

    username = info["username"]

    game_id = str(
        data.get("game_id", "")
    ).strip() or None

    if game_id:
        game = active_games.get(game_id)

        if not game:
            emit(
                "game_chat_error",
                {"error": "این بازی دیگر فعال نیست."}
            )
            return

        if hasattr(game, "players"):
            is_member = username in game.players
        else:
            is_member = username in game.get("players", [])

        if not is_member:
            emit(
                "game_chat_error",
                {"error": "شما عضو این بازی نیستید."}
            )
            return

    emit(
        "game_chat_history",
        {
            "messages": get_chat_history(game_id)
        }
    )


@socketio.on("game_chat")
def socket_chat(data):
    data = data or {}

    info = user_sids.get(request.sid)
    if not info:
        return

    username = info["username"]

    message = str(
        data.get("message", "")
    ).strip()

    game_id = str(
        data.get("game_id", "")
    ).strip() or None

    if not message:
        return

    if len(message) > 500:
        emit(
            "game_chat_error",
            {
                "error": "پیام خیلی طولانی است."
            }
        )
        return

    if game_id:
        game = active_games.get(game_id)

        if not game:
            emit(
                "game_chat_error",
                {"error": "این بازی دیگر فعال نیست."}
            )
            return

        if hasattr(game, "players"):
            is_member = username in game.players
        else:
            is_member = username in game.get("players", [])

        if not is_member:
            emit(
                "game_chat_error",
                {"error": "شما عضو این بازی نیستید."}
            )
            return

    saved = save_chat_message(
        username,
        message,
        False,
        game_id
    )

    target_room = (
        f"game_{game_id}"
        if game_id
        else MAIN_ROOM
    )

    socketio.emit(
        "game_chat_message",
        saved,
        room=target_room
    )


@socketio.on("game_chat_image")
def socket_chat_image(data):
    data = data or {}

    info = user_sids.get(request.sid)
    if not info:
        return

    username = info["username"]

    image_url = str(
        data.get("image_url", "")
    ).strip()

    game_id = str(
        data.get("game_id", "")
    ).strip() or None

    if not image_url:
        return

    if game_id:
        game = active_games.get(game_id)

        if not game:
            emit(
                "game_chat_error",
                {"error": "این بازی دیگر فعال نیست."}
            )
            return

        if hasattr(game, "players"):
            is_member = username in game.players
        else:
            is_member = username in game.get("players", [])

        if not is_member:
            emit(
                "game_chat_error",
                {"error": "شما عضو این بازی نیستید."}
            )
            return

    saved = save_chat_message(
        username,
        image_url,
        True,
        game_id
    )

    target_room = (
        f"game_{game_id}"
        if game_id
        else MAIN_ROOM
    )

    socketio.emit(
        "game_chat_message",
        saved,
        room=target_room
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

    username = get_socket_username()

    game_type = str(
        data.get("game_type", "")
    ).strip()

    game_id = str(
        data.get("game_id", "")
    ).strip()

    if not username:
        emit(
            "game_error",
            {
                "error": "نشست کاربر معتبر نیست."
            }
        )
        return

    if game_type not in VALID_GAMES:
        return

    # ========================================================
    # LEGACY — Mystery / Forbidden
    # ========================================================

    game = None

    if game_id:
        game = active_games.get(game_id)

    if game is not None:

        if hasattr(game, "get"):
            players = game.get(
                "players",
                []
            )

            if username not in players:
                emit(
                    "game_error",
                    {
                        "error": "شما عضو این بازی نیستید."
                    }
                )
                return

            game_room = f"game_{game_id}"

            join_room(game_room)

            emit(
                "game_room_joined",
                {
                    "game_id": game_id,
                    "game_type": game_type,
                    "messages": get_chat_history(game_id)
                }
            )

            emit(
                "game_state_update",
                {
                    "game_type": game_type,
                    "game_id": game_id,
                    "game_state": {
                        "phase": game.get("phase"),
                        "phase_ends_at": game.get(
                            "phase_ends_at"
                        ),
                        "message": "بازی آماده است."
                    }
                }
            )

            return

    emit(
        "game_state_update",
        {
            "game_type": game_type,
            "game_state": {
                "phase": "waiting",
                "message": "بازی در حال آماده‌سازی است."
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


# ============================================================
# SPY GAME ENGINE
# ============================================================

from spy_game import (
    register_spy_socket,
    disconnect_spy_user,
    spy_engine,
)

def get_socket_username():
    info = user_sids.get(request.sid)
    if not info:
        return None
    return info.get("username")


register_spy_socket(
    socketio,
    save_chat_callback=save_chat_message,
    get_chat_history_callback=get_chat_history,
    get_socket_username_callback=get_socket_username,
    get_spy_words_callback=get_active_spy_words
)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print("GAME ROOM BACKEND")
    print("=" * 50)
    print(f"Room: {MAIN_ROOM}")
    print(f"Port: {PORT}")
    print(f"Database: {DB_PATH}")
    print("=" * 50)

    socketio.run(
        app,
        host=HOST,
        port=PORT,
        allow_unsafe_werkzeug=True
    )
