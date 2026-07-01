import streamlit as st
import streamlit.components.v1 as components
import sys
import os

# 🛠 CẮM ỐNG DẪN LLM ROUTER
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from llm_router import generate_with_fallback
except ImportError:
    st.error("⚠️ Không tìm thấy file `llm_router.py`. Vui lòng kiểm tra lại thư mục gốc.")

# Cấu hình UI
st.set_page_config(page_title="AI Strategy Advisor", page_icon="🧠", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 1. HACK GIAO DIỆN: FULL MÀN HÌNH + ĐÁNH THỨC ROBOT
# ==========================================
st.markdown("""
    <style>
        /* ĐƯA ROBOT TRỞ LẠI TRÀN VIỀN 100% VÀ MỞ TƯƠNG TÁC */
        iframe {
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            width: 100vw !important;
            height: 100vh !important;
            z-index: -1 !important; 
            border: none !important;
            pointer-events: auto !important; /* 👈 CHÌA KHÓA Ở ĐÂY: Đánh thức Robot! */
        }
        
        /* MA THUẬT: Biến Container của Streamlit thành "Không Khí" để chuột đâm xuyên qua */
        .block-container {
            z-index: 10 !important;
            background: transparent !important;
            padding-top: 2rem !important;
            max-width: 100% !important;
            pointer-events: none !important; 
        }

        header { background: transparent !important; }

        /* Bơm lại khả năng Click chuột cho riêng cái cột bên phải (Cột Chat) */
        [data-testid="column"]:nth-of-type(2), 
        .stChatMessage, 
        .stChatFloatingInputContainer,
        .stMarkdown {
            pointer-events: auto !important;
        }

        /* Khung chat tối, chữ trắng tinh nét căng */
        .stChatMessage {
            background: rgba(15, 15, 15, 0.85) !important;
            backdrop-filter: blur(20px) !important;
            -webkit-backdrop-filter: blur(20px) !important;
            border: 1px solid rgba(255, 255, 255, 0.15) !important;
            border-radius: 12px !important;
            padding: 15px !important;
            margin-bottom: 15px !important;
        }
        
        .stChatMessage p, .stChatMessage li, .stChatMessage span {
            color: #FFFFFF !important;
            font-size: 1.05rem !important;
            text-shadow: none !important;
            line-height: 1.6 !important;
        }
        
        .stChatFloatingInputContainer {
            background: rgba(5, 5, 5, 0.95) !important; 
            backdrop-filter: blur(20px) !important;
            border-top: 1px solid rgba(255, 255, 255, 0.2) !important;
            padding-bottom: 15px !important;
        }
        
        h1, h2, h3 {
            text-shadow: 0px 2px 5px rgba(0,0,0,0.8);
        }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. RENDER CON ROBOT 3D (CHẠY NGẦM LÀM NỀN)
# ==========================================
spline_html = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body, html { margin: 0; padding: 0; width: 100%; height: 100%; background-color: #000; overflow: hidden; }
        spline-viewer { width: 100%; height: 100%; }
    </style>
    <script type="module" src="https://unpkg.com/@splinetool/viewer@1.0.94/build/spline-viewer.js"></script>
</head>
<body>
    <spline-viewer url="https://prod.spline.design/kZDDjO5HuC9GJUM2/scene.splinecode"></spline-viewer>
</body>
</html>
"""
components.html(spline_html, height=100) 

# ==========================================
# 3. BỐ CỤC CHAT (NẰM Ở CỘT BÊN PHẢI)
# ==========================================
col_empty, col_chat = st.columns([1.5, 1])

with col_chat:
    st.markdown("<h1 style='text-align: right; color: white;'>🤖 C-Suite Terminal</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: right; color: #00E396;'>RAG • Tool Calling • LLM Router</p>", unsafe_allow_html=True)
    st.write("") 
    
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant", 
                "content": "👋 **Hệ thống OmniSense AI đã trực tuyến.**\n\nTôi là bộ não LLM đang lắng nghe ngài. Ngài cần truy vấn số liệu, tra cứu cẩm nang rủi ro hay ra lệnh thực thi tác vụ gì hôm nay?"
            }
        ]

    chat_container = st.container(height=500)
    
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if prompt := st.chat_input("Nhập lệnh cho C-Suite AI..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                status_placeholder = st.empty()
                status_placeholder.info("🧠 Đang kết nối LLM Router & Phân tích ngữ cảnh...")

                # [PLACEHOLDER] Da luoc bo noi dung system_instruction (persona,
                # phong cach, quy tac phan hoi) va cach ghep full_prompt vi ly
                # do bao mat chat xam. Ban day du: xay dung system_instruction
                # + goi generate_with_fallback(full_prompt).
                try:
                    raise NotImplementedError("Xem ban day du o source goc cua chu repo.")
                except Exception as e:
                    response_content = f"🚨 LLM Router báo lỗi kết nối: {e}"
                
                status_placeholder.empty()
                st.markdown(response_content)
        
        st.session_state.messages.append({"role": "assistant", "content": response_content})