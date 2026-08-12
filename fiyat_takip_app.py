import streamlit as st
import requests

st.set_page_config(page_title="Canlı Fiyat Takip", layout="wide")

st.title("🔍 Canlı Fiyat Takip & Karşılaştırma")
st.caption("Trendyol üzerinden doğrudan ürün ve fiyat verilerini çeker.")

search_query = st.text_input("Aramak istediğiniz ürünün adı:", placeholder="Örn: Grundig Club")

def get_trendyol_products(query):
    # Trendyol'un arama servisi
    url = f"https://public.trendyol.com/discovery-web-searchgw-service/v2/api/infinite-scroll/sr?q={query}&culture=tr-TR&storefrontId=1"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    products = []
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            result_list = data.get("result", {}).get("products", [])
            
            for item in result_list[:10]:
                brand = item.get("brand", {}).get("name", "")
                name = item.get("name", "")
                full_name = f"{brand} {name}".strip()
                
                # Fiyat bilgisi alma
                price_info = item.get("price", {})
                price = price_info.get("discountedPrice") or price_info.get("sellingPrice") or 0
                
                # Ürün linki
                link_path = item.get("url", "")
                full_link = f"https://www.trendyol.com{link_path}" if link_path else "#"
                
                products.append({
                    "Urun": full_name,
                    "Fiyat": f"{price} TL",
                    "Link": full_link
                })
    except Exception as e:
        st.error(f"Veri çekilirken hata oluştu: {e}")
        
    return products

if st.button("Fiyatları Canlı Ara ve Karşılaştır"):
    if search_query:
        with st.spinner("Trendyol verileri çekiliyor..."):
            items = get_trendyol_products(search_query)
            if items:
                st.success(f"'{search_query}' için bulunan canlı Trendyol sonuçları:")
                for item in items:
                    col1, col2, col3 = st.columns([3, 1, 1])
                    col1.write(f"**{item['Urun']}**")
                    col2.write(f"🏷️ **{item['Fiyat']}**")
                    col3.markdown(f"[👉 Ürüne Git]({item['Link']})")
                    st.divider()
            else:
                st.warning("Ürün bulunamadı veya erişim sağlayan API yanıt vermedi.")
    else:
        st.info("Lütfen bir ürün adı girin.")
