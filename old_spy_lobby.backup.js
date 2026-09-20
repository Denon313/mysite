    function openSpyLobby() {

        if (!state.currentUser?.username) {
            toast("ابتدا وارد حساب کاربری شو.");
            return;
        }

        state.currentGame = {
            type: "spy-lobby",
            data: null
        };

        const content = $("#gameContent");

        if (!content) {
            return;
        }

        content.innerHTML = "";

        const header = document.createElement("div");

        header.style.textAlign = "center";
        header.style.padding = "25px 10px 15px";

        const icon = document.createElement("div");

        icon.style.fontSize = "54px";
        icon.textContent = "🕵️";

        const title = document.createElement("h2");

        title.textContent = "لابی جاسوس";
        title.style.marginTop = "12px";

        const description = document.createElement("p");

        description.textContent =
            "بازیکنان وارد می‌شوند؛ مدیر زمان شروع بازی را تعیین می‌کند.";

        description.style.marginTop = "8px";
        description.style.color = "var(--muted)";
        description.style.fontSize = "12px";

        header.appendChild(icon);
        header.appendChild(title);
        header.appendChild(description);

        content.appendChild(header);

        const lobby = document.createElement("div");

        lobby.id = "spyLobbyContent";

        lobby.innerHTML = `
            <div style="
                text-align:center;
                padding:20px;
                border-radius:18px;
                background:rgba(255,255,255,.04);
                border:1px solid rgba(255,255,255,.08);
            ">

                <div style="
                    font-size:28px;
                    font-weight:800;
                    margin-bottom:8px;
                " id="spyLobbyCount">
                    0 / 5
                </div>

                <div style="
                    color:var(--muted);
                    font-size:13px;
                    margin-bottom:20px;
                ">
                    بازیکنان حاضر در لابی
                </div>

                <div id="spyLobbyPlayers"
                     style="
                        display:flex;
                        flex-direction:column;
                        gap:10px;
                     ">
                </div>

                <div id="spyLobbyStartArea"
                     style="margin-top:20px;">
                </div>

            </div>
        `;

        content.appendChild(lobby);

        show($("#gameModal"));

        if (state.socket?.connected) {

            state.socket.emit(
