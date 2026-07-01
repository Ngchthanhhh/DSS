import streamlit as st

st.set_page_config(page_title="Khám Bệnh Streamlit", page_icon="🏥", layout="centered")

st.title("🏥 Trạm y tế Streamlit")
st.divider()

st.success("✅ NẾU SẾP ĐỌC ĐƯỢC DÒNG NÀY, TỨC LÀ STREAMLIT VẪN SỐNG VÀ HOẠT ĐỘNG HOÀN HẢO!")

st.info("💡 Nếu màn hình hiển thị được dòng chữ này, chứng tỏ lỗi màn hình xám lúc nãy KHÔNG PHẢI do Streamlit, mà là do các thư viện AI (Langchain, ChromaDB) bên trong file app.py gây kẹt luồng render.")

# Nút bấm test logic
if st.button("Bóp cò Test Logic UI", type="primary"):
    st.balloons()
    st.write("🎉 Nút bấm hoạt động mượt mà! WebSocket không bị nghẽn.")