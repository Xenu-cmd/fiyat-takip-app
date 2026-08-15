import streamlit as st
import requests
import re
import html
import time
from urllib.parse import urlparse


# ============================================================
# SAYFA AYARLARI
# ============================================================

st.set_page_config(
    page_title="Akıllı Fiyat Karşılaştırma",
    page_icon="🔎",
    layout="wide"
)


# ============================================================
# TASARIM
# ============================================================

st.markdown("""
<style>

.main-title {
    text-align: center;
    font-size: 40px;
    font-weight: 900;
    color: #111827;
    margin-top: 10px;
}

.subtitle {
    text-align: center;
    color: #6b7280;
    font-size: 16px;
    margin-bottom: 28px;
}

.best-card {
    background: linear-gradient(
        135deg,
        #ecfdf5,
        #f0fdf4
    );

    border: 2px solid #22c55e;
    border-radius: 20px;
    padding: 26px;
    margin: 20px 0;
}

.best-title {
    font-size: 19px;
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
    font-size: 44px;
    font-weight: 900;
    color: #15803d;
    margin-top: 8px;
}

.best-store {
    font-size: 17px;
    margin-top: 8px;
    color: #374151;
}

.best-condition {
    margin-top: 6px;
    font-weight: 800;
    color: #374151;
}

.offer {
    background: white;
    border-radius: 15px;
    padding: 17px;
    margin-bottom: 8px;
    border: 1px solid #e5e7eb;
    box-shadow: 0 3px 12px rgba(0,0,0,.04);
}

.offer-new {
    border-left: 6px solid #22c55e;
}

.offer-used {
    border-left: 6px solid #f97316;
}

.offer-refurb {
    border-left: 6px solid #3b82f6;
}

.offer-title {
    font-size: 18px;
    font-weight: 800;
    color: #111827;
}

.offer-price {
    font-size: 28px;
    font-weight: 900;
    color: #111827;
    margin-top: 5px;
}

.offer-store {
    color: #2563eb;
    font-weight: 800;
    margin-top: 5px;
}

.offer-source {
    color: #6b7280;
    font-size: 13px;
    margin-top: 5px;
}

.section-new {
    color: #15803d;
}

.section-used {
    color: #c2410c;
}

.section-refurb {
    color: #1d4ed8;
}

.info-box {
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 14px;
    color: #4b5563;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# API KEY
# ============================================================

try:
    API_KEY = st.secrets["SOCIALCRAWL_API_KEY"]
except Exception:
    API_KEY = ""


API_HEADERS = {
    "x-api-key": API_KEY,
    "Accept": "application/json"
}


# ============================================================
# BAŞLIK
# ============================================================

st.markdown(
    '<div class="main-title">🔎 Akıllı Fiyat Karşılaştırma</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Sıfır, ikinci el ve yenilenmiş ürünleri farklı kaynaklarda karşılaştır'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# ARAMA KUTUSU
# ============================================================

product = st.text_input(
    "Ürün adı",
    placeholder="Örn: Grundig Club BT Hoparlör"
)

search_button = st.button(
    "🔍 Fiyatları Bul",
    type="primary",
    use_container_width=True
)


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def normalize(text):
    """
    Türkçe karakterleri basitleştirir.
    Karşılaştırmayı kolaylaştırır.
    """

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


def product_words(product):
    """
    Ürün adını kelimelere böler.
    """

    ignored = {
        "ve",
        "ile",
        "icin",
        "bir",
        "the",
        "for"
    }

    return [
        word
        for word in normalize(product).split()
        if len(word) >= 2
        and word not in ignored
    ]


def get_domain(url):
    """
    URL'den domain çıkarır.
    """

    if not url:
        return ""

    try:
        parsed = urlparse(url)

        domain = parsed.netloc.lower()

        if domain.startswith("www."):
            domain = domain[4:]

        return domain

    except Exception:
        return ""


def source_name(url):
    """
    Domain'i kullanıcı dostu isim yapar.
    """

    domain = get_domain(url)

    names = {
        "akakce.com": "Akakçe",
        "cimri.com": "Cimri",
        "hepsiburada.com": "Hepsiburada",
        "trendyol.com": "Trendyol",
        "n11.com": "N11",
        "amazon.com.tr": "Amazon",
        "dolap.com": "Dolap",
        "sahibinden.com": "Sahibinden",
        "letgo.com": "Letgo",
        "grundig.com.tr": "Grundig"
    }

    return names.get(
        domain,
        domain
    )


# ============================================================
# FİYAT ÇIKARMA
# ============================================================

def extract_prices(text):

    if not text:
        return []

    text = str(text)

    text = text.replace(
        "\xa0",
        " "
    )

    patterns = [

        # 1.999 TL
        r'(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?)\s*(?:TL|₺)',

        # 1,999 TL / 1999 TL
        r'(\d{1,6}(?:,\d{1,2})?)\s*(?:TL|₺)',

        # TL 1.999
        r'(?:TL|₺)\s*(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?)',

        # TL 1999
        r'(?:TL|₺)\s*(\d{1,6}(?:,\d{1,2})?)'
    ]

    prices = []

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        for raw in matches:

            try:

                value = str(raw).strip()

                # 1.999,90
                if "." in value and "," in value:

                    value = (
                        value
                        .replace(".", "")
                        .replace(",", ".")
                    )

                # 1,999
                elif "," in value:

                    last = value.split(",")[-1]

                    if len(last) <= 2:

                        value = value.replace(
                            ",",
                            "."
                        )

                    else:

                        value = value.replace(
                            ",",
                            ""
                        )

                # 1.999
                elif "." in value:

                    parts = value.split(".")

                    if len(parts[-1]) == 3:

                        value = value.replace(
                            ".",
                            ""
                        )

                number = float(value)

                # Ürün fiyatı için mantıklı sınır
                if 1 <= number <= 10_000_000:

                    prices.append(number)

            except Exception:
                continue

    return sorted(
        set(prices)
    )


# ============================================================
# ÜRÜN RELEVANSI
# ============================================================

def relevance_score(
    product,
    text
):

    words = product_words(
        product
    )

    text_normalized = normalize(
        text
    )

    if not words:
        return 0

    score = 0

    for word in words:

        if word in text_normalized:
            score += 1

    return score


def is_relevant(
    product,
    title,
    snippet=""
):

    combined = (
        str(title)
        + " "
        + str(snippet)
    )

    words = product_words(
        product
    )

    score = relevance_score(
        product,
        combined
    )

    if len(words) >= 3:

        return score >= max(
            2,
            len(words) - 1
        )

    if len(words) == 2:

        return score >= 2

    return score >= 1


# ============================================================
# SOCIALCRAWL GENEL GET
# ============================================================

def api_get(
    endpoint,
    params,
    timeout=90
):

    if not API_KEY:
        return None

    url = (
        "https://www.socialcrawl.dev"
        + endpoint
    )

    try:

        response = requests.get(
            url,
            params=params,
            headers=API_HEADERS,
            timeout=timeout
        )

        if response.status_code == 504:

            return None

        if response.status_code != 200:

            return None

        data = response.json()

        if not data.get("success"):

            return None

        return data

    except Exception:

        return None


# ============================================================
# GOOGLE SEARCH API
# ============================================================

def google_search(
    query,
    page=1
):

    data = api_get(
        "/v1/google/search",
        {
            "query": query,
            "region": "TR",
            "page": page
        }
    )

    if not data:
        return []

    return (
        data
        .get("data", {})
        .get("items", [])
    )


# ============================================================
# GOOGLE SHOPPING API
# ============================================================

def google_shopping(
    query
):

    data = api_get(
        "/v1/google_shopping/product-search",
        {
            "query": query,
            "country": "Turkey",
            "language": "tr",
            "depth": 40
        },
        timeout=120
    )

    if not data:
        return []

    return (
        data
        .get("data", {})
        .get("items", [])
    )


# ============================================================
# GOOGLE SHOPPING SONUÇLARINI DÖNÜŞTÜR
# ============================================================

def parse_shopping(
    items,
    product,
    condition="Sıfır"
):

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

        if not is_relevant(
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

        currency = str(
            price_data.get(
                "currency",
                ""
            )
        ).upper()

        # Türkiye dışındaki sonuçları
        # yanlış TL gibi göstermeyelim.
        if currency not in {
            "TRY",
            "TL"
        }:
            continue

        try:
            price = float(price)
        except Exception:
            continue

        seller = product_data.get(
            "seller",
            ""
        )

        url = product_data.get(
            "url",
            ""
        )

        results.append({

            "title": title,

            "price": price,

            "seller": seller or "Mağaza",

            "url": url,

            "condition": condition,

            "source": "Google Shopping"

        })

    return results


# ============================================================
# GOOGLE SEARCH SONUÇLARINI DÖNÜŞTÜR
# ============================================================

def parse_google_results(
    items,
    product,
    condition
):

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

        snippet = item.get(
            "snippet",
            ""
        )

        if not is_relevant(
            product,
            title,
            snippet
        ):
            continue

        combined = (
            title
            + " "
            + snippet
        )

        prices = extract_prices(
            combined
        )

        if not prices:
            continue

        price = min(
            prices
        )

        store = source_name(
            url
        )

        if not store:

            store = get_domain(
                url
            )

        results.append({

            "title": title,

            "price": price,

            "seller": store,

            "url": url,

            "condition": condition,

            "source": "Google Search"

        })

    return results


# ============================================================
# KAYNAK BAZLI GOOGLE ARAMASI
# ============================================================

def search_google_source(
    product,
    domain,
    condition,
    extra=""
):

    query = (
        f'"{product}" '
        f'site:{domain} '
        f'{extra}'
    ).strip()

    items = google_search(
        query
    )

    return parse_google_results(
        items,
        product,
        condition
    )


# ============================================================
# SIFIR
# ============================================================

def search_new(
    product
):

    results = []

    # --------------------------------------------------------
    # Google Shopping
    # --------------------------------------------------------

    shopping_queries = [
        product,
        f"{product} fiyat"
    ]

    for query in shopping_queries:

        items = google_shopping(
            query
        )

        results.extend(
            parse_shopping(
                items,
                product,
                "Sıfır"
            )
        )

        time.sleep(0.5)

    # --------------------------------------------------------
    # Google Search kaynakları
    # --------------------------------------------------------

    domains = [
        "akakce.com",
        "cimri.com",
        "hepsiburada.com",
        "trendyol.com",
        "n11.com",
        "amazon.com.tr",
        "grundig.com.tr"
    ]

    for domain in domains:

        found = search_google_source(
            product,
            domain,
            "Sıfır"
        )

        results.extend(
            found
        )

        time.sleep(0.2)

    return clean_results(
        results
    )


# ============================================================
# İKİNCİ EL
# ============================================================

def search_used(
    product
):

    results = []

    domains = [
        "dolap.com",
        "sahibinden.com",
        "letgo.com"
    ]

    search_variants = [
        "",
        "ikinci el",
        "2.el"
    ]

    for domain in domains:

        for variant in search_variants:

            found = search_google_source(
                product,
                domain,
                "İkinci El",
                variant
            )

            results.extend(
                found
            )

            time.sleep(0.2)

    # Google Search'te genel ikinci el araması
    general_queries = [
        f'"{product}" ikinci el',
        f'"{product}" 2.el'
    ]

    for query in general_queries:

        items = google_search(
            query
        )

        parsed = parse_google_results(
            items,
            product,
            "İkinci El"
        )

        # Genel aramadan gelen sonucu
        # yalnızca ikinci el kaynaklarından kabul et.
        for item in parsed:

            domain = get_domain(
                item["url"]
            )

            if domain in {
                "dolap.com",
                "sahibinden.com",
                "letgo.com"
            }:

                results.append(
                    item
                )

    return clean_results(
        results
    )


# ============================================================
# YENİLENMİŞ
# ============================================================

def search_refurbished(
    product
):

    results = []

    domains = [
        "hepsiburada.com",
        "trendyol.com",
        "n11.com",
        "amazon.com.tr"
    ]

    variants = [
        "yenilenmiş",
        "refurbished",
        "renewed"
    ]

    for domain in domains:

        for variant in variants:

            found = search_google_source(
                product,
                domain,
                "Yenilenmiş",
                variant
            )

            results.extend(
                found
            )

            time.sleep(0.2)

    # Genel Google Search
    for variant in variants:

        query = (
            f'"{product}" {variant}'
        )

        items = google_search(
            query
        )

        parsed = parse_google_results(
            items,
            product,
            "Yenilenmiş"
        )

        for item in parsed:

            text = normalize(
                item["title"]
                + " "
                + item["seller"]
            )

            # Başlıkta yenilenmiş ibaresi
            # yoksa yanlışlıkla sıfır ürünü
            # yenilenmiş göstermeyelim.
            if any(
                word in text
                for word in [
                    "yenilenmis",
                    "refurbished",
                    "renewed"
                ]
            ):

                results.append(
                    item
                )

    return clean_results(
        results
    )


# ============================================================
# SONUÇ TEMİZLEME
# ============================================================

def clean_results(
    results
):

    unique = {}

    for item in results:

        try:

            price = float(
                item["price"]
            )

        except Exception:

            continue

        if price <= 0:
            continue

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

        seller = normalize(
            item.get(
                "seller",
                ""
            )
        )

        condition = item.get(
            "condition",
            ""
        )

        # Öncelikle URL üzerinden tekrarları engelle
        if url:

            key = (
                url.split("?")[0],
                condition
            )

        else:

            key = (
                title,
                seller,
                round(price, 2),
                condition
            )

        if key not in unique:

            item["price"] = price

            unique[key] = item

        else:

            # Aynı URL farklı kaynakta çıktıysa
            # daha temiz olan sonucu tercih et.
            old = unique[key]

            if (
                old.get("source") != "Google Search"
                and item.get("source") == "Google Search"
            ):

                unique[key] = item

    cleaned = list(
        unique.values()
    )

    cleaned.sort(
        key=lambda x: x["price"]
    )

    return cleaned


# ============================================================
# KAYNAK ÖZETİ
# ============================================================

def source_summary(
    results
):

    summary = {}

    for item in results:

        seller = item.get(
            "seller",
            "Bilinmeyen"
        )

        summary[seller] = (
            summary.get(
                seller,
                0
            ) + 1
        )

    return summary


# ============================================================
# EN UCUZ KART
# ============================================================

def show_best(
    results
):

    if not results:
        return

    cheapest = min(
        results,
        key=lambda x: x["price"]
    )

    title = html.escape(
        cheapest["title"]
    )

    seller = html.escape(
        cheapest["seller"]
    )

    condition = html.escape(
        cheapest["condition"]
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
                {cheapest["price"]:,.2f} TL
            </div>

            <div class="best-store">
                🏪 {seller}
            </div>

            <div class="best-condition">
                📦 {condition}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    if cheapest.get("url"):

        st.link_button(
            "🛒 En Ucuz Sonuca Git",
            cheapest["url"]
        )


# ============================================================
# KATEGORİ GÖSTER
# ============================================================

def show_category(
    title,
    icon,
    results,
    css_class
):

    st.subheader(
        f"{icon} {title}"
    )

    if not results:

        st.markdown(
            '<div class="info-box">'
            'Bu kategoride uygun fiyatlı sonuç bulunamadı.'
            '</div>',
            unsafe_allow_html=True
        )

        return

    for index, item in enumerate(
        results[:30],
        start=1
    ):

        title_html = html.escape(
            item["title"]
        )

        seller_html = html.escape(
            item["seller"]
        )

        condition_html = html.escape(
            item["condition"]
        )

        source_html = html.escape(
            item["source"]
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
                    🏪 {seller_html}
                </div>

                <div class="offer-source">
                    📦 {condition_html}
                    · Kaynak: {source_html}
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )

        if item.get("url"):

            st.link_button(
                "🛒 Sonuca Git",
                item["url"]
            )


# ============================================================
# UYGULAMAYI ÇALIŞTIR
# ============================================================

if search_button:

    # --------------------------------------------------------
    # ÜRÜN KONTROL
    # --------------------------------------------------------

    if not product.strip():

        st.warning(
            "Lütfen bir ürün adı yaz."
        )

        st.stop()

    # --------------------------------------------------------
    # API KEY KONTROL
    # --------------------------------------------------------

    if not API_KEY:

        st.error(
            "SocialCrawl API anahtarı bulunamadı."
        )

        st.info(
            "Streamlit → Settings → Secrets "
            "bölümüne SOCIALCRAWL_API_KEY ekle."
        )

        st.stop()

    product = product.strip()

    st.info(
        f"🔎 **{product}** için fiyatlar "
        f"farklı kaynaklardan araştırılıyor..."
    )

    # --------------------------------------------------------
    # PROGRESS
    # --------------------------------------------------------

    progress = st.progress(
        0
    )

    status = st.empty()

    # --------------------------------------------------------
    # SIFIR
    # --------------------------------------------------------

    status.write(
        "🟢 Sıfır ürünler aranıyor..."
    )

    new_results = search_new(
        product
    )

    progress.progress(
        33
    )

    # --------------------------------------------------------
    # İKİNCİ EL
    # --------------------------------------------------------

    status.write(
        "🟠 Dolap, Sahibinden ve Letgo aranıyor..."
    )

    used_results = search_used(
        product
    )

    progress.progress(
        66
    )

    # --------------------------------------------------------
    # YENİLENMİŞ
    # --------------------------------------------------------

    status.write(
        "🔵 Yenilenmiş ürünler aranıyor..."
    )

    refurb_results = search_refurbished(
        product
    )

    progress.progress(
        100
    )

    time.sleep(
        0.3
    )

    progress.empty()
    status.empty()

    # --------------------------------------------------------
    # TEKRAR TEMİZLE
    # --------------------------------------------------------

    new_results = clean_results(
        new_results
    )

    used_results = clean_results(
        used_results
    )

    refurb_results = clean_results(
        refurb_results
    )

    all_results = clean_results(
        new_results
        + used_results
        + refurb_results
    )

    # --------------------------------------------------------
    # SONUÇ
    # --------------------------------------------------------

    if not all_results:

        st.error(
            f'"{product}" için fiyatlı sonuç bulunamadı.'
        )

        st.markdown(
            '<div class="info-box">'
            'Ürün adını model numarasıyla birlikte '
            'aramayı deneyebilirsin.'
            '</div>',
            unsafe_allow_html=True
        )

        st.stop()

    # --------------------------------------------------------
    # EN UCUZ
    # --------------------------------------------------------

    show_best(
        all_results
    )

    # --------------------------------------------------------
    # ÖZET
    # --------------------------------------------------------

    st.divider()

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "🟢 Sıfır Teklifi",
            len(new_results)
        )

    with col2:

        st.metric(
            "🟠 İkinci El",
            len(used_results)
        )

    with col3:

        st.metric(
            "🔵 Yenilenmiş",
            len(refurb_results)
        )

    with col4:

        st.metric(
            "💰 Toplam Teklif",
            len(all_results)
        )

    # --------------------------------------------------------
    # FİYAT ARALIĞI
    # --------------------------------------------------------

    if len(all_results) >= 2:

        cheapest_price = min(
            x["price"]
            for x in all_results
        )

        highest_price = max(
            x["price"]
            for x in all_results
        )

        difference = (
            highest_price
            - cheapest_price
        )

        st.info(
            f"💰 En düşük ve en yüksek sonuç "
            f"arasında **{difference:,.2f} TL** fark var."
        )

    # --------------------------------------------------------
    # KAYNAKLAR
    # --------------------------------------------------------

    st.divider()

    st.subheader(
        "📊 Kaynak Özeti"
    )

    summary = source_summary(
        all_results
    )

    if summary:

        summary_cols = st.columns(
            min(
                len(summary),
                4
            )
        )

        for index, (
            source,
            count
        ) in enumerate(
            summary.items()
        ):

            with summary_cols[
                index % len(summary_cols)
            ]:

                st.metric(
                    source,
                    count
                )

    # --------------------------------------------------------
    # SIFIR
    # --------------------------------------------------------

    st.divider()

    show_category(
        "Sıfır Ürünler",
        "🟢",
        new_results,
        "offer-new"
    )

    # --------------------------------------------------------
    # İKİNCİ EL
    # --------------------------------------------------------

    st.divider()

    show_category(
        "İkinci El",
        "🟠",
        used_results,
        "offer-used"
    )

    # --------------------------------------------------------
    # YENİLENMİŞ
    # --------------------------------------------------------

    st.divider()

    show_category(
        "Yenilenmiş",
        "🔵",
        refurb_results,
        "offer-refurb"
    )
