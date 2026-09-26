/* =========================================================
   GAME ROOM - FRONTEND APPLICATION
   ========================================================= */

(() => {
    

console.log("GAME_ROOM_APP_JS_LOADED");


    "use strict";

    function escapeHtml(value) {
        return String(value ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    /* =====================================================
       CONFIG
    ===================================================== */

    const CONFIG = {
        API_BASE:
            window.location.hostname === "localhost" ||
            window.location.hostname === "127.0.0.1"
                ? "http://127.0.0.1:5000"
                : "https://movie-night-backend-production.up.railway.app",

        SOCKET_PATH: "/socket.io",

        MAX_MESSAGE_LENGTH: 500,
        MAX_DISPLAY_NAME_LENGTH: 30,

        PLAYERS: {
            mehdi: {
                username: "mehdi",
                name: "مهدی",
                role: "admin",
                emoji: "👑"
            },

            rastin: {
                username: "rastin",
                name: "راستین",
                role: "player",
                emoji: "🎮"
            },

            amirali: {
                username: "amirali",
                name: "امیرعلی",
                role: "player",
                emoji: "🎮"
            },

            mahna: {
                username: "mahna",
                name: "مهنا",
                role: "player",
                emoji: "🎮"
            },

            fatemeh: {
                username: "fatemeh",
                name: "فاطمه",
                role: "player",
                emoji: "🎮"
            }
        },

        GAMES: {
            spy: {
                title: "جاسوس",
                emoji: "🕵️"
            },

            mystery: {
                title: "اتاق پرونده مرموز",
                emoji: "🔎"
            },

            forbidden: {
                title: "کلمه ممنوعه",
                emoji: "🚫"
            },

            nature3d: {
                title: "جنگل آرام",
                emoji: "🌲"
            },

            mehestan: {
                title: "مهستان",
                emoji: "🕵️‍♂️"
            }
        }
    };


    /* =====================================================
       STATE
    ===================================================== */

    const state = {
        currentUser: null,
        profile: null,

        socket: null,
        connected: false,

        players: {},
        activities: [],

        unreadMessages: 0,
        chatOpen: false,

        currentGame: null,

        pendingAdminLogin: false,

        initialized: false
    };


    /* =====================================================
       DOM HELPERS
    ===================================================== */

    const $ = (selector) => document.querySelector(selector);

    const $$ = (selector) => {
        return Array.from(document.querySelectorAll(selector));
    };


    function show(element) {
        if (element) {
            element.classList.remove("hidden");
        }
    }


    function hide(element) {
        if (element) {
            element.classList.add("hidden");
        }
    }


    function setText(element, value) {
        if (element) {
            element.textContent = value ?? "";
        }
    }


    /* =====================================================
       STORAGE
    ===================================================== */

    function saveCurrentUser() {
        if (!state.currentUser) {
            localStorage.removeItem("game_room_user");
            return;
        }

        localStorage.setItem(
            "game_room_user",
            state.currentUser.username
        );
    }


    function getSavedUser() {
        const username =
            localStorage.getItem("game_room_user");

        if (!username) {
            return null;
        }

        return CONFIG.PLAYERS[username] || null;
    }


    /* =====================================================
       TOAST
    ===================================================== */

    function toast(message, duration = 2800) {
        const container = $("#toastContainer");

        if (!container) {
            return;
        }

        const item = document.createElement("div");

        item.className = "toast";
        item.textContent = message;

        container.appendChild(item);

        window.setTimeout(() => {
            item.style.opacity = "0";
            item.style.transform = "translateY(8px)";

            window.setTimeout(() => {
                item.remove();
            }, 220);
        }, duration);
    }


    /* =====================================================
       LOGIN
    ===================================================== */

    function setupLoginButtons() {
        document.addEventListener("click", (event) => {
            const button = event.target.closest(".player-login");

            if (!button) {
                return;
            }

            console.log("LOGIN BUTTON CLICKED:", button.dataset.username);

            const username = button.dataset.username;

            if (!username) {
                return;
            }

            const player = CONFIG.PLAYERS[username];

            if (!player) {
                return;
            }

            if (player.role === "admin") {
                openAdminPassword(username);
                return;
            }

            loginAs(username, "");
        });
    }

    function openAdminPassword(username) {
        state.pendingAdminLogin = username;

        const modal = $("#passwordModal");
        const input = $("#passwordInput");
        const error = $("#passwordError");

        if (!modal || !input) {
            return;
        }

        input.value = "";
        hide(error);
        show(modal);

        window.setTimeout(() => {
            input.focus();
        }, 100);
    }


    function closeAdminPassword() {
        state.pendingAdminLogin = false;

        hide($("#passwordModal"));

        const input = $("#passwordInput");

        if (input) {
            input.value = "";
        }

        hide($("#passwordError"));
    }


    async function loginAs(username, password) {

        const player = CONFIG.PLAYERS[username];

        if (!player) {
            toast("بازیکن پیدا نشد.");
            return;
        }

        try {

            if (player.role === "admin") {

                if (!password) {
                    toast("رمز مدیریت وارد نشده.");
                    return;
                }

                await verifyAdminPassword(username, password);
            }

            state.currentUser = {
                ...player
            };

            saveCurrentUser();

            await loadProfile();

            showMainScreen();

            connectSocket();

        } catch (error) {

            console.error(error);

            if (player.role === "admin") {
                show($("#passwordError"));
                setText(
                    $("#passwordError"),
                    "رمز مدیریت اشتباه است."
                );
            } else {
                toast(
                    error.message ||
                    "ورود انجام نشد."
                );
            }
        }
    }


    async function verifyAdminPassword(username, password) {

        const response = await fetch(
            `${CONFIG.API_BASE}/api/game/login`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    username,
                    password
                })
            }
        );

        /*
         * بعضی نسخه‌های Backend ممکن است هنوز
         * endpoint login را نداشته باشند.
         *
         * در نسخه نهایی Backend همین endpoint
         * اضافه خواهد شد.
         */

        if (!response.ok) {

            let data = {};

            try {
                data = await response.json();
            } catch (_) {}

            throw new Error(
                data.error ||
                "رمز مدیریت اشتباه است."
            );
        }

        return response.json();
    }


    function showMainScreen() {

        hide($("#loginScreen"));
        show($("#mainScreen"));

        updateHeaderProfile();
        renderMembers();
        updateAdminButton();
    }


    function logout() {

        if (state.socket) {
            try {
                state.socket.disconnect();
            } catch (_) {}
        }

        state.socket = null;
        state.connected = false;
        state.currentUser = null;
        state.profile = null;

        localStorage.removeItem(
            "game_room_user"
        );

        hide($("#mainScreen"));
        hide($("#chatPanel"));
        hide($("#profileModal"));
        hide($("#adminModal"));
        hide($("#gameModal"));

        show($("#loginScreen"));
    }


    /* =====================================================
       PROFILE
    ===================================================== */

    async function loadProfile() {

        if (!state.currentUser) {
            return;
        }

        try {

            const response = await fetch(
                `${CONFIG.API_BASE}/api/game/profile/${encodeURIComponent(
                    state.currentUser.username
                )}`
            );

            if (!response.ok) {
                throw new Error(
                    "profile request failed"
                );
            }

            const data =
                await response.json();

            state.profile = {
                username:
                    data.username ||
                    state.currentUser.username,

                display_name:
                    data.display_name ||
                    state.currentUser.name,

                avatar_url:
                    data.avatar_url ||
                    null
            };

        } catch (error) {

            console.warn(
                "Profile could not be loaded:",
                error
            );

            state.profile = {
                username:
                    state.currentUser.username,

                display_name:
                    state.currentUser.name,

                avatar_url: null
            };
        }

        updateHeaderProfile();
    }


    function updateHeaderProfile() {

        if (!state.currentUser) {
            return;
        }

        const displayName =
            state.profile?.display_name ||
            state.currentUser.name;

        setText(
            $("#headerName"),
            displayName
        );

        const avatar =
            state.profile?.avatar_url;

        const headerAvatar =
            $("#headerAvatar");

        if (!headerAvatar) {
            return;
        }

        headerAvatar.innerHTML = "";

        if (avatar) {

            const image =
                document.createElement("img");

            image.src =
                absoluteUrl(avatar);

            image.alt =
                "تصویر پروفایل";

            headerAvatar.appendChild(image);

        } else {

            headerAvatar.textContent =
                state.currentUser.emoji;
        }
    }


    function openProfile() {

        if (!state.currentUser) {
            return;
        }

        const modal =
            $("#profileModal");

        const nameInput =
            $("#displayNameInput");

        const username =
            $("#profileUsername");

        const avatarImage =
            $("#profileAvatarImage");

        const avatarFallback =
            $("#profileAvatarFallback");

        setText(
            username,
            state.currentUser.username
        );

        if (nameInput) {
            nameInput.value =
                state.profile?.display_name ||
                state.currentUser.name;
        }

        const avatar =
            state.profile?.avatar_url;

        if (avatar) {

            avatarImage.src =
                absoluteUrl(avatar);

            show(avatarImage);
            hide(avatarFallback);

        } else {

            hide(avatarImage);
            show(avatarFallback);

            setText(
                avatarFallback,
                state.currentUser.emoji
            );
        }

        show(modal);
    }


    async function saveProfile() {

        if (!state.currentUser) {
            return;
        }

        const input =
            $("#displayNameInput");

        if (!input) {
            return;
        }

        let displayName =
            input.value.trim();

        if (!displayName) {
            toast("نام نمایشی نمی‌تواند خالی باشد.");
            return;
        }

        if (
            displayName.length >
            CONFIG.MAX_DISPLAY_NAME_LENGTH
        ) {

            toast(
                `نام نمایشی باید حداکثر ${CONFIG.MAX_DISPLAY_NAME_LENGTH} کاراکتر باشد.`
            );

            return;
        }

        try {

            const response = await fetch(
                `${CONFIG.API_BASE}/api/game/profile/${encodeURIComponent(
                    state.currentUser.username
                )}`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        display_name:
                            displayName
                    })
                }
            );

            const data =
                await response.json();

            if (!response.ok) {
                throw new Error(
                    data.error ||
                    "ذخیره پروفایل انجام نشد."
                );
            }

            state.profile = {
                ...(state.profile || {}),
                username:
                    state.currentUser.username,
                display_name:
                    data.display_name ||
                    displayName,
                avatar_url:
                    data.avatar_url ||
                    state.profile?.avatar_url ||
                    null
            };

            updateHeaderProfile();
            renderMembers();

            if (state.socket?.connected) {

                state.socket.emit(
                    "game_profile_update",
                    {
                        username:
                            state.currentUser.username,

                        display_name:
                            state.profile.display_name,

                        avatar_url:
                            state.profile.avatar_url
                    }
                );
            }

            hide($("#profileModal"));

            toast("پروفایل ذخیره شد ✅");

        } catch (error) {

            console.error(error);

            toast(
                error.message ||
                "خطا در ذخیره پروفایل."
            );
        }
    }


    async function uploadProfileAvatar(file) {

        if (!state.currentUser || !file) {
            return;
        }

        if (!file.type.startsWith("image/")) {
            toast("فقط فایل تصویری انتخاب کن.");
            return;
        }

        if (file.size > 5 * 1024 * 1024) {
            toast("حجم تصویر نباید بیشتر از ۵ مگابایت باشد.");
            return;
        }

        const formData =
            new FormData();

        formData.append(
            "avatar",
            file
        );

        try {

            toast("در حال آپلود تصویر...");

            const response = await fetch(
                `${CONFIG.API_BASE}/api/game/profile/${encodeURIComponent(
                    state.currentUser.username
                )}/avatar`,
                {
                    method: "POST",
                    body: formData
                }
            );

            const data =
                await response.json();

            if (!response.ok) {
                throw new Error(
                    data.error ||
                    "آپلود تصویر انجام نشد."
                );
            }

            state.profile = {
                ...(state.profile || {}),
                avatar_url:
                    data.avatar_url ||
                    null
            };

            updateHeaderProfile();
            openProfile();
            renderMembers();

            if (state.socket?.connected) {

                state.socket.emit(
                    "game_profile_update",
                    {
                        username:
                            state.currentUser.username,

                        display_name:
                            state.profile.display_name,

                        avatar_url:
                            state.profile.avatar_url
                    }
                );
            }

            toast("تصویر پروفایل تغییر کرد ✅");

        } catch (error) {

            console.error(error);

            toast(
                error.message ||
                "آپلود تصویر ناموفق بود."
            );
        }
    }


    /* =====================================================
       PLAYERS
    ===================================================== */

    async function loadPlayers() {

        try {

            const response = await fetch(
                `${CONFIG.API_BASE}/api/game/players`
            );

            if (!response.ok) {
                throw new Error(
                    "players request failed"
                );
            }

            const data =
                await response.json();

            const list =
                Array.isArray(data)
                    ? data
                    : data.players || [];

            state.players = {};

            list.forEach((player) => {

                if (!player.username) {
                    return;
                }

                state.players[player.username] =
                    player;
            });

            renderMembers();

        } catch (error) {

            console.warn(
                "Players could not be loaded:",
                error
            );

            /*
             * حتی اگر Backend هنوز deploy نشده باشد،
             * پنج عضو ثابت را نمایش می‌دهیم.
             */

            Object.values(CONFIG.PLAYERS)
                .forEach((player) => {

                    if (!state.players[player.username]) {

                        state.players[player.username] = {
                            username:
                                player.username,

                            display_name:
                                player.name,

                            avatar_url: null,

                            status: "offline",

                            role: player.role
                        };
                    }
                });

            renderMembers();
        }
    }


    function renderMembers() {

        const grid =
            $("#membersGrid");

        if (!grid) {
            return;
        }

        grid.innerHTML = "";

        const players =
            Object.values(CONFIG.PLAYERS);

        let onlineCount = 0;

        players.forEach((basePlayer) => {

            const serverPlayer =
                state.players[
                    basePlayer.username
                ] || {};

            const isMe =
                state.currentUser &&
                state.currentUser.username ===
                    basePlayer.username;

            let displayName =
                serverPlayer.display_name ||
                (isMe
                    ? state.profile?.display_name
                    : null) ||
                basePlayer.name;

            let status =
                serverPlayer.status ||
                "offline";

            if (isMe && state.connected) {
                status = "online";
            }

            if (status === "online") {
                onlineCount++;
            }

            const card =
                document.createElement("div");

            card.className =
                "member-card";

            const avatar =
                document.createElement("div");

            avatar.className =
                "member-avatar";

            const imageUrl =
                serverPlayer.avatar_url ||
                (isMe
                    ? state.profile?.avatar_url
                    : null);

            if (imageUrl) {

                const image =
                    document.createElement("img");

                image.src =
                    absoluteUrl(imageUrl);

                image.alt =
                    displayName;

                avatar.appendChild(image);

            } else {

                avatar.textContent =
                    basePlayer.emoji;
            }

            const dot =
                document.createElement("span");

            dot.className =
                "status-dot " +
                getStatusClass(status);

            avatar.appendChild(dot);

            const name =
                document.createElement("div");

            name.className =
                "member-name";

            name.textContent =
                displayName;

            const statusText =
                document.createElement("div");

            statusText.className =
                "member-status";

            statusText.textContent =
                getStatusText(status);

            card.appendChild(avatar);
            card.appendChild(name);
            card.appendChild(statusText);

            grid.appendChild(card);
        });

        setText(
            $("#onlineCount"),
            onlineCount
        );

        setText(
            $("#adminOnlineCount"),
            onlineCount
        );
    }


    function getStatusClass(status) {

        switch (status) {

            case "online":
                return "status-online";

            case "weak":
                return "status-weak";

            default:
                return "status-offline";
        }
    }


    function getStatusText(status) {

        switch (status) {

            case "online":
                return "آنلاین";

            case "weak":
                return "اینترنت ضعیف";

            default:
                return "آفلاین";
        }
    }


    /* =====================================================
       SOCKET
    ===================================================== */

    function connectSocket() {

        if (!state.currentUser) {
            return;
        }

        if (typeof io !== "function") {

            toast(
                "کتابخانه اتصال زنده بارگذاری نشده."
            );

            return;
        }

        if (state.socket) {

            try {
                state.socket.disconnect();
            } catch (_) {}
        }

        state.socket = io(
            CONFIG.API_BASE,
            {
                path: CONFIG.SOCKET_PATH,
                transports: [
                    "websocket",
                    "polling"
                ],
                reconnection: true,
                reconnectionAttempts: Infinity,
                reconnectionDelay: 1200,
                timeout: 10000
            }
        );

        setupSocketEvents();
        setupSpySocketListeners();
    }


    function setupSocketEvents() {

        const socket =
            state.socket;

        if (!socket) {
            return;
        }

        socket.on(
            "connect",
            () => {

                state.connected = true;

                socket.emit(
                    "game_join",
                    {
                        username:
                            state.currentUser.username
                    }
                );

                if (
                    state.currentGame?.type === "spy-lobby" &&
                    state.currentUser?.username
                ) {
                    socket.emit(
                        "spy_lobby_join",
                        {
                            username:
                                state.currentUser.username
                        }
                    );
                }

                renderMembers();

                addActivity(
                    "🟢",
                    "اتصال برقرار شد",
                    "به اتاق Game Room متصل شدی."
                );
            }
        );


        socket.on(
            "disconnect",
            () => {

                state.connected = false;

                renderMembers();

                addActivity(
                    "🔴",
                    "اتصال قطع شد",
                    "در حال تلاش برای اتصال مجدد..."
                );
            }
        );


        socket.on(
            "connect_error",
            (error) => {

                console.warn(
                    "Socket connection error:",
                    error
                );

                state.connected = false;

                renderMembers();
            }
        );


        socket.on(
            "game_joined",
            (data) => {

                if (data?.player) {

                    mergePlayer(
                        data.player
                    );
                }

                if (Array.isArray(data?.players)) {

                    data.players.forEach(
                        mergePlayer
                    );
                }

                renderMembers();

                toast("به اتاق خوش اومدی 🎮");
            }
        );


        socket.on(
            "game_error",
            (data) => {

                toast(
                    data?.error ||
                    "ورود به اتاق انجام نشد."
                );
            }
        );


        socket.on(
            "game_players_update",
            (data) => {

                const players =
                    Array.isArray(data)
                        ? data
                        : data?.players || [];

                players.forEach(
                    mergePlayer
                );

                renderMembers();
            }
        );


        socket.on(
            "game_profile_update",
            (data) => {

                if (!data?.username) {
                    return;
                }

                mergePlayer(data);

                if (
                    state.currentUser &&
                    data.username ===
                        state.currentUser.username
                ) {

                    state.profile = {
                        ...(state.profile || {}),
                        display_name:
                            data.display_name ||
                            state.profile?.display_name ||
                            state.currentUser.name,

                        avatar_url:
                            data.avatar_url ||
                            state.profile?.avatar_url ||
                            null
                    };

                    updateHeaderProfile();
                }

                renderMembers();
            }
        );


        socket.on("game_chat_message", (data) => {
            addChatMessage(data);

            if (!state.chatOpen) {
                state.unreadMessages++;
                updateChatBadge();
            }
        });

        socket.on("game_chat_history", (data) => {
            const messages =
                Array.isArray(data)
                    ? data
                    : data?.messages || [];

            renderChatHistory(messages);
        });

        socket.on(
            "game_chat_error",
            (data) => {
                toast(
                    data?.error ||
                    "ارسال پیام انجام نشد."
                );
            }
        );

        

        


        


        


        


        socket.on("game_state", (data) => {
            if (!data) {
                return;
            }

            const players =
                Array.isArray(data.players)
                    ? data.players
                    : data.players?.players || [];

            players.forEach(mergePlayer);

            if (data.server_time) {
                state.serverTime = data.server_time;
            }

            renderMembers();
        });

        socket.on("game_state_update", (data) => {
            updateCurrentGame(data);
        });

        socket.on("game_started", (data) => {
            if (!data?.game_type) {
                return;
            }

            openGame(data.game_type, data);
        });

        socket.on("game_room_joined", (data) => {
            if (!data) {
                return;
            }

            const gameId = data.game_id || null;
            const gameType =
                data.game_type ||
                state.currentGame?.type ||
                null;

            if (!state.currentGame) {
                state.currentGame = {
                    type: gameType,
                    data,
                    gameId,
                    spyRole: null,
                    spyState: null,
                    spyResult: null
                };
            } else {
                state.currentGame.gameId =
                    gameId || state.currentGame.gameId;

                if (gameType) {
                    state.currentGame.type = gameType;
                }

                state.currentGame.data = data;
            }
        });
    }


    function mergePlayer(player) {

        if (!player?.username) {
            return;
        }

        state.players[player.username] = {
            ...(state.players[player.username] || {}),
            ...player
        };
    }


    /* =====================================================
       HEARTBEAT
    ===================================================== */

    let heartbeatTimer = null;

    function startHeartbeat() {

        if (heartbeatTimer) {
            clearInterval(
                heartbeatTimer
            );
        }

        heartbeatTimer =
            setInterval(() => {

                if (
                    state.socket?.connected &&
                    state.currentUser
                ) {

                    state.socket.emit(
                        "game_heartbeat",
                        {
                            username:
                                state.currentUser.username
                        }
                    );
                }

            }, 15000);
    }


    /* =====================================================
       CHAT
    ===================================================== */

    function openChat() {

        if (!state.currentUser) {
            toast("اول وارد Game Room شو.");
            return;
        }

        state.chatOpen = true;
        state.unreadMessages = 0;

        show($("#chatPanel"));

        updateChatBadge();

        if (state.socket?.connected) {

            state.socket.emit(
                "game_chat_history"
            );
        }

        scrollChatToBottom();
    }


    function closeChat() {

        state.chatOpen = false;

        hide($("#chatPanel"));
    }


    function sendChatMessage() {

        if (!state.currentUser) {
            return;
        }

        const input =
            $("#chatInput");

        if (!input) {
            return;
        }

        const message =
            input.value.trim();

        if (!message) {
            return;
        }

        if (
            message.length >
            CONFIG.MAX_MESSAGE_LENGTH
        ) {

            toast(
                `پیام باید حداکثر ${CONFIG.MAX_MESSAGE_LENGTH} کاراکتر باشد.`
            );

            return;
        }

        if (!state.socket?.connected) {

            toast(
                "اتصال به سرور برقرار نیست."
            );

            return;
        }

        state.socket.emit(
            "game_chat",
            {
                username:
                    state.currentUser.username,

                message
            }
        );

        input.value = "";
        input.focus();
    }


    function renderChatHistory(messages) {

        const container =
            $("#chatMessages");

        if (!container) {
            return;
        }

        container.innerHTML = "";

        if (!messages.length) {

            addSystemMessage(
                "هنوز پیامی نیست. اولین پیام رو بفرست 👋"
            );

            return;
        }

        messages.forEach(
            addChatMessage
        );

        scrollChatToBottom();
    }


    function addChatMessage(data) {

        if (!data) {
            return;
        }

        const container =
            $("#chatMessages");

        if (!container) {
            return;
        }

        const username =
            data.username || "";

        const isMine =
            state.currentUser &&
            username ===
                state.currentUser.username;

        const wrapper =
            document.createElement("div");

        wrapper.className =
            `chat-message ${
                isMine
                    ? "mine"
                    : "other"
            }`;

        const bubble =
            document.createElement("div");

        bubble.className =
            "message-bubble";

        const sender =
            document.createElement("div");

        sender.className =
            "message-meta";

        let senderName =
            data.display_name ||
            state.players[username]?.display_name ||
            CONFIG.PLAYERS[username]?.name ||
            username;

        sender.textContent =
            isMine
                ? "شما"
                : senderName;

        bubble.appendChild(sender);

        const message =
            data.message || "";

        if (
            data.is_image ||
            isImageUrl(message)
        ) {

            const image =
                document.createElement("img");

            image.className =
                "message-image";

            image.src =
                absoluteUrl(message);

            image.alt =
                "تصویر ارسال شده";

            image.loading =
                "lazy";

            bubble.appendChild(image);

        } else {

            const text =
                document.createElement("div");

            text.textContent =
                message;

            bubble.appendChild(text);
        }

        wrapper.appendChild(bubble);

        container.appendChild(wrapper);

        scrollChatToBottom();
    }


    function addSystemMessage(message) {

        const container =
            $("#chatMessages");

        if (!container) {
            return;
        }

        const item =
            document.createElement("div");

        item.className =
            "system-message";

        item.textContent =
            message;

        container.appendChild(item);

        scrollChatToBottom();
    }


    function updateChatBadge() {

        const badge =
            $("#chatBadge");

        const floatingBadge =
            $("#floatingChatBadge");

        const count =
            state.unreadMessages;

        if (count > 0) {

            setText(
                badge,
                count > 99
                    ? "99+"
                    : count
            );

            setText(
                floatingBadge,
                count > 99
                    ? "99+"
                    : count
            );

            show(badge);
            show(floatingBadge);

        } else {

            hide(badge);
            hide(floatingBadge);
        }
    }


    function scrollChatToBottom() {

        const container =
            $("#chatMessages");

        if (!container) {
            return;
        }

        window.requestAnimationFrame(
            () => {
                container.scrollTop =
                    container.scrollHeight;
            }
        );
    }


    function isImageUrl(value) {

        if (
            typeof value !==
            "string"
        ) {
            return false;
        }

        return (
            value.startsWith(
                "/api/game/uploads/"
            ) ||
            /\.(jpg|jpeg|png|webp|gif)(\?.*)?$/i.test(
                value
            )
        );
    }


    /* =====================================================
       CHAT IMAGE
    ===================================================== */

    async function uploadChatImage(file) {

        if (!state.currentUser || !file) {
            return;
        }

        if (!file.type.startsWith("image/")) {

            toast(
                "فقط فایل تصویری انتخاب کن."
            );

            return;
        }

        if (file.size > 5 * 1024 * 1024) {

            toast(
                "حجم تصویر نباید بیشتر از ۵ مگابایت باشد."
            );

            return;
        }

        const formData =
            new FormData();

        formData.append(
            "image",
            file
        );

        formData.append(
            "username",
            state.currentUser.username
        );

        try {

            toast(
                "در حال ارسال تصویر..."
            );

            const response =
                await fetch(
                    `${CONFIG.API_BASE}/api/game/chat/upload`,
                    {
                        method: "POST",
                        body: formData
                    }
                );

            const data =
                await response.json();

            if (!response.ok) {

                throw new Error(
                    data.error ||
                    "ارسال تصویر انجام نشد."
                );
            }

            if (
                state.socket?.connected &&
                data.url
            ) {

                state.socket.emit(
                    "game_chat_image",
                    {
                        username:
                            state.currentUser.username,

                        image_url:
                            data.url
                    }
                );

            } else {

                toast(
                    "اتصال چت برقرار نیست."
                );
            }

        } catch (error) {

            console.error(error);

            toast(
                error.message ||
                "ارسال تصویر ناموفق بود."
            );
        }
    }


    /* =====================================================
       GAMES
    ===================================================== */

    // SPY_START_API_CONNECTED



    


/* ============================================================
   SPY GAME - SINGLE CLEAN UI
   ============================================================ */

const SpyGameUI = {
    gameId: null,
    replyTo: null,
    selectedVote: null,
    messages: [],
    lastPhase: null,
    boundSocket: null,

    open(gameId = "spy-main-room") {
        this.gameId = gameId || "spy-main-room";
        this.replyTo = null;
        this.selectedVote = null;
        this.messages = [];
        this.lastPhase = null;

        state.currentGame = {
            type: "spy",
            gameId: this.gameId,
            data: null
        };

        this.render();
        this.bind();

        this.ensureSocket();

        return true;
    },

    ensureSocket() {
        if (!state.currentUser) {
            toast("ابتدا وارد حساب شو.");
            return;
        }

        if (
            !state.socket ||
            !state.socket.connected
        ) {
            if (
                typeof connectSocket === "function"
            ) {
                connectSocket();
            }
            return;
        }

        this.enterRoom();
    },

    enterRoom() {
        if (
            !state.socket ||
            !state.socket.connected ||
            !state.currentUser
        ) {
            return;
        }

        const username =
            state.currentUser.username;

        state.socket.emit(
            "spy_create",
            {
                game_id: this.gameId,
                username
            }
        );

        state.socket.emit(
            "spy_join",
            {
                game_id: this.gameId,
                username
            }
        );

        state.socket.emit(
            "spy_join_chat",
            {
                game_id: this.gameId,
                username
            }
        );

        state.socket.emit(
            "spy_chat_history",
            {
                game_id: this.gameId
            }
        );

        state.socket.emit(
            "spy_state",
            {
                game_id: this.gameId,
                username
            }
        );
    },

    render() {
        const modal = $("#gameModal");

        if (!modal) {
            return;
        }

        modal.innerHTML = `
            <div class="spy-v2">
                <div class="spy-v2-header">
                    <div>
                        <div class="spy-v2-title">
                            🕵️ بازی جاسوس
                        </div>
                        <div id="spyStatus"
                             class="spy-v2-subtitle">
                            در حال اتصال...
                        </div>
                    </div>

                    <button
                        type="button"
                        id="spyClose"
                        class="spy-v2-close"
                    >×</button>
                </div>

                <div id="spyLobby"
                     class="spy-v2-panel"></div>

                <div id="spyRole"
                     class="spy-v2-panel"></div>

                <div id="spyTimer"
                     class="spy-v2-panel"></div>

                <div id="spyPlayers"
                     class="spy-v2-panel"></div>

                <div id="spyVoting"
                     class="spy-v2-panel"></div>

                <div id="spyGuess"
                     class="spy-v2-panel"></div>

                <div id="spyResult"
                     class="spy-v2-panel"></div>

                <div class="spy-v2-chat">
                    <div class="spy-v2-chat-head">
                        <div>
                            <strong>💬 گفت‌وگوی بازی</strong>
                            <span id="spyNewMessage"
                                  hidden>
                                پیام جدید
                            </span>
                        </div>
                    </div>

                    <div
                        id="spyMessages"
                        class="spy-v2-messages"
                    ></div>

                    <div
                        id="spyReply"
                        class="spy-v2-reply"
                        hidden
                    >
                        <div>
                            <small>در پاسخ به</small>
                            <strong id="spyReplyText"></strong>
                        </div>

                        <button
                            type="button"
                            id="spyCancelReply"
                        >×</button>
                    </div>

                    <div class="spy-v2-input-row">
                        <input
                            id="spyInput"
                            type="text"
                            maxlength="1000"
                            autocomplete="off"
                            placeholder="پیامت رو بنویس..."
                        >

                        <button
                            type="button"
                            id="spySend"
                            class="spy-v2-primary"
                        >ارسال</button>
                    </div>
                </div>
            </div>
        `;

        show(modal);
    },

    bind() {
        $("#spyClose")?.addEventListener(
            "click",
            () => this.close()
        );

        $("#spySend")?.addEventListener(
            "click",
            () => this.sendChat()
        );

        $("#spyInput")?.addEventListener(
            "keydown",
            (event) => {
                if (
                    event.key === "Enter" &&
                    !event.shiftKey
                ) {
                    event.preventDefault();
                    this.sendChat();
                }
            }
        );

        $("#spyCancelReply")?.addEventListener(
            "click",
            () => {
                this.replyTo = null;
                this.renderReply();
            }
        );

        $("#spyNewMessage")?.addEventListener(
            "click",
            () => {
                const box = $("#spyMessages");

                if (box) {
                    box.scrollTop =
                        box.scrollHeight;
                    box.classList.remove(
                        "has-new"
                    );
                }

                hide($("#spyNewMessage"));
            }
        );
    },

    renderLobby(data) {
        const box = $("#spyLobby");

        if (!box) return;

        const players =
            Array.isArray(data.players)
                ? data.players
                : [];

        const me =
            state.currentUser?.username;

        const isHost =
            data.host === me ||
            players.some(
                p =>
                    p.username === me &&
                    p.is_host
            );

        if (data.phase !== "lobby") {
            box.innerHTML = "";
            return;
        }

        box.innerHTML = `
            <div class="spy-v2-section-title">
                انتظار بازیکن‌ها
            </div>

            <div class="spy-v2-count">
                ${players.length}/${data.max_players || 5}
            </div>

            ${
                isHost
                    ? `
                    <label class="spy-v2-label">
                        زمان بحث، به ثانیه
                    </label>

                    <input
                        id="spyDiscussion"
                        class="spy-v2-number"
                        type="number"
                        min="10"
                        max="1800"
                        value="120"
                    >

                    <button
                        type="button"
                        id="spyStart"
                        class="spy-v2-primary spy-v2-wide"
                    >
                        شروع بازی
                    </button>
                    `
                    : `
                    <div class="spy-v2-wait">
                        منتظر سازنده بازی هستیم...
                    </div>
                    `
            }
        `;

        $("#spyStart")?.addEventListener(
            "click",
            () => {
                let seconds =
                    Number(
                        $("#spyDiscussion")?.value
                        || 120
                    );

                if (!Number.isFinite(seconds)) {
                    seconds = 120;
                }

                seconds = Math.max(
                    10,
                    Math.min(
                        1800,
                        Math.floor(seconds)
                    )
                );

                if (
                    !state.socket?.connected
                ) {
                    toast(
                        "اتصال به سرور برقرار نیست."
                    );
                    return;
                }

                state.socket.emit(
                    "spy_start",
                    {
                        game_id: this.gameId,
                        username:
                            state.currentUser.username,
                        discussion_seconds:
                            seconds
                    }
                );
            }
        );
    },

    renderRole(data) {
        const box = $("#spyRole");

        if (!box) return;

        if (data.phase === "lobby") {
            box.innerHTML = "";
            return;
        }

        if (data.my_role === "spy") {
            box.innerHTML = `
                <div class="spy-role spy-role-spy">
                    <div class="spy-role-icon">🕵️</div>
                    <strong>شما جاسوس هستید</strong>
                    <span>
                        کلمه را نمی‌بینی.
                        سعی کن از صحبت‌ها بفهمی.
                    </span>

                    ${
                        data.can_guess
                            ? `
                            <button
                                type="button"
                                id="spyGuessOpen"
                                class="spy-v2-secondary spy-v2-wide"
                            >
                                کلمه رو فهمیدم
                            </button>
                            `
                            : ""
                    }
                </div>
            `;
        } else if (data.my_role === "citizen") {
            box.innerHTML = `
                <div class="spy-role spy-role-citizen">
                    <div class="spy-role-icon">👤</div>
                    <strong>شهروند هستی</strong>
                    <span>کلمه مخفی:</span>
                    <b>${escapeHtml(
                        data.secret_word || "—"
                    )}</b>
                </div>
            `;
        } else {
            box.innerHTML = "";
        }

        $("#spyGuessOpen")?.addEventListener(
            "click",
            () => this.renderGuessForm()
        );
    },

    renderTimer(data) {
        const box = $("#spyTimer");

        if (!box) return;

        if (
            data.phase !== "discussion" &&
            data.phase !== "voting"
        ) {
            box.innerHTML = "";
            return;
        }

        const seconds = Math.max(
            0,
            Number(
                data.remaining_seconds || 0
            )
        );

        const title =
            data.phase === "discussion"
                ? "💬 زمان بحث"
                : "🗳️ زمان رأی‌گیری";

        box.innerHTML = `
            <div class="spy-timer">
                <span>${title}</span>
                <strong>${seconds}</strong>
                <small>ثانیه</small>
            </div>
        `;
    },

    renderPlayers(data) {
        const box = $("#spyPlayers");

        if (!box) return;

        const players =
            Array.isArray(data.players)
                ? data.players
                : [];

        if (!players.length) {
            box.innerHTML = "";
            return;
        }

        box.innerHTML = `
            <div class="spy-v2-section-title">
                بازیکن‌ها
            </div>

            <div class="spy-player-list">
                ${players.map(player => `
                    <div class="spy-player">
                        <span>
                            ${
                                player.is_host
                                    ? "👑 "
                                    : "🎮 "
                            }
                            ${escapeHtml(
                                player.username
                            )}
                        </span>

                        <span>
                            ${
                                player.connected
                                    ? "🟢"
                                    : "🔴"
                            }
                        </span>
                    </div>
                `).join("")}
            </div>
        `;
    },

    renderVoting(data) {
        const box = $("#spyVoting");

        if (!box) return;

        if (data.phase !== "voting") {
            box.innerHTML = "";
            return;
        }

        const players =
            Array.isArray(data.players)
                ? data.players
                : [];

        const me =
            state.currentUser?.username;

        box.innerHTML = `
            <div class="spy-vote-card">
                <div class="spy-v2-section-title">
                    چه کسی جاسوس است؟
                </div>

                <div class="spy-vote-list">
                    ${players
                        .filter(
                            p =>
                                p.username !== me
                        )
                        .map(player => `
                            <button
                                type="button"
                                class="
                                    spy-vote-button
                                    ${
                                        this.selectedVote ===
                                        player.username
                                            ? "selected"
                                            : ""
                                    }
                                "
                                data-spy-vote="${escapeHtml(
                                    player.username
                                )}"
                            >
                                <span>🎮</span>
                                ${escapeHtml(
                                    player.username
                                )}
                            </button>
                        `)
                        .join("")}
                </div>

                <div class="spy-vote-note">
                    می‌تونی تا پایان ۱۰ ثانیه رأی خودت رو تغییر بدی.
                </div>
            </div>
        `;

        box
            .querySelectorAll(
                "[data-spy-vote]"
            )
            .forEach(button => {
                button.addEventListener(
                    "click",
                    () => {
                        const target =
                            button.dataset.spyVote;

                        this.selectedVote = target;

                        state.socket?.emit(
                            "spy_vote",
                            {
                                game_id:
                                    this.gameId,
                                username:
                                    state.currentUser
                                        ?.username,
                                target
                            }
                        );

                        this.renderVoting(
                            data
                        );
                    }
                );
            });
    },

    renderGuessForm() {
        const box = $("#spyGuess");

        if (!box) return;

        box.innerHTML = `
            <div class="spy-guess-card">
                <div class="spy-v2-section-title">
                    حدس کلمه
                </div>

                <input
                    id="spyGuessInput"
                    type="text"
                    maxlength="100"
                    class="spy-v2-text"
                    placeholder="کلمه‌ای که فکر می‌کنی..."
                >

                <div class="spy-v2-actions">
                    <button
                        type="button"
                        id="spyGuessCancel"
                        class="spy-v2-muted"
                    >
                        برگشت
                    </button>

                    <button
                        type="button"
                        id="spyGuessSubmit"
                        class="spy-v2-primary"
                    >
                        ثبت حدس
                    </button>
                </div>
            </div>
        `;

        $("#spyGuessCancel")?.addEventListener(
            "click",
            () => {
                box.innerHTML = "";
            }
        );

        $("#spyGuessSubmit")?.addEventListener(
            "click",
            () => {
                const input =
                    $("#spyGuessInput");

                const guess =
                    input?.value.trim();

                if (!guess) {
                    toast(
                        "حدست رو وارد کن."
                    );
                    return;
                }

                state.socket?.emit(
                    "spy_guess",
                    {
                        game_id: this.gameId,
                        username:
                            state.currentUser
                                ?.username,
                        guess
                    }
                );
            }
        );

        $("#spyGuessInput")?.focus();
    },

    renderResult(result) {
        const box = $("#spyResult");

        if (!box || !result) return;

        const winner =
            result.winner === "spy"
                ? "جاسوس"
                : "شهروندها";

        box.innerHTML = `
            <div class="spy-result">
                <div class="spy-result-icon">
                    ${
                        result.winner === "spy"
                            ? "🕵️"
                            : "🎉"
                    }
                </div>

                <strong>
                    برنده: ${winner}
                </strong>

                <span>
                    ${escapeHtml(
                        result.reason || ""
                    )}
                </span>

                <div class="spy-result-details">
                    <div>
                        جاسوس:
                        <b>${escapeHtml(
                            result.spy || "—"
                        )}</b>
                    </div>

                    <div>
                        کلمه:
                        <b>${escapeHtml(
                            result.secret_word || "—"
                        )}</b>
                    </div>

                    ${
                        result.eliminated
                            ? `
                            <div>
                                انتخاب‌شده:
                                <b>${escapeHtml(
                                    result.eliminated
                                )}</b>
                            </div>
                            `
                            : ""
                    }
                </div>
            </div>
        `;
    },

    setStatus(text, seconds = null) {
        const box = $("#spyStatus");

        if (!box) return;

        box.textContent =
            seconds === null
                ? text
                : `${text} • ${seconds} ثانیه`;
    },

    renderState(data) {
        if (!data) return;

        if (data.game_id) {
            this.gameId =
                data.game_id;

            if (state.currentGame) {
                state.currentGame.gameId =
                    data.game_id;
            }
        }

        this.lastPhase =
            data.phase;

        this.renderLobby(data);
        this.renderRole(data);
        this.renderTimer(data);
        this.renderPlayers(data);

        if (data.phase === "voting") {
            this.renderVoting(data);
        } else {
            $("#spyVoting").innerHTML = "";
        }

        if (data.phase === "finished") {
            this.renderResult(
                data.result
            );
        }

        const labels = {
            lobby: "در انتظار بازیکن‌ها",
            discussion: "💬 مرحله بحث",
            voting: "🗳️ مرحله رأی‌گیری",
            finished: "🏁 بازی تمام شد"
        };

        this.setStatus(
            labels[data.phase]
                || "بازی جاسوس"
        );
    },

    renderReply() {
        const box = $("#spyReply");
        const text = $("#spyReplyText");

        if (!box || !text) return;

        if (!this.replyTo) {
            box.hidden = true;
            text.textContent = "";
            return;
        }

        box.hidden = false;

        text.textContent =
            this.replyTo.username
                ? `${this.replyTo.username}: ${this.replyTo.message}`
                : this.replyTo.message;
    },

    sendChat() {
        const input = $("#spyInput");

        if (!input) return;

        const message =
            input.value.trim();

        if (!message) return;

        if (
            !state.socket?.connected
        ) {
            toast(
                "اتصال به سرور برقرار نیست."
            );
            return;
        }

        state.socket.emit(
            "spy_chat",
            {
                game_id: this.gameId,
                username:
                    state.currentUser?.username,
                message,
                reply_to:
                    this.replyTo?.id || null
            }
        );

        input.value = "";
        this.replyTo = null;
        this.renderReply();
    },

    renderChatHistory(messages) {
        this.messages =
            Array.isArray(messages)
                ? messages
                : [];

        const box = $("#spyMessages");

        if (!box) return;

        box.innerHTML = "";

        this.messages.forEach(
            message => {
                this.renderChatMessage(
                    message,
                    false
                );
            }
        );

        box.scrollTop =
            box.scrollHeight;
    },

    renderChatMessage(
        data,
        autoScroll = true
    ) {
        const box = $("#spyMessages");

        if (!box || !data) return;

        const item =
            document.createElement("div");

        item.className =
            "spy-message";

        if (
            data.username ===
            state.currentUser?.username
        ) {
            item.classList.add("mine");
        }

        const reply =
            data.reply_to
                ? `
                    <button
                        type="button"
                        class="spy-message-reply"
                        data-jump-reply
                        data-jump-id="${escapeHtml(
                            data.reply_to
                        )}"
                    >
                        ↩ پاسخ به پیام
                    </button>
                `
                : "";

        item.dataset.messageId =
            data.id || "";

        item.innerHTML = `
            <div class="spy-message-head">
                <strong>
                    ${escapeHtml(
                        data.username || "کاربر"
                    )}
                </strong>
            </div>

            ${reply}

            <div class="spy-message-text">
                ${escapeHtml(
                    data.message || ""
                )}
            </div>

            <button
                type="button"
                class="spy-message-action"
                data-reply
            >
                پاسخ
            </button>
        `;

        item
            .querySelector("[data-reply]")
            ?.addEventListener(
                "click",
                () => {
                    this.replyTo = {
                        id: data.id,
                        username:
                            data.username,
                        message:
                            data.message
                    };

                    this.renderReply();
                    $("#spyInput")?.focus();
                }
            );

        item
            .querySelector("[data-jump-reply]")
            ?.addEventListener(
                "click",
                () => {
                    const id =
                        item
                            .querySelector(
                                "[data-jump-reply]"
                            )
                            ?.dataset.jumpId;

                    if (!id) return;

                    const target =
                        box.querySelector(
                            `[data-message-id="${CSS.escape(id)}"]`
                        );

                    target?.scrollIntoView({
                        behavior: "smooth",
                        block: "center"
                    });
                }
            );

        box.appendChild(item);

        if (autoScroll) {
            const nearBottom =
                box.scrollHeight -
                box.scrollTop -
                box.clientHeight < 120;

            if (nearBottom) {
                box.scrollTop =
                    box.scrollHeight;
            }
        }
    },

    close() {
        if (
            state.socket?.connected
        ) {
            state.socket.emit(
                "spy_leave",
                {
                    game_id: this.gameId,
                    username:
                        state.currentUser
                            ?.username
                }
            );
        }

        state.currentGame = null;

        hide($("#gameModal"));
    }
};


/* ============================================================
   SPY SOCKET EVENTS
   ============================================================ */

function setupSpySocketListeners() {
    const socket = state.socket;

    if (
        !socket ||
        socket === SpyGameUI.boundSocket
    ) {
        return;
    }

    SpyGameUI.boundSocket =
        socket;

    socket.on(
        "connect",
        () => {
            if (
                state.currentGame?.type ===
                "spy"
            ) {
                SpyGameUI.enterRoom();
            }
        }
    );

    socket.on(
        "spy_created",
        data => {
            SpyGameUI.renderState(
                data
            );
        }
    );

    socket.on(
        "spy_joined",
        data => {
            SpyGameUI.renderState(
                data
            );
        }
    );

    socket.on(
        "spy_state",
        data => {
            SpyGameUI.renderState(
                data
            );
        }
    );

    socket.on(
        "spy_started",
        () => {
            socket.emit(
                "spy_state",
                {
                    game_id:
                        SpyGameUI.gameId,
                    username:
                        state.currentUser
                            ?.username
                }
            );
        }
    );

    socket.on(
        "spy_tick",
        data => {
            if (!data) return;

            SpyGameUI.renderTimer(
                data
            );

            if (
                data.phase === "voting"
            ) {
                SpyGameUI.renderVoting(
                    {
                        ...data,
                        players:
                            state.currentGame
                                ?.data
                                ?.players || []
                    }
                );
            }

            if (
                data.phase === "finished"
            ) {
                SpyGameUI.renderResult(
                    data.result
                );
            }
        }
    );

    socket.on(
        "spy_voting_started",
        data => {
            SpyGameUI.selectedVote =
                null;

            SpyGameUI.renderState(
                {
                    ...data,
                    phase: "voting"
                }
            );
        }
    );

    socket.on(
        "spy_vote",
        data => {
            if (
                data?.username ===
                state.currentUser?.username
            ) {
                toast(
                    "✅ رأی ثبت شد."
                );
            }
        }
    );

    socket.on(
        "spy_finished",
        data => {
            SpyGameUI.renderResult(
                data
            );

            SpyGameUI.renderState(
                {
                    ...data,
                    phase: "finished",
                    result: data
                }
            );
        }
    );

    socket.on(
        "spy_chat_history",
        data => {
            SpyGameUI.renderChatHistory(
                Array.isArray(data)
                    ? data
                    : data?.messages || []
            );
        }
    );

    socket.on(
        "spy_chat",
        data => {
            const box =
                $("#spyMessages");

            if (!box) return;

            const nearBottom =
                box.scrollHeight -
                box.scrollTop -
                box.clientHeight < 120;

            SpyGameUI.renderChatMessage(
                data,
                nearBottom
            );

            if (!nearBottom) {
                box.classList.add(
                    "has-new"
                );

                show(
                    $("#spyNewMessage")
                );
            }
        }
    );

    socket.on(
        "spy_error",
        data => {
            toast(
                data?.message ||
                data?.error ||
                "خطایی در بازی جاسوس رخ داد."
            );
        }
    );
}

setupSpySocketListeners();



/* =====================================================
   MEHESTAN GAME UI
   ===================================================== */

const MehestanGameUI = {

    open() {
        state.currentGame = {
            type: "mehestan",
            gameId: null,
            data: null
        };

        const content = $("#gameContent");

        if (!content) {
            toast("محیط مهستان پیدا نشد.");
            return;
        }

        content.innerHTML = `
            <div class="mehestan-shell">

                <div class="mehestan-header">
                    <div class="mehestan-header-icon">🕵️‍♂️</div>

                    <div>
                        <div class="mehestan-title">پرونده مرموز — شهر مهستان</div>
                        <div class="mehestan-subtitle">
                            واحد تحقیقات جنایی
                        </div>
                    </div>
                </div>

                <div class="mehestan-intro">

                    <div class="mehestan-case-badge">
                        پرونده شماره M-001
                    </div>

                    <h1>پرونده قتل در شهر مهستان</h1>

                    <p>
                        یک پرونده جنایی جدید در شهر مهستان ثبت شده است.
                        اطلاعات اولیه پرونده هنوز ناقص است و تحقیقات رسمی
                        از این لحظه آغاز می‌شود.
                    </p>

                    <div class="mehestan-case-grid">

                        <div class="mehestan-case-item">
                            <span>🕘</span>
                            <strong>زمان حادثه</strong>
                            <small>23:40</small>
                        </div>

                        <div class="mehestan-case-item">
                            <span>📍</span>
                            <strong>محل اولیه</strong>
                            <small>در حال شناسایی</small>
                        </div>

                        <div class="mehestan-case-item">
                            <span>👤</span>
                            <strong>وضعیت قربانی</strong>
                            <small>تأیید شده</small>
                        </div>

                    </div>

                    <div class="mehestan-objective">

                        <div class="mehestan-objective-title">
                            🎯 مأموریت شما
                        </div>

                        <p>
                            محیط شهر را بررسی کنید، سرنخ‌ها را پیدا کنید،
                            ارتباط میان افراد و مکان‌ها را کشف کنید و
                            حقیقت پرونده را به دست آورید.
                        </p>

                    </div>

                    <button
                        id="mehestanEnterCity"
                        class="mehestan-primary-button"
                        type="button"
                    >
                        🗺️ ورود به شهر مهستان
                    </button>

                </div>

            </div>
        `;

        show($("#gameModal"));

        $("#mehestanEnterCity")?.addEventListener(
            "click",
            () => this.enterCity()
        );
    },

    enterCity() {

        const content = $("#gameContent");

        if (!content) {
            toast("محیط مهستان پیدا نشد.");
            return;
        }

        const locations = [
  {id:"hospital-central",name:"بیمارستان مرکزی مهستان",category:"hospital",icon:"🏥",x:48,y:52},
  {id:"hospital-pahlavi",name:"بیمارستان پهلوی",category:"hospital",icon:"🏥",x:25,y:30},
  {id:"hospital-valiasr",name:"بیمارستان ولیعصر",category:"hospital",icon:"🏥",x:68,y:35},
  {id:"hospital-shafa",name:"بیمارستان شفا",category:"hospital",icon:"🏥",x:82,y:62},
  {id:"hospital-noor",name:"بیمارستان نور",category:"hospital",icon:"🏥",x:35,y:73},
  {id:"hospital-rajai",name:"بیمارستان رجایی",category:"hospital",icon:"🏥",x:57,y:22},
  {id:"hospital-emam",name:"بیمارستان امام",category:"hospital",icon:"🏥",x:16,y:47},
  {id:"clinic-salamat",name:"درمانگاه سلامت",category:"hospital",icon:"🩺",x:73,y:19},
  {id:"clinic-shahr",name:"درمانگاه شبانه‌روزی شهر",category:"hospital",icon:"🩺",x:88,y:44},
  {id:"clinic-omid",name:"درمانگاه امید",category:"hospital",icon:"🩺",x:42,y:82},
  {id:"court-central",name:"دادگستری مرکزی مهستان",category:"court",icon:"⚖️",x:54,y:45},
  {id:"court-family",name:"دادگاه خانواده",category:"court",icon:"⚖️",x:61,y:38},
  {id:"court-criminal",name:"دادگاه کیفری",category:"court",icon:"⚖️",x:47,y:28},
  {id:"court-civil",name:"دادگاه حقوقی",category:"court",icon:"⚖️",x:76,y:52},
  {id:"court-justice",name:"شورای حل اختلاف",category:"court",icon:"⚖️",x:29,y:65},
  {id:"police-central",name:"کلانتری مرکزی",category:"police",icon:"🚓",x:52,y:57},
  {id:"police-pahlavi",name:"کلانتری پهلوی",category:"police",icon:"🚓",x:22,y:27},
  {id:"police-valiasr",name:"کلانتری ولیعصر",category:"police",icon:"🚓",x:74,y:32},
  {id:"police-north",name:"کلانتری شمال",category:"police",icon:"🚓",x:86,y:21},
  {id:"police-south",name:"کلانتری جنوب",category:"police",icon:"🚓",x:31,y:84},
  {id:"police-east",name:"کلانتری شرق",category:"police",icon:"🚓",x:91,y:58},
  {id:"police-west",name:"کلانتری غرب",category:"police",icon:"🚓",x:11,y:54},
  {id:"police-crime",name:"پلیس آگاهی",category:"police",icon:"🕵️",x:63,y:67},
  {id:"bank-melli-1",name:"بانک ملی شعبه مرکزی",category:"bank",icon:"🏦",x:46,y:48},
  {id:"bank-melli-2",name:"بانک ملی شعبه ولیعصر",category:"bank",icon:"🏦",x:71,y:27},
  {id:"bank-melli-3",name:"بانک ملی شعبه پهلوی",category:"bank",icon:"🏦",x:27,y:36},
  {id:"bank-mellat-1",name:"بانک ملت شعبه مرکزی",category:"bank",icon:"🏦",x:57,y:54},
  {id:"bank-mellat-2",name:"بانک ملت شعبه شمال",category:"bank",icon:"🏦",x:81,y:18},
  {id:"bank-mellat-3",name:"بانک ملت شعبه جنوب",category:"bank",icon:"🏦",x:38,y:78},
  {id:"bank-saderat-1",name:"بانک صادرات شعبه مرکزی",category:"bank",icon:"🏦",x:39,y:42},
  {id:"bank-saderat-2",name:"بانک صادرات شعبه امیرکبیر",category:"bank",icon:"🏦",x:67,y:61},
  {id:"bank-tejarat-1",name:"بانک تجارت شعبه مرکزی",category:"bank",icon:"🏦",x:60,y:72},
  {id:"bank-tejarat-2",name:"بانک تجارت شعبه شرق",category:"bank",icon:"🏦",x:84,y:51},
  {id:"bank-refah-1",name:"بانک رفاه شعبه بیمارستان",category:"bank",icon:"🏦",x:49,y:66},
  {id:"bank-refah-2",name:"بانک رفاه شعبه بازار",category:"bank",icon:"🏦",x:19,y:61},
  {id:"gold-bazaar-1",name:"طلافروشی الماس",category:"gold",icon:"💎",x:43,y:39},
  {id:"gold-bazaar-2",name:"طلافروشی نگین",category:"gold",icon:"💎",x:48,y:37},
  {id:"gold-bazaar-3",name:"طلافروشی مهستان",category:"gold",icon:"💎",x:52,y:39},
  {id:"gold-valiasr",name:"طلافروشی ولیعصر",category:"gold",icon:"💎",x:69,y:42},
  {id:"gold-pahlavi",name:"طلافروشی پهلوی",category:"gold",icon:"💎",x:24,y:42},
  {id:"mobile-central-1",name:"موبایل مرکزی ۱",category:"mobile",icon:"📱",x:45,y:33},
  {id:"mobile-central-2",name:"موبایل مرکزی ۲",category:"mobile",icon:"📱",x:49,y:31},
  {id:"mobile-valiasr-1",name:"موبایل ولیعصر",category:"mobile",icon:"📱",x:72,y:45},
  {id:"mobile-valiasr-2",name:"موبایل ولیعصر شعبه ۲",category:"mobile",icon:"📱",x:76,y:47},
  {id:"mobile-pahlavi",name:"موبایل پهلوی",category:"mobile",icon:"📱",x:29,y:31},
  {id:"mobile-amirkabir",name:"موبایل امیرکبیر",category:"mobile",icon:"📱",x:61,y:24},
  {id:"mobile-south",name:"موبایل جنوب",category:"mobile",icon:"📱",x:37,y:75},
  {id:"store-central-1",name:"فروشگاه مرکزی",category:"store",icon:"🛍️",x:40,y:51},
  {id:"store-central-2",name:"فروشگاه مرکزی شعبه ۲",category:"store",icon:"🛍️",x:43,y:54},
  {id:"store-pahlavi-1",name:"فروشگاه پهلوی",category:"store",icon:"🛍️",x:23,y:34},
  {id:"store-pahlavi-2",name:"فروشگاه پهلوی شعبه ۲",category:"store",icon:"🛍️",x:27,y:39},
  {id:"store-valiasr-1",name:"فروشگاه ولیعصر",category:"store",icon:"🛍️",x:73,y:39},
  {id:"store-valiasr-2",name:"فروشگاه ولیعصر شعبه ۲",category:"store",icon:"🛍️",x:78,y:42},
  {id:"store-east",name:"فروشگاه شرق",category:"store",icon:"🛍️",x:88,y:55},
  {id:"store-west",name:"فروشگاه غرب",category:"store",icon:"🛍️",x:15,y:58},
  {id:"market-central",name:"هایپرمارکت مرکزی",category:"supermarket",icon:"🛒",x:51,y:62},
  {id:"market-pahlavi",name:"هایپرمارکت پهلوی",category:"supermarket",icon:"🛒",x:19,y:29},
  {id:"market-valiasr",name:"هایپرمارکت ولیعصر",category:"supermarket",icon:"🛒",x:79,y:30},
  {id:"market-north",name:"هایپرمارکت شمال",category:"supermarket",icon:"🛒",x:64,y:14},
  {id:"market-south",name:"هایپرمارکت جنوب",category:"supermarket",icon:"🛒",x:48,y:88},
  {id:"market-east",name:"هایپرمارکت شرق",category:"supermarket",icon:"🛒",x:92,y:70},
  {id:"market-west",name:"هایپرمارکت غرب",category:"supermarket",icon:"🛒",x:9,y:72},
  {id:"hotel-shahr",name:"هتل شهر",category:"hotel",icon:"🏨",x:56,y:50},
  {id:"hotel-mahestan",name:"هتل بزرگ مهستان",category:"hotel",icon:"🏨",x:62,y:57},
  {id:"hotel-pahlavi",name:"هتل پهلوی",category:"hotel",icon:"🏨",x:31,y:25},
  {id:"hotel-valiasr",name:"هتل ولیعصر",category:"hotel",icon:"🏨",x:76,y:26},
  {id:"hotel-rail",name:"هتل ایستگاه",category:"hotel",icon:"🏨",x:17,y:43},
  {id:"hotel-river",name:"هتل ساحل رودخانه",category:"hotel",icon:"🏨",x:85,y:77},
  {id:"restaurant-central-1",name:"رستوران مرکزی",category:"restaurant",icon:"🍽️",x:44,y:57},
  {id:"restaurant-central-2",name:"رستوران سنتی مهستان",category:"restaurant",icon:"🍽️",x:50,y:58},
  {id:"restaurant-pahlavi-1",name:"رستوران پهلوی",category:"restaurant",icon:"🍽️",x:25,y:48},
  {id:"restaurant-pahlavi-2",name:"رستوران شبانه پهلوی",category:"restaurant",icon:"🍽️",x:30,y:52},
  {id:"restaurant-valiasr-1",name:"رستوران ولیعصر",category:"restaurant",icon:"🍽️",x:70,y:52},
  {id:"restaurant-valiasr-2",name:"رستوران دریچه شهر",category:"restaurant",icon:"🍽️",x:78,y:58},
  {id:"restaurant-north",name:"رستوران شمال",category:"restaurant",icon:"🍽️",x:59,y:17},
  {id:"restaurant-south",name:"رستوران جنوب",category:"restaurant",icon:"🍽️",x:42,y:82},
  {id:"pharmacy-central",name:"داروخانه مرکزی",category:"pharmacy",icon:"💊",x:53,y:47},
  {id:"pharmacy-shafa",name:"داروخانه شفا",category:"pharmacy",icon:"💊",x:48,y:70},
  {id:"pharmacy-pahlavi",name:"داروخانه پهلوی",category:"pharmacy",icon:"💊",x:26,y:57},
  {id:"pharmacy-valiasr",name:"داروخانه ولیعصر",category:"pharmacy",icon:"💊",x:82,y:36},
  {id:"pharmacy-night",name:"داروخانه شبانه‌روزی",category:"pharmacy",icon:"💊",x:67,y:76},
  {id:"pharmacy-hospital",name:"داروخانه بیمارستان",category:"pharmacy",icon:"💊",x:51,y:55},
  {id:"telecom-central",name:"مخابرات مرکزی",category:"telecom",icon:"📡",x:55,y:41},
  {id:"telecom-pahlavi",name:"مخابرات پهلوی",category:"telecom",icon:"📡",x:21,y:51},
  {id:"telecom-valiasr",name:"مخابرات ولیعصر",category:"telecom",icon:"📡",x:80,y:48},
  {id:"telecom-north",name:"مرکز مخابرات شمال",category:"telecom",icon:"📡",x:66,y:12},
  {id:"telecom-south",name:"مرکز مخابرات جنوب",category:"telecom",icon:"📡",x:46,y:86},
  {id:"station-central",name:"ایستگاه قطار مرکزی",category:"station",icon:"🚉",x:18,y:45},
  {id:"station-north",name:"ایستگاه شمال",category:"station",icon:"🚉",x:53,y:8},
  {id:"station-south",name:"ایستگاه جنوب",category:"station",icon:"🚉",x:57,y:92},
  {id:"terminal-east",name:"پایانه شرق",category:"station",icon:"🚌",x:91,y:48},
  {id:"terminal-west",name:"پایانه غرب",category:"station",icon:"🚌",x:7,y:48},
  {id:"gas-central",name:"پمپ بنزین مرکزی",category:"gas",icon:"⛽",x:34,y:20},
  {id:"gas-pahlavi",name:"پمپ بنزین پهلوی",category:"gas",icon:"⛽",x:13,y:34},
  {id:"gas-valiasr",name:"پمپ بنزین ولیعصر",category:"gas",icon:"⛽",x:88,y:27},
  {id:"gas-east",name:"پمپ بنزین شرق",category:"gas",icon:"⛽",x:93,y:79},
  {id:"gas-south",name:"پمپ بنزین جنوب",category:"gas",icon:"⛽",x:69,y:89},
  {id:"park-old",name:"پارک قدیمی مهستان",category:"park",icon:"🌳",x:34,y:61},
  {id:"park-central",name:"پارک مرکزی",category:"park",icon:"🌳",x:58,y:62},
  {id:"park-pahlavi",name:"پارک پهلوی",category:"park",icon:"🌳",x:20,y:20},
  {id:"park-valiasr",name:"پارک ولیعصر",category:"park",icon:"🌳",x:83,y:19},
  {id:"park-river",name:"پارک کنار رودخانه",category:"park",icon:"🌳",x:74,y:76},
  {id:"park-east",name:"پارک شرقی",category:"park",icon:"🌳",x:91,y:62},
  {id:"factory-abandoned",name:"کارخانه متروکه",category:"factory",icon:"🏭",x:84,y:84},
  {id:"factory-north",name:"کارخانه شمال",category:"factory",icon:"🏭",x:71,y:8},
  {id:"warehouse-east",name:"انبار صنعتی شرق",category:"factory",icon:"🏭",x:94,y:39},
  {id:"warehouse-west",name:"انبار صنعتی غرب",category:"factory",icon:"🏭",x:6,y:82},
  {id:"factory-old",name:"کارخانه قدیمی",category:"factory",icon:"🏭",x:28,y:89},
  {id:"cityhall",name:"شهرداری مرکزی مهستان",category:"cityhall",icon:"🏛️",x:55,y:35},
  {id:"cityhall-north",name:"اداره منطقه شمال",category:"cityhall",icon:"🏛️",x:65,y:22},
  {id:"cityhall-south",name:"اداره منطقه جنوب",category:"cityhall",icon:"🏛️",x:61,y:81},
  {id:"registry",name:"اداره ثبت اسناد",category:"cityhall",icon:"📜",x:43,y:27},
  {id:"tax-office",name:"اداره مالیات",category:"cityhall",icon:"🏛️",x:69,y:69},
  {id:"newspaper",name:"روزنامه مهستان",category:"newspaper",icon:"📰",x:37,y:45},
  {id:"news-office",name:"دفتر خبرگزاری شهر",category:"newspaper",icon:"📰",x:63,y:48},
  {id:"radio",name:"رادیو مهستان",category:"newspaper",icon:"📻",x:72,y:66},
  {id:"bar-central",name:"بار مرکزی",category:"bar",icon:"🍸",x:58,y:44},
  {id:"cafe-pahlavi",name:"کافه پهلوی",category:"bar",icon:"☕",x:32,y:43},
  {id:"cafe-valiasr",name:"کافه ولیعصر",category:"bar",icon:"☕",x:75,y:62},
  {id:"cafe-river",name:"کافه رودخانه",category:"bar",icon:"☕",x:86,y:73},
  {id:"security-center",name:"مرکز امنیت شهر",category:"security",icon:"🛡️",x:62,y:32},
  {id:"cyber-unit",name:"واحد جرایم سایبری",category:"security",icon:"💻",x:67,y:28},
  {id:"cctv-center",name:"مرکز کنترل دوربین‌ها",category:"security",icon:"📹",x:59,y:69},
  {id:"data-center",name:"مرکز داده مهستان",category:"security",icon:"🖥️",x:80,y:68},
  {id:"school-central",name:"دبیرستان مرکزی",category:"public",icon:"🏫",x:35,y:36},
  {id:"university",name:"دانشگاه مهستان",category:"public",icon:"🎓",x:45,y:13},
  {id:"library",name:"کتابخانه مرکزی",category:"public",icon:"📚",x:52,y:17},
  {id:"museum",name:"موزه شهر",category:"public",icon:"🏛️",x:30,y:16},
  {id:"stadium",name:"ورزشگاه مهستان",category:"public",icon:"🏟️",x:15,y:76},
  {id:"market-old",name:"بازار قدیمی",category:"public",icon:"🏪",x:41,y:46},
  {id:"victim-house",name:"خانه قربانی",category:"case",icon:"🏠",x:33,y:54},
  {id:"crime-scene",name:"محل وقوع قتل",category:"case",icon:"🔎",x:52,y:53},
  {id:"mystery-house",name:"خانه متروکه",category:"case",icon:"🏚️",x:82,y:38},
  {id:"secret-garage",name:"گاراژ مخفی",category:"case",icon:"🚗",x:12,y:67},
  {id:"evidence-storage",name:"انبار مدارک",category:"case",icon:"📦",x:58,y:74},
  {id:"hidden-office",name:"دفتر مخفی",category:"case",icon:"🗄️",x:88,y:64},
  {id:"suspect-house-1",name:"خانه مظنون شماره ۱",category:"case",icon:"🏠",x:26,y:72},
  {id:"suspect-house-2",name:"خانه مظنون شماره ۲",category:"case",icon:"🏠",x:69,y:82},
  {id:"suspect-house-3",name:"خانه مظنون شماره ۳",category:"case",icon:"🏠",x:91,y:33},
  {id:"suspect-house-4",name:"خانه مظنون شماره ۴",category:"case",icon:"🏠",x:18,y:18},
];

        const categories = [
            ["all", "همه", "📍"],
            ["hospital", "بیمارستان", "🟢"],
            ["gold", "طلافروشی", "🔴"],
            ["mobile", "موبایل", "🟡"],
            ["police", "کلانتری", "🔵"],
            ["hotel", "هتل", "🟣"],
            ["restaurant", "رستوران", "🟠"],
            ["bank", "بانک", "🟤"],
            ["pharmacy", "داروخانه", "⚪"],
            ["store", "فروشگاه", "🔷"],
            ["telecom", "مخابرات", "🩷"]
        ];

        const renderMarkers = (list = locations) => {
            const layer = $("#mehestanMapMarkers");
            if (!layer) return;

            layer.innerHTML = list.map(location => `
                <button
                    class="mehestan-map-marker"
                    data-location-id="${location.id}"
                    style="left:${location.x}%;top:${location.y}%"
                    title="${location.name}"
                    type="button"
                >
                    <span>${location.icon}</span>
                    <small>${location.name}</small>
                </button>
            `).join("");

            $$(".mehestan-map-marker").forEach(marker => {
                marker.addEventListener("click", () => {
                    const location = locations.find(
                        item => item.id === marker.dataset.locationId
                    );

                    if (location) {
                        this.openLocation(location);
                    }
                });
            });
        };

        content.innerHTML = `
            <div class="mehestan-city">

                <div class="mehestan-city-topbar">

                    <div class="mehestan-city-title">
                        <span>🗺️</span>
                        <div>
                            <strong>شهر مهستان</strong>
                            <small>جمعیت تقریبی: ۳۰۰٬۰۰۰ نفر</small>
                        </div>
                    </div>

                    <div class="mehestan-city-search">
                        <span>🔎</span>
                        <input
                            id="mehestanLocationSearch"
                            type="search"
                            placeholder="جست‌وجوی مکان، خیابان یا نام..."
                            autocomplete="off"
                        />
                    </div>

                    <div class="mehestan-city-clock">
                        <span>🌙</span>
                        <strong id="mehestanGameClock">23:40</strong>
                    </div>
    <button id="mehestanFullscreen" class="mehestan-fullscreen-button" type="button" title="تمام صفحه">
      ⛶
      <span>تمام صفحه</span>
    </button>

                </div>

                <div class="mehestan-city-layout">

                    <aside class="mehestan-map-sidebar">

                        <div class="mehestan-sidebar-title">
                            📍 مکان‌های شهر
                        </div>

                        <div id="mehestanCategories" class="mehestan-categories">
                            ${categories.map(([id, name, icon]) => `
                                <button
                                    class="mehestan-category-button ${id === "all" ? "active" : ""}"
                                    data-category="${id}"
                                    type="button"
                                >
                                    <span>${icon}</span>
                                    ${name}
                                </button>
                            `).join("")}
                        </div>

                        <div class="mehestan-map-results-title">
                            نتایج جست‌وجو
                        </div>

                        <div id="mehestanLocationResults"
                             class="mehestan-location-results">
                        </div>

                    </aside>

                    <main class="mehestan-map-area">

                        <div id="mehestanMap"
                             class="mehestan-map"
                             tabindex="0">

                            <div class="mehestan-map-grid"></div>

                            <div class="mehestan-map-road road-1"></div>
                            <div class="mehestan-map-road road-2"></div>
                            <div class="mehestan-map-road road-3"></div>
                            <div class="mehestan-map-road road-4"></div>

                            <div class="mehestan-map-district district-a">
                                مرکز شهر
                            </div>

                            <div class="mehestan-map-district district-b">
                                منطقه پهلوی
                            </div>

                            <div class="mehestan-map-district district-c">
                                منطقه ولیعصر
                            </div>

                            <div id="mehestanMapMarkers"></div>

                            <div class="mehestan-map-controls">
                                <button id="mehestanZoomIn" type="button">＋</button>
                                <button id="mehestanZoomOut" type="button">−</button>
                                <button id="mehestanResetMap" type="button">⌖</button>
                            </div>

                            <div class="mehestan-map-info">
                                🕵️ حالت تحقیقات فعال
                            </div>

                        </div>

                    </main>

                </div>

                <div class="mehestan-floating-chat">
                    💬
                </div>

            </div>
        `;

        let activeCategory = "all";
        let zoom = 1;

        const renderResults = (list) => {
            const results = $("#mehestanLocationResults");

            if (!results) return;

            results.innerHTML = list.length
                ? list.map(location => `
                    <button
                        class="mehestan-location-result"
                        data-location-id="${location.id}"
                        type="button"
                    >
                        <span>${location.icon}</span>
                        <span>
                            <strong>${location.name}</strong>
                            <small>مهستان · قابل بررسی</small>
                        </span>
                    </button>
                `).join("")
                : `<div class="mehestan-no-results">مکانی پیدا نشد.</div>`;

            $$(".mehestan-location-result").forEach(button => {
                button.addEventListener("click", () => {
                    const location = locations.find(
                        item => item.id === button.dataset.locationId
                    );

                    if (location) {
                        this.openLocation(location);
                    }
                });
            });
        };

        
const mehestanFullscreenButton = $("#mehestanFullscreen");

const updateMehestanFullscreenButton = () => {
  if (!mehestanFullscreenButton) return;

  const active =
    document.fullscreenElement ||
    document.webkitFullscreenElement;

  mehestanFullscreenButton.querySelector("span").textContent =
    active ? "خروج از تمام صفحه" : "تمام صفحه";

  mehestanFullscreenButton.firstChild.textContent =
    active ? "✕ " : "⛶ ";
};

const enterMehestanFullscreen = async () => {
  const target = document.querySelector(".mehestan-city") || document.documentElement;

  try {
    if (target.requestFullscreen) {
      await target.requestFullscreen();
    } else if (target.webkitRequestFullscreen) {
      target.webkitRequestFullscreen();
    } else {
      document.body.classList.add("mehestan-force-fullscreen");
    }
  } catch (error) {
    document.body.classList.add("mehestan-force-fullscreen");
  }

  updateMehestanFullscreenButton();
};

const exitMehestanFullscreen = async () => {
  try {
    if (document.exitFullscreen) {
      await document.exitFullscreen();
    } else if (document.webkitExitFullscreen) {
      document.webkitExitFullscreen();
    }
  } catch (error) {}

  document.body.classList.remove("mehestan-force-fullscreen");
  updateMehestanFullscreenButton();
};

mehestanFullscreenButton?.addEventListener("click", async () => {
  const active =
    document.fullscreenElement ||
    document.webkitFullscreenElement;

  if (active) {
    await exitMehestanFullscreen();
  } else {
    await enterMehestanFullscreen();
  }
});

document.addEventListener("fullscreenchange", updateMehestanFullscreenButton);
document.addEventListener("webkitfullscreenchange", updateMehestanFullscreenButton);

updateMehestanFullscreenButton();

const filterLocations = () => {
            const query = ($("#mehestanLocationSearch")?.value || "")
                .trim()
                .toLowerCase();

            const filtered = locations.filter(location => {
                const categoryMatch =
                    activeCategory === "all" ||
                    location.category === activeCategory;

                const textMatch =
                    !query ||
                    location.name.toLowerCase().includes(query);

                return categoryMatch && textMatch;
            });

            renderMarkers(filtered);
            renderResults(filtered);
        };

        $$(".mehestan-category-button").forEach(button => {
            button.addEventListener("click", () => {
                $$(".mehestan-category-button")
                    .forEach(item => item.classList.remove("active"));

                button.classList.add("active");
                activeCategory = button.dataset.category;
                filterLocations();
            });
        });

        $("#mehestanLocationSearch")?.addEventListener(
            "input",
            filterLocations
        );

        $("#mehestanZoomIn")?.addEventListener("click", () => {
            zoom = Math.min(zoom + 0.15, 2);
            $("#mehestanMapMarkers").style.transform =
                `scale(${zoom})`;
        });

        $("#mehestanZoomOut")?.addEventListener("click", () => {
            zoom = Math.max(zoom - 0.15, 1);
            $("#mehestanMapMarkers").style.transform =
                `scale(${zoom})`;
        });

        $("#mehestanResetMap")?.addEventListener("click", () => {
            zoom = 1;
            $("#mehestanMapMarkers").style.transform = "scale(1)";
        });

        renderMarkers(locations);
        renderResults(locations);

        toast("نقشه شهر مهستان آماده شد.");
    },

    openLocation(location) {
        toast(`در حال ورود به ${location.name}...`);

        setTimeout(() => {
            toast(`📍 ${location.name} آماده بررسی است.`);
        }, 700);
    }

};

function closeGame() {
        document.body.classList.remove("mehestan-fullscreen-active");

        state.currentGame =
            null;

        hide($("#gameModal"));

        if (state.socket?.connected) {

            state.socket.emit(
                "game_leave",
                {
                    username:
                        state.currentUser?.username
                }
            );
        }
    }


    /* =====================================================
       ADMIN
    ===================================================== */

    function updateAdminButton() {

        const button =
            $("#adminButton");

        if (!button) {
            return;
        }

        if (
            state.currentUser?.role ===
            "admin"
        ) {

            show(button);

        } else {

            hide(button);
        }
    }


    function openAdminPanel() {

        if (
            state.currentUser?.role !==
            "admin"
        ) {

            toast(
                "فقط مدیر به این بخش دسترسی دارد."
            );

            return;
        }

        show($("#adminModal"));

        loadAdminDashboard();
    }


    function closeAdminPanel() {

        hide($("#adminModal"));
    }


    async function loadAdminDashboard() {

        try {

            const response =
                await fetch(
                    `${CONFIG.API_BASE}/api/game/admin/dashboard`
                );

            if (!response.ok) {
                return;
            }

            const data =
                await response.json();

            setText(
                $("#adminOnlineCount"),
                data.online_count ??
                    0
            );

            setText(
                $("#adminRoomCount"),
                data.active_rooms ??
                    0
            );

            setText(
                $("#adminGameCount"),
                data.games_running ??
                    0
            );

        } catch (error) {

            console.warn(
                "Admin dashboard unavailable:",
                error
            );
        }
    }


    function setupAdminTabs() {

        $$(".admin-tab")
            .forEach((button) => {

                button.addEventListener(
                    "click",
                    () => {

                        $$(".admin-tab")
                            .forEach((tab) => {
                                tab.classList.remove(
                                    "active"
                                );
                            });

                        button.classList.add(
                            "active"
                        );

                        const tab =
                            button.dataset.adminTab;

                        loadAdminTab(tab);
                    }
                );
            });
    }


    async function loadAdminTab(tab) {

        const content =
            $("#adminContent");

        if (!content) {
            return;
        }

        if (tab === "dashboard") {

            await loadAdminDashboard();
            return;
        }

        content.innerHTML = "";

        const box =
            document.createElement("div");

        box.className =
            "empty-activity";

        const labels = {
            players: "👥 مدیریت بازیکنان",
            rooms: "🚪 مدیریت اتاق‌ها",
            scenarios: "🧩 مدیریت سناریوها",
            settings: "⚙️ تنظیمات بازی"
        };

        box.textContent =
            `${labels[tab] || "بخش مدیریت"} آماده است.`;

        content.appendChild(box);
    }


    /* =====================================================
       ACTIVITY
    ===================================================== */

    function addActivity(
        icon,
        title,
        description
    ) {

        state.activities.unshift({
            icon,
            title,
            description,
            time: new Date()
        });

        state.activities =
            state.activities.slice(
                0,
                20
            );

        renderActivities();
    }


    function renderActivities() {

        const list =
            $("#activityList");

        if (!list) {
            return;
        }

        if (!state.activities.length) {

            list.innerHTML =
                `<div class="empty-activity">
                    هنوز فعالیتی ثبت نشده.
                </div>`;

            return;
        }

        list.innerHTML = "";

        state.activities.forEach(
            (activity) => {

                const item =
                    document.createElement("div");

                item.className =
                    "activity-item";

                const icon =
                    document.createElement("div");

                icon.className =
                    "activity-icon";

                icon.textContent =
                    activity.icon;

                const text =
                    document.createElement("div");

                text.className =
                    "activity-text";

                const title =
                    document.createElement("strong");

                title.textContent =
                    activity.title;

                const description =
                    document.createElement("small");

                description.textContent =
                    activity.description;

                text.appendChild(title);
                text.appendChild(description);

                item.appendChild(icon);
                item.appendChild(text);

                list.appendChild(item);
            }
        );
    }


    /* =====================================================
       EVENT SETUP
    ===================================================== */

    function setupEvents() {

        /* Password */

        $("#cancelPassword")
            ?.addEventListener(
                "click",
                closeAdminPassword
            );


        $("#confirmPassword")
            ?.addEventListener(
                "click",
                async () => {

                    const username =
                        state.pendingAdminLogin;

                    const password =
                        $("#passwordInput")
                            ?.value
                            .trim();

                    if (!username) {
                        return;
                    }

                    await loginAs(
                        username,
                        password
                    );
                }
            );


        $("#passwordInput")
            ?.addEventListener(
                "keydown",
                (event) => {

                    if (
                        event.key ===
                        "Enter"
                    ) {

                        $("#confirmPassword")
                            ?.click();
                    }
                }
            );


        /* Profile */

        $("#profileButton")
            ?.addEventListener(
                "click",
                openProfile
            );


        $("#closeProfile")
            ?.addEventListener(
                "click",
                () => {
                    hide($("#profileModal"));
                }
            );


        $("#changeAvatarButton")
            ?.addEventListener(
                "click",
                () => {
                    $("#profileAvatarInput")
                        ?.click();
                }
            );


        $("#profileAvatarInput")
            ?.addEventListener(
                "change",
                (event) => {

                    const file =
                        event.target.files?.[0];

                    if (file) {
                        uploadProfileAvatar(
                            file
                        );
                    }

                    event.target.value =
                        "";
                }
            );


        $("#saveProfileButton")
            ?.addEventListener(
                "click",
                saveProfile
            );


        /* Chat */

        $("#chatButton")
            ?.addEventListener(
                "click",
                openChat
            );


        $("#floatingChatButton")
            ?.addEventListener(
                "click",
                openChat
            );


        $("#closeChat")
            ?.addEventListener(
                "click",
                closeChat
            );


        $("#sendChatButton")
            ?.addEventListener(
                "click",
                sendChatMessage
            );


        $("#chatInput")
            ?.addEventListener(
                "keydown",
                (event) => {

                    if (
                        event.key ===
                        "Enter" &&
                        !event.shiftKey
                    ) {

                        event.preventDefault();

                        sendChatMessage();
                    }
                }
            );


        $("#chatImageButton")
            ?.addEventListener(
                "click",
                () => {
                    $("#chatImageInput")
                        ?.click();
                }
            );


        $("#chatImageInput")
            ?.addEventListener(
                "change",
                (event) => {

                    const file =
                        event.target.files?.[0];

                    if (file) {
                        uploadChatImage(
                            file
                        );
                    }

                    event.target.value =
                        "";
                }
            );


        /* Games */
        $$(".play-button").forEach((button) => {
            button.addEventListener("click", () => {
                const game = button.dataset.game;

                if (game === "spy") {
                    SpyGameUI.open();
                } else if (game === "mehestan") {
                    MehestanGameUI.open();
                } else if (typeof openGame === "function") {
                    openGame(game);
                } else {
                    toast("این بازی هنوز آماده نشده است.");
                }
            });
        });


        $("#closeGame")
            ?.addEventListener(
                "click",
                closeGame
            );


        /* Admin */

        $("#adminButton")
            ?.addEventListener(
                "click",
                openAdminPanel
            );


        $("#closeAdmin")
            ?.addEventListener(
                "click",
                closeAdminPanel
            );


        setupAdminTabs();


        /* Menu */

        $("#menuButton")
            ?.addEventListener(
                "click",
                () => {

                    if (
                        state.currentUser?.role ===
                        "admin"
                    ) {

                        openAdminPanel();

                    } else {

                        toast(
                            "پروفایل یا چت رو از بالای صفحه باز کن."
                        );
                    }
                }
            );


        /* Logout with double click on profile */

        $("#profileButton")
            ?.addEventListener(
                "dblclick",
                () => {

                    const ok =
                        window.confirm(
                            "از حساب خارج بشی؟"
                        );

                    if (ok) {
                        logout();
                    }
                }
            );


        /* Modal overlays */

        $$(".modal-overlay")
            .forEach((overlay) => {

                overlay.addEventListener(
                    "click",
                    () => {

                        const modal =
                            overlay.closest(
                                ".modal"
                            );

                        if (!modal) {
                            return;
                        }

                        if (
                            modal.id ===
                            "passwordModal"
                        ) {

                            closeAdminPassword();

                        } else if (
                            modal.id ===
                            "profileModal"
                        ) {

                            hide(modal);

                        } else if (
                            modal.id ===
                            "gameModal"
                        ) {

                            closeGame();

                        } else if (
                            modal.id ===
                            "adminModal"
                        ) {

                            closeAdminPanel();
                        }
                    }
                );
            });
    }


    /* =====================================================
       URL
    ===================================================== */

    function absoluteUrl(url) {

        if (!url) {
            return "";
        }

        if (
            url.startsWith("http://") ||
            url.startsWith("https://") ||
            url.startsWith("data:")
        ) {
            return url;
        }

        if (url.startsWith("/")) {
            return CONFIG.API_BASE + url;
        }

        return url;
    }


    /* =====================================================
       AUTO LOGIN
    ===================================================== */

    async function restoreSession() {

        const saved =
            getSavedUser();

        if (!saved) {
            return;
        }

        /*
         * برای مهدی، چون رمز نباید داخل LocalStorage
         * ذخیره شود، ورود خودکار انجام نمی‌دهیم.
         */

        if (saved.role === "admin") {
            return;
        }

        state.currentUser = {
            ...saved
        };

        await loadProfile();

        showMainScreen();

        connectSocket();
    }


    /* =====================================================
       INITIALIZATION
    ===================================================== */

    async function init() {
        console.log("GAME_ROOM_INIT_STARTED");

        if (state.initialized) {
            return;
        }

        state.initialized = true;
        console.log("GAME_ROOM_BEFORE_LOGIN_BUTTONS");

        setupLoginButtons();
        console.log("GAME_ROOM_AFTER_LOGIN_BUTTONS");
        setupEvents();

        renderActivities();

        await loadPlayers();

        startHeartbeat();

        await restoreSession();
    }


    /* =====================================================
       START
    ===================================================== */

    if (
        document.readyState ===
        "loading"
    ) {

        document.addEventListener(
            "DOMContentLoaded",
            init,
            {
                once: true
            }
        );

    } else {

        init();
    }

})();

/* ============================================================
   ============================================================ */



if (typeof socket !== "undefined") {
    

    

    

    

    

    

    

    

    

    
}
