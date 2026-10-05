const API_URL = "https://YOUR-RAILWAY-URL.up.railway.app";

let token = localStorage.getItem("rayka_admin_token");

const loginPage = document.getElementById("loginPage");
const adminPanel = document.getElementById("adminPanel");

const loginButton = document.getElementById("loginButton");
const logoutButton = document.getElementById("logoutButton");

const usernameInput = document.getElementById("username");
const passwordInput = document.getElementById("password");
const loginMessage = document.getElementById("loginMessage");

const categoryList = document.getElementById("categoryList");
const productList = document.getElementById("productList");

const categoryCount = document.getElementById("categoryCount");
const productCount = document.getElementById("productCount");
const availableCount = document.getElementById("availableCount");
const unavailableCount = document.getElementById("unavailableCount");

const addCategoryButton =
    document.getElementById("addCategoryButton");

const addProductButton =
    document.getElementById("addProductButton");


/* =========================
   START
========================= */

document.addEventListener("DOMContentLoaded", () => {

    if (token) {
        showAdminPanel();
        loadAdminData();
    } else {
        showLogin();
    }

});


/* =========================
   LOGIN
========================= */

loginButton.addEventListener("click", login);

passwordInput.addEventListener("keydown", event => {

    if (event.key === "Enter") {
        login();
    }

});


async function login() {

    const username =
        usernameInput.value.trim();

    const password =
        passwordInput.value;


    if (!username || !password) {

        loginMessage.textContent =
            "نام کاربری و رمز عبور را وارد کنید.";

        return;
    }


    loginButton.disabled = true;

    loginButton.textContent =
        "در حال ورود...";


    try {

        const response = await fetch(
            `${API_URL}/api/auth/login`,
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


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.message ||
                "ورود ناموفق بود."
            );

        }


        token = data.token;

        localStorage.setItem(
            "rayka_admin_token",
            token
        );


        loginMessage.textContent = "";

        showAdminPanel();

        await loadAdminData();


    } catch (error) {

        console.error(error);

        loginMessage.textContent =
            error.message ||
            "خطا در ورود.";

    } finally {

        loginButton.disabled = false;

        loginButton.textContent =
            "ورود به پنل";

    }

}


/* =========================
   LOGOUT
========================= */

logoutButton.addEventListener(
    "click",
    logout
);


function logout() {

    token = null;

    localStorage.removeItem(
        "rayka_admin_token"
    );

    showLogin();

}


/* =========================
   PAGE STATE
========================= */

function showLogin() {

    loginPage.classList.remove("hidden");

    adminPanel.classList.add("hidden");

}


function showAdminPanel() {

    loginPage.classList.add("hidden");

    adminPanel.classList.remove("hidden");

}


/* =========================
   LOAD ADMIN DATA
========================= */

async function loadAdminData() {

    try {

        const response =
            await adminRequest(
                "/api/admin/menu"
            );


        if (!response.ok) {

            if (response.status === 401) {

                logout();

                return;
            }

            throw new Error(
                "دریافت اطلاعات ناموفق بود."
            );

        }


        const data =
            await response.json();


        renderDashboard(data);

        renderCategories(data);

        renderProducts(data);


    } catch (error) {

        console.error(error);

        showAdminError(
            "ارتباط با سرور برقرار نشد."
        );

    }

}


/* =========================
   ADMIN REQUEST
========================= */

async function adminRequest(
    endpoint,
    options = {}
) {

    const headers = {
        ...(options.headers || {}),
        "Authorization": `Bearer ${token}`
    };


    return fetch(
        `${API_URL}${endpoint}`,
        {
            ...options,
            headers
        }
    );

}


/* =========================
   DASHBOARD
========================= */

function renderDashboard(data) {

    const categories =
        data.categories || [];

    const products =
        data.products || [];


    const activeProducts =
        products.filter(
            product =>
                product.active !== false
        );


    const availableProducts =
        activeProducts.filter(
            product =>
                product.available !== false
        );


    const unavailableProducts =
        activeProducts.filter(
            product =>
                product.available === false
        );


    categoryCount.textContent =
        categories.length;


    productCount.textContent =
        activeProducts.length;


    availableCount.textContent =
        availableProducts.length;


    unavailableCount.textContent =
        unavailableProducts.length;

}


/* =========================
   CATEGORIES
========================= */

function renderCategories(data) {

    const categories =
        data.categories || [];


    if (!categories.length) {

        categoryList.innerHTML = `
            <div class="menu-message">
                هنوز دسته‌ای ساخته نشده.
            </div>
        `;

        return;
    }


    categoryList.innerHTML = "";


    categories.forEach(category => {

        const item =
            document.createElement("div");


        item.className =
            "category-admin";


        item.innerHTML = `

            <span class="category-admin-name">
                ${escapeHTML(category.name)}
            </span>

            <div class="category-admin-actions">

                <button
                    class="small-button"
                    data-action="edit-category"
                    data-id="${category.id}"
                >
                    ویرایش
                </button>

                <button
                    class="small-button danger"
                    data-action="delete-category"
                    data-id="${category.id}"
                >
                    حذف
                </button>

            </div>
        `;


        categoryList.appendChild(item);

    });

}


/* =========================
   PRODUCTS
========================= */

function renderProducts(data) {

    const products =
        (data.products || [])
            .filter(
                product =>
                    product.active !== false
            );


    if (!products.length) {

        productList.innerHTML = `
            <div class="menu-message">
                هنوز محصولی ثبت نشده.
            </div>
        `;

        return;
    }


    productList.innerHTML = "";


    products.forEach(product => {

        const item =
            document.createElement("div");


        item.className =
            "category-admin";


        const status =
            product.available !== false
                ? "🟢 موجود"
                : "🔴 ناموجود";


        item.innerHTML = `

            <div>

                <div class="category-admin-name">
                    ${escapeHTML(product.name)}
                </div>

                <small
                    style="
                        color:#777;
                        font-size:9px;
                    "
                >
                    ${formatPrice(product.price)}
                    تومان
                    ·
                    ${status}
                </small>

            </div>


            <div class="category-admin-actions">

                <button
                    class="small-button"
                    data-action="edit-product"
                    data-id="${product.id}"
                >
                    ویرایش
                </button>

                <button
                    class="small-button"
                    data-action="toggle-product"
                    data-id="${product.id}"
                >
                    ${
                        product.available !== false
                            ? "ناموجود"
                            : "موجود"
                    }
                </button>

                <button
                    class="small-button danger"
                    data-action="delete-product"
                    data-id="${product.id}"
                >
                    حذف
                </button>

            </div>
        `;


        productList.appendChild(item);

    });

}


/* =========================
   ADD CATEGORY
========================= */

addCategoryButton.addEventListener(
    "click",
    async () => {

        const name =
            prompt("نام دسته جدید را وارد کنید:");


        if (!name || !name.trim()) {
            return;
        }


        try {

            const response =
                await adminRequest(
                    "/api/admin/categories",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify({
                            name: name.trim()
                        })
                    }
                );


            const data =
                await response.json();


            if (!response.ok) {

                throw new Error(
                    data.message ||
                    "ساخت دسته ناموفق بود."
                );

            }


            await loadAdminData();


        } catch (error) {

            alert(error.message);

        }

    }
);


/* =========================
   ADD PRODUCT
========================= */

addProductButton.addEventListener(
    "click",
    async () => {

        const name =
            prompt("نام محصول:");


        if (!name || !name.trim()) {
            return;
        }


        const price =
            prompt("قیمت محصول به تومان:");


        if (!price) {
            return;
        }


        const description =
            prompt(
                "توضیحات محصول:",
                ""
            );


        const categoryId =
            prompt(
                "شناسه دسته‌بندی محصول:"
            );


        if (!categoryId) {
            return;
        }


        try {

            const response =
                await adminRequest(
                    "/api/admin/products",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify({

                            name:
                                name.trim(),

                            price:
                                Number(price),

                            description:
                                description || "",

                            category_id:
                                Number(categoryId),

                            available:
                                true,

                            active:
                                true

                        })
                    }
                );


            const data =
                await response.json();


            if (!response.ok) {

                throw new Error(
                    data.message ||
                    "ساخت محصول ناموفق بود."
                );

            }


            await loadAdminData();


        } catch (error) {

            alert(error.message);

        }

    }
);


/* =========================
   CATEGORY ACTIONS
========================= */

categoryList.addEventListener(
    "click",
    async event => {

        const button =
            event.target.closest("button");


        if (!button) {
            return;
        }


        const action =
            button.dataset.action;


        const id =
            Number(button.dataset.id);


        if (action === "edit-category") {

            await editCategory(id);

        }


        if (action === "delete-category") {

            await deleteCategory(id);

        }

    }
);


/* =========================
   PRODUCT ACTIONS
========================= */

productList.addEventListener(
    "click",
    async event => {

        const button =
            event.target.closest("button");


        if (!button) {
            return;
        }


        const action =
            button.dataset.action;


        const id =
            Number(button.dataset.id);


        if (action === "edit-product") {

            await editProduct(id);

        }


        if (action === "toggle-product") {

            await toggleProduct(id);

        }


        if (action === "delete-product") {

            await deleteProduct(id);

        }

    }
);


/* =========================
   EDIT CATEGORY
========================= */

async function editCategory(id) {

    const name =
        prompt(
            "نام جدید دسته:"
        );


    if (!name || !name.trim()) {
        return;
    }


    try {

        const response =
            await adminRequest(
                `/api/admin/categories/${id}`,
                {
                    method: "PATCH",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        name: name.trim()
                    })
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.message ||
                "ویرایش ناموفق بود."
            );

        }


        await loadAdminData();


    } catch (error) {

        alert(error.message);

    }

}


/* =========================
   DELETE CATEGORY
========================= */

async function deleteCategory(id) {

    const confirmed =
        confirm(
            "این دسته حذف شود؟\nمحصولات آن نیز ممکن است تحت تأثیر قرار بگیرند."
        );


    if (!confirmed) {
        return;
    }


    try {

        const response =
            await adminRequest(
                `/api/admin/categories/${id}`,
                {
                    method: "DELETE"
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.message ||
                "حذف ناموفق بود."
            );

        }


        await loadAdminData();


    } catch (error) {

        alert(error.message);

    }

}


/* =========================
   EDIT PRODUCT
========================= */

async function editProduct(id) {

    const name =
        prompt("نام جدید محصول:");

    if (!name || !name.trim()) {
        return;
    }


    const price =
        prompt("قیمت جدید:");

    if (!price) {
        return;
    }


    const description =
        prompt(
            "توضیحات جدید:",
            ""
        );


    try {

        const response =
            await adminRequest(
                `/api/admin/products/${id}`,
                {
                    method: "PATCH",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        name:
                            name.trim(),

                        price:
                            Number(price),

                        description:
                            description || ""

                    })
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.message ||
                "ویرایش ناموفق بود."
            );

        }


        await loadAdminData();


    } catch (error) {

        alert(error.message);

    }

}


/* =========================
   TOGGLE PRODUCT
========================= */

async function toggleProduct(id) {

    try {

        const response =
            await adminRequest(
                `/api/admin/products/${id}/toggle`,
                {
                    method: "PATCH"
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.message ||
                "تغییر وضعیت ناموفق بود."
            );

        }


        await loadAdminData();


    } catch (error) {

        alert(error.message);

    }

}


/* =========================
   DELETE PRODUCT
========================= */

async function deleteProduct(id) {

    const confirmed =
        confirm(
            "این محصول حذف شود؟"
        );


    if (!confirmed) {
        return;
    }


    try {

        const response =
            await adminRequest(
                `/api/admin/products/${id}`,
                {
                    method: "DELETE"
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.message ||
                "حذف ناموفق بود."
            );

        }


        await loadAdminData();


    } catch (error) {

        alert(error.message);

    }

}


/* =========================
   ERROR
========================= */

function showAdminError(message) {

    categoryList.innerHTML = `
        <div class="menu-message">
            <strong>
                خطا
            </strong>

            ${escapeHTML(message)}
        </div>
    `;

}


/* =========================
   PRICE
========================= */

function formatPrice(price) {

    const number =
        Number(price);


    if (!Number.isFinite(number)) {
        return "0";
    }


    return number.toLocaleString("fa-IR");

}


/* =========================
   SECURITY
========================= */

function escapeHTML(value) {

    if (
        value === null ||
        value === undefined
    ) {
        return "";
    }


    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");

}
