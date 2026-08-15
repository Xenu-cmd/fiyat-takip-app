import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin, urlparse
import re
import time
import html


# ============================================================
# AYARLAR
# ============================================================

st.set_page_config(
    page_title="Fiyat Avcısı",
    page_icon="💰",
    layout="wide"
)

TIMEOUT = 20

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    )
}


# ============================================================
# CSS
# ============================================================

st.markdown("""
<style>

.main-title {
    text-align: center;
    font-size: 42px;
    font-weight: 900;
    color: #111827;
    margin-bottom: 4px;
}

.subtitle {
    text-align: center;
    color: #6b7280;
    font-size: 17px;
    margin-bottom: 25px;
}

.best-card {
    background: linear-gradient(135deg, #ecfdf5, #f0fdf4);
    border: 2px solid #22c55e;
    border-radius: 20px;
    padding: 28px;
    margin: 20px 0;
    box-shadow: 0 8px 25px rgba(0,0,0,.06);
}

.best-title {
    font-size: 22px;
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
    font-size: 42px;
    font-weight: 900;
    color: #15803d;
    margin-top: 8px;
}

.best-store {
    font-size: 17px;
    font-weight: 800;
    margin-top: 8px;
}

.best-condition {
    font-size: 16px;
    font-weight: 800;
    margin-top: 7px;
}

.offer {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 16px;
    padding: 18px;
    margin-bottom: 12px;
    box-shadow: 0 3px 12px rgba(0,0,0,.04);
}

.offer-new {
    border-left: 6px solid #22c55e;
}

.offer-used {
    border-left: 6px solid #f97316;
}

.offer-refurbished {
    border-left: 6px solid #3b82f6;
}

.offer-title {
    font-size: 18px;
    font-weight: 800;
    color: #111827;
}

.offer-price {
    font-size: 29px;
    font-weight: 900;
    color: #15803d;
    margin-top: 6px;
}

.offer-store {
    color: #2563eb;
    font-weight: 800;
    margin-top: 6px;
}

.offer-condition {
    font-weight: 800;
    margin-top: 5px;
}

.source-ok {
    background: #ecfdf5;
    border: 1px solid #bbf7d0;
    padding: 10px;
    border-radius: 10px;
    margin-bottom: 6px;
}

.source-empty {
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    padding: 10px;
    border-radius: 10px;
    margin-bottom: 6px;
}

.source-error {
    background: #fff7ed;
    border: 1px solid #fed7aa;
    padding: 10px;
    border-radius: 10px;
    margin-bottom: 6px;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# BAŞLIK
# ============================================================

st.markdown(
    '<div class="main-title">💰 Fiyat Avcısı</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Sıfır • İkinci El • Yenilenmiş • Gerçek Kaynak Karşılaştırması'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

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
        "ü": "u",
    }

    for a, b in replacements.items():
        text = text.replace(a, b)

    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def product_words(query):
    stop = {
        "ve",
        "ile",
        "icin",
        "için",
        "urun",
        "ürün",
        "fiyat",
        "al",
        "satın",
        "satin",
        "hoparlor",
        "hoparlör",
    }

    return [
        x
        for x in normalize(query).split()
        if len(x) >= 2 and x not in stop
    ]


def relevance_score(query, title):
    words = product_words(query)
    text = normalize(title)

    if not words:
        return 0

    return sum(
        1 for word in words
        if word in text
    )


def relevant(query, title):
    words = product_words(query)

    if not words:
        return False

    score = relevance_score(
        query,
        title
    )

    if len(words) == 1:
        return score >= 1

    if len(words) == 2:
        return score >= 2

    return score >= max(
        2,
        len(words) - 1
    )


# ============================================================
# FİYAT PARSE
# ============================================================

def parse_price(value):

    if value is None:
        return None

    if isinstance(value, (int, float)):
        try:
            value = float(value)

            if 1 <= value <= 10000000:
                return value

        except Exception:
            return None

    value = str(value)

    value = value.replace("₺", "")
    value = re.sub(
        r"\bTL\b",
        "",
        value,
        flags=re.I
    )

    value = value.strip()

    # 1.799,00
    if re.fullmatch(
        r"\d{1,3}(?:\.\d{3})+,\d{1,2}",
        value
    ):
        value = value.replace(".", "")
        value = value.replace(",", ".")

    # 1,799.00
    elif re.fullmatch(
        r"\d{1,3}(?:,\d{3})+\.\d{1,2}",
        value
    ):
        value = value.replace(",", "")

    # 1799,00
    elif re.fullmatch(
        r"\d+,\d{1,2}",
        value
    ):
        value = value.replace(",", ".")

    # 1.799
    elif re.fullmatch(
        r"\d{1,3}(?:\.\d{3})+",
        value
    ):
        value = value.replace(".", "")

    else:
        value = re.sub(
            r"[^0-9.,]",
            "",
            value
        )

    try:
        price = float(value)

        if 1 <= price <= 10000000:
            return price

    except Exception:
        pass

    return None


def extract_prices(text):

    if not text:
        return []

    text = str(text)

    patterns = [
        r"\d{1,3}(?:\.\d{3})+,\d{1,2}\s*(?:TL|₺)",
        r"\d+,\d{1,2}\s*(?:TL|₺)",
        r"\d{1,3}(?:\.\d{3})+\s*(?:TL|₺)",
        r"\d+(?:\.\d{1,2})?\s*(?:TL|₺)",
    ]

    found = []

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text,
            flags=re.I
        )

        for match in matches:

            price = parse_price(match)

            if price is not None:
                found.append(price)

    return found


# ============================================================
# HTTP
# ============================================================

def fetch(url):

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=TIMEOUT,
            allow_redirects=True
        )

        return response

    except Exception:
        return None


# ============================================================
# KAYNAK ADI
# ============================================================

def source_name(url):

    domain = urlparse(
        url
    ).netloc.lower()

    mapping = {
        "akakce.com": "Akakçe",
        "www.akakce.com": "Akakçe",

        "cimri.com": "Cimri",
        "www.cimri.com": "Cimri",

        "hepsiburada.com": "Hepsiburada",
        "www.hepsiburada.com": "Hepsiburada",

        "trendyol.com": "Trendyol",
        "www.trendyol.com": "Trendyol",

        "n11.com": "N11",
        "www.n11.com": "N11",

        "amazon.com.tr": "Amazon Türkiye",
        "www.amazon.com.tr": "Amazon Türkiye",

        "dolap.com": "Dolap",
        "www.dolap.com": "Dolap",

        "sahibinden.com": "Sahibinden",
        "www.sahibinden.com": "Sahibinden",

        "letgo.com": "Letgo",
        "www.letgo.com": "Letgo",

        "grundig.com.tr": "Grundig"
    }

    return mapping.get(
        domain,
        domain
    )


# ============================================================
# DUCKDUCKGO İLE KAYNAK BUL
# ============================================================

def search_engine(query, domain):

    search = (
        f"site:{domain} "
        f'"{query}"'
    )

    url = (
        "https://html.duckduckgo.com/html/?q="
        + quote_plus(search)
    )

    response = fetch(url)

    if not response:
        return []

    if response.status_code != 200:
        return []

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    links = []

    for result in soup.select(
        ".result__a"
    ):

        href = result.get(
            "href",
            ""
        )

        title = result.get_text(
            " ",
            strip=True
        )

        if not href:
            continue

        if href.startswith("//"):
            href = "https:" + href

        if href.startswith("/"):
            continue

        links.append({
            "url": href,
            "title": title
        })

    return links[:10]


# ============================================================
# AKAKÇE
# ============================================================

def search_akakce(query):

    status = {
        "name": "Akakçe",
        "count": 0,
        "error": None
    }

    results = []

    links = search_engine(
        query,
        "akakce.com"
    )

    # Arama motoru sonuç vermediyse doğrudan
    # Akakçe URL kalıbını da deniyoruz.
    if not links:

        slug = normalize(query)
        slug = slug.replace(" ", "-")

        links = [{
            "url": (
                "https://www.akakce.com/"
                "arama/?q="
                + quote_plus(query)
            ),
            "title": query
        }]

    for item in links:

        url = item["url"]

        response = fetch(url)

        if not response:
            continue

        if response.status_code != 200:
            continue

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        page_text = soup.get_text(
            " ",
            strip=True
        )

        title = soup.title.get_text(
            " ",
            strip=True
        ) if soup.title else item["title"]

        if not relevant(
            query,
            title + " " + page_text[:1500]
        ):
            continue

        prices = extract_prices(
            page_text
        )

        # Çok küçük / anlamsız fiyatları ele.
        prices = [
            p for p in prices
            if p >= 50
        ]

        if prices:

            price = min(
                prices
            )

            results.append({
                "title": title[:200],
                "price": price,
                "store": "Akakçe",
                "condition": "Sıfır",
                "source": "Akakçe",
                "url": url
            })

        time.sleep(.4)

    status["count"] = len(results)

    return results, status


# ============================================================
# CİMRİ
# ============================================================

def search_cimri(query):

    status = {
        "name": "Cimri",
        "count": 0,
        "error": None
    }

    results = []

    links = search_engine(
        query,
        "cimri.com"
    )

    for item in links:

        url = item["url"]

        response = fetch(url)

        if not response:
            continue

        if response.status_code != 200:
            continue

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        page_text = soup.get_text(
            " ",
            strip=True
        )

        title = soup.title.get_text(
            " ",
            strip=True
        ) if soup.title else item["title"]

        if not relevant(
            query,
            title
        ):
            continue

        prices = extract_prices(
            page_text
        )

        prices = [
            p for p in prices
            if p >= 50
        ]

        if prices:

            results.append({
                "title": title[:200],
                "price": min(prices),
                "store": "Cimri",
                "condition": "Sıfır",
                "source": "Cimri",
                "url": url
            })

        time.sleep(.4)

    status["count"] = len(results)

    return results, status


# ============================================================
# MAĞAZA ARAMASI
# ============================================================

STORE_DOMAINS = {
    "Hepsiburada": "hepsiburada.com",
    "Trendyol": "trendyol.com",
    "N11": "n11.com",
    "Amazon Türkiye": "amazon.com.tr",
}


def search_store(
    query,
    store,
    domain,
    condition="Sıfır"
):

    status = {
        "name": store,
        "count": 0,
        "error": None
    }

    results = []

    links = search_engine(
        query,
        domain
    )

    for item in links:

        url = item["url"]

        response = fetch(url)

        if not response:
            continue

        if response.status_code != 200:
            continue

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        title = soup.title.get_text(
            " ",
            strip=True
        ) if soup.title else item["title"]

        page_text = soup.get_text(
            " ",
            strip=True
        )

        if not relevant(
            query,
            title
        ):
            continue

        prices = extract_prices(
            page_text
        )

        prices = [
            p for p in prices
            if p >= 50
        ]

        if prices:

            results.append({
                "title": title[:220],
                "price": min(prices),
                "store": store,
                "condition": condition,
                "source": store,
                "url": url
            })

        time.sleep(.3)

    status["count"] = len(results)

    return results, status


# ============================================================
# İKİNCİ EL
# ============================================================

USED_SOURCES = {
    "Dolap": "dolap.com",
    "Sahibinden": "sahibinden.com",
    "Letgo": "letgo.com",
}


def search_used(
    query,
    store,
    domain
):

    status = {
        "name": "İkinci El • " + store,
        "count": 0,
        "error": None
    }

    results = []

    search = (
        f'"{query}" '
        f'site:{domain} '
        f'(ikinci el OR kullanılmış OR kullanilmis)'
    )

    url = (
        "https://html.duckduckgo.com/html/?q="
        + quote_plus(search)
    )

    response = fetch(url)

    if not response:
        return results, status

    if response.status_code != 200:
        return results, status

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    links = []

    for a in soup.select(
        ".result__a"
    ):

        href = a.get(
            "href",
            ""
        )

        title = a.get_text(
            " ",
            strip=True
        )

        if href:
            links.append(
                (href, title)
            )

    for href, title in links[:10]:

        page = fetch(href)

        if not page:
            continue

        if page.status_code != 200:
            continue

        page_soup = BeautifulSoup(
            page.text,
            "html.parser"
        )

        page_title = (
            page_soup.title.get_text(
                " ",
                strip=True
            )
            if page_soup.title
            else title
        )

        text = page_soup.get_text(
            " ",
            strip=True
        )

        if not relevant(
            query,
            page_title
        ):
            continue

        prices = extract_prices(
            text
        )

        prices = [
            p for p in prices
            if p >= 20
        ]

        if prices:

            results.append({
                "title": page_title[:220],
                "price": min(prices),
                "store": store,
                "condition": "İkinci El",
                "source": store,
                "url": href
            })

        time.sleep(.3)

    status["count"] = len(results)

    return results, status


# ============================================================
# YENİLENMİŞ
# ============================================================

def search_refurbished(
    query,
    store,
    domain
):

    status = {
        "name": "Yenilenmiş • " + store,
        "count": 0,
        "error": None
    }

    results = []

    search = (
        f'"{query}" '
        f'"yenilenmiş" '
        f'site:{domain}'
    )

    url = (
        "https://html.duckduckgo.com/html/?q="
        + quote_plus(search)
    )

    response = fetch(url)

    if not response:
        return results, status

    if response.status_code != 200:
        return results, status

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    for a in soup.select(
        ".result__a"
    )[:10]:

        href = a.get(
            "href",
            ""
        )

        title = a.get_text(
            " ",
            strip=True
        )

        if not href:
            continue

        page = fetch(href)

        if not page:
            continue

        if page.status_code != 200:
            continue

        page_soup = BeautifulSoup(
            page.text,
            "html.parser"
        )

        page_title = (
            page_soup.title.get_text(
                " ",
                strip=True
            )
            if page_soup.title
            else title
        )

        text = page_soup.get_text(
            " ",
            strip=True
        )

        normalized = normalize(
            text[:10000]
        )

        if "yenilenmis" not in normalized:
            continue

        if not relevant(
            query,
            page_title
        ):
            continue

        prices = extract_prices(
            text
        )

        prices = [
            p for p in prices
            if p >= 50
        ]

        if prices:

            results.append({
                "title": page_title[:220],
                "price": min(prices),
                "store": store,
                "condition": "Yenilenmiş",
                "source": store,
                "url": href
            })

        time.sleep(.3)

    status["count"] = len(results)

    return results, status


# ============================================================
# TEKRARLARI TEMİZLE
# ============================================================

def clean_results(results):

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

        title = str(
            item.get(
                "title",
                ""
            )
        )

        store = str(
            item.get(
                "store",
                ""
            )
        )

        condition = str(
            item.get(
                "condition",
                ""
            )
        )

        url = str(
            item.get(
                "url",
                ""
            )
        )

        key = (
            normalize(title),
            normalize(store),
            normalize(condition),
            round(price, 2)
        )

        if key not in unique:

            item["price"] = price

            unique[key] = item

    result = list(
        unique.values()
    )

    result.sort(
        key=lambda x: x["price"]
    )

    return result


# ============================================================
# KAYNAK DURUMU
# ============================================================

def show_source_status(statuses):

    st.markdown(
        "### 📊 Kaynak Durumu"
    )

    for status in statuses:

        name = status["name"]
        count = status["count"]
        error = status["error"]

        if error:

            st.markdown(
                f"""
                <div class="source-error">
                    🟠 <b>{html.escape(name)}</b>
                    → {html.escape(str(error))}
                </div>
                """,
                unsafe_allow_html=True
            )

        elif count > 0:

            st.markdown(
                f"""
                <div class="source-ok">
                    🟢 <b>{html.escape(name)}</b>
                    → {count} sonuç
                </div>
                """,
                unsafe_allow_html=True
            )

        else:

            st.markdown(
                f"""
                <div class="source-empty">
                    ⚪ <b>{html.escape(name)}</b>
                    → 0 doğrulanabilir sonuç
                </div>
                """,
                unsafe_allow_html=True
            )


# ============================================================
# EN UCUZ
# ============================================================

def show_best(results):

    if not results:
        return

    best = min(
        results,
        key=lambda x: x["price"]
    )

    title = html.escape(
        best["title"]
    )

    store = html.escape(
        best["store"]
    )

    condition = html.escape(
        best["condition"]
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
                {best["price"]:,.2f} TL
            </div>

            <div class="best-store">
                🏪 {store}
            </div>

            <div class="best-condition">
                📦 {condition}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    if best.get("url"):

        st.link_button(
            "🛒 En Ucuz Fiyata Git",
            best["url"],
            use_container_width=True
        )


# ============================================================
# SONUÇLARI GÖSTER
# ============================================================

def show_results(
    title,
    results,
    css
):

    st.subheader(title)

    if not results:

        st.info(
            "Bu kategoride doğrulanabilir "
            "sonuç bulunamadı."
        )

        return

    for index, item in enumerate(
        results[:30],
        1
    ):

        safe_title = html.escape(
            item["title"]
        )

        safe_store = html.escape(
            item["store"]
        )

        safe_condition = html.escape(
            item["condition"]
        )

        st.markdown(
            f"""
            <div class="offer {css}">

                <div class="offer-title">
                    {index}. {safe_title}
                </div>

                <div class="offer-price">
                    {item["price"]:,.2f} TL
                </div>

                <div class="offer-store">
                    🏪 {safe_store}
                </div>

                <div class="offer-condition">
                    📦 {safe_condition}
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )

        if item.get("url"):

            st.link_button(
                "Ürüne Git",
                item["url"]
            )


# ============================================================
# ARAMA
# ============================================================

query = st.text_input(
    "🔎 Ürün adı",
    placeholder="Örn: Grundig Club BT"
)

search_button = st.button(
    "🔍 FİYATLARI BUL",
    type="primary",
    use_container_width=True
)


# ============================================================
# ÇALIŞTIR
# ============================================================

if search_button:

    query = query.strip()

    if not query:

        st.warning(
            "Önce ürün adını yaz."
        )

        st.stop()

    all_results = []
    statuses = []

    progress = st.progress(
        0,
        text="Arama başlıyor..."
    )

    # --------------------------------------------------------
    # AKAKÇE
    # --------------------------------------------------------

    progress.progress(
        8,
        text="Akakçe araştırılıyor..."
    )

    akakce_results, status = (
        search_akakce(query)
    )

    all_results.extend(
        akakce_results
    )

    statuses.append(
        status
    )

    # --------------------------------------------------------
    # CİMRİ
    # --------------------------------------------------------

    progress.progress(
        20,
        text="Cimri araştırılıyor..."
    )

    cimri_results, status = (
        search_cimri(query)
    )

    all_results.extend(
        cimri_results
    )

    statuses.append(
        status
    )

    # --------------------------------------------------------
    # MAĞAZALAR
    # --------------------------------------------------------

    percent = 30

    for store, domain in STORE_DOMAINS.items():

        progress.progress(
            percent,
            text=f"{store} araştırılıyor..."
        )

        results, status = search_store(
            query,
            store,
            domain
        )

        all_results.extend(
            results
        )

        statuses.append(
            status
        )

        percent += 10

    # --------------------------------------------------------
    # DOLAP / SAHİBİNDEN / LETGO
    # --------------------------------------------------------

    for store, domain in USED_SOURCES.items():

        progress.progress(
            min(percent, 85),
            text=f"{store} ikinci el aranıyor..."
        )

        results, status = search_used(
            query,
            store,
            domain
        )

        all_results.extend(
            results
        )

        statuses.append(
            status
        )

        percent += 4

    # --------------------------------------------------------
    # YENİLENMİŞ
    # --------------------------------------------------------

    for store, domain in {
        "Hepsiburada": "hepsiburada.com",
        "Trendyol": "trendyol.com",
        "N11": "n11.com",
        "Amazon Türkiye": "amazon.com.tr"
    }.items():

        progress.progress(
            min(percent, 96),
            text=f"{store} yenilenmiş ürünleri aranıyor..."
        )

        results, status = (
            search_refurbished(
                query,
                store,
                domain
            )
        )

        all_results.extend(
            results
        )

        statuses.append(
            status
        )

        percent += 1

    progress.progress(
        100,
        text="Sonuçlar hazırlanıyor..."
    )

    time.sleep(.3)

    progress.empty()

    # --------------------------------------------------------
    # TEMİZLE
    # --------------------------------------------------------

    all_results = clean_results(
        all_results
    )

    # --------------------------------------------------------
    # DURUM
    # --------------------------------------------------------

    with st.expander(
        "📊 Kaynak Durumu",
        expanded=True
    ):

        show_source_status(
            statuses
        )

    # --------------------------------------------------------
    # SONUÇ YOK
    # --------------------------------------------------------

    if not all_results:

        st.error(
            f'"{query}" için doğrulanabilir fiyat bulunamadı.'
        )

        st.info(
            "Bu sonuç, ücretli API kredisi bittiği için "
            "değil; ücretsiz kaynaklardan fiyat "
            "doğrulanamadığı için gösteriliyor."
        )

        st.stop()

    # --------------------------------------------------------
    # KATEGORİLER
    # --------------------------------------------------------

    new_results = [
        x for x in all_results
        if x["condition"] == "Sıfır"
    ]

    used_results = [
        x for x in all_results
        if x["condition"] == "İkinci El"
    ]

    refurbished_results = [
        x for x in all_results
        if x["condition"] == "Yenilenmiş"
    ]

    # --------------------------------------------------------
    # EN UCUZ
    # --------------------------------------------------------

    show_best(
        all_results
    )

    # --------------------------------------------------------
    # ÖZET
    # --------------------------------------------------------

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "🟢 Sıfır",
            len(new_results)
        )

    with c2:
        st.metric(
            "🟠 İkinci El",
            len(used_results)
        )

    with c3:
        st.metric(
            "🔵 Yenilenmiş",
            len(refurbished_results)
        )

    with c4:
        st.metric(
            "📦 Toplam",
            len(all_results)
        )

    # --------------------------------------------------------
    # FİYAT ARALIĞI
    # --------------------------------------------------------

    prices = [
        x["price"]
        for x in all_results
    ]

    if prices:

        cheapest = min(prices)
        highest = max(prices)

        difference = (
            highest - cheapest
        )

        st.success(
            f"💰 En ucuz: **{cheapest:,.2f} TL**   |   "
            f"En pahalı: **{highest:,.2f} TL**   |   "
            f"Fark: **{difference:,.2f} TL**"
        )

    # --------------------------------------------------------
    # SONUÇLAR
    # --------------------------------------------------------

    st.divider()

    show_results(
        "🟢 Sıfır Ürünler",
        new_results,
        "offer-new"
    )

    st.divider()

    show_results(
        "🟠 İkinci El",
        used_results,
        "offer-used"
    )

    st.divider()

    show_results(
        "🔵 Yenilenmiş",
        refurbished_results,
        "offer-refurbished"
    )
