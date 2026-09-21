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
        adminToken: null,

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

                const adminLogin = await verifyAdminPassword(
                    username,
                    password
                );

                state.adminToken =
                    adminLogin.admin_token || null;
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
    chatJoined: false,

    open(gameId = "spy-main-room") {
        this.gameId = gameId || "spy-main-room";
        this.chatJoined = false;
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

        modal.classList.add("spy-game-active");
        modal.classList.remove("hidden");

        modal.innerHTML = `
            <div class="spy-v2">
                <div class="spy-v2-head">
                    <div>
                        <div class="spy-v2-title spy-v2-head-title">
                            🕵️ بازی جاسوس
                        </div>
                        <div id="spyStatus"
                             class="spy-v2-subtitle spy-v2-head-subtitle">
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

                    <div class="spy-v2-input">
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
                data.remaining_seconds ??
                data.remaining ??
                0
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

        const gameModal = $("#gameModal");

        if (gameModal) {
            if (
                data.phase === "discussion" ||
                data.phase === "voting"
            ) {
                gameModal.classList.add(
                    "spy-chat-fullscreen"
                );
            } else {
                gameModal.classList.remove(
                    "spy-chat-fullscreen"
                );
            }
        }

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

        const modal = $("#gameModal");
        modal?.classList.remove(
            "spy-game-active",
            "spy-chat-fullscreen"
        );

        hide(modal);
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

            if (
                data?.ok &&
                data.game_id &&
                !SpyGameUI.chatJoined
            ) {
                SpyGameUI.chatJoined = true;

                socket.emit(
                    "spy_join_chat",
                    {
                        game_id: data.game_id
                    }
                );

                socket.emit(
                    "spy_chat_history",
                    {
                        game_id: data.game_id
                    }
                );
            }
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


    async function adminApiFetch(path, options = {}) {
        const headers = {
            ...(options.headers || {})
        };

        if (state.adminToken) {
            headers["X-Admin-Token"] =
                state.adminToken;
        }

        return fetch(
            `${CONFIG.API_BASE}${path}`,
            {
                ...options,
                headers
            }
        );
    }


    async function renderSpyWordsAdmin(content) {
        content.innerHTML = `
            <div class="admin-spy-words">
                <div class="admin-spy-words-head">
                    <div>
                        <h3>🕵️ بانک کلمات Spy</h3>
                        <p>مدیریت کلمات و Aliasهای بازی</p>
                    </div>

                    <div class="admin-spy-head-actions">
                        <button
                            class="admin-spy-add"
                            id="spyWordsAdd"
                            type="button"
                        >
                            ➕ افزودن کلمه
                        </button>

                        <button
                            class="admin-spy-refresh"
                            id="spyWordsRefresh"
                            type="button"
                        >
                            🔄 تازه‌سازی
                        </button>
                    </div>
                </div>

                <div class="admin-spy-stats">
                    <div class="admin-stat">
                        <span>📚</span>
                        <strong id="spyWordsTotal">0</strong>
                        <small>کل کلمات</small>
                    </div>

                    <div class="admin-stat">
                        <span>🟢</span>
                        <strong id="spyWordsEnabled">0</strong>
                        <small>فعال</small>
                    </div>

                    <div class="admin-stat">
                        <span>⚪</span>
                        <strong id="spyWordsDisabled">0</strong>
                        <small>غیرفعال</small>
                    </div>
                </div>

                <div class="admin-spy-search">
                    <input
                        id="spyWordsSearch"
                        type="search"
                        placeholder="🔍 جستجوی کلمه یا Alias..."
                        autocomplete="off"
                    >
                </div>

                <div
                    id="spyWordAddForm"
                    class="admin-spy-add-form"
                    hidden
                >
                    <div class="admin-spy-form-head">
                        <strong>➕ افزودن کلمه جدید</strong>
                        <button
                            type="button"
                            id="spyWordAddClose"
                            class="admin-spy-form-close"
                        >
                            ✕
                        </button>
                    </div>

                    <label class="admin-spy-field">
                        <span>کلمه اصلی</span>
                        <input
                            id="spyWordInput"
                            type="text"
                            autocomplete="off"
                            placeholder="مثلاً: بیمارستان"
                        >
                    </label>

                    <label class="admin-spy-field">
                        <span>Aliasها</span>
                        <textarea
                            id="spyWordAliases"
                            rows="3"
                            placeholder="مثلاً: درمانگاه، شفاخانه، بیمارستانی"
                        ></textarea>
                        <small>
                            Aliasها را با ویرگول جدا کنید.
                        </small>
                    </label>

                    <div class="admin-spy-form-actions">
                        <button
                            type="button"
                            id="spyWordAddCancel"
                            class="admin-spy-cancel"
                        >
                            انصراف
                        </button>

                        <button
                            type="button"
                            id="spyWordAddSubmit"
                            class="admin-spy-submit"
                        >
                            💾 ثبت کلمه
                        </button>
                    </div>
                </div>

                <div id="spyWordsList">
                    <div class="empty-activity">
                        ⏳ در حال دریافت بانک کلمات...
                    </div>
                </div>
            </div>
        `;

        setupSpyWordAddForm(content);

        const refreshButton =
            $("#spyWordsRefresh");

        if (refreshButton) {
            refreshButton.addEventListener(
                "click",
                () => renderSpyWordsAdmin(content)
            );
        }

        try {
            const words =
                await loadSpyWords();

            window.__spyWordsCache = words;

            renderSpyWordsList(words);

            const list =
                $("#spyWordsList");

            if (
                list &&
                !list.dataset.actionsReady
            ) {
                setupSpyWordActions(list);
                list.dataset.actionsReady = "true";
            }

            const search =
                $("#spyWordsSearch");

            if (search) {
                search.addEventListener(
                    "input",
                    () => {
                        renderSpyWordsList(
                            words,
                            search.value
                        );
                    }
                );
            }

        } catch (error) {
            console.error(error);

            const list =
                $("#spyWordsList");

            if (list) {
                list.innerHTML = `
                    <div class="empty-activity">
                        ❌ ${escapeHtml(
                            error.message ||
                            "دریافت بانک کلمات ناموفق بود."
                        )}
                    </div>
                `;
            }
        }
    }


    function renderSpyWordsList(words, searchText = "") {
        const query =
            String(searchText || "")
                .trim()
                .toLowerCase();

        const filtered =
            words.filter((item) => {
                const word =
                    String(item.word || "")
                        .toLowerCase();

                const aliases =
                    Array.isArray(item.aliases)
                        ? item.aliases.join(" ").toLowerCase()
                        : "";

                return !query ||
                    word.includes(query) ||
                    aliases.includes(query);
            });

        const total =
            words.length;

        const enabled =
            words.filter(
                (item) => item.enabled
            ).length;

        const disabled =
            total - enabled;

        setText(
            $("#spyWordsTotal"),
            total
        );

        setText(
            $("#spyWordsEnabled"),
            enabled
        );

        setText(
            $("#spyWordsDisabled"),
            disabled
        );

        const list =
            $("#spyWordsList");

        if (!list) {
            return;
        }

        if (!filtered.length) {
            list.innerHTML = `
                <div class="admin-spy-empty">
                    🔎 کلمه‌ای پیدا نشد.
                </div>
            `;
            return;
        }

        list.innerHTML =
            filtered.map((item) => {
                const aliases =
                    Array.isArray(item.aliases)
                        ? item.aliases
                        : [];

                return `
                    <div
                        class="admin-spy-word-card"
                        data-spy-word-id="${item.id}"
                    >
                        <div class="admin-spy-word-main">
                            <strong class="admin-spy-word-title">
                                ${escapeHtml(item.word)}
                            </strong>

                            <span class="${
                                item.enabled
                                    ? "spy-word-enabled"
                                    : "spy-word-disabled"
                            }">
                                ${
                                    item.enabled
                                        ? "🟢 فعال"
                                        : "⚪ غیرفعال"
                                }
                            </span>
                        </div>

                        <div class="admin-spy-aliases">
                            ${
                                aliases.length
                                    ? aliases.map(
                                        (alias) =>
                                            `<span class="admin-spy-alias">${escapeHtml(alias)}</span>`
                                    ).join("")
                                    : `<small>بدون Alias</small>`
                            }
                        </div>

                        <div class="admin-spy-word-actions">
                            <button
                                type="button"
                                class="admin-spy-action admin-spy-edit"
                                data-spy-action="edit"
                                data-spy-id="${item.id}"
                            >
                                ✏️ ویرایش
                            </button>

                            <button
                                type="button"
                                class="admin-spy-action admin-spy-toggle"
                                data-spy-action="toggle"
                                data-spy-id="${item.id}"
                            >
                                ${
                                    item.enabled
                                        ? "⚪ غیرفعال"
                                        : "🟢 فعال"
                                }
                            </button>

                            <button
                                type="button"
                                class="admin-spy-action admin-spy-delete"
                                data-spy-action="delete"
                                data-spy-id="${item.id}"
                            >
                                🗑️ حذف
                            </button>
                        </div>
                    </div>
                `;
            }).join("");
    }


    async function createSpyWord(word, aliases = []) {
        const response = await adminApiFetch(
            "/api/game/admin/spy-words",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    word: String(word || "").trim(),
                    aliases: Array.isArray(aliases)
                        ? aliases
                        : []
                })
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.error ||
                "افزودن کلمه انجام نشد."
            );
        }

        return data;
    }

    async function updateSpyWord(
        wordId,
        word,
        aliases = [],
        enabled = true
    ) {
        const response = await adminApiFetch(
            `/api/game/admin/spy-words/${wordId}`,
            {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    word: String(word || "").trim(),
                    aliases: Array.isArray(aliases)
                        ? aliases
                        : [],
                    enabled: Boolean(enabled)
                })
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.error ||
                "ویرایش کلمه انجام نشد."
            );
        }

        return data;
    }

    async function toggleSpyWord(wordId) {
        const response = await adminApiFetch(
            `/api/game/admin/spy-words/${wordId}/toggle`,
            {
                method: "PATCH"
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.error ||
                "تغییر وضعیت کلمه انجام نشد."
            );
        }

        return data;
    }

    async function deleteSpyWord(wordId) {
        const response = await adminApiFetch(
            `/api/game/admin/spy-words/${wordId}`,
            {
                method: "DELETE"
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.error ||
                "حذف کلمه انجام نشد."
            );
        }

        return data;
    }


    function setupSpyWordActions(list) {
        if (!list) {
            return;
        }

        list.addEventListener("click", async (event) => {
            const button =
                event.target.closest(
                    "[data-spy-action]"
                );

            if (!button) {
                return;
            }

            const action =
                button.dataset.spyAction;

            const wordId =
                Number(button.dataset.spyId);

            if (!wordId) {
                return;
            }

            const words =
                window.__spyWordsCache || [];

            const item =
                words.find(
                    (word) =>
                        Number(word.id) === wordId
                );

            if (!item) {
                toast("کلمه پیدا نشد.");
                return;
            }

            try {
                button.disabled = true;

                if (action === "toggle") {
                    await toggleSpyWord(wordId);

                    toast(
                        item.enabled
                            ? "کلمه غیرفعال شد."
                            : "کلمه فعال شد."
                    );

                    await refreshSpyWordsAdmin();
                    return;
                }

                if (action === "delete") {
                    const confirmed =
                        confirm(
                            `کلمه «${item.word}» حذف شود؟`
                        );

                    if (!confirmed) {
                        return;
                    }

                    await deleteSpyWord(wordId);

                    toast("کلمه حذف شد.");

                    await refreshSpyWordsAdmin();
                    return;
                }

                if (action === "edit") {
                    const newWord =
                        prompt(
                            "کلمه جدید:",
                            item.word
                        );

                    if (
                        newWord === null ||
                        !newWord.trim()
                    ) {
                        return;
                    }

                    const aliasText =
                        prompt(
                            "Aliasها را با ویرگول جدا کنید:",
                            Array.isArray(item.aliases)
                                ? item.aliases.join(", ")
                                : ""
                        );

                    if (aliasText === null) {
                        return;
                    }

                    const aliases =
                        aliasText
                            .split(",")
                            .map(
                                (alias) =>
                                    alias.trim()
                            )
                            .filter(Boolean);

                    await updateSpyWord(
                        wordId,
                        newWord.trim(),
                        aliases,
                        Boolean(item.enabled)
                    );

                    toast("کلمه ویرایش شد.");

                    await refreshSpyWordsAdmin();
                }
            } catch (error) {
                console.error(
                    "Spy word action error:",
                    error
                );

                toast(
                    error.message ||
                    "عملیات انجام نشد."
                );
            } finally {
                button.disabled = false;
            }
        });
    }

    async function refreshSpyWordsAdmin() {
        const content =
            $("#adminContent");

        if (!content) {
            return;
        }

        await renderSpyWordsAdmin(content);
    }


    function setupSpyWordAddForm(content) {
        const form = $("#spyWordAddForm");
        const openButton = $("#spyWordsAdd");
        const closeButton = $("#spyWordAddClose");
        const cancelButton = $("#spyWordAddCancel");
        const submitButton = $("#spyWordAddSubmit");
        const wordInput = $("#spyWordInput");
        const aliasesInput = $("#spyWordAliases");

        if (
            !form ||
            !openButton ||
            !submitButton ||
            !wordInput ||
            !aliasesInput
        ) {
            return;
        }

        const closeForm = () => {
            form.hidden = true;
            wordInput.value = "";
            aliasesInput.value = "";
        };

        openButton.addEventListener("click", () => {
            form.hidden = false;
            wordInput.focus();
        });

        if (closeButton) {
            closeButton.addEventListener(
                "click",
                closeForm
            );
        }

        if (cancelButton) {
            cancelButton.addEventListener(
                "click",
                closeForm
            );
        }

        submitButton.addEventListener(
            "click",
            async () => {
                const word =
                    wordInput.value.trim();

                if (!word) {
                    toast("کلمه اصلی را وارد کنید.");
                    wordInput.focus();
                    return;
                }

                const aliases =
                    aliasesInput.value
                        .split(",")
                        .map(
                            (alias) =>
                                alias.trim()
                        )
                        .filter(Boolean);

                try {
                    submitButton.disabled = true;

                    await createSpyWord(
                        word,
                        aliases
                    );

                    toast(
                        "✅ کلمه با موفقیت اضافه شد."
                    );

                    closeForm();

                    await refreshSpyWordsAdmin();
                } catch (error) {
                    console.error(
                        "Create spy word error:",
                        error
                    );

                    toast(
                        error.message ||
                        "افزودن کلمه انجام نشد."
                    );
                } finally {
                    submitButton.disabled = false;
                }
            }
        );

        if (content) {
            content.addEventListener(
                "keydown",
                (event) => {
                    if (
                        event.key === "Escape" &&
                        !form.hidden
                    ) {
                        closeForm();
                    }
                }
            );
        }
    }

    async function loadSpyWords() {
        const response =
            await adminApiFetch(
                "/api/game/admin/spy-words"
            );

        if (!response.ok) {
            let data = {};

            try {
                data = await response.json();
            } catch (_) {}

            throw new Error(
                data.error ||
                "دریافت بانک کلمات انجام نشد."
            );
        }

        const data =
            await response.json();

        return Array.isArray(data.words)
            ? data.words
            : [];
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

        if (tab === "spy-words") {
            await renderSpyWordsAdmin(content);
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

                            SpyGameUI.open();

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
