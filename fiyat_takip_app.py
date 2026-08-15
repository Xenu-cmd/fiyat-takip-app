import streamlit as st
import requests


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
}

.subtitle {
    text-align: center;
    color: #6b7280;
    margin-bottom: 30px;
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

.best-card {
    background: #fefce8;
    border: 2px solid #facc15;
    padding: 25px;
    border-radius: 18px;
    margin: 20px 0;
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
# API ANAHTARI
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
            "Streamlit Secrets bölümüne "
            "SOCIALCRAWL_API_KEY ekle."
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

        "depth": 40

    }


    headers = {

        "x-api-key": api_key

    }


    try:

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=60
        )

    except Exception as e:

        st.error(
            f"API bağlantı hatası: {e}"
        )

        return []


    if response.status_code != 200:

        st.error(
            f"SocialCrawl HTTP hatası: "
            f"{response.status_code}"
        )

        try:

            st.code(
                response.text[:2000]
            )

        except:

            pass

        return []


    try:

        data = response.json()

    except:

        st.error(
            "API geçerli JSON döndürmedi."
        )

        return []


    if not data.get("success"):

        st.error(
            "SocialCrawl araması başarısız."
        )

        if "error" in data:

            st.code(
                str(data["error"])
            )

        return []


    return data.get(
        "data",
        {}
    ).get(
        "items",
        []
    )


# =========================================================
# ÜRÜN VERİLERİNİ DÜZENLE
# =========================================================

def prepare_products(items):

    products = []


    for item in items:

        product = item.get(
            "product",
            {}
        )


        title = product.get(
            "title"
        )


        if not title:

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

        except:

            continue


        currency = price_data.get(
            "currency",
            "TRY"
        )


        products.append({

            "title": title,

            "price": current_price,

            "currency": currency,

            "seller": product.get(
                "seller",
                "Bilinmeyen satıcı"
            ),

            "url": product.get(
                "url",
                ""
            ),

            "image": (
                product.get(
                    "image_urls",
                    []
                )[0]
                if product.get(
                    "image_urls",
                    []
                )
                else ""
            ),

            "rating": (
                product.get(
                    "rating",
                    {}
                ).get(
                    "average"
                )
                if isinstance(
                    product.get(
                        "rating",
                        {}
                    ),
                    dict
                )
                else None
            ),

            "rating_count": (
                product.get(
                    "rating",
                    {}
                ).get(
                    "count"
                )
                if isinstance(
                    product.get(
                        "rating",
                        {}
                    ),
                    dict
                )
                else None
            ),

            "availability": product.get(
                "availability"
            )

        })


    # Aynı ürün + satıcı + fiyat tekrarlarını temizle

    unique = {}

    for product in products:

        key = (
            product["title"].lower(),
            product["seller"].lower(),
            product["price"]
        )

        if key not in unique:

            unique[key] = product


    products = list(
        unique.values()
    )


    # En ucuzdan pahalıya sırala

    products.sort(
        key=lambda x: x["price"]
    )


    return products


# =========================================================
# İKİNCİ EL / YENİLENMİŞ TESPİTİ
# =========================================================

def detect_condition(product):

    text = (
        product["title"] + " " +
        str(product["seller"])
    ).lower()


    used_words = [

        "ikinci el",
        "2.el",
        "2 el",
        "used",
        "pre-owned",
        "preowned",
        "kullanılmış"

    ]


    refurbished_words = [

        "yenilenmiş",
        "refurbished",
        "renewed"

    ]


    for word in refurbished_words:

        if word in text:

            return "Yenilenmiş"


    for word in used_words:

        if word in text:

            return "İkinci El"


    return "Sıfır"


# =========================================================
# PARA BİRİMİ
# =========================================================

def format_price(price, currency):

    if currency == "TRY":

        return f"{price:,.2f} TL"

    if currency == "USD":

        return f"${price:,.2f}"

    if currency == "EUR":

        return f"€{price:,.2f}"

    return f"{price:,.2f} {currency}"


# =========================================================
# SONUÇ KARTI
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

            except:

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


        if product["rating"]:

            rating_text = (
                f"⭐ {product['rating']}"
            )

            if product["rating_count"]:

                rating_text += (
                    f" ({product['rating_count']:,} değerlendirme)"
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
    placeholder="Örn: Grundig Club"
)


search_button = st.button(
    "🔍 Fiyatları Ara",
    type="primary",
    use_container_width=True
)


# =========================================================
# ARAMA
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
        raw_items
    )


    if not products:

        st.error(
            f'"{product_name}" için ürün bulunamadı.'
        )

        st.write(
            "API sonuç döndürmedi. "
            "Ürün adını model numarasıyla birlikte "
            "deneyebilirsin."
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
        x for x in products
        if x["condition"] == "Sıfır"
    ]


    used_products = [
        x for x in products
        if x["condition"] == "İkinci El"
    ]


    refurbished_products = [
        x for x in products
        if x["condition"] == "Yenilenmiş"
    ]


    # =====================================================
    # EN UCUZ
    # =====================================================

    cheapest = products[0]


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
                {format_price(
                    cheapest["price"],
                    cheapest["currency"]
                )}
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

        for item in new_products:

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

        for item in used_products:

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

        for item in refurbished_products:

            show_product(
                item,
                "refurbished-card"
            )


    else:

        st.info(
            "Bu aramada yenilenmiş sonuç bulunamadı."
        )


    # =====================================================
    # API BİLGİSİ
    # =====================================================

    st.divider()

    st.caption(
        f"🔎 {len(products)} fiyat sonucu bulundu."
    )
