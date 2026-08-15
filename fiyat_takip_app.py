import streamlit as st
import requests
import re
import html
import time

from urllib.parse import quote_plus, urlparse
from bs4 import BeautifulSoup


# =========================================================
# SAYFA
# =========================================================

st.set_page_config(
    page_title="Fiyat Avcısı",
    page_icon="💰",
    layout="wide"
)


# =========================================================
# CSS
# =========================================================

st.markdown("""
<style>

.main-title {
    text-align:center;
    font-size:42px;
    font-weight:900;
    color:#111827;
}

.subtitle {
    text-align:center;
    color:#6b7280;
    font-size:17px;
    margin-bottom:25px;
}

.best-card {
    background:linear-gradient(135deg,#ecfdf5,#f0fdf4);
    border:2px solid #22c55e;
    border-radius:20px;
    padding:28px;
    margin:20px 0;
    box-shadow:0 8px 25px rgba(0,0,0,.06);
}

.best-title {
    font-size:22px;
    font-weight:900;
    color:#166534;
}

.best-product {
    font-size:25px;
    font-weight:900;
    color:#111827;
    margin-top:8px;
}

.best-price {
    font-size:42px;
    font-weight:900;
    color:#15803d;
    margin-top:8px;
}

.best-store {
    font-size:17px;
    font-weight:800;
    margin-top:8px;
}

.best-condition {
    font-size:15px;
    font-weight:800;
    margin-top:7px;
}

.offer {
    background:white;
    border:1px solid #e5e7eb;
    border-radius:16px;
    padding:18px;
    margin-bottom:12px;
    box-shadow:0 3px 12px rgba(0,0,0,.04);
}

.offer.new {
    border-left:6px solid #22c55e;
}

.offer.used {
    border-left:6px solid #f97316;
}

.offer.refurbished {
    border-left:6px solid #3b82f6;
}

.offer-title {
    font-size:18px;
    font-weight:800;
}

.offer-price {
    font-size:29px;
    font-weight:900;
    margin-top:6px;
}

.offer-store {
    color:#2563eb;
    font-weight:800;
    margin-top:6px;
}

.offer-condition {
    font-weight:800;
    margin-top:5px;
}

.offer-source {
    color:#6b7280;
    font-size:13px;
    margin-top:5px;
}

.source-ok {
    background:#ecfdf5;
    border:1px solid #bbf7d0;
    padding:10px;
    border-radius:10px;
    margin-bottom:6px;
}

.source-zero {
    background:#f9fafb;
    border:1px solid #e5e7eb;
    padding:10px;
    border-radius:10px;
    margin-bottom:6px;
}

.source-error {
    background:#fff7ed;
    border:1px solid #fed7aa;
    padding:10px;
    border-radius:10px;
    margin-bottom:6px;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# BAŞLIK
# =========================================================

st.markdown(
    '<div class="main-title">💰 Fiyat Avcısı</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Sıfır • İkinci El • Yenilenmiş • Türkiye Fiyat Karşılaştırma'
    '</div>',
    unsafe_allow_html=True
)


# =========================================================
# API KEY
# =========================================================

try:
    API_KEY = st.secrets["SOCIALCRAWL_API_KEY"]
except Exception:
    API_KEY = ""


BASE_URL = "https://www.socialcrawl.dev"

API_HEADERS = {
    "x-api-key": API_KEY,
    "Accept": "application/json",
    "User-Agent": "FiyatAvcisi/1.0"
}

WEB_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9"
}


# =========================================================
# ARAMA KUTUSU
# =========================================================

query = st.text_input(
    "🔎 Ürün adı",
    placeholder="Örn: Grundig Club BT Hoparlör"
)

search_button = st.button(
    "🔍 FİYATLARI BUL",
    type="primary",
    use_container_width=True
)


# =========================================================
# YARDIMCI
# =========================================================

def normalize(text):

    if text is None:
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

    for a, b in replacements.items():
        text = text.replace(a, b)

    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def get_domain(url):

    try:

        domain = urlparse(
            str(url)
        ).netloc.lower()

        if domain.startswith("www."):
            domain = domain[4:]

        return domain

    except Exception:
        return ""


def store_from_url(url):

    domain = get_domain(url)

    stores = {
        "hepsiburada.com": "Hepsiburada",
        "trendyol.com": "Trendyol",
        "n11.com": "N11",
        "amazon.com.tr": "Amazon Türkiye",
        "akakce.com": "Akakçe",
        "cimri.com": "Cimri",
        "dolap.com": "Dolap",
        "sahibinden.com": "Sahibinden",
        "letgo.com": "Letgo"
    }

    return stores.get(
        domain,
        domain or "Mağaza"
    )


def product_words(query):

    stop = {
        "ve",
        "ile",
        "icin",
        "için",
        "urun",
        "ürün",
        "fiyat",
        "satın",
        "satin",
        "al"
    }

    return [
        x for x in normalize(query).split()
        if len(x) >= 2 and x not in stop
    ]


def relevance_score(
    query,
    title,
    description=""
):

    words = product_words(query)

    text = normalize(
        str(title) + " " + str(description)
    )

    return sum(
        1 for word in words
        if word in text
    )


def is_relevant(
    query,
    title,
    description=""
):

    words = product_words(query)

    if not words:
        return False

    score = relevance_score(
        query,
        title,
        description
    )

    if len(words) <= 2:
        return score >= len(words)

    return score >= max(
        2,
        len(words) - 1
    )


# =========================================================
# FİYAT
# =========================================================

def parse_price(value):

    if value is None:
        return None

    try:

        if isinstance(value, (int, float)):

            value = float(value)

            if 0 < value < 10000000:
                return value

            return None

        value = str(value)

        value = value.replace("₺", "")
        value = re.sub(
            r"\bTL\b",
            "",
            value,
            flags=re.I
        )

        value = value.strip()

        if "," in value and "." in value:

            if value.rfind(",") > value.rfind("."):

                value = value.replace(".", "")
                value = value.replace(",", ".")

            else:

                value = value.replace(",", "")

        elif "," in value:

            last = value.split(",")[-1]

            if len(last) <= 2:
                value = value.replace(",", ".")
            else:
                value = value.replace(",", "")

        elif "." in value:

            parts = value.split(".")

            if len(parts) == 2 and len(parts[1]) == 3:
                value = value.replace(".", "")

        price = float(value)

        if 0 < price < 10000000:
            return price

    except Exception:
        return None

    return None


def extract_price(text):

    if not text:
        return None

    patterns = [

        r"(\d{1,3}(?:[.\s]\d{3})+(?:,\d{1,2})?)\s*(?:TL|₺)",

        r"(\d{3,7}(?:,\d{1,2})?)\s*(?:TL|₺)",

        r"(?:TL|₺)\s*(\d{3,7}(?:[.,]\d{1,2})?)"

    ]

    for pattern in patterns:

        matches = re.findall(
            pattern,
            str(text),
            re.I
        )

        for match in matches:

            price = parse_price(match)

            if price is not None:
                return price

    return None


# =========================================================
# API
# =========================================================

def api_get(
    endpoint,
    params,
    timeout=180
):

    if not API_KEY:

        return {
            "success": False,
            "status": 0,
            "error": "API anahtarı bulunamadı.",
            "data": None
        }

    try:

        response = requests.get(
            BASE_URL + endpoint,
            params=params,
            headers=API_HEADERS,
            timeout=timeout
        )

        try:
            data = response.json()
        except Exception:
            data = None

        if response.status_code != 200:

            return {
                "success": False,
                "status": response.status_code,
                "error": (
                    f"HTTP {response.status_code}"
                ),
                "data": data
            }

        return {
            "success": True,
            "status": response.status_code,
            "error": None,
            "data": data
        }

    except requests.exceptions.Timeout:

        return {
            "success": False,
            "status": 504,
            "error": "API zaman aşımına uğradı.",
            "data": None
        }

    except Exception as e:

        return {
            "success": False,
            "status": 0,
            "error": str(e),
            "data": None
        }


# =========================================================
# GOOGLE SHOPPING
# =========================================================

def google_product_search(query):

    return api_get(
        "/v1/google_shopping/product-search",
        {
            "query": query,
            "country": "Turkey",
            "language": "tr",
            "depth": 40
        },
        timeout=240
    )


def parse_google_products(
    response,
    query
):

    results = []

    if not response.get("success"):
        return results

    payload = response.get("data")

    if not isinstance(payload, dict):
        return results

    data = payload.get("data", {})

    if not isinstance(data, dict):
        return results

    items = data.get("items", [])

    if not isinstance(items, list):
        return results

    for item in items:

        if not isinstance(item, dict):
            continue

        product = item.get(
            "product",
            {}
        )

        if not isinstance(product, dict):
            continue

        title = product.get(
            "title",
            ""
        )

        description = product.get(
            "description",
            ""
        )

        if not title:
            continue

        if not is_relevant(
            query,
            title,
            description
        ):
            continue

        price_info = product.get(
            "price",
            {}
        )

        if not isinstance(
            price_info,
            dict
        ):
            continue

        price = parse_price(
            price_info.get("current")
        )

        if price is None:
            continue

        currency = str(
            price_info.get(
                "currency",
                ""
            )
        ).upper()

        # Türkiye aramasında TRY bekliyoruz.
        # Ancak API bazen para birimini boş döndürebilir.
        if currency and currency not in {
            "TRY",
            "TL",
            "₺"
        }:
            continue

        url = product.get(
            "url",
            ""
        )

        seller = product.get(
            "seller",
            ""
        )

        if seller:
            store = str(seller)
        else:
            store = store_from_url(url)

        results.append({
            "title": title,
            "price": price,
            "store": store,
            "url": url,
            "condition": "Sıfır",
            "source": "Google Shopping"
        })

    return results


# =========================================================
# WEB ARAMA
# =========================================================

def google_web_search(
    search_query,
    condition,
    wanted_domain=None
):

    url = (
        "https://www.google.com/search?q="
        + quote_plus(search_query)
        + "&hl=tr"
        + "&gl=tr"
        + "&num=30"
    )

    try:

        response = requests.get(
            url,
            headers=WEB_HEADERS,
            timeout=25
        )

        if response.status_code != 200:
            return []

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

    except Exception:
        return []

    results = []

    for link in soup.select("a"):

        href = link.get(
            "href",
            ""
        )

        title = link.get_text(
            " ",
            strip=True
        )

        if not href.startswith("http"):
            continue

        if not title:
            continue

        domain = get_domain(href)

        if wanted_domain:

            if (
                domain != wanted_domain
                and not domain.endswith(
                    "." + wanted_domain
                )
            ):
                continue

        price = extract_price(
            title
        )

        if price is None:

            parent = link.parent

            if parent:

                price = extract_price(
                    parent.get_text(
                        " ",
                        strip=True
                    )
                )

        if price is None:
            continue

        results.append({
            "title": title[:300],
            "price": price,
            "store": store_from_url(href),
            "url": href,
            "condition": condition,
            "source": "Google Web"
        })

    return results


# =========================================================
# KAYNAK ARAMALARI
# =========================================================

def search_marketplaces(query):

    results = []

    sources = [

        (
            "Akakçe",
            "akakce.com",
            f'"{query}" site:akakce.com'
        ),

        (
            "Cimri",
            "cimri.com",
            f'"{query}" site:cimri.com'
        ),

        (
            "Hepsiburada",
            "hepsiburada.com",
            f'"{query}" site:hepsiburada.com'
        ),

        (
            "Trendyol",
            "trendyol.com",
            f'"{query}" site:trendyol.com'
        ),

        (
            "N11",
            "n11.com",
            f'"{query}" site:n11.com'
        ),

        (
            "Amazon Türkiye",
            "amazon.com.tr",
            f'"{query}" site:amazon.com.tr'
        )
    ]

    for store, domain, search_query in sources:

        found = google_web_search(
            search_query,
            "Sıfır",
            domain
        )

        results.extend(found)

        time.sleep(.3)

    return results


def search_used(query):

    results = []

    sources = [

        (
            "Dolap",
            "dolap.com",
            f'"{query}" site:dolap.com'
        ),

        (
            "Sahibinden",
            "sahibinden.com",
            f'"{query}" site:sahibinden.com'
        ),

        (
            "Letgo",
            "letgo.com",
            f'"{query}" site:letgo.com'
        )
    ]

    for store, domain, search_query in sources:

        found = google_web_search(
            search_query,
            "İkinci El",
            domain
        )

        # Mağaza ismi garanti olsun
        for item in found:
            item["store"] = store

        results.extend(found)

        time.sleep(.3)

    return results


def search_refurbished(query):

    results = []

    sources = [

        (
            "Hepsiburada",
            "hepsiburada.com",
            f'"{query}" yenilenmiş site:hepsiburada.com'
        ),

        (
            "Trendyol",
            "trendyol.com",
            f'"{query}" yenilenmiş site:trendyol.com'
        ),

        (
            "N11",
            "n11.com",
            f'"{query}" yenilenmiş site:n11.com'
        ),

        (
            "Amazon Türkiye",
            "amazon.com.tr",
            f'"{query}" yenilenmiş site:amazon.com.tr'
        )
    ]

    for store, domain, search_query in sources:

        found = google_web_search(
            search_query,
            "Yenilenmiş",
            domain
        )

        for item in found:
            item["store"] = store
            item["condition"] = "Yenilenmiş"

        results.extend(found)

        time.sleep(.3)

    return results


# =========================================================
# TEMİZLE
# =========================================================

def clean_results(results):

    unique = {}

    for item in results:

        try:

            price = float(
                item["price"]
            )

        except Exception:
            continue

        if price <= 0:
            continue

        title = str(
            item.get(
                "title",
                ""
            )
        ).strip()

        store = str(
            item.get(
                "store",
                ""
            )
        ).strip()

        url = str(
            item.get(
                "url",
                ""
            )
        ).strip()

        if not title:
            continue

        key = (
            normalize(title),
            normalize(store),
            round(price, 2)
        )

        if key not in unique:

            item["price"] = price

            unique[key] = item

    result = list(
        unique.values()
    )

    result.sort(
        key=lambda x: x["price"]
    )

    return result


# =========================================================
# DURUM
# =========================================================

def condition_of(item):

    condition = normalize(
        item.get(
            "condition",
            ""
        )
    )

    title = normalize(
        item.get(
            "title",
            ""
        )
    )

    store = normalize(
        item.get(
            "store",
            ""
        )
    )

    text = (
        condition
        + " "
        + title
        + " "
        + store
    )

    if any(
        x in text
        for x in [
            "yenilenmis",
            "refurbished",
            "renewed"
        ]
    ):
        return "Yenilenmiş"

    if any(
        x in text
        for x in [
            "ikinci el",
            "2 el",
            "2.el",
            "kullanilmis",
            "dolap",
            "sahibinden",
            "letgo"
        ]
    ):
        return "İkinci El"

    return "Sıfır"


# =========================================================
# EN UCUZ
# =========================================================

def show_best(results):

    if not results:
        return

    best = min(
        results,
        key=lambda x: x["price"]
    )

    title = html.escape(
        best["title"]
    )

    store = html.escape(
        best["store"]
    )

    condition = html.escape(
        condition_of(best)
    )

    st.markdown(
        f"""
        <div class="best-card">

            <div class="best-title">
                🏆 En Ucuz Fiyat
            </div>

            <div class="best-product">
                {title}
            </div>

            <div class="best-price">
                {best["price"]:,.2f} TL
            </div>

            <div class="best-store">
                🏪 {store}
            </div>

            <div class="best-condition">
                📦 {condition}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    if best.get("url"):
        st.link_button(
            "🛒 Bu ürüne git",
            best["url"]
        )


# =========================================================
# SONUÇLAR
# =========================================================

def show_results(
    title,
    emoji,
    results,
    css
):

    st.subheader(
        f"{emoji} {title}"
    )

    if not results:

        st.info(
            "Bu kategoride doğrulanabilir "
            "fiyat bulunamadı."
        )

        return

    for i, item in enumerate(
        results[:40],
        1
    ):

        safe_title = html.escape(
            item["title"]
        )

        safe_store = html.escape(
            item["store"]
        )

        safe_condition = html.escape(
            condition_of(item)
        )

        safe_source = html.escape(
            item["source"]
        )

        st.markdown(
            f"""
            <div class="offer {css}">

                <div class="offer-title">
                    {i}. {safe_title}
                </div>

                <div class="offer-price">
                    {item["price"]:,.2f} TL
                </div>

                <div class="offer-store">
                    🏪 {safe_store}
                </div>

                <div class="offer-condition">
                    📦 {safe_condition}
                </div>

                <div class="offer-source">
                    🔎 {safe_source}
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )

        if item.get("url"):

            st.link_button(
                "Ürüne Git",
                item["url"]
            )


# =========================================================
# KAYNAK DURUMU
# =========================================================

def source_box(
    name,
    count
):

    if count > 0:

        st.markdown(
            f"""
            <div class="source-ok">
                🟢 <b>{html.escape(name)}</b>
                → {count} sonuç
            </div>
            """,
            unsafe_allow_html=True
        )

    else:

        st.markdown(
            f"""
            <div class="source-zero">
                ⚪ <b>{html.escape(name)}</b>
                → 0 sonuç
            </div>
            """,
            unsafe_allow_html=True
        )


# =========================================================
# ÇALIŞTIR
# =========================================================

if search_button:

    query = query.strip()

    if not query:

        st.warning(
            "Önce bir ürün adı yaz."
        )

        st.stop()

    if not API_KEY:

        st.error(
            "SOCIALCRAWL_API_KEY bulunamadı."
        )

        st.code(
            'SOCIALCRAWL_API_KEY = "sc_..."',
            language="toml"
        )

        st.stop()

    st.info(
        f'🔎 "{query}" için fiyatlar aranıyor...'
    )

    # -----------------------------------------------------
    # GOOGLE SHOPPING
    # -----------------------------------------------------

    with st.spinner(
        "Google Shopping taranıyor..."
    ):

        google_response = (
            google_product_search(
                query
            )
        )

        google_results = (
            parse_google_products(
                google_response,
                query
            )
        )

    # -----------------------------------------------------
    # MARKETPLACE
    # -----------------------------------------------------

    with st.spinner(
        "Akakçe, Cimri ve mağazalar taranıyor..."
    ):

        marketplace_results = (
            search_marketplaces(
                query
            )
        )

    # -----------------------------------------------------
    # İKİNCİ EL
    # -----------------------------------------------------

    with st.spinner(
        "Dolap, Sahibinden ve Letgo taranıyor..."
    ):

        used_results = (
            search_used(
                query
            )
        )

    # -----------------------------------------------------
    # YENİLENMİŞ
    # -----------------------------------------------------

    with st.spinner(
        "Yenilenmiş ürünler aranıyor..."
    ):

        refurbished_results = (
            search_refurbished(
                query
            )
        )

    # -----------------------------------------------------
    # TEMİZLE
    # -----------------------------------------------------

    google_results = clean_results(
        google_results
    )

    marketplace_results = clean_results(
        marketplace_results
    )

    used_results = clean_results(
        used_results
    )

    refurbished_results = clean_results(
        refurbished_results
    )

    # -----------------------------------------------------
    # TÜM SIFIR SONUÇLAR
    # -----------------------------------------------------

    new_results = clean_results(
        google_results
        + marketplace_results
    )

    all_results = clean_results(
        new_results
        + used_results
        + refurbished_results
    )

    # -----------------------------------------------------
    # KAYNAK SAYILARI
    # -----------------------------------------------------

    def count_store(
        results,
        store
    ):

        return sum(
            1
            for x in results
            if x["store"] == store
        )

    with st.expander(
        "📊 Kaynak Durumu",
        expanded=True
    ):

        source_box(
            "Google Shopping",
            len(google_results)
        )

        source_box(
            "Akakçe",
            count_store(
                marketplace_results,
                "Akakçe"
            )
        )

        source_box(
            "Cimri",
            count_store(
                marketplace_results,
                "Cimri"
            )
        )

        source_box(
            "Hepsiburada",
            count_store(
                marketplace_results,
                "Hepsiburada"
            )
        )

        source_box(
            "Trendyol",
            count_store(
                marketplace_results,
                "Trendyol"
            )
        )

        source_box(
            "N11",
            count_store(
                marketplace_results,
                "N11"
            )
        )

        source_box(
            "Amazon Türkiye",
            count_store(
                marketplace_results,
                "Amazon Türkiye"
            )
        )

        source_box(
            "İkinci El • Dolap",
            count_store(
                used_results,
                "Dolap"
            )
        )

        source_box(
            "İkinci El • Sahibinden",
            count_store(
                used_results,
                "Sahibinden"
            )
        )

        source_box(
            "İkinci El • Letgo",
            count_store(
                used_results,
                "Letgo"
            )
        )

        source_box(
            "Yenilenmiş",
            len(refurbished_results)
        )

    # -----------------------------------------------------
    # API HATASI
    # -----------------------------------------------------

    if not google_response.get("success"):

        st.warning(
            "Google Shopping şu anda cevap vermedi: "
            + str(
                google_response.get(
                    "error",
                    "Bilinmeyen API hatası"
                )
            )
        )

    # -----------------------------------------------------
    # SONUÇ YOK
    # -----------------------------------------------------

    if not all_results:

        st.error(
            f'"{query}" için doğrulanabilir fiyat bulunamadı.'
        )

        st.stop()

    # -----------------------------------------------------
    # EN UCUZ
    # -----------------------------------------------------

    show_best(
        all_results
    )

    # -----------------------------------------------------
    # ÖZET
    # -----------------------------------------------------

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
            len(refurbished_results)
        )

    with c4:
        st.metric(
            "📦 Toplam",
            len(all_results)
        )

    # -----------------------------------------------------
    # FİYAT ARALIĞI
    # -----------------------------------------------------

    prices = [
        x["price"]
        for x in all_results
        if x.get("price") is not None
    ]

    if prices:

        cheapest = min(prices)
        highest = max(prices)

        difference = (
            highest - cheapest
        )

        st.success(
            f"💰 En ucuz: **{cheapest:,.2f} TL**  |  "
            f"En pahalı: **{highest:,.2f} TL**  |  "
            f"Fark: **{difference:,.2f} TL**"
        )

    # -----------------------------------------------------
    # SONUÇLAR
    # -----------------------------------------------------

    st.divider()

    show_results(
        "🟢 Sıfır Ürünler",
        "",
        new_results,
        "new"
    )

    st.divider()

    show_results(
        "🟠 İkinci El",
        "",
        used_results,
        "used"
    )

    st.divider()

    show_results(
        "🔵 Yenilenmiş",
        "",
        refurbished_results,
        "refurbished"
    )

    # -----------------------------------------------------
    # TEKNİK API BİLGİSİ
    # -----------------------------------------------------

    with st.expander(
        "🛠️ Teknik API Bilgisi"
    ):

        st.write(
            "HTTP:",
            google_response.get(
                "status"
            )
        )

        if google_response.get(
            "error"
        ):

            st.write(
                "Hata:",
                google_response.get(
                    "error"
                )
            )

        payload = google_response.get(
            "data"
        )

        if isinstance(
            payload,
            dict
        ):

            api_data = payload.get(
                "data",
                {}
            )

            if isinstance(
                api_data,
                dict
            ):

                items = api_data.get(
                    "items",
                    []
                )

                st.write(
                    "Google Shopping API ürün sayısı:",
                    len(items)
                    if isinstance(items, list)
                    else 0
                )
