import streamlit as st
import json
import os
import streamlit.components.v1 as components

# =========================================================
# 🎛️ BỘ LỌC CSS ÉP NỀN TRONG SUỐT VÀ LỚP PHỦ SIÊU ĐẬM NEON
# =========================================================
def inject_background_css():
    st.markdown("""
        <style>
            /* 1. Ép toàn bộ các tầng giao diện chính của Streamlit thành trong suốt */
            .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stMain"] {
                background: transparent !important;
                background-color: transparent !important;
            }

            /* 2. Định dạng khung nền cố định vạn năng tràn màn hình */
            .absolute-bg-master {
                position: fixed !important;
                top: 0 !important;
                left: 0 !important;
                width: 100vw !important;
                height: 100vh !important;
                z-index: -9999 !important; /* Dìm sâu dưới đáy chữ nghĩa */
                pointer-events: none !important; /* Chuột click xuyên qua */
                overflow: hidden !important;
                background-color: #0E1117 !important; /* Màu nền tối gốc giúp đỡ bị chớp trắng */
            }
            .absolute-bg-master iframe {
                width: 100vw !important;
                height: 100vh !important;
                border: none !important;
            }

            /* 🌟 LỚP PHỦ SIÊU ĐẬM NEON (TỐI ƯU GPU - GIẢM LAG GIẬT CHUYỂN TRANG)
               Thay vì dùng filter, ta dùng lớp phủ hòa trộn màu giúp tăng độ rực cực nhẹ */
            .ultra-neon-glow-overlay {
                position: fixed !important;
                top: 0 !important;
                left: 0 !important;
                width: 100vw !important;
                height: 100vh !important;
                background: rgba(0, 191, 255, 0.05) !important; /* Phủ nhẹ lớp cyan tăng sáng */
                mix-blend-mode: screen !important; /* Hòa trộn làm nổi bật vệt neon sáng */
                z-index: -9998 !important;
                pointer-events: none !important;
            }

            /* 🌟 ĐẶC TRỊ CỤC KHỐI VUÔNG TRẮNG TRÊN MENU SIDEBAR
               Truy tìm đúng thẻ bọc component HTML của Streamlit và ép tàng hình tuyệt đối */
            div[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > .element-container:has(iframe[title="streamlit.components.v1.html"]),
            iframe[title="streamlit.components.v1.html"] {
                position: absolute !important;
                width: 0 !important;
                height: 0 !important;
                margin: 0 !important;
                padding: 0 !important;
                opacity: 0 !important;
                pointer-events: none !important;
                visibility: hidden !important;
                display: none !important;
            }

            /* Làm mờ nhẹ Sidebar theo phong cách kính mờ cao cấp */
            [data-testid="stSidebar"] {
                background-color: rgba(15, 17, 26, 0.75) !important;
                backdrop-filter: blur(12px) !important;
                border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
            }
        </style>
    """, unsafe_allow_html=True)

# Hàm JavaScript bốc đầu phần tử ra khỏi luồng Streamlit đưa vào Body gốc
def dynamic_move_to_body(element_id: str):
    st.markdown(f"""
        <script>
            (function() {{
                function doMove() {{
                    const el = window.parent.document.getElementById('{element_id}');
                    if (el && el.parentElement !== window.parent.document.body) {{
                        window.parent.document.body.appendChild(el);
                    }}
                }}
                if (window.parent.document.readyState === 'loading') {{
                    window.parent.document.addEventListener('DOMContentLoaded', doMove);
                }} else {{
                    doMove();
                }}
                setTimeout(doMove, 100);
                setTimeout(doMove, 300);
            }})();
        </script>
    """, unsafe_allow_html=True)

# ==========================================
# 1. HÀM RENDER TRANG CHỦ APP.PY (ĐÃ DẸP BỎ NỀN ĐỘNG)
# ==========================================
def render_full_wave():
    inject_background_css()
    st.markdown("""
        <style>
            .stApp { background-color: #0E1117 !important; }
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. HÀM RENDER SPLINE (CHO 3 TRANG CON)
# ==========================================
def render_full_risk():
    inject_background_css()
    # Trang 1: Vệt sáng chuyển động siêu đậm + lớp phủ rực màu
    st.markdown("""
        <div id="master-risk-bg" class="absolute-bg-master">
            <iframe src="https://my.spline.design/motiontrails-FVzrLZW5TuaX8beAqPmQNL5D/"></iframe>
        </div>
        <div class="ultra-neon-glow-overlay"></div>
    """, unsafe_allow_html=True)
    dynamic_move_to_body("master-risk-bg")

def render_full_churn():
    inject_background_css()
    # Trang 2: Khối chip 3D rực rỡ đậm đà
    st.markdown("""
        <div id="master-churn-bg" class="absolute-bg-master">
            <iframe src="https://my.spline.design/chips-lleItpGyDggw1csfxLjejdy7/"></iframe>
        </div>
        <div class="ultra-neon-glow-overlay"></div>
    """, unsafe_allow_html=True)
    dynamic_move_to_body("master-churn-bg")

def render_full_seller():
    inject_background_css()
    # Trang 3: Vòng tròn hạt neon mới siêu rực rỡ, đậm đà hút mắt
    st.markdown("""
        <div id="master-seller-bg" class="absolute-bg-master">
            <iframe src="https://my.spline.design/trails-1rktGkz11NmGP87Z2VYZFXqQ/"></iframe>
        </div>
        <div class="ultra-neon-glow-overlay" style="background: rgba(0, 255, 127, 0.05) !important;"></div>
    """, unsafe_allow_html=True)
    dynamic_move_to_body("master-seller-bg")

def render_full_app():
    inject_background_css()
    # Trang App chính: Clarity Stream
    st.markdown("""
        <div id="master-app-bg" class="absolute-bg-master">
            <iframe src="https://my.spline.design/claritystream-B9aVsi3WgbepZvpKmXSggnwh/"></iframe>
        </div>
        <div class="ultra-neon-glow-overlay"></div>
    """, unsafe_allow_html=True)
    dynamic_move_to_body("master-app-bg")