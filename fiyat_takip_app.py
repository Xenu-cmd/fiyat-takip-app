import streamlit as st
import requests
import re
import html
from urllib.parse import urlparse


# =========================================================
# SAYFA AYARLARI
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
    background: linear-gradient(135deg,#ecfdf5,#f0fdf4);
    border: 2px solid #22c55e;
    border-radius: 20px;
    padding: 26px;
    margin: 20px 0;
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
    box-shadow: 0 3px 12px rgba(0,0,0,.04);
}

.new {
    border-left: 6px solid #22c55e;
}

.used {
    border-left: 6px solid #f97316;
}

.refurbished {
    border-left: 6px solid #3b82f6;
}

.offer-title {
    font-size: 18px;
    font-weight: 800;
}

.offer-price {
    font-size: 28px;
    font-weight: 900;
    margin-top: 6px;
}

.offer-store {
    color: #2563eb;
    font-weight: 800;
    margin-top: 5px;
}

.offer-condition {
    color: #6b7280;
    font-size: 14px;
    margin-top: 5px;
}

.source-row {
    background: #f9fafb;
    padding: 10px 14px;
    border-radius: 10px;
    margin-bottom: 5px;
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
    'Sıfır • İkinci El • Yenilenmiş'
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
    "Accept": "application/json"
}


# =========================================================
# ARAMA
# =========================================================

product_query = st.text_input(
    "Ürün adı",
    placeholder="Örn: Grundig Club BT Hoparlör"
)

search_button = st.button(
    "🔍 Fiyatları Ara",
    type="primary",
    use_container_width=True
)


# =========================================================
# METİN NORMALİZASYONU
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
# ARAMA KELİMELERİ
# =========================================================

def important_words(query):

    stop_words = {
        "ve",
        "ile",
        "icin",
        "bir",
        "the",
        "for",
        "satin",
        "al",
        "urun",
        "fiyat"
    }

    words = normalize(query).split()

    return [
        word
        for word in words
        if len(word) >= 2
        and word not in stop_words
    ]


# =========================================================
# ÜRÜN EŞLEŞTİRME
# =========================================================

def product_score(
    query,
    title,
    description=""
):

    query_words = important_words(
        query
    )

    text = normalize(
        f"{title} {description}"
    )

    score = 0

    for word in query_words:

        if word in text:
            score += 1

    return score


def is_relevant(
    query,
    title,
    description=""
):

    words = important_words(
        query
    )

    if not words:
        return False

    score = product_score(
        query,
        title,
        description
    )

    # Örneğin:
    # Grundig Club
    #
    # Sonuçta hem Grundig
    # hem Club bulunmalı.

    if len(words) == 1:
        return score >= 1

    if len(words) == 2:
        return score >= 2

    if len(words) == 3:
        return score >= 2

    return score >= 3


# =========================================================
# PARA
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

            if number > 0:
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

        if 0 < number <= 10_000_000:
            return number

    except Exception:
        pass

    return None


# =========================================================
# URL / MAĞAZA
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


def nice_store(
    seller="",
    url=""
):

    seller = str(
        seller or ""
    ).strip()

    if seller:
        return seller

    domain = get_domain(
        url
    )

    names = {

        "hepsiburada.com":
            "Hepsiburada",

        "trendyol.com":
            "Trendyol",

        "n11.com":
            "N11",

        "amazon.com.tr":
            "Amazon Türkiye",

        "akakce.com":
            "Akakçe",

        "cimri.com":
            "Cimri",

        "dolap.com":
            "Dolap",

        "sahibinden.com":
            "Sahibinden",

        "letgo.com":
            "Letgo"
    }

    return names.get(
        domain,
        domain or "Mağaza"
    )


# =========================================================
# API ÇAĞRISI
# =========================================================

def call_api(
    endpoint,
    params,
    timeout=180
):

    if not API_KEY:
        return {
            "ok": False,
            "status": 0,
            "error": "API anahtarı yok"
        }

    try:

        response = requests.get(
            BASE_URL + endpoint,
            params=params,
            headers=API_HEADERS,
            timeout=timeout
        )

        status = response.status_code

        try:
            data = response.json()
        except Exception:
            data = None

        if status != 200:

            return {
                "ok": False,
                "status": status,
                "error": (
                    data
                    if data is not None
                    else response.text[:500]
                )
            }

        if not isinstance(
            data,
            dict
        ):

            return {
                "ok": False,
                "status": status,
                "error": "Geçersiz JSON"
            }

        if not data.get(
            "success",
            False
        ):

            return {
                "ok": False,
                "status": status,
                "error": data
            }

        return {
            "ok": True,
            "status": status,
            "data": data
        }

    except requests.exceptions.Timeout:

        return {
            "ok": False,
            "status": 504,
            "error": "API zaman aşımına uğradı."
        }

    except requests.exceptions.RequestException as e:

        return {
            "ok": False,
            "status": 0,
            "error": str(e)
        }

    except Exception as e:

        return {
            "ok": False,
            "status": 0,
            "error": str(e)
        }


# =========================================================
# GOOGLE SHOPPING PRODUCT SEARCH
# =========================================================

def google_shopping_search(
    query
):

    return call_api(
        "/v1/google_shopping/product-search",
        {
            "query": query,
            "country": "Turkey",
            "language": "tr",
            "depth": 120,
            "sort_by": "price_low_to_high"
        },
        timeout=240
    )


# =========================================================
# GOOGLE SHOPPING PRODUCT DETAIL
# =========================================================

def google_product_detail(
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

    if gid:
        params["gid"] = gid

    if data_docid:
        params["data_docid"] = data_docid

    if len(params) == 2:
        return None

    return call_api(
        "/v1/google_shopping/product",
        params,
        timeout=120
    )


# =========================================================
# GOOGLE SHOPPING SELLERS
# =========================================================

def google_sellers(
    product_id,
    gid,
    data_docid
):

    # GID önemli.
    # Ürün aramasından gelen üç ID'yi birlikte gönderiyoruz.

    if not gid:
        return None

    params = {

        "gid": gid,

        "country":
            "Turkey",

        "language":
            "tr"
    }

    if product_id:
        params["product_id"] = product_id

    if data_docid:
        params["data_docid"] = data_docid

    return call_api(
        "/v1/google_shopping/sellers",
        params,
        timeout=120
    )


# =========================================================
# ÜRÜN ARAMA SONUCUNU OKU
# =========================================================

def parse_product_search(
    response,
    query
):

    results = []

    if not response:
        return results

    if not response.get("ok"):
        return results

    data = response.get(
        "data",
        {}
    )

    items = (
        data
        .get("data", {})
        .get("items", [])
    )

    for item in items:

        product = item.get(
            "product",
            {}
        )

        if not product:
            continue

        title = product.get(
            "title",
            ""
        )

        description = product.get(
            "description",
            ""
        )

        if not is_relevant(
            query,
            title,
            description
        ):
            continue

        price = product.get(
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

            # TRY değilse TL sonucu olarak
            # göstermiyoruz.
            continue

        current = parse_price(
            price.get(
                "current"
            )
        )

        if current is None:
            continue

        ext = product.get(
            "ext",
            {}
        )

        results.append({

            "title":
                title,

            "price":
                current,

            "store":
                nice_store(
                    product.get(
                        "seller"
                    ),
                    product.get(
                        "url",
                        ""
                    )
                ),

            "url":
                product.get(
                    "url",
                    ""
                ),

            "condition":
                "Sıfır",

            "source":
                "Google Shopping",

            "product_id":
                product.get(
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
                product.get(
                    "rating",
                    {}
                )
        })

    return results


# =========================================================
# SELLER SONUÇLARINI OKU
# =========================================================

def parse_seller_response(
    response,
    query
):

    results = []

    if not response:
        return results

    if not response.get("ok"):
        return results

    data = response.get(
        "data",
        {}
    )

    items = (
        data
        .get("data", {})
        .get("items", [])
    )

    for item in items:

        # Bazı cevaplarda offer,
        # bazı cevaplarda seller alanı olabilir.

        seller = item.get(
            "seller",
            {}
        )

        if not isinstance(
            seller,
            dict
        ):
            seller = {}

        offer = item.get(
            "offer",
            {}
        )

        if not isinstance(
            offer,
            dict
        ):
            offer = {}

        title = (
            item.get("title")
            or offer.get("title")
            or item.get("product_title")
            or query
        )

        if not is_relevant(
            query,
            title,
            ""
        ):
            continue

        price_data = (
            item.get("price")
            or offer.get("price")
            or {}
        )

        if isinstance(
            price_data,
            dict
        ):

            current = parse_price(
                price_data.get(
                    "current"
                )
                or
                price_data.get(
                    "value"
                )
                or
                price_data.get(
                    "amount"
                )
            )

            currency = str(
                price_data.get(
                    "currency",
                    "TRY"
                )
            ).upper()

        else:

            current = parse_price(
                price_data
            )

            currency = "TRY"

        if current is None:
            continue

        if currency not in {
            "TRY",
            "TL"
        }:
            continue

        url = (
            item.get("url")
            or offer.get("url")
            or ""
        )

        seller_name = (
            item.get("seller_name")
            or seller.get("name")
            or item.get("merchant")
            or item.get("store")
            or "Mağaza"
        )

        results.append({

            "title":
                title,

            "price":
                current,

            "store":
                nice_store(
                    seller_name,
                    url
                ),

            "url":
                url,

            "condition":
                "Sıfır",

            "source":
                "Google Shopping Satıcı",

            "product_id":
                None,

            "gid":
                None,

            "data_docid":
                None
        })

    return results


# =========================================================
# ANA GOOGLE SHOPPING TARAMASI
# =========================================================

def search_google_shopping(
    query,
    diagnostics
):

    results = []

    response = google_shopping_search(
        query
    )

    if not response["ok"]:

        diagnostics[
            "Google Shopping"
        ] = {

            "count": 0,

            "status":
                response.get(
                    "status"
                ),

            "error":
                response.get(
                    "error"
                )
        }

        return results

    products = parse_product_search(
        response,
        query
    )

    diagnostics[
        "Google Shopping"
    ] = {

        "count":
            len(products),

        "status":
            response.get(
                "status"
            ),

        "error":
            None
    }

    results.extend(
        products
    )

    # -----------------------------------------------------
    # SATICALARI ÇEK
    # -----------------------------------------------------

    seller_results = []

    # Aynı ürünü tekrar tekrar çağırmamak için
    # benzersiz GID kullanıyoruz.

    seen_gids = set()

    for product in products:

        gid = product.get(
            "gid"
        )

        if not gid:
            continue

        if gid in seen_gids:
            continue

        seen_gids.add(
            gid
        )

        seller_response = google_sellers(

            product.get(
                "product_id"
            ),

            gid,

            product.get(
                "data_docid"
            )
        )

        parsed = parse_seller_response(
            seller_response,
            query
        )

        seller_results.extend(
            parsed
        )

    diagnostics[
        "Google Shopping Satıcıları"
    ] = {

        "count":
            len(seller_results),

        "status":
            200 if seller_results else None,

        "error":
            None
    }

    results.extend(
        seller_results
    )

    return results


# =========================================================
# KAYNAK BİLGİSİ
# =========================================================

def source_domain(
    url
):

    return get_domain(
        url
    )


# =========================================================
# SONUÇLARI TEMİZLE
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
# İKİNCİ EL FİLTRESİ
# =========================================================

USED_WORDS = [
    "ikinci el",
    "2.el",
    "2 el",
    "kullanilmis",
    "kullanılmış",
    "sahibinden",
    "dolap",
    "letgo",
    "az kullanildi",
    "az kullanıldı",
    "temiz kullanildi",
    "temiz kullanıldı"
]


REFURBISHED_WORDS = [
    "yenilenmis",
    "yenilenmiş",
    "refurbished",
    "renewed"
]


def has_used_word(text):

    text = normalize(
        text
    )

    return any(
        normalize(word) in text
        for word in USED_WORDS
    )


def has_refurbished_word(text):

    text = normalize(
        text
    )

    return any(
        normalize(word) in text
        for word in REFURBISHED_WORDS
    )


# =========================================================
# SONUÇ SINIFLANDIRMA
# =========================================================

def classify_result(
    item
):

    text = (
        f'{item.get("title","")} '
        f'{item.get("store","")} '
        f'{item.get("source","")}'
    )

    if has_refurbished_word(
        text
    ):

        return "Yenilenmiş"

    if has_used_word(
        text
    ):

        return "İkinci El"

    return item.get(
        "condition",
        "Sıfır"
    )


# =========================================================
# KART
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
        classify_result(best)
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

        title_html = html.escape(
            item["title"]
        )

        store_html = html.escape(
            item["store"]
        )

        condition_html = html.escape(
            classify_result(item)
        )

        st.markdown(
            f"""
            <div class="offer {css_class}">

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

                <div class="offer-condition">
                    🔎 {html.escape(item["source"])}
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

    if not product_query.strip():

        st.warning(
            "Lütfen ürün adı yaz."
        )

        st.stop()

    if not API_KEY:

        st.error(
            "❌ SOCIALCRAWL_API_KEY bulunamadı."
        )

        st.info(
            "Streamlit → Settings → Secrets "
            "bölümüne şu satırı ekle:"
        )

        st.code(
            'SOCIALCRAWL_API_KEY = "sc_..."',
            language="toml"
        )

        st.stop()

    query = product_query.strip()

    diagnostics = {}

    st.info(
        f"🔎 **{query}** için gerçek ürün ve satıcı "
        f"fiyatları aranıyor..."
    )

    with st.spinner(
        "Google Shopping ve satıcılar taranıyor..."
    ):

        all_results = search_google_shopping(
            query,
            diagnostics
        )

    all_results = clean_results(
        all_results
    )

    # =====================================================
    # TEŞHİS
    # =====================================================

    with st.expander(
        "🔧 Kaynak durumu",
        expanded=False
    ):

        for source, info in diagnostics.items():

            count = info.get(
                "count",
                0
            )

            status = info.get(
                "status"
            )

            error = info.get(
                "error"
            )

            if count > 0:

                st.success(
                    f"{source} → {count} sonuç"
                )

            elif error:

                st.warning(
                    f"{source} → 0 sonuç "
                    f"(HTTP {status})"
                )

                st.caption(
                    str(error)[:700]
                )

            else:

                st.info(
                    f"{source} → 0 sonuç"
                )

    # =====================================================
    # SONUÇ YOK
    # =====================================================

    if not all_results:

        st.error(
            f'"{query}" için doğrulanabilir '
            f'Google Shopping fiyatı bulunamadı.'
        )

        st.write(
            "Bu kez özellikle API'nin gerçekten "
            "ne döndürdüğünü yukarıdaki Kaynak Durumu "
            "bölümünden görebilirsin."
        )

        st.stop()

    # =====================================================
    # KATEGORİLERE AYIR
    # =====================================================

    new_results = []
    used_results = []
    refurbished_results = []

    for item in all_results:

        condition = classify_result(
            item
        )

        if condition == "İkinci El":

            used_results.append(
                item
            )

        elif condition == "Yenilenmiş":

            refurbished_results.append(
                item
            )

        else:

            new_results.append(
                item
            )

    # =====================================================
    # EN UCUZ
    # =====================================================

    show_best(
        all_results
    )

    # =====================================================
    # ÖZET
    # =====================================================

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

    # =====================================================
    # FİYAT ARALIĞI
    # =====================================================

    prices = [
        x["price"]
        for x in all_results
    ]

    if prices:

        cheapest = min(
            prices
        )

        expensive = max(
            prices
        )

        difference = (
            expensive
            - cheapest
        )

        st.info(
            f"💰 En düşük: **{cheapest:,.2f} TL**  "
            f"| En yüksek: **{expensive:,.2f} TL**  "
            f"| Fark: **{difference:,.2f} TL**"
        )

    st.divider()

    # =====================================================
    # KATEGORİLER
    # =====================================================

    show_category(
        "Sıfır Ürünler",
        "🟢",
        new_results,
        "new"
    )

    st.divider()

    show_category(
        "İkinci El",
        "🟠",
        used_results,
        "used"
    )

    st.divider()

    show_category(
        "Yenilenmiş",
        "🔵",
        refurbished_results,
        "refurbished"
    )
