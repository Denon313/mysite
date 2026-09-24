from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
from zoneinfo import ZoneInfo
import uuid

app = Flask(__name__)

CORS(
    app,
    resources={
        r"/*": {
            "origins": "*"
        }
    }
)

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="eventlet"
)

# =========================================================
# GAME CONFIG
# =========================================================

ROOM_ID = "GAME_ROOM"
MAX_PLAYERS = 5
MIN_PLAYERS = 2

PLAYERS = {
    "mehdi": {
        "username": "mehdi",
        "name": "مهدی",
        "title": "کارآگاه",
        "admin": True,
    },
    "rastin": {
        "username": "rastin",
        "name": "راستین",
        "title": "کارآگاه",
        "admin": False,
    },
    "amirali": {
        "username": "amirali",
        "name": "امیرعلی",
        "title": "کارآگاه",
        "admin": False,
    },
    "mahna": {
        "username": "mahna",
        "name": "مهنا",
        "title": "کارآگاه",
        "admin": False,
    },
    "fatemeh": {
        "username": "fatemeh",
        "name": "فاطمه",
        "title": "کارآگاه",
        "admin": False,
    },
}

# اتصال فعلی کاربران
USER_SIDS = {}

# وضعیت کاربران
USER_STATUS = {}

# چت تیم
CHAT_MESSAGES = []

# رویدادهای بازی
GAME_EVENTS = []

# وضعیت پرونده
GAME_STATE = {
    "game": "mystery",
    "title": "پرونده مرموز — شهر مهستان",
    "city": "مهستان",
    "phase": "lobby",
    "started": False,
    "scenario": {
        "title": "پرونده مرموز — شهر مهستان",
        "text": (
            "در شهر مهستان، پرونده‌ای مرموز آغاز شده است. "
            "شما و تیم کارآگاهان باید حقیقت را پیدا کنید، "
            "مدارک را بررسی کنید و ارتباط میان افراد شهر را کشف کنید."
        ),
    },
}

# =========================================================
# TIME
# =========================================================

def iran_time():
    return datetime.now(
        ZoneInfo("Asia/Tehran")
    ).isoformat()


# =========================================================
# HELPERS
# =========================================================

def get_player(username):
    return PLAYERS.get(username)


def player_exists(username):
    return username in PLAYERS


def connected_count():
    return len(USER_SIDS)


def public_players():
    result = []

    for username, player in PLAYERS.items():
        sid = USER_SIDS.get(username)

        if sid:
            status = USER_STATUS.get(username, "online")
        else:
            status = "offline"

        result.append({
            "username": username,
            "name": player["name"],
            "title": player["title"],
            "admin": player["admin"],
            "status": status,
            "online": bool(sid),
        })

    return result


def public_state():
    return {
        "room": ROOM_ID,
        "max_players": MAX_PLAYERS,
        "min_players": MIN_PLAYERS,
        "connected_players": connected_count(),
        "players": public_players(),
        "game": GAME_STATE,
        "chat": CHAT_MESSAGES[-100:],
        "events": GAME_EVENTS[-100:],
        "server_time": iran_time(),
    }


def broadcast_state():
    socketio.emit(
        "game_state",
        public_state(),
        room=ROOM_ID
    )


def add_event(event_type, text, username=None):
    event = {
        "id": str(uuid.uuid4()),
        "type": event_type,
        "text": text,
        "username": username,
        "time": iran_time(),
    }

    GAME_EVENTS.append(event)

    if len(GAME_EVENTS) > 200:
        del GAME_EVENTS[:-200]

    return event


# =========================================================
# BASIC HTTP ROUTES
# =========================================================

@app.get("/")
def home():
    return jsonify({
        "success": True,
        "message": "Mehestan Mystery Case backend is running",
        "game": "پرونده مرموز — شهر مهستان",
        "room": ROOM_ID,
    })


@app.get("/health")
def health():
    return jsonify({
        "success": True,
        "status": "ok",
        "game": "mehestan",
        "room": ROOM_ID,
        "players": connected_count(),
        "time": iran_time(),
    })


@app.get("/api/state")
def api_state():
    return jsonify({
        "success": True,
        "state": public_state(),
    })


# =========================================================
# LOGIN
# =========================================================

@app.post("/api/game/login")
def login():
    data = request.get_json(silent=True) or {}

    username = str(
        data.get("username", "")
    ).strip().lower()

    if not username:
        return jsonify({
            "success": False,
            "message": "نام کاربری وارد نشده است.",
        }), 400

    player = get_player(username)

    if not player:
        return jsonify({
            "success": False,
            "message": "این کاربر در اتاق تعریف نشده است.",
        }), 404

    if username in USER_SIDS:
        return jsonify({
            "success": False,
            "message": "این کاربر در حال حاضر وارد بازی است.",
        }), 409

    if connected_count() >= MAX_PLAYERS:
        return jsonify({
            "success": False,
            "message": "ظرفیت اتاق تکمیل است.",
        }), 403

    return jsonify({
        "success": True,
        "message": "ورود موفق بود.",
        "player": {
            "username": player["username"],
            "name": player["name"],
            "title": player["title"],
            "admin": player["admin"],
        },
        "room": ROOM_ID,
    })


# =========================================================
# SOCKET CONNECTION
# =========================================================

@socketio.on("connect")
def handle_connect():
    emit("connection_ok", {
        "success": True,
        "message": "اتصال به سرور برقرار شد.",
        "time": iran_time(),
    })


@socketio.on("disconnect")
def handle_disconnect():
    username = None

    for user, sid in list(USER_SIDS.items()):
        if sid == request.sid:
            username = user
            break

    if not username:
        return

    USER_SIDS.pop(username, None)
    USER_STATUS[username] = "offline"

    add_event(
        "player_offline",
        f"{PLAYERS[username]['name']} از بازی خارج شد.",
        username
    )

    broadcast_state()


# =========================================================
# JOIN GAME
# =========================================================

@socketio.on("game_join")
def game_join(data):
    data = data or {}

    username = str(
        data.get("username", "")
    ).strip().lower()

    if not username:
        emit("game_error", {
            "message": "نام کاربری نامعتبر است."
        })
        return

    if not player_exists(username):
        emit("game_error", {
            "message": "کاربر در اتاق تعریف نشده است."
        })
        return

    existing_sid = USER_SIDS.get(username)

    if existing_sid and existing_sid != request.sid:
        emit("game_error", {
            "message": "این کاربر قبلاً وارد شده است."
        })
        return

    if (
        username not in USER_SIDS
        and connected_count() >= MAX_PLAYERS
    ):
        emit("game_error", {
            "message": "ظرفیت اتاق تکمیل است."
        })
        return

    USER_SIDS[username] = request.sid
    USER_STATUS[username] = "online"

    join_room(ROOM_ID)

    player = PLAYERS[username]

    emit("game_joined", {
        "success": True,
        "room": ROOM_ID,
        "player": {
            "username": username,
            "name": player["name"],
            "title": player["title"],
            "admin": player["admin"],
        },
        "state": public_state(),
    })

    add_event(
        "player_online",
        f"{player['name']} وارد اتاق شد.",
        username
    )

    broadcast_state()


# =========================================================
# PLAYER STATUS
# =========================================================

@socketio.on("player_status")
def player_status(data):
    data = data or {}

    username = str(
        data.get("username", "")
    ).strip().lower()

    status = str(
        data.get("status", "online")
    ).strip().lower()

    allowed = {
        "online",
        "weak",
        "offline",
    }

    if username not in USER_SIDS:
        return

    if status not in allowed:
        status = "online"

    USER_STATUS[username] = status

    broadcast_state()


# =========================================================
# TEAM CHAT
# =========================================================

@socketio.on("team_chat")
def team_chat(data):
    data = data or {}

    username = str(
        data.get("username", "")
    ).strip().lower()

    message = str(
        data.get("message", "")
    ).strip()

    if username not in USER_SIDS:
        emit("game_error", {
            "message": "ابتدا وارد بازی شوید."
        })
        return

    if not message:
        return

    if len(message) > 1000:
        message = message[:1000]

    player = PLAYERS[username]

    item = {
        "id": str(uuid.uuid4()),
        "username": username,
        "name": player["name"],
        "title": player["title"],
        "message": message,
        "time": iran_time(),
    }

    CHAT_MESSAGES.append(item)

    if len(CHAT_MESSAGES) > 300:
        del CHAT_MESSAGES[:-300]

    socketio.emit(
        "team_chat",
        item,
        room=ROOM_ID
    )

    broadcast_state()


# =========================================================
# START CASE
# =========================================================

@socketio.on("case_start")
def case_start(data):
    data = data or {}

    username = str(
        data.get("username", "")
    ).strip().lower()

    if username != "mehdi":
        emit("game_error", {
            "message": "فقط مهدی (مدیر) می‌تواند پرونده را شروع کند."
        })
        return

    if connected_count() < MIN_PLAYERS:
        emit("game_error", {
            "message": f"برای شروع حداقل {MIN_PLAYERS} کارآگاه لازم است."
        })
        return

    if GAME_STATE["started"]:
        emit("game_error", {
            "message": "پرونده قبلاً شروع شده است."
        })
        return

    GAME_STATE["started"] = True
    GAME_STATE["phase"] = "scenario"

    add_event(
        "case_started",
        "پرونده مرموز شهر مهستان آغاز شد.",
        username
    )

    socketio.emit(
        "case_started",
        {
            "success": True,
            "phase": "scenario",
            "scenario": GAME_STATE["scenario"],
        },
        room=ROOM_ID
    )

    broadcast_state()


# =========================================================
# CONTINUE FROM SCENARIO
# =========================================================

@socketio.on("case_continue")
def case_continue(data):
    data = data or {}

    username = str(
        data.get("username", "")
    ).strip().lower()

    if username not in USER_SIDS:
        emit("game_error", {
            "message": "ابتدا وارد بازی شوید."
        })
        return

    if not GAME_STATE["started"]:
        emit("game_error", {
            "message": "پرونده هنوز شروع نشده است."
        })
        return

    if GAME_STATE["phase"] != "scenario":
        emit("game_error", {
            "message": "پرونده قبلاً وارد مرحله بعد شده است."
        })
        return

    GAME_STATE["phase"] = "city"

    add_event(
        "case_continue",
        "کارآگاهان وارد شهر مهستان شدند.",
        username
    )

    socketio.emit(
        "case_city",
        {
            "success": True,
            "phase": "city",
            "city": "مهستان",
        },
        room=ROOM_ID
    )

    broadcast_state()


# =========================================================
# RESET CASE
# =========================================================

@socketio.on("case_reset")
def case_reset(data):
    data = data or {}

    username = str(
        data.get("username", "")
    ).strip().lower()

    if username != "mehdi":
        emit("game_error", {
            "message": "فقط مدیر می‌تواند پرونده را ریست کند."
        })
        return

    GAME_STATE["started"] = False
    GAME_STATE["phase"] = "lobby"

    CHAT_MESSAGES.clear()
    GAME_EVENTS.clear()

    add_event(
        "case_reset",
        "پرونده برای شروع مجدد آماده شد.",
        username
    )

    broadcast_state()


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    print("=" * 60)
    print("MEHESTAN MYSTERY CASE")
    print("پرونده مرموز — شهر مهستان")
    print("=" * 60)
    print(f"Room: {ROOM_ID}")
    print(f"Players: {MAX_PLAYERS}")
    print("Server starting...")

    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        debug=False,
        use_reloader=False,
    )
