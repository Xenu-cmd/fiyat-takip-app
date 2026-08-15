import streamlit as st
import requests
import re
import html
import time
from urllib.parse import urlparse, quote_plus


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
    margin-bottom: 4px;
}

.subtitle {
    text-align: center;
    color: #6b7280;
    margin-bottom: 28px;
}

.best-card {
    background: linear-gradient(
        135deg,
        #ecfdf5,
        #f0fdf4
    );

    border: 2px solid #22c55e;
    border-radius: 20px;
    padding: 26px;
    margin: 20px 0;

    box-shadow:
        0 8px 25px rgba(0,0,0,0.05);
}

.best-title {
    font-size: 21px;
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
    font-size: 42px;
    font-weight: 900;
    color: #15803d;
    margin-top: 8px;
}

.best-store {
    font-size: 17px;
    margin-top: 8px;
    font-weight: 700;
}

.best-condition {
    font-weight: 800;
    margin-top: 6px;
}

.offer {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 16px;
    padding: 18px;
    margin-bottom: 10px;

    box-shadow:
        0 3px 12px rgba(0,0,0,0.04);
}

.offer.new {
    border-left: 6px solid #22c55e;
}

.offer.used {
    border-left: 6px solid #f97316;
}

.offer.refurbished {
    border-left: 6px solid #3b82f6;
}

.offer-title {
    font-size: 18px;
    font-weight: 800;
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
    margin-top: 5px;
}

.offer-source {
    color: #6b7280;
    font-size: 13px;
    margin-top: 5px;
}

.offer-condition {
    color: #374151;
    font-size: 14px;
    font-weight: 700;
    margin-top: 5px;
}

.source-ok {
    background: #ecfdf5;
    border: 1px solid #bbf7d0;
    padding: 10px;
    border-radius: 10px;
    margin-bottom: 6px;
}

.source-zero {
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    padding: 10px;
    border-radius: 10px;
    margin-bottom: 6px;
}

.source-error {
    background: #fff7ed;
    border: 1px solid #fed7aa;
    padding: 10px;
    border-radius: 10px;
    margin-bottom: 6px;
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
    'Sıfır • İkinci El • Yenilenmiş • Satıcı Karşılaştırma'
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

HEADERS = {
    "x-api-key": API_KEY,
    "Accept": "application/json",
    "User-Agent": (
        "Mozilla/5.0 "
        "AppleWebKit/537.36 "
        "Chrome/131.0 Safari/537.36"
    )
}


# =========================================================
# ARAMA KUTUSU
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
# NORMALİZE
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
# ÖNEMLİ KELİMELER
# =========================================================

def product_words(product_name):

    stop_words = {
        "ve",
        "ile",
        "icin",
        "bir",
        "urun",
        "ürün",
        "fiyat",
        "satin",
        "satın",
        "al",
        "the",
        "for"
    }

    words = normalize(
        product_name
    ).split()

    return [
        word
        for word in words
        if len(word) >= 2
        and word not in stop_words
    ]


# =========================================================
# ÜRÜN SKORU
# =========================================================

def relevance_score(
    product_name,
    title,
    description=""
):

    words = product_words(
        product_name
    )

    text = normalize(
        str(title) + " " +
        str(description)
    )

    score = 0

    for word in words:

        if word in text:
            score += 1

    return score


def is_relevant(
    product_name,
    title,
    description=""
):

    words = product_words(
        product_name
    )

    score = relevance_score(
        product_name,
        title,
        description
    )

    if not words:
        return False

    # İki kelimelik ürün:
    # Grundig Club
    # ikisi de bulunmalı.

    if len(words) == 1:
        return score >= 1

    if len(words) == 2:
        return score >= 2

    if len(words) == 3:
        return score >= 2

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

        if isinstance(
            value,
            (int, float)
        ):

            number = float(value)

            if 0 < number <= 10_000_000:
                return number

            return None

        value = str(
            value
        ).strip()

        value = value.replace(
            "₺",
            ""
        )

        value = value.replace(
            "TL",
            ""
        )

        value = value.strip()

        if "," in value and "." in value:

            # 1.999,00
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

            if len(parts[-1]) in (1, 2):

                # 1999,99
                value = value.replace(
                    ",",
                    "."
                )

            else:

                # 1,999
                value = value.replace(
                    ",",
                    ""
                )

        elif "." in value:

            parts = value.split(".")

            if len(parts[-1]) == 3:

                # 1.999
                value = value.replace(
                    ".",
                    ""
                )

        number = float(
            value
        )

        if 0 < number <= 10_000_000:
            return number

    except Exception:
        pass

    return None


# =========================================================
# DOMAIN
# =========================================================

def get_domain(url):

    try:

        parsed = urlparse(
            str(url)
        )

        domain = parsed.netloc.lower()

        if domain.startswith(
            "www."
        ):

            domain = domain[4:]

        return domain

    except Exception:

        return ""


# =========================================================
# MAĞAZA ADI
# =========================================================

def store_name(
    seller,
    url
):

    seller = str(
        seller or ""
    ).strip()

    if seller:
        return seller

    domain = get_domain(
        url
    )

    known = {

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

        "akakce.com":
            "Akakçe",

        "cimri.com":
            "Cimri"
    }

    return known.get(
        domain,
        domain or "Mağaza"
    )


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

            headers=HEADERS,

            timeout=timeout
        )

        status = response.status_code

        try:

            payload = response.json()

        except Exception:

            payload = None

        if status != 200:

            return {
                "success": False,
                "status": status,
                "error": (
                    str(payload)
                    if payload
                    else response.text[:500]
                ),
                "data": payload
            }

        if not isinstance(
            payload,
            dict
        ):

            return {
                "success": False,
                "status": status,
                "error": "API JSON döndürmedi.",
                "data": None
            }

        return {
            "success": payload.get(
                "success",
                True
            ),
            "status": status,
            "error": None,
            "data": payload
        }

    except requests.exceptions.Timeout:

        return {
            "success": False,
            "status": 504,
            "error": "API zaman aşımı.",
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

def google_product_search(
    query
):

    return api_get(

        "/v1/google_shopping/product-search",

        {
            "query":
                query,

            "country":
                "Turkey",

            "language":
                "tr",

            "depth":
                40
        },

        timeout=240
    )


# =========================================================
# GERÇEK API CEVABINI OKU
#
# ÖNEMLİ:
#
# Senin verdiğin JSON:
#
# data:
#   items:
#      product:
#
# Burada data.items kullanıyoruz.
# =========================================================

def extract_api_items(
    payload
):

    if not isinstance(
        payload,
        dict
    ):

        return []

    root_data = payload.get(
        "data",
        {}
    )

    if not isinstance(
        root_data,
        dict
    ):

        return []

    # DOĞRU YAPI
    items = root_data.get(
        "items",
        []
    )

    if isinstance(
        items,
        list
    ):

        return items

    return []


# =========================================================
# GOOGLE ÜRÜNLERİNİ OKU
# =========================================================

def parse_google_products(
    response,
    query
):

    results = []

    if not response.get(
        "success"
    ):

        return results

    payload = response.get(
        "data"
    )

    items = extract_api_items(
        payload
    )

    for item in items:

        if not isinstance(
            item,
            dict
        ):
            continue

        product_data = item.get(
            "product",
            {}
        )

        if not isinstance(
            product_data,
            dict
        ):
            continue

        title = product_data.get(
            "title",
            ""
        )

        description = product_data.get(
            "description",
            ""
        )

        # ---------------------------------------------
        # ÜRÜN EŞLEŞTİRME
        # ---------------------------------------------

        if not is_relevant(
            query,
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

        current = parse_price(
            price_data.get(
                "current"
            )
        )

        if current is None:
            continue

        currency = str(
            price_data.get(
                "currency",
                ""
            )
        ).upper()

        # ---------------------------------------------
        # SADECE TÜRKİYE FİYATI
        # ---------------------------------------------

        if currency not in {
            "TRY",
            "TL",
            "₺"
        }:

            continue

        url = product_data.get(
            "url",
            ""
        )

        seller = product_data.get(
            "seller",
            ""
        )

        ext = product_data.get(
            "ext",
            {}
        )

        if not isinstance(
            ext,
            dict
        ):

            ext = {}

        results.append({

            "title":
                title,

            "price":
                current,

            "store":
                store_name(
                    seller,
                    url
                ),

            "url":
                url,

            "condition":
                "Sıfır",

            "source":
                "Google Shopping",

            "product_id":
                product_data.get(
                    "id"
                ),

            "gid":
                ext.get(
                    "gid"
                ),

            "data_docid":
                ext.get(
                    "data_docid"
                ),

            "rating":
                product_data.get(
                    "rating"
                )
        })

    return results


# =========================================================
# HTML ARAMA
#
# Google Shopping'de sonuç çıkmazsa
# ikinci bir yol olarak HTML araması.
#
# Burada doğrudan alışveriş sitelerinin
# veritabanını kopyalamıyoruz.
# =========================================================

def web_search(
    query,
    condition
):

    url = (
        "https://www.google.com/search?"
        "q=" + quote_plus(query)
    )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/131.0 Safari/537.36"
        ),
        "Accept-Language":
            "tr-TR,tr;q=0.9"
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=20
        )

        if response.status_code != 200:
            return []

        text = response.text

        soup = BeautifulSoup(
            text,
            "html.parser"
        )

    except Exception:

        return []

    results = []

    # Google sonuçlarındaki normal linkler
    for link in soup.select(
        "a"
    ):

        href = link.get(
            "href",
            ""
        )

        title = link.get_text(
            " ",
            strip=True
        )

        if not href or not title:
            continue

        if not href.startswith(
            "http"
        ):
            continue

        combined = (
            title + " " + href
        )

        if not is_relevant(
            product,
            title,
            combined
        ):

            continue

        # -------------------------------------------------
        # FİYAT
        # -------------------------------------------------

        price = extract_price_from_text(
            combined
        )

        if price is None:

            continue

        store = store_name(
            "",
            href
        )

        results.append({

            "title":
                title[:250],

            "price":
                price,

            "store":
                store,

            "url":
                href,

            "condition":
                condition,

            "source":
                "Web araması",

            "product_id":
                None,

            "gid":
                None,

            "data_docid":
                None
        })

    return results


# =========================================================
# METİNDEN FİYAT
# =========================================================

def extract_price_from_text(
    text
):

    if not text:
        return None

    text = (
        str(text)
        .replace(
            "\xa0",
            " "
        )
    )

    patterns = [

        r'(\d{1,3}(?:[.\s]\d{3})+(?:,\d{1,2})?)\s*(?:TL|₺)',

        r'(\d{3,7}(?:,\d{1,2})?)\s*(?:TL|₺)',

        r'(?:TL|₺)\s*(\d{3,7}(?:[.,]\d{1,2})?)'
    ]

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        for value in matches:

            price = parse_price(
                value
            )

            if price is not None:

                return price

    return None


# =========================================================
# İKİNCİ EL ARAMA
# =========================================================

def search_used_sources(
    query
):

    results = []

    sources = {

        "Dolap":
            f'"{query}" site:dolap.com',

        "Sahibinden":
            f'"{query}" site:sahibinden.com',

        "Letgo":
            f'"{query}" site:letgo.com'
    }

    for source, search_query in sources.items():

        found = web_search(
            search_query,
            "İkinci El"
        )

        for item in found:

            item["store"] = source

            item["condition"] = (
                "İkinci El"
            )

            results.append(
                item
            )

        time.sleep(
            0.5
        )

    return results


# =========================================================
# YENİLENMİŞ ARAMA
# =========================================================

def search_refurbished(
    query
):

    results = []

    queries = [

        f'"{query}" yenilenmiş',

        f'"{query}" refurbished',

        f'"{query}" renewed'
    ]

    for search_query in queries:

        found = web_search(
            search_query,
            "Yenilenmiş"
        )

        for item in found:

            item["condition"] = (
                "Yenilenmiş"
            )

            results.append(
                item
            )

        time.sleep(
            0.4
        )

    return results


# =========================================================
# TEMİZLE
# =========================================================

def clean_results(
    results
):

    unique = {}

    for item in results:

        price = parse_price(
            item.get(
                "price"
            )
        )

        if price is None:
            continue

        title = item.get(
            "title",
            ""
        )

        store = item.get(
            "store",
            ""
        )

        condition = item.get(
            "condition",
            ""
        )

        url = item.get(
            "url",
            ""
        )

        key = (
            normalize(title),
            normalize(store),
            condition,
            url.split("?")[0]
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
# SONUÇLARI KATEGORİLENDİR
# =========================================================

def classify(
    item
):

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

    source = normalize(
        item.get(
            "source",
            ""
        )
    )

    combined = (
        condition + " " +
        title + " " +
        source
    )

    if any(
        x in combined
        for x in [
            "yenilenmis",
            "refurbished",
            "renewed"
        ]
    ):

        return "Yenilenmiş"

    if any(
        x in combined
        for x in [
            "ikinci el",
            "2 el",
            "2.el",
            "dolap",
            "sahibinden",
            "letgo",
            "kullanilmis"
        ]
    ):

        return "İkinci El"

    return "Sıfır"


# =========================================================
# EN UCUZ
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
        classify(best)
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

    if best.get(
        "url"
    ):

        st.link_button(
            "🛒 Bu Sonuca Git",
            best["url"]
        )


# =========================================================
# KATEGORİ GÖSTER
# =========================================================

def show_category(
    title,
    emoji,
    results,
    css_class
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

    for index, item in enumerate(
        results[:30],
        1
    ):

        safe_title = html.escape(
            item["title"]
        )

        safe_store = html.escape(
            item["store"]
        )

        safe_source = html.escape(
            item["source"]
        )

        safe_condition = html.escape(
            classify(item)
        )

        st.markdown(
            f"""
            <div class="offer {css_class}">

                <div class="offer-title">
                    {index}. {safe_title}
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
                    🔎 Kaynak: {safe_source}
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
            "❌ SOCIALCRAWL_API_KEY bulunamadı."
        )

        st.code(
            'SOCIALCRAWL_API_KEY = "sc_..."',
            language="toml"
        )

        st.stop()

    query = product.strip()

    diagnostics = {}

    st.info(
        f"🔎 **{query}** aranıyor..."
    )

    # -----------------------------------------------------
    # GOOGLE SHOPPING
    # -----------------------------------------------------

    with st.spinner(
        "Google Shopping taranıyor..."
    ):

        google_results = (
            search_google(
                query
            )
        )

    # -----------------------------------------------------
    # İKİNCİ EL
    # -----------------------------------------------------

    with st.spinner(
        "İkinci el kaynakları kontrol ediliyor..."
    ):

        used_results = (
            search_used_sources(
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
    # BİRLEŞTİR
    # -----------------------------------------------------

    google_results = clean_results(
        google_results
    )

    used_results = clean_results(
        used_results
    )

    refurbished_results = clean_results(
        refurbished_results
    )

    # -----------------------------------------------------
    # KAYNAK TEŞHİSİ
    # -----------------------------------------------------

    diagnostics[
        "Google Shopping"
    ] = len(
        google_results
    )

    diagnostics[
        "İkinci El • Dolap"
    ] = len([
        x for x in used_results
        if x["store"] == "Dolap"
    ])

    diagnostics[
        "İkinci El • Sahibinden"
    ] = len([
        x for x in used_results
        if x["store"] == "Sahibinden"
    ])

    diagnostics[
        "İkinci El • Letgo"
    ] = len([
        x for x in used_results
        if x["store"] == "Letgo"
    ])

    diagnostics[
        "Yenilenmiş"
    ] = len(
        refurbished_results
    )

    all_results = (
        google_results
        + used_results
        + refurbished_results
    )

    all_results = clean_results(
        all_results
    )

    # -----------------------------------------------------
    # KAYNAK DURUMU
    # -----------------------------------------------------

    with st.expander(
        "🔧 Kaynak Durumu",
        expanded=False
    ):

        for source, count in diagnostics.items():

            if count > 0:

                st.markdown(
                    f"""
                    <div class="source-ok">
                        🟢 <b>{html.escape(source)}</b>
                        → {count} sonuç
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            else:

                st.markdown(
                    f"""
                    <div class="source-zero">
                        ⚪ <b>{html.escape(source)}</b>
                        → 0 sonuç
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    # -----------------------------------------------------
    # HAM API TEŞHİSİ
    # -----------------------------------------------------

    if not google_results:

        with st.expander(
            "🧪 Google Shopping API teşhisi",
            expanded=False
        ):

            st.write(
                "API cevap verdi ancak "
                "uygun TL ürünü ayrıştırılamadı."
            )

            st.write(
                "Özellikle `data.items` yapısı "
                "kontrol edildi."
            )

    # -----------------------------------------------------
    # HİÇBİR SONUÇ YOK
    # -----------------------------------------------------

    if not all_results:

        st.error(
            f'"{query}" için doğrulanabilir '
            f'fiyat bulunamadı.'
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

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "🟢 Sıfır",
            len(
                google_results
            )
        )

    with col2:

        st.metric(
            "🟠 İkinci El",
            len(
                used_results
            )
        )

    with col3:

        st.metric(
            "🔵 Yenilenmiş",
            len(
                refurbished_results
            )
        )

    with col4:

        st.metric(
            "📦 Toplam",
            len(
                all_results
            )
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

        cheapest = min(
            prices
        )

        expensive = max(
            prices
        )

        difference = (
            expensive -
            cheapest
        )

        st.info(
            f"💰 En düşük: "
            f"**{cheapest:,.2f} TL**  "
            f"• En yüksek: "
            f"**{expensive:,.2f} TL**  "
            f"• Fark: "
            f"**{difference:,.2f} TL**"
        )

    st.divider()

    # -----------------------------------------------------
    # SIFIR
    # -----------------------------------------------------

    show_category(
        "Sıfır Ürünler",
        "🟢",
        google_results,
        "new"
    )

    st.divider()

    # -----------------------------------------------------
    # İKİNCİ EL
    # -----------------------------------------------------

    show_category(
        "İkinci El",
        "🟠",
        used_results,
        "used"
    )

    st.divider()

    # -----------------------------------------------------
    # YENİLENMİŞ
    # -----------------------------------------------------

    show_category(
        "Yenilenmiş",
        "🔵",
        refurbished_results,
        "refurbished"
    )
