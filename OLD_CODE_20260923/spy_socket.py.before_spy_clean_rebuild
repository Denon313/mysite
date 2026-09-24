# -*- coding: utf-8 -*-

import threading
import time

from flask import request
from flask_socketio import join_room, leave_room

from spy_game import (
    create_game,
    get_game,
    add_player,
    start_game,
    vote,
    spy_guess,
    get_state,
    tick_game,
    finish_game,
)


SPY_ROOM_PREFIX = "spy_"
_timers = {}
_timers_lock = threading.RLock()


def room_name(game_id):
    return f"{SPY_ROOM_PREFIX}{game_id}"


def register_spy_socket(
    socketio,
    save_chat_callback=None,
    get_chat_history_callback=None,
):

    def send_state(game_id, username, sid):
        state = get_state(game_id, username)

        if state:
            socketio.emit(
                "spy_state",
                state,
                to=sid,
            )

    def broadcast_states(game_id):
        game = get_game(game_id)

        if not game:
            return

        # State عمومی
        state = get_state(game_id)

        if state:
            socketio.emit(
                "spy_state",
                state,
                room=room_name(game_id),
            )

    def finish_and_broadcast(game_id):
        game = get_game(game_id)

        if not game:
            return

        result = finish_game(game_id)

        socketio.emit(
            "spy_finished",
            {
                "result": result or {}
            },
            room=room_name(game_id),
        )

        socketio.emit(
            "spy_state",
            get_state(game_id),
            room=room_name(game_id),
        )

    def timer_worker(game_id):
        try:
            last_phase = None

            while True:
                game = get_game(game_id)

                if not game:
                    break

                phase = tick_game(game_id)

                state = get_state(game_id)

                if not state:
                    break

                current_phase = state.get("phase")
                remaining = state.get(
                    "remaining_seconds",
                    0,
                )

                socketio.emit(
                    "spy_tick",
                    {
                        "phase": current_phase,
                        "remaining_seconds": remaining,
                    },
                    room=room_name(game_id),
                )

                if (
                    last_phase == "discussion"
                    and current_phase == "voting"
                ):
                    socketio.emit(
                        "spy_voting_started",
                        {
                            "seconds": 10
                        },
                        room=room_name(game_id),
                    )

                if current_phase == "finished":
                    socketio.emit(
                        "spy_finished",
                        {
                            "result": state.get(
                                "result",
                                {}
                            )
                        },
                        room=room_name(game_id),
                    )
                    break

                last_phase = current_phase

                time.sleep(0.25)

        finally:
            with _timers_lock:
                _timers.pop(game_id, None)

    def start_timer(game_id):
        with _timers_lock:
            if game_id in _timers:
                return

            thread = threading.Thread(
                target=timer_worker,
                args=(game_id,),
                daemon=True,
            )

            _timers[game_id] = thread
            thread.start()

    @socketio.on("spy_create")
    def spy_create(data):
        data = data or {}

        username = str(
            data.get("username", "")
        ).strip()

        game_id = str(
            data.get("game_id", "")
        ).strip() or "spy-main-room"

        if not username:
            socketio.emit(
                "spy_error",
                {"message": "نام کاربری نامعتبر است."},
                to=request.sid,
            )
            return

        create_game(
            game_id,
            username,
        )

        ok, message = add_player(
            game_id,
            username,
        )

        if not ok:
            socketio.emit(
                "spy_error",
                {"message": message},
                to=request.sid,
            )
            return

        join_room(room_name(game_id))

        socketio.emit(
            "spy_created",
            {"game_id": game_id},
            to=request.sid,
        )

        send_state(
            game_id,
            username,
            request.sid,
        )

    @socketio.on("spy_join")
    def spy_join(data):
        data = data or {}

        username = str(
            data.get("username", "")
        ).strip()

        game_id = str(
            data.get("game_id", "")
        ).strip()

        game = get_game(game_id)

        if not game:
            socketio.emit(
                "spy_error",
                {"message": "بازی پیدا نشد."},
                to=request.sid,
            )
            return

        ok, message = add_player(
            game_id,
            username,
        )

        if not ok:
            socketio.emit(
                "spy_error",
                {"message": message},
                to=request.sid,
            )
            return

        join_room(room_name(game_id))

        socketio.emit(
            "spy_joined",
            {"game_id": game_id},
            to=request.sid,
        )

        send_state(
            game_id,
            username,
            request.sid,
        )

        start_timer(game_id)

    @socketio.on("spy_start")
    def spy_start(data):
        data = data or {}

        username = str(
            data.get("username", "")
        ).strip()

        game_id = str(
            data.get("game_id", "")
        ).strip()

        seconds = data.get(
            "discussion_seconds",
            120,
        )

        game = get_game(game_id)

        if not game:
            socketio.emit(
                "spy_error",
                {"message": "بازی پیدا نشد."},
                to=request.sid,
            )
            return

        if username != game.host:
            socketio.emit(
                "spy_error",
                {
                    "message":
                        "فقط سازنده بازی می‌تواند شروع کند."
                },
                to=request.sid,
            )
            return

        ok, message = start_game(
            game_id,
            seconds,
        )

        if not ok:
            socketio.emit(
                "spy_error",
                {"message": message},
                to=request.sid,
            )
            return

        socketio.emit(
            "spy_started",
            {},
            room=room_name(game_id),
        )

        broadcast_states(game_id)
        start_timer(game_id)

    @socketio.on("spy_vote")
    def spy_vote(data):
        data = data or {}

        game_id = str(
            data.get("game_id", "")
        ).strip()

        username = str(
            data.get("username", "")
        ).strip()

        target = str(
            data.get("target", "")
        ).strip()

        ok, message = vote(
            game_id,
            username,
            target,
        )

        if not ok:
            socketio.emit(
                "spy_error",
                {"message": message},
                to=request.sid,
            )
            return

        socketio.emit(
            "spy_vote_saved",
            {"voted": True},
            to=request.sid,
        )

        socketio.emit(
            "spy_vote_state",
            {
                "username": username,
                "voted": True,
            },
            room=room_name(game_id),
        )

        send_state(
            game_id,
            username,
            request.sid,
        )

    @socketio.on("spy_guess")
    def spy_guess_handler(data):
        data = data or {}

        game_id = str(
            data.get("game_id", "")
        ).strip()

        username = str(
            data.get("username", "")
        ).strip()

        guess = str(
            data.get("guess", "")
        ).strip()

        ok, result = spy_guess(
            game_id,
            username,
            guess,
        )

        if not ok:
            socketio.emit(
                "spy_error",
                {"message": result},
                to=request.sid,
            )
            return

        socketio.emit(
            "spy_guess_submitted",
            {"username": username},
            to=request.sid,
        )

        socketio.emit(
            "spy_finished",
            {
                "result": result
            },
            room=room_name(game_id),
        )

        start_timer(game_id)

    @socketio.on("spy_state")
    def spy_state(data):
        data = data or {}

        game_id = str(
            data.get("game_id", "")
        ).strip()

        username = str(
            data.get("username", "")
        ).strip()

        game = get_game(game_id)

        if not game:
            socketio.emit(
                "spy_error",
                {"message": "بازی پیدا نشد."},
                to=request.sid,
            )
            return

        join_room(room_name(game_id))

        send_state(
            game_id,
            username,
            request.sid,
        )

        start_timer(game_id)

    @socketio.on("spy_join_chat")
    def spy_join_chat(data):
        data = data or {}

        game_id = str(
            data.get("game_id", "")
        ).strip()

        username = str(
            data.get("username", "")
        ).strip()

        game = get_game(game_id)

        if not game or username not in game.players:
            return

        join_room(room_name(game_id))

        if get_chat_history_callback:
            try:
                history = get_chat_history_callback(
                    game_id
                ) or []

                socketio.emit(
                    "spy_chat_history",
                    {
                        "messages": history
                    },
                    to=request.sid,
                )

            except Exception:
                socketio.emit(
                    "spy_chat_history",
                    {"messages": []},
                    to=request.sid,
                )

    @socketio.on("spy_chat_history")
    def spy_chat_history(data):
        data = data or {}

        game_id = str(
            data.get("game_id", "")
        ).strip()

        if not get_chat_history_callback:
            return

        try:
            history = get_chat_history_callback(
                game_id
            ) or []

            socketio.emit(
                "spy_chat_history",
                {
                    "messages": history
                },
                to=request.sid,
            )

        except Exception:
            socketio.emit(
                "spy_chat_history",
                {"messages": []},
                to=request.sid,
            )

    @socketio.on("spy_chat")
    def spy_chat(data):
        data = data or {}

        game_id = str(
            data.get("game_id", "")
        ).strip()

        username = str(
            data.get("username", "")
        ).strip()

        message = str(
            data.get("message", "")
        ).strip()

        reply_to = data.get(
            "reply_to"
        )

        game = get_game(game_id)

        if not game:
            return

        if username not in game.players:
            return

        if game.phase == "finished":
            socketio.emit(
                "spy_error",
                {
                    "message":
                        "بازی تمام شده و چت بسته است."
                },
                to=request.sid,
            )
            return

        if not message:
            return

        if len(message) > 2000:
            socketio.emit(
                "spy_error",
                {
                    "message":
                        "پیام بیش از حد طولانی است."
                },
                to=request.sid,
            )
            return

        payload = {
            "username": username,
            "message": message,
            "reply_to": reply_to,
            "timestamp": time.time(),
        }

        if save_chat_callback:
            try:
                saved = save_chat_callback(
                    username=username,
                    message=message,
                    game_id=game_id,
                    reply_to=reply_to,
                )

                if isinstance(saved, dict):
                    payload.update(saved)

            except Exception:
                pass

        socketio.emit(
            "spy_chat_message",
            payload,
            room=room_name(game_id),
        )

    @socketio.on("spy_leave")
    def spy_leave(data):
        data = data or {}

        game_id = str(
            data.get("game_id", "")
        ).strip()

        if game_id:
            leave_room(
                room_name(game_id)
            )

    @socketio.on("spy_disconnect_player")
    def spy_disconnect_player(data):
        data = data or {}

        game_id = str(
            data.get("game_id", "")
        ).strip()

        username = str(
            data.get("username", "")
        ).strip()

        game = get_game(game_id)

        if game and username:
            game.disconnect_player(
                username
            )

            broadcast_states(game_id)
