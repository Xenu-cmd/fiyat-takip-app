import streamlit as st
from duckduckgo_search import DDGS

st.set_page_config(page_title="Canlı Fiyat Takip", layout="wide")

st.title("🔍 Canlı Fiyat Takip & Karşılaştırma")
st.caption("E-ticaret sitelerinden canlı fiyat sonuçlarını çekin.")

search_query = st.text_input("Aramak istediğiniz ürünün adı:", placeholder="Örn: Grundig Club")

def search_prices(query):
    results = []
    try:
        with DDGS() as ddgs:
            # Sadece alışveriş ve e-ticaret sitelerini hedefler
            focused_query = f"{query} (site:akakce.com OR site:cimri.com OR site:trendyol.com OR site:hepsiburada.com OR site:n11.com OR site:pazarama.com)"
            search_results = ddgs.text(focused_query, region="tr-tr", max_results=10)
            
            for r in search_results:
                results.append({
                    "Urun": r.get("title", "Başlıksız Ürün"),
                    "Aciklama": r.get("body", ""),
                    "Link": r.get("href", "#")
                })
    except Exception as e:
        st.error(f"Arama sırasında bir hata oluştu: {e}")
    return results

if st.button("Fiyatları Canlı Ara ve Karşılaştır"):
    if search_query:
        with st.spinner("E-ticaret siteleri taranıyor..."):
            data = search_prices(search_query)
            if data:
                st.success(f"'{search_query}' için mağaza sonuçları:")
                for item in data:
                    st.subheader(item['Urun'])
                    st.write(item['Aciklama'])
                    st.markdown(f"[👉 Mağazaya / Fiyata Git]({item['Link']})")
                    st.divider()
            else:
                st.warning("Sonuç bulunamadı. Lütfen ürün adını kontrol edin.")
    else:
        st.info("Lütfen bir ürün adı girin.")
