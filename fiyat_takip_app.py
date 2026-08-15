import streamlit as st
import requests
import re
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
# TASARIM
# =========================================================

st.markdown("""
<style>

.main-title {
    text-align: center;
    font-size: 42px;
    font-weight: 900;
    color: #111827;
    margin-bottom: 5px;
}

.subtitle {
    text-align: center;
    color: #6b7280;
    font-size: 17px;
    margin-bottom: 25px;
}

.best-card {
    background: linear-gradient(
        135deg,
        #ecfdf5,
        #f0fdf4
    );

    border: 2px solid #22c55e;
    border-radius: 20px;

    padding: 25px;

    margin-top: 20px;
    margin-bottom: 20px;
}

.best-title {
    font-size: 18px;
    font-weight: 800;
    color: #166534;
}

.best-product {
    font-size: 24px;
    font-weight: 800;
    color: #111827;
    margin-top: 8px;
}

.best-price {
    font-size: 42px;
    font-weight: 900;
    color: #15803d;
    margin-top: 8px;
}

.result-card {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 16px;
    padding: 18px;
    margin-bottom: 12px;
}

.new-card {
    border-left: 6px solid #22c55e;
}

.used-card {
    border-left: 6px solid #f97316;
}

.refurb-card {
    border-left: 6px solid #3b82f6;
}

.result-title {
    font-size: 18px;
    font-weight: 800;
    color: #111827;
}

.result-price {
    font-size: 27px;
    font-weight: 900;
    color: #111827;
    margin-top: 7px;
}

.result-store {
    color: #2563eb;
    font-weight: 700;
    margin-top: 5px;
}

.result-condition {
    font-weight: 800;
    margin-top: 4px;
}

.warning-box {
    background: #fffbeb;
    border: 1px solid #fcd34d;
    border-radius: 12px;
    padding: 15px;
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
    'Sıfır • İkinci El • Yenilenmiş ürünleri tek yerde karşılaştır'
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


HEADERS = {
    "x-api-key": API_KEY,
    "Accept": "application/json"
}


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
# ÜRÜN KELİMELERİ
# =========================================================

def get_product_words(product):

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

    for word in normalize(
        product
    ).split():

        if len(word) < 2:

            continue

        if word in ignored:

            continue

        words.append(
            word
        )

    return words


# =========================================================
# ÜRÜNÜN BAŞLIKTA GERÇEKTEN VAR OLUP OLMADIĞINI KONTROL
# =========================================================

def is_product_match(
    product,
    title,
    description=""
):

    product_words = get_product_words(
        product
    )

    if not product_words:

        return True


    title_normalized = normalize(
        title
    )


    description_normalized = normalize(
        description
    )


    # -----------------------------------------------------
    # EN ÖNEMLİ KURAL
    #
    # "Grundig Club"
    #
    # için başlıkta hem:
    #
    # grundig
    # club
    #
    # bulunmalı.
    # -----------------------------------------------------

    for word in product_words:

        if word not in title_normalized:

            return False


    # -----------------------------------------------------
    # ALÂKASIZ ÜRÜNLER
    # -----------------------------------------------------

    product_text = normalize(
        product
    )

    combined_text = (
        title_normalized
        + " "
        + description_normalized
    )


    unrelated_words = [

        "kulaklik",
        "kulak ici",
        "kulakici",
        "headphone",
        "headset",

        "kablolu",
        "kablo",

        "mikrofon",
        "microphone",

        "kilif",
        "case",

        "canta",

        "yedek parca",

        "kumanda",
        "remote"

    ]


    for bad_word in unrelated_words:

        if bad_word in combined_text:

            if bad_word not in product_text:

                return False


    return True


# =========================================================
# DOMAIN
# =========================================================

def get_domain(url):

    try:

        parsed = urlparse(
            url
        )

        return parsed.netloc.replace(
            "www.",
            ""
        )

    except Exception:

        return "Bilinmiyor"


# =========================================================
# FİYAT BUL
# =========================================================

def extract_price(text):

    if not text:

        return None


    text = text.replace(
        "\xa0",
        " "
    )


    patterns = [

        # 1.999,99 TL
        r"(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?)\s*(?:TL|₺)",

        # 1999,99 TL
        r"(\d{3,7}(?:,\d{1,2})?)\s*(?:TL|₺)",

        # TL 1999
        r"(?:TL|₺)\s*(\d{3,7}(?:[.,]\d{1,2})?)"

    ]


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

                    if len(parts[-1]) == 2:

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


                price = float(
                    value
                )


                if (
                    price >= 10
                    and
                    price <= 10000000
                ):

                    return price


            except Exception:

                continue


    return None


# =========================================================
# GOOGLE SHOPPING
# =========================================================

def google_shopping_search(
    product
):

    endpoint = (
        "https://www.socialcrawl.dev"
        "/v1/google_shopping/product-search"
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

    except Exception as error:

        st.warning(
            f"Google Shopping bağlantı hatası: {error}"
        )

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


    items = (
        data
        .get("data", {})
        .get("items", [])
    )


    results = []


    for item in items:

        product_data = item.get(
            "product",
            {}
        )


        title = product_data.get(
            "title",
            ""
        )


        description = product_data.get(
            "description",
            ""
        )


        # -------------------------------------------------
        # ÇOK ÖNEMLİ FİLTRE
        # -------------------------------------------------

        if not is_product_match(

            product,

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


        price = price_data.get(
            "current"
        )


        if price is None:

            continue


        try:

            price = float(
                price
            )

        except Exception:

            continue


        currency = str(
            price_data.get(
                "currency",
                "TRY"
            )
        ).upper()


        image_urls = product_data.get(
            "image_urls",
            []
        )


        image = ""

        if image_urls:

            image = image_urls[0]


        ext = product_data.get(
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

            "currency":
                currency,

            "seller":
                product_data.get(
                    "seller",
                    "Bilinmiyor"
                ),

            "url":
                product_data.get(
                    "url",
                    ""
                ),

            "image":
                image,

            "condition":
                "Sıfır",

            "source":
                "Google Shopping",

            "gid":
                ext.get(
                    "gid",
                    ""
                ),

            "product_id":
                product_data.get(
                    "id",
                    ""
                ),

            "data_docid":
                ext.get(
                    "data_docid",
                    ""
                )

        })


    return results


# =========================================================
# GOOGLE SEARCH
# =========================================================

def google_search(
    query,
    product,
    condition
):

    endpoint = (
        "https://www.socialcrawl.dev"
        "/v1/google/search"
    )


    params = {

        "query": query,

        "region": "TR"

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


    items = (
        data
        .get("data", {})
        .get("items", [])
    )


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


        description = item.get(
            "snippet",
            item.get(
                "description",
                ""
            )
        )


        if not title:

            continue


        # -------------------------------------------------
        # ÜRÜN FİLTRESİ
        # -------------------------------------------------

        if not is_product_match(

            product,

            title,

            description

        ):

            continue


        combined = (
            title
            + " "
            + description
        )


        price = extract_price(
            combined
        )


        if price is None:

            continue


        results.append({

            "title":
                title,

            "description":
                description,

            "price":
                price,

            "currency":
                "TRY",

            "seller":
                get_domain(
                    url
                ),

            "url":
                url,

            "image":
                "",

            "condition":
                condition,

            "source":
                "Google Search"

        })


    return results


# =========================================================
# İKİNCİ EL ARAMA
# =========================================================

def search_used(
    product
):

    queries = [

        f'"{product}" ikinci el',

        f'"{product}" 2.el',

        f'"{product}" 2 el',

        f'"{product}" kullanılmış',

        f'"{product}" site:sahibinden.com',

        f'"{product}" site:letgo.com',

        f'"{product}" ikinci el fiyat',

        f'"{product}" ikinci el TL'

    ]


    results = []


    for query in queries:

        found = google_search(

            query,

            product,

            "İkinci El"

        )


        results.extend(
            found
        )


    return results


# =========================================================
# YENİLENMİŞ
# =========================================================

def search_refurbished(
    product
):

    queries = [

        f'"{product}" yenilenmiş',

        f'"{product}" yenilenmiş fiyat',

        f'"{product}" yenilenmiş TL',

        f'"{product}" refurbished',

        f'"{product}" renewed',

        f'"{product}" site:easycep.com',

        f'"{product}" site:hepsiburada.com yenilenmiş',

        f'"{product}" site:trendyol.com yenilenmiş'

    ]


    results = []


    for query in queries:

        found = google_search(

            query,

            product,

            "Yenilenmiş"

        )


        results.extend(
            found
        )


    return results


# =========================================================
# SONUÇ TEKRARLARINI TEMİZLE
# =========================================================

def remove_duplicates(
    results
):

    unique = {}


    for item in results:

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


        try:

            price = round(
                float(
                    item["price"]
                ),
                2
            )

        except:

            continue


        # URL varsa URL önemli.
        # URL yoksa başlık + satıcı + fiyat.
        if url:

            key = (
                url,
                price
            )

        else:

            key = (
                title,
                seller,
                price
            )


        if key not in unique:

            unique[key] = item


    final = list(
        unique.values()
    )


    # EN UCUZDAN PAHALIYA
    final.sort(
        key=lambda x:
            x["price"]
    )


    return final


# =========================================================
# SADECE TL SONUÇLARI
# =========================================================

def only_try(
    results
):

    output = []


    for item in results:

        currency = str(
            item.get(
                "currency",
                "TRY"
            )
        ).upper()


        if currency in [
            "TRY",
            "TL"
        ]:

            output.append(
                item
            )


    return output


# =========================================================
# SONUÇ KARTI
# =========================================================

def show_result(
    item,
    number=None
):

    condition = item[
        "condition"
    ]


    if condition == "Sıfır":

        css = "new-card"

        icon = "🟢"


    elif condition == "İkinci El":

        css = "used-card"

        icon = "🟠"


    else:

        css = "refurb-card"

        icon = "🔵"


    number_text = ""

    if number is not None:

        number_text = f"{number}. "


    st.markdown(
        f"""
        <div class="result-card {css}">

            <div class="result-title">
                {number_text}
                {icon}
                {item["title"]}
            </div>

            <div class="result-price">
                {item["price"]:,.2f} TL
            </div>

            <div class="result-store">
                🏪 {item["seller"]}
            </div>

            <div class="result-condition">
                📦 {condition}
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
# EN UCUZU GÖSTER
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
                📦 {cheapest["condition"]}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )


    if cheapest.get(
        "url"
    ):

        st.link_button(
            "🛒 En Ucuz Ürüne Git",
            cheapest["url"]
        )


# =========================================================
# ARAMA KUTUSU
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
# ANA PROGRAM
# =========================================================

if search_button:


    # -----------------------------------------------------
    # API KONTROL
    # -----------------------------------------------------

    if not API_KEY:

        st.error(
            "❌ SocialCrawl API anahtarı bulunamadı."
        )

        st.info(
            "Streamlit → Settings → Secrets "
            "bölümüne API anahtarını ekle."
        )

        st.code(
            'SOCIALCRAWL_API_KEY = "sc_..."'
        )

        st.stop()


    # -----------------------------------------------------
    # ÜRÜN KONTROL
    # -----------------------------------------------------

    if not product.strip():

        st.warning(
            "Lütfen bir ürün adı yaz."
        )

        st.stop()


    product = product.strip()


    # -----------------------------------------------------
    # ARAMA BAŞLIYOR
    # -----------------------------------------------------

    st.info(
        f"🔎 **{product}** için araştırma yapılıyor..."
    )


    # -----------------------------------------------------
    # SIFIR
    # -----------------------------------------------------

    with st.spinner(
        "🟢 Sıfır ürünler araştırılıyor..."
    ):

        shopping_results = (
            google_shopping_search(
                product
            )
        )


    # -----------------------------------------------------
    # İKİNCİ EL
    # -----------------------------------------------------

    with st.spinner(
        "🟠 İkinci el ürünler araştırılıyor..."
    ):

        used_results = search_used(
            product
        )


    # -----------------------------------------------------
    # YENİLENMİŞ
    # -----------------------------------------------------

    with st.spinner(
        "🔵 Yenilenmiş ürünler araştırılıyor..."
    ):

        refurbished_results = (
            search_refurbished(
                product
            )
        )


    # -----------------------------------------------------
    # SADECE TL
    # -----------------------------------------------------

    shopping_results = only_try(
        shopping_results
    )

    used_results = only_try(
        used_results
    )

    refurbished_results = only_try(
        refurbished_results
    )


    # -----------------------------------------------------
    # TEMİZLE
    # -----------------------------------------------------

    new_results = remove_duplicates(
        shopping_results
    )

    used_results = remove_duplicates(
        used_results
    )

    refurbished_results = remove_duplicates(
        refurbished_results
    )


    # -----------------------------------------------------
    # TÜM SONUÇLAR
    # -----------------------------------------------------

    all_results = remove_duplicates(

        new_results
        + used_results
        + refurbished_results

    )


    # -----------------------------------------------------
    # SONUÇ YOK
    # -----------------------------------------------------

    if not all_results:

        st.error(
            f'"{product}" için uygun fiyat bulunamadı.'
        )

        st.warning(
            "Ürün adının modelini daha açık yazmayı dene."
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

        if new_results:

            st.metric(
                "🟢 Sıfır",
                f"{new_results[0]['price']:,.2f} TL"
            )

        else:

            st.metric(
                "🟢 Sıfır",
                "Yok"
            )


    with col2:

        if used_results:

            st.metric(
                "🟠 İkinci El",
                f"{used_results[0]['price']:,.2f} TL"
            )

        else:

            st.metric(
                "🟠 İkinci El",
                "Yok"
            )


    with col3:

        if refurbished_results:

            st.metric(
                "🔵 Yenilenmiş",
                f"{refurbished_results[0]['price']:,.2f} TL"
            )

        else:

            st.metric(
                "🔵 Yenilenmiş",
                "Yok"
            )


    with col4:

        st.metric(
            "📦 Toplam",
            len(all_results)
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


    for index, item in enumerate(
        all_results,
        start=1
    ):

        show_result(
            item,
            index
        )


    # =====================================================
    # SIFIR
    # =====================================================

    st.divider()

    st.header(
        "🟢 Sıfır Ürünler"
    )


    if new_results:

        for index, item in enumerate(
            new_results,
            start=1
        ):

            show_result(
                item,
                index
            )

    else:

        st.info(
            "Sıfır ürün bulunamadı."
        )


    # =====================================================
    # İKİNCİ EL
    # =====================================================

    st.divider()

    st.header(
        "🟠 İkinci El"
    )


    if used_results:

        for index, item in enumerate(
            used_results,
            start=1
        ):

            show_result(
                item,
                index
            )

    else:

        st.info(
            "Bu ürün için fiyatı görünen ikinci el sonucu bulunamadı."
        )


    # =====================================================
    # YENİLENMİŞ
    # =====================================================

    st.divider()

    st.header(
        "🔵 Yenilenmiş"
    )


    if refurbished_results:

        for index, item in enumerate(
            refurbished_results,
            start=1
        ):

            show_result(
                item,
                index
            )

    else:

        st.info(
            "Bu ürün için fiyatı görünen yenilenmiş sonucu bulunamadı."
        )


    # =====================================================
    # FİYAT ARALIĞI
    # =====================================================

    st.divider()

    prices = [

        x["price"]

        for x in all_results

        if str(
            x.get(
                "currency",
                "TRY"
            )
        ).upper()
        in ["TRY", "TL"]

    ]


    if len(prices) >= 2:

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
                "Fiyat farkı",
                f"{difference:,.2f} TL"
            )
