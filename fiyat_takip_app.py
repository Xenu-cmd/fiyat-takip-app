import streamlit as st
import requests
import re
from urllib.parse import urlparse, quote


# =========================================================
# AYARLAR
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

.title {
    text-align:center;
    font-size:42px;
    font-weight:900;
    color:#111827;
}

.subtitle {
    text-align:center;
    color:#6b7280;
    margin-bottom:30px;
}

.best {
    background:linear-gradient(
        135deg,
        #ecfdf5,
        #f0fdf4
    );
    border:2px solid #22c55e;
    border-radius:20px;
    padding:28px;
    margin:20px 0;
}

.best-title {
    font-size:18px;
    font-weight:800;
    color:#166534;
}

.best-product {
    font-size:25px;
    font-weight:800;
    margin-top:8px;
}

.best-price {
    font-size:42px;
    font-weight:900;
    color:#15803d;
    margin-top:8px;
}

.card {
    background:white;
    border:1px solid #e5e7eb;
    border-radius:16px;
    padding:18px;
    margin:10px 0;
}

.new-card {
    border-left:6px solid #22c55e;
}

.used-card {
    border-left:6px solid #f97316;
}

.refurb-card {
    border-left:6px solid #3b82f6;
}

.product-title {
    font-size:18px;
    font-weight:750;
}

.product-price {
    font-size:25px;
    font-weight:900;
    color:#111827;
    margin-top:6px;
}

.seller {
    color:#2563eb;
    font-weight:700;
}

.condition {
    font-weight:800;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# BAŞLIK
# =========================================================

st.markdown(
    '<div class="title">🔎 Akıllı Fiyat Karşılaştırma</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Sıfır • İkinci El • Yenilenmiş ürünleri karşılaştır'
    '</div>',
    unsafe_allow_html=True
)


# =========================================================
# API KEY
# =========================================================

try:

    API_KEY = st.secrets["SOCIALCRAWL_API_KEY"]

except:

    API_KEY = ""


HEADERS = {
    "x-api-key": API_KEY,
    "Accept": "application/json"
}


# =========================================================
# YARDIMCI FONKSİYONLAR
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


def get_domain(url):

    try:

        return urlparse(
            url
        ).netloc.replace(
            "www.",
            ""
        )

    except:

        return "Bilinmiyor"


def price_from_text(text):

    if not text:
        return None

    text = text.replace(
        "\xa0",
        " "
    )

    patterns = [

        # 1.848,00 TL
        r"(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?)\s*(?:TL|₺)",

        # 1848,00 TL
        r"(\d{3,7}(?:,\d{1,2})?)\s*(?:TL|₺)",

        # TL 1848
        r"(?:TL|₺)\s*(\d{3,7}(?:[.,]\d{1,2})?)"

    ]

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text,
            flags=re.I
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

                    last = value.split(",")[-1]

                    if len(last) == 2:

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

                    last = value.split(".")[-1]

                    if len(last) == 3:

                        value = value.replace(
                            ".",
                            ""
                        )

                number = float(value)

                if 10 <= number <= 10000000:

                    return number

            except:

                pass

    return None


def relevant(product, title, description=""):

    words = [
        x for x in normalize(
            product
        ).split()
        if len(x) >= 2
    ]

    if not words:
        return True

    text = normalize(
        str(title)
        + " "
        + str(description)
    )

    matches = 0

    for word in words:

        if word in text:
            matches += 1

    # Tek kelimelik ürün
    if len(words) == 1:

        return matches >= 1

    # Çok kelimeli ürün
    return (
        matches / len(words)
    ) >= 0.5


# =========================================================
# GOOGLE SHOPPING
# =========================================================

def google_shopping(product):

    url = (
        "https://www.socialcrawl.dev"
        "/v1/google_shopping/product-search"
    )

    params = {

        "query": product,

        "country": "Turkey",

        "language": "tr",

        "depth": 40

    }

    try:

        r = requests.get(
            url,
            params=params,
            headers=HEADERS,
            timeout=60
        )

        if r.status_code != 200:
            return []

        data = r.json()

    except Exception:

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

        if not relevant(
            product,
            title,
            description
        ):
            continue

        price_data = p.get(
            "price",
            {}
        )

        price = price_data.get(
            "current"
        )

        if price is None:
            continue

        try:
            price = float(price)
        except:
            continue

        image_urls = p.get(
            "image_urls",
            []
        )

        image = (
            image_urls[0]
            if image_urls
            else ""
        )

        results.append({

            "title": title,

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
                image,

            "condition":
                "Sıfır",

            "source":
                "Google Shopping"

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

    url = (
        "https://www.socialcrawl.dev"
        "/v1/google/search"
    )

    params = {

        "query": query,

        "region": "TR"

    }

    try:

        r = requests.get(
            url,
            params=params,
            headers=HEADERS,
            timeout=45
        )

        if r.status_code != 200:
            return []

        data = r.json()

    except Exception:

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

        title = item.get(
            "title",
            ""
        )

        description = item.get(
            "snippet",
            item.get(
                "description",
                ""
            )
        )

        url_value = item.get(
            "url",
            ""
        )

        if not relevant(
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

        price = price_from_text(
            combined
        )

        if price is None:
            continue

        results.append({

            "title":
                title,

            "price":
                price,

            "currency":
                "TRY",

            "seller":
                get_domain(
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
# AKAKÇE ARAMA
# =========================================================

def search_akakce(product):

    queries = [

        f'"{product}" site:akakce.com',

        f'"{product}" akakce'

    ]

    results = []

    for query in queries:

        found = google_search(
            query,
            product,
            "Sıfır"
        )

        results.extend(
            found
        )

    return results


# =========================================================
# İKİNCİ EL
# =========================================================

def search_used(product):

    queries = [

        f'"{product}" ikinci el',

        f'"{product}" 2.el',

        f'"{product}" 2 el',

        f'"{product}" kullanılmış',

        f'"{product}" site:sahibinden.com',

        f'"{product}" site:letgo.com'

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

def search_refurbished(product):

    queries = [

        f'"{product}" yenilenmiş',

        f'"{product}" refurbished',

        f'"{product}" renewed',

        f'"{product}" yenilenmiş fiyat',

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
# TEKRARLARI TEMİZLE
# =========================================================

def remove_duplicates(results):

    unique = {}

    for item in results:

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

        price = round(
            float(
                item["price"]
            ),
            2
        )

        key = (
            url,
            title,
            price
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
# SONUÇ GÖSTER
# =========================================================

def result_card(item):

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


    st.markdown(
        f"""
        <div class="card {css}">

            <div class="product-title">
                {icon} {item["title"]}
            </div>

            <div class="product-price">
                {item["price"]:,.2f} TL
            </div>

            <div class="seller">
                🏪 {item["seller"]}
            </div>

            <div class="condition">
                📦 {condition}
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
# ARAMA
# =========================================================

product = st.text_input(
    "🔎 Ürün ara",
    placeholder=
    "Örn: Grundig Club BT Hoparlör"
)


search = st.button(
    "🔍 Ara ve Fiyatları Karşılaştır",
    type="primary",
    use_container_width=True
)


# =========================================================
# ÇALIŞTIR
# =========================================================

if search:

    if not API_KEY:

        st.error(
            "SocialCrawl API anahtarı bulunamadı."
        )

        st.info(
            "Streamlit → Settings → Secrets "
            "bölümüne SOCIALCRAWL_API_KEY ekle."
        )

        st.code(
            'SOCIALCRAWL_API_KEY = "sc_..."'
        )

        st.stop()


    if not product.strip():

        st.warning(
            "Önce ürün adı yaz."
        )

        st.stop()


    product = product.strip()


    # =====================================================
    # ARAMALAR
    # =====================================================

    with st.spinner(
        "🟢 Sıfır ürünler araştırılıyor..."
    ):

        shopping_results = google_shopping(
            product
        )


    with st.spinner(
        "🟢 Akakçe sonuçları araştırılıyor..."
    ):

        akakce_results = search_akakce(
            product
        )


    with st.spinner(
        "🟠 İkinci el sonuçları araştırılıyor..."
    ):

        used_results = search_used(
            product
        )


    with st.spinner(
        "🔵 Yenilenmiş sonuçları araştırılıyor..."
    ):

        refurbished_results = (
            search_refurbished(
                product
            )
        )


    # =====================================================
    # BİRLEŞTİR
    # =====================================================

    new_results = (
        shopping_results
        + akakce_results
    )

    new_results = remove_duplicates(
        new_results
    )

    used_results = remove_duplicates(
        used_results
    )

    refurbished_results = remove_duplicates(
        refurbished_results
    )


    # =====================================================
    # TÜMÜ
    # =====================================================

    all_results = remove_duplicates(

        new_results
        + used_results
        + refurbished_results

    )


    # =====================================================
    # EN UCUZ
    # =====================================================

    if all_results:

        cheapest = min(
            all_results,
            key=lambda x:
                x["price"]
        )


        st.markdown(
            f"""
            <div class="best">

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
                    font-weight:700;
                ">
                    📦 {cheapest["condition"]}
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


    # =====================================================
    # ÖZET
    # =====================================================

    st.divider()

    c1, c2, c3, c4 = st.columns(4)


    with c1:

        if new_results:

            st.metric(
                "🟢 Sıfır",
                f"{new_results[0]['price']:,.2f} TL"
            )

        else:

            st.metric(
                "🟢 Sıfır",
                "Bulunamadı"
            )


    with c2:

        if used_results:

            st.metric(
                "🟠 İkinci El",
                f"{used_results[0]['price']:,.2f} TL"
            )

        else:

            st.metric(
                "🟠 İkinci El",
                "Bulunamadı"
            )


    with c3:

        if refurbished_results:

            st.metric(
                "🔵 Yenilenmiş",
                f"{refurbished_results[0]['price']:,.2f} TL"
            )

        else:

            st.metric(
                "🔵 Yenilenmiş",
                "Bulunamadı"
            )


    with c4:

        st.metric(
            "📦 Toplam Sonuç",
            len(all_results)
        )


    # =====================================================
    # TÜM SONUÇLAR
    # =====================================================

    st.divider()

    st.header(
        "💰 Tüm Fiyatlar"
    )

    if all_results:

        for item in all_results:

            result_card(
                item
            )

    else:

        st.warning(
            "Fiyat bulunamadı."
        )


    # =====================================================
    # SIFIR
    # =====================================================

    st.divider()

    st.header(
        "🟢 Sıfır Ürünler"
    )

    if new_results:

        for item in new_results:

            result_card(
                item
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

        for item in used_results:

            result_card(
                item
            )

    else:

        st.info(
            "Bu ürün için fiyat içeren ikinci el sonuç bulunamadı."
        )


    # =====================================================
    # YENİLENMİŞ
    # =====================================================

    st.divider()

    st.header(
        "🔵 Yenilenmiş"
    )

    if refurbished_results:

        for item in refurbished_results:

            result_card(
                item
            )

    else:

        st.info(
            "Bu ürün için fiyat içeren yenilenmiş sonuç bulunamadı."
        )
