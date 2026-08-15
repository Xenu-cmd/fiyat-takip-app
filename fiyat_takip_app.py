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
# API
# =========================================================

BASE_URL = "https://www.socialcrawl.dev"

try:
    API_KEY = st.secrets["SOCIALCRAWL_API_KEY"]
except Exception:
    API_KEY = ""


HEADERS = {
    "x-api-key": API_KEY,
    "Accept": "application/json"
}


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
    margin-top:10px;
}

.subtitle {
    text-align:center;
    color:#6b7280;
    margin-bottom:28px;
}

.best-card {
    background:linear-gradient(135deg,#ecfdf5,#f0fdf4);
    border:2px solid #22c55e;
    border-radius:20px;
    padding:26px;
    margin:20px 0;
}

.best-title {
    color:#166534;
    font-size:21px;
    font-weight:900;
}

.best-product {
    color:#111827;
    font-size:25px;
    font-weight:900;
    margin-top:8px;
}

.best-price {
    color:#15803d;
    font-size:42px;
    font-weight:900;
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
    background:white;
    border-radius:15px;
    padding:18px;
    margin-bottom:12px;
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
    font-size:14px;
    margin-top:5px;
}

.source {
    background:#f9fafb;
    padding:10px 14px;
    border-radius:10px;
    margin-bottom:6px;
}

.warning-box {
    background:#fff7ed;
    border:1px solid #fed7aa;
    border-radius:12px;
    padding:15px;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# BAŞLIK
# =========================================================

st.markdown(
    '<div class="main-title">🔎 Akıllı Fiyat Karşılaştırma</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Sıfır • İkinci El • Yenilenmiş ürünleri karşılaştır'
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
    "🔍 Fiyatları Ara",
    type="primary",
    use_container_width=True
)


# =========================================================
# YARDIMCI
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


def get_words(product):

    stop_words = {
        "ve",
        "ile",
        "icin",
        "bir",
        "the",
        "for",
        "satin",
        "al"
    }

    return [
        x
        for x in normalize(product).split()
        if len(x) >= 2
        and x not in stop_words
    ]


def relevance_score(
    product,
    title,
    description=""
):

    text = normalize(
        f"{title} {description}"
    )

    words = get_words(product)

    score = 0

    for word in words:

        if word in text:
            score += 1

    return score


def relevant(
    product,
    title,
    description=""
):

    words = get_words(product)

    if not words:
        return False

    score = relevance_score(
        product,
        title,
        description
    )

    # Grundig Club gibi iki kelimelik
    # aramalarda ikisinin de bulunmasını isteriz.

    if len(words) <= 2:
        return score >= len(words)

    if len(words) == 3:
        return score >= 2

    return score >= 3


# =========================================================
# DOMAIN
# =========================================================

def domain_of(url):

    try:

        domain = urlparse(
            url
        ).netloc.lower()

        if domain.startswith("www."):
            domain = domain[4:]

        return domain

    except Exception:

        return ""


def store_name(
    url,
    fallback=""
):

    domain = domain_of(url)

    names = {

        "akakce.com":
            "Akakçe",

        "cimri.com":
            "Cimri",

        "hepsiburada.com":
            "Hepsiburada",

        "trendyol.com":
            "Trendyol",

        "n11.com":
            "N11",

        "amazon.com.tr":
            "Amazon Türkiye",

        "dolap.com":
            "Dolap",

        "sahibinden.com":
            "Sahibinden",

        "letgo.com":
            "Letgo",

        "gizerler.com":
            "Gizerler"
    }

    return names.get(
        domain,
        fallback or domain or "Mağaza"
    )


# =========================================================
# FİYAT
# =========================================================

def extract_prices(text):

    if not text:
        return []

    text = str(text).replace(
        "\xa0",
        " "
    )

    patterns = [

        # 1.999,00 TL
        r'(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?)\s*(?:TL|₺)',

        # 1999,00 TL
        r'(\d{2,7}(?:,\d{1,2})?)\s*(?:TL|₺)',

        # TL 1.999
        r'(?:TL|₺)\s*(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?)',

        # TL 1999
        r'(?:TL|₺)\s*(\d{2,7}(?:,\d{1,2})?)'
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

                if "." in value and "," in value:

                    value = value.replace(
                        ".",
                        ""
                    )

                    value = value.replace(
                        ",",
                        "."
                    )

                elif "," in value:

                    parts = value.split(",")

                    if len(parts[-1]) <= 2:

                        value = value.replace(
                            ",",
                            "."
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

                if 1 <= number <= 10_000_000:

                    prices.append(number)

            except Exception:
                pass

    return sorted(
        set(prices)
    )


# =========================================================
# API GET
# =========================================================

def api_get(
    endpoint,
    params,
    timeout=120
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

        if not data.get(
            "success",
            False
        ):
            return None

        return data

    except Exception:

        return None


# =========================================================
# GOOGLE SHOPPING
# =========================================================

def shopping_search(product):

    return api_get(
        "/v1/google_shopping/product-search",
        {
            "query": product,
            "country": "Turkey",
            "language": "tr",
            "depth": 120,
            "sort_by": "price_low_to_high"
        },
        timeout=180
    )


# =========================================================
# SELLERS
# =========================================================

def shopping_sellers(
    product_id=None,
    gid=None,
    data_docid=None
):

    params = {
        "country": "Turkey",
        "language": "tr"
    }

    if product_id:
        params["product_id"] = product_id

    elif gid:
        params["gid"] = gid

    elif data_docid:
        params["data_docid"] = data_docid

    else:
        return None

    return api_get(
        "/v1/google_shopping/sellers",
        params,
        timeout=120
    )


# =========================================================
# GOOGLE SEARCH
# =========================================================

def google_search(query):

    return api_get(
        "/v1/google/search",
        {
            "query": query,
            "region": "TR",
            "page": 1
        },
        timeout=120
    )


# =========================================================
# SHOPPING PARSE
# =========================================================

def parse_shopping(
    data,
    product
):

    results = []

    if not data:
        return results

    items = (
        data
        .get("data", {})
        .get("items", [])
    )

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

        price = p.get(
            "price",
            {}
        )

        if not isinstance(
            price,
            dict
        ):
            continue

        currency = str(
            price.get(
                "currency",
                ""
            )
        ).upper()

        if currency not in {
            "TRY",
            "TL"
        }:
            continue

        try:

            current = float(
                price.get(
                    "current"
                )
            )

        except Exception:

            continue

        if current <= 0:
            continue

        ext = p.get(
            "ext",
            {}
        )

        results.append({

            "title":
                title,

            "price":
                current,

            "store":
                p.get(
                    "seller"
                ) or "Mağaza",

            "url":
                p.get(
                    "url",
                    ""
                ),

            "condition":
                "Sıfır",

            "source":
                "Google Shopping",

            "product_id":
                p.get(
                    "id"
                ),

            "gid":
                ext.get(
                    "gid"
                ),

            "data_docid":
                ext.get(
                    "data_docid"
                )
        })

    return results


# =========================================================
# SELLER PARSE
# =========================================================

def parse_sellers(
    data,
    product
):

    results = []

    if not data:
        return results

    items = (
        data
        .get("data", {})
        .get("items", [])
    )

    for row in items:

        title = (
            row.get("title")
            or row.get("product_title")
            or product
        )

        seller = (
            row.get("seller")
            or row.get("merchant")
            or row.get("store")
            or row.get("seller_name")
            or row.get("merchant_name")
            or "Mağaza"
        )

        url = (
            row.get("url")
            or row.get("link")
            or row.get("offer_url")
            or ""
        )

        price_value = None

        price = row.get(
            "price"
        )

        if isinstance(
            price,
            dict
        ):

            price_value = (
                price.get("current")
                or price.get("value")
                or price.get("amount")
            )

        elif price is not None:

            price_value = price

        if price_value is None:

            price_value = (
                row.get("current_price")
                or row.get("price_current")
                or row.get("amount")
                or row.get("offer_price")
            )

        try:

            price_value = float(
                price_value
            )

        except Exception:

            found = extract_prices(
                str(row)
            )

            if found:
                price_value = min(found)

        if price_value is None:
            continue

        if price_value <= 0:
            continue

        results.append({

            "title":
                title,

            "price":
                price_value,

            "store":
                seller,

            "url":
                url,

            "condition":
                "Sıfır",

            "source":
                "Google Shopping • Satıcı"
        })

    return results


# =========================================================
# GOOGLE SEARCH PARSE
# =========================================================

def parse_google(
    data,
    product,
    condition,
    allowed_domains
):

    results = []

    if not data:
        return results

    items = (
        data
        .get("data", {})
        .get("items", [])
    )

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

        domain = domain_of(
            url
        )

        if domain not in allowed_domains:
            continue

        if not relevant(
            product,
            title,
            snippet
        ):
            continue

        prices = extract_prices(
            f"{title} {snippet}"
        )

        if not prices:
            continue

        results.append({

            "title":
                title,

            "price":
                min(prices),

            "store":
                store_name(url),

            "url":
                url,

            "condition":
                condition,

            "source":
                "Google Search"
        })

    return results


# =========================================================
# KAYNAK TARAMA
# =========================================================

def search_source(
    product,
    domain,
    condition,
    extra=""
):

    query = (
        f'"{product}" '
        f'site:{domain} '
        f'{extra}'
    ).strip()

    data = google_search(
        query
    )

    return parse_google(
        data,
        product,
        condition,
        {domain}
    )


# =========================================================
# TEMİZLE
# =========================================================

def clean_results(
    results
):

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

        url = item.get(
            "url",
            ""
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

        condition = item.get(
            "condition",
            ""
        )

        key = (
            url.split("?")[0]
            if url
            else f"{title}|{store}|{price}",
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
# SIFIR
# =========================================================

def search_new(
    product,
    diagnostics
):

    results = []

    # -----------------------------------
    # GOOGLE SHOPPING
    # -----------------------------------

    shopping_data = shopping_search(
        product
    )

    shopping_results = parse_shopping(
        shopping_data,
        product
    )

    diagnostics[
        "Google Shopping"
    ] = len(
        shopping_results
    )

    results.extend(
        shopping_results
    )

    # -----------------------------------
    # SATICALAR
    # -----------------------------------

    seller_results = []

    for item in shopping_results[:8]:

        seller_data = shopping_sellers(

            product_id=item.get(
                "product_id"
            ),

            gid=item.get(
                "gid"
            ),

            data_docid=item.get(
                "data_docid"
            )
        )

        parsed = parse_sellers(
            seller_data,
            product
        )

        seller_results.extend(
            parsed
        )

    diagnostics[
        "Google Shopping Satıcıları"
    ] = len(
        seller_results
    )

    results.extend(
        seller_results
    )

    # -----------------------------------
    # MAĞAZALAR
    # -----------------------------------

    sources = [

        "akakce.com",
        "cimri.com",
        "hepsiburada.com",
        "trendyol.com",
        "n11.com",
        "amazon.com.tr"
    ]

    for domain in sources:

        found = search_source(
            product,
            domain,
            "Sıfır",
            "fiyat"
        )

        diagnostics[
            domain
        ] = len(found)

        results.extend(
            found
        )

    return clean_results(
        results
    )


# =========================================================
# İKİNCİ EL
# =========================================================

def search_used(
    product,
    diagnostics
):

    results = []

    sources = [

        "dolap.com",
        "sahibinden.com",
        "letgo.com"
    ]

    for domain in sources:

        found_total = 0

        for extra in [
            "ikinci el",
            "2.el",
            ""
        ]:

            found = search_source(
                product,
                domain,
                "İkinci El",
                extra
            )

            found_total += len(
                found
            )

            results.extend(
                found
            )

        diagnostics[
            "İkinci El • " + domain
        ] = found_total

    return clean_results(
        results
    )


# =========================================================
# YENİLENMİŞ
# =========================================================

def search_refurbished(
    product,
    diagnostics
):

    results = []

    sources = [

        "hepsiburada.com",
        "trendyol.com",
        "n11.com",
        "amazon.com.tr"
    ]

    for domain in sources:

        found_total = 0

        for extra in [
            "yenilenmiş",
            "refurbished",
            "renewed"
        ]:

            found = search_source(
                product,
                domain,
                "Yenilenmiş",
                extra
            )

            found_total += len(
                found
            )

            results.extend(
                found
            )

        diagnostics[
            "Yenilenmiş • " + domain
        ] = found_total

    return clean_results(
        results
    )


# =========================================================
# EN UCUZ KART
# =========================================================

def show_best(
    results
):

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
        best["condition"]
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
            "🛒 En Ucuz Sonuca Git",
            best["url"]
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
            "Bu kategoride doğrulanabilir "
            "fiyat bulunamadı."
        )

        return

    for i, item in enumerate(
        results[:20],
        1
    ):

        title_html = html.escape(
            item["title"]
        )

        store_html = html.escape(
            item["store"]
        )

        condition_html = html.escape(
            item["condition"]
        )

        st.markdown(
            f"""
            <div class="offer {css}">

                <div class="offer-title">
                    {i}. {title_html}
                </div>

                <div class="offer-price">
                    {item["price"]:,.2f} TL
                </div>

                <div class="offer-store">
                    🏪 {store_html}
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
                "🛒 Ürüne Git",
                item["url"]
            )


# =========================================================
# UYGULAMA
# =========================================================

if search_button:

    if not product.strip():

        st.warning(
            "Önce bir ürün adı yaz."
        )

        st.stop()

    if not API_KEY:

        st.error(
            "SocialCrawl API anahtarı bulunamadı."
        )

        st.info(
            "Streamlit → Settings → Secrets "
            "bölümündeki SOCIALCRAWL_API_KEY "
            "ayarını kontrol et."
        )

        st.stop()

    product = product.strip()

    diagnostics = {}

    st.info(
        f"🔎 **{product}** için kaynaklar taranıyor..."
    )

    progress = st.progress(0)

    status = st.empty()

    # -----------------------------------
    # SIFIR
    # -----------------------------------

    status.write(
        "🟢 Sıfır ürünler aranıyor..."
    )

    new_results = search_new(
        product,
        diagnostics
    )

    progress.progress(40)

    # -----------------------------------
    # İKİNCİ EL
    # -----------------------------------

    status.write(
        "🟠 Dolap, Sahibinden ve Letgo aranıyor..."
    )

    used_results = search_used(
        product,
        diagnostics
    )

    progress.progress(70)

    # -----------------------------------
    # YENİLENMİŞ
    # -----------------------------------

    status.write(
        "🔵 Yenilenmiş ürünler aranıyor..."
    )

    refurbished_results = search_refurbished(
        product,
        diagnostics
    )

    progress.progress(100)

    progress.empty()
    status.empty()

    # -----------------------------------
    # TÜM SONUÇLAR
    # -----------------------------------

    all_results = clean_results(
        new_results
        + used_results
        + refurbished_results
    )

    # -----------------------------------
    # TEŞHİS
    # -----------------------------------

    with st.expander(
        "🔧 Kaynak durumu",
        expanded=False
    ):

        st.caption(
            "Burada uygulamanın hangi kaynaktan "
            "kaç doğrulanabilir fiyat alabildiğini "
            "görebilirsin."
        )

        for source, count in diagnostics.items():

            st.markdown(
                f"""
                <div class="source">
                    <b>{html.escape(str(source))}</b>
                    &nbsp; → &nbsp;
                    {count} sonuç
                </div>
                """,
                unsafe_allow_html=True
            )

    # -----------------------------------
    # SONUÇ YOK
    # -----------------------------------

    if not all_results:

        st.error(
            f'"{product}" için doğrulanabilir '
            f'fiyat bulunamadı.'
        )

        st.stop()

    # -----------------------------------
    # EN UCUZ
    # -----------------------------------

    show_best(
        all_results
    )

    # -----------------------------------
    # ÖZET
    # -----------------------------------

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
            len(refurbished_results)
        )

    with c4:

        st.metric(
            "💰 Toplam",
            len(all_results)
        )

    # -----------------------------------
    # FİYAT ARALIĞI
    # -----------------------------------

    prices = [
        x["price"]
        for x in all_results
        if x.get("price") is not None
    ]

    if len(prices) >= 2:

        low = min(prices)
        high = max(prices)

        st.info(
            f"💰 Fiyat aralığı: "
            f"**{low:,.2f} TL** — "
            f"**{high:,.2f} TL**"
        )

    # -----------------------------------
    # SONUÇLAR
    # -----------------------------------

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
        refurbished_results,
        "offer-refurb"
    )
