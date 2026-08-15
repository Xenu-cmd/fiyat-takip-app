import streamlit as st
import requests
import time
import re
from urllib.parse import urlparse


# =========================================================
# SAYFA
# =========================================================

st.set_page_config(
    page_title="Akıllı Fiyat Karşılaştırma",
    page_icon="🔎",
    layout="wide"
)


# =========================================================
# TASARIM
# =========================================================

st.markdown("""
<style>

.main-title {
    text-align: center;
    font-size: 40px;
    font-weight: 900;
    color: #111827;
    margin-bottom: 5px;
}

.subtitle {
    text-align: center;
    color: #6b7280;
    font-size: 17px;
    margin-bottom: 30px;
}

.best-card {
    background: linear-gradient(135deg, #ecfdf5, #f0fdf4);
    border: 2px solid #22c55e;
    border-radius: 20px;
    padding: 25px;
    margin: 20px 0 25px 0;
}

.best-title {
    font-size: 18px;
    font-weight: 900;
    color: #166534;
}

.best-product {
    font-size: 25px;
    font-weight: 900;
    color: #111827;
    margin-top: 8px;
}

.best-price {
    font-size: 44px;
    font-weight: 900;
    color: #15803d;
    margin-top: 8px;
}

.offer-card {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 15px;
    padding: 18px;
    margin-bottom: 8px;
    box-shadow: 0 3px 12px rgba(0,0,0,0.04);
}

.new-card {
    border-left: 6px solid #22c55e;
}

.used-card {
    border-left: 6px solid #f97316;
}

.refurb-card {
    border-left: 6px solid #3b82f6;
}

.offer-title {
    font-size: 18px;
    font-weight: 800;
    color: #111827;
}

.offer-price {
    font-size: 28px;
    font-weight: 900;
    color: #111827;
    margin-top: 6px;
}

.offer-store {
    color: #2563eb;
    font-weight: 800;
    margin-top: 4px;
}

.offer-description {
    color: #6b7280;
    font-size: 14px;
    margin-top: 8px;
}

.summary-card {
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 15px;
    padding: 18px;
    text-align: center;
}

.summary-number {
    font-size: 28px;
    font-weight: 900;
}

.summary-label {
    color: #6b7280;
    font-weight: 700;
}

.info-box {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    padding: 15px;
    border-radius: 12px;
    margin-bottom: 15px;
}

.warning-box {
    background: #fff7ed;
    border: 1px solid #fed7aa;
    padding: 15px;
    border-radius: 12px;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# API
# =========================================================

BASE_URL = "https://www.socialcrawl.dev"

try:
    API_KEY = st.secrets["SOCIALCRAWL_API_KEY"]
except Exception:
    API_KEY = ""


HEADERS = {
    "Accept": "application/json"
}

if API_KEY:
    HEADERS["x-api-key"] = API_KEY


# =========================================================
# BAŞLIK
# =========================================================

st.markdown(
    '<div class="main-title">🔎 Akıllı Fiyat Karşılaştırma</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Sıfır, ikinci el ve yenilenmiş ürünleri karşılaştır'
    '</div>',
    unsafe_allow_html=True
)


# =========================================================
# ÜRÜN ARAMA
# =========================================================

product = st.text_input(
    "🔎 Ürün adı",
    placeholder="Örn: Grundig Club BT Hoparlör"
)

search_button = st.button(
    "🔍 Fiyatları Bul",
    type="primary",
    use_container_width=True
)


# =========================================================
# METİN NORMALİZE
# =========================================================

def normalize(text):

    if not text:
        return ""

    text = str(text).lower()

    replacements = {
        "ç": "c",
        "ğ": "g",
        "ı": "i",
        "ö": "o",
        "ş": "s",
        "ü": "u"
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(
        r"[^a-z0-9\s]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =========================================================
# ÜRÜN KELİMELERİ
# =========================================================

def get_product_words(product):

    ignored = {
        "ve",
        "ile",
        "icin",
        "bir",
        "the",
        "a",
        "an",
        "ürün",
        "urun"
    }

    words = []

    for word in normalize(product).split():

        if len(word) < 2:
            continue

        if word in ignored:
            continue

        words.append(word)

    return words


# =========================================================
# ÜRÜN EŞLEŞMESİ
# =========================================================

def is_relevant(
    searched_product,
    title,
    description=""
):

    wanted = get_product_words(
        searched_product
    )

    text = normalize(
        (title or "") + " " + (description or "")
    )

    if not wanted:
        return False

    # Aranan kelimelerin hepsi başlıkta
    # bulunuyorsa güçlü eşleşme
    found = 0

    for word in wanted:

        if word in text:
            found += 1

    # Çok kelimeli aramada hepsi gerekli
    if len(wanted) >= 2:

        if found < len(wanted):
            return False

    else:

        if found == 0:
            return False

    # -----------------------------------------------------
    # YANLIŞ ÜRÜN FİLTRESİ
    # -----------------------------------------------------

    searched = normalize(
        searched_product
    )

    bad_words = [
        "kulaklik",
        "kulak ici",
        "kulakici",
        "headphone",
        "headset",
        "mikrofon",
        "microphone",
        "kablo",
        "kilif",
        "case",
        "canta",
        "kumanda",
        "remote",
        "yedek parca",
        "parca"
    ]

    for bad in bad_words:

        if bad in text and bad not in searched:
            return False

    return True


# =========================================================
# DOMAIN
# =========================================================

def get_domain(url):

    if not url:
        return "Bilinmiyor"

    try:

        return urlparse(
            url
        ).netloc.replace(
            "www.",
            ""
        )

    except Exception:

        return "Bilinmiyor"


# =========================================================
# GOOGLE SHOPPING API
# =========================================================

def shopping_search(
    query,
    attempts=2
):

    endpoint = (
        BASE_URL
        + "/v1/google_shopping/product-search"
    )

    params = {
        "query": query,
        "country": "Turkey",
        "language": "tr",
        "depth": 10
    }

    for attempt in range(attempts):

        try:

            response = requests.get(
                endpoint,
                params=params,
                headers=HEADERS,
                timeout=120
            )

        except requests.exceptions.Timeout:

            if attempt < attempts - 1:

                time.sleep(4)
                continue

            return []

        except requests.exceptions.RequestException:

            if attempt < attempts - 1:

                time.sleep(4)
                continue

            return []

        # -------------------------------------------------
        # 504
        # -------------------------------------------------

        if response.status_code == 504:

            if attempt < attempts - 1:

                time.sleep(5)
                continue

            return []

        # -------------------------------------------------
        # Diğer HTTP hataları
        # -------------------------------------------------

        if response.status_code != 200:

            return []

        try:

            data = response.json()

        except Exception:

            return []

        if not data.get("success"):

            return []

        return (
            data
            .get("data", {})
            .get("items", [])
        )

    return []


# =========================================================
# SONUÇLARI ÜRÜNE DÖNÜŞTÜR
# =========================================================

def parse_products(
    items,
    searched_product,
    condition
):

    results = []

    for item in items:

        product_data = item.get(
            "product",
            {}
        )

        title = product_data.get(
            "title",
            ""
        )

        description = product_data.get(
            "description",
            ""
        )

        if not is_relevant(
            searched_product,
            title,
            description
        ):
            continue

        price_data = product_data.get(
            "price",
            {}
        )

        if not isinstance(
            price_data,
            dict
        ):
            continue

        price = price_data.get(
            "current"
        )

        if price is None:
            continue

        try:

            price = float(price)

        except Exception:

            continue

        currency = str(
            price_data.get(
                "currency",
                ""
            )
        ).upper()

        # Türkiye dışı fiyatları alma
        if currency not in [
            "TRY",
            "TL"
        ]:
            continue

        seller = product_data.get(
            "seller",
            ""
        )

        if not seller:
            seller = "Satıcı belirtilmemiş"

        url = product_data.get(
            "url",
            ""
        )

        image_urls = product_data.get(
            "image_urls",
            []
        )

        image = ""

        if isinstance(
            image_urls,
            list
        ) and image_urls:

            image = image_urls[0]

        results.append({

            "title": title,

            "description": description or "",

            "price": price,

            "seller": str(seller),

            "url": url,

            "domain": get_domain(url),

            "condition": condition,

            "image": image

        })

    return results


# =========================================================
# TEKRARLARI TEMİZLE
# =========================================================

def remove_duplicates(results):

    unique = {}

    for item in results:

        key = (
            normalize(
                item["seller"]
            ),
            round(
                item["price"],
                2
            ),
            normalize(
                item["title"]
            )
        )

        if key not in unique:

            unique[key] = item

    final = list(
        unique.values()
    )

    final.sort(
        key=lambda x: x["price"]
    )

    return final


# =========================================================
# ANA SIFIR ÜRÜN ARAMASI
# =========================================================

def search_new(product):

    # İlk sorgu en önemli olan.
    queries = [

        product,

        f'"{product}"',

        f'{product} fiyat',

    ]

    all_results = []

    for query in queries:

        items = shopping_search(
            query
        )

        parsed = parse_products(
            items,
            product,
            "Sıfır"
        )

        all_results.extend(
            parsed
        )

        # Sonuç bulduysak diğer ağır
        # sorgulara gereksiz yüklenme
        if len(all_results) >= 10:

            break

        time.sleep(1)

    return remove_duplicates(
        all_results
    )


# =========================================================
# İKİNCİ EL
# =========================================================

def search_used(product):

    queries = [

        f'{product} ikinci el',

        f'{product} 2 el'

    ]

    all_results = []

    for query in queries:

        items = shopping_search(
            query,
            attempts=1
        )

        parsed = parse_products(
            items,
            product,
            "İkinci El"
        )

        # Google Shopping bazen ikinci el
        # sonucunu doğrudan belirtmez.
        # Bu yüzden yalnızca başlık/snippet
        # içinde ikinci el işareti varsa alıyoruz.

        for item in parsed:

            text = normalize(
                item["title"]
                + " "
                + item["description"]
            )

            used_words = [
                "ikinci el",
                "2 el",
                "2.el",
                "kullanilmis",
                "sahibinden",
                "letgo"
            ]

            if any(
                word in text
                for word in used_words
            ):

                all_results.append(
                    item
                )

        time.sleep(1)

    return remove_duplicates(
        all_results
    )


# =========================================================
# YENİLENMİŞ
# =========================================================

def search_refurbished(product):

    queries = [

        f'{product} yenilenmiş',

        f'{product} refurbished'

    ]

    all_results = []

    for query in queries:

        items = shopping_search(
            query,
            attempts=1
        )

        parsed = parse_products(
            items,
            product,
            "Yenilenmiş"
        )

        for item in parsed:

            text = normalize(
                item["title"]
                + " "
                + item["description"]
            )

            refurb_words = [
                "yenilenmis",
                "refurbished",
                "renewed"
            ]

            if any(
                word in text
                for word in refurb_words
            ):

                all_results.append(
                    item
                )

        time.sleep(1)

    return remove_duplicates(
        all_results
    )


# =========================================================
# EN UCUZ KART
# =========================================================

def show_best(results):

    if not results:
        return

    cheapest = min(
        results,
        key=lambda x: x["price"]
    )

    if cheapest["condition"] == "Sıfır":

        icon = "📦"

    elif cheapest["condition"] == "İkinci El":

        icon = "🟠"

    else:

        icon = "🔵"

    st.markdown(
        f"""
        <div class="best-card">

            <div class="best-title">
                🏆 En Ucuz Fiyat
            </div>

            <div class="best-product">
                {cheapest["title"]}
            </div>

            <div class="best-price">
                {cheapest["price"]:,.2f} TL
            </div>

            <div style="
                font-size:17px;
                margin-top:8px;
            ">
                🏪 {cheapest["seller"]}
            </div>

            <div style="
                margin-top:6px;
                font-weight:800;
            ">
                {icon} {cheapest["condition"]}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    if cheapest["url"]:

        st.link_button(
            "🛒 En Ucuz Satıcıya Git",
            cheapest["url"]
        )


# =========================================================
# SONUÇLARI GÖSTER
# =========================================================

def show_results(
    title,
    icon,
    results,
    css_class
):

    st.subheader(
        f"{icon} {title}"
    )

    if not results:

        st.info(
            f"{title} için uygun fiyat bulunamadı."
        )

        return

    for index, item in enumerate(
        results,
        start=1
    ):

        st.markdown(
            f"""
            <div class="offer-card {css_class}">

                <div class="offer-title">
                    {index}. {item["title"]}
                </div>

                <div class="offer-price">
                    {item["price"]:,.2f} TL
                </div>

                <div class="offer-store">
                    🏪 {item["seller"]}
                </div>

                <div class="offer-description">
                    {item["condition"]}
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )

        if item["url"]:

            st.link_button(
                "🛒 Satıcıya Git",
                item["url"]
            )


# =========================================================
# ÇALIŞTIR
# =========================================================

if search_button:

    # -----------------------------------------------------
    # API KEY
    # -----------------------------------------------------

    if not API_KEY:

        st.error(
            "❌ API anahtarı bulunamadı."
        )

        st.info(
            "Streamlit Secrets bölümüne "
            "SOCIALCRAWL_API_KEY eklemelisin."
        )

        st.code(
            'SOCIALCRAWL_API_KEY = "sc_..."'
        )

        st.stop()

    # -----------------------------------------------------
    # ÜRÜN KONTROL
    # -----------------------------------------------------

    if not product.strip():

        st.warning(
            "Önce bir ürün adı yaz."
        )

        st.stop()

    product = product.strip()

    # -----------------------------------------------------
    # ARAMA
    # -----------------------------------------------------

    st.info(
        f"🔎 **{product}** aranıyor..."
    )

    # -----------------------------------------------------
    # SIFIR
    # -----------------------------------------------------

    with st.spinner(
        "🟢 Sıfır ürünler aranıyor..."
    ):

        new_results = search_new(
            product
        )

    # -----------------------------------------------------
    # İKİNCİ EL
    # -----------------------------------------------------

    with st.spinner(
        "🟠 İkinci el ürünler kontrol ediliyor..."
    ):

        used_results = search_used(
            product
        )

    # -----------------------------------------------------
    # YENİLENMİŞ
    # -----------------------------------------------------

    with st.spinner(
        "🔵 Yenilenmiş ürünler kontrol ediliyor..."
    ):

        refurbished_results = search_refurbished(
            product
        )

    # -----------------------------------------------------
    # TÜM SONUÇLAR
    # -----------------------------------------------------

    all_results = remove_duplicates(
        new_results
        + used_results
        + refurbished_results
    )

    # -----------------------------------------------------
    # HİÇBİR ŞEY YOK
    # -----------------------------------------------------

    if not all_results:

        st.error(
            f'"{product}" için uygun fiyat bulunamadı.'
        )

        st.warning(
            "API geçici olarak cevap vermemiş veya "
            "Google Shopping bu ürün için sonuç döndürmemiş olabilir."
        )

        st.stop()

    # -----------------------------------------------------
    # EN UCUZ
    # -----------------------------------------------------

    show_best(
        all_results
    )

    # -----------------------------------------------------
    # ÜRÜN ÖZETİ
    # -----------------------------------------------------

    st.divider()

    st.subheader(
        "📊 Fiyat Özeti"
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.markdown(
            f"""
            <div class="summary-card">
                <div class="summary-number">
                    {len(new_results)}
                </div>
                <div class="summary-label">
                    🟢 Sıfır
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:

        st.markdown(
            f"""
            <div class="summary-card">
                <div class="summary-number">
                    {len(used_results)}
                </div>
                <div class="summary-label">
                    🟠 İkinci El
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:

        st.markdown(
            f"""
            <div class="summary-card">
                <div class="summary-number">
                    {len(refurbished_results)}
                </div>
                <div class="summary-label">
                    🔵 Yenilenmiş
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col4:

        st.markdown(
            f"""
            <div class="summary-card">
                <div class="summary-number">
                    {len(all_results)}
                </div>
                <div class="summary-label">
                    💰 Toplam
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # -----------------------------------------------------
    # TÜM FİYATLAR
    # -----------------------------------------------------

    st.divider()

    show_results(
        "Tüm Fiyatlar",
        "💰",
        all_results,
        "new-card"
    )

    # -----------------------------------------------------
    # SIFIR
    # -----------------------------------------------------

    st.divider()

    show_results(
        "Sıfır Ürünler",
        "🟢",
        new_results,
        "new-card"
    )

    # -----------------------------------------------------
    # İKİNCİ EL
    # -----------------------------------------------------

    st.divider()

    show_results(
        "İkinci El",
        "🟠",
        used_results,
        "used-card"
    )

    # -----------------------------------------------------
    # YENİLENMİŞ
    # -----------------------------------------------------

    st.divider()

    show_results(
        "Yenilenmiş",
        "🔵",
        refurbished_results,
        "refurb-card"
    )

    # -----------------------------------------------------
    # FİYAT ARALIĞI
    # -----------------------------------------------------

    prices = [
        item["price"]
        for item in all_results
    ]

    if len(prices) >= 2:

        lowest = min(prices)
        highest = max(prices)

        difference = highest - lowest

        st.divider()

        st.subheader(
            "📈 Fiyat Aralığı"
        )

        c1, c2, c3 = st.columns(3)

        with c1:

            st.metric(
                "En ucuz",
                f"{lowest:,.2f} TL"
            )

        with c2:

            st.metric(
                "En pahalı",
                f"{highest:,.2f} TL"
            )

        with c3:

            st.metric(
                "Fiyat farkı",
                f"{difference:,.2f} TL"
            )
