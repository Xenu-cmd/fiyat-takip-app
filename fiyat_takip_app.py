import streamlit as st
import requests
import re
import time
from bs4 import BeautifulSoup
from urllib.parse import quote, urljoin


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
    text-align:center;
    font-size:40px;
    font-weight:900;
    color:#111827;
}

.subtitle {
    text-align:center;
    color:#6b7280;
    margin-bottom:30px;
}

.best-card {
    background:linear-gradient(135deg,#ecfdf5,#f0fdf4);
    border:2px solid #22c55e;
    border-radius:20px;
    padding:25px;
    margin:20px 0;
}

.best-title {
    font-size:18px;
    font-weight:900;
    color:#166534;
}

.best-product {
    font-size:25px;
    font-weight:900;
    margin-top:8px;
}

.best-price {
    font-size:44px;
    font-weight:900;
    color:#15803d;
    margin-top:8px;
}

.offer {
    background:white;
    border:1px solid #e5e7eb;
    border-radius:15px;
    padding:18px;
    margin-bottom:10px;
    box-shadow:0 3px 12px rgba(0,0,0,.04);
}

.new {
    border-left:6px solid #22c55e;
}

.used {
    border-left:6px solid #f97316;
}

.refurb {
    border-left:6px solid #3b82f6;
}

.offer-title {
    font-size:18px;
    font-weight:800;
}

.offer-price {
    font-size:28px;
    font-weight:900;
    margin-top:5px;
}

.offer-store {
    color:#2563eb;
    font-weight:800;
    margin-top:5px;
}

.offer-condition {
    color:#6b7280;
    margin-top:5px;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# API AYARLARI
# =========================================================

try:
    API_KEY = st.secrets["SOCIALCRAWL_API_KEY"]
except:
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
    'Sıfır, ikinci el ve yenilenmiş ürünleri tek yerde karşılaştır'
    '</div>',
    unsafe_allow_html=True
)


# =========================================================
# ARAMA
# =========================================================

product = st.text_input(
    "Ürün adı",
    placeholder="Örn: Grundig Club BT Hoparlör"
)

search_button = st.button(
    "🔍 Fiyatları Bul",
    type="primary",
    use_container_width=True
)


# =========================================================
# NORMALIZE
# =========================================================

def normalize(text):

    if not text:
        return ""

    text = str(text).lower()

    replacements = {
        "ç":"c",
        "ğ":"g",
        "ı":"i",
        "ö":"o",
        "ş":"s",
        "ü":"u"
    }

    for a,b in replacements.items():
        text = text.replace(a,b)

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

def product_words(product):

    ignored = {
        "ve",
        "ile",
        "icin",
        "bir",
        "the"
    }

    return [
        w
        for w in normalize(product).split()
        if len(w) >= 2 and w not in ignored
    ]


# =========================================================
# ALAN ADI
# =========================================================

def domain(url):

    if not url:
        return ""

    try:
        return (
            url.split("//")[-1]
            .split("/")[0]
            .replace("www.","")
        )
    except:
        return ""


# =========================================================
# FİYAT ÇIKAR
# =========================================================

def extract_prices(text):

    if not text:
        return []

    text = text.replace(
        "\xa0",
        " "
    )

    patterns = [

        r'(\d{1,3}(?:[.\s]\d{3})*(?:,\d{1,2})?)\s*(?:TL|₺)',

        r'(?:TL|₺)\s*(\d{1,3}(?:[.\s]\d{3})*(?:,\d{1,2})?)'

    ]

    prices = []

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        for value in matches:

            try:

                value = value.strip()
                value = value.replace(
                    " ",
                    ""
                )

                if "," in value:

                    parts = value.split(",")

                    if len(parts[-1]) <= 2:

                        value = (
                            value
                            .replace(".","")
                            .replace(",",".")
                        )

                    else:

                        value = value.replace(
                            ",",
                            ""
                        )

                elif "." in value:

                    parts = value.split(".")

                    if len(parts[-1]) == 3:

                        value = value.replace(
                            ".",
                            ""
                        )

                number = float(value)

                if 1 <= number <= 10000000:

                    prices.append(
                        number
                    )

            except:
                pass

    return sorted(
        set(prices)
    )


# =========================================================
# İLGİLİ ÜRÜN MÜ?
# =========================================================

def relevant(product, text):

    words = product_words(
        product
    )

    text = normalize(
        text
    )

    if not words:
        return False

    found = 0

    for word in words:

        if word in text:
            found += 1

    # "Grundig Club" gibi iki kelimeli
    # aramada ikisinin de bulunmasını istiyoruz.
    if len(words) >= 2:

        return found >= len(words)

    return found >= 1


# =========================================================
# SOCIALCRAWL GOOGLE SHOPPING
# =========================================================

def google_shopping(query):

    if not API_KEY:
        return []

    endpoint = (
        "https://www.socialcrawl.dev"
        "/v1/google_shopping/product-search"
    )

    params = {
        "query": query,
        "country": "Turkey",
        "language": "tr",
        "depth": 10
    }

    for attempt in range(2):

        try:

            response = requests.get(
                endpoint,
                params=params,
                headers=HEADERS,
                timeout=120
            )

            if response.status_code == 504:

                if attempt == 0:
                    time.sleep(5)
                    continue

                return []

            if response.status_code != 200:
                return []

            data = response.json()

            if not data.get("success"):
                return []

            return (
                data
                .get("data", {})
                .get("items", [])
            )

        except:

            if attempt == 0:

                time.sleep(4)

            else:

                return []

    return []


# =========================================================
# GOOGLE SHOPPING SONUÇLARI
# =========================================================

def parse_google(
    items,
    product
):

    results = []

    for item in items:

        p = item.get(
            "product",
            {}
        )

        title = p.get(
            "title",
            ""
        )

        description = p.get(
            "description",
            ""
        )

        text = (
            title
            + " "
            + str(description)
        )

        if not relevant(
            product,
            text
        ):
            continue

        price_data = p.get(
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

        currency = str(
            price_data.get(
                "currency",
                ""
            )
        ).upper()

        if price is None:
            continue

        if currency not in [
            "TRY",
            "TL"
        ]:
            continue

        try:
            price = float(price)
        except:
            continue

        results.append({

            "title": title,

            "price": price,

            "seller": p.get(
                "seller",
                "Mağaza"
            ),

            "url": p.get(
                "url",
                ""
            ),

            "condition": "Sıfır",

            "source": "Google Shopping"

        })

    return results


# =========================================================
# WEB ARAMASI
# =========================================================

def web_search(
    query,
    condition,
    sites
):

    results = []

    headers = {
        "User-Agent":
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "Chrome/131.0 Safari/537.36"
    }

    for site in sites:

        search_query = (
            f'"{query}" site:{site}'
        )

        url = (
            "https://html.duckduckgo.com/html/"
        )

        try:

            response = requests.get(
                url,
                params={
                    "q": search_query
                },
                headers=headers,
                timeout=20
            )

            if response.status_code != 200:
                continue

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            for result in soup.select(
                ".result"
            ):

                link = result.select_one(
                    ".result__a"
                )

                snippet = result.select_one(
                    ".result__snippet"
                )

                if not link:
                    continue

                title = link.get_text(
                    " ",
                    strip=True
                )

                href = link.get(
                    "href",
                    ""
                )

                description = ""

                if snippet:

                    description = snippet.get_text(
                        " ",
                        strip=True
                    )

                combined = (
                    title
                    + " "
                    + description
                )

                if not relevant(
                    query,
                    combined
                ):
                    continue

                prices = extract_prices(
                    combined
                )

                if not prices:
                    continue

                results.append({

                    "title": title,

                    "price": min(prices),

                    "seller": site,

                    "url": href,

                    "condition": condition,

                    "source": site

                })

        except:
            continue

        time.sleep(.5)

    return results


# =========================================================
# SIFIR ARAMA
# =========================================================

def search_new(product):

    results = []

    queries = [
        product,
        f"{product} fiyat"
    ]

    for query in queries:

        items = google_shopping(
            query
        )

        results.extend(
            parse_google(
                items,
                product
            )
        )

        time.sleep(1)

    # Google Shopping yanında
    # doğrudan mağaza araması
    sites = [
        "akakce.com",
        "cimri.com",
        "hepsiburada.com",
        "trendyol.com",
        "n11.com",
        "amazon.com.tr"
    ]

    results.extend(
        web_search(
            product,
            "Sıfır",
            sites
        )
    )

    return clean_results(
        results
    )


# =========================================================
# İKİNCİ EL ARAMA
# =========================================================

def search_used(product):

    results = []

    # Google Shopping
    queries = [
        f"{product} ikinci el",
        f"{product} 2.el"
    ]

    for query in queries:

        items = google_shopping(
            query
        )

        parsed = parse_google(
            items,
            product
        )

        for item in parsed:

            item["condition"] = (
                "İkinci El"
            )

            results.append(
                item
            )

    # Doğrudan ikinci el siteleri
    sites = [
        "sahibinden.com",
        "letgo.com"
    ]

    results.extend(
        web_search(
            product,
            "İkinci El",
            sites
        )
    )

    return clean_results(
        results
    )


# =========================================================
# YENİLENMİŞ
# =========================================================

def search_refurbished(product):

    results = []

    queries = [
        f"{product} yenilenmiş",
        f"{product} refurbished"
    ]

    for query in queries:

        items = google_shopping(
            query
        )

        parsed = parse_google(
            items,
            product
        )

        for item in parsed:

            text = normalize(
                item["title"]
            )

            if (
                "yenilenmis" in text
                or
                "refurbished" in text
                or
                "renewed" in text
            ):

                item["condition"] = (
                    "Yenilenmiş"
                )

                results.append(
                    item
                )

    return clean_results(
        results
    )


# =========================================================
# TEMİZLE
# =========================================================

def clean_results(results):

    unique = {}

    for item in results:

        key = (
            normalize(
                item["title"]
            ),
            normalize(
                item["seller"]
            ),
            round(
                item["price"],
                2
            )
        )

        if key not in unique:

            unique[key] = item

    results = list(
        unique.values()
    )

    results.sort(
        key=lambda x: x["price"]
    )

    return results


# =========================================================
# EN UCUZ
# =========================================================

def show_best(results):

    if not results:
        return

    cheapest = min(
        results,
        key=lambda x: x["price"]
    )

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
                📦 {cheapest["condition"]}
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
# KATEGORİ
# =========================================================

def show_category(
    title,
    icon,
    results,
    css
):

    st.subheader(
        f"{icon} {title}"
    )

    if not results:

        st.info(
            f"{title} için uygun sonuç bulunamadı."
        )

        return

    for i, item in enumerate(
        results[:20],
        1
    ):

        st.markdown(
            f"""
            <div class="offer {css}">

                <div class="offer-title">
                    {i}. {item["title"]}
                </div>

                <div class="offer-price">
                    {item["price"]:,.2f} TL
                </div>

                <div class="offer-store">
                    🏪 {item["seller"]}
                </div>

                <div class="offer-condition">
                    {item["condition"]}
                    · {item["source"]}
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )

        if item["url"]:

            st.link_button(
                "🛒 İlan / Mağazaya Git",
                item["url"]
            )


# =========================================================
# ÇALIŞTIR
# =========================================================

if search_button:

    if not product.strip():

        st.warning(
            "Ürün adı yaz."
        )

        st.stop()

    if not API_KEY:

        st.error(
            "SocialCrawl API anahtarı bulunamadı."
        )

        st.info(
            "Streamlit Secrets içine "
            "SOCIALCRAWL_API_KEY ekle."
        )

        st.stop()

    product = product.strip()

    st.info(
        f"🔎 **{product}** için tüm kaynaklar taranıyor..."
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
        "🟠 Sahibinden ve Letgo ikinci el ilanları aranıyor..."
    ):

        used_results = search_used(
            product
        )

    # -----------------------------------------------------
    # YENİLENMİŞ
    # -----------------------------------------------------

    with st.spinner(
        "🔵 Yenilenmiş ürünler aranıyor..."
    ):

        refurb_results = search_refurbished(
            product
        )

    # -----------------------------------------------------
    # TÜMÜ
    # -----------------------------------------------------

    all_results = clean_results(
        new_results
        + used_results
        + refurb_results
    )

    # -----------------------------------------------------
    # EN UCUZ
    # -----------------------------------------------------

    if all_results:

        show_best(
            all_results
        )

    else:

        st.error(
            f'"{product}" için fiyat bulunamadı.'
        )

    # -----------------------------------------------------
    # ÖZET
    # -----------------------------------------------------

    st.divider()

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "🟢 Sıfır",
            len(new_results)
        )

    with c2:
        st.metric(
            "🟠 İkinci El",
            len(used_results)
        )

    with c3:
        st.metric(
            "🔵 Yenilenmiş",
            len(refurb_results)
        )

    with c4:
        st.metric(
            "💰 Toplam",
            len(all_results)
        )

    # -----------------------------------------------------
    # SIFIR
    # -----------------------------------------------------

    st.divider()

    show_category(
        "Sıfır Ürünler",
        "🟢",
        new_results,
        "new"
    )

    # -----------------------------------------------------
    # İKİNCİ EL
    # -----------------------------------------------------

    st.divider()

    show_category(
        "İkinci El",
        "🟠",
        used_results,
        "used"
    )

    # -----------------------------------------------------
    # YENİLENMİŞ
    # -----------------------------------------------------

    st.divider()

    show_category(
        "Yenilenmiş",
        "🔵",
        refurb_results,
        "refurb"
    )
