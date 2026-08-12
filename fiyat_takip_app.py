import streamlit as st
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re

st.set_page_config(page_title="Canlı Fiyat Takip & Karşılaştırma Botu", layout="wide")

st.title("🔍 Canlı Fiyat Takip & Karşılaştırma Botu")
st.caption("E-ticaret siteleri ve 2. el platformlarından canlı fiyatları çekin ve karşılaştırın.")

col_search, col_file = st.columns([2, 1])

with col_search:
    search_query = st.text_input("Aramak istediğiniz ürünün adı:", placeholder="Örn: Grundig Club")

with col_file:
    uploaded_file = st.file_uploader("Veya ürün resmi yükleyin:", type=["jpg", "png", "jpeg"])

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
}

def clean_price(price_str):
    """Fiyat metnini temizler ve sayıya dönüştürür."""
    if not price_str:
        return None
    cleaned = re.sub(r"[^\d,\.]", "", price_str)
    if not cleaned:
        return None
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None

def fetch_live_prices(query):
    """Canlı arama motoru ve e-ticaret/2. el sonuçlarını tarar."""
    results = []
    encoded_query = urllib.parse.quote(f"{query} fiyatı satılık")
    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            snippets = soup.find_all("div", class_="result__body")
            
            for item in snippets:
                title_elem = item.find("a", class_="result__url")
                snippet_elem = item.find("a", class_="result__snippet")
                if not title_elem or not snippet_elem:
                    continue
                
                link = title_elem.get("href", "")
                snippet_text = snippet_elem.get_text()
                title_text = item.find("h2", class_="result__title").get_text(strip=True) if item.find("h2", class_="result__title") else ""
                
                price_match = re.search(r"(\d+[\.\,]?\d*)\s*(TL|TL|₺|EUR|USD)", snippet_text, re.IGNORECASE)
                if price_match:
                    price_val = clean_price(price_match.group(1))
                    if price_val and price_val > 0:
                        is_second_hand = any(keyword in (title_text + snippet_text + link).lower() 
                                             for keyword in ["sahibinden", "letgo", "dolap", "gardrops", "2.el", "ikinci el", "kullanılmış", "temiz"])
                        
                        platform = "2. El Platformu" if is_second_hand else "E-Ticaret Sitesi"
                        if "sahibinden" in link.lower(): platform = "Sahibinden"
                        elif "letgo" in link.lower(): platform = "Letgo"
                        elif "dolap" in link.lower(): platform = "Dolap"
                        elif "trendyol" in link.lower(): platform = "Trendyol"
                        elif "hepsiburada" in link.lower(): platform = "Hepsiburada"
                        elif "n11" in link.lower(): platform = "N11"
                        elif "akakce" in link.lower(): platform = "Akakçe"
                        
                        results.append({
                            "platform": platform,
                            "durum": "2. El" if is_second_hand else "Sıfır",
                            "title": title_text[:80] + "..." if len(title_text) > 80 else title_text,
                            "fiyat": price_val,
                            "link": link
                        })
    except Exception as e:
        st.error(f"Arama yapılırken hata oluştu: {e}")
        
    return results

if st.button("Fiyatları Canlı Ara ve Karşılaştır", type="primary"):
    if not search_query and not uploaded_file:
        st.warning("Lütfen bir ürün adı yazın veya bir resim yükleyin.")
    else:
        query_text = search_query if search_query else "Görsel Ürünü"
            
        with st.spinner(f"'{query_text}' için canlı fiyat verileri taranıyor..."):
            live_results = fetch_live_prices(query_text)
            
            if not live_results:
                st.warning("Doğrudan fiyat verisi çekilemedi. Arama terimini daha net yazarak tekrar deneyin.")
            else:
                sorted_data = sorted(live_results, key=lambda x: x["fiyat"])
                
                ikinci_el = [x for x in sorted_data if x["durum"] == "2. El"]
                sifir = [x for x in sorted_data if x["durum"] == "Sıfır"]
                
                c1, c2 = st.columns(2)
                if ikinci_el:
                    best_2el = ikinci_el[0]
                    c1.success(f"🏆 **En Ucuz 2. El:** {best_2el['fiyat']:,.2f} TL ({best_2el['platform']})\n\n[{best_2el['title']}]({best_2el['link']})")
                else:
                    c1.info("2. el kategorisinde fiyat bulunamadı.")
                    
                if sifir:
                    best_sifir = sifir[0]
                    c2.info(f"🏷️ **En Ucuz Sıfır:** {best_sifir['fiyat']:,.2f} TL ({best_sifir['platform']})\n\n[{best_sifir['title']}]({best_sifir['link']})")
                else:
                    c2.info("Sıfır kategorisinde fiyat bulunamadı.")
                    
                st.divider()
                st.subheader(f"📋 Bulunan Canlı Fiyat Listesi ({len(sorted_data)} Sonuç)")
                
                table_data = []
                for item in sorted_data:
                    table_data.append({
                        "Platform": item["platform"],
                        "Durum": item["durum"],
                        "İlan / Ürün Başlığı": item["title"],
                        "Fiyat": f"{item['fiyat']:,.2f} TL",
                        "Bağlantı": item["link"]
                    })
                    
                st.dataframe(table_data, use_container_width=True)
