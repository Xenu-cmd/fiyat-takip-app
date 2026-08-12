import streamlit as st
import requests

st.set_page_config(page_title="Canlı Fiyat Takip", layout="wide")

st.title("🔍 Canlı Fiyat Takip & Karşılaştırma")
st.caption("Doğrudan Google API altyapısıyla canlı sonuçlar.")

search_query = st.text_input("Aramak istediğiniz ürünün adı:", placeholder="Örn: Grundig Club")

def search_prices_google(query):
    # Google CS API Endpoint (Public)
    url = f"https://html.duckduckgo.com/html/"
    # Doğrudan mağaza araması parametresi
    params = {"q": f"{query} fiyatı site:trendyol.com OR site:hepsiburada.com OR site:akakce.com OR site:cimri.com"}
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    
    results = []
    try:
        # Arama motoru API yerine DuckDuckGo Lite kullanıyoruz
        res = requests.get(f"https://lite.duckduckgo.com/lite/", params={"q": f"{query} fiyatı satın al"}, headers=headers, timeout=10)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(res.text, "html.parser")
        
        # Sonuç tablolarını tara
        for tr in soup.find_all("tr"):
            link_tag = tr.find("a", class_="result-link")
            snippet = tr.find_next_sibling("tr")
            if link_tag:
                title = link_tag.get_text(strip=True)
                link = link_tag["href"]
                desc = snippet.get_text(strip=True) if snippet else ""
                results.append({"Urun": title, "Detay": desc, "Link": link})
                if len(results) >= 8:
                    break
    except Exception as e:
        st.error(f"Hata: {e}")
        
    return results

if st.button("Fiyatları Canlı Ara ve Karşılaştır"):
    if search_query:
        with st.spinner("Sonuçlar getiriliyor..."):
            data = search_prices_google(search_query)
            if data:
                st.success(f"'{search_query}' için bulunan canlı sonuçlar:")
                for item in data:
                    st.write(f"### {item['Urun']}")
                    st.write(item['Detay'])
                    st.markdown(f"[👉 Ürüne / Mağazaya Git]({item['Link']})")
                    st.divider()
            else:
                st.warning("Sonuç bulunamadı.")
    else:
        st.info("Lütfen bir ürün adı girin.")
