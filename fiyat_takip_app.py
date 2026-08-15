import streamlit as st
import requests
import re


# =========================================================
# SAYFA AYARLARI
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
    margin-top: 20px;
}

.subtitle {
    text-align: center;
    color: #6b7280;
    margin-bottom: 30px;
}

.best-card {
    background: #fefce8;
    border: 2px solid #facc15;
    padding: 25px;
    border-radius: 18px;
    margin: 25px 0;
}

.product-card {
    padding: 18px;
    border-radius: 16px;
    background: white;
    border: 1px solid #e5e7eb;
    margin-bottom: 15px;
    box-shadow: 0 3px 12px rgba(0,0,0,0.05);
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
    font-size: 19px;
    font-weight: 800;
}

.product-price {
    font-size: 28px;
    font-weight: 900;
    color: #15803d;
}

.product-store {
    color: #2563eb;
    font-weight: 700;
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
    'Sıfır, ikinci el ve yenilenmiş ürünleri karşılaştır'
    '</div>',
    unsafe_allow_html=True
)


# =========================================================
# API KEY
# =========================================================

def get_api_key():

    try:
        return st.secrets["SOCIALCRAWL_API_KEY"]

    except Exception:
        return None


# =========================================================
# SOCIALCRAWL ARAMA
# =========================================================

def search_socialcrawl(product):

    api_key = get_api_key()

    if not api_key:

        st.error(
            "❌ SOCIALCRAWL_API_KEY bulunamadı."
        )

        st.info(
            "Streamlit Secrets bölümünde şu değer bulunmalı:"
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

        "query": product,

        "country": "Turkey",

        "language": "tr",

        "depth": 40,

        "sort_by": "price_low_to_high"

    }


    headers = {

        "x-api-key": api_key

    }


    try:

        response = requests.get(

            url,

            params=params,

            headers=headers,

            timeout=30

        )


    except requests.exceptions.Timeout:

        st.error(
            "⏱️ Arama 30 saniye içinde cevap vermedi."
        )

        return []


    except Exception as e:

        st.error(
            f"❌ API bağlantı hatası: {e}"
        )

        return []


    if response.status_code != 200:

        st.error(
            f"❌ API HTTP hatası: "
            f"{response.status_code}"
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
            "❌ API geçerli bir cevap döndürmedi."
        )

        return []


    if not data.get("success"):

        st.error(
            "❌ SocialCrawl araması başarısız."
        )

        return []


    return (
        data
        .get("data", {})
        .get("items", [])
    )


# =========================================================
# TÜRKÇE KARAKTER TEMİZLEME
# =========================================================

def normalize_text(text):

    if not text:

        return ""

    text = text.lower()

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
# ÜRÜN UYGUNLUK KONTROLÜ
# =========================================================

def product_matches(
    search_query,
    title
):

    search = normalize_text(
        search_query
    )

    title = normalize_text(
        title
    )

    search_words = [
        word
        for word in search.split()
        if len(word) >= 2
    ]

    if not search_words:

        return True


    matched = 0


    for word in search_words:

        if word in title:

            matched += 1


    ratio = (
        matched /
        len(search_words)
    )


    # Tek kelimelik aramalarda
    # kelimenin bulunması yeterli

    if len(search_words) == 1:

        return matched == 1


    # Çok kelimeli aramalarda
    # en az %70 eşleşme

    return ratio >= 0.70


# =========================================================
# ÜRÜNLERİ HAZIRLA
# =========================================================

def prepare_products(
    items,
    search_query
):

    products = []


    for item in items:

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


        # Alakasız ürünleri filtrele

        if not product_matches(
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


        current_price = price_data.get(
            "current"
        )


        if current_price is None:

            continue


        try:

            current_price = float(
                current_price
            )

        except Exception:

            continue


        if current_price <= 0:

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


        image_urls = product.get(
            "image_urls",
            []
        )


        image = ""


        if image_urls:

            image = image_urls[0]


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


        products.append({

            "title": title,

            "price": current_price,

            "currency": currency,

            "seller": seller,

            "url": url,

            "image": image,

            "rating": rating,

            "rating_count": rating_count

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

            product["price"]

        )


        if key not in unique:

            unique[key] = product


    products = list(
        unique.values()
    )


    # =====================================================
    # FİYATA GÖRE SIRALA
    # =====================================================

    products.sort(
        key=lambda x: x["price"]
    )


    return products


# =========================================================
# ÜRÜN DURUMUNU BUL
# =========================================================

def detect_condition(
    product
):

    text = normalize_text(

        product["title"]
        + " "
        + str(product["seller"])

    )


    refurbished_words = [

        "yenilenmis",

        "refurbished",

        "renewed"

    ]


    used_words = [

        "ikinci el",

        "2 el",

        "2el",

        "used",

        "pre owned",

        "preowned",

        "kullanilmis"

    ]


    for word in refurbished_words:

        if word in text:

            return "Yenilenmiş"


    for word in used_words:

        if word in text:

            return "İkinci El"


    return "Sıfır"


# =========================================================
# FİYAT FORMATLAMA
# =========================================================

def format_price(
    price,
    currency
):

    if currency == "TRY":

        return f"{price:,.2f} TL"


    if currency == "EUR":

        return f"{price:,.2f} €"


    if currency == "USD":

        return f"{price:,.2f} $"


    if currency == "GBP":

        return f"{price:,.2f} £"


    return f"{price:,.2f} {currency}"


# =========================================================
# ÜRÜN KARTI
# =========================================================

def show_product(
    product,
    card_class
):

    price = format_price(

        product["price"],

        product["currency"]

    )


    col1, col2 = st.columns(
        [1, 4]
    )


    with col1:

        if product["image"]:

            try:

                st.image(
                    product["image"],
                    width=150
                )

            except Exception:

                pass


    with col2:

        st.markdown(

            f"""
            <div class="product-card {card_class}">

                <div class="product-title">
                    {product["title"]}
                </div>

                <div class="product-price">
                    {price}
                </div>

                <div class="product-store">
                    🏪 {product["seller"]}
                </div>

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
                    f"değerlendirme)"

                )


            st.write(
                rating_text
            )


        if product["url"]:

            st.link_button(

                "🛒 Ürüne Git",

                product["url"]

            )


# =========================================================
# ARAMA KUTUSU
# =========================================================

product_name = st.text_input(

    "🔎 Ürün adı",

    placeholder=(
        "Örn: Grundig Club"
    )

)


search_button = st.button(

    "🔍 Fiyatları Ara",

    type="primary",

    use_container_width=True

)


# =========================================================
# PROGRAMI ÇALIŞTIR
# =========================================================

if search_button:

    if not product_name.strip():

        st.warning(
            "Lütfen bir ürün adı yaz."
        )

        st.stop()


    product_name = product_name.strip()


    with st.spinner(

        f'"{product_name}" aranıyor...'

    ):

        raw_items = search_socialcrawl(

            product_name

        )


    products = prepare_products(

        raw_items,

        product_name

    )


    if not products:

        st.error(

            f'"{product_name}" için '
            f'uygun ürün bulunamadı.'

        )

        st.info(

            "Örneğin ürünün model numarasını "
            "da yazarak tekrar deneyebilirsin."

        )

        st.stop()


    # =====================================================
    # KATEGORİLER
    # =====================================================

    for item in products:

        item["condition"] = detect_condition(
            item
        )


    new_products = [

        item

        for item in products

        if item["condition"] == "Sıfır"

    ]


    used_products = [

        item

        for item in products

        if item["condition"] == "İkinci El"

    ]


    refurbished_products = [

        item

        for item in products

        if item["condition"] == "Yenilenmiş"

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

            <h2>🏆 En Ucuz Fiyat</h2>

            <div style="
                font-size:22px;
                font-weight:800;
            ">
                {cheapest["title"]}
            </div>

            <div style="
                font-size:38px;
                font-weight:900;
                color:#15803d;
            ">
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
    # ÖZET
    # =====================================================

    col1, col2, col3 = st.columns(3)


    with col1:

        if new_products:

            st.metric(

                "🟢 Sıfır",

                format_price(

                    new_products[0]["price"],

                    new_products[0]["currency"]

                )

            )

        else:

            st.metric(

                "🟢 Sıfır",

                "Bulunamadı"

            )


    with col2:

        if used_products:

            st.metric(

                "🟠 İkinci El",

                format_price(

                    used_products[0]["price"],

                    used_products[0]["currency"]

                )

            )

        else:

            st.metric(

                "🟠 İkinci El",

                "Bulunamadı"

            )


    with col3:

        if refurbished_products:

            st.metric(

                "🔵 Yenilenmiş",

                format_price(

                    refurbished_products[0]["price"],

                    refurbished_products[0]["currency"]

                )

            )

        else:

            st.metric(

                "🔵 Yenilenmiş",

                "Bulunamadı"

            )


    st.divider()


    # =====================================================
    # SIFIR
    # =====================================================

    st.header(
        "🟢 Sıfır Ürünler"
    )


    if new_products:

        for item in new_products[:20]:

            show_product(

                item,

                "new-card"

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

        for item in used_products[:20]:

            show_product(

                item,

                "used-card"

            )

    else:

        st.info(
            "Bu aramada ikinci el sonuç bulunamadı."
        )


    st.divider()


    # =====================================================
    # YENİLENMİŞ
    # =====================================================

    st.header(
        "🔵 Yenilenmiş"
    )


    if refurbished_products:

        for item in refurbished_products[:20]:

            show_product(

                item,

                "refurbished-card"

            )

    else:

        st.info(
            "Bu aramada yenilenmiş sonuç bulunamadı."
        )


    st.divider()


    st.success(

        f"🔎 {len(products)} uygun ürün sonucu bulundu."

    )
