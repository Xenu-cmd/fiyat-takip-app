import streamlit as st
import requests
from bs4 import BeautifulSoup
import urllib.parse

st.set_page_config(page_title="Canlı Fiyat Takip", layout="wide")

st.title("🔍 Canlı Fiyat Takip & Karşılaştırma")
st.caption("E-ticaret platformlarından fiyatları canlı çekin.")

search_query = st.text_input("Aramak istediğiniz ürünün adı:", placeholder="Örn: Grundig Club")

def search_google_shopping(query):
    results = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    encoded_query = urllib.parse.quote(query)
    url = f"https://www.google.com/search?q={encoded_query}&tbm=shop"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            cards = soup.select(".sh-dgr__content, .sh-pr__target")
            
            for card in cards[:10]:
                title_elem = card.select_one("h3, .XiyJu")
                price_elem = card.select_one(".a83U2c, .off36e, .1vA1P")
                link_elem = card.select_one("a")
                
                if title_elem and price_elem:
                    title = title_elem.get_text(strip=True)
                    price = price_elem.get_text(strip=True)
                    link = "https://www.google.com" + link_elem["href"] if link_elem and link_elem.get("href", "").startswith("/") else (link_elem["href"] if link_elem else "#")
                    results.append({"Urun": title, "Fiyat": price, "Link": link})
    except Exception as e:
        st.error(f"Arama sırasında bir hata oluştu: {e}")
    
    return results

if st.button("Fiyatları Canlı Ara ve Karşılaştır"):
    if search_query:
        with st.spinner("Fiyatlar getiriliyor..."):
            data = search_google_shopping(search_query)
            if data:
                st.success(f"'{search_query}' için sonuçlar bulundu!")
                for item in data:
                    col1, col2, col3 = st.columns([3, 1, 1])
                    col1.write(f"**{item['Urun']}**")
                    col2.write(f"🟢 **{item['Fiyat']}**")
                    col3.markdown(f"[Satın Al / İncele]({item['Link']})")
                    st.divider()
            else:
                st.warning("Sonuç bulunamadı veya site erişimi engelledi. Lütfen farklı bir arama terimi deneyin.")
    else:
        st.info("Lütfen bir ürün adı girin.")
