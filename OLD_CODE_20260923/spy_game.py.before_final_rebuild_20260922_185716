from __future__ import annotations

from flask_socketio import join_room

import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional


# =========================================================
# SPY GAME ENGINE — FULL REWRITE
# Server-authoritative game state / timer / voting
# =========================================================

MIN_PLAYERS = 1
MAX_PLAYERS = 5

MIN_DISCUSSION_SECONDS = 10
MAX_DISCUSSION_SECONDS = 1800

VOTING_SECONDS = 10


@dataclass
class SpyPlayer:
    username: str
    display_name: str
    sid: Optional[str] = None

    role: Optional[str] = None
    word: Optional[str] = None

    vote: Optional[str] = None
    connected: bool = True


@dataclass
class SpyRoom:
    room_id: str

    players: Dict[str, SpyPlayer] = field(default_factory=dict)

    phase: str = "lobby"

    duration_seconds: Optional[int] = None

    phase_started_at: Optional[float] = None
    phase_ends_at: Optional[float] = None

    spy_username: Optional[str] = None
    word: Optional[str] = None

    winner: Optional[str] = None

    spy_guess: Optional[str] = None
    spy_guess_correct: Optional[bool] = None

    votes: Dict[str, str] = field(default_factory=dict)

    timer_generation: int = 0

    game_id: Optional[str] = None

    lock: threading.RLock = field(
        default_factory=threading.RLock,
        repr=False,
    )


class SpyEngine:

    def __init__(
        self,
        emit_callback: Optional[Callable[..., Any]] = None,
        save_chat_callback: Optional[Callable[..., Any]] = None,
        get_chat_history_callback: Optional[Callable[..., Any]] = None,
        get_socket_username_callback: Optional[Callable[..., Any]] = None,
        get_spy_words_callback: Optional[Callable[..., Any]] = None,
    ):
        self.emit_callback = emit_callback
        self.save_chat_callback = save_chat_callback
        self.get_chat_history_callback = get_chat_history_callback
        self.get_socket_username_callback = get_socket_username_callback
        self.get_spy_words_callback = get_spy_words_callback

        self.rooms: Dict[str, SpyRoom] = {}

        self.user_rooms: Dict[str, str] = {}

        self.lock = threading.RLock()

    # =====================================================
    # BASIC HELPERS
    # =====================================================

    @staticmethod
    def now() -> float:
        return time.time()

    @staticmethod
    def is_admin(username: Optional[str]) -> bool:
        return username == "mehdi"

    def get_or_create_room(self) -> SpyRoom:
        with self.lock:

            if "SPY" not in self.rooms:
                self.rooms["SPY"] = SpyRoom(
                    room_id="SPY"
                )

            return self.rooms["SPY"]

    def get_room(self) -> SpyRoom:
        return self.get_or_create_room()

    @staticmethod
    def player_public_data(player: SpyPlayer) -> dict:
        return {
            "username": player.username,
            "display_name": player.display_name,
            "connected": player.connected,
        }

    # =====================================================
    # EMIT
    # =====================================================

    def emit(
        self,
        event: str,
        data: Optional[dict] = None,
        room: Optional[str] = None,
        sid: Optional[str] = None,
    ):
        if not self.emit_callback:
            return

        payload = data or {}

        try:
            self.emit_callback(
                event,
                payload,
                room=room,
                sid=sid,
            )
            return
        except TypeError:
            pass

        try:
            self.emit_callback(
                event,
                payload,
                room,
            )
            return
        except TypeError:
            pass

        try:
            self.emit_callback(
                event,
                payload,
            )
        except Exception:
            pass

    def emit_room(
        self,
        event: str,
        data: Optional[dict] = None,
    ):
        self.emit(
            event,
            data or {},
            room="SPY",
        )

    def emit_user(
        self,
        sid: Optional[str],
        event: str,
        data: Optional[dict] = None,
    ):
        if not sid:
            return

        self.emit(
            event,
            data or {},
            sid=sid,
        )

    # =====================================================
    # STATE
    # =====================================================

    def remaining_seconds(
        self,
        room: SpyRoom,
    ) -> int:

        if (
            room.phase_started_at is None
            or room.phase_ends_at is None
        ):
            return 0

        remaining = room.phase_ends_at - self.now()

        if remaining <= 0:
            return 0

        return int(remaining + 0.999999)

    def public_state(
        self,
        room: SpyRoom,
    ) -> dict:

        players = [
            self.player_public_data(player)
            for player in room.players.values()
        ]

        return {
            "room_id": room.room_id,
            "phase": room.phase,
            "players": players,
            "player_count": len(players),
            "min_players": MIN_PLAYERS,
            "max_players": MAX_PLAYERS,
            "duration_seconds": room.duration_seconds,
            "remaining_seconds": self.remaining_seconds(room),
            "game_id": room.game_id,
            "winner": room.winner,
        }

    # =====================================================
    # LOBBY
    # =====================================================

    def join_lobby(
        self,
        username: str,
        display_name: str,
        sid: Optional[str] = None,
    ) -> dict:

        room = self.get_room()

        with room.lock:

            # Already here
            if username in room.players:

                player = room.players[username]

                player.sid = sid
                player.connected = True

                self.user_rooms[username] = room.room_id

                self.emit_room(
                    "spy_joined",
                    self.public_state(room),
                )

                return {
                    "success": True,
                    "state": self.public_state(room),
                }

            # Never allow joining a running game
            if room.phase not in (
                "lobby",
                "duration",
            ):

                return {
                    "success": False,
                    "error": "بازی در حال اجراست."
                }

            if len(room.players) >= MAX_PLAYERS:

                return {
                    "success": False,
                    "error": "ظرفیت بازی تکمیل است."
                }

            room.players[username] = SpyPlayer(
                username=username,
                display_name=display_name,
                sid=sid,
                connected=True,
            )

            self.user_rooms[username] = room.room_id

            self.emit_room(
                "spy_joined",
                self.public_state(room),
            )

            return {
                "success": True,
                "state": self.public_state(room),
            }

    # =====================================================
    # LEAVE LOBBY
    # =====================================================

    def leave_lobby(
        self,
        username: str,
    ) -> dict:

        room = self.get_room()

        with room.lock:

            if username not in room.players:

                return {
                    "success": True,
                    "state": self.public_state(room),
                }

            if room.phase not in (
                "lobby",
                "duration",
            ):

                return {
                    "success": False,
                    "error": "در زمان اجرای بازی امکان خروج از این بخش وجود ندارد."
                }

            del room.players[username]

            self.user_rooms.pop(
                username,
                None,
            )

            self.emit_room(
                "spy_left",
                self.public_state(room),
            )

            return {
                "success": True,
                "state": self.public_state(room),
            }

    # =====================================================
    # DURATION
    # =====================================================

    def prepare_start(
        self,
        username: str,
    ) -> dict:

        if not self.is_admin(username):

            return {
                "success": False,
                "error": "فقط مهدی می‌تواند بازی را شروع کند."
            }

        room = self.get_room()

        with room.lock:

            if room.phase != "lobby":

                return {
                    "success": False,
                    "error": "بازی در حال آماده‌سازی یا اجراست."
                }

            if len(room.players) < MIN_PLAYERS:

                return {
                    "success": False,
                    "error": "تعداد بازیکنان کافی نیست."
                }

            room.phase = "duration"

            room.timer_generation += 1

            self.emit_room(
                "spy_prepared",
                self.public_state(room),
            )

            return {
                "success": True,
                "state": self.public_state(room),
            }

    # =====================================================
    # WORD
    # =====================================================

    def get_words(self) -> list:

        if not self.get_spy_words_callback:
            return []

        try:
            words = self.get_spy_words_callback()
        except Exception:
            return []

        if not words:
            return []

        # Supports:
        # ["شیر", "ماشین"]
        if isinstance(words, list):

            normalized = []

            for item in words:

                if isinstance(item, str):
                    normalized.append({
                        "word": item,
                        "aliases": [],
                    })

                elif isinstance(item, dict):

                    word = item.get("word")

                    if word:
                        normalized.append({
                            "word": str(word),
                            "aliases": item.get(
                                "aliases",
                                [],
                            ),
                        })

            return normalized

        return []

    def choose_word(self) -> Optional[str]:

        words = self.get_words()

        if not words:
            return None

        item = random.choice(words)

        if isinstance(item, dict):
            return item.get("word")

        return str(item)

    # =====================================================
    # START GAME
    # =====================================================

    def start_game(
        self,
        username: str,
        duration_seconds: Any,
    ) -> dict:

        if not self.is_admin(username):

            return {
                "success": False,
                "error": "فقط مهدی می‌تواند بازی را شروع کند."
            }

        try:
            duration = int(
                str(duration_seconds).strip()
            )
        except Exception:

            return {
                "success": False,
                "error": "زمان واردشده معتبر نیست."
            }

        if duration < MIN_DISCUSSION_SECONDS:

            return {
                "success": False,
                "error": f"حداقل زمان {MIN_DISCUSSION_SECONDS} ثانیه است."
            }

        if duration > MAX_DISCUSSION_SECONDS:

            return {
                "success": False,
                "error": f"حداکثر زمان {MAX_DISCUSSION_SECONDS} ثانیه است."
            }

        room = self.get_room()

        with room.lock:

            if room.phase not in (
                "lobby",
                "duration",
            ):

                return {
                    "success": False,
                    "error": "بازی از قبل شروع شده است."
                }

            if len(room.players) < MIN_PLAYERS:

                return {
                    "success": False,
                    "error": "بازیکن کافی وجود ندارد."
                }

            word = self.choose_word()

            if not word:

                return {
                    "success": False,
                    "error": "کلمه‌ای برای بازی پیدا نشد."
                }

            usernames = list(
                room.players.keys()
            )

            spy_username = random.choice(
                usernames
            )

            room.duration_seconds = duration
            room.spy_username = spy_username
            room.word = word

            room.game_id = (
                "spy_"
                + uuid.uuid4().hex
            )

            room.winner = None
            room.spy_guess = None
            room.spy_guess_correct = None

            room.votes.clear()

            for player in room.players.values():

                player.role = (
                    "spy"
                    if player.username == spy_username
                    else "citizen"
                )

                player.word = (
                    None
                    if player.username == spy_username
                    else word
                )

                player.vote = None

            # =================================================
            # IMPORTANT:
            # THE TIMER STARTS HERE.
            # EXACTLY duration_seconds FROM THIS MOMENT.
            # =================================================

            room.phase = "chat"

            room.phase_started_at = self.now()

            room.phase_ends_at = (
                room.phase_started_at
                + duration
            )

            room.timer_generation += 1

            generation = room.timer_generation

            state = self.public_state(room)

            self.emit_room(
                "spy_started",
                state,
            )

            # Send private role information
            for player in room.players.values():

                role_payload = {
                    "game_id": room.game_id,
                    "phase": "chat",
                    "role": player.role,
                    "word": player.word,
                    "remaining_seconds": self.remaining_seconds(room),
                    "duration_seconds": duration,
                }

                self.emit_user(
                    player.sid,
                    "spy_state",
                    role_payload,
                )

                # Also send start privately so clients
                # that depend on it transition correctly.
                self.emit_user(
                    player.sid,
                    "spy_started",
                    state,
                )

            # Start server timer
            timer = threading.Thread(
                target=self._run_timer,
                args=(
                    room.room_id,
                    generation,
                    "chat",
                ),
                daemon=True,
            )

            timer.start()

            return {
                "success": True,
                "state": state,
            }

    # =====================================================
    # SERVER TIMER
    # =====================================================

    def _run_timer(
        self,
        room_id: str,
        generation: int,
        expected_phase: str,
    ):

        last_second = None

        while True:

            room = self.rooms.get(room_id)

            if room is None:
                return

            with room.lock:

                if room.timer_generation != generation:
                    return

                if room.phase != expected_phase:
                    return

                remaining = self.remaining_seconds(
                    room
                )

                # Broadcast the authoritative value
                # from the server.
                if remaining != last_second:

                    last_second = remaining

                    self.emit_room(
                        "spy_tick",
                        {
                            "game_id": room.game_id,
                            "phase": room.phase,
                            "remaining_seconds": remaining,
                            "server_time": self.now(),
                        },
                    )

                if remaining <= 0:
                    break

            time.sleep(0.2)

        room = self.rooms.get(room_id)

        if room is None:
            return

        with room.lock:

            if room.timer_generation != generation:
                return

            if room.phase != expected_phase:
                return

            if expected_phase == "chat":

                self._start_voting_locked(
                    room
                )

            elif expected_phase == "voting":

                self._finish_voting_locked(
                    room
                )

    # =====================================================
    # VOTING
    # =====================================================

    def _start_voting_locked(
        self,
        room: SpyRoom,
    ):

        room.phase = "voting"

        room.phase_started_at = self.now()

        room.phase_ends_at = (
            room.phase_started_at
            + VOTING_SECONDS
        )

        room.timer_generation += 1

        generation = room.timer_generation

        room.votes.clear()

        for player in room.players.values():
            player.vote = None

        players = [
            self.player_public_data(player)
            for player in room.players.values()
        ]

        state = {
            "game_id": room.game_id,
            "phase": "voting",
            "players": players,
            "remaining_seconds": VOTING_SECONDS,
            "voting_seconds": VOTING_SECONDS,
        }

        self.emit_room(
            "spy_state",
            state,
        )

        timer = threading.Thread(
            target=self._run_timer,
            args=(
                room.room_id,
                generation,
                "voting",
            ),
            daemon=True,
        )

        timer.start()

    def save_vote(
        self,
        username: str,
        target_username: str,
    ) -> dict:

        room = self.get_room()

        with room.lock:

            if room.phase != "voting":

                return {
                    "success": False,
                    "error": "الان زمان رأی‌گیری نیست."
                }

            voter = room.players.get(
                username
            )

            target = room.players.get(
                target_username
            )

            if not voter:

                return {
                    "success": False,
                    "error": "بازیکن رأی‌دهنده پیدا نشد."
                }

            if not target:

                return {
                    "success": False,
                    "error": "این بازیکن در بازی نیست."
                }

            # Player can change vote.
            voter.vote = target_username

            room.votes[
                username
            ] = target_username

            # Never broadcast who voted for whom.
            self.emit_user(
                voter.sid,
                "spy_vote_saved",
                {
                    "success": True,
                    "target": target_username,
                    "remaining_seconds": self.remaining_seconds(room),
                },
            )

            return {
                "success": True,
                "target": target_username,
            }

    # =====================================================
    # FINISH VOTING
    # =====================================================

    def _finish_voting_locked(
        self,
        room: SpyRoom,
    ):

        counts: Dict[str, int] = {}

        for target in room.votes.values():

            if target not in room.players:
                continue

            counts[target] = (
                counts.get(target, 0)
                + 1
            )

        selected_username = None

        if counts:

            highest = max(
                counts.values()
            )

            leaders = [
                username
                for username, count in counts.items()
                if count == highest
            ]

            # Tie = spy survives
            if len(leaders) == 1:

                selected_username = leaders[0]

        if (
            selected_username
            and selected_username == room.spy_username
        ):

            room.winner = "citizens"

            room.phase = "result"

            self._emit_result_locked(
                room,
                spy_found=True,
                selected_username=selected_username,
            )

            return

        room.winner = "spy"

        room.phase = "result"

        self._emit_result_locked(
            room,
            spy_found=False,
            selected_username=selected_username,
        )

    # =====================================================
    # RESULT
    # =====================================================

    def _emit_result_locked(
        self,
        room: SpyRoom,
        spy_found: bool,
        selected_username: Optional[str],
    ):

        result = {
            "game_id": room.game_id,
            "phase": "result",

            "spy_username": room.spy_username,

            "spy_display_name": (
                room.players[
                    room.spy_username
                ].display_name
                if room.spy_username in room.players
                else room.spy_username
            ),

            "word": room.word,

            "spy_found": spy_found,

            "selected_username": selected_username,

            "winner": room.winner,

            "result_text": (
                "جاسوس پیدا شد"
                if spy_found
                else "جاسوس برنده شد"
            ),
        }

        self.emit_room(
            "spy_finished",
            result,
        )

    # =====================================================
    # SPY GUESS
    # =====================================================

    def spy_guess(
        self,
        username: str,
        guess: str,
    ) -> dict:

        room = self.get_room()

        with room.lock:

            if room.phase != "result":

                return {
                    "success": False,
                    "error": "زمان حدس جاسوس نیست."
                }

            if username != room.spy_username:

                return {
                    "success": False,
                    "error": "فقط جاسوس می‌تواند حدس بزند."
                }

            guess = str(
                guess or ""
            ).strip()

            if not guess:

                return {
                    "success": False,
                    "error": "حدس نمی‌تواند خالی باشد."
                }

            room.spy_guess = guess

            # Simple exact comparison.
            # Word itself is normalized only for whitespace.
            room.spy_guess_correct = (
                guess.strip().casefold()
                ==
                str(
                    room.word or ""
                ).strip().casefold()
            )

            if room.spy_guess_correct:

                room.winner = "spy"

            else:

                room.winner = "citizens"

            payload = {
                "game_id": room.game_id,
                "spy_username": room.spy_username,
                "word": room.word,
                "guess": room.spy_guess,
                "correct": room.spy_guess_correct,
                "winner": room.winner,
            }

            self.emit_room(
                "spy_guess_result",
                payload,
            )

            return {
                "success": True,
                **payload,
            }

    # =====================================================
    # REPLAY
    # =====================================================

    def replay(
        self,
        username: str,
    ) -> dict:

        if not self.is_admin(username):

            return {
                "success": False,
                "error": "فقط مهدی می‌تواند بازی را مجدد شروع کند."
            }

        room = self.get_room()

        with room.lock:

            room.timer_generation += 1

            room.phase = "duration"

            room.duration_seconds = None

            room.phase_started_at = None
            room.phase_ends_at = None

            room.spy_username = None
            room.word = None

            room.winner = None

            room.spy_guess = None
            room.spy_guess_correct = None

            room.votes.clear()

            room.game_id = None

            for player in room.players.values():

                player.role = None
                player.word = None
                player.vote = None

            state = self.public_state(
                room
            )

            self.emit_room(
                "spy_replay_ready",
                state,
            )

            return {
                "success": True,
                "state": state,
            }

    # =====================================================
    # CHAT
    # =====================================================

    def join_chat(
        self,
        username: str,
    ) -> dict:

        room = self.get_room()

        with room.lock:

            if room.phase != "chat":

                return {
                    "success": False,
                    "error": "چت بازی فعال نیست."
                }

            player = room.players.get(
                username
            )

            if not player:

                return {
                    "success": False,
                    "error": "بازیکن در این بازی نیست."
                }

            history = []

            if self.get_chat_history_callback:

                try:
                    history = (
                        self.get_chat_history_callback(
                            room.game_id
                        )
                    )
                except TypeError:

                    try:
                        history = (
                            self.get_chat_history_callback()
                        )
                    except Exception:
                        history = []

                except Exception:
                    history = []

            self.emit_user(
                player.sid,
                "spy_chat_history",
                {
                    "game_id": room.game_id,
                    "messages": history or [],
                },
            )

            return {
                "success": True,
                "game_id": room.game_id,
                "messages": history or [],
            }

    def chat(
        self,
        username: str,
        message: str,
        reply_to: Optional[Any] = None,
        is_image: bool = False,
    ) -> dict:

        room = self.get_room()

        with room.lock:

            if room.phase != "chat":

                return {
                    "success": False,
                    "error": "چت بازی فعال نیست."
                }

            player = room.players.get(
                username
            )

            if not player:

                return {
                    "success": False,
                    "error": "بازیکن در این بازی نیست."
                }

            message = str(
                message or ""
            ).strip()

            if not message and not is_image:

                return {
                    "success": False,
                    "error": "پیام خالی است."
                }

            if self.save_chat_callback:

                try:
                    saved = self.save_chat_callback(
                        username,
                        message,
                        is_image,
                        room.game_id,
                        reply_to,
                    )
                except TypeError:

                    try:
                        saved = self.save_chat_callback(
                            username,
                            message,
                            is_image,
                            room.game_id,
                        )
                    except TypeError:

                        saved = self.save_chat_callback(
                            username,
                            message,
                        )

                except Exception:

                    saved = None

            else:

                saved = None

            payload = {
                "game_id": room.game_id,
                "username": username,
                "display_name": player.display_name,
                "message": message,
                "is_image": is_image,
                "reply_to": reply_to,
            }

            if isinstance(saved, dict):
                payload.update(saved)

            # Exactly one room broadcast.
            # Every player receives the same message.
            self.emit_room(
                "spy_chat",
                payload,
            )

            return {
                "success": True,
                "message": payload,
            }

    # =====================================================
    # DISCONNECT
    # =====================================================

    def disconnect(
        self,
        username: str,
    ):

        room = self.get_room()

        with room.lock:

            player = room.players.get(
                username
            )

            if not player:
                return

            player.connected = False
            player.sid = None

            # Do NOT destroy the game.
            # Reconnection is allowed.

            self.emit_room(
                "spy_joined",
                self.public_state(room),
            )

    # =====================================================
    # SOCKET REGISTRATION
    # =====================================================

    def register_socket_handlers(
        self,
        socketio,
    ):

        @socketio.on("spy_join_lobby")
        def handle_spy_join_lobby(data=None):

            data = data or {}

            username = self._socket_username()
            join_room("SPY")

            if not username:
                return

            display_name = data.get(
                "display_name",
                username,
            )

            result = self.join_lobby(
                username=username,
                display_name=display_name,
                sid=self._socket_sid(),
            )

            if not result.get("success"):

                self.emit_user(
                    self._socket_sid(),
                    "spy_error",
                    {
                        "error": result.get(
                            "error",
                            "خطا"
                        )
                    },
                )

        @socketio.on("spy_join")
        def handle_spy_join(data=None):

            data = data or {}

            username = self._socket_username()
            join_room("SPY")

            if not username:
                return

            display_name = data.get(
                "display_name",
                username,
            )

            result = self.join_lobby(
                username=username,
                display_name=display_name,
                sid=self._socket_sid(),
            )

            if not result.get("success"):

                self.emit_user(
                    self._socket_sid(),
                    "spy_error",
                    {
                        "error": result.get(
                            "error",
                            "خطا"
                        )
                    },
                )

        @socketio.on("spy_leave_lobby")
        def handle_spy_leave_lobby(data=None):

            username = self._socket_username()

            if not username:
                return

            result = self.leave_lobby(
                username
            )

            if not result.get("success"):

                self.emit_user(
                    self._socket_sid(),
                    "spy_error",
                    {
                        "error": result.get(
                            "error",
                            "خطا"
                        )
                    },
                )

        @socketio.on("spy_prepare_start")
        def handle_spy_prepare_start(data=None):

            username = self._socket_username()

            if not username:
                return

            result = self.prepare_start(
                username
            )

            if not result.get("success"):

                self.emit_user(
                    self._socket_sid(),
                    "spy_error",
                    {
                        "error": result.get(
                            "error",
                            "خطا"
                        )
                    },
                )

        @socketio.on("spy_start")
        def handle_spy_start(data=None):

            data = data or {}

            username = self._socket_username()

            if not username:
                return

            duration = (
                data.get("duration_seconds")
                if "duration_seconds" in data
                else data.get("duration")
            )

            result = self.start_game(
                username,
                duration,
            )

            if not result.get("success"):

                self.emit_user(
                    self._socket_sid(),
                    "spy_error",
                    {
                        "error": result.get(
                            "error",
                            "خطا در شروع بازی"
                        )
                    },
                )

        @socketio.on("spy_join_chat")
        def handle_spy_join_chat(data=None):

            username = self._socket_username()

            if not username:
                return

            result = self.join_chat(
                username
            )

            if not result.get("success"):

                self.emit_user(
                    self._socket_sid(),
                    "spy_error",
                    {
                        "error": result.get(
                            "error",
                            "خطا"
                        )
                    },
                )

        @socketio.on("spy_chat")
        def handle_spy_chat(data=None):

            data = data or {}

            username = self._socket_username()

            if not username:
                return

            message = data.get(
                "message",
                "",
            )

            reply_to = data.get(
                "reply_to"
            )

            result = self.chat(
                username=username,
                message=message,
                reply_to=reply_to,
                is_image=bool(
                    data.get(
                        "is_image",
                        False,
                    )
                ),
            )

            if not result.get("success"):

                self.emit_user(
                    self._socket_sid(),
                    "spy_error",
                    {
                        "error": result.get(
                            "error",
                            "خطا"
                        )
                    },
                )

        @socketio.on("spy_vote")
        def handle_spy_vote(data=None):

            data = data or {}

            username = self._socket_username()

            if not username:
                return

            target = (
                data.get("target_username")
                if "target_username" in data
                else data.get("target")
            )

            result = self.save_vote(
                username=username,
                target_username=target,
            )

            if not result.get("success"):

                self.emit_user(
                    self._socket_sid(),
                    "spy_error",
                    {
                        "error": result.get(
                            "error",
                            "خطا در رأی‌گیری"
                        )
                    },
                )

        @socketio.on("spy_guess")
        def handle_spy_guess(data=None):

            data = data or {}

            username = self._socket_username()

            if not username:
                return

            result = self.spy_guess(
                username=username,
                guess=data.get(
                    "guess",
                    "",
                ),
            )

            if not result.get("success"):

                self.emit_user(
                    self._socket_sid(),
                    "spy_error",
                    {
                        "error": result.get(
                            "error",
                            "خطا"
                        )
                    },
                )

        @socketio.on("spy_replay")
        def handle_spy_replay(data=None):

            username = self._socket_username()

            if not username:
                return

            result = self.replay(
                username
            )

            if not result.get("success"):

                self.emit_user(
                    self._socket_sid(),
                    "spy_error",
                    {
                        "error": result.get(
                            "error",
                            "خطا"
                        )
                    },
                )

    # =====================================================
    # SOCKET CONTEXT
    # =====================================================

    def _socket_sid(self):

        try:
            from flask import request

            return request.sid

        except Exception:
            return None

    def _socket_username(self):

        if self.get_socket_username_callback:

            try:
                return (
                    self.get_socket_username_callback()
                )
            except Exception:
                pass

        return None

    # =====================================================
    # DEBUG / COMPATIBILITY
    # =====================================================

    def lobby_state(self) -> dict:

        room = self.get_room()

        with room.lock:

            return self.public_state(
                room
            )


# =========================================================
# GLOBAL ENGINE
# =========================================================

spy_engine = SpyEngine()


# =========================================================
# COMPATIBILITY REGISTRATION
# =========================================================

def register_spy_socket(
    socketio,
    save_chat_callback=None,
    get_chat_history_callback=None,
    get_socket_username_callback=None,
    get_spy_words_callback=None,
):

    global spy_engine

    def socket_emit(
        event,
        payload=None,
        room=None,
        sid=None,
    ):
        payload = payload or {}

        try:
            if sid:
                socketio.emit(
                    event,
                    payload,
                    to=sid,
                )
            elif room:
                socketio.emit(
                    event,
                    payload,
                    to=room,
                )
            else:
                socketio.emit(
                    event,
                    payload,
                )
        except TypeError:
            if sid:
                socketio.emit(
                    event,
                    payload,
                    room=sid,
                )
            elif room:
                socketio.emit(
                    event,
                    payload,
                    room=room,
                )
            else:
                socketio.emit(
                    event,
                    payload,
                )

    spy_engine = SpyEngine(
        emit_callback=socket_emit,
        save_chat_callback=save_chat_callback,
        get_chat_history_callback=get_chat_history_callback,
        get_socket_username_callback=get_socket_username_callback,
        get_spy_words_callback=get_spy_words_callback,
    )

    spy_engine.register_socket_handlers(
        socketio
    )

    return spy_engine


def disconnect_spy_user(
    username: str,
):

    try:
        spy_engine.disconnect(
            username
        )
    except Exception:
        pass
