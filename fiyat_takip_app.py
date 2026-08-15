import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urlparse
import re
import json
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

TIMEOUT = 15

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,"
        "image/webp,*/*;q=0.8"
    )
}

# ============================================================
# CSS
# ============================================================

st.markdown("""
<style>

.best-card {
    background: linear-gradient(135deg,#ecfdf5,#f0fdf4);
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
    margin-top: 8px;
    color: #111827;
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
    margin-top: 6px;
}

.offer {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 15px;
    padding: 18px;
    margin: 10px 0;
}

.new {
    border-left: 6px solid #22c55e;
}

.used {
    border-left: 6px solid #f97316;
}

.refurb {
    border-left: 6px solid #3b82f6;
}

.offer-title {
    font-size: 18px;
    font-weight: 800;
}

.offer-price {
    font-size: 28px;
    font-weight: 900;
    color: #15803d;
    margin-top: 5px;
}

.offer-store {
    font-weight: 800;
    color: #2563eb;
    margin-top: 5px;
}

.source-ok {
    background:#ecfdf5;
    border:1px solid #bbf7d0;
    padding:9px;
    border-radius:9px;
    margin:5px 0;
}

.source-empty {
    background:#f9fafb;
    border:1px solid #e5e7eb;
    padding:9px;
    border-radius:9px;
    margin:5px 0;
}

.source-error {
    background:#fff7ed;
    border:1px solid #fed7aa;
    padding:9px;
    border-radius:9px;
    margin:5px 0;
}

</style>
""", unsafe_allow_html=True)

# ============================================================
# YARDIMCI
# ============================================================

def normalize(text):
    if not text:
        return ""

    text = str(text).lower()

    table = str.maketrans({
        "ç": "c",
        "ğ": "g",
        "ı": "i",
        "ö": "o",
        "ş": "s",
        "ü": "u"
    })

    text = text.translate(table)

    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def query_tokens(query):
    stop = {
        "ve", "ile", "icin", "için",
        "fiyat", "urun", "ürün",
        "en", "ucuz"
    }

    return [
        x for x in normalize(query).split()
        if len(x) > 1 and x not in stop
    ]


def relevance(query, title):
    q = query_tokens(query)
    t = normalize(title)

    if not q:
        return 0

    return sum(
        1 for word in q
        if word in t
    )


def is_relevant(query, title):
    score = relevance(query, title)
    words = query_tokens(query)

    if len(words) <= 1:
        return score >= 1

    return score >= max(2, len(words) - 1)


# ============================================================
# FİYAT
# ============================================================

def parse_price(value):

    if value is None:
        return None

    value = str(value).strip()

    value = value.replace("₺", "")
    value = re.sub(
        r"\bTL\b",
        "",
        value,
        flags=re.I
    )

    value = value.strip()

    # 1.599,00
    if re.fullmatch(
        r"\d{1,3}(?:\.\d{3})+,\d{1,2}",
        value
    ):
        value = value.replace(".", "")
        value = value.replace(",", ".")

    # 1,599.00
    elif re.fullmatch(
        r"\d{1,3}(?:,\d{3})+\.\d{1,2}",
        value
    ):
        value = value.replace(",", "")

    # 1599,00
    elif re.fullmatch(
        r"\d+,\d{1,2}",
        value
    ):
        value = value.replace(",", ".")

    # 1.599
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

    except:
        pass

    return None


def extract_prices(text):

    if not text:
        return []

    patterns = [
        r"\d{1,3}(?:\.\d{3})+,\d{1,2}\s*(?:TL|₺)",
        r"\d+,\d{1,2}\s*(?:TL|₺)",
        r"\d{1,3}(?:\.\d{3})+\s*(?:TL|₺)",
        r"\d+(?:\.\d{1,2})?\s*(?:TL|₺)",
    ]

    prices = []

    for pattern in patterns:

        for match in re.findall(
            pattern,
            text,
            flags=re.I
        ):

            price = parse_price(match)

            if price:
                prices.append(price)

    return prices


# ============================================================
# HTTP
# ============================================================

def fetch(url):

    try:

        r = requests.get(
            url,
            headers=HEADERS,
            timeout=TIMEOUT,
            allow_redirects=True
        )

        return r

    except Exception:
        return None


# ============================================================
# GOOGLE ARAMA
# ============================================================

def google_search(query):

    url = (
        "https://www.google.com/search?"
        "hl=tr&num=10&q="
        + quote_plus(query)
    )

    response = fetch(url)

    if not response:
        return [], "Google'a ulaşılamadı"

    if response.status_code != 200:
        return [], f"HTTP {response.status_code}"

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    results = []

    for block in soup.select("div.MjjYud"):

        a = block.select_one("a[href]")

        if not a:
            continue

        href = a.get("href", "")

        if not href.startswith("http"):
            continue

        title_node = block.select_one("h3")

        title = (
            title_node.get_text(
                " ",
                strip=True
            )
            if title_node
            else ""
        )

        text = block.get_text(
            " ",
            strip=True
        )

        if title:

            results.append({
                "url": href,
                "title": title,
                "text": text
            })

    return results, None


# ============================================================
# BING ARAMA
# ============================================================

def bing_search(query):

    url = (
        "https://www.bing.com/search?"
        "count=10&q="
        + quote_plus(query)
    )

    response = fetch(url)

    if not response:
        return [], "Bing'e ulaşılamadı"

    if response.status_code != 200:
        return [], f"HTTP {response.status_code}"

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    results = []

    for li in soup.select("li.b_algo"):

        a = li.select_one("h2 a")

        if not a:
            continue

        href = a.get("href", "")

        title = a.get_text(
            " ",
            strip=True
        )

        text = li.get_text(
            " ",
            strip=True
        )

        results.append({
            "url": href,
            "title": title,
            "text": text
        })

    return results, None


# ============================================================
# DUCKDUCKGO YEDEK
# ============================================================

def ddg_search(query):

    url = (
        "https://html.duckduckgo.com/html/?q="
        + quote_plus(query)
    )

    response = fetch(url)

    if not response:
        return [], "DuckDuckGo'ya ulaşılamadı"

    if response.status_code != 200:
        return [], f"HTTP {response.status_code}"

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    results = []

    for a in soup.select(
        "a.result__a"
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

            results.append({
                "url": href,
                "title": title,
                "text": title
            })

    return results, None


# ============================================================
# ÇOKLU ARAMA
# ============================================================

def multi_search(query, domain):

    searches = [
        f"site:{domain} {query}",
        f"site:{domain} \"{query}\""
    ]

    all_results = []
    errors = []

    for q in searches:

        results, error = google_search(q)

        if results:
            all_results.extend(results)

        if error:
            errors.append(error)

        if results:
            break

    if not all_results:

        for q in searches:

            results, error = bing_search(q)

            if results:
                all_results.extend(results)
                break

            if error:
                errors.append(error)

    if not all_results:

        for q in searches:

            results, error = ddg_search(q)

            if results:
                all_results.extend(results)
                break

            if error:
                errors.append(error)

    # URL tekrarlarını sil
    unique = {}

    for item in all_results:

        url = item.get("url")

        if url and url not in unique:
            unique[url] = item

    return list(unique.values()), errors


# ============================================================
# ÜRÜN SAYFASI ANALİZ
# ============================================================

def analyze_product_page(
    query,
    result,
    store,
    condition
):

    url = result.get("url", "")
    search_title = result.get("title", "")
    search_text = result.get("text", "")

    if not url:
        return None

    # İlk olarak arama sonucunun kendi metnini dene
    candidate_text = (
        search_title + " " + search_text
    )

    prices = extract_prices(
        candidate_text
    )

    # Sayfayı aç
    response = fetch(url)

    page_title = search_title
    page_text = ""

    if response:

        if response.status_code == 200:

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            if soup.title:

                page_title = soup.title.get_text(
                    " ",
                    strip=True
                )

            page_text = soup.get_text(
                " ",
                strip=True
            )

            # JSON-LD fiyatlarını özellikle ara
            for script in soup.select(
                'script[type="application/ld+json"]'
            ):

                raw = script.string

                if not raw:
                    continue

                try:

                    data = json.loads(raw)

                    stack = (
                        data
                        if isinstance(data, list)
                        else [data]
                    )

                    for obj in stack:

                        if not isinstance(
                            obj,
                            dict
                        ):
                            continue

                        offers = obj.get(
                            "offers"
                        )

                        if isinstance(
                            offers,
                            dict
                        ):

                            price = offers.get(
                                "price"
                            )

                            p = parse_price(
                                price
                            )

                            if p:
                                prices.append(p)

                        elif isinstance(
                            offers,
                            list
                        ):

                            for offer in offers:

                                if not isinstance(
                                    offer,
                                    dict
                                ):
                                    continue

                                p = parse_price(
                                    offer.get(
                                        "price"
                                    )
                                )

                                if p:
                                    prices.append(p)

                except:
                    pass

            # Sayfa fiyatları
            prices.extend(
                extract_prices(
                    page_text
                )
            )

    combined = (
        page_title + " " +
        candidate_text + " " +
        page_text[:15000]
    )

    # Ürün eşleşmiyorsa alma
    if not is_relevant(
        query,
        combined
    ):
        return None

    # Yenilenmiş ürün filtresi
    if condition == "Yenilenmiş":

        if "yenilen" not in normalize(
            combined
        ):
            return None

    # İkinci el filtresi
    if condition == "İkinci El":

        normalized = normalize(
            combined
        )

        used_words = [
            "ikinci el",
            "kullanilmis",
            "kullanılmış",
            "sahibinden",
            "temiz kullanilmis",
            "az kullanilmis"
        ]

        if not any(
            normalize(x) in normalized
            for x in used_words
        ):
            return None

    # Mantıksız fiyatları çıkar
    prices = [
        p for p in prices
        if 20 <= p <= 1000000
    ]

    if not prices:
        return None

    # Çok büyük olasılıkla sayfadaki
    # gerçek satış fiyatlarından en düşüğünü al.
    price = min(prices)

    return {
        "title": page_title[:250],
        "price": price,
        "store": store,
        "condition": condition,
        "url": url
    }


# ============================================================
# KAYNAK
# ============================================================

def search_source(
    query,
    store,
    domain,
    condition="Sıfır"
):

    status = {
        "name": store,
        "count": 0,
        "state": "empty",
        "detail": ""
    }

    search_results, errors = multi_search(
        query,
        domain
    )

    if not search_results:

        status["state"] = "error"

        if errors:
            status["detail"] = errors[-1]
        else:
            status["detail"] = (
                "Arama motorundan sonuç alınamadı"
            )

        return [], status

    output = []

    for result in search_results[:8]:

        item = analyze_product_page(
            query,
            result,
            store,
            condition
        )

        if item:

            output.append(item)

        time.sleep(.25)

    # tekrarları kaldır
    unique = {}

    for item in output:

        key = (
            item["url"],
            round(item["price"], 2)
        )

        unique[key] = item

    output = list(
        unique.values()
    )

    output.sort(
        key=lambda x: x["price"]
    )

    status["count"] = len(output)

    if output:
        status["state"] = "ok"
    else:
        status["state"] = "empty"
        status["detail"] = (
            "Kaynakta sonuç bulundu ancak "
            "ürün/fiyat doğrulanamadı"
        )

    return output, status


# ============================================================
# KAYNAKLAR
# ============================================================

NEW_SOURCES = [
    ("Akakçe", "akakce.com"),
    ("Cimri", "cimri.com"),
    ("Hepsiburada", "hepsiburada.com"),
    ("Trendyol", "trendyol.com"),
    ("N11", "n11.com"),
    ("Amazon Türkiye", "amazon.com.tr"),
]

USED_SOURCES = [
    ("Dolap", "dolap.com"),
    ("Sahibinden", "sahibinden.com"),
    ("Letgo", "letgo.com"),
]

REFURBISHED_SOURCES = [
    ("Yenilenmiş • Hepsiburada", "hepsiburada.com"),
    ("Yenilenmiş • Trendyol", "trendyol.com"),
    ("Yenilenmiş • N11", "n11.com"),
    ("Yenilenmiş • Amazon Türkiye", "amazon.com.tr"),
]


# ============================================================
# KAYNAK DURUMU
# ============================================================

def show_status(statuses):

    st.subheader("📊 Kaynak Durumu")

    for s in statuses:

        name = html.escape(
            s["name"]
        )

        count = s["count"]

        if s["state"] == "ok":

            st.markdown(
                f"""
                <div class="source-ok">
                🟢 <b>{name}</b> → {count} doğrulanabilir sonuç
                </div>
                """,
                unsafe_allow_html=True
            )

        elif s["state"] == "error":

            detail = html.escape(
                s["detail"]
            )

            st.markdown(
                f"""
                <div class="source-error">
                🟠 <b>{name}</b> → Erişilemedi
                <br>
                <small>{detail}</small>
                </div>
                """,
                unsafe_allow_html=True
            )

        else:

            detail = html.escape(
                s["detail"]
            )

            st.markdown(
                f"""
                <div class="source-empty">
                ⚪ <b>{name}</b> → 0 doğrulanabilir sonuç
                <br>
                <small>{detail}</small>
                </div>
                """,
                unsafe_allow_html=True
            )


# ============================================================
# SONUÇ TEMİZLE
# ============================================================

def clean_results(results):

    unique = {}

    for item in results:

        key = (
            normalize(item["store"]),
            normalize(item["title"]),
            round(item["price"], 2),
            normalize(item["condition"])
        )

        if key not in unique:
            unique[key] = item

    result = list(
        unique.values()
    )

    result.sort(
        key=lambda x: x["price"]
    )

    return result


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
            "🛒 Bu Fiyata Git",
            best["url"],
            use_container_width=True
        )


# ============================================================
# KATEGORİ GÖSTER
# ============================================================

def show_category(
    title,
    results,
    css
):

    st.subheader(title)

    if not results:

        st.info(
            "Bu kategoride doğrulanabilir sonuç bulunamadı."
        )

        return

    for i, item in enumerate(
        results[:30],
        1
    ):

        title_text = html.escape(
            item["title"]
        )

        store = html.escape(
            item["store"]
        )

        condition = html.escape(
            item["condition"]
        )

        st.markdown(
            f"""
            <div class="offer {css}">

                <div class="offer-title">
                    {i}. {title_text}
                </div>

                <div class="offer-price">
                    {item["price"]:,.2f} TL
                </div>

                <div class="offer-store">
                    🏪 {store}
                </div>

                <div>
                    📦 {condition}
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
# ARAYÜZ
# ============================================================

st.title("💰 Fiyat Avcısı")

st.caption(
    "Sıfır • İkinci El • Yenilenmiş • Çoklu Kaynak"
)

query = st.text_input(
    "🔎 Ürün ara",
    placeholder="Örn: Grundig Club BT"
)

search = st.button(
    "🔍 FİYATLARI BUL",
    type="primary",
    use_container_width=True
)


# ============================================================
# ÇALIŞTIR
# ============================================================

if search:

    query = query.strip()

    if not query:

        st.warning(
            "Ürün adını yaz."
        )

        st.stop()

    all_results = []
    statuses = []

    progress = st.progress(
        0,
        text="Arama hazırlanıyor..."
    )

    # --------------------------------------------------------
    # SIFIR
    # --------------------------------------------------------

    total = len(
        NEW_SOURCES
        + USED_SOURCES
        + REFURBISHED_SOURCES
    )

    done = 0

    for store, domain in NEW_SOURCES:

        done += 1

        progress.progress(
            int(done / total * 100),
            text=f"{store} aranıyor..."
        )

        results, status = search_source(
            query,
            store,
            domain,
            "Sıfır"
        )

        all_results.extend(
            results
        )

        statuses.append(
            status
        )

    # --------------------------------------------------------
    # İKİNCİ EL
    # --------------------------------------------------------

    for store, domain in USED_SOURCES:

        done += 1

        progress.progress(
            int(done / total * 100),
            text=f"{store} ikinci el aranıyor..."
        )

        results, status = search_source(
            query,
            f"İkinci El • {store}",
            domain,
            "İkinci El"
        )

        all_results.extend(
            results
        )

        statuses.append(
            status
        )

    # --------------------------------------------------------
    # YENİLENMİŞ
    # --------------------------------------------------------

    for store, domain in REFURBISHED_SOURCES:

        done += 1

        progress.progress(
            int(done / total * 100),
            text=f"{store} aranıyor..."
        )

        results, status = search_source(
            query,
            store,
            domain,
            "Yenilenmiş"
        )

        all_results.extend(
            results
        )

        statuses.append(
            status
        )

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

        show_status(
            statuses
        )

    # --------------------------------------------------------
    # SONUÇ
    # --------------------------------------------------------

    if not all_results:

        st.error(
            f'"{query}" için doğrulanabilir fiyat bulunamadı.'
        )

        st.info(
            "Kaynakların cevap verip vermediğini "
            "yukarıdaki Kaynak Durumu bölümünden görebilirsin."
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

    new = [
        x for x in all_results
        if x["condition"] == "Sıfır"
    ]

    used = [
        x for x in all_results
        if x["condition"] == "İkinci El"
    ]

    refurbished = [
        x for x in all_results
        if x["condition"] == "Yenilenmiş"
    ]

    a, b, c, d = st.columns(4)

    a.metric(
        "🟢 Sıfır",
        len(new)
    )

    b.metric(
        "🟠 İkinci El",
        len(used)
    )

    c.metric(
        "🔵 Yenilenmiş",
        len(refurbished)
    )

    d.metric(
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
        expensive = max(prices)

        st.success(
            f"💰 En ucuz: **{cheapest:,.2f} TL**  |  "
            f"En pahalı: **{expensive:,.2f} TL**  |  "
            f"Fark: **{expensive - cheapest:,.2f} TL**"
        )

    # --------------------------------------------------------
    # KATEGORİLER
    # --------------------------------------------------------

    st.divider()

    show_category(
        "🟢 Sıfır Ürünler",
        new,
        "new"
    )

    st.divider()

    show_category(
        "🟠 İkinci El",
        used,
        "used"
    )

    st.divider()

    show_category(
        "🔵 Yenilenmiş",
        refurbished,
        "refurb"
    )
