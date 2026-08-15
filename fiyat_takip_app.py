import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import unquote
import re
import time


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
    font-size: 38px;
    font-weight: 800;
    color: #111827;
    margin-bottom: 5px;
}

.subtitle {
    text-align: center;
    color: #6b7280;
    margin-bottom: 30px;
}

.price-card {
    padding: 20px;
    border-radius: 16px;
    margin-bottom: 12px;
    background: white;
    border: 1px solid #e5e7eb;
    box-shadow: 0 3px 12px rgba(0,0,0,0.05);
}

.price {
    font-size: 25px;
    font-weight: 800;
    color: #111827;
}

.store {
    color: #2563eb;
    font-weight: 700;
}

.small {
    color: #6b7280;
    font-size: 14px;
}

.new-box {
    background: #ecfdf5;
    border: 1px solid #bbf7d0;
}

.used-box {
    background: #fff7ed;
    border: 1px solid #fed7aa;
}

.refurbished-box {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
}

.best-box {
    background: #fefce8;
    border: 2px solid #facc15;
    padding: 20px;
    border-radius: 16px;
    margin-bottom: 25px;
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
    '<div class="subtitle">Sıfır, ikinci el ve yenilenmiş ürünleri araştır</div>',
    unsafe_allow_html=True
)


# =========================================================
# ARAMA KUTUSU
# =========================================================

product = st.text_input(
    "Ürün adı",
    placeholder="Örn: Grundig Club, iPhone 17 Pro, Samsung S25..."
)


search_button = st.button(
    "🔍 İnternette Ara",
    type="primary",
    use_container_width=True
)


# =========================================================
# HTTP AYARLARI
# =========================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    )
}


# =========================================================
# FİYAT BULMA
# =========================================================

def extract_prices(text):

    if not text:
        return []

    text = text.replace("\xa0", " ")

    prices = []

    patterns = [
        r'(\d{1,3}(?:[.\s]\d{3})+(?:,\d{1,2})?)\s*(?:TL|₺)',
        r'(\d{3,6}(?:,\d{1,2})?)\s*(?:TL|₺)',
        r'(?:TL|₺)\s*(\d{3,6}(?:[.,]\d{1,2})?)'
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
                    value = value.replace(".", "")
                    value = value.replace(",", ".")

                elif "," in value:
                    parts = value.split(",")

                    if len(parts[-1]) == 2:
                        value = value.replace(",", ".")
                    else:
                        value = value.replace(",", "")

                elif "." in value:
                    parts = value.split(".")

                    if len(parts[-1]) == 3:
                        value = value.replace(".", "")

                number = float(value)

                # Çok geniş aralık bırakıyoruz
                if 1 <= number <= 10000000:
                    prices.append(number)

            except:
                continue

    return sorted(list(set(prices)))



# =========================================================
# DOMAIN BUL
# =========================================================

def get_domain(url):

    try:

        domain = url.split("//")[-1].split("/")[0]

        return domain.replace("www.", "")

    except:

        return ""


# =========================================================
# ÜRÜN RELEVANSI
# =========================================================

def relevance_score(product_name, title, description):

    words = [
        w.lower()
        for w in product_name.split()
        if len(w) >= 2
    ]

    text = (
        (title or "") + " " +
        (description or "")
    ).lower()

    score = 0

    for word in words:

        if word in text:
            score += 1

    return score


# =========================================================
# DUCKDUCKGO ARAMASI
# =========================================================

def search_web(query, category):

    url = "https://html.duckduckgo.com/html/"

    try:

        response = requests.get(
            url,
            params={"q": query},
            headers=HEADERS,
            timeout=15
        )

        response.raise_for_status()

    except Exception:

        return []


    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    results = []


    for item in soup.select(".result"):

        title_element = item.select_one(
            ".result__title"
        )

        link_element = item.select_one(
            ".result__a"
        )

        snippet_element = item.select_one(
            ".result__snippet"
        )


        if not link_element:

            continue


        title = (
            link_element.get_text(
                " ",
                strip=True
            )
        )


        href = link_element.get(
            "href",
            ""
        )


        snippet = ""

        if snippet_element:

            snippet = snippet_element.get_text(
                " ",
                strip=True
            )


        # DuckDuckGo bazen yönlendirme URL'si verir
        if "uddg=" in href:

            try:

                href = unquote(
                    href.split("uddg=")[1]
                    .split("&")[0]
                )

            except:

                pass


        combined_text = (
            title + " " + snippet
        )


        prices = extract_prices(
            combined_text
        )


        score = relevance_score(
            product,
            title,
            snippet
        )


        # Arama kategorisine göre ek puan
        category_text = combined_text.lower()


        if category == "new":

            keywords = [
                "sıfır",
                "yeni",
                "stok",
                "mağaza",
                "satın al"
            ]

        elif category == "used":

            keywords = [
                "ikinci el",
                "2.el",
                "2 el",
                "kullanılmış",
                "sahibinden",
                "letgo",
                "ilan"
            ]

        else:

            keywords = [
                "yenilenmiş",
                "refurbished",
                "renewed"
            ]


        for keyword in keywords:

            if keyword in category_text:

                score += 2


        # Çok alakasız sonuçları ele
        if score < 1:

            continue


        results.append({

            "title": title,
            "url": href,
            "description": snippet,
            "prices": prices,
            "category": category,
            "score": score,
            "domain": get_domain(href)

        })


    return results


# =========================================================
# ARAMA PLANLARI
# =========================================================

def build_queries(product):

    return {

        "new": [

            f'"{product}" fiyat',
            f'"{product}" satın al',
            f'"{product}" site:akakce.com',
            f'"{product}" site:hepsiburada.com',
            f'"{product}" site:trendyol.com',
            f'"{product}" site:amazon.com.tr'

        ],

        "used": [

            f'"{product}" ikinci el',
            f'"{product}" 2.el',
            f'"{product}" site:sahibinden.com',
            f'"{product}" site:letgo.com'

        ],

        "refurbished": [

            f'"{product}" yenilenmiş',
            f'"{product}" refurbished',
            f'"{product}" yenilenmiş fiyat'

        ]

    }


# =========================================================
# SONUÇLARI TEMİZLE
# =========================================================

def clean_results(results):

    unique = {}

    for item in results:

        key = item["url"]

        if not key:
            continue


        if key not in unique:

            unique[key] = item

        else:

            # Daha yüksek puanlı sonucu tut
            if item["score"] > unique[key]["score"]:

                unique[key] = item


    final = list(unique.values())


    # Fiyatı olanları önce getir
    final.sort(
        key=lambda x: (
            0 if x["prices"] else 1,
            min(x["prices"])
            if x["prices"]
            else 999999999
        )
    )


    return final


# =========================================================
# SONUÇLARI ARA
# =========================================================

def search_product(product):

    queries = build_queries(
        product
    )


    all_results = {
        "new": [],
        "used": [],
        "refurbished": []
    }


    progress = st.progress(
        0
    )


    total_queries = sum(
        len(v)
        for v in queries.values()
    )

    completed = 0


    for category, category_queries in queries.items():

        for query in category_queries:

            results = search_web(
                query,
                category
            )


            all_results[category].extend(
                results
            )


            completed += 1

            progress.progress(
                min(
                    completed / total_queries,
                    1.0
                )
            )


            # Arama motoruna çok hızlı yüklenmemek için
            time.sleep(0.4)


    progress.empty()


    for category in all_results:

        all_results[category] = clean_results(
            all_results[category]
        )


    return all_results


# =========================================================
# FİYATLI SONUÇLARI AL
# =========================================================

def priced_results(results):

    output = []

    for result in results:

        if not result["prices"]:

            continue


        # Sonuçtaki en düşük fiyatı kullan
        result["price"] = min(
            result["prices"]
        )


        output.append(
            result
        )


    output.sort(
        key=lambda x: x["price"]
    )


    return output


# =========================================================
# SONUÇ GÖSTER
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
            "Bu kategoride fiyat bulunamadı."
        )

        return []


    for index, item in enumerate(
        results[:15],
        start=1
    ):

        price = item["price"]


        st.markdown(
            f"""
            <div class="price-card {css_class}">

                <div style="font-size:18px;font-weight:700;">
                    {index}. {item["title"]}
                </div>

                <div class="store">
                    🏪 {item["domain"]}
                </div>

                <div class="price">
                    {price:,.2f} TL
                </div>

                <div class="small">
                    {item["description"][:350]}
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


        st.link_button(
            "🔗 Ürüne Git",
            item["url"]
        )


        st.write("")


    return results


# =========================================================
# ÇALIŞTIR
# =========================================================

if search_button:

    if not product.strip():

        st.warning(
            "Lütfen önce bir ürün adı yaz."
        )

        st.stop()


    product = product.strip()


    st.info(
        f"🔎 **{product}** için internet araştırması yapılıyor..."
    )


    with st.spinner(
        "Sıfır, ikinci el ve yenilenmiş ürünler aranıyor..."
    ):

        results = search_product(
            product
        )


    new_results = priced_results(
        results["new"]
    )

    used_results = priced_results(
        results["used"]
    )

    refurbished_results = priced_results(
        results["refurbished"]
    )


    # =====================================================
    # TÜM SONUÇLAR
    # =====================================================

    all_priced = (
        new_results +
        used_results +
        refurbished_results
    )


    # =====================================================
    # EN UCUZ
    # =====================================================

    if all_priced:

        cheapest = min(
            all_priced,
            key=lambda x: x["price"]
        )


        st.markdown(
            f"""
            <div class="best-box">

                <h2>💰 Bulunan En Ucuz Fiyat</h2>

                <div style="font-size:22px;font-weight:700;">
                    {cheapest["title"]}
                </div>

                <div style="
                    font-size:34px;
                    font-weight:900;
                    color:#15803d;
                ">
                    {cheapest["price"]:,.2f} TL
                </div>

                <div>
                    🏪 {cheapest["domain"]}
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
                else "Bulunamadı"
            )
        )


    with col2:

        st.metric(
            "🟠 İkinci El",
            (
                f"{used_results[0]['price']:,.2f} TL"
                if used_results
                else "Bulunamadı"
            )
        )


    with col3:

        st.metric(
            "🔵 Yenilenmiş",
            (
                f"{refurbished_results[0]['price']:,.2f} TL"
                if refurbished_results
                else "Bulunamadı"
            )
        )


    st.divider()


    # =====================================================
    # KATEGORİLER
    # =====================================================

    show_category(
        "Sıfır Ürünler",
        "🟢",
        new_results,
        "new-box"
    )


    st.divider()


    show_category(
        "İkinci El",
        "🟠",
        used_results,
        "used-box"
    )


    st.divider()


    show_category(
        "Yenilenmiş",
        "🔵",
        refurbished_results,
        "refurbished-box"
    )


    # =====================================================
    # SONUÇ YOK
    # =====================================================

    if not all_priced:

        st.error(
            f'"{product}" için fiyat içeren sonuç bulunamadı.'
        )

        st.write(
            "Ürün adını model numarasıyla birlikte "
            "aramayı deneyebilirsin."
        )
