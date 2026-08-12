import streamlit as st
import requests
from bs4 import BeautifulSoup
import urllib.parse

st.set_page_config(page_title="Canlı Fiyat Takip", layout="wide")

st.title("🔍 Canlı Fiyat Takip & Karşılaştırma")
st.caption("Üye olmadan ve API anahtarı kullanmadan canlı fiyat arayın.")

search_query = st.text_input("Aramak istediğiniz ürünün adı:", placeholder="Örn: Grundig Club")

def search_no_api(query):
    # DuckDuckGo HTML sürümü üzerinden doğrudan mağaza sonuçlarını çeker
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
    }
    
    # Sadece Türkiye e-ticaret sitelerinde arama yapar
    target_query = f"{query} fiyatı (site:akakce.com OR site:trendyol.com OR site:hepsiburada.com OR site:n11.com OR site:pazarama.com)"
    encoded_query = urllib.parse.quote(target_query)
    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
    
    results = []
    try:
        response = requests.post(
            "https://html.duckduckgo.com/html/", 
            data={"q": target_query}, 
            headers=headers, 
            timeout=10
        )
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            elements = soup.find_all("a", class_="result__snippet")
            
            for elem in elements[:10]:
                title = elem.parent.parent.find("a", class_="result__a").get_text(strip=True) if elem.parent.parent.find("a", class_="result__a") else "Ürün"
                link = elem.parent.parent.find("a", class_="result__a")["href"]
                snippet = elem.get_text(strip=True)
                
                results.append({
                    "Urun": title,
                    "Detay": snippet,
                    "Link": link
                })
    except Exception as e:
        st.error(f"Arama hatası: {e}")
        
    return results

if st.button("Fiyatları Canlı Ara ve Karşılaştır"):
    if search_query:
        with st.spinner("Canlı mağaza verileri taranıyor..."):
            items = search_no_api(search_query)
            if items:
                st.success(f"'{search_query}' için bulunan canlı mağaza bağlantıları:")
                for item in items:
                    st.subheader(item['Urun'])
                    st.write(item['Detay'])
                    st.markdown(f"[👉 Fiyata / Mağazaya Git]({item['Link']})")
                    st.divider()
            else:
                st.warning("Sonuç bulunamadı. Lütfen ürün adını değiştirip tekrar deneyin.")
    else:
        st.info("Lütfen bir ürün adı girin.")
