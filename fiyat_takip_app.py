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

.result-card {
    padding: 18px;
    border-radius: 14px;
    border: 1px solid #e5e7eb;
    margin-bottom: 12px;
    background-color: #ffffff;
}

.best-card {
    padding: 25px;
    border-radius: 18px;
    background-color: #f0fdf4;
    border: 2px solid #22c55e;
    margin-bottom: 25px;
}

.price-big {
    font-size: 32px;
    font-weight: 800;
    color: #15803d;
}

.store-name {
    font-size: 17px;
    font-weight: 700;
    color: #2563eb;
}

.used {
    color: #c2410c;
    font-weight: 700;
}

.new {
    color: #15803d;
    font-weight: 700;
}

.refurbished {
    color: #2563eb;
    font-weight: 700;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# BAŞLIK
# =========================================================

st.title("🔎 Akıllı Fiyat Karşılaştırma")

st.write(
    "Sıfır, ikinci el ve yenilenmiş ürünleri "
    "tek aramada karşılaştır."
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


API_KEY = get_api_key()


# =========================================================
# API HEADERS
# =========================================================

API_HEADERS = {

    "x-api-key": API_KEY or "",

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

def product_words(product):

    words = []

    for word in normalize(
        product
    ).split():

        if len(word) >= 2:

            words.append(
                word
            )

    return words


# =========================================================
# ALAKALILIK
# =========================================================

def relevance(
    product,
    title,
    description=""
):

    words = product_words(
        product
    )

    text = normalize(
        str(title)
        + " "
        + str(description)
    )

    if not words:

        return 0

    score = 0

    for word in words:

        if word in text:

            score += 1

    return score


# =========================================================
# ÜRÜN ALAKALI MI
# =========================================================

def is_relevant(
    product,
    title,
    description=""
):

    words = product_words(
        product
    )

    score = relevance(
        product,
        title,
        description
    )

    if not words:

        return True

    # Tek kelimelik aramada
    if len(words) == 1:

        return score >= 1

    # 2+ kelimede en az %60
    return (
        score / len(words)
    ) >= 0.60


# =========================================================
# DOMAIN
# =========================================================

def domain(url):

    try:

        return urlparse(
            url
        ).netloc.replace(
            "www.",
            ""
        )

    except:

        return ""


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
        r"(\d{1,3}(?:[.]\d{3})+(?:,\d{1,2})?)\s*(?:TL|₺)",

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

                price = float(
                    value
                )

                if (
                    price >= 10
                    and
                    price <= 10000000
                ):

                    return price

            except:

                continue

    return None


# =========================================================
# GOOGLE SHOPPING API
# =========================================================

def shopping_search(
    product
):

    if not API_KEY:

        return []

    url = (
        "https://www.socialcrawl.dev"
        "/v1/google_shopping/"
        "product-search"
    )

    params = {

        "query": product,

        "country": "Turkey",

        "language": "tr",

        "depth": 40,

        "sort_by":
            "price_low_to_high"

    }

    try:

        response = requests.get(

            url,

            params=params,

            headers=API_HEADERS,

            timeout=60

        )

    except Exception:

        return []

    if response.status_code != 200:

        return []

    try:

        data = response.json()

    except:

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

        price = price_data.get(
            "current"
        )

        if price is None:

            continue

        try:

            price = float(
                price
            )

        except:

            continue

        results.append({

            "title": title,

            "description":
                description,

            "price": price,

            "currency":
                price_data.get(
                    "currency",
                    "TRY"
                ),

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

            "image":
                (
                    p.get(
                        "image_urls",
                        [""]
                    )[0]
                    if p.get(
                        "image_urls"
                    )
                    else ""
                ),

            "condition":
                "Sıfır",

            "source":
                "Google Shopping"

        })

    return results


# =========================================================
# GOOGLE SEARCH API
# =========================================================

def google_search(
    query,
    product,
    condition
):

    if not API_KEY:

        return []

    url = (
        "https://www.socialcrawl.dev"
        "/v1/google/search"
    )

    params = {

        "query": query,

        "region": "TR"

    }

    try:

        response = requests.get(

            url,

            params=params,

            headers=API_HEADERS,

            timeout=40

        )

    except Exception:

        return []

    if response.status_code != 200:

        return []

    try:

        data = response.json()

    except:

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

        description = item.get(
            "description",
            ""
        )

        url_value = item.get(
            "url",
            ""
        )

        if not title:

            continue

        if not is_relevant(
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
                domain(
                    url_value
                ),

            "url":
                url_value,

            "image":
                "",

            "condition":
                condition,

            "source":
                "Google Search"

        })

    return results


# =========================================================
# İKİNCİ EL ARAMALARI
# =========================================================

def search_used(
    product
):

    results = []

    queries = [

        f'"{product}" ikinci el fiyat',

        f'"{product}" 2.el fiyat',

        f'"{product}" ikinci el TL',

        f'"{product}" site:letgo.com',

        f'"{product}" site:sahibinden.com',

    ]

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
# YENİLENMİŞ ARAMALARI
# =========================================================

def search_refurbished(
    product
):

    results = []

    queries = [

        f'"{product}" yenilenmiş',

        f'"{product}" yenilenmiş fiyat',

        f'"{product}" refurbished',

        f'"{product}" yenilenmiş TL',

        f'"{product}" site:easycep.com',

        f'"{product}" site:hepsiburada.com yenilenmiş',

        f'"{product}" site:trendyol.com yenilenmiş'

    ]

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
# TEKRARLARI TEMİZLE
# =========================================================

def remove_duplicates(
    results
):

    unique = {}

    for item in results:

        key = (

            normalize(
                item["title"]
            ),

            normalize(
                item["seller"]
            ),

            round(
                item["price"],
                2
            )

        )

        if key not in unique:

            unique[key] = item

    results = list(
        unique.values()
    )

    results.sort(
        key=lambda x:
            x["price"]
    )

    return results


# =========================================================
# TL FORMAT
# =========================================================

def money(
    price,
    currency="TRY"
):

    try:

        price = float(
            price
        )

    except:

        return "Fiyat yok"

    currency = str(
        currency
    ).upper()

    if currency in [
        "TRY",
        "TL"
    ]:

        return (
            f"{price:,.2f} TL"
        )

    if currency == "USD":

        return (
            f"${price:,.2f}"
        )

    if currency == "EUR":

        return (
            f"€{price:,.2f}"
        )

    return (
        f"{price:,.2f} "
        f"{currency}"
    )


# =========================================================
# SONUÇ KARTI
# =========================================================

def show_result(
    item
):

    condition = item[
        "condition"
    ]

    if condition == "Sıfır":

        icon = "🟢"

    elif condition == "İkinci El":

        icon = "🟠"

    else:

        icon = "🔵"


    with st.container(
        border=True
    ):

        col1, col2 = st.columns(
            [1, 4]
        )

        with col1:

            if item.get(
                "image"
            ):

                try:

                    st.image(
                        item["image"],
                        width=130
                    )

                except:

                    pass

        with col2:

            st.write(
                f"### {item['title']}"
            )

            st.write(
                f"💰 **{money(item['price'], item['currency'])}**"
            )

            st.write(
                f"🏪 **{item['seller']}**"
            )

            st.write(
                f"{icon} **{condition}**"
            )

            if item.get(
                "description"
            ):

                description = (
                    item["description"]
                    .strip()
                )

                if description:

                    st.caption(
                        description[:300]
                    )

            if item.get(
                "url"
            ):

                st.link_button(
                    "🛒 Ürüne Git",
                    item["url"]
                )


# =========================================================
# ARAMA KUTUSU
# =========================================================

product = st.text_input(

    "Ürün adı",

    placeholder=
        "Örn: Grundig Club BT Hoparlör"

)


search_button = st.button(

    "🔍 Fiyatları Karşılaştır",

    type="primary",

    use_container_width=True

)


# =========================================================
# ÇALIŞTIR
# =========================================================

if search_button:

    if not product.strip():

        st.warning(
            "Lütfen ürün adı gir."
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

        st.code(
            'SOCIALCRAWL_API_KEY = "sc_..."'
        )

        st.stop()


    product = product.strip()


    # -----------------------------------------------------
    # ARAMA
    # -----------------------------------------------------

    st.info(
        f"🔎 **{product}** aranıyor..."
    )


    # -----------------------------------------------------
    # SIFIR
    # -----------------------------------------------------

    with st.spinner(
        "🟢 Sıfır ürünler aranıyor..."
    ):

        new_results = shopping_search(
            product
        )


    # -----------------------------------------------------
    # İKİNCİ EL
    # -----------------------------------------------------

    with st.spinner(
        "🟠 İkinci el ilanlar aranıyor..."
    ):

        used_results = search_used(
            product
        )


    # -----------------------------------------------------
    # YENİLENMİŞ
    # -----------------------------------------------------

    with st.spinner(
        "🔵 Yenilenmiş ürünler aranıyor..."
    ):

        refurbished_results = (
            search_refurbished(
                product
            )
        )


    # -----------------------------------------------------
    # TEMİZLE
    # -----------------------------------------------------

    new_results = remove_duplicates(
        new_results
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

    all_results = (

        new_results

        + used_results

        + refurbished_results

    )


    all_results = remove_duplicates(
        all_results
    )


    # -----------------------------------------------------
    # SONUÇ YOK
    # -----------------------------------------------------

    if not all_results:

        st.error(
            f'"{product}" için fiyat bulunamadı.'
        )

        st.stop()


    # -----------------------------------------------------
    # EN UCUZ
    # -----------------------------------------------------

    cheapest = min(

        all_results,

        key=lambda x:
            x["price"]

    )


    st.success(
        "🏆 En ucuz fiyat bulundu!"
    )


    with st.container(
        border=True
    ):

        st.subheader(
            "🏆 En Ucuz Fiyat"
        )

        st.write(
            f"### {cheapest['title']}"
        )

        st.markdown(
            f"# {money(cheapest['price'], cheapest['currency'])}"
        )

        st.write(
            f"🏪 **{cheapest['seller']}**"
        )

        st.write(
            f"📦 **{cheapest['condition']}**"
        )

        if cheapest.get(
            "url"
        ):

            st.link_button(
                "🛒 En Ucuz Ürüne Git",
                cheapest["url"]
            )


    st.divider()


    # -----------------------------------------------------
    # ÖZET
    # -----------------------------------------------------

    st.subheader(
        "📊 Fiyat Özeti"
    )


    c1, c2, c3, c4 = st.columns(
        4
    )


    with c1:

        if new_results:

            st.metric(
                "🟢 Sıfır",
                money(
                    new_results[0]["price"],
                    new_results[0]["currency"]
                )
            )

        else:

            st.metric(
                "🟢 Sıfır",
                "Yok"
            )


    with c2:

        if used_results:

            st.metric(
                "🟠 İkinci El",
                money(
                    used_results[0]["price"],
                    used_results[0]["currency"]
                )
            )

        else:

            st.metric(
                "🟠 İkinci El",
                "Yok"
            )


    with c3:

        if refurbished_results:

            st.metric(
                "🔵 Yenilenmiş",
                money(
                    refurbished_results[0]["price"],
                    refurbished_results[0]["currency"]
                )
            )

        else:

            st.metric(
                "🔵 Yenilenmiş",
                "Yok"
            )


    with c4:

        st.metric(
            "📦 Toplam",
            len(all_results)
        )


    st.divider()


    # =====================================================
    # TÜM FİYATLAR
    # =====================================================

    st.header(
        "💰 Tüm Fiyatlar"
    )


    st.caption(
        "Sonuçlar en ucuzdan en pahalıya sıralanmıştır."
    )


    for item in all_results:

        show_result(
            item
        )


    # =====================================================
    # KATEGORİLER
    # =====================================================

    st.header(
        "🟢 Sıfır Ürünler"
    )

    if new_results:

        for item in new_results:

            show_result(
                item
            )

    else:

        st.info(
            "Sıfır ürün bulunamadı."
        )


    st.header(
        "🟠 İkinci El"
    )

    if used_results:

        for item in used_results:

            show_result(
                item
            )

    else:

        st.info(
            "Bu aramada ikinci el fiyat sonucu bulunamadı."
        )


    st.header(
        "🔵 Yenilenmiş"
    )

    if refurbished_results:

        for item in refurbished_results:

            show_result(
                item
            )

    else:

        st.info(
            "Bu aramada yenilenmiş fiyat sonucu bulunamadı."
        )


    # =====================================================
    # FİYAT FARKI
    # =====================================================

    try:

        try_prices = [

            float(
                x["price"]
            )

            for x in all_results

            if x["currency"]
            in ["TRY", "TL"]

        ]

        if len(
            try_prices
        ) >= 2:

            lowest = min(
                try_prices
            )

            highest = max(
                try_prices
            )

            difference = (
                highest
                - lowest
            )

            st.divider()

            st.subheader(
                "📈 Fiyat Farkı"
            )

            c1, c2, c3 = st.columns(
                3
            )

            with c1:

                st.metric(
                    "En ucuz",
                    money(
                        lowest,
                        "TRY"
                    )
                )

            with c2:

                st.metric(
                    "En pahalı",
                    money(
                        highest,
                        "TRY"
                    )
                )

            with c3:

                st.metric(
                    "Fark",
                    money(
                        difference,
                        "TRY"
                    )
                )

    except:

        pass
