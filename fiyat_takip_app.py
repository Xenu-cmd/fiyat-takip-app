import streamlit as st
import requests
import re
from urllib.parse import urlparse


# =========================================================
# AYARLAR
# =========================================================

st.set_page_config(
    page_title="Akıllı Fiyat Karşılaştırma",
    page_icon="🔎",
    layout="wide"
)


API_URL = "https://www.socialcrawl.dev"

HEADERS = {
    "Accept": "application/json"
}


# =========================================================
# API KEY
# =========================================================

try:
    API_KEY = st.secrets["SOCIALCRAWL_API_KEY"]
except Exception:
    API_KEY = ""


if API_KEY:
    HEADERS["x-api-key"] = API_KEY


# =========================================================
# TASARIM
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
    background:linear-gradient(
        135deg,
        #ecfdf5,
        #f0fdf4
    );

    border:2px solid #22c55e;
    border-radius:20px;

    padding:25px;

    margin-top:20px;
    margin-bottom:25px;
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
    color:#111827;
}

.best-price {
    font-size:44px;
    font-weight:900;
    color:#15803d;
    margin-top:8px;
}

.offer-card {
    background:#ffffff;

    border:1px solid #e5e7eb;
    border-radius:15px;

    padding:18px;

    margin-bottom:12px;

    box-shadow:
        0 3px 12px
        rgba(0,0,0,0.04);
}

.offer-price {
    font-size:27px;
    font-weight:900;
    color:#111827;
}

.offer-store {
    color:#2563eb;
    font-weight:800;
    margin-top:4px;
}

.used-card {
    border-left:6px solid #f97316;
}

.new-card {
    border-left:6px solid #22c55e;
}

.refurb-card {
    border-left:6px solid #3b82f6;
}

.summary-card {
    background:#f9fafb;
    border:1px solid #e5e7eb;
    border-radius:15px;
    padding:18px;
    text-align:center;
}

.summary-number {
    font-size:28px;
    font-weight:900;
}

.summary-label {
    color:#6b7280;
    font-weight:700;
}

.info-box {
    background:#eff6ff;
    border:1px solid #bfdbfe;
    padding:15px;
    border-radius:12px;
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
    'Aynı ürünün farklı satıcılarındaki fiyatları karşılaştır'
    '</div>',
    unsafe_allow_html=True
)


# =========================================================
# NORMALİZE
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

def product_words(product):

    ignored = {
        "ve",
        "ile",
        "icin",
        "bir",
        "the",
        "a",
        "an"
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
# ÜRÜN EŞLEŞTİRME
# =========================================================

def product_matches(
    searched_product,
    result_title,
    description=""
):

    wanted = product_words(
        searched_product
    )

    title = normalize(
        result_title
    )

    description = normalize(
        description
    )

    if not wanted:
        return True

    # -----------------------------------------------------
    # ÇOK KELİMELİ ÜRÜN
    #
    # Grundig Club
    #
    # hem Grundig hem Club içermeli.
    # -----------------------------------------------------

    for word in wanted:

        if word not in title:

            return False

    # -----------------------------------------------------
    # ALAKASIZ ÜRÜN FİLTRESİ
    # -----------------------------------------------------

    combined = (
        title
        + " "
        + description
    )

    searched = normalize(
        searched_product
    )

    bad_words = [

        "kulaklik",
        "kulakici",
        "kulak ici",

        "headphone",
        "headset",

        "mikrofon",
        "microphone",

        "kablo",

        "kablolu",

        "kilif",
        "case",

        "canta",

        "yedek parca",

        "kumanda",
        "remote"

    ]

    for bad in bad_words:

        if bad in combined:

            if bad not in searched:

                return False

    return True


# =========================================================
# DOMAIN
# =========================================================

def domain_from_url(url):

    if not url:
        return ""

    try:

        return urlparse(
            url
        ).netloc.replace(
            "www.",
            ""
        )

    except Exception:

        return ""


# =========================================================
# GOOGLE SHOPPING ÜRÜN ARAMA
# =========================================================

def search_products(product):

    endpoint = (
        API_URL
        + "/v1/google_shopping/product-search"
    )

    params = {

        "query": product,

        "country": "Turkey",

        "language": "tr",

        "depth": 120,

        "sort_by":
            "price_low_to_high"

    }

    try:

        response = requests.get(

            endpoint,

            params=params,

            headers=HEADERS,

            timeout=90

        )

    except Exception as e:

        st.error(
            f"Google Shopping bağlantı hatası: {e}"
        )

        return []

    if response.status_code != 200:

        st.error(
            f"API hatası: HTTP {response.status_code}"
        )

        return []

    try:

        data = response.json()

    except Exception:

        st.error(
            "API geçerli JSON döndürmedi."
        )

        return []

    if not data.get("success"):

        return []

    items = (
        data
        .get("data", {})
        .get("items", [])
    )

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

        # -------------------------------------------------
        # YANLIŞ ÜRÜNLERİ AT
        # -------------------------------------------------

        if not product_matches(

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

        # Türkiye için sadece TL
        if currency not in [
            "TRY",
            "TL"
        ]:

            continue

        ext = p.get(
            "ext",
            {}
        )

        results.append({

            "title":
                title,

            "description":
                description,

            "price":
                price,

            "seller":
                p.get(
                    "seller",
                    "Bilinmiyor"
                ),

            "url":
                p.get(
                    "url",
                    ""
                ),

            "currency":
                currency,

            "product_id":
                p.get(
                    "id",
                    ""
                ),

            "gid":
                ext.get(
                    "gid",
                    ""
                ),

            "data_docid":
                ext.get(
                    "data_docid",
                    ""
                ),

            "image":
                (
                    p.get(
                        "image_urls",
                        []
                    )[0]
                    if p.get(
                        "image_urls",
                        []
                    )
                    else ""
                )

        })

    return results


# =========================================================
# EN DOĞRU ÜRÜNÜ SEÇ
# =========================================================

def choose_best_product(
    searched_product,
    products
):

    if not products:

        return None

    wanted = product_words(
        searched_product
    )

    scored = []

    for item in products:

        title = normalize(
            item["title"]
        )

        score = 0

        # Her arama kelimesi
        # başlıkta varsa puan
        for word in wanted:

            if word in title:

                score += 10

        # Başlığın ilk kısmı aramaya
        # benziyorsa ekstra puan
        normalized_search = normalize(
            searched_product
        )

        if normalized_search in title:

            score += 20

        # Fiyatı olan sonuç
        if item.get("price") is not None:

            score += 2

        scored.append(
            (
                score,
                item
            )
        )

    scored.sort(
        key=lambda x: (
            -x[0],
            x[1]["price"]
        )
    )

    return scored[0][1]


# =========================================================
# SATIŞ TEKLİFLERİNİ GETİR
# =========================================================

def get_sellers(product_item):

    endpoint = (
        API_URL
        + "/v1/google_shopping/sellers"
    )

    params = {}

    # Dokümantasyondaki ürün kimliklerini
    # mümkün olduğunca birlikte gönderiyoruz.

    if product_item.get(
        "gid"
    ):

        params["gid"] = product_item[
            "gid"
        ]

    if product_item.get(
        "product_id"
    ):

        params["product_id"] = product_item[
            "product_id"
        ]

    if product_item.get(
        "data_docid"
    ):

        params["data_docid"] = product_item[
            "data_docid"
        ]

    params["country"] = "Turkey"

    params["language"] = "tr"

    try:

        response = requests.get(

            endpoint,

            params=params,

            headers=HEADERS,

            timeout=60

        )

    except Exception:

        return []

    if response.status_code != 200:

        return []

    try:

        data = response.json()

    except Exception:

        return []

    if not data.get(
        "success"
    ):

        return []

    raw = (
        data
        .get("data", {})
    )

    # -----------------------------------------------------
    # API şeması değişirse bile mümkün olduğunca
    # farklı liste isimlerini destekle.
    # -----------------------------------------------------

    sellers = []

    for key in [
        "sellers",
        "offers",
        "items",
        "results"
    ]:

        value = raw.get(
            key
        )

        if isinstance(
            value,
            list
        ):

            sellers = value

            break

    # Bazı cevaplarda data doğrudan liste olabilir.
    if not sellers and isinstance(
        raw,
        list
    ):

        sellers = raw

    results = []

    for seller in sellers:

        if not isinstance(
            seller,
            dict
        ):

            continue

        # -------------------------------------------------
        # SATIŞ FİYATINI BUL
        # -------------------------------------------------

        price = None

        price_data = seller.get(
            "price"
        )

        if isinstance(
            price_data,
            dict
        ):

            price = price_data.get(
                "current"
            )

            if price is None:

                price = price_data.get(
                    "value"
                )

        elif price_data is not None:

            price = price_data

        if price is None:

            for key in [
                "current_price",
                "price_current",
                "offer_price",
                "amount"
            ]:

                if seller.get(
                    key
                ) is not None:

                    price = seller.get(
                        key
                    )

                    break

        try:

            price = float(
                price
            )

        except Exception:

            continue

        # -------------------------------------------------
        # PARA BİRİMİ
        # -------------------------------------------------

        currency = seller.get(
            "currency",
            ""
        )

        if isinstance(
            price_data,
            dict
        ):

            currency = (
                price_data.get(
                    "currency"
                )
                or currency
            )

        currency = str(
            currency
        ).upper()

        if currency not in [
            "",
            "TRY",
            "TL"
        ]:

            continue

        # -------------------------------------------------
        # SATICI
        # -------------------------------------------------

        seller_name = (

            seller.get(
                "seller"
            )

            or seller.get(
                "seller_name"
            )

            or seller.get(
                "merchant"
            )

            or seller.get(
                "store"
            )

            or seller.get(
                "retailer"
            )

            or "Bilinmiyor"

        )

        # Eğer seller bir dict ise
        if isinstance(
            seller_name,
            dict
        ):

            seller_name = (

                seller_name.get(
                    "name"
                )

                or seller_name.get(
                    "title"
                )

                or "Bilinmiyor"

            )

        # -------------------------------------------------
        # URL
        # -------------------------------------------------

        url = (

            seller.get(
                "url"
            )

            or seller.get(
                "link"
            )

            or seller.get(
                "offer_url"
            )

            or ""

        )

        results.append({

            "title":
                product_item["title"],

            "price":
                price,

            "seller":
                str(
                    seller_name
                ),

            "url":
                url,

            "condition":
                "Sıfır",

            "currency":
                "TRY"

        })

    return results


# =========================================================
# GOOGLE ARAMA
# İKİNCİ EL / YENİLENMİŞ
# =========================================================

def google_search(
    query,
    searched_product,
    condition
):

    endpoint = (
        API_URL
        + "/v1/google/search"
    )

    params = {
        "query": query,
        "region": "Turkey"
    }

    try:

        response = requests.get(

            endpoint,

            params=params,

            headers=HEADERS,

            timeout=60

        )

    except Exception:

        return []

    if response.status_code != 200:

        return []

    try:

        data = response.json()

    except Exception:

        return []

    if not data.get(
        "success"
    ):

        return []

    raw = (
        data
        .get("data", {})
    )

    items = []

    if isinstance(
        raw,
        dict
    ):

        for key in [
            "items",
            "results",
            "organic_results"
        ]:

            if isinstance(
                raw.get(key),
                list
            ):

                items = raw.get(
                    key
                )

                break

    results = []

    for item in items:

        title = item.get(
            "title",
            ""
        )

        url = item.get(
            "url",
            ""
        )

        snippet = (

            item.get(
                "snippet"
            )

            or item.get(
                "description"
            )

            or ""

        )

        # Ürün eşleşmesi
        if not product_matches(

            searched_product,

            title,

            snippet

        ):

            continue

        combined = (
            title
            + " "
            + snippet
        )

        # -------------------------------------------------
        # TL FİYAT
        # -------------------------------------------------

        price = extract_tl_price(
            combined
        )

        if price is None:

            continue

        results.append({

            "title":
                title,

            "price":
                price,

            "seller":
                domain_from_url(
                    url
                ),

            "url":
                url,

            "condition":
                condition,

            "currency":
                "TRY"

        })

    return results


# =========================================================
# TL FİYAT ÇIKAR
# =========================================================

def extract_tl_price(text):

    if not text:

        return None

    text = text.replace(
        "\xa0",
        " "
    )

    patterns = [

        r"(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?)\s*(?:TL|₺)",

        r"(\d{3,7}(?:,\d{1,2})?)\s*(?:TL|₺)",

        r"(?:TL|₺)\s*(\d{3,7}(?:[.,]\d{1,2})?)"

    ]

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

                    if len(
                        parts[-1]
                    ) == 2:

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

                    if len(
                        parts[-1]
                    ) == 3:

                        value = value.replace(
                            ".",
                            ""
                        )

                number = float(
                    value
                )

                if (
                    10
                    <= number
                    <= 10000000
                ):

                    return number

            except Exception:

                pass

    return None


# =========================================================
# İKİNCİ EL
# =========================================================

def search_used(
    product
):

    queries = [

        f'"{product}" ikinci el',

        f'"{product}" 2.el',

        f'"{product}" site:sahibinden.com',

        f'"{product}" site:letgo.com'

    ]

    results = []

    for query in queries:

        results.extend(

            google_search(

                query,

                product,

                "İkinci El"

            )

        )

    return remove_duplicates(
        results
    )


# =========================================================
# YENİLENMİŞ
# =========================================================

def search_refurbished(
    product
):

    queries = [

        f'"{product}" yenilenmiş',

        f'"{product}" refurbished',

        f'"{product}" site:easycep.com',

        f'"{product}" yenilenmiş fiyat'

    ]

    results = []

    for query in queries:

        results.extend(

            google_search(

                query,

                product,

                "Yenilenmiş"

            )

        )

    return remove_duplicates(
        results
    )


# =========================================================
# TEKRARLARI SİL
# =========================================================

def remove_duplicates(
    results
):

    unique = {}

    for item in results:

        key = (

            normalize(
                item.get(
                    "seller",
                    ""
                )
            ),

            round(
                float(
                    item.get(
                        "price",
                        0
                    )
                ),
                2
            ),

            normalize(
                item.get(
                    "title",
                    ""
                )
            )

        )

        if key not in unique:

            unique[key] = item

    final = list(
        unique.values()
    )

    final.sort(
        key=lambda x:
            x["price"]
    )

    return final


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
        key=lambda x:
            x["price"]
    )

    condition = cheapest.get(
        "condition",
        "Sıfır"
    )

    if condition == "Sıfır":
        icon = "🟢"

    elif condition == "İkinci El":
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
                margin-top:5px;
                font-weight:800;
            ">
                {icon} {condition}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    if cheapest.get("url"):

        st.link_button(
            "🛒 En Ucuz Ürüne Git",
            cheapest["url"]
        )


# =========================================================
# TEKLİF LİSTESİ
# =========================================================

def show_offers(
    title,
    results,
    css_class,
    icon,
    limit=30
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
        results[:limit],
        start=1
    ):

        st.markdown(
            f"""
            <div class="offer-card {css_class}">

                <div style="
                    font-size:18px;
                    font-weight:800;
                ">
                    {index}. {item["title"]}
                </div>

                <div class="offer-price">
                    {item["price"]:,.2f} TL
                </div>

                <div class="offer-store">
                    🏪 {item["seller"]}
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )

        if item.get(
            "url"
        ):

            st.link_button(
                "🛒 Satıcıya Git",
                item["url"]
            )


# =========================================================
# ARAMA
# =========================================================

product = st.text_input(

    "🔎 Ürün adı",

    placeholder=
    "Örn: Grundig Club BT Hoparlör"

)


search_button = st.button(

    "🔍 Ara ve Karşılaştır",

    type="primary",

    use_container_width=True

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
            "❌ SocialCrawl API anahtarı bulunamadı."
        )

        st.code(
            'SOCIALCRAWL_API_KEY = "sc_..."'
        )

        st.stop()


    if not product.strip():

        st.warning(
            "Lütfen ürün adı yaz."
        )

        st.stop()


    product = product.strip()


    # =====================================================
    # 1 — GOOGLE SHOPPING ÜRÜN ARAMA
    # =====================================================

    with st.spinner(
        "🔎 Ürün aranıyor..."
    ):

        products = search_products(
            product
        )


    if not products:

        st.error(
            f'"{product}" için uygun ürün bulunamadı.'
        )

        st.stop()


    # =====================================================
    # 2 — DOĞRU ÜRÜNÜ SEÇ
    # =====================================================

    best_product = choose_best_product(

        product,

        products

    )


    if not best_product:

        st.error(
            "Uygun ürün eşleştirilemedi."
        )

        st.stop()


    # =====================================================
    # ÜRÜN BİLGİSİ
    # =====================================================

    st.success(
        "✅ Doğru ürün eşleştirildi."
    )


    st.markdown(
        f"""
        <div class="info-box">

        <b>Aranan:</b> {product}<br>

        <b>Eşleşen ürün:</b>
        {best_product["title"]}

        </div>
        """,
        unsafe_allow_html=True
    )


    # =====================================================
    # 3 — AYNI ÜRÜNÜN SATICILARI
    # =====================================================

    with st.spinner(
        "🏪 Aynı ürünün satıcıları ve fiyatları getiriliyor..."
    ):

        seller_results = get_sellers(
            best_product
        )


    # Seller endpoint boş dönerse
    # Shopping arama sonuçlarını yedek olarak kullan.
    if not seller_results:

        seller_results = []

        for item in products:

            if product_matches(

                product,

                item["title"],

                item["description"]

            ):

                seller_results.append({

                    "title":
                        item["title"],

                    "price":
                        item["price"],

                    "seller":
                        item["seller"],

                    "url":
                        item["url"],

                    "condition":
                        "Sıfır",

                    "currency":
                        "TRY"

                })


    new_results = remove_duplicates(
        seller_results
    )


    # =====================================================
    # 4 — İKİNCİ EL
    # =====================================================

    with st.spinner(
        "🟠 İkinci el araştırılıyor..."
    ):

        used_results = search_used(
            product
        )


    # =====================================================
    # 5 — YENİLENMİŞ
    # =====================================================

    with st.spinner(
        "🔵 Yenilenmiş ürünler araştırılıyor..."
    ):

        refurbished_results = (
            search_refurbished(
                product
            )
        )


    # =====================================================
    # TÜM SONUÇLAR
    # =====================================================

    all_results = remove_duplicates(

        new_results
        + used_results
        + refurbished_results

    )


    if not all_results:

        st.error(
            "Uygun fiyat bulunamadı."
        )

        st.stop()


    # =====================================================
    # EN UCUZ
    # =====================================================

    st.header(
        "🏆 En Ucuz Sonuç"
    )

    show_best(
        all_results
    )


    # =====================================================
    # ÖZET
    # =====================================================

    st.divider()

    st.subheader(
        "📊 Fiyat Özeti"
    )


    col1, col2, col3, col4 = st.columns(
        4
    )


    with col1:

        st.markdown(
            f"""
            <div class="summary-card">

                <div class="summary-number">
                    {len(new_results)}
                </div>

                <div class="summary-label">
                    🟢 Sıfır Fiyat
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
                    💰 Toplam Fiyat
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


    # =====================================================
    # TÜM FİYATLAR
    # =====================================================

    st.divider()

    st.header(
        "💰 Tüm Fiyatlar"
    )

    st.caption(
        "En ucuzdan en pahalıya sıralanmıştır."
    )


    show_offers(

        "Tüm Fiyatlar",

        all_results,

        "new-card",

        "💰",

        50

    )


    # =====================================================
    # SIFIR
    # =====================================================

    st.divider()

    show_offers(

        "Sıfır Ürünler",

        new_results,

        "new-card",

        "🟢",

        50

    )


    # =====================================================
    # İKİNCİ EL
    # =====================================================

    st.divider()

    show_offers(

        "İkinci El",

        used_results,

        "used-card",

        "🟠",

        30

    )


    # =====================================================
    # YENİLENMİŞ
    # =====================================================

    st.divider()

    show_offers(

        "Yenilenmiş",

        refurbished_results,

        "refurb-card",

        "🔵",

        30

    )


    # =====================================================
    # FİYAT ARALIĞI
    # =====================================================

    if len(all_results) >= 2:

        prices = [

            x["price"]

            for x in all_results

        ]

        lowest = min(
            prices
        )

        highest = max(
            prices
        )

        difference = (
            highest
            - lowest
        )


        st.divider()

        st.subheader(
            "📈 Fiyat Aralığı"
        )


        c1, c2, c3 = st.columns(
            3
        )


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
                "Fark",
                f"{difference:,.2f} TL"
            )
