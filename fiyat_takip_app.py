import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote, urljoin
import re


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
    text-align:center;
    font-size:38px;
    font-weight:800;
    color:#111827;
}

.subtitle {
    text-align:center;
    color:#6b7280;
    margin-bottom:25px;
}

.card {
    padding:18px;
    border-radius:15px;
    margin-bottom:12px;
    border:1px solid #e5e7eb;
    background:white;
    box-shadow:0 3px 10px rgba(0,0,0,.05);
}

.new {
    border-left:6px solid #22c55e;
}

.used {
    border-left:6px solid #f97316;
}

.refurbished {
    border-left:6px solid #3b82f6;
}

.price {
    font-size:27px;
    font-weight:800;
    color:#15803d;
}

.store {
    color:#2563eb;
    font-weight:700;
}

.best {
    padding:22px;
    border-radius:16px;
    background:#fefce8;
    border:2px solid #facc15;
    margin-bottom:25px;
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
    'Sıfır • İkinci El • Yenilenmiş ürünleri karşılaştır'
    '</div>',
    unsafe_allow_html=True
)


# =========================================================
# ARAMA
# =========================================================

product = st.text_input(
    "Ürün adı",
    placeholder="Örn: Grundig Club"
)

search = st.button(
    "🔍 Ürünü Ara",
    type="primary",
    use_container_width=True
)


# =========================================================
# HTTP
# =========================================================

HEADERS = {
    "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
}


# =========================================================
# FİYAT DÖNÜŞTÜR
# =========================================================

def price_to_number(value):

    if not value:
        return None

    value = value.strip()

    value = value.replace("TL", "")
    value = value.replace("₺", "")
    value = value.replace(" ", "")

    try:

        # 1.799,90
        if "." in value and "," in value:

            value = value.replace(".", "")
            value = value.replace(",", ".")

        # 1.799
        elif "." in value:

            parts = value.split(".")

            if len(parts[-1]) == 3:
                value = value.replace(".", "")

        # 1799,90
        elif "," in value:

            value = value.replace(",", ".")

        number = float(value)

        if 1 <= number <= 10000000:
            return number

    except:
        pass

    return None


# =========================================================
# METİNDEN FİYATLARI BUL
# =========================================================

def extract_prices(text):

    if not text:
        return []

    patterns = [

        r'(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?)\s*(?:TL|₺)',

        r'(\d{3,7}(?:,\d{1,2})?)\s*(?:TL|₺)',

        r'(?:TL|₺)\s*(\d{3,7}(?:[.,]\d{1,2})?)'

    ]

    prices = []

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        for value in matches:

            number = price_to_number(value)

            if number is not None:
                prices.append(number)

    return sorted(set(prices))


# =========================================================
# ÜRÜN UYGUN MU?
# =========================================================

def product_match(search_name, title):

    search_words = [
        x.lower()
        for x in search_name.split()
        if len(x) >= 2
    ]

    title = title.lower()

    if not search_words:
        return True

    matched = 0

    for word in search_words:

        if word in title:
            matched += 1

    # Aranan kelimelerin en az yarısı başlıkta olsun
    return matched >= max(
        1,
        len(search_words) // 2
    )


# =========================================================
# AKAKÇE
# =========================================================

def search_akakce(product):

    results = []

    search_url = (
        "https://www.akakce.com/arama/"
        "?q=" + quote(product)
    )

    try:

        response = requests.get(
            search_url,
            headers=HEADERS,
            timeout=20
        )

        response.raise_for_status()

    except Exception:
        return results


    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )


    # Akakçe arama sayfasındaki bağlantıları bul
    links = soup.find_all("a")


    seen = set()


    for link in links:

        title = link.get_text(
            " ",
            strip=True
        )

        href = link.get(
            "href",
            ""
        )


        if not title or not href:
            continue


        if not product_match(
            product,
            title
        ):
            continue


        if href.startswith("/"):

            href = urljoin(
                "https://www.akakce.com",
                href
            )


        if "akakce.com" not in href:
            continue


        if href in seen:
            continue


        seen.add(href)


        # Ürün sayfasını aç
        try:

            product_response = requests.get(
                href,
                headers=HEADERS,
                timeout=15
            )

            product_soup = BeautifulSoup(
                product_response.text,
                "html.parser"
            )

            page_text = product_soup.get_text(
                " ",
                strip=True
            )

            prices = extract_prices(
                page_text
            )

        except:

            prices = []


        if not prices:
            continue


        # Aşırı fazla rakam varsa ilk birkaç makul fiyatı al
        prices = [
            p for p in prices
            if p >= 50
        ]


        if not prices:
            continue


        results.append({

            "title": title,

            "price": min(prices),

            "url": href,

            "store": "Akakçe",

            "condition": "Sıfır"

        })


        if len(results) >= 10:
            break


    return results


# =========================================================
# EPEY
# =========================================================

def search_epey(product):

    results = []

    search_url = (
        "https://www.google.com/search?q="
        + quote(
            product +
            " site:epey.com"
        )
    )

    try:

        response = requests.get(
            search_url,
            headers=HEADERS,
            timeout=20
        )

        response.raise_for_status()

    except:

        return results


    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )


    for link in soup.find_all("a"):

        href = link.get(
            "href",
            ""
        )

        text = link.get_text(
            " ",
            strip=True
        )


        if "epey.com" not in href:
            continue


        if not product_match(
            product,
            text
        ):
            continue


        # Epey sayfasını aç
        try:

            page = requests.get(
                href,
                headers=HEADERS,
                timeout=15
            )

            page_soup = BeautifulSoup(
                page.text,
                "html.parser"
            )

            page_text = page_soup.get_text(
                " ",
                strip=True
            )

            prices = extract_prices(
                page_text
            )

        except:

            continue


        if not prices:
            continue


        results.append({

            "title": text[:150],

            "price": min(prices),

            "url": href,

            "store": "Epey",

            "condition": "Sıfır"

        })


        if len(results) >= 10:
            break


    return results


# =========================================================
# GENEL WEB ARAMASI
# =========================================================

def search_web(product, condition):

    results = []


    if condition == "İkinci El":

        queries = [
            f'"{product}" ikinci el',
            f'"{product}" 2.el',
            f'"{product}" site:sahibinden.com',
            f'"{product}" site:letgo.com'
        ]

    elif condition == "Yenilenmiş":

        queries = [
            f'"{product}" yenilenmiş',
            f'"{product}" refurbished'
        ]

    else:

        queries = [
            f'"{product}" fiyat',
            f'"{product}" satın al'
        ]


    for query in queries:

        url = (
            "https://html.duckduckgo.com/html/"
        )


        try:

            response = requests.get(
                url,
                params={"q": query},
                headers=HEADERS,
                timeout=15
            )

            response.raise_for_status()

        except:

            continue


        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )


        for item in soup.select(
            ".result"
        ):

            link = item.select_one(
                ".result__a"
            )

            snippet = item.select_one(
                ".result__snippet"
            )


            if not link:
                continue


            title = link.get_text(
                " ",
                strip=True
            )

            href = link.get(
                "href",
                ""
            )


            description = ""

            if snippet:

                description = snippet.get_text(
                    " ",
                    strip=True
                )


            combined = (
                title + " " +
                description
            )


            if not product_match(
                product,
                combined
            ):
                continue


            prices = extract_prices(
                combined
            )


            if not prices:
                continue


            results.append({

                "title": title,

                "price": min(prices),

                "url": href,

                "store": (
                    href.split("//")[-1]
                    .split("/")[0]
                    .replace("www.", "")
                ),

                "condition": condition

            })


    return results


# =========================================================
# TEKRARLARI SİL
# =========================================================

def unique_results(results):

    unique = {}

    for item in results:

        key = (
            item["url"],
            item["price"]
        )

        if key not in unique:

            unique[key] = item


    results = list(
        unique.values()
    )


    results.sort(
        key=lambda x: x["price"]
    )


    return results


# =========================================================
# SONUÇ KARTI
# =========================================================

def show_results(
    title,
    emoji,
    results,
    css
):

    st.subheader(
        f"{emoji} {title}"
    )


    if not results:

        st.info(
            "Bu kategoride sonuç bulunamadı."
        )

        return


    for index, item in enumerate(
        results[:15],
        1
    ):

        st.markdown(
            f"""
            <div class="card {css}">

                <div style="
                    font-size:18px;
                    font-weight:700;
                ">
                    {index}. {item["title"]}
                </div>

                <div class="store">
                    🏪 {item["store"]}
                </div>

                <div class="price">
                    {item["price"]:,.2f} TL
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


        st.link_button(
            "🔗 Ürüne Git",
            item["url"]
        )


# =========================================================
# ÇALIŞTIR
# =========================================================

if search:

    if not product.strip():

        st.warning(
            "Lütfen bir ürün adı yaz."
        )

        st.stop()


    product = product.strip()


    with st.spinner(
        f'"{product}" araştırılıyor...'
    ):

        # -----------------------------------------
        # SIFIR
        # -----------------------------------------

        new_results = []

        new_results.extend(
            search_akakce(product)
        )

        new_results.extend(
            search_epey(product)
        )

        new_results.extend(
            search_web(
                product,
                "Sıfır"
            )
        )


        # -----------------------------------------
        # İKİNCİ EL
        # -----------------------------------------

        used_results = search_web(
            product,
            "İkinci El"
        )


        # -----------------------------------------
        # YENİLENMİŞ
        # -----------------------------------------

        refurbished_results = search_web(
            product,
            "Yenilenmiş"
        )


    new_results = unique_results(
        new_results
    )

    used_results = unique_results(
        used_results
    )

    refurbished_results = unique_results(
        refurbished_results
    )


    # =====================================================
    # EN UCUZ
    # =====================================================

    all_results = (
        new_results +
        used_results +
        refurbished_results
    )


    if all_results:

        cheapest = min(
            all_results,
            key=lambda x: x["price"]
        )


        st.markdown(
            f"""
            <div class="best">

                <h2>💰 Bulunan En Ucuz</h2>

                <div style="
                    font-size:21px;
                    font-weight:700;
                ">
                    {cheapest["title"]}
                </div>

                <div style="
                    font-size:36px;
                    font-weight:900;
                    color:#15803d;
                ">
                    {cheapest["price"]:,.2f} TL
                </div>

                <div>
                    🏪 {cheapest["store"]}
                    <br>
                    📦 {cheapest["condition"]}
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

        st.metric(
            "🟢 Sıfır",
            (
                f"{new_results[0]['price']:,.2f} TL"
                if new_results
                else "-"
            )
        )


    with col2:

        st.metric(
            "🟠 İkinci El",
            (
                f"{used_results[0]['price']:,.2f} TL"
                if used_results
                else "-"
            )
        )


    with col3:

        st.metric(
            "🔵 Yenilenmiş",
            (
                f"{refurbished_results[0]['price']:,.2f} TL"
                if refurbished_results
                else "-"
            )
        )


    st.divider()


    # =====================================================
    # SONUÇLAR
    # =====================================================

    show_results(
        "Sıfır Ürünler",
        "🟢",
        new_results,
        "new"
    )


    st.divider()


    show_results(
        "İkinci El",
        "🟠",
        used_results,
        "used"
    )


    st.divider()


    show_results(
        "Yenilenmiş",
        "🔵",
        refurbished_results,
        "refurbished"
    )


    if not all_results:

        st.error(
            f'"{product}" için sonuç bulunamadı.'
        )
