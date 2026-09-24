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
            "game_join_error",
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



    


function openSpyLobby() {
    if (!state.currentUser?.username) {
        toast("ابتدا وارد حساب کاربری شو.");
        return;
    }

    setupSpySocketListeners();
    SpyGameUI.open("spy-main-room");
}

function openGame(gameType, serverData = null) {
    const game = CONFIG.GAMES[gameType];
    if (!game) {
        toast("این بازی پیدا نشد.");
        return;
    }

    state.currentGame = {
        type: gameType,
        data: serverData,
        gameId: serverData?.game_id || serverData?.id || null,
        spyRole: null,
        spyState: null,
        spyResult: null
    };

    const content = $("#gameContent");
    if (!content) return;

    content.innerHTML = "";

    if (gameType === "spy") {
        SpyGameUI.open(state.currentGame.gameId || "spy-main-room");
    } else {
        const header = document.createElement("div");
        header.style.textAlign = "center";
        header.style.padding = "30px 10px 20px";

        const icon = document.createElement("div");
        icon.style.fontSize = "54px";
        icon.textContent = game.emoji;

        const title = document.createElement("h2");
        title.textContent = game.title;
        title.style.marginTop = "12px";

        const description = document.createElement("p");
        description.style.marginTop = "8px";
        description.style.color = "var(--muted)";
        description.style.fontSize = "11px";
        description.textContent = getGameDescription(gameType);

        header.appendChild(icon);
        header.appendChild(title);
        header.appendChild(description);
        content.appendChild(header);

        const status = document.createElement("div");
        status.className = "system-message";
        status.textContent = "در حال اتصال به اتاق بازی...";
        content.appendChild(status);
    }

    show($("#gameModal"));

    if (state.socket?.connected) {
        state.socket.emit("game_open", {
            username: state.currentUser?.username,
            game_type: gameType,
            game_id: state.currentGame.gameId
        });
    }
}












function getGameDescription(gameType) {

        switch (gameType) {

            case "spy":
                return "سرنخ بده، شک کن و جاسوس رو پیدا کن!";

            case "mystery":
                return "با هم سرنخ‌ها رو بررسی کنید و پرونده رو حل کنید.";

            case "forbidden":
                return "کلمه رو توضیح بده، بدون اینکه کلمات ممنوعه رو بگی.";

            default:
                return "بازی آماده می‌شود.";
        }
    }


    function updateCurrentGame(data) {

        if (
            !state.currentGame ||
            !data
        ) {
            return;
        }

        state.currentGame.data =
            data;

        /*
         * موتور کامل هر سه بازی در Backend
         * کنترل خواهد شد.
         *
         * این قسمت نقطه ورود UI بازی است.
         */

        renderGameState(data);
    }


    function renderGameState(data) {

        const content =
            $("#gameContent");

        if (!content) {
            return;
        }

        if (!data.game_state) {
            return;
        }

        const stateData =
            data.game_state;

        const info =
            document.createElement("div");

        info.className =
            "system-message";

        if (stateData.phase) {

            info.textContent =
                `مرحله بازی: ${stateData.phase}`;

        } else {

            info.textContent =
                "وضعیت بازی به‌روزرسانی شد.";
        }

        content.appendChild(info);
    }


    


    


    


    


    
/* ============================================================
   SPY GAME — SINGLE UNIFIED FRONTEND
   ============================================================ */

const SpyGameUI = {
    gameId: null,
    selectedVote: null,
    replyTo: null,
    guessOpen: false,
    lastPhase: null,

    open(gameId) {
        this.gameId = gameId || "spy-main-room";
        this.selectedVote = null;
        this.replyTo = null;
        this.guessOpen = false;
        this.lastPhase = null;

        state.currentGame = {
            type: "spy",
            gameId: this.gameId,
            data: null,
            spyRole: null,
            spyState: null,
            spyResult: null
        };

        const content = $("#gameContent");
        if (!content) return;

        content.innerHTML = `
            <div class="spy-v2">
                <div class="spy-v2-head">
                    <div>
                        <div class="spy-v2-kicker">GAME ROOM • SPY</div>
                        <h2>🕵️ جاسوس</h2>
                        <p>بحث کن، حدس بزن، رأی بده.</p>
                    </div>
                    <div class="spy-v2-live">
                        <span></span>
                        آنلاین
                    </div>
                </div>

                <div id="spyV2Lobby" class="spy-v2-panel"></div>
                <div id="spyV2Role" class="spy-v2-panel"></div>
                <div id="spyV2Status" class="spy-v2-panel"></div>
                <div id="spyV2Players" class="spy-v2-panel"></div>
                <div id="spyV2Voting" class="spy-v2-panel"></div>
                <div id="spyV2Guess" class="spy-v2-panel"></div>
                <div id="spyV2Result" class="spy-v2-panel"></div>

                <div class="spy-v2-chat spy-v2-panel">
                    <div class="spy-v2-chat-head">
                        <div>
                            <strong>💬 چت بازی</strong>
                            <small>گفت‌وگو فقط بین بازیکنان همین بازی</small>
                        </div>
                        <button type="button" id="spyV2NewMessage">پیام جدید</button>
                    </div>

                    <div id="spyV2Messages" class="spy-v2-messages"></div>

                    <div id="spyV2Reply" class="spy-v2-reply" hidden>
                        <div>
                            <small>در حال پاسخ به</small>
                            <strong id="spyV2ReplyText"></strong>
                        </div>
                        <button type="button" id="spyV2CancelReply">×</button>
                    </div>

                    <div class="spy-v2-input">
                        <input
                            id="spyV2Input"
                            type="text"
                            maxlength="500"
                            autocomplete="off"
                            placeholder="پیامت رو بنویس..."
                        >
                        <button type="button" id="spyV2Send">ارسال</button>
                    </div>
                </div>
            </div>
        `;

        this.bind();
        this.renderLobby({
            players: [],
            count: 0,
            min_players: 3,
            max_players: 5,
            phase: "lobby"
        });

        if (state.socket?.connected) {
            state.socket.emit("spy_create", {
                game_id: this.gameId,
                username: state.currentUser.username
            });

            state.socket.emit("spy_join", {
                game_id: this.gameId,
                username: state.currentUser.username
            });

            state.socket.emit("spy_join_chat", {
                game_id: this.gameId,
                username: state.currentUser.username
            });

            state.socket.emit("spy_chat_history", {
                game_id: this.gameId
            });

            state.socket.emit("spy_state", {
                game_id: this.gameId,
                username: state.currentUser.username
            });
        } else {
            this.setStatus("اتصال به سرور برقرار نیست.");
        }
    },

    bind() {
        const input = $("#spyV2Input");
        const send = $("#spyV2Send");
        const cancel = $("#spyV2CancelReply");
        const newMessage = $("#spyV2NewMessage");

        send?.addEventListener("click", () => this.sendChat());

        input?.addEventListener("keydown", (event) => {
            if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                this.sendChat();
            }
        });

        cancel?.addEventListener("click", () => {
            this.replyTo = null;
            this.renderReply();
        });

        newMessage?.addEventListener("click", () => {
            const box = $("#spyV2Messages");
            if (box) {
                box.scrollTop = box.scrollHeight;
                box.classList.remove("has-new");
            }
        });
    },

    setStatus(text, timer = null) {
        const box = $("#spyV2Status");
        if (!box) return;

        box.innerHTML = `
            <div class="spy-v2-status-row">
                <span>${escapeHtml(text || "")}</span>
                ${timer !== null ? `<strong>${escapeHtml(String(timer))}</strong>` : ""}
            </div>
        `;
    },

    renderLobby(data) {
        const box = $("#spyV2Lobby");
        if (!box) return;

        const players = Array.isArray(data?.players)
            ? data.players
            : [];

        const count = Number(data?.count ?? players.length);
        const min = Number(data?.min_players ?? 3);
        const max = Number(data?.max_players ?? 5);

        const isAdmin =
            state.currentUser?.role === "admin";

        box.innerHTML = `
            <div class="spy-v2-panel-title">
                <div>
                    <small>لابی بازی</small>
                    <h3>بازیکنان</h3>
                </div>
                <span class="spy-v2-count">${count}/${max}</span>
            </div>

            <div class="spy-v2-players">
                ${
                    players.length
                        ? players.map((player) => `
                            <div class="spy-v2-player">
                                <div class="spy-v2-avatar">
                                    ${
                                        player.avatar_url
                                            ? `<img src="${escapeHtml(absoluteUrl(player.avatar_url))}" alt="">`
                                            : escapeHtml(player.emoji || "🎮")
                                    }
                                </div>
                                <div class="spy-v2-player-name">
                                    <strong>${escapeHtml(player.display_name || player.username || "بازیکن")}</strong>
                                    ${
                                        player.username === state.currentUser?.username
                                            ? `<small>شما</small>`
                                            : ""
                                    }
                                </div>
                            </div>
                        `).join("")
                        : `<div class="spy-v2-empty">هنوز بازیکنی وارد نشده.</div>`
                }
            </div>

            <div class="spy-v2-lobby-actions">
                ${
                    isAdmin
                        ? `
                            <label class="spy-v2-field">
                                <span>زمان مرحله بحث</span>
                                <div class="spy-v2-time-row">
                                    <input id="spyV2Discussion" type="number" min="10" max="1800" value="120">
                                    <span>ثانیه</span>
                                </div>
                            </label>

                            <button
                                type="button"
                                id="spyV2Start"
                                class="spy-v2-primary"
                                ${count < min ? "disabled" : ""}
                            >
                                ${
                                    count < min
                                        ? `🔒 حداقل ${min} بازیکن`
                                        : "🚀 شروع بازی"
                                }
                            </button>
                        `
                        : `
                            <div class="spy-v2-waiting">
                                ⏳ منتظر شروع بازی توسط مدیر...
                            </div>
                        `
                }
            </div>
        `;

        $("#spyV2Start")?.addEventListener("click", () => {
            let debug = document.getElementById("spyStartDebug");

            if (!debug) {
                debug = document.createElement("div");
                debug.id = "spyStartDebug";
                debug.style.cssText =
                    "position:fixed;z-index:999999;top:10px;left:10px;right:10px;" +
                    "padding:14px;background:#111;color:#fff;border:2px solid #00ff88;" +
                    "border-radius:12px;font:14px monospace;direction:ltr;" +
                    "white-space:pre-wrap;word-break:break-word;";
                document.body.appendChild(debug);
            }

            debug.textContent =
                "SPY START CLICK DETECTED\n" +
                "socket exists: " + !!state.socket + "\n" +
                "socket connected: " + !!state.socket?.connected + "\n" +
                "game id: " + String(this.gameId) + "\n" +
                "username: " + String(state.currentUser?.username || "");

            const input = $("#spyV2Discussion");
            let seconds = Number(input?.value || 120);

            if (!Number.isFinite(seconds)) seconds = 120;

            seconds = Math.max(
                10,
                Math.min(1800, Math.floor(seconds))
            );

            if (!state.socket?.connected) {
                debug.textContent +=
                    "\n\n❌ SOCKET NOT CONNECTED";
                debug.style.borderColor = "#ff4444";
                toast("اتصال به سرور برقرار نیست.");
                return;
            }

            debug.textContent +=
                "\n\n📤 EMITTING spy_start...";

            state.socket.emit("spy_start", {
                game_id: this.gameId,
                username: state.currentUser.username,
                discussion_seconds: seconds
            });

            setTimeout(() => {
                debug.textContent +=
                    "\n\n⏱️ 1 second after emit..." +
                    "\nIf nothing else appears, server response was not received.";
            }, 1000);
        });

    },
    renderState(data) {
        if (!data) return;

        state.currentGame.spyState = data;

        const phase = data.phase || "lobby";
        const remaining =
            Number(data.remaining_seconds ?? data.timer ?? 0);

        this.renderPlayers(data);

        if (phase === "lobby") {
            this.renderLobby(data);
            return;
        }

        const role = data.my_role || data.role;

        if (role) {
            state.currentGame.spyRole = {
                role,
                word: data.word || data.secret_word || null
            };
            this.renderRole(state.currentGame.spyRole);
        }

        if (phase === "discussion") {
            this.setStatus("💬 مرحله بحث", remaining);
            this.renderGuessButton(role);
            this.hideVoting();
            return;
        }

        if (phase === "voting") {
            this.setStatus("🗳️ رأی‌گیری", remaining);
            this.renderVoting(data);
            return;
        }

        if (phase === "finished") {
            this.hideVoting();
            this.hideGuess();
            this.renderResult(data.result || state.currentGame.spyResult || data);
        }
    },

    renderRole(roleData) {
        const box = $("#spyV2Role");
        if (!box || !roleData) return;

        const isSpy = roleData.role === "spy";

        box.innerHTML = `
            <div class="spy-v2-role ${isSpy ? "danger" : "citizen"}">
                <div class="spy-v2-role-icon">${isSpy ? "🕵️" : "🟢"}</div>
                <div>
                    <small>نقش شما</small>
                    <h3>${isSpy ? "شما جاسوس هستید" : "شما شهروند هستید"}</h3>
                    <p>
                        ${
                            isSpy
                                ? "کلمه مخفی را نمی‌دانی. از بحث استفاده کن تا شناسایی نشوی."
                                : `کلمه مخفی: <strong>${escapeHtml(roleData.word || "—")}</strong>`
                        }
                    </p>
                </div>
            </div>
        `;
    },

    renderPlayers(data) {
        const box = $("#spyV2Players");
        if (!box) return;

        const players = Array.isArray(data?.players)
            ? data.players
            : [];

        if (!players.length) {
            box.innerHTML = "";
            return;
        }

        box.innerHTML = `
            <div class="spy-v2-panel-title">
                <div>
                    <small>بازیکنان بازی</small>
                    <h3>بازیکنان حاضر</h3>
                </div>
            </div>

            <div class="spy-v2-compact-players">
                ${players.map((username) => {
                    const player =
                        state.players?.[username] || {};

                    const name =
                        player.display_name ||
                        CONFIG.PLAYERS?.[username]?.name ||
                        username;

                    return `
                        <div class="spy-v2-compact-player">
                            <span>🎮</span>
                            <strong>${escapeHtml(name)}</strong>
                            ${
                                username === state.currentUser?.username
                                    ? `<small>شما</small>`
                                    : ""
                            }
                        </div>
                    `;
                }).join("")}
            </div>
        `;
    },

    renderGuessButton(role) {
        const box = $("#spyV2Guess");
        if (!box) return;

        if (role !== "spy") {
            box.innerHTML = "";
            return;
        }

        box.innerHTML = `
            <div class="spy-v2-action-card">
                <div>
                    <small>حرکت ویژه جاسوس</small>
                    <h3>فکر می‌کنی کلمه رو فهمیدی؟</h3>
                    <p>می‌تونی حدست رو ثبت کنی؛ چت تا قبل از ثبت حدس باز می‌مونه.</p>
                </div>
                <button type="button" id="spyV2GuessOpen" class="spy-v2-secondary">
                    🧠 کلمه رو فهمیدم
                </button>
            </div>
        `;

        $("#spyV2GuessOpen")?.addEventListener("click", () => {
            this.openGuess();
        });
    },

    openGuess() {
        const box = $("#spyV2Guess");
        if (!box) return;

        this.guessOpen = true;

        box.innerHTML = `
            <div class="spy-v2-action-card">
                <div>
                    <small>حدس جاسوس</small>
                    <h3>کلمه رو وارد کن</h3>
                    <p>بعد از ثبت، نتیجه نهایی می‌شه.</p>
                </div>

                <div class="spy-v2-guess-form">
                    <input
                        id="spyV2GuessInput"
                        type="text"
                        maxlength="100"
                        placeholder="حدس تو..."
                        autocomplete="off"
                    >
                    <div>
                        <button type="button" id="spyV2GuessCancel" class="spy-v2-muted">
                            برگشت به چت
                        </button>
                        <button type="button" id="spyV2GuessSubmit" class="spy-v2-primary">
                            ثبت حدس
                        </button>
                    </div>
                </div>
            </div>
        `;

        $("#spyV2GuessCancel")?.addEventListener("click", () => {
            this.guessOpen = false;
            const role = state.currentGame?.spyRole?.role;
            this.renderGuessButton(role);
        });

        $("#spyV2GuessSubmit")?.addEventListener("click", () => {
            const input = $("#spyV2GuessInput");
            const guess = input?.value.trim();

            if (!guess) {
                toast("اول حدست رو بنویس.");
                return;
            }

            if (!state.socket?.connected) {
                toast("اتصال به سرور برقرار نیست.");
                return;
            }

            state.socket.emit("spy_guess", {
                game_id: this.gameId,
                username: state.currentUser.username,
                guess
            });
        });

        $("#spyV2GuessInput")?.focus();
    },

    hideGuess() {
        const box = $("#spyV2Guess");
        if (box) box.innerHTML = "";
    },

    renderVoting(data) {
        const box = $("#spyV2Voting");
        if (!box) return;

        const players = Array.isArray(data?.players)
            ? data.players
            : [];

        const me = state.currentUser?.username;

        box.innerHTML = `
            <div class="spy-v2-vote-card">
                <div class="spy-v2-panel-title">
                    <div>
                        <small>مرحله نهایی</small>
                        <h3>🗳️ جاسوس کیه؟</h3>
                    </div>
                    <span>۱۰ ثانیه</span>
                </div>

                <p class="spy-v2-vote-note">
                    رأی دیگران دیده نمی‌شود. می‌تونی تا پایان زمان، رأی خودت رو تغییر بدی.
                </p>

                <div class="spy-v2-votes">
                    ${
                        players
                            .filter((username) => username !== me)
                            .map((username) => {
                                const player =
                                    state.players?.[username] || {};

                                const name =
                                    player.display_name ||
                                    CONFIG.PLAYERS?.[username]?.name ||
                                    username;

                                const selected =
                                    this.selectedVote === username;

                                return `
                                    <button
                                        type="button"
                                        class="spy-v2-vote ${selected ? "selected" : ""}"
                                        data-vote-target="${escapeHtml(username)}"
                                    >
                                        <span>🎯</span>
                                        <strong>${escapeHtml(name)}</strong>
                                        ${selected ? "<small>رأی فعلی شما</small>" : ""}
                                    </button>
                                `;
                            })
                            .join("")
                    }
                </div>

                <div id="spyV2VoteStatus" class="spy-v2-vote-status">
                    ${
                        this.selectedVote
                            ? "✅ رأی ثبت شده — در صورت نیاز تغییرش بده."
                            : "یک نفر را انتخاب کن."
                    }
                </div>
            </div>
        `;

        box.querySelectorAll("[data-vote-target]").forEach((button) => {
            button.addEventListener("click", () => {
                const target = button.dataset.voteTarget;

                if (!target || !state.socket?.connected) {
                    return;
                }

                this.selectedVote = target;

                state.socket.emit("spy_vote", {
                    game_id: this.gameId,
                    username: state.currentUser.username,
                    target
                });

                this.renderVoting(data);
            });
        });
    },

    hideVoting() {
        const box = $("#spyV2Voting");
        if (box) box.innerHTML = "";
    },

    renderResult(data) {
        const box = $("#spyV2Result");
        if (!box || !data) return;

        state.currentGame.spyResult = data;

        const citizensWon =
            data.winner === "citizens";

        const votes = data.votes || data.vote_counts || {};

        box.innerHTML = `
            <div class="spy-v2-result ${citizensWon ? "citizens" : "spy"}">
                <div class="spy-v2-result-icon">
                    ${citizensWon ? "🎉" : "🕵️"}
                </div>

                <small>نتیجه نهایی</small>

                <h2>
                    ${
                        citizensWon
                            ? "شهروندها برنده شدند"
                            : "جاسوس برنده شد"
                    }
                </h2>

                <div class="spy-v2-result-grid">
                    <div>
                        <small>جاسوس</small>
                        <strong>${escapeHtml(data.spy || "نامشخص")}</strong>
                    </div>

                    <div>
                        <small>کلمه</small>
                        <strong>${escapeHtml(data.common_word || data.word || "—")}</strong>
                    </div>
                </div>

                ${
                    Object.keys(votes).length
                        ? `
                            <div class="spy-v2-final-votes">
                                <small>تعداد رأی‌ها</small>
                                ${Object.entries(votes).map(([username, count]) => `
                                    <div>
                                        <span>${escapeHtml(username)}</span>
                                        <strong>${escapeHtml(String(count))}</strong>
                                    </div>
                                `).join("")}
                            </div>
                        `
                        : ""
                }
            </div>
        `;
    },

    sendChat() {
        const input = $("#spyV2Input");

        if (!input || !state.currentUser) return;

        const message = input.value.trim();

        if (!message) return;

        if (!state.socket?.connected) {
            toast("اتصال به سرور برقرار نیست.");
            return;
        }

        state.socket.emit("spy_chat", {
            game_id: this.gameId,
            username: state.currentUser.username,
            message,
            reply_to: this.replyTo?.id || null
        });

        input.value = "";
        this.replyTo = null;
        this.renderReply();
        input.focus();
    },

    renderReply() {
        const box = $("#spyV2Reply");
        const text = $("#spyV2ReplyText");

        if (!box || !text) return;

        if (!this.replyTo) {
            box.hidden = true;
            return;
        }

        text.textContent =
            this.replyTo.message ||
            this.replyTo.display_name ||
            "پیام";

        box.hidden = false;
    },

    renderChatHistory(messages) {
        const box = $("#spyV2Messages");
        if (!box) return;

        box.innerHTML = "";

        if (!Array.isArray(messages) || !messages.length) {
            box.innerHTML = `
                <div class="spy-v2-chat-empty">
                    هنوز پیامی نیست. اولین پیام رو بفرست 👋
                </div>
            `;
            return;
        }

        messages.forEach((message) => {
            this.renderChatMessage(message, false);
        });

        box.scrollTop = box.scrollHeight;
    },

    renderChatMessage(data, autoScroll = true) {
        const box = $("#spyV2Messages");

        if (!box || !data) return;

        const mine =
            data.username === state.currentUser?.username;

        const sender =
            data.display_name ||
            state.players?.[data.username]?.display_name ||
            CONFIG.PLAYERS?.[data.username]?.name ||
            data.username ||
            "بازیکن";

        const item = document.createElement("div");

        item.className =
            `spy-v2-message ${mine ? "mine" : "other"}`;

        item.dataset.messageId =
            data.id || "";

        const reply =
            data.reply_to
                ? `
                    <button
                        type="button"
                        class="spy-v2-message-reply"
                        data-jump-reply="${escapeHtml(String(data.reply_to))}"
                    >
                        ↩ پاسخ به پیام
                    </button>
                `
                : "";

        const body =
            data.is_image
                ? "🖼️ تصویر"
                : data.message || "";

        item.innerHTML = `
            ${reply}

            <div class="spy-v2-message-head">
                <strong>${escapeHtml(mine ? "شما" : sender)}</strong>
            </div>

            <div class="spy-v2-message-body">
                ${escapeHtml(body)}
            </div>

            <div class="spy-v2-message-actions">
                <button
                    type="button"
                    data-reply-message
                >
                    پاسخ
                </button>
            </div>
        `;

        item.querySelector("[data-reply-message]")?.addEventListener(
            "click",
            () => {
                this.replyTo = {
                    id: data.id,
                    message: data.message || "پیام"
                };

                this.renderReply();
                $("#spyV2Input")?.focus();
            }
        );

        item.querySelector("[data-jump-reply]")?.addEventListener(
            "click",
            () => {
                const target =
                    item.querySelector("[data-jump-reply]")?.dataset.jumpReply;

                const original =
                    box.querySelector(`[data-message-id="${CSS.escape(target || "")}"]`);

                original?.scrollIntoView({
                    behavior: "smooth",
                    block: "center"
                });

                original?.classList.add("reply-highlight");

                setTimeout(() => {
                    original?.classList.remove("reply-highlight");
                }, 1000);
            }
        );

        box.appendChild(item);

        if (autoScroll) {
            box.scrollTop = box.scrollHeight;
        }
    }
};

/* Spy socket events */

if (typeof socket !== "undefined") {
    // kept empty intentionally; main socket is state.socket
}

function setupSpySocketListeners() {
    if (!state.socket || state.spySocketListenersReady) {
        return;
    }

    state.spySocketListenersReady = true;

    state.socket.on("spy_created", (data) => {
        if (!data) return;

        if (data.game_id) {
            SpyGameUI.gameId = data.game_id;
            state.currentGame.gameId = data.game_id;
        }

        SpyGameUI.renderState(data);
    });

    state.socket.on("spy_joined", (data) => {
        if (!data) return;

        if (data.game_id) {
            SpyGameUI.gameId = data.game_id;
            state.currentGame.gameId = data.game_id;
        }

        SpyGameUI.renderState(data);
    });

    state.socket.on("spy_state", (data) => {
        if (!data) return;
        SpyGameUI.renderState(data);
    });

    state.socket.on("spy_started", (data) => {
        if (!data) return;

        SpyGameUI.renderState(data);

        state.socket.emit("spy_state", {
            game_id: SpyGameUI.gameId,
            username: state.currentUser?.username
        });
    });

    state.socket.on("spy_tick", (data) => {
        if (!data) return;

        if (data.phase === "discussion") {
            SpyGameUI.setStatus(
                "💬 مرحله بحث",
                Number(data.remaining_seconds ?? 0)
            );
        } else if (data.phase === "voting") {
            SpyGameUI.setStatus(
                "🗳️ رأی‌گیری",
                Number(data.remaining_seconds ?? 0)
            );

            SpyGameUI.renderVoting(data);
        }

        if (data.phase === "finished") {
            SpyGameUI.renderResult(
                data.result || data
            );
        }
    });

    state.socket.on("spy_voting_started", (data) => {
        if (!data) return;

        SpyGameUI.selectedVote = null;
        SpyGameUI.renderState({
            ...data,
            phase: "voting"
        });
    });

    state.socket.on("spy_finished", (data) => {
        if (!data) return;

        SpyGameUI.renderResult(data);
        SpyGameUI.hideVoting();
        SpyGameUI.hideGuess();
        SpyGameUI.setStatus("🏁 بازی تمام شد");
    });

    state.socket.on("spy_chat_history", (data) => {
        const messages =
            Array.isArray(data)
                ? data
                : data?.messages || [];

        SpyGameUI.renderChatHistory(messages);
    });

    state.socket.on("spy_chat", (data) => {
        if (!data) return;

        SpyGameUI.renderChatMessage(data);

        const box = $("#spyV2Messages");

        if (box) {
            const nearBottom =
                box.scrollHeight -
                box.scrollTop -
                box.clientHeight < 100;

            if (!nearBottom) {
                box.classList.add("has-new");
                show($("#spyV2NewMessage"));
            }
        }
    });

    state.socket.on("spy_vote", (data) => {
        if (!data) return;

        if (
            data.username ===
            state.currentUser?.username
        ) {
            toast("✅ رأی ثبت شد.");
        }
    });

    state.socket.on("spy_error", (data) => {
        toast(
            data?.message ||
            data?.error ||
            "عملیات جاسوس انجام نشد."
        );
    });
}

setupSpySocketListeners();


function closeGame() {

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

        $$(".play-button")
            .forEach((button) => {

                button.addEventListener(
                    "click",
                    () => {

                        const game =
                            button.dataset.game;

                        if (game === "spy") {

                            openSpyLobby();

                        } else {

                            openGame(
                                game
                            );
                        }
                    }
                );
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
