(function(){const t=document.createElement("link").relList;if(t&&t.supports&&t.supports("modulepreload"))return;for(const n of document.querySelectorAll('link[rel="modulepreload"]'))d(n);new MutationObserver(n=>{for(const s of n)if(s.type==="childList")for(const l of s.addedNodes)l.tagName==="LINK"&&l.rel==="modulepreload"&&d(l)}).observe(document,{childList:!0,subtree:!0});function a(n){const s={};return n.integrity&&(s.integrity=n.integrity),n.referrerPolicy&&(s.referrerPolicy=n.referrerPolicy),n.crossOrigin==="use-credentials"?s.credentials="include":n.crossOrigin==="anonymous"?s.credentials="omit":s.credentials="same-origin",s}function d(n){if(n.ep)return;n.ep=!0;const s=a(n);fetch(n.href,s)}})();const E="rayka_menu_products_v2",q="rayka_menu_logs_v2",L=[{id:crypto.randomUUID(),name:"پیتزا پپرونی",category:"فست‌فود",section:"پیتزا",description:"سوسیس پپرونی تند، پنیر پیتزا، فلفل دلمه، قارچ و سس مخصوص رایکا",price:285e3,stock:12,available:!0,image:""},{id:crypto.randomUUID(),name:"چیکن آلفردو",category:"غذای اصلی",section:"پاستا",description:"پاستا، فیله مرغ، سس آلفردو، قارچ و پنیر پارمزان",price:32e4,stock:8,available:!0,image:""},{id:crypto.randomUUID(),name:"کباب مخصوص رایکا",category:"کباب",section:"کباب",description:"کباب مخصوص سرآشپز، برنج ایرانی، گوجه کبابی و کره",price:42e4,stock:5,available:!0,image:""},{id:crypto.randomUUID(),name:"برگر ویژه رایکا",category:"فست‌فود",section:"برگر",description:"گوشت گریل‌شده، پنیر چدار، قارچ، کاهو، گوجه و سس مخصوص",price:31e4,stock:0,available:!1,image:""},{id:crypto.randomUUID(),name:"نوشابه",category:"نوشیدنی",section:"نوشیدنی",description:"نوشیدنی خنک",price:45e3,stock:24,available:!0,image:""},{id:crypto.randomUUID(),name:"آب معدنی",category:"نوشیدنی",section:"نوشیدنی",description:"آب معدنی خنک",price:25e3,stock:30,available:!0,image:""}],U=["همه","غذای اصلی","فست‌فود","کباب","نوشیدنی","پاستا","برگر","پیتزا"];let c=M(),y=C(),g="همه",h=!1;const D=document.querySelector("#app");function M(){try{const e=localStorage.getItem(E);return e?JSON.parse(e):L}catch{return L}}function k(){localStorage.setItem(E,JSON.stringify(c))}function C(){try{return JSON.parse(localStorage.getItem(q)||"[]")}catch{return[]}}function K(){localStorage.setItem(q,JSON.stringify(y))}function v(e,t,a=""){y.unshift({id:crypto.randomUUID(),action:e,productName:t,details:a,time:new Date().toLocaleString("fa-IR")}),y=y.slice(0,300),K()}function x(e){return new Intl.NumberFormat("fa-IR").format(Number(e||0))+" تومان"}function u(e=""){return String(e).replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;")}function I(){return`
    <div class="image-fallback">
      <span>R</span>
      <small>RAYKA</small>
    </div>
  `}function F(e){return e.image?`
    <img
      src="${e.image}"
      alt="${u(e.name)}"
      class="product-image"
      loading="lazy"
      onerror="this.style.display='none';this.nextElementSibling.style.display='flex'"
    >
    <div class="image-fallback image-fallback-hidden">
      <span>R</span>
      <small>RAYKA</small>
    </div>
  `:I()}function T(){return g==="همه"?c:c.filter(e=>e.category===g||e.section===g)}function Y(e){const t=e.available&&e.stock>0;return`
    <article class="product-card ${t?"":"is-unavailable"}">

      <div class="product-media">
        ${F(e)}

        <div class="availability-badge ${t?"available":"unavailable"}">
          <span class="status-dot"></span>
          <span>${t?"موجود":"ناموجود"}</span>
        </div>

        <span class="product-section-badge">
          ${u(e.section||e.category)}
        </span>
      </div>

      <div class="product-info">

        <h3>${u(e.name)}</h3>

        <p class="product-description">
          ${u(e.description)}
        </p>

        <div class="product-meta">
          <strong class="product-price">${x(e.price)}</strong>

          <span class="stock-label ${e.stock<=2?"low":""}">
            ${t?`موجودی: ${new Intl.NumberFormat("fa-IR").format(e.stock)}`:"اتمام موجودی"}
          </span>
        </div>

        ${h?`
              <div class="card-admin-actions">
                <button class="small-btn edit-product" data-id="${e.id}">
                  ویرایش
                </button>

                <button
                  class="small-btn stock-minus"
                  data-id="${e.id}"
                  ${e.stock<=0?"disabled":""}
                >−</button>

                <button class="small-btn stock-plus" data-id="${e.id}">
                  +
                </button>
              </div>
            `:""}

      </div>
    </article>
  `}function A(){const e=document.querySelector("#categories");e.innerHTML=U.map(t=>`
    <button
      type="button"
      class="category-btn ${g===t?"active":""}"
      data-category="${t}"
    >
      ${t}
    </button>
  `).join(""),e.querySelectorAll(".category-btn").forEach(t=>{t.addEventListener("click",()=>{g=t.dataset.category,A(),m()})})}function m(){const e=document.querySelector("#products"),t=T();e.innerHTML=t.length?t.map(Y).join(""):`
      <div class="empty-state">
        <div>🍽️</div>
        <h3>محصولی پیدا نشد</h3>
        <p>در این دسته هنوز محصولی ثبت نشده است.</p>
      </div>
    `,_()}function _(){document.querySelectorAll(".edit-product").forEach(e=>{e.addEventListener("click",()=>{const t=c.find(a=>a.id===e.dataset.id);t&&H(t)})}),document.querySelectorAll(".stock-plus").forEach(e=>{e.addEventListener("click",()=>{const t=c.find(a=>a.id===e.dataset.id);t&&(t.stock++,t.stock>0&&(t.available=!0),v("افزایش موجودی",t.name,`موجودی جدید: ${t.stock}`),k(),m())})}),document.querySelectorAll(".stock-minus").forEach(e=>{e.addEventListener("click",()=>{const t=c.find(a=>a.id===e.dataset.id);!t||t.stock<=0||(t.stock--,t.stock===0&&(t.available=!1),v("کاهش موجودی",t.name,`موجودی جدید: ${t.stock}`),k(),m())})})}function H(e=null){const t=!!e,a=document.createElement("div");a.className="modal-overlay",a.innerHTML=`
    <div class="modal product-modal">

      <div class="modal-header">
        <div>
          <span class="modal-eyebrow">
            ${t?"EDIT PRODUCT":"NEW PRODUCT"}
          </span>

          <h2>
            ${t?"ویرایش محصول":"افزودن محصول"}
          </h2>
        </div>

        <button class="modal-close" type="button">×</button>
      </div>

      <form id="product-form">

        <label>
          نام محصول
          <input
            name="name"
            required
            maxlength="80"
            value="${t?u(e.name):""}"
            placeholder="مثلاً پاستای مخصوص رایکا"
          >
        </label>

        <div class="form-grid">

          <label>
            دسته‌بندی
            <select name="category">
              ${U.filter(o=>o!=="همه").map(o=>`
                  <option
                    value="${o}"
                    ${t&&e.category===o?"selected":""}
                  >${o}</option>
                `).join("")}
            </select>
          </label>

          <label>
            بخش
            <input
              name="section"
              maxlength="50"
              value="${t?u(e.section):""}"
              placeholder="مثلاً پاستا"
            >
          </label>

        </div>

        <label>
          توضیحات
          <textarea
            name="description"
            maxlength="220"
            rows="4"
            placeholder="مواد اولیه و توضیح کوتاه محصول..."
          >${t?u(e.description):""}</textarea>
        </label>

        <div class="form-grid">

          <label>
            قیمت
            <input
              name="price"
              type="number"
              min="0"
              step="1000"
              required
              value="${t?e.price:""}"
              placeholder="قیمت به تومان"
            >
          </label>

          <label>
            موجودی
            <input
              name="stock"
              type="number"
              min="0"
              step="1"
              required
              value="${t?e.stock:"0"}"
            >
          </label>

        </div>

        <label class="switch-row">
          <span>
            <strong>وضعیت محصول</strong>
            <small>اگر خاموش باشد محصول ناموجود نمایش داده می‌شود.</small>
          </span>

          <input
            name="available"
            type="checkbox"
            ${t?e.available?"checked":"":"checked"}
          >

          <span class="switch"></span>
        </label>

        <label class="upload-box">
          <input id="product-image-input" type="file" accept="image/jpeg,image/png,image/webp,image/avif">

          <span class="upload-icon">🖼️</span>
          <strong>انتخاب عکس محصول</strong>
          <small>JPG / PNG / WEBP / AVIF — حداکثر 3MB</small>
        </label>

        <div id="image-preview" class="image-preview">
          ${t&&e.image?`<img src="${e.image}" alt="preview">`:I()}
        </div>

        <div class="modal-actions">

          ${t?`
                <button
                  type="button"
                  class="danger-btn"
                  id="delete-product"
                >
                  حذف محصول
                </button>
              `:""}

          <button type="button" class="secondary-btn modal-cancel">
            انصراف
          </button>

          <button type="submit" class="primary-btn">
            ${t?"ذخیره تغییرات":"افزودن محصول"}
          </button>

        </div>

      </form>
    </div>
  `,document.body.appendChild(a);const d=()=>a.remove();a.querySelector(".modal-close").onclick=d,a.querySelector(".modal-cancel").onclick=d;const n=a.querySelector("#product-image-input"),s=a.querySelector("#image-preview");let l=t?e.image:"";n.addEventListener("change",()=>{const o=n.files?.[0];if(!o)return;if(o.size>3*1024*1024){alert("حجم عکس نباید بیشتر از 3 مگابایت باشد."),n.value="";return}if(!["image/jpeg","image/png","image/webp","image/avif"].includes(o.type)){alert("فرمت عکس مجاز نیست."),n.value="";return}const r=new FileReader;r.onload=p=>{l=p.target.result,s.innerHTML=`
        <img src="${l}" alt="preview">
      `},r.readAsDataURL(o)}),a.querySelector("#product-form").addEventListener("submit",o=>{o.preventDefault();const i=new FormData(o.currentTarget),r=String(i.get("name")||"").trim(),p=String(i.get("category")||"").trim(),$=String(i.get("section")||"").trim()||p,w=String(i.get("description")||"").trim(),f=Number(i.get("price")),b=Math.max(0,Number(i.get("stock"))),O=i.get("available")==="on";if(!r){alert("نام محصول را وارد کن.");return}if(!Number.isFinite(f)||f<0){alert("قیمت محصول صحیح نیست.");return}if(!Number.isFinite(b)||b<0){alert("موجودی محصول صحیح نیست.");return}const R=O&&b>0;if(t)Object.assign(e,{name:r,category:p,section:$,description:w,price:f,stock:b,available:R,image:l}),v("ویرایش محصول",r,"اطلاعات محصول ویرایش شد.");else{const P={id:crypto.randomUUID(),name:r,category:p,section:$,description:w,price:f,stock:b,available:R,image:l};c.push(P),v("افزودن محصول",r,"محصول جدید ثبت شد.")}k(),A(),m(),d()});const S=a.querySelector("#delete-product");S&&(S.onclick=()=>{confirm(`آیا مطمئنی «${e.name}» حذف شود؟`)&&(c=c.filter(i=>i.id!==e.id),v("حذف محصول",e.name,"محصول حذف شد."),k(),A(),m(),d())})}function j(){const e=document.createElement("div");e.className="modal-overlay",e.innerHTML=`
    <div class="modal about-modal">

      <button class="modal-close about-close" type="button">×</button>

      <div class="about-logo">R</div>

      <span class="modal-eyebrow">ABOUT RAYKA</span>

      <h2>درباره رایکا</h2>

      <p>
        رایکا با عشق آماده می‌شود تا تجربه‌ای متفاوت،
        خوش‌طعم و به‌یادماندنی برای شما بسازد.
      </p>

      <div class="about-line"></div>

      <span>RAYKA RESTAURANT</span>

    </div>
  `,document.body.appendChild(e),e.querySelector(".modal-close").onclick=()=>e.remove()}function B(){D.innerHTML=`
    <main class="rayka-shell">

      <section class="welcome-screen" id="welcome-screen">

        <button
          class="welcome-close"
          id="welcome-close"
          type="button"
          aria-label="بستن"
        >
          ×
        </button>

        <div class="welcome-glow"></div>

        <div class="welcome-content">

          <div class="welcome-mark">
            <span>R</span>
          </div>

          <span class="welcome-eyebrow">
            RAYKA RESTAURANT
          </span>

          <h1>به رایکا خوش آمدید</h1>

          <p>
            خوشحالیم که ما را انتخاب کردید ❤️
          </p>

        </div>

      </section>

      <section class="menu-screen">

        <header class="menu-header">

          <div class="brand-block">

            <span class="eyebrow">
              RAYKA RESTAURANT
            </span>

            <h1>منوی رایکا</h1>

            <p>
              طعم خوب، حال خوب.
            </p>

          </div>

          <button
            class="admin-button"
            id="admin-button"
            type="button"
          >
            <span>⚙</span>
            مدیریت
          </button>

        </header>

        <section class="category-area">

          <div class="section-heading">
            <span>MENU</span>
            <h2>انتخاب کن، لذت ببر</h2>
          </div>

          <nav
            class="categories"
            id="categories"
            aria-label="دسته‌بندی محصولات"
          ></nav>

        </section>

        <section class="products-section">

          <div class="products-heading">

            <div>
              <span class="heading-kicker">RAYKA SPECIAL</span>
              <h2>پیشنهادهای رایکا</h2>
            </div>

            <span class="product-count" id="product-count"></span>

          </div>

          <div
            class="products-grid"
            id="products"
          ></div>

        </section>

        <section class="about-section">

          <div class="about-card">

            <span class="about-kicker">RAYKA</span>

            <h2>یک تجربه متفاوت</h2>

            <p>
              جایی برای غذاهای خوش‌طعم، فضای خوب
              و لحظه‌هایی که ارزش به خاطر سپردن دارند.
            </p>

            <button
              type="button"
              id="about-button"
            >
              درباره ما
              <span>←</span>
            </button>

          </div>

        </section>

        <footer class="menu-footer">

          <span>RAYKA RESTAURANT</span>

          <small>
            ساخته شده با عشق ❤️
          </small>

        </footer>

      </section>

    </main>
  `,document.querySelector("#welcome-close").onclick=()=>{document.querySelector("#welcome-screen")?.remove()},document.querySelector("#admin-button").onclick=()=>{h=!h,document.querySelector("#admin-button").classList.toggle("active",h),m()},document.querySelector("#about-button").onclick=j,A(),m(),N(),setTimeout(()=>{document.querySelector("#welcome-screen")?.classList.add("hide")},3e3)}function N(){const e=document.querySelector("#product-count");if(!e)return;const t=T().length;e.textContent=`${new Intl.NumberFormat("fa-IR").format(t)} محصول`}B();const G=new MutationObserver(()=>{N()});G.observe(document.querySelector("#products"),{childList:!0});
