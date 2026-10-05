const API_URL = "https://YOUR-RAILWAY-URL.up.railway.app";

const menuContainer = document.getElementById("menuContainer");
const categoryBar = document.getElementById("categoryBar");

let menuData = [];
let observer = null;


/* =========================
   START
========================= */

document.addEventListener("DOMContentLoaded", () => {
    loadMenu();
});


/* =========================
   LOAD MENU
========================= */

async function loadMenu() {

    try {

        const response = await fetch(`${API_URL}/api/menu`, {
            method: "GET",
            headers: {
                "Accept": "application/json"
            }
        });

        if (!response.ok) {
            throw new Error("خطا در دریافت منو");
        }

        const data = await response.json();

        menuData = data;

        renderMenu(data);

    } catch (error) {

        console.error(error);

        showMessage(
            "منو در دسترس نیست",
            "لطفاً چند لحظه بعد دوباره تلاش کنید."
        );

    }

}


/* =========================
   RENDER MENU
========================= */

function renderMenu(data) {

    menuContainer.innerHTML = "";

    categoryBar.innerHTML = `
        <button
            class="category-item active"
            data-category="all"
        >
            همه
        </button>
    `;

    if (!data || !data.categories || data.categories.length === 0) {

        showMessage(
            "منویی ثبت نشده",
            "در حال حاضر محصولی برای نمایش وجود ندارد."
        );

        return;
    }


    data.categories.forEach(category => {

        const products = data.products.filter(
            product =>
                product.category_id === category.id &&
                product.active !== false
        );

        if (products.length === 0) {
            return;
        }


        /* =========================
           CATEGORY BUTTON
        ========================== */

        const categoryButton = document.createElement("button");

        categoryButton.className = "category-item";

        categoryButton.dataset.category = category.id;

        categoryButton.textContent = category.name;

        categoryButton.addEventListener("click", () => {

            const section = document.getElementById(
                `category-${category.id}`
            );

            if (!section) {
                return;
            }

            const top =
                section.getBoundingClientRect().top +
                window.scrollY -
                75;

            window.scrollTo({
                top: top,
                behavior: "smooth"
            });

        });

        categoryBar.appendChild(categoryButton);


        /* =========================
           CATEGORY SECTION
        ========================== */

        const section = document.createElement("section");

        section.className = "menu-category";

        section.id = `category-${category.id}`;

        section.dataset.category = category.id;


        const title = document.createElement("div");

        title.className = "category-title";

        title.innerHTML = `
            <h2>${escapeHTML(category.name)}</h2>
            <div class="category-title-line"></div>
        `;


        section.appendChild(title);


        /* =========================
           PRODUCTS
        ========================== */

        products.forEach(product => {

            const card = createProductCard(product);

            section.appendChild(card);

        });


        menuContainer.appendChild(section);

    });


    setupCategoryObserver();

}


/* =========================
   PRODUCT CARD
========================= */

function createProductCard(product) {

    const card = document.createElement("article");

    const available = product.available !== false;

    card.className =
        available
            ? "product-card"
            : "product-card unavailable";


    const statusText =
        available
            ? "موجود"
            : "ناموجود";


    const formattedPrice =
        formatPrice(product.price);


    card.innerHTML = `

        <div class="product-info">

            <div class="product-name">
                ${escapeHTML(product.name)}
            </div>

            ${
                product.description
                    ? `
                        <div class="product-description">
                            ${escapeHTML(product.description)}
                        </div>
                    `
                    : ""
            }

            <div class="product-price">

                ${formattedPrice}

                <span>
                    تومان
                </span>

            </div>

        </div>


        <div class="product-status">

            <span
                class="availability-dot ${
                    available
                        ? "available"
                        : "unavailable"
                }"
            ></span>

            <span>
                ${statusText}
            </span>

        </div>

    `;


    return card;

}


/* =========================
   CATEGORY OBSERVER
========================= */

function setupCategoryObserver() {

    if (observer) {
        observer.disconnect();
    }


    const sections =
        document.querySelectorAll(".menu-category");


    if (!sections.length) {
        return;
    }


    observer = new IntersectionObserver(

        entries => {

            const visibleSections =
                Array.from(entries)
                    .filter(entry => entry.isIntersecting);


            if (!visibleSections.length) {
                return;
            }


            visibleSections.sort(
                (a, b) =>
                    a.boundingClientRect.top -
                    b.boundingClientRect.top
            );


            const current =
                visibleSections[0];


            setActiveCategory(
                current.target.dataset.category
            );

        },

        {
            root: null,

            rootMargin:
                "-100px 0px -55% 0px",

            threshold: 0
        }

    );


    sections.forEach(section => {

        observer.observe(section);

    });

}


/* =========================
   ACTIVE CATEGORY
========================= */

function setActiveCategory(categoryId) {

    const buttons =
        document.querySelectorAll(
            ".category-item"
        );


    buttons.forEach(button => {

        button.classList.remove("active");

    });


    const activeButton =
        document.querySelector(
            `.category-item[data-category="${categoryId}"]`
        );


    if (!activeButton) {
        return;
    }


    activeButton.classList.add("active");


    activeButton.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
        inline: "center"
    });

}


/* =========================
   ALL BUTTON
========================= */

document.addEventListener(
    "click",
    event => {

        const button =
            event.target.closest(
                '.category-item[data-category="all"]'
            );


        if (!button) {
            return;
        }


        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });


        document
            .querySelectorAll(".category-item")
            .forEach(item => {
                item.classList.remove("active");
            });


        button.classList.add("active");

    }
);


/* =========================
   PRICE FORMAT
========================= */

function formatPrice(price) {

    const number =
        Number(price);


    if (!Number.isFinite(number)) {
        return "قیمت نامشخص";
    }


    return number.toLocaleString("fa-IR");

}


/* =========================
   HTML SECURITY
========================= */

function escapeHTML(value) {

    if (value === null || value === undefined) {
        return "";
    }


    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");

}


/* =========================
   MESSAGE
========================= */

function showMessage(title, text) {

    menuContainer.innerHTML = `

        <div class="menu-message">

            <strong>
                ${escapeHTML(title)}
            </strong>

            <span>
                ${escapeHTML(text)}
            </span>

        </div>

    `;

}
