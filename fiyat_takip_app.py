import streamlit as st
from duckduckgo_search import DDGS

st.set_page_config(page_title="Canlı Fiyat Takip", layout="wide")

st.title("🔍 Canlı Fiyat Takip & Karşılaştırma")
st.caption("Arama motoru üzerinden canlı fiyat ve ürün bağlantılarını çekin.")

search_query = st.text_input("Aramak istediğiniz ürünün adı:", placeholder="Örn: Grundig Club")

def search_prices(query):
    results = []
    try:
        with DDGS() as ddgs:
            # Fiyat odaklı canlı web araması yapar
            search_results = ddgs.text(f"{query} fiyatı satın al", region="tr-tr", max_results=10)
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
        with st.spinner("Canlı veriler çekiliyor..."):
            data = search_prices(search_query)
            if data:
                st.success(f"'{search_query}' için bulunan canlı sonuçlar:")
                for item in data:
                    st.subheader(item['Urun'])
                    st.write(item['Aciklama'])
                    st.markdown(f"[👉 Ürüne / Mağazaya Git]({item['Link']})")
                    st.divider()
            else:
                st.warning("Sonuç bulunamadı. Lütfen farklı bir arama terimi deneyin.")
    else:
        st.info("Lütfen bir ürün adı girin.")
