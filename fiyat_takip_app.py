import streamlit as st
import requests
import re
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
    font-size: 42px;
    font-weight: 900;
    color: #111827;
    margin-top: 15px;
}

.subtitle {
    text-align: center;
    color: #6b7280;
    font-size: 17px;
    margin-bottom: 30px;
}

.best-card {
    background: linear-gradient(
        135deg,
        #fefce8,
        #fff7ed
    );

    border: 2px solid #facc15;

    padding: 25px;

    border-radius: 20px;

    margin: 25px 0;

    box-shadow:
        0 5px 20px
        rgba(0,0,0,0.06);
}

.best-title {
    font-size: 23px;
    font-weight: 800;
}

.best-price {
    font-size: 40px;
    font-weight: 900;
    color: #15803d;
}

.card {
    background: white;

    padding: 18px;

    border-radius: 16px;

    border: 1px solid #e5e7eb;

    margin-bottom: 14px;

    box-shadow:
        0 3px 12px
        rgba(0,0,0,0.05);
}

.new-card {
    border-left: 6px solid #22c55e;
}

.used-card {
    border-left: 6px solid #f97316;
}

.refurbished-card {
    border-left: 6px solid #3b82f6;
}

.product-title {
    font-size: 18px;
    font-weight: 800;
    color: #111827;
}

.price {
    font-size: 28px;
    font-weight: 900;
    color: #15803d;
    margin-top: 5px;
}

.seller {
    font-weight: 700;
    color: #2563eb;
    margin-top: 5px;
}

.condition {
    display: inline-block;

    padding: 5px 10px;

    border-radius: 999px;

    font-size: 13px;

    font-weight: 700;

    margin-top: 8px;
}

.condition-new {
    background: #dcfce7;
    color: #166534;
}

.condition-used {
    background: #ffedd5;
    color: #9a3412;
}

.condition-refurbished {
    background: #dbeafe;
    color: #1e40af;
}

.stats-card {
    background: #f9fafb;

    padding: 18px;

    border-radius: 15px;

    border: 1px solid #e5e7eb;

    text-align: center;
}

.stats-number {
    font-size: 26px;
    font-weight: 900;
}

.stats-label {
    color: #6b7280;
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
    'Sıfır, ikinci el ve yenilenmiş ürünleri tek yerde karşılaştır'
    '</div>',
    unsafe_allow_html=True
)


# =========================================================
# API KEY
# =========================================================

def get_api_key():

    try:

        return st.secrets[
            "SOCIALCRAWL_API_KEY"
        ]

    except Exception:

        return None


# =========================================================
# METİN NORMALİZE
# =========================================================

def normalize_text(text):

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

        text = text.replace(
            old,
            new
        )

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

def get_search_words(query):

    query = normalize_text(
        query
    )

    words = []

    for word in query.split():

        if len(word) >= 2:

            words.append(word)

    return words


# =========================================================
# ÜRÜN EŞLEŞTİRME
# =========================================================

def product_match(
    search_query,
    title
):

    search_words = get_search_words(
        search_query
    )

    title_normalized = normalize_text(
        title
    )

    if not search_words:

        return True


    matched = 0


    for word in search_words:

        if word in title_normalized:

            matched += 1


    # Tek kelimelik arama

    if len(search_words) == 1:

        return matched == 1


    # İki veya daha fazla kelimelik arama

    ratio = (
        matched /
        len(search_words)
    )


    return ratio >= 0.70


# =========================================================
# API ARAMA
# =========================================================

def search_google_shopping(
    product_name
):

    api_key = get_api_key()


    if not api_key:

        st.error(
            "❌ SOCIALCRAWL_API_KEY bulunamadı."
        )

        st.code(
            'SOCIALCRAWL_API_KEY = "sc_..."'
        )

        return []


    url = (
        "https://www.socialcrawl.dev/"
        "v1/google_shopping/product-search"
    )


    params = {

        "query": product_name,

        "country": "Turkey",

        "language": "tr",

        "depth": 80,

        "sort_by": "price_low_to_high"

    }


    headers = {

        "x-api-key": api_key,

        "Accept": "application/json"

    }


    try:

        response = requests.get(

            url,

            params=params,

            headers=headers,

            timeout=45

        )

    except requests.exceptions.Timeout:

        st.error(
            "⏱️ Arama 45 saniyede tamamlanmadı."
        )

        return []


    except Exception as e:

        st.error(
            f"❌ Bağlantı hatası: {e}"
        )

        return []


    if response.status_code != 200:

        st.error(
            "❌ SocialCrawl API hata verdi."
        )

        st.write(
            "HTTP:",
            response.status_code
        )

        try:

            st.code(
                response.text[:3000]
            )

        except Exception:

            pass

        return []


    try:

        data = response.json()

    except Exception:

        st.error(
            "❌ API JSON verisi döndürmedi."
        )

        return []


    if not data.get(
        "success",
        False
    ):

        st.error(
            "❌ API araması başarısız."
        )

        return []


    return (
        data
        .get("data", {})
        .get("items", [])
    )


# =========================================================
# PARA BİRİMİ
# =========================================================

def currency_symbol(
    currency
):

    currency = (
        currency or ""
    ).upper()


    symbols = {

        "TRY": "TL",

        "TL": "TL",

        "EUR": "€",

        "USD": "$",

        "GBP": "£",

        "AED": "AED",

        "SAR": "SAR"

    }


    return symbols.get(
        currency,
        currency
    )


# =========================================================
# FİYAT
# =========================================================

def format_price(
    price,
    currency
):

    try:

        price = float(
            price
        )

    except Exception:

        return "Fiyat yok"


    symbol = currency_symbol(
        currency
    )


    return (
        f"{price:,.2f} "
        f"{symbol}"
    )


# =========================================================
# DOMAIN
# =========================================================

def get_domain(
    url
):

    try:

        domain = urlparse(
            url
        ).netloc

        return domain.replace(
            "www.",
            ""
        )

    except Exception:

        return ""


# =========================================================
# DURUM TESPİTİ
# =========================================================

def detect_condition(
    title,
    seller,
    description=""
):

    text = normalize_text(

        str(title)
        + " "
        + str(seller)
        + " "
        + str(description)

    )


    refurbished = [

        "yenilenmis",

        "refurbished",

        "renewed",

        "outlet"

    ]


    used = [

        "ikinci el",

        "2 el",

        "2el",

        "used",

        "pre owned",

        "preowned",

        "kullanilmis",

        "sahibinden",

        "letgo"

    ]


    for word in refurbished:

        if word in text:

            return "Yenilenmiş"


    for word in used:

        if word in text:

            return "İkinci El"


    return "Sıfır"


# =========================================================
# ÜRÜNLERİ HAZIRLA
# =========================================================

def prepare_products(
    raw_items,
    search_query
):

    products = []


    for item in raw_items:

        product = item.get(
            "product",
            {}
        )


        title = product.get(
            "title",
            ""
        )


        if not title:

            continue


        # ---------------------------------------------
        # ALAKASIZ ÜRÜN FİLTRESİ
        # ---------------------------------------------

        if not product_match(
            search_query,
            title
        ):

            continue


        price_data = product.get(
            "price",
            {}
        )


        if not isinstance(
            price_data,
            dict
        ):

            continue


        current = price_data.get(
            "current"
        )


        if current is None:

            continue


        try:

            current = float(
                current
            )

        except Exception:

            continue


        if current <= 0:

            continue


        currency = price_data.get(
            "currency",
            "TRY"
        )


        seller = product.get(
            "seller",
            "Bilinmeyen satıcı"
        )


        url = product.get(
            "url",
            ""
        )


        description = product.get(
            "description",
            ""
        )


        images = product.get(
            "image_urls",
            []
        )


        image = ""


        if isinstance(
            images,
            list
        ) and images:

            image = images[0]


        rating = None

        rating_count = None


        rating_data = product.get(
            "rating",
            {}
        )


        if isinstance(
            rating_data,
            dict
        ):

            rating = rating_data.get(
                "average"
            )

            rating_count = rating_data.get(
                "count"
            )


        condition = detect_condition(

            title,

            seller,

            description

        )


        # ID bilgileri

        gid = (
            product
            .get("ext", {})
            .get("gid")
        )


        data_docid = (
            product
            .get("ext", {})
            .get("data_docid")
        )


        product_id = product.get(
            "id"
        )


        products.append({

            "title": title,

            "price": current,

            "currency": currency,

            "seller": seller,

            "url": url,

            "domain": get_domain(url),

            "description": description,

            "image": image,

            "rating": rating,

            "rating_count": rating_count,

            "condition": condition,

            "gid": gid,

            "product_id": product_id,

            "data_docid": data_docid

        })


    # =====================================================
    # TEKRARLARI TEMİZLE
    # =====================================================

    unique = {}


    for product in products:

        key = (

            normalize_text(
                product["title"]
            ),

            normalize_text(
                product["seller"]
            ),

            product["price"],

            product["currency"]

        )


        if key not in unique:

            unique[key] = product


    products = list(
        unique.values()
    )


    # =====================================================
    # FİYAT SIRALAMASI
    # =====================================================

    products.sort(

        key=lambda x: (

            x["price"]

        )

    )


    return products


# =========================================================
# AYNI MAĞAZADAN GELENLERİ TEMİZLE
# =========================================================

def cheapest_by_store(
    products
):

    stores = {}


    for product in products:

        seller = product["seller"]


        if seller not in stores:

            stores[seller] = product

        else:

            if (
                product["price"]
                <
                stores[seller]["price"]
            ):

                stores[seller] = product


    result = list(
        stores.values()
    )


    result.sort(
        key=lambda x: x["price"]
    )


    return result


# =========================================================
# FİYAT İSTATİSTİKLERİ
# =========================================================

def get_statistics(
    products
):

    if not products:

        return {

            "count": 0,

            "min": None,

            "max": None,

            "average": None,

            "difference": None

        }


    prices = [

        x["price"]

        for x in products

    ]


    minimum = min(
        prices
    )

    maximum = max(
        prices
    )

    average = (
        sum(prices)
        /
        len(prices)
    )


    return {

        "count": len(prices),

        "min": minimum,

        "max": maximum,

        "average": average,

        "difference": (
            maximum -
            minimum
        )

    }


# =========================================================
# ÜRÜN KARTI
# =========================================================

def show_product(
    product
):

    if product["condition"] == "Sıfır":

        card_class = (
            "new-card"
        )

        condition_class = (
            "condition-new"
        )

    elif product["condition"] == "İkinci El":

        card_class = (
            "used-card"
        )

        condition_class = (
            "condition-used"
        )

    else:

        card_class = (
            "refurbished-card"
        )

        condition_class = (
            "condition-refurbished"
        )


    price = format_price(

        product["price"],

        product["currency"]

    )


    left, right = st.columns(
        [1, 4]
    )


    with left:

        if product["image"]:

            try:

                st.image(

                    product["image"],

                    width=150

                )

            except Exception:

                pass


    with right:

        st.markdown(

            f"""
            <div class="card {card_class}">

                <div class="product-title">
                    {product["title"]}
                </div>

                <div class="price">
                    {price}
                </div>

                <div class="seller">
                    🏪 {product["seller"]}
                </div>

                <span class="
                    condition
                    {condition_class}
                ">
                    {product["condition"]}
                </span>

            </div>
            """,

            unsafe_allow_html=True

        )


        if product["rating"] is not None:

            rating_text = (
                f"⭐ {product['rating']}"
            )


            if product["rating_count"]:

                rating_text += (
                    f" "
                    f"({product['rating_count']:,} "
                    f"oy)"
                )


            st.write(
                rating_text
            )


        if product["domain"]:

            st.caption(
                f"🌐 {product['domain']}"
            )


        if product["url"]:

            st.link_button(

                "🛒 Mağazaya Git",

                product["url"]

            )


# =========================================================
# MAĞAZA KARŞILAŞTIRMA TABLOSU
# =========================================================

def show_comparison_table(
    products
):

    if not products:

        return


    stores = cheapest_by_store(
        products
    )


    rows = []


    for index, product in enumerate(
        stores,
        start=1
    ):

        rows.append({

            "#": index,

            "Mağaza": product["seller"],

            "Ürün": product["title"],

            "Fiyat": format_price(

                product["price"],

                product["currency"]

            ),

            "Durum": product["condition"]

        })


    st.dataframe(

        rows,

        use_container_width=True,

        hide_index=True

    )


# =========================================================
# ARAMA KUTUSU
# =========================================================

product_name = st.text_input(

    "🔎 Ürün adı",

    placeholder=(
        "Örn: Grundig Club BT Hoparlör"
    )

)


search_button = st.button(

    "🔍 İnternette Ara",

    type="primary",

    use_container_width=True

)


# =========================================================
# ÇALIŞTIR
# =========================================================

if search_button:

    if not product_name.strip():

        st.warning(
            "Lütfen ürün adı yaz."
        )

        st.stop()


    product_name = product_name.strip()


    st.info(

        f"🔎 **{product_name}** aranıyor..."

    )


    with st.spinner(

        "Google Shopping'den fiyatlar getiriliyor..."

    ):

        raw_items = search_google_shopping(

            product_name

        )


    if not raw_items:

        st.error(

            f'"{product_name}" için '
            f'API sonucu bulunamadı.'

        )

        st.stop()


    products = prepare_products(

        raw_items,

        product_name

    )


    # =====================================================
    # SONUÇ YOK
    # =====================================================

    if not products:

        st.error(

            f'"{product_name}" için '
            f'uygun ürün bulunamadı.'

        )

        st.warning(

            "Ürün adını model numarasıyla birlikte "
            "aramayı deneyebilirsin."

        )

        st.stop()


    # =====================================================
    # KATEGORİLER
    # =====================================================

    new_products = [

        x

        for x in products

        if x["condition"] == "Sıfır"

    ]


    used_products = [

        x

        for x in products

        if x["condition"] == "İkinci El"

    ]


    refurbished_products = [

        x

        for x in products

        if x["condition"] == "Yenilenmiş"

    ]


    # =====================================================
    # EN UCUZ
    # =====================================================

    cheapest = min(

        products,

        key=lambda x: x["price"]

    )


    cheapest_price = format_price(

        cheapest["price"],

        cheapest["currency"]

    )


    st.markdown(

        f"""
        <div class="best-card">

            <div class="best-title">
                🏆 En Ucuz Fiyat
            </div>

            <div style="
                font-size:22px;
                font-weight:800;
                margin-top:8px;
            ">
                {cheapest["title"]}
            </div>

            <div class="best-price">
                {cheapest_price}
            </div>

            <div style="
                font-size:17px;
                margin-top:8px;
            ">
                🏪 {cheapest["seller"]}
            </div>

        </div>
        """,

        unsafe_allow_html=True

    )


    # =====================================================
    # İSTATİSTİKLER
    # =====================================================

    stats = get_statistics(
        products
    )


    c1, c2, c3, c4 = st.columns(4)


    with c1:

        st.metric(

            "🛍️ Mağaza",

            len(
                cheapest_by_store(
                    products
                )
            )

        )


    with c2:

        st.metric(

            "💰 En Ucuz",

            format_price(

                stats["min"],

                cheapest["currency"]

            )

        )


    with c3:

        st.metric(

            "📈 En Pahalı",

            format_price(

                stats["max"],

                cheapest["currency"]

            )

        )


    with c4:

        st.metric(

            "📊 Sonuç",

            stats["count"]

        )


    st.divider()


    # =====================================================
    # MAĞAZA KARŞILAŞTIRMA
    # =====================================================

    st.header(
        "🏪 Mağaza Fiyat Karşılaştırması"
    )


    show_comparison_table(
        products
    )


    st.divider()


    # =====================================================
    # SIFIR
    # =====================================================

    st.header(
        "🟢 Sıfır Ürünler"
    )


    if new_products:

        for product in new_products[:20]:

            show_product(
                product
            )

    else:

        st.info(
            "Sıfır ürün bulunamadı."
        )


    st.divider()


    # =====================================================
    # İKİNCİ EL
    # =====================================================

    st.header(
        "🟠 İkinci El"
    )


    if used_products:

        for product in used_products[:20]:

            show_product(
                product
            )

    else:

        st.info(
            "Google Shopping aramasında "
            "ikinci el sonuç bulunamadı."
        )


    st.divider()


    # =====================================================
    # YENİLENMİŞ
    # =====================================================

    st.header(
        "🔵 Yenilenmiş"
    )


    if refurbished_products:

        for product in refurbished_products[:20]:

            show_product(
                product
            )

    else:

        st.info(
            "Google Shopping aramasında "
            "yenilenmiş sonuç bulunamadı."
        )


    st.divider()


    # =====================================================
    # FİYAT FARKI
    # =====================================================

    if stats["difference"] is not None:

        difference = format_price(

            stats["difference"],

            cheapest["currency"]

        )


        st.success(

            f"💡 En ucuz ve en pahalı sonuç arasında "
            f"**{difference}** fiyat farkı var."

        )


    st.caption(

        f"🔎 Toplam {len(products)} uygun "
        f"ürün sonucu işlendi."

    )
