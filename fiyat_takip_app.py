import streamlit as st
import requests
import re
from urllib.parse import unquote, urlparse


# =========================================================
# SAYFA
# =========================================================

st.set_page_config(
    page_title="Akıllı Fiyat Karşılaştırma",
    page_icon="🔎",
    layout="wide"
)


# =========================================================
# BAŞLIK
# =========================================================

st.title("🔎 Akıllı Fiyat Karşılaştırma")

st.caption(
    "Sıfır, ikinci el ve yenilenmiş ürünleri tek yerde karşılaştır."
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
# HTTP
# =========================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    )
}


# =========================================================
# METİN NORMALİZE
# =========================================================

def normalize_text(text):

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


# =========================================================
# ÜRÜN KELİMELERİ
# =========================================================

def product_words(product):

    words = []

    for word in normalize_text(product).split():

        if len(word) >= 2:
            words.append(word)

    return words


# =========================================================
# ÜRÜN UYGUN MU?
# =========================================================

def product_is_relevant(
    product,
    title,
    description=""
):

    words = product_words(product)

    text = normalize_text(
        str(title) + " " + str(description)
    )

    if not words:
        return True

    matched = 0

    for word in words:

        if word in text:
            matched += 1

    if len(words) == 1:
        return matched == 1

    ratio = matched / len(words)

    return ratio >= 0.65


# =========================================================
# PARA BİRİMİ
# =========================================================

def currency_symbol(currency):

    currency = str(
        currency or ""
    ).upper()

    symbols = {
        "TRY": "TL",
        "TL": "TL",
        "USD": "$",
        "EUR": "€",
        "GBP": "£"
    }

    return symbols.get(
        currency,
        currency
    )


# =========================================================
# FİYAT GÖSTER
# =========================================================

def format_price(
    price,
    currency="TRY"
):

    try:
        price = float(price)
    except:
        return "Fiyat yok"

    symbol = currency_symbol(currency)

    if symbol == "TL":

        return f"{price:,.2f} TL"

    if symbol in ["$", "€", "£"]:

        return f"{price:,.2f} {symbol}"

    return f"{price:,.2f} {symbol}"


# =========================================================
# DOMAIN
# =========================================================

def get_domain(url):

    try:

        domain = urlparse(
            url
        ).netloc

        return domain.replace(
            "www.",
            ""
        )

    except:
        return ""


# =========================================================
# GOOGLE SHOPPING
# =========================================================

def search_shopping(product):

    api_key = get_api_key()

    if not api_key:

        st.error(
            "❌ SOCIALCRAWL_API_KEY bulunamadı."
        )

        st.info(
            "Streamlit → Settings → Secrets bölümüne "
            "API anahtarını eklemelisin."
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
        "x-api-key": api_key,
        "Accept": "application/json"
    }

    try:

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=40
        )

    except requests.exceptions.Timeout:

        st.error(
            "⏱️ Fiyat araması zaman aşımına uğradı."
        )

        return []

    except Exception as e:

        st.error(
            f"❌ Bağlantı hatası: {e}"
        )

        return []

    if response.status_code != 200:

        st.error(
            f"❌ API hatası: {response.status_code}"
        )

        return []

    try:

        data = response.json()

    except:

        st.error(
            "❌ API cevabı okunamadı."
        )

        return []

    if not data.get("success"):

        st.error(
            "❌ Google Shopping araması başarısız."
        )

        return []

    return (
        data
        .get("data", {})
        .get("items", [])
    )


# =========================================================
# GOOGLE WEB ARAMASI
# =========================================================

def search_web(
    query,
    product,
    condition
):

    url = (
        "https://www.google.com/"
        "search"
    )

    params = {
        "q": query,
        "hl": "tr",
        "gl": "tr",
        "num": 20
    }

    try:

        response = requests.get(
            url,
            params=params,
            headers=HEADERS,
            timeout=20
        )

    except:

        return []

    if response.status_code != 200:
        return []

    soup_text = response.text

    results = []

    # Google'ın HTML yapısı değişebildiği için
    # genel linkleri buluyoruz.

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(
        soup_text,
        "html.parser"
    )

    for link in soup.select("a"):

        href = link.get(
            "href",
            ""
        )

        title = link.get_text(
            " ",
            strip=True
        )

        if not href:
            continue

        if not title:
            continue

        if not href.startswith("http"):
            continue

        # Google kendi linklerini alma
        if "google.com" in href:
            continue

        if not product_is_relevant(
            product,
            title
        ):
            continue

        # Fiyat bul

        price = extract_price(
            title
        )

        if price is None:

            # Link metninde fiyat yoksa
            # çevresindeki HTML metnini dene

            parent = link.parent

            if parent:

                text = parent.get_text(
                    " ",
                    strip=True
                )

                price = extract_price(
                    text
                )

        if price is None:
            continue

        results.append({

            "title": title,

            "price": price,

            "currency": "TRY",

            "seller": get_domain(
                href
            ),

            "url": href,

            "image": "",

            "rating": None,

            "rating_count": None,

            "condition": condition

        })

    return results


# =========================================================
# FİYAT ÇIKAR
# =========================================================

def extract_price(text):

    if not text:
        return None

    text = text.replace(
        "\xa0",
        " "
    )

    patterns = [

        r"(\d{1,3}(?:[.\s]\d{3})+(?:,\d{1,2})?)\s*(?:TL|₺)",

        r"(\d{3,7}(?:,\d{1,2})?)\s*(?:TL|₺)",

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

                number = float(
                    value
                )

                if (
                    number >= 10
                    and
                    number <= 10000000
                ):

                    return number

            except:
                pass

    return None


# =========================================================
# SHOPPING SONUÇLARINI DÖNÜŞTÜR
# =========================================================

def prepare_shopping(
    items,
    product
):

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

        if not title:
            continue

        if not product_is_relevant(
            product,
            title,
            p.get(
                "description",
                ""
            )
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
            price = float(price)
        except:
            continue

        if price <= 0:
            continue

        seller = p.get(
            "seller",
            "Bilinmeyen mağaza"
        )

        results.append({

            "title": title,

            "price": price,

            "currency": price_data.get(
                "currency",
                "TRY"
            ),

            "seller": seller,

            "url": p.get(
                "url",
                ""
            ),

            "image": (
                p.get(
                    "image_urls",
                    [""] 
                )[0]
                if p.get(
                    "image_urls",
                    []
                )
                else ""
            ),

            "rating": (
                p.get(
                    "rating",
                    {}
                ).get(
                    "average"
                )
                if isinstance(
                    p.get(
                        "rating",
                        {}
                    ),
                    dict
                )
                else None
            ),

            "rating_count": (
                p.get(
                    "rating",
                    {}
                ).get(
                    "count"
                )
                if isinstance(
                    p.get(
                        "rating",
                        {}
                    ),
                    dict
                )
                else None
            ),

            "condition": "Sıfır"

        })

    return results


# =========================================================
# TEKRARLARI TEMİZLE
# =========================================================

def remove_duplicates(
    products
):

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

    result = list(
        unique.values()
    )

    result.sort(
        key=lambda x: x["price"]
    )

    return result


# =========================================================
# ÜRÜN GÖSTER
# =========================================================

def show_product(
    product
):

    condition = product.get(
        "condition",
        "Sıfır"
    )

    if condition == "Sıfır":

        emoji = "🟢"

    elif condition == "İkinci El":

        emoji = "🟠"

    else:

        emoji = "🔵"


    col1, col2 = st.columns(
        [1, 4]
    )


    with col1:

        image = product.get(
            "image",
            ""
        )

        if image:

            try:

                st.image(
                    image,
                    width=140
                )

            except:
                pass


    with col2:

        st.subheader(
            product["title"]
        )

        st.markdown(
            f"## {format_price(product['price'], product['currency'])}"
        )

        st.write(
            f"🏪 **{product['seller']}**"
        )

        st.write(
            f"{emoji} **{condition}**"
        )


        rating = product.get(
            "rating"
        )

        rating_count = product.get(
            "rating_count"
        )

        if rating:

            rating_text = (
                f"⭐ {rating}"
            )

            if rating_count:

                rating_text += (
                    f" ({rating_count:,} oy)"
                )

            st.write(
                rating_text
            )


        if product.get("url"):

            st.link_button(
                "🛒 Mağazaya Git",
                product["url"]
            )


    st.divider()


# =========================================================
# ARAMA
# =========================================================

product_name = st.text_input(
    "🔎 Ürün adı",
    placeholder="Örn: Grundig Club BT Hoparlör"
)


search_button = st.button(
    "🔍 Fiyatları Ara",
    type="primary",
    use_container_width=True
)


# =========================================================
# ÇALIŞTIR
# =========================================================

if search_button:

    if not product_name.strip():

        st.warning(
            "Lütfen ürün adı yaz."
        )

        st.stop()


    product_name = product_name.strip()


    # =====================================================
    # SIFIR
    # =====================================================

    with st.spinner(
        "🟢 Sıfır ürünler aranıyor..."
    ):

        shopping_raw = search_shopping(
            product_name
        )

        new_products = prepare_shopping(
            shopping_raw,
            product_name
        )


    # =====================================================
    # İKİNCİ EL
    # =====================================================

    with st.spinner(
        "🟠 İkinci el ürünler aranıyor..."
    ):

        used_products = []

        used_queries = [

            f'"{product_name}" ikinci el fiyat TL',

            f'"{product_name}" 2.el fiyat TL',

            f'"{product_name}" site:letgo.com TL',

            f'"{product_name}" site:sahibinden.com TL'

        ]

        for query in used_queries:

            results = search_web(

                query,

                product_name,

                "İkinci El"

            )

            used_products.extend(
                results
            )


    # =====================================================
    # YENİLENMİŞ
    # =====================================================

    with st.spinner(
        "🔵 Yenilenmiş ürünler aranıyor..."
    ):

        refurbished_products = []

        refurbished_queries = [

            f'"{product_name}" yenilenmiş fiyat TL',

            f'"{product_name}" refurbished fiyat TL',

            f'"{product_name}" yenilenmiş site:hepsiburada.com',

            f'"{product_name}" yenilenmiş site:trendyol.com'

        ]

        for query in refurbished_queries:

            results = search_web(

                query,

                product_name,

                "Yenilenmiş"

            )

            refurbished_products.extend(
                results
            )


    # =====================================================
    # TEMİZLE
    # =====================================================

    new_products = remove_duplicates(
        new_products
    )

    used_products = remove_duplicates(
        used_products
    )

    refurbished_products = remove_duplicates(
        refurbished_products
    )


    # =====================================================
    # TÜM SONUÇLAR
    # =====================================================

    all_products = (

        new_products
        +
        used_products
        +
        refurbished_products

    )


    # =====================================================
    # SONUÇ YOK
    # =====================================================

    if not all_products:

        st.error(
            f'"{product_name}" için fiyat bulunamadı.'
        )

        st.stop()


    # =====================================================
    # EN UCUZ
    # =====================================================

    cheapest = min(
        all_products,
        key=lambda x: x["price"]
    )


    st.success(
        "🏆 En ucuz fiyat bulundu!"
    )


    st.subheader(
        "🏆 En Ucuz Fiyat"
    )


    st.write(
        f"### {cheapest['title']}"
    )

    st.markdown(
        f"# {format_price(cheapest['price'], cheapest['currency'])}"
    )

    st.write(
        f"🏪 **{cheapest['seller']}**"
    )

    st.write(
        f"📦 **{cheapest['condition']}**"
    )


    if cheapest.get("url"):

        st.link_button(
            "🛒 En Ucuz Mağazaya Git",
            cheapest["url"]
        )


    st.divider()


    # =====================================================
    # ÖZET
    # =====================================================

    st.subheader(
        "📊 Fiyat Özeti"
    )


    c1, c2, c3, c4 = st.columns(4)


    with c1:

        st.metric(
            "🟢 Sıfır",
            (
                format_price(
                    new_products[0]["price"],
                    new_products[0]["currency"]
                )
                if new_products
                else "Bulunamadı"
            )
        )


    with c2:

        st.metric(
            "🟠 İkinci El",
            (
                format_price(
                    used_products[0]["price"],
                    used_products[0]["currency"]
                )
                if used_products
                else "Bulunamadı"
            )
        )


    with c3:

        st.metric(
            "🔵 Yenilenmiş",
            (
                format_price(
                    refurbished_products[0]["price"],
                    refurbished_products[0]["currency"]
                )
                if refurbished_products
                else "Bulunamadı"
            )
        )


    with c4:

        st.metric(
            "🔎 Toplam",
            len(all_products)
        )


    st.divider()


    # =====================================================
    # SIFIR
    # =====================================================

    st.header(
        "🟢 Sıfır Ürünler"
    )


    if new_products:

        for product in new_products[:20]:

            show_product(
                product
            )

    else:

        st.info(
            "Bu aramada sıfır ürün bulunamadı."
        )


    # =====================================================
    # İKİNCİ EL
    # =====================================================

    st.header(
        "🟠 İkinci El"
    )


    if used_products:

        for product in used_products[:20]:

            show_product(
                product
            )

    else:

        st.info(
            "Bu aramada ikinci el ürün bulunamadı."
        )


    # =====================================================
    # YENİLENMİŞ
    # =====================================================

    st.header(
        "🔵 Yenilenmiş"
    )


    if refurbished_products:

        for product in refurbished_products[:20]:

            show_product(
                product
            )

    else:

        st.info(
            "Bu aramada yenilenmiş ürün bulunamadı."
        )


    # =====================================================
    # FİYAT FARKI
    # =====================================================

    prices = [

        product["price"]

        for product in all_products

        if product["currency"] == cheapest["currency"]

    ]


    if len(prices) >= 2:

        lowest = min(prices)

        highest = max(prices)

        difference = (
            highest - lowest
        )


        st.divider()

        st.subheader(
            "💰 Fiyat Farkı"
        )


        st.write(

            f"En ucuz: **"
            f"{format_price(lowest, cheapest['currency'])}"
            f"**"

        )

        st.write(

            f"En pahalı: **"
            f"{format_price(highest, cheapest['currency'])}"
            f"**"

        )

        st.write(

            f"Aradaki fark: **"
            f"{format_price(difference, cheapest['currency'])}"
            f"**"

        )


    st.success(
        f"✅ Toplam {len(all_products)} fiyat sonucu bulundu."
    )
