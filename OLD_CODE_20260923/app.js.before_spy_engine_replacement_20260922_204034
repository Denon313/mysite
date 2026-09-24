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
    phase: "lobby",
    state: null,
    replyTo: null,
    selectedVote: null,
    messages: [],
    boundSocket: null,
    lobbyJoined: false,
    gameJoined: false,
    chatJoined: false,
    tickTimer: null,

    open() {
        this.resetLocal();

        state.currentGame = {
            type: "spy",
            gameId: null,
            data: null
        };

        this.renderLobby();
        this.bindSocket();
        this.ensureSocket();

        return true;
    },

    resetLocal() {
        this.gameId = null;
        this.phase = "lobby";
        this.state = null;
        this.replyTo = null;
        this.selectedVote = null;
        this.messages = [];
        this.lobbyJoined = false;
        this.gameJoined = false;
        this.chatJoined = false;

        if (this.tickTimer) {
            clearInterval(this.tickTimer);
            this.tickTimer = null;
        }
    },

    ensureSocket() {
        if (!state.currentUser) {
            toast("ابتدا وارد حساب شو.");
            return;
        }

        if (!state.socket || !state.socket.connected) {
            if (typeof connectSocket === "function") {
                connectSocket();
            }
            return;
        }

        this.joinLobby();
    },

    bindSocket() {
        const socket = state.socket;

        if (!socket || socket === this.boundSocket) {
            return;
        }

        this.boundSocket = socket;

        socket.on("connect", () => {
            if (
                state.currentGame?.type === "spy" &&
                !this.lobbyJoined &&
                !this.gameJoined
            ) {
                this.joinLobby();
            }
        });

        socket.on("spy_lobby", (data) => {
            if (state.currentGame?.type !== "spy") return;

            this.lobbyJoined = true;
            this.gameJoined = false;
            this.gameId = null;
            this.phase = "lobby";

            this.renderLobby(data || {});
        });

        socket.on("spy_prepared", (data) => {
            if (state.currentGame?.type !== "spy") return;

            this.gameId = data?.game_id || this.gameId;
            this.phase = "duration_selection";

            if (data?.ok === false) return;

            this.renderDuration();
        });

        socket.on("spy_joined", (data) => {
            if (state.currentGame?.type !== "spy") return;

            this.gameJoined = true;
            this.lobbyJoined = false;
            this.gameId = data?.game_id || this.gameId;

            if (data?.state) {
                this.state = data.state;
                this.renderGame(data.state);
            }
        });

        socket.on("spy_state", (data) => {
            if (state.currentGame?.type !== "spy") return;

            this.state = data || this.state;

            if (data?.game_id) {
                this.gameId = data.game_id;
            }

            this.renderGame(data);
        });

        socket.on("spy_started", (data) => {
            if (state.currentGame?.type !== "spy") return;

            this.gameId = data?.game_id || this.gameId;

            if (data?.state) {
                this.state = data.state;
                this.renderGame(data.state);
            }
        });

        socket.on("spy_tick", (data) => {
            if (state.currentGame?.type !== "spy") return;

            this.handleTick({
                ...(data || {}),
                remaining_seconds: Number(
                    data?.remaining_seconds ?? data?.remaining ?? 0
                )
            });
        });

        socket.on("spy_vote_saved", (data) => {
            if (state.currentGame?.type !== "spy") return;

            if (data?.state) {
                this.state = data.state;
                this.renderGame(data.state);
            }
        });

        socket.on("spy_guess_result", (data) => {
            if (state.currentGame?.type !== "spy") return;

            this.state = data?.state || data || this.state;
            this.renderResult(this.state);
        });

        socket.on("spy_finished", (data) => {
            if (state.currentGame?.type !== "spy") return;

            this.state = data?.state || data || this.state;
            this.renderResult(this.state);
        });

        socket.on("spy_replay_ready", (data) => {
            if (state.currentGame?.type !== "spy") return;

            this.gameId = data?.game_id || this.gameId;

            this.roleRevealGameId = null;

            clearTimeout(this.roleRevealTimer);

            this.state = {
                ...(this.state || {}),
                ...(data?.state || {}),
                game_id: this.gameId,
                phase: "duration_selection",
                my_role: null,
                role: null,
                secret_word: null,
                result: null
            };

            this.phase = "duration_selection";

            this.renderDuration();
        });

        socket.on("spy_chat_history", (data) => {
            if (state.currentGame?.type !== "spy") return;

            this.handleChatHistory(data);
        });

        socket.on("spy_chat", (data) => {
            if (state.currentGame?.type !== "spy") return;

            this.handleChatMessage(data);
        });

        socket.on("spy_error", (data) => {
            if (state.currentGame?.type !== "spy") return;

            const message =
                data?.message ||
                data?.error ||
                "خطایی در بازی جاسوس رخ داد.";

            alert(message);
        });

        socket.on("spy_left", () => {
            if (state.currentGame?.type !== "spy") return;

            this.gameJoined = false;
            this.lobbyJoined = false;
            this.gameId = null;
        });
    },

    joinLobby() {
        if (!state.socket?.connected || !state.currentUser) {
            return;
        }

        state.socket.emit("spy_join_lobby");
        this.lobbyJoined = true;
    },

    renderLobby(data = null) {
        this.phase = "lobby";

        const players = Array.isArray(data?.players)
            ? data.players
            : [];

        const host = data?.host || players[0] || null;
        const me = state.currentUser?.username;

        const rows = players.length
            ? players.map((username, index) => `
                <div class="spy-zero-player">
                    <div class="spy-zero-avatar">
                        ${(index + 1)}
                    </div>
                    <div class="spy-zero-player-info">
                        <strong>${this.escape(
                            this.displayName(username)
                        )}</strong>
                        ${
                            username === host
                                ? `<span class="spy-zero-host">میزبان</span>`
                                : ""
                        }
                    </div>
                    ${
                        username === me
                            ? `<span class="spy-zero-me">شما</span>`
                            : ""
                    }
                </div>
            `).join("")
            : `
                <div class="spy-zero-empty">
                    <div>🕵️</div>
                    <span>هنوز بازیکنی وارد نشده</span>
                </div>
            `;

        const canStart =
            me === "mehdi" &&
            players.length >= 1 &&
            players.length <= 5;

        this.setContent(`
            <div class="spy-zero-screen">
                <div class="spy-zero-top">
                    <div>
                        <span class="spy-zero-label">SPY GAME</span>
                        <h2>بازی جاسوس</h2>
                        <p>بازیکن‌ها وارد اتاق می‌شوند.</p>
                    </div>

                    <button
                        class="spy-zero-close"
                        type="button"
                        data-spy-close
                    >✕</button>
                </div>

                <div class="spy-zero-card">
                    <div class="spy-zero-card-head">
                        <strong>بازیکن‌ها</strong>
                        <span>${players.length}/5</span>
                    </div>

                    <div class="spy-zero-players">
                        ${rows}
                    </div>
                </div>

                <div class="spy-zero-status">
                    ${
                        players.length < 1
                            ? "منتظر ورود بازیکن‌ها..."
                            : host === me
                                ? "شما میزبان هستید."
                                : "منتظر شروع میزبان..."
                    }
                </div>

                ${
                    canStart
                        ? `
                            <button
                                class="spy-zero-primary"
                                type="button"
                                data-spy-prepare
                            >
                                شروع و انتخاب زمان
                            </button>
                        `
                        : ""
                }

                <button
                    class="spy-zero-secondary"
                    type="button"
                    data-spy-leave-lobby
                >
                    خروج
                </button>
            </div>
        `);

        this.bindLobbyButtons();
    },

    bindLobbyButtons() {
        this.q("[data-spy-prepare]")?.addEventListener(
            "click",
            () => {
                state.socket?.emit("spy_prepare_start");
            }
        );

        this.q("[data-spy-leave-lobby]")?.addEventListener(
            "click",
            () => this.leaveLobby()
        );

        this.q("[data-spy-close]")?.addEventListener(
            "click",
            () => this.leaveLobby()
        );
    },

    renderDuration() {
        this.phase = "duration_selection";

        this.setContent(`
            <div class="spy-zero-screen spy-zero-centered">
                <div class="spy-zero-top">
                    <div>
                        <span class="spy-zero-label">SPY GAME</span>
                        <h2>زمان بحث</h2>
                        <p>مدت زمان را برحسب ثانیه وارد کن.</p>
                    </div>

                    <button
                        class="spy-zero-close"
                        type="button"
                        data-spy-close
                    >✕</button>
                </div>

                <div class="spy-zero-duration-card">
                    <label for="spyDuration">
                        مدت زمان
                    </label>

                    <input
                        id="spyDuration"
                        class="spy-zero-duration-input"
                        type="number"
                        min="10"
                        max="1800"
                        value="120"
                        inputmode="numeric"
                    >

                    <div class="spy-zero-duration-hint">
                        مثال: 120 ثانیه = ۲ دقیقه
                    </div>

                    <div class="spy-zero-presets">
                        <button type="button" data-duration="60">۶۰</button>
                        <button type="button" data-duration="120">۱۲۰</button>
                        <button type="button" data-duration="180">۱۸۰</button>
                        <button type="button" data-duration="300">۳۰۰</button>
                    </div>

                    <button
                        class="spy-zero-primary"
                        type="button"
                        data-spy-start
                    >
                        شروع بازی
                    </button>
                </div>
            </div>
        `);

        this.q("[data-spy-close]")?.addEventListener(
            "click",
            () => this.close()
        );

        this.qa("[data-duration]").forEach(button => {
            button.addEventListener("click", () => {
                const input = this.q("#spyDuration");
                if (input) {
                    input.value = button.dataset.duration;
                }
            });
        });

        this.q("[data-spy-start]")?.addEventListener(
            "click",
            () => {
                const input = this.q("#spyDuration");
                let seconds = Number(input?.value || 120);

                seconds = Math.max(
                    10,
                    Math.min(
                        1800,
                        Math.floor(seconds)
                    )
                );

                if (input) {
                    input.value = seconds;
                }

                state.socket?.emit(
                    "spy_start",
                    {
                        game_id: this.gameId,
                        duration_seconds: seconds
                    }
                );
            }
        );
    },

    renderGame(gameState = this.state) {
        if (!gameState) return;

        this.phase = gameState.phase || "discussion";

        if (this.phase === "duration_selection") {
            this.renderDuration();
            return;
        }

        if (
            this.phase === "finished" ||
            this.phase === "spy_guess"
        ) {
            this.renderResult(gameState);
            return;
        }

        if (this.phase === "voting") {
            this.renderVoting(gameState);
            return;
        }

        if (this.phase === "discussion") {
            const role = gameState?.my_role ?? gameState?.role;

            if (
                this.roleRevealGameId !== gameState?.game_id
            ) {
                this.roleRevealGameId = gameState?.game_id;
                this.renderRoleReveal(gameState);

                clearTimeout(this.roleRevealTimer);

                this.roleRevealTimer = setTimeout(() => {
                    if (
                        this.state?.game_id === gameState?.game_id &&
                        this.state?.phase === "discussion"
                    ) {
                        this.renderDiscussion(this.state);
                    }
                }, 3000);

                return;
            }
        }

        this.renderDiscussion(gameState);
    },

    renderRoleReveal(data) {
        const role = data?.my_role ?? data?.role;
        const word = data?.secret_word;

        this.setContent(`
            <div class="spy-zero-screen spy-zero-centered">
                <div class="spy-zero-role-reveal">
                    <span class="spy-zero-label">SPY GAME</span>

                    <div class="spy-zero-reveal-icon">
                        ${role === "spy" ? "🕵️" : "👤"}
                    </div>

                    <h2>
                        ${role === "spy" ? "تو جاسوسی!" : "تو شهروندی!"}
                    </h2>

                    <div class="spy-zero-reveal-word">
                        <span>کلمه</span>
                        <strong>
                            ${
                                role === "spy"
                                    ? "مخفی"
                                    : this.escape(word || "—")
                            }
                        </strong>
                    </div>

                    <p>این اطلاعات فقط برای توست.</p>
                    <small>تا چند لحظه دیگر وارد اتاق بحث می‌شوی...</small>
                </div>
            </div>
        `);
    },

    renderDiscussion(data) {
        const role = data?.my_role ?? data?.role;
        const word = data?.secret_word;
        const players = Array.isArray(data?.players)
            ? data.players
            : [];

        this.setContent(`
            <div class="spy-zero-chat-screen">
                <header class="spy-zero-chat-header">
                    <div class="spy-zero-chat-title">
                        <span class="spy-zero-label">SPY GAME</span>
                        <strong>اتاق بحث</strong>
                    </div>

                    <div class="spy-zero-timer" id="spyZeroTimer">
                        ${this.formatSeconds(
                            data?.remaining_seconds
                        )}
                    </div>

                    <button
                        class="spy-zero-header-close"
                        type="button"
                        data-spy-close
                    >✕</button>
                </header>

                <div class="spy-zero-role-strip">
                    <div>
                        <span>نقش شما</span>
                        <strong>
                            ${
                                role === "spy"
                                    ? "🕵️ جاسوس"
                                    : "👤 شهروند"
                            }
                        </strong>
                    </div>

                    <div class="spy-zero-word-box">
                        <span>کلمه</span>
                        <strong>
                            ${
                                role === "spy"
                                    ? "مخفی"
                                    : this.escape(word || "—")
                            }
                        </strong>
                    </div>

                    <div class="spy-zero-count">
                        👥 ${players.length}
                    </div>
                </div>

                <div
                    class="spy-zero-messages"
                    id="spyZeroMessages"
                >
                    ${this.renderMessages()}
                </div>

                <div
                    class="spy-zero-reply"
                    id="spyZeroReply"
                    hidden
                ></div>

                <form
                    class="spy-zero-chat-input"
                    id="spyZeroChatForm"
                >
                    <input
                        id="spyZeroMessageInput"
                        type="text"
                        autocomplete="off"
                        maxlength="1000"
                        placeholder="پیامت رو بنویس..."
                    >

                    <button type="submit">
                        ➤
                    </button>
                </form>
            </div>
        `);

        this.bindChat();
        this.scrollMessages(true);
        this.updateTimer(data);
    },

    renderVoting(data) {
        const players = Array.isArray(data?.players)
            ? data.players
            : [];

        this.setContent(`
            <div class="spy-zero-chat-screen spy-zero-voting-screen">
                <header class="spy-zero-chat-header">
                    <div class="spy-zero-chat-title">
                        <span class="spy-zero-label">SPY GAME</span>
                        <strong>رأی‌گیری</strong>
                    </div>

                    <div class="spy-zero-timer" id="spyZeroTimer">
                        ${this.formatSeconds(
                            data?.remaining_seconds
                        )}
                    </div>

                    <button
                        class="spy-zero-header-close"
                        type="button"
                        data-spy-close
                    >✕</button>
                </header>

                <div class="spy-zero-vote-intro">
                    <strong>به کسی که فکر می‌کنی جاسوسه رأی بده.</strong>
                    <span>رأی‌ها تا پایان مخفی می‌مانند.</span>
                </div>

                <div class="spy-zero-vote-list">
                    ${
                        players.map(username => `
                            <button
                                type="button"
                                class="spy-zero-vote-button ${
                                    this.selectedVote === username
                                        ? "selected"
                                        : ""
                                }"
                                data-vote="${this.escape(
                                    username
                                )}"
                            >
                                <span class="spy-zero-vote-avatar">
                                    👤
                                </span>

                                <span>
                                    ${this.escape(
                                        this.displayName(username)
                                    )}
                                </span>

                                ${
                                    this.selectedVote === username
                                        ? `<b>✓</b>`
                                        : ""
                                }
                            </button>
                        `).join("")
                    }
                </div>

                <div class="spy-zero-vote-note">
                    می‌توانی تا پایان زمان رأی خودت را تغییر بدهی.
                </div>
            </div>
        `);

        this.q("[data-spy-close]")?.addEventListener(
            "click",
            () => this.close()
        );

        this.qa("[data-vote]").forEach(button => {
            button.addEventListener("click", () => {
                const username = button.dataset.vote;

                this.selectedVote = username;

                state.socket?.emit(
                    "spy_vote",
                    {
                        game_id: this.gameId,
                        username
                    }
                );

                this.renderVoting({
                    ...this.state,
                    ...data
                });
            });
        });

        this.updateTimer(data);
    },

    renderResult(data) {
        const result = data?.result || data || {};
        const phase = data?.phase || this.phase;

        const waitingGuess =
            phase === "spy_guess" ||
            result?.phase === "spy_guess";

        const winner = result?.winner || data?.winner;
        const spy = result?.spy_username || data?.spy_username;
        const word = result?.secret_word || data?.secret_word;

        this.setContent(`
            <div class="spy-zero-result-screen">
                <div class="spy-zero-result-top">
                    <button
                        type="button"
                        class="spy-zero-back"
                        data-spy-close
                    >
                        ← بازگشت
                    </button>

                    <span class="spy-zero-label">
                        SPY GAME
                    </span>
                </div>

                <div class="spy-zero-result-content">
                    <div class="spy-zero-result-icon">
                        ${
                            waitingGuess
                                ? "🕵️"
                                : winner === "spy"
                                    ? "🕵️"
                                    : "🎉"
                        }
                    </div>

                    <h2>
                        ${
                            waitingGuess
                                ? "جاسوس پیدا شد!"
                                : winner === "spy"
                                    ? "جاسوس برنده شد"
                                    : "شهروندها برنده شدند"
                        }
                    </h2>

                    <p class="spy-zero-result-sub">
                        ${
                            waitingGuess
                                ? "حالا جاسوس یک فرصت برای حدس کلمه دارد."
                                : "نتیجه این دور مشخص شد."
                        }
                    </p>

                    <div class="spy-zero-result-grid">
                        <div>
                            <span>جاسوس</span>
                            <strong>
                                ${this.escape(
                                    this.displayName(spy)
                                )}
                            </strong>
                        </div>

                        <div>
                            <span>کلمه</span>
                            <strong>
                                ${this.escape(word || "—")}
                            </strong>
                        </div>
                    </div>

                    ${
                        waitingGuess
                            ? `
                                <form
                                    id="spyZeroGuessForm"
                                    class="spy-zero-guess"
                                >
                                    <input
                                        id="spyZeroGuessInput"
                                        type="text"
                                        maxlength="100"
                                        autocomplete="off"
                                        placeholder="حدس جاسوس..."
                                    >

                                    <button type="submit">
                                        ثبت حدس
                                    </button>
                                </form>
                            `
                            : `
                                ${
                                    result?.spy_guess
                                        ? `
                                            <div class="spy-zero-guess-result">
                                                <span>حدس جاسوس</span>
                                                <strong>
                                                    ${this.escape(
                                                        result.spy_guess
                                                    )}
                                                </strong>
                                            </div>
                                        `
                                        : ""
                                }

                                <button
                                    type="button"
                                    class="spy-zero-primary"
                                    data-spy-replay
                                >
                                    بازی مجدد
                                </button>
                            `
                    }
                </div>
            </div>
        `);

        this.q("[data-spy-close]")?.addEventListener(
            "click",
            () => this.close()
        );

        this.q("[data-spy-replay]")?.addEventListener(
            "click",
            event => {
                const button = event.currentTarget;

                if (button.dataset.replaying === "1") {
                    return;
                }

                button.dataset.replaying = "1";
                button.disabled = true;

                state.socket?.emit(
                    "spy_replay",
                    {
                        game_id: this.gameId
                    }
                );
            }
        );

        this.q("#spyZeroGuessForm")?.addEventListener(
            "submit",
            event => {
                event.preventDefault();

                const input = this.q("#spyZeroGuessInput");
                const guess = String(
                    input?.value || ""
                ).trim();

                if (!guess) {
                    toast("حدست رو وارد کن.");
                    return;
                }

                state.socket?.emit(
                    "spy_guess",
                    {
                        game_id: this.gameId,
                        guess
                    }
                );
            }
        );
    },

    renderMessages() {
        if (!this.messages.length) {
            return `
                <div class="spy-zero-chat-empty">
                    <div>💬</div>
                    <span>هنوز پیامی ارسال نشده.</span>
                </div>
            `;
        }

        return this.messages.map(message => {
            const mine =
                message.username ===
                state.currentUser?.username;

            const reply =
                message.reply_to &&
                this.messages.find(
                    item =>
                        String(item.id) ===
                        String(message.reply_to)
                );

            return `
                <div
                    class="spy-zero-message ${mine ? "mine" : ""}"
                    data-message-id="${this.escape(
                        String(message.id || "")
                    )}"
                >
                    ${
                        reply
                            ? `
                                <div class="spy-zero-message-reply">
                                    ↩ ${this.escape(
                                        reply.display_name ||
                                        this.displayName(
                                            reply.username
                                        )
                                    )}
                                </div>
                            `
                            : ""
                    }

                    <div class="spy-zero-message-meta">
                        <strong>
                            ${this.escape(
                                message.display_name ||
                                this.displayName(
                                    message.username
                                )
                            )}
                        </strong>

                        ${
                            message.created_at
                                ? `<span>${this.formatMessageTime(
                                    message.created_at
                                )}</span>`
                                : ""
                        }
                    </div>

                    <div class="spy-zero-message-body">
                        ${this.escape(
                            message.message || ""
                        )}
                    </div>

                    <button
                        type="button"
                        class="spy-zero-reply-button"
                        data-reply-id="${this.escape(
                            String(message.id || "")
                        )}"
                    >
                        پاسخ
                    </button>
                </div>
            `;
        }).join("");
    },

    bindChat() {
        const form = this.q("#spyZeroChatForm");
        const input = this.q("#spyZeroMessageInput");

        form?.addEventListener(
            "submit",
            event => {
                event.preventDefault();

                const message =
                    String(input?.value || "").trim();

                if (!message) return;

                state.socket?.emit(
                    "spy_chat",
                    {
                        game_id: this.gameId,
                        message,
                        reply_to: this.replyTo
                    }
                );

                input.value = "";
                this.clearReply();
            }
        );

        this.qa("[data-reply-id]").forEach(button => {
            button.addEventListener("click", () => {
                this.replyTo =
                    button.dataset.replyId || null;

                const message =
                    this.messages.find(
                        item =>
                            String(item.id) ===
                            String(this.replyTo)
                    );

                const box = this.q("#spyZeroReply");

                if (!box) return;

                box.hidden = false;

                box.innerHTML = `
                    ↩ پاسخ به
                    <strong>
                        ${this.escape(
                            message?.display_name ||
                            this.displayName(
                                message?.username
                            )
                        )}
                    </strong>

                    <button
                        type="button"
                        data-clear-reply
                    >✕</button>
                `;

                this.q("[data-clear-reply]")?.addEventListener(
                    "click",
                    () => this.clearReply()
                );

                input?.focus();
            });
        });

        this.q("[data-spy-close]")?.addEventListener(
            "click",
            () => this.close()
        );
    },

    clearReply() {
        this.replyTo = null;

        const box = this.q("#spyZeroReply");

        if (box) {
            box.hidden = true;
            box.innerHTML = "";
        }
    },

    handleChatHistory(data) {
        this.messages =
            Array.isArray(data)
                ? data
                : Array.isArray(data?.messages)
                    ? data.messages
                    : [];

        if (
            this.phase === "discussion" &&
            this.q("#spyZeroMessages")
        ) {
            const box = this.q("#spyZeroMessages");
            box.innerHTML = this.renderMessages();
            this.bindMessageReplies();
            this.scrollMessages(true);
        }
    },

    handleChatMessage(data) {
        if (!data) return;

        if (
            data.game_id &&
            this.gameId &&
            String(data.game_id) !== String(this.gameId)
        ) {
            return;
        }

        const id = data.id;

        if (
            id &&
            this.messages.some(
                item => String(item.id) === String(id)
            )
        ) {
            return;
        }

        this.messages.push(data);

        const box = this.q("#spyZeroMessages");

        if (!box) return;

        const wasBottom =
            box.scrollHeight -
            box.scrollTop -
            box.clientHeight < 120;

        box.innerHTML = this.renderMessages();
        this.bindMessageReplies();

        if (wasBottom) {
            this.scrollMessages(true);
        }
    },

    bindMessageReplies() {
        this.qa("[data-reply-id]").forEach(button => {
            button.addEventListener("click", () => {
                this.replyTo =
                    button.dataset.replyId || null;

                const message =
                    this.messages.find(
                        item =>
                            String(item.id) ===
                            String(this.replyTo)
                    );

                const box = this.q("#spyZeroReply");

                if (!box) return;

                box.hidden = false;

                box.innerHTML = `
                    ↩ پاسخ به
                    <strong>
                        ${this.escape(
                            message?.display_name ||
                            this.displayName(
                                message?.username
                            )
                        )}
                    </strong>

                    <button
                        type="button"
                        data-clear-reply
                    >✕</button>
                `;

                this.q("[data-clear-reply]")?.addEventListener(
                    "click",
                    () => this.clearReply()
                );

                this.q("#spyZeroMessageInput")?.focus();
            });
        });
    },

    scrollMessages(force = false) {
        const box = this.q("#spyZeroMessages");

        if (!box) return;

        if (force) {
            box.scrollTop = box.scrollHeight;
        }
    },

    updateTimer(data) {
        const timer = this.q("#spyZeroTimer");

        if (!timer) return;

        const seconds = Number(
            data?.remaining_seconds ?? 0
        );

        timer.textContent =
            this.formatSeconds(seconds);
    },

    handleTick(data) {
        if (!data) return;

        this.updateTimer(data);

        if (
            data.phase &&
            data.phase !== this.phase
        ) {
            this.phase = data.phase;

            if (
                data.phase === "voting" ||
                data.phase === "finished" ||
                data.phase === "spy_guess"
            ) {
                this.state = {
                    ...(this.state || {}),
                    ...data
                };

                if (data.phase === "voting") {
                    this.selectedVote = data.my_vote || null;
                }

                this.renderGame(this.state);
            }
        }
    },

    handleState(data) {
        if (!data) return;

        if (data.game_id) {
            this.gameId = data.game_id;

            if (state.currentGame) {
                state.currentGame.gameId =
                    data.game_id;
            }
        }

        this.state = {
            ...(this.state || {}),
            ...data
        };

        this.phase = data.phase || this.phase;

        if (
            this.phase === "discussion" &&
            !this.chatJoined
        ) {
            this.joinChat();
        }

        this.renderGame(this.state);
    },

    joinChat() {
        if (
            !this.gameId ||
            !state.socket?.connected
        ) {
            return;
        }

        state.socket.emit(
            "spy_join_chat",
            {
                game_id: this.gameId
            }
        );

        this.chatJoined = true;
    },

    joinGame(gameId) {
        if (
            !gameId ||
            !state.socket?.connected
        ) {
            return;
        }

        this.gameId = gameId;

        if (state.currentGame) {
            state.currentGame.gameId = gameId;
        }

        state.socket.emit(
            "spy_join",
            {
                game_id: gameId
            }
        );

        this.gameJoined = true;
    },

    leaveLobby() {
        if (state.socket?.connected) {
            state.socket.emit("spy_leave_lobby");
        }

        this.lobbyJoined = false;
        this.close();
    },

    close() {
        if (state.socket?.connected) {
            if (this.gameId) {
                state.socket.emit(
                    "spy_leave",
                    {
                        game_id: this.gameId
                    }
                );
            } else if (this.lobbyJoined) {
                state.socket.emit(
                    "spy_leave_lobby"
                );
            }
        }

        this.resetLocal();

        state.currentGame = null;

        const modal = $("#gameModal");

        modal?.classList.remove(
            "spy-game-active",
            "spy-chat-fullscreen"
        );

        hide(modal);
    },

    setContent(html) {
        const modal = $("#gameModal");
        const content = $("#gameContent");

        if (!content) return;

        modal?.classList.add("spy-game-active");

        content.innerHTML = html;

        show(modal);
    },

    displayName(username) {
        if (!username) return "بازیکن";

        const players =
            state.players ||
            state.connectedUsers ||
            [];

        const item =
            Array.isArray(players)
                ? players.find(
                    player =>
                        player.username === username ||
                        player.id === username
                )
                : null;

        return (
            item?.display_name ||
            item?.displayName ||
            username
        );
    },

    formatSeconds(seconds) {
        const value = Math.max(
            0,
            Number(seconds || 0)
        );

        const minutes =
            Math.floor(value / 60);

        const secs =
            value % 60;

        return `${String(minutes).padStart(2, "0")}:${String(
            secs
        ).padStart(2, "0")}`;
    },

    formatMessageTime(value) {
        try {
            const date = new Date(value);

            if (Number.isNaN(date.getTime())) {
                return "";
            }

            return date.toLocaleTimeString(
                "fa-IR",
                {
                    hour: "2-digit",
                    minute: "2-digit"
                }
            );
        } catch {
            return "";
        }
    },

    escape(value) {
        return String(value ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    },

    q(selector) {
        return document.querySelector(selector);
    },

    qa(selector) {
        return Array.from(
            document.querySelectorAll(selector)
        );
    }
};




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
