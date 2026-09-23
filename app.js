const socket = io();

const state = {
    player: null,
    players: [],
    phase: "lobby",
    connected: false,
    flashlight: false
};

const $ = (selector) => document.querySelector(selector);

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function render() {
    let root = $("#app");

    if (!root) {
        root = document.createElement("div");
        root.id = "app";
        document.body.prepend(root);
    }

    if (!state.player) {
        root.innerHTML = `
            <div class="case-login">
                <h1>پرونده مرموز</h1>
                <h2>شهر مهستان</h2>
                <p>برای ورود، کارآگاه خود را انتخاب کنید.</p>

                <div class="case-players">
                    ${[
                        ["mehdi", "مهدی", "admin"],
                        ["rastin", "راستین", "player"],
                        ["amirali", "امیرعلی", "player"],
                        ["mahna", "مهنا", "player"],
                        ["fatemeh", "فاطمه", "player"]
                    ].map(([id, name, role]) => `
                        <button class="case-player" data-login="${id}">
                            <strong>کارآگاه ${escapeHtml(name)}</strong>
                            ${role === "admin" ? "<small>مدیر پرونده</small>" : ""}
                        </button>
                    `).join("")}
                </div>
            </div>
        `;

        document.querySelectorAll("[data-login]").forEach(button => {
            button.addEventListener("click", () => login(button.dataset.login));
        });

        return;
    }

    if (state.phase === "lobby") {
        root.innerHTML = `
            <div class="case-lobby">
                <div class="case-header">
                    <div>
                        <small>GAME ROOM</small>
                        <h1>پرونده مرموز — شهر مهستان</h1>
                    </div>
                    <div class="connection">
                        ${state.connected ? "🟢 آنلاین" : "🔴 اتصال قطع"}
                    </div>
                </div>

                <div class="detectives">
                    <h2>کارآگاهان</h2>
                    ${state.players.map(p => `
                        <div class="detective">
                            <span>🟢</span>
                            <strong>کارآگاه ${escapeHtml(p.name)}</strong>
                            ${p.role === "admin" ? "<em>مدیر</em>" : ""}
                        </div>
                    `).join("")}
                </div>

                <div class="case-start-box">
                    <h2>پرونده آماده است</h2>
                    <p>حداقل ۲ کارآگاه برای شروع لازم است.</p>

                    ${state.player.role === "admin"
                        ? `<button id="startCase" ${state.players.length < 2 ? "disabled" : ""}>
                            ▶ شروع پرونده
                           </button>`
                        : `<p>منتظر شروع پرونده توسط مدیر باشید...</p>`
                    }
                </div>
            </div>
        `;

        $("#startCase")?.addEventListener("click", () => {
            socket.emit("case_start");
        });

        return;
    }

    if (state.phase === "scenario") {
        root.innerHTML = `
            <div class="case-scenario">
                <div class="scenario-label">CASE FILE</div>
                <h1>پرونده مرموز — شهر مهستان</h1>

                <div class="scenario-card">
                    <h2>پرونده شماره MH-001</h2>
                    <p>
                        شهر مهستان چند ساعت است که درگیر یک حادثه مرموز شده.
                        اطلاعات اولیه ناقص است و هنوز مشخص نیست چه کسی حقیقت را پنهان می‌کند.
                    </p>
                    <p>
                        شما و دیگر کارآگاهان باید وارد شهر شوید،
                        مدارک را پیدا کنید، با افراد صحبت کنید،
                        زمان‌بندی اتفاقات را بازسازی کنید و حقیقت پرونده را کشف کنید.
                    </p>
                </div>

                <button id="continueCase">▶ ادامه</button>
            </div>
        `;

        $("#continueCase")?.addEventListener("click", () => {
            socket.emit("case_continue");
        });

        return;
    }

    if (state.phase === "city") {
        root.innerHTML = `
            <div class="mehestan-game">

                <div class="game-top">
                    <div>
                        <small>مهستان</small>
                        <strong>پرونده MH-001</strong>
                    </div>

                    <div class="game-time">
                        ${new Date().toLocaleTimeString("fa-IR", {
                            hour: "2-digit",
                            minute: "2-digit"
                        })}
                    </div>
                </div>

                <div class="game-world">
                    <div class="city-title">
                        <span>🏙️</span>
                        <h1>شهر مهستان</h1>
                        <p>پرونده آغاز شد</p>
                    </div>

                    <div class="city-location">
                        📍 میدان مرکزی مهستان
                    </div>

                    <div class="flashlight-status ${state.flashlight ? "active" : ""}">
                        🔦 چراغ‌قوه ${state.flashlight ? "روشن" : "خاموش"}
                    </div>
                </div>

                <div class="game-hud">

                    <button id="flashlight" class="hud-button">
                        🔦
                        <small>چراغ‌قوه</small>
                    </button>

                    <button class="hud-button">
                        🪪
                        <small>هویت</small>
                    </button>

                    <button class="hud-button">
                        📱
                        <small>موبایل</small>
                    </button>

                    <button class="hud-button">
                        📹
                        <small>دوربین</small>
                    </button>

                </div>

            </div>
        `;

        $("#flashlight")?.addEventListener("click", toggleFlashlight);
    }
}

async function login(username) {
    try {
        const response = await fetch("/api/game/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ username })
        });

        const data = await response.json();

        if (!data.success) {
            alert(data.message || "ورود ناموفق بود");
            return;
        }

        state.player = data.player;

        socket.emit("game_join", {
            username: state.player.username
        });

        render();

    } catch (error) {
        console.error(error);
        alert("ارتباط با سرور برقرار نشد.");
    }
}

function toggleFlashlight() {
    state.flashlight = !state.flashlight;

    document.body.classList.toggle(
        "flashlight-on",
        state.flashlight
    );

    render();
}

socket.on("connect", () => {
    state.connected = true;

    if (state.player) {
        socket.emit("game_join", {
            username: state.player.username
        });
    }

    render();
});

socket.on("disconnect", () => {
    state.connected = false;
    render();
});

socket.on("state_update", (data) => {
    if (!data) return;

    if (Array.isArray(data.players)) {
        state.players = data.players;
    }

    if (data.phase) {
        state.phase = data.phase;
    }

    render();
});

socket.on("game_state", (data) => {
    if (!data) return;

    if (Array.isArray(data.players)) {
        state.players = data.players;
    }

    if (data.phase) {
        state.phase = data.phase;
    }

    render();
});

document.addEventListener("DOMContentLoaded", render);

/* ===== MEHESTAN 3D ENGINE TEST ===== */

function start3DTest() {
    if (state.phase !== "city") return;

    const world = document.querySelector(".game-world");
    if (!world) return;

    world.innerHTML = `
        <div id="mehesatan3d">
            <div class="world-sky"></div>

            <div class="world-ground">
                <div class="road"></div>
                <div class="building building-a"></div>
                <div class="building building-b"></div>
                <div class="building building-c"></div>

                <div class="clue-object" id="testClue">
                    🗝️
                </div>
            </div>

            <div class="crosshair">+</div>

            <div class="interaction-message" id="interactionMessage">
                برای بررسی شیء نزدیک شوید
            </div>

            <div class="mobile-controls">
                <button id="moveForward">▲</button>
                <button id="moveLeft">◀</button>
                <button id="moveBack">▼</button>
                <button id="moveRight">▶</button>
            </div>
        </div>
    `;

    const clue = document.getElementById("testClue");
    const message = document.getElementById("interactionMessage");

    clue?.addEventListener("click", () => {
        message.textContent = "📁 مدرک پیدا شد — کلید شماره 017";
        clue.classList.add("found");
    });

    document.getElementById("moveForward")?.addEventListener("click", () => {
        world.scrollTop -= 80;
    });

    document.getElementById("moveBack")?.addEventListener("click", () => {
        world.scrollTop += 80;
    });

    document.getElementById("moveLeft")?.addEventListener("click", () => {
        world.scrollLeft -= 80;
    });

    document.getElementById("moveRight")?.addEventListener("click", () => {
        world.scrollLeft += 80;
    });
}

const oldRender = render;

render = function() {
    oldRender();

    if (state.phase === "city") {
        setTimeout(start3DTest, 0);
    }
};


/* ===== NATURE 3D GAME ===== */

function openNature3D() {
    const modal = document.getElementById("gameModal");
    const content = document.getElementById("gameContent");

    if (!modal || !content) return;

    modal.classList.remove("hidden");

    content.innerHTML = `
        <div class="nature3d-placeholder">
            <div class="nature3d-placeholder-icon">🌲</div>
            <h1>جنگل آرام</h1>
            <p>دنیای سه‌بعدی در حال آماده‌سازی...</p>
        </div>
    `;
}

document.addEventListener("click", (event) => {
    const button = event.target.closest('[data-game="nature3d"]');

    if (!button) return;

    event.preventDefault();
    event.stopPropagation();

    openNature3D();
});

document.getElementById("closeGame")?.addEventListener("click", () => {
    document.getElementById("gameModal")?.classList.add("hidden");
});

