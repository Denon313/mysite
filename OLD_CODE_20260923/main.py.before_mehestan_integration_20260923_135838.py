import os
import json
import uuid
import secrets
import sqlite3
import traceback
from pathlib import Path
from functools import wraps
from datetime import datetime

from flask import (
    Flask,
    jsonify,
    request,
    send_from_directory
)
from flask_cors import CORS
from flask_socketio import (
    SocketIO,
    emit,
    join_room,
    leave_room
)


# ============================================================
# PATHS / CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

UPLOAD_DIR = PROJECT_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = BASE_DIR / "database.db"

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 5000))

ADMIN_PASSWORD = os.environ.get(
    "ADMIN_PASSWORD",
    "Mahdi1646"
)

FRONTEND_ORIGINS = os.environ.get(
    "FRONTEND_ORIGINS",
    "https://denon313.github.io,http://localhost:8000,http://127.0.0.1:8000"
)

FRONTEND_ORIGINS_LIST = [
    x.strip()
    for x in FRONTEND_ORIGINS.split(",")
    if x.strip()
]

MAIN_ROOM = "GAME_ROOM"

MAX_PLAYERS = 5
MAX_CHAT_MESSAGES = 200
MAX_MESSAGE_LENGTH = 500
MAX_PROFILE_NAME = 30

ALLOWED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif"
}


# ============================================================
# APP
# ============================================================

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
            "origins": FRONTEND_ORIGINS_LIST
        }
    }
)

socketio = SocketIO(
    app,
    cors_allowed_origins=FRONTEND_ORIGINS_LIST,
    async_mode="threading"
)


# ============================================================
# FIXED PLAYERS
# ============================================================

PLAYERS = {
    "mehdi": {
        "display_name": "مهدی",
        "role": "admin",
        "avatar": "",
        "emoji": "👑"
    },
    "rastin": {
        "display_name": "راستین",
        "role": "player",
        "avatar": "",
        "emoji": "🎮"
    },
    "amirali": {
        "display_name": "امیرعلی",
        "role": "player",
        "avatar": "",
        "emoji": "🎮"
    },
    "mahna": {
        "display_name": "مهنا",
        "role": "player",
        "avatar": "",
        "emoji": "🎮"
    },
    "fatemeh": {
        "display_name": "فاطمه",
        "role": "player",
        "avatar": "",
        "emoji": "🎮"
    }
}


# ============================================================
# RUNTIME STATE
# ============================================================

connected_users = {}
user_sids = {}

admin_sessions = set()

active_games = {}

chat_cache = []


# ============================================================
# DATABASE
# ============================================================

def get_db():
    conn = sqlite3.connect(
        DB_PATH,
        timeout=30,
        check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    return conn


def column_exists(conn, table_name, column_name):
    rows = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return any(
        row["name"] == column_name
        for row in rows
    )


def ensure_column(
    conn,
    table_name,
    column_name,
    definition
):
    if not column_exists(
        conn,
        table_name,
        column_name
    ):
        conn.execute(
            f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_name} {definition}
            """
        )


def init_database():
    conn = get_db()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS players (
            username TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            avatar_url TEXT DEFAULT '',
            role TEXT DEFAULT 'player',
            blocked INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            display_name TEXT NOT NULL,
            message TEXT NOT NULL,
            is_image INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    ensure_column(
        conn,
        "chat_messages",
        "game_id",
        "TEXT"
    )

    ensure_column(
        conn,
        "chat_messages",
        "reply_to",
        "INTEGER"
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS scenarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_type TEXT NOT NULL,
            title TEXT NOT NULL,
            data TEXT DEFAULT '{}',
            enabled INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            icon TEXT DEFAULT '🎮',
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rooms (
            id TEXT PRIMARY KEY,
            game_type TEXT DEFAULT '',
            status TEXT DEFAULT 'waiting',
            state TEXT DEFAULT '{}',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    for username, info in PLAYERS.items():
        existing = conn.execute(
            """
            SELECT username
            FROM players
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

        if not existing:
            conn.execute(
                """
                INSERT INTO players
                (
                    username,
                    display_name,
                    avatar_url,
                    role,
                    blocked
                )
                VALUES (?, ?, ?, ?, 0)
                """,
                (
                    username,
                    info["display_name"],
                    info.get("avatar", ""),
                    info["role"]
                )
            )

    existing_room = conn.execute(
        """
        SELECT id
        FROM rooms
        WHERE id = ?
        """,
        (MAIN_ROOM,)
    ).fetchone()

    if not existing_room:
        conn.execute(
            """
            INSERT INTO rooms
            (
                id,
                game_type,
                status,
                state
            )
            VALUES (?, '', 'waiting', '{}')
            """,
            (MAIN_ROOM,)
        )

    conn.commit()
    conn.close()


init_database()


# ============================================================
# BASIC HELPERS
# ============================================================

def now():
    return datetime.utcnow().isoformat()


def json_body():
    data = request.get_json(
        silent=True
    )

    if not isinstance(data, dict):
        return {}

    return data


def valid_username(username):
    return (
        isinstance(username, str)
        and username.strip().lower() in PLAYERS
    )


def normalize_username(username):
    if not isinstance(username, str):
        return ""

    username = username.strip().lower()

    if username not in PLAYERS:
        return ""

    return username


def get_player(username):
    username = normalize_username(username)

    if not username:
        return None

    conn = get_db()

    row = conn.execute(
        """
        SELECT *
        FROM players
        WHERE username = ?
        """,
        (username,)
    ).fetchone()

    conn.close()

    if not row:
        return None

    return dict(row)


def player_public(username):
    player = get_player(username)

    if not player:
        return None

    fixed = PLAYERS.get(
        username,
        {}
    )

    return {
        "username": player["username"],
        "display_name": player["display_name"],
        "avatar_url": player.get("avatar_url", ""),
        "role": player.get("role", "player"),
        "blocked": bool(player.get("blocked", 0)),
        "emoji": fixed.get("emoji", "🎮"),
        "online": username in connected_users
    }


def all_players():
    result = []

    for username in PLAYERS:
        player = player_public(username)

        if player:
            result.append(player)

    return result


def room_players():
    result = []

    for username in connected_users:
        player = player_public(username)

        if player:
            result.append(player)

    return result


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


def get_recent_activities(limit=30):
    conn = get_db()

    rows = conn.execute(
        """
        SELECT *
        FROM activities
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,)
    ).fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# CHAT DATABASE HELPERS
# ============================================================

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
            ORDER BY id ASC
            LIMIT ?
            """,
            (
                game_id,
                MAX_CHAT_MESSAGES
            )
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
            ORDER BY id ASC
            LIMIT ?
            """,
            (MAX_CHAT_MESSAGES,)
        ).fetchall()

    conn.close()

    return [
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


def save_chat_message(
    username,
    message,
    is_image=False,
    game_id=None,
    reply_to=None
):
    player = get_player(username)

    if not player:
        return None

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
            player["display_name"],
            message,
            1 if is_image else 0,
            game_id,
            reply_to
        )
    )

    conn.commit()

    message_id = cursor.lastrowid

    row = conn.execute(
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
        WHERE id = ?
        """,
        (message_id,)
    ).fetchone()

    conn.close()

    if not row:
        return None

    return {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "message": row["message"],
        "is_image": bool(row["is_image"]),
        "game_id": row["game_id"],
        "reply_to": row["reply_to"],
        "created_at": row["created_at"]
    }


# ============================================================
# ADMIN AUTH
# ============================================================

def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):

        token = (
            request.headers.get("X-Admin-Token")
            or request.args.get("admin_token")
        )

        if not token:
            return jsonify({
                "success": False,
                "error": "دسترسی مدیر لازم است."
            }), 401

        if token not in admin_sessions:
            return jsonify({
                "success": False,
                "error": "توکن مدیر معتبر نیست."
            }), 403

        return func(*args, **kwargs)

    return wrapper


# ============================================================
# FRONTEND
# ============================================================

@app.get("/")
def index():
    return send_from_directory(
        PROJECT_DIR,
        "index.html"
    )


@app.get("/health")
def health():
    return jsonify({
        "success": True,
        "status": "ok",
        "service": "Game Room"
    })


# ============================================================
# LOGIN
# ============================================================

@app.post("/api/game/login")
def login():

    data = json_body()

    username = normalize_username(
        data.get("username", "")
    )

    password = str(
        data.get("password", "")
    )

    if not username:
        return jsonify({
            "success": False,
            "error": "کاربر معتبر نیست."
        }), 401

    player = get_player(username)

    if not player:
        return jsonify({
            "success": False,
            "error": "کاربر پیدا نشد."
        }), 404

    if player["blocked"]:
        return jsonify({
            "success": False,
            "error": "حساب شما مسدود شده است."
        }), 403

    # Maintenance Mode:
    # فقط مهدی اجازه ورود دارد.
    if username != "mehdi":
        return jsonify({
            "success": False,
            "maintenance": True,
            "error": "سایت موقتاً در حال بروزرسانی است."
        }), 503

    response = {
        "success": True,
        "player": player_public(username)
    }

    if username == "mehdi":

        if password != ADMIN_PASSWORD:
            return jsonify({
                "success": False,
                "error": "رمز مدیر اشتباه است."
            }), 401

        admin_token = secrets.token_urlsafe(32)

        admin_sessions.add(
            admin_token
        )

        response["admin_token"] = admin_token
        response["is_admin"] = True

    return jsonify(response)


# ============================================================
# PROFILE
# ============================================================

@app.get("/api/game/profile/<username>")
def get_profile(username):

    username = normalize_username(username)

    if not username:
        return jsonify({
            "success": False,
            "error": "کاربر معتبر نیست."
        }), 404

    player = player_public(username)

    if not player:
        return jsonify({
            "success": False,
            "error": "کاربر پیدا نشد."
        }), 404

    return jsonify({
        "success": True,
        "player": player
    })


@app.post("/api/game/profile/<username>")
def update_profile(username):

    username = normalize_username(username)

    if not username:
        return jsonify({
            "success": False,
            "error": "کاربر معتبر نیست."
        }), 404

    data = json_body()

    display_name = str(
        data.get("display_name", "")
    ).strip()

    if not display_name:
        return jsonify({
            "success": False,
            "error": "نام نمی‌تواند خالی باشد."
        }), 400

    if len(display_name) > MAX_PROFILE_NAME:
        return jsonify({
            "success": False,
            "error": "نام خیلی طولانی است."
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

    return jsonify({
        "success": True,
        "player": player
    })


@app.post("/api/game/profile/<username>/avatar")
def upload_avatar(username):

    username = normalize_username(username)

    if not username:
        return jsonify({
            "success": False,
            "error": "کاربر معتبر نیست."
        }), 404

    if "avatar" not in request.files:
        return jsonify({
            "success": False,
            "error": "تصویر ارسال نشده."
        }), 400

    file = request.files["avatar"]

    if not file.filename:
        return jsonify({
            "success": False,
            "error": "فایل انتخاب نشده."
        }), 400

    extension = Path(
        file.filename
    ).suffix.lower()

    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        return jsonify({
            "success": False,
            "error": "فرمت تصویر مجاز نیست."
        }), 400

    filename = (
        f"avatar_{username}_"
        f"{uuid.uuid4().hex}"
        f"{extension}"
    )

    file.save(
        UPLOAD_DIR / filename
    )

    url = f"/uploads/{filename}"

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


# ============================================================
# UPLOADS
# ============================================================

@app.get("/uploads/<path:filename>")
def uploaded_file(filename):

    return send_from_directory(
        UPLOAD_DIR,
        filename
    )


# ============================================================
# PLAYERS
# ============================================================

@app.get("/api/game/players")
def players():

    return jsonify({
        "players": all_players()
    })


# ============================================================
# ACTIVITIES
# ============================================================

@app.get("/api/game/activity")
def activities():

    return jsonify({
        "activities":
            get_recent_activities()
    })


# ============================================================
# MAIN CHAT IMAGE UPLOAD
# ============================================================

@app.post("/api/game/chat/upload")
def chat_upload():

    username = normalize_username(
        request.form.get(
            "username",
            ""
        )
    )

    if not username:
        return jsonify({
            "error": "کاربر معتبر نیست."
        }), 401

    if "image" not in request.files:
        return jsonify({
            "error": "تصویر ارسال نشده."
        }), 400

    file = request.files["image"]

    if not file.filename:
        return jsonify({
            "error": "فایل انتخاب نشده."
        }), 400

    extension = Path(
        file.filename
    ).suffix.lower()

    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        return jsonify({
            "error": "فرمت تصویر مجاز نیست."
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
        "url": f"/uploads/{filename}"
    })


# ============================================================
# ROOM
# ============================================================

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


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.get("/api/game/admin/dashboard")
@admin_required
def admin_dashboard():

    online_count = sum(
        1
        for status in connected_users.values()
        if status == "online"
    )

    weak_count = sum(
        1
        for status in connected_users.values()
        if status == "weak"
    )

    return jsonify({
        "success": True,
        "online_count": online_count,
        "weak_count": weak_count,
        "offline_count": max(
            0,
            MAX_PLAYERS -
            online_count -
            weak_count
        ),
        "active_rooms": 1,
        "games_running": len(active_games),
        "players": all_players()
    })


@app.post("/api/game/admin/block/<username>")
@admin_required
def block_player(username):

    username = normalize_username(username)

    if not username:
        return jsonify({
            "error": "کاربر پیدا نشد."
        }), 404

    if username == "mehdi":
        return jsonify({
            "error": "مدیر قابل مسدود کردن نیست."
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


@app.post("/api/game/admin/unblock/<username>")
@admin_required
def unblock_player(username):

    username = normalize_username(username)

    if not username:
        return jsonify({
            "error": "کاربر پیدا نشد."
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


# ============================================================
# SCENARIOS
# ============================================================

@app.get("/api/game/scenarios")
def get_scenarios():

    game_type = str(
        request.args.get(
            "game_type",
            ""
        )
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

    return jsonify({
        "scenarios": [
            dict(row)
            for row in rows
        ]
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


# ============================================================
# SPY DEBUG
# ============================================================

@app.get("/api/game/spy-lobby-debug")
def spy_lobby_debug():

    try:
        from spy_game import spy_engine

        state = spy_engine.lobby_state()

        return jsonify({
            "success": True,
            "players": state.get(
                "players",
                []
            ),
            "count": len(
                state.get(
                    "players",
                    []
                )
            ),
            "host": state.get("host"),
            "phase": state.get("phase"),
            "game_id": state.get("game_id"),
            "remaining_seconds":
                state.get(
                    "remaining_seconds",
                    0
                ),
            "connected_users":
                list(
                    connected_users.keys()
                )
        })

    except Exception as error:

        return jsonify({
            "success": False,
            "error": str(error)
        }), 500


# ============================================================
# GAME MANAGEMENT
# ============================================================

VALID_GAMES = {
    "spy",
    "mystery",
    "forbidden"
}


@app.post("/api/game/start")
def start_game():

    data = json_body()

    username = normalize_username(
        data.get(
            "username",
            ""
        )
    )

    game_type = str(
        data.get(
            "game_type",
            ""
        )
    ).strip()

    if not username:
        return jsonify({
            "success": False,
            "error": "کاربر معتبر نیست."
        }), 401

    if game_type not in VALID_GAMES:
        return jsonify({
            "success": False,
            "error": "بازی معتبر نیست."
        }), 400

    if username != "mehdi":
        return jsonify({
            "success": False,
            "error": "فقط مدیر می‌تواند بازی را شروع کند."
        }), 403

    if game_type == "spy":

        try:
            from spy_game import spy_engine

            discussion_seconds = int(
                data.get(
                    "discussion_seconds",
                    120
                )
            )

            discussion_seconds = max(
                10,
                min(
                    3600,
                    discussion_seconds
                )
            )

            result = spy_engine.start(
                username,
                discussion_seconds
            )

            if not result.get("success", False):
                return jsonify(result), 400

            return jsonify(result)

        except Exception as error:

            traceback.print_exc()

            return jsonify({
                "success": False,
                "error": "خطا در شروع بازی جاسوس.",
                "detail": str(error)
            }), 500

    return jsonify({
        "success": False,
        "error": "این بازی هنوز فعال نشده است."
    }), 400


# ============================================================
# SOCKET HELPERS
# ============================================================

def get_socket_username():

    info = user_sids.get(
        request.sid
    )

    if not info:
        return None

    return info.get("username")


def emit_main_players():

    socketio.emit(
        "game_players_update",
        {
            "players": all_players()
        },
        room=MAIN_ROOM
    )


# ============================================================
# SOCKET CONNECT
# ============================================================

@socketio.on("connect")
def socket_connect():

    print(
        "Socket connected:",
        request.sid,
        flush=True
    )


# ============================================================
# SOCKET DISCONNECT
# ============================================================

@socketio.on("disconnect")
def socket_disconnect():

    sid = request.sid

    info = user_sids.pop(
        sid,
        None
    )

    if not info:
        return

    username = info.get(
        "username"
    )

    if not username:
        return

    # Spy connection is handled by spy_game.py.
    try:
        from spy_game import disconnect_spy_user

        disconnect_spy_user(
            username
        )
    except Exception:
        pass

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

    emit_main_players()


# ============================================================
# MAIN ROOM JOIN
# ============================================================

@socketio.on("game_join")
def socket_join(data):

    data = data or {}

    username = normalize_username(
        data.get(
            "username",
            ""
        )
    )

    if not username:

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

    # اگر همین کاربر قبلاً با Socket دیگری وارد شده،
    # Socket جدید جای قبلی را می‌گیرد.
    for old_sid, info in list(
        user_sids.items()
    ):
        if (
            info.get("username") == username
            and old_sid != request.sid
        ):
            user_sids.pop(
                old_sid,
                None
            )

    if (
        username not in connected_users
        and len(connected_users) >= MAX_PLAYERS
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
            "player": player_data,
            "players": all_players(),
            "messages": get_chat_history()
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

    emit_main_players()

    add_activity(
        "🟢",
        f"{player_data['display_name']} وارد شد",
        "به Game Room پیوست."
    )


# ============================================================
# HEARTBEAT
# ============================================================

@socketio.on("game_heartbeat")
def socket_heartbeat(data=None):

    username = get_socket_username()

    if not username:
        return

    connected_users[
        username
    ] = "online"


# ============================================================
# PROFILE UPDATE EVENT
# ============================================================

@socketio.on("game_profile_update")
def socket_profile_update(data):

    data = data or {}

    username = normalize_username(
        data.get(
            "username",
            ""
        )
    )

    if not username:
        return

    player = player_public(
        username
    )

    if not player:
        return

    socketio.emit(
        "game_profile_update",
        player,
        room=MAIN_ROOM
    )


# ============================================================
# MAIN CHAT HISTORY
# ============================================================

@socketio.on("game_chat_history")
def socket_chat_history(data=None):

    data = data or {}

    username = get_socket_username()

    if not username:
        return

    game_id = str(
        data.get(
            "game_id",
            ""
        )
    ).strip() or None

    if game_id:

        game = active_games.get(
            game_id
        )

        if not game:
            emit(
                "game_chat_error",
                {
                    "error":
                        "این بازی دیگر فعال نیست."
                }
            )
            return

        if username not in game.get(
            "players",
            []
        ):
            emit(
                "game_chat_error",
                {
                    "error":
                        "شما عضو این بازی نیستید."
                }
            )
            return

    emit(
        "game_chat_history",
        {
            "messages":
                get_chat_history(
                    game_id
                )
        }
    )


# ============================================================
# MAIN CHAT
# ============================================================

@socketio.on("game_chat")
def socket_chat(data):

    data = data or {}

    username = get_socket_username()

    if not username:
        return

    message = str(
        data.get(
            "message",
            ""
        )
    ).strip()

    game_id = str(
        data.get(
            "game_id",
            ""
        )
    ).strip() or None

    reply_to = data.get(
        "reply_to"
    )

    if not message:
        return

    if len(message) > MAX_MESSAGE_LENGTH:

        emit(
            "game_chat_error",
            {
                "error":
                    "پیام خیلی طولانی است."
            }
        )

        return

    if game_id:

        game = active_games.get(
            game_id
        )

        if not game:

            emit(
                "game_chat_error",
                {
                    "error":
                        "این بازی دیگر فعال نیست."
                }
            )

            return

        if username not in game.get(
            "players",
            []
        ):

            emit(
                "game_chat_error",
                {
                    "error":
                        "شما عضو این بازی نیستید."
                }
            )

            return

    saved = save_chat_message(
        username,
        message,
        False,
        game_id,
        reply_to
    )

    if not saved:
        return

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


# ============================================================
# CHAT IMAGE
# ============================================================

@socketio.on("game_chat_image")
def socket_chat_image(data):

    data = data or {}

    username = get_socket_username()

    if not username:
        return

    image_url = str(
        data.get(
            "image_url",
            ""
        )
    ).strip()

    game_id = str(
        data.get(
            "game_id",
            ""
        )
    ).strip() or None

    reply_to = data.get(
        "reply_to"
    )

    if not image_url:
        return

    if game_id:

        game = active_games.get(
            game_id
        )

        if not game:

            emit(
                "game_chat_error",
                {
                    "error":
                        "این بازی دیگر فعال نیست."
                }
            )

            return

        if username not in game.get(
            "players",
            []
        ):

            emit(
                "game_chat_error",
                {
                    "error":
                        "شما عضو این بازی نیستید."
                }
            )

            return

    saved = save_chat_message(
        username,
        image_url,
        True,
        game_id,
        reply_to
    )

    if not saved:
        return

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


# ============================================================
# DELETE OWN CHAT MESSAGE
# ============================================================

@socketio.on("game_chat_delete")
def socket_chat_delete(data):

    data = data or {}

    username = get_socket_username()

    if not username:
        return

    try:
        message_id = int(
            data.get(
                "message_id"
            )
        )
    except (
        TypeError,
        ValueError
    ):
        return

    game_id = str(
        data.get(
            "game_id",
            ""
        )
    ).strip() or None

    conn = get_db()

    row = conn.execute(
        """
        SELECT *
        FROM chat_messages
        WHERE id = ?
        """,
        (message_id,)
    ).fetchone()

    if not row:

        conn.close()

        emit(
            "game_chat_error",
            {
                "error":
                    "پیام پیدا نشد."
            }
        )

        return

    if row["username"] != username:

        conn.close()

        emit(
            "game_chat_error",
            {
                "error":
                    "فقط فرستنده پیام می‌تواند آن را حذف کند."
            }
        )

        return

    if (
        game_id is not None
        and row["game_id"] != game_id
    ):

        conn.close()
        return

    conn.execute(
        """
        DELETE FROM chat_messages
        WHERE id = ?
        """,
        (message_id,)
    )

    conn.commit()
    conn.close()

    target_room = (
        f"game_{game_id}"
        if game_id
        else MAIN_ROOM
    )

    socketio.emit(
        "game_chat_deleted",
        {
            "message_id": message_id,
            "username": username
        },
        room=target_room
    )


# ============================================================
# STATUS UPDATE
# ============================================================

@socketio.on("game_status_update")
def socket_status_update(data):

    data = data or {}

    username = get_socket_username()

    if not username:
        return

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


# ============================================================
# OPEN GAME
# ============================================================

@socketio.on("game_open")
def socket_game_open(data):

    data = data or {}

    username = get_socket_username()

    if not username:
        username = normalize_username(
            data.get(
                "username",
                ""
            )
        )

    game_type = str(
        data.get(
            "game_type",
            ""
        )
    ).strip()

    game_id = str(
        data.get(
            "game_id",
            ""
        )
    ).strip()

    if game_type not in VALID_GAMES:
        return

    if not username:
        return

    game = None

    if game_id:
        game = active_games.get(
            game_id
        )

    if (
        game is None
        and game_type == "spy"
    ):
        try:
            from spy_game import spy_engine

            state = spy_engine.state_for(
                username
            )

            if state:
                game_id = state.get(
                    "game_id"
                )

        except Exception:
            pass

    if game is not None:

        if username not in game.get(
            "players",
            []
        ):
            emit(
                "game_error",
                {
                    "error":
                        "شما عضو این بازی نیستید."
                }
            )
            return

        game_room = (
            f"game_{game_id}"
        )

        join_room(
            game_room
        )

        emit(
            "game_room_joined",
            {
                "game_id": game_id,
                "game_type": game_type,
                "messages":
                    get_chat_history(
                        game_id
                    )
            }
        )

        return

    # Spy state is managed independently.
    if game_type == "spy":

        try:
            from spy_game import spy_engine

            state = spy_engine.state_for(
                username
            )

            if state:

                game_id = state.get(
                    "game_id"
                )

                if game_id:

                    join_room(
                        f"game_{game_id}"
                    )

                emit(
                    "game_room_joined",
                    {
                        "game_id": game_id,
                        "game_type": "spy",
                        "messages":
                            get_chat_history(
                                game_id
                            )
                    }
                )

                return

        except Exception:
            traceback.print_exc()

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


# ============================================================
# GAME LEAVE
# ============================================================

@socketio.on("game_leave")
def socket_game_leave(data=None):

    emit(
        "game_system_message",
        {
            "message":
                "از بازی خارج شدی."
        }
    )


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(413)
def file_too_large(error):

    return jsonify({
        "success": False,
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


# ============================================================
# SPY ENGINE
# ============================================================

try:

    from spy_game import register_spy_socket

    register_spy_socket(
        socketio,
        get_socket_username
    )

    print(
        "SPY ENGINE: loaded successfully",
        flush=True
    )

except Exception as error:

    print(
        "SPY ENGINE LOAD ERROR:",
        repr(error),
        flush=True
    )

    traceback.print_exc()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("GAME ROOM BACKEND")
    print("=" * 60)
    print(f"Room: {MAIN_ROOM}")
    print(f"Port: {PORT}")
    print(f"Database: {DB_PATH}")
    print("Spy Engine: enabled")
    print("=" * 60)

    socketio.run(
        app,
        host=HOST,
        port=PORT,
        allow_unsafe_werkzeug=True
    )
