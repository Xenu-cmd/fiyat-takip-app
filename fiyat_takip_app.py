import streamlit as st
import requests
import re
import html
from urllib.parse import urlparse


# =========================================================
# AYARLAR
# =========================================================

st.set_page_config(
    page_title="Akıllı Fiyat Karşılaştırma",
    page_icon="🔎",
    layout="wide"
)

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
    background:linear-gradient(
        135deg,
        #ecfdf5,
        #f0fdf4
    );

    border:2px solid #22c55e;
    border-radius:20px;
    padding:25px;
    margin:20px 0;
}

.best-title {
    color:#166534;
    font-size:20px;
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
    background:#fff;
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

.source-card {
    background:#f9fafb;
    border-radius:12px;
    padding:12px;
    margin:5px 0;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# BAŞLIK
# =========================================================

st.markdown(
    '<div class="main-title">'
    '🔎 Akıllı Fiyat Karşılaştırma'
    '</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Sıfır • İkinci El • Yenilenmiş'
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
# METİN TEMİZLE
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

def product_words(product):

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
        word
        for word in normalize(product).split()
        if len(word) >= 2
        and word not in stop_words
    ]


# =========================================================
# ALÂKA KONTROLÜ
# =========================================================

def relevance_score(
    product,
    title,
    description=""
):

    text = normalize(
        str(title)
        + " "
        + str(description)
    )

    words = product_words(
        product
    )

    score = 0

    for word in words:

        if word in text:
            score += 1

    return score


def is_relevant(
    product,
    title,
    description=""
):

    words = product_words(
        product
    )

    score = relevance_score(
        product,
        title,
        description
    )

    if len(words) <= 2:
        return score >= len(words)

    if len(words) == 3:
        return score >= 2

    return score >= 3


# =========================================================
# DOMAIN
# =========================================================

def get_domain(url):

    try:

        domain = urlparse(
            url
        ).netloc.lower()

        if domain.startswith("www."):
            domain = domain[4:]

        return domain

    except Exception:
        return ""


# =========================================================
# MAĞAZA ADI
# =========================================================

def get_store_name(
    url,
    fallback=""
):

    domain = get_domain(
        url
    )

    stores = {

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

        "grundig.com.tr":
            "Grundig"
    }

    return stores.get(
        domain,
        fallback or domain or "Mağaza"
    )


# =========================================================
# FİYAT BUL
# =========================================================

def extract_prices(text):

    if not text:
        return []

    text = str(text)

    text = text.replace(
        "\xa0",
        " "
    )

    patterns = [

        # 1.999,00 TL
        r'(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?)\s*(?:TL|₺)',

        # 1999,00 TL
        r'(\d{2,7}(?:,\d{1,2})?)\s*(?:TL|₺)',

        # TL 1.999,00
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

                number = float(
                    value
                )

                if 1 <= number <= 10_000_000:

                    prices.append(
                        number
                    )

            except Exception:
                pass

    return sorted(
        set(prices)
    )


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

def google_shopping_search(
    product
):

    return api_get(
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


# =========================================================
# SHOPPING SELLERS
# =========================================================

def google_shopping_sellers(
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
        timeout=90
    )


# =========================================================
# GOOGLE SEARCH
# =========================================================

def google_search(
    query
):

    return api_get(
        "/v1/google/search",
        {
            "query": query,
            "region": "TR",
            "page": 1
        },
        timeout=90
    )


# =========================================================
# SHOPPING SONUÇLARINI PARSE ET
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

        if not is_relevant(
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

        currency = str(
            price_data.get(
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

            price = float(
                price_data.get(
                    "current"
                )
            )

        except Exception:
            continue

        if price <= 0:
            continue

        ext = p.get(
            "ext",
            {}
        )

        results.append({

            "title": title,

            "price": price,

            "store": (
                p.get("seller")
                or "Mağaza"
            ),

            "url": p.get(
                "url",
                ""
            ),

            "condition": "Sıfır",

            "source": "Google Shopping",

            "product_id": p.get(
                "id"
            ),

            "gid": ext.get(
                "gid"
            ),

            "data_docid": ext.get(
                "data_docid"
            )
        })

    return results


# =========================================================
# SELLER SONUÇLARINI ESNEK PARSE ET
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

        # Seller satırlarında API yapısı
        # değişebileceği için birkaç alanı
        # kontrol ediyoruz.

        title = (
            row.get("title")
            or row.get("product_title")
            or product
        )

        store = (
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

        price = None

        price_data = row.get(
            "price"
        )

        if isinstance(
            price_data,
            dict
        ):

            price = (
                price_data.get(
                    "current"
                )
                or price_data.get(
                    "value"
                )
                or price_data.get(
                    "amount"
                )
            )

        elif price_data is not None:

            price = price_data

        if price is None:

            price = (
                row.get(
                    "current_price"
                )
                or row.get(
                    "price_current"
                )
                or row.get(
                    "amount"
                )
                or row.get(
                    "offer_price"
                )
            )

        try:

            price = float(
                price
            )

        except Exception:

            prices = extract_prices(
                str(row)
            )

            if prices:

                price = min(
                    prices
                )

        if price is None:
            continue

        if price <= 0:
            continue

        results.append({

            "title": title,

            "price": price,

            "store": store,

            "url": url,

            "condition": "Sıfır",

            "source": "Google Shopping • Satıcı"
        })

    return results


# =========================================================
# GOOGLE SEARCH PARSE
# =========================================================

def parse_google_results(
    data,
    product,
    condition,
    allowed_domains=None
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

        domain = get_domain(
            url
        )

        if allowed_domains:

            if domain not in allowed_domains:
                continue

        if not is_relevant(
            product,
            title,
            snippet
        ):
            continue

        prices = extract_prices(
            str(title)
            + " "
            + str(snippet)
        )

        if not prices:
            continue

        price = min(
            prices
        )

        results.append({

            "title": title,

            "price": price,

            "store": get_store_name(
                url
            ),

            "url": url,

            "condition": condition,

            "source": "Google Search"
        })

    return results


# =========================================================
# KAYNAK ARAMA
# =========================================================

def search_site(
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

    return parse_google_results(
        data,
        product,
        condition,
        {domain}
    )


# =========================================================
# SIFIR ÜRÜNLER
# =========================================================

def search_new(
    product,
    diagnostics
):

    results = []

    # -----------------------------
    # Google Shopping
    # -----------------------------

    shopping_data = (
        google_shopping_search(
            product
        )
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

    # -----------------------------
    # SELLERS
    # -----------------------------

    seller_count = 0

    # En fazla ilk 10 gerçek
    # ürün için satıcıları çek.

    for item in shopping_results[:10]:

        seller_data = (
            google_shopping_sellers(
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
        )

        seller_results = parse_sellers(
            seller_data,
            product
        )

        seller_count += len(
            seller_results
        )

        results.extend(
            seller_results
        )

    diagnostics[
        "Shopping Satıcıları"
    ] = seller_count

    # -----------------------------
    # MAĞAZA KAYNAKLARI
    # -----------------------------

    domains = [

        "akakce.com",

        "cimri.com",

        "hepsiburada.com",

        "trendyol.com",

        "n11.com",

        "amazon.com.tr"
    ]

    for domain in domains:

        found = search_site(
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

    domains = [

        "dolap.com",

        "sahibinden.com",

        "letgo.com"
    ]

    for domain in domains:

        total = 0

        for extra in [
            "ikinci el",
            "2.el",
            ""
        ]:

            found = search_site(
                product,
                domain,
                "İkinci El",
                extra
            )

            total += len(
                found
            )

            results.extend(
                found
            )

        diagnostics[
            domain
        ] = total

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

    domains = [

        "hepsiburada.com",

        "trendyol.com",

        "n11.com",

        "amazon.com.tr"
    ]

    for domain in domains:

        total = 0

        for extra in [
            "yenilenmiş",
            "refurbished",
            "renewed"
        ]:

            found = search_site(
                product,
                domain,
                "Yenilenmiş",
                extra
            )

            total += len(
                found
            )

            results.extend(
                found
            )

        diagnostics[
            "Yenilenmiş: " + domain
        ] = total

    return clean_results(
        results
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

        url = item.get(
            "url",
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
                store,
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
# EN UCUZ
# =========================================================

def show_best(
    results
):

    if not results:
        return

    cheapest = min(
        results,
        key=lambda x: x["price"]
    )

    title = html.escape(
        cheapest["title"]
    )

    store = html.escape(
        cheapest["store"]
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
                🏪 {store}
            </div>

            <div class="best-condition">
                📦 {condition}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    if cheapest.get(
        "url"
    ):

        st.link_button(
            "🛒 En Ucuz Sonuca Git",
            cheapest["url"]
        )


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

        st.info(
            "Bu kategoride doğrulanmış "
            "fiyatlı sonuç bulunamadı."
        )

        return

    for index, item in enumerate(
        results[:25],
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
                    {index}. {title_html}
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

        if item.get(
            "url"
        ):

            st.link_button(
                "🛒 Ürüne Git",
                item["url"]
            )


# =========================================================
# ÇALIŞTIR
# =========================================================

if search_button:

    if not product.strip():

        st.warning(
            "Lütfen ürün adı yaz."
        )

        st.stop()

    if not API_KEY:

        st.error(
            "SOCIALCRAWL_API_KEY bulunamadı."
        )

        st.info(
            "Streamlit → Settings → Secrets "
            "bölümüne API anahtarını ekle."
        )

        st.stop()

    product = product.strip()

    diagnostics = {}

    st.info(
        f"🔎 **{product}** için kaynaklar taranıyor..."
    )

    progress = st.progress(
        0
    )

    status = st.empty()

    # -----------------------------
    # SIFIR
    # -----------------------------

    status.write(
        "🟢 Mağazalar ve Google Shopping taranıyor..."
    )

    new_results = search_new(
        product,
        diagnostics
    )

    progress.progress(
        40
    )

    # -----------------------------
    # İKİNCİ EL
    # -----------------------------

    status.write(
        "🟠 Dolap, Sahibinden ve Letgo taranıyor..."
    )

    used_results = search_used(
        product,
        diagnostics
    )

    progress.progress(
        70
    )

    # -----------------------------
    # YENİLENMİŞ
    # -----------------------------

    status.write(
        "🔵 Yenilenmiş ürünler taranıyor..."
    )

    refurb_results = search_refurbished(
        product,
        diagnostics
    )

    progress.progress(
        100
    )

    progress.empty()
    status.empty()

    # -----------------------------
    # TÜM SONUÇLAR
    # -----------------------------

    all_results = clean_results(
        new_results
        + used_results
        + refurb_results
    )

    # =====================================================
    # KAYNAK TEŞHİS
    # =====================================================

    with st.expander(
        "🔧 Arama kaynakları",
        expanded=False
    ):

        st.write(
            "Bu bölüm hangi kaynaktan gerçekten "
            "kaç fiyat geldiğini gösterir."
        )

        for source, count in diagnostics.items():

            st.markdown(
                f"""
                <div class="source-card">
                    <b>{html.escape(str(source))}</b>
                    :
                    {count} fiyatlı sonuç
                </div>
                """,
                unsafe_allow_html=True
            )

    # =====================================================
    # SONUÇ YOK
    # =====================================================

    if not all_results:

        st.error(
            f'"{product}" için doğrulanmış '
            f'fiyat bulunamadı.'
        )

        st.stop()

    # =====================================================
    # EN UCUZ
    # =====================================================

    show_best(
        all_results
    )

    # =====================================================
    # ÖZET
    # =====================================================

    st.divider()

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "🟢 Sıfır",
            len(new_results)
        )

    with col2:

        st.metric(
            "🟠 İkinci El",
            len(used_results)
        )

    with col3:

        st.metric(
            "🔵 Yenilenmiş",
            len(refurb_results)
        )

    with col4:

        st.metric(
            "💰 Toplam",
            len(all_results)
        )

    # =====================================================
    # FİYAT ARALIĞI
    # =====================================================

    if len(all_results) >= 2:

        cheapest_price = min(
            x["price"]
            for x in all_results
        )

        highest_price = max(
            x["price"]
            for x in all_results
        )

        st.info(
            f"💰 Bulunan fiyat aralığı: "
            f"**{cheapest_price:,.2f} TL** — "
            f"**{highest_price:,.2f} TL**"
        )

    # =====================================================
    # SONUÇLAR
    # =====================================================

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
