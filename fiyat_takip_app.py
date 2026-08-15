import streamlit as st
import requests
import re
import html
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
# CSS
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
    padding:26px;
    margin:20px 0;
}

.best-title {
    font-size:20px;
    font-weight:900;
    color:#166534;
}

.best-product {
    font-size:25px;
    font-weight:900;
    margin-top:8px;
    color:#111827;
}

.best-price {
    font-size:44px;
    font-weight:900;
    color:#15803d;
    margin-top:8px;
}

.best-store {
    font-size:17px;
    margin-top:8px;
}

.best-condition {
    font-weight:800;
    margin-top:6px;
}

.offer {
    background:#ffffff;
    border-radius:15px;
    padding:18px;
    margin-bottom:10px;
    border:1px solid #e5e7eb;
    box-shadow:0 3px 12px rgba(0,0,0,.04);
}

.offer-new {
    border-left:6px solid #22c55e;
}

.offer-used {
    border-left:6px solid #f97316;
}

.offer-refurb {
    border-left:6px solid #3b82f6;
}

.offer-title {
    font-size:18px;
    font-weight:800;
    color:#111827;
}

.offer-price {
    font-size:29px;
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
    font-size:14px;
}

.empty-box {
    padding:15px;
    border-radius:12px;
    background:#f9fafb;
    color:#6b7280;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# API KEY
# =========================================================

try:
    API_KEY = st.secrets["SOCIALCRAWL_API_KEY"]
except Exception:
    API_KEY = ""


HEADERS = {
    "x-api-key": API_KEY,
    "Accept": "application/json"
}


BASE_URL = "https://www.socialcrawl.dev"


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
# YARDIMCILAR
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

    for a, b in replacements.items():
        text = text.replace(a, b)

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


def words_of(product):

    stop_words = {
        "ve",
        "ile",
        "icin",
        "bir",
        "the",
        "for",
        "bluetooth"
    }

    return [
        x
        for x in normalize(product).split()
        if len(x) >= 2
        and x not in stop_words
    ]


def domain_of(url):

    try:

        domain = urlparse(url).netloc.lower()

        if domain.startswith("www."):
            domain = domain[4:]

        return domain

    except Exception:
        return ""


def store_name(url):

    domain = domain_of(url)

    stores = {
        "akakce.com": "Akakçe",
        "cimri.com": "Cimri",
        "hepsiburada.com": "Hepsiburada",
        "trendyol.com": "Trendyol",
        "n11.com": "N11",
        "amazon.com.tr": "Amazon",
        "dolap.com": "Dolap",
        "sahibinden.com": "Sahibinden",
        "letgo.com": "Letgo",
        "grundig.com.tr": "Grundig"
    }

    return stores.get(
        domain,
        domain or "Mağaza"
    )


# =========================================================
# FİYAT AYIKLA
# =========================================================

def extract_prices(text):

    if not text:
        return []

    text = str(text)
    text = text.replace("\xa0", " ")

    patterns = [

        r'(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?)\s*(?:TL|₺)',

        r'(\d{1,7}(?:,\d{1,2})?)\s*(?:TL|₺)',

        r'(?:TL|₺)\s*(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?)',

        r'(?:TL|₺)\s*(\d{1,7}(?:,\d{1,2})?)'
    ]

    output = []

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text,
            re.IGNORECASE
        )

        for value in matches:

            try:

                value = value.strip()

                if "." in value and "," in value:

                    value = value.replace(".", "")
                    value = value.replace(",", ".")

                elif "," in value:

                    parts = value.split(",")

                    if len(parts[-1]) <= 2:

                        value = value.replace(",", ".")

                    else:

                        value = value.replace(",", "")

                elif "." in value:

                    parts = value.split(".")

                    if len(parts[-1]) == 3:

                        value = value.replace(".", "")

                number = float(value)

                if 1 <= number <= 10_000_000:

                    output.append(number)

            except Exception:
                pass

    return sorted(set(output))


# =========================================================
# ÜRÜN ALÂKASI
# =========================================================

def relevance(product, text):

    product_words = words_of(product)

    if not product_words:
        return 0

    text = normalize(text)

    score = 0

    for word in product_words:

        if word in text:
            score += 1

    return score


def relevant(product, title, description=""):

    combined = (
        str(title)
        + " "
        + str(description)
    )

    score = relevance(
        product,
        combined
    )

    total = len(
        words_of(product)
    )

    if total >= 4:
        return score >= 3

    if total == 3:
        return score >= 2

    if total == 2:
        return score >= 2

    return score >= 1


# =========================================================
# API ÇAĞRISI
# =========================================================

def api_get(
    endpoint,
    params,
    timeout=90
):

    if not API_KEY:
        return None

    try:

        response = requests.get(
            BASE_URL + endpoint,
            params=params,
            headers=HEADERS,
            timeout=timeout
        )

        if response.status_code != 200:
            return None

        data = response.json()

        if not data.get("success"):
            return None

        return data

    except Exception:

        return None


# =========================================================
# GOOGLE SEARCH
# =========================================================

def google_search(query):

    data = api_get(
        "/v1/google/search",
        {
            "query": query,
            "region": "TR",
            "page": 1
        }
    )

    if not data:
        return []

    return (
        data
        .get("data", {})
        .get("items", [])
    )


# =========================================================
# GOOGLE SHOPPING
# =========================================================

def shopping_search(product):

    data = api_get(
        "/v1/google_shopping/product-search",
        {
            "query": product,
            "country": "Turkey",
            "language": "tr",
            "depth": 120,
            "sort_by": "price_low_to_high"
        },
        timeout=150
    )

    if not data:
        return []

    return (
        data
        .get("data", {})
        .get("items", [])
    )


# =========================================================
# SHOPPING SONUÇLARI
# =========================================================

def parse_shopping(
    items,
    product
):

    results = []

    for row in items:

        p = row.get(
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

        if not relevant(
            product,
            title,
            description
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

        if currency not in {
            "TRY",
            "TL"
        }:
            continue

        try:
            price = float(price)
        except Exception:
            continue

        results.append({

            "title": title,

            "price": price,

            "seller": (
                p.get("seller")
                or "Mağaza"
            ),

            "url": p.get(
                "url",
                ""
            ),

            "condition": "Sıfır",

            "source": "Google Shopping",

            "gid": (
                p.get("ext", {})
                .get("gid")
            ),

            "product_id": p.get(
                "id"
            ),

            "data_docid": (
                p.get("ext", {})
                .get("data_docid")
            )
        })

    return results


# =========================================================
# SHOPPING SATICILARI
# =========================================================

def shopping_sellers(item):

    gid = item.get(
        "gid"
    )

    if not gid:
        return []

    params = {
        "gid": gid,
        "country": "Turkey",
        "language": "tr"
    }

    if item.get("product_id"):
        params["product_id"] = item["product_id"]

    if item.get("data_docid"):
        params["data_docid"] = item["data_docid"]

    data = api_get(
        "/v1/google_shopping/sellers",
        params,
        timeout=90
    )

    if not data:
        return []

    return (
        data
        .get("data", {})
        .get("items", [])
    )


# =========================================================
# SELLER JSON'UNDAN FİYAT BUL
# =========================================================

def parse_seller_item(
    row,
    product
):

    # API'nin döndürdüğü olası yapıları
    # esnek biçimde kontrol ediyoruz.

    obj = row

    if isinstance(
        row.get("seller"),
        dict
    ):
        obj = row["seller"]

    title = (
        obj.get("title")
        or obj.get("name")
        or product
    )

    seller = (
        obj.get("seller")
        or obj.get("merchant")
        or obj.get("store")
        or obj.get("seller_name")
        or "Mağaza"
    )

    url = (
        obj.get("url")
        or obj.get("link")
        or ""
    )

    price_data = obj.get(
        "price"
    )

    price = None

    if isinstance(
        price_data,
        dict
    ):

        price = (
            price_data.get("current")
            or price_data.get("value")
        )

    elif price_data is not None:

        price = price_data

    if price is None:

        price = (
            obj.get("current_price")
            or obj.get("price_current")
            or obj.get("amount")
        )

    try:

        price = float(price)

    except Exception:

        # Son çare bütün objeyi yazıya çevir
        prices = extract_prices(
            str(row)
        )

        if not prices:
            return None

        price = min(prices)

    if price <= 0:
        return None

    return {

        "title": str(title),

        "price": price,

        "seller": str(seller),

        "url": str(url),

        "condition": "Sıfır",

        "source": "Google Shopping"

    }


# =========================================================
# GOOGLE SEARCH SONUÇLARI
# =========================================================

def parse_google(
    items,
    product,
    condition
):

    results = []

    for row in items:

        title = row.get(
            "title",
            ""
        )

        url = row.get(
            "url",
            ""
        )

        snippet = row.get(
            "snippet",
            ""
        )

        if not relevant(
            product,
            title,
            snippet
        ):
            continue

        combined = (
            title
            + " "
            + snippet
        )

        prices = extract_prices(
            combined
        )

        if not prices:
            continue

        # İlan/fiyat sayfasında bulunan
        # en düşük fiyatı al.
        price = min(
            prices
        )

        results.append({

            "title": title,

            "price": price,

            "seller": store_name(
                url
            ),

            "url": url,

            "condition": condition,

            "source": "Google Search"

        })

    return results


# =========================================================
# KAYNAK ARA
# =========================================================

def search_source(
    product,
    domain,
    condition,
    words=""
):

    query = (
        f'"{product}" '
        f'site:{domain} '
        f'{words}'
    ).strip()

    items = google_search(
        query
    )

    return parse_google(
        items,
        product,
        condition
    )


# =========================================================
# SIFIR
# =========================================================

def search_new(product):

    results = []

    # -----------------------------------------
    # Google Shopping
    # -----------------------------------------

    shopping_items = shopping_search(
        product
    )

    shopping_results = parse_shopping(
        shopping_items,
        product
    )

    results.extend(
        shopping_results
    )

    # -----------------------------------------
    # Shopping seller teklifleri
    # İlk 5 uygun ürün için
    # -----------------------------------------

    for item in shopping_results[:5]:

        sellers = shopping_sellers(
            item
        )

        for seller_row in sellers:

            parsed = parse_seller_item(
                seller_row,
                product
            )

            if parsed:

                results.append(
                    parsed
                )

    # -----------------------------------------
    # Google Search mağazaları
    # -----------------------------------------

    domains = [
        "akakce.com",
        "cimri.com",
        "hepsiburada.com",
        "trendyol.com",
        "n11.com",
        "amazon.com.tr",
        "grundig.com.tr"
    ]

    for domain in domains:

        found = search_source(
            product,
            domain,
            "Sıfır",
            "fiyat"
        )

        results.extend(
            found
        )

    return clean_results(
        results
    )


# =========================================================
# İKİNCİ EL
# =========================================================

def search_used(product):

    results = []

    domains = [
        "dolap.com",
        "sahibinden.com",
        "letgo.com"
    ]

    for domain in domains:

        variants = [
            "",
            "ikinci el",
            "2.el"
        ]

        for variant in variants:

            found = search_source(
                product,
                domain,
                "İkinci El",
                variant
            )

            results.extend(
                found
            )

    # Genel Google araması
    # Sadece ikinci el sitelerini kabul ediyoruz.

    for query in [
        f'"{product}" ikinci el',
        f'"{product}" 2.el'
    ]:

        items = google_search(
            query
        )

        parsed = parse_google(
            items,
            product,
            "İkinci El"
        )

        for item in parsed:

            domain = domain_of(
                item["url"]
            )

            if domain in {
                "dolap.com",
                "sahibinden.com",
                "letgo.com"
            }:

                results.append(
                    item
                )

    return clean_results(
        results
    )


# =========================================================
# YENİLENMİŞ
# =========================================================

def search_refurbished(product):

    results = []

    domains = [
        "hepsiburada.com",
        "trendyol.com",
        "n11.com",
        "amazon.com.tr"
    ]

    variants = [
        "yenilenmiş",
        "refurbished",
        "renewed"
    ]

    for domain in domains:

        for variant in variants:

            found = search_source(
                product,
                domain,
                "Yenilenmiş",
                variant
            )

            results.extend(
                found
            )

    # Genel arama

    for variant in variants:

        query = (
            f'"{product}" {variant}'
        )

        items = google_search(
            query
        )

        parsed = parse_google(
            items,
            product,
            "Yenilenmiş"
        )

        for item in parsed:

            text = normalize(
                item["title"]
                + " "
                + item["seller"]
            )

            if any(
                word in text
                for word in [
                    "yenilenmis",
                    "refurbished",
                    "renewed"
                ]
            ):

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

        try:
            price = float(
                item["price"]
            )
        except Exception:
            continue

        if price <= 0:
            continue

        title = normalize(
            item.get(
                "title",
                ""
            )
        )

        seller = normalize(
            item.get(
                "seller",
                ""
            )
        )

        url = item.get(
            "url",
            ""
        )

        condition = item.get(
            "condition",
            ""
        )

        if url:

            key = (
                url.split("?")[0],
                condition
            )

        else:

            key = (
                title,
                seller,
                round(price, 2),
                condition
            )

        if key not in unique:

            item["price"] = price

            unique[key] = item

    output = list(
        unique.values()
    )

    output.sort(
        key=lambda x: x["price"]
    )

    return output


# =========================================================
# KATEGORİ GÖSTER
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

        st.markdown(
            '<div class="empty-box">'
            'Bu kategoride uygun fiyatlı sonuç bulunamadı.'
            '</div>',
            unsafe_allow_html=True
        )

        return

    for index, item in enumerate(
        results[:30],
        1
    ):

        title_html = html.escape(
            item["title"]
        )

        seller_html = html.escape(
            item["seller"]
        )

        condition_html = html.escape(
            item["condition"]
        )

        st.markdown(
            f"""
            <div class="offer {css}">

                <div class="offer-title">
                    {index}. {title_html}
                </div>

                <div class="offer-price">
                    {item["price"]:,.2f} TL
                </div>

                <div class="offer-store">
                    🏪 {seller_html}
                </div>

                <div class="offer-condition">
                    📦 {condition_html}
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )

        if item.get("url"):

            st.link_button(
                "🛒 Sonuca Git",
                item["url"]
            )


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

    title = html.escape(
        cheapest["title"]
    )

    seller = html.escape(
        cheapest["seller"]
    )

    condition = html.escape(
        cheapest["condition"]
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
                {cheapest["price"]:,.2f} TL
            </div>

            <div class="best-store">
                🏪 {seller}
            </div>

            <div class="best-condition">
                📦 {condition}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    if cheapest.get("url"):

        st.link_button(
            "🛒 En Ucuz Sonuca Git",
            cheapest["url"]
        )


# =========================================================
# ÇALIŞTIR
# =========================================================

if search_button:

    if not product.strip():

        st.warning(
            "Önce ürün adını yaz."
        )

        st.stop()

    if not API_KEY:

        st.error(
            "SOCIALCRAWL_API_KEY bulunamadı."
        )

        st.info(
            "Streamlit Secrets bölümüne "
            "SOCIALCRAWL_API_KEY ekle."
        )

        st.stop()

    product = product.strip()

    st.info(
        f"🔎 **{product}** için tüm kaynaklar taranıyor..."
    )

    progress = st.progress(
        0
    )

    status = st.empty()

    # -----------------------------------------------------
    # SIFIR
    # -----------------------------------------------------

    status.write(
        "🟢 Sıfır ürünler ve mağazalar aranıyor..."
    )

    new_results = search_new(
        product
    )

    progress.progress(
        35
    )

    # -----------------------------------------------------
    # İKİNCİ EL
    # -----------------------------------------------------

    status.write(
        "🟠 Dolap, Sahibinden ve Letgo aranıyor..."
    )

    used_results = search_used(
        product
    )

    progress.progress(
        70
    )

    # -----------------------------------------------------
    # YENİLENMİŞ
    # -----------------------------------------------------

    status.write(
        "🔵 Yenilenmiş ürünler aranıyor..."
    )

    refurb_results = search_refurbished(
        product
    )

    progress.progress(
        100
    )

    progress.empty()
    status.empty()

    # -----------------------------------------------------
    # TÜMÜ
    # -----------------------------------------------------

    new_results = clean_results(
        new_results
    )

    used_results = clean_results(
        used_results
    )

    refurb_results = clean_results(
        refurb_results
    )

    all_results = clean_results(
        new_results
        + used_results
        + refurb_results
    )

    # -----------------------------------------------------
    # SONUÇ YOK
    # -----------------------------------------------------

    if not all_results:

        st.error(
            f'"{product}" için fiyatlı sonuç bulunamadı.'
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
    # FİYAT FARKI
    # -----------------------------------------------------

    if len(all_results) >= 2:

        low = min(
            x["price"]
            for x in all_results
        )

        high = max(
            x["price"]
            for x in all_results
        )

        st.info(
            f"💰 Fiyat aralığı: "
            f"**{low:,.2f} TL – {high:,.2f} TL**"
        )

    # -----------------------------------------------------
    # KATEGORİLER
    # -----------------------------------------------------

    st.divider()

    show_category(
        "Sıfır Ürünler",
        "🟢",
        new_results,
        "offer-new"
    )

    st.divider()

    show_category(
        "İkinci El",
        "🟠",
        used_results,
        "offer-used"
    )

    st.divider()

    show_category(
        "Yenilenmiş",
        "🔵",
        refurb_results,
        "offer-refurb"
    )
