import ui_utils
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.graph_objects as go
import redis
import json
import os
import re
from langchain_openai import ChatOpenAI
# from streamlit_autorefresh import st_autorefresh 
from dotenv import load_dotenv
from streamlit_lottie import st_lottie  # <-- Đã thêm thư viện hỗ trợ Lottie

load_dotenv()

st.set_page_config(page_title="OmniSense C-Suite", page_icon="🌐", layout="wide")

# 🛠 KÍCH HOẠT AUTO-REFRESH MỖI 10 GIÂY
# with st.sidebar:
#     st_autorefresh(interval=10000, limit=None, key="data_refresh")

@st.cache_resource
def init_connection():
    return create_engine("postgresql://dss_user:CHANGE_ME_PASSWORD@postgres_db:5432/omnisense")

engine = init_connection()

@st.cache_resource
def get_redis():
    try:
        r = redis.Redis(host='redis_cache', port=6379, db=0, decode_responses=True)
        r.ping()
        return r
    except Exception:
        return None

r = get_redis()

st.title("🌐 OmniSense: C-Suite Command Center")
st.markdown("Hệ thống Hỗ trợ Ra Quyết định & Quản trị Rủi ro Thương mại điện tử (Multi-Agent AI)")
st.divider()
ui_utils.render_full_app()


@st.cache_data(ttl=300)
def get_kpis_and_trends():
    raw_conn = engine.raw_connection()
    try:
        rev_raw = pd.read_sql("SELECT SUM(payment_value) as total FROM order_payments", raw_conn).iloc[0]['total']
        ords_raw = pd.read_sql("SELECT COUNT(order_id) as total FROM orders", raw_conn).iloc[0]['total']
        cust_raw = pd.read_sql("SELECT COUNT(DISTINCT customer_unique_id) as total FROM customers", raw_conn).iloc[0]['total']

        mom_query = """
            SELECT TO_CHAR(o.order_purchase_timestamp, 'YYYY-MM') as month, 
                   SUM(p.payment_value) as revenue,
                   COUNT(DISTINCT o.order_id) as orders,
                   COUNT(DISTINCT c.customer_unique_id) as customers
            FROM orders o JOIN order_payments p ON o.order_id = p.order_id JOIN customers c ON o.customer_id = c.customer_id
            WHERE o.order_status = 'delivered' GROUP BY month ORDER BY month DESC LIMIT 2
        """
        df_mom = pd.read_sql(mom_query, raw_conn)
    finally:
        raw_conn.close()

    if len(df_mom) == 2:
        rev_delta = ((df_mom.iloc[0]['revenue'] - df_mom.iloc[1]['revenue']) / df_mom.iloc[1]['revenue']) * 100
        ord_delta = ((df_mom.iloc[0]['orders'] - df_mom.iloc[1]['orders']) / df_mom.iloc[1]['orders']) * 100
        cust_delta = ((df_mom.iloc[0]['customers'] - df_mom.iloc[1]['customers']) / df_mom.iloc[1]['customers']) * 100
    else:
        rev_delta = ord_delta = cust_delta = 0.0

    return float(rev_raw), int(ords_raw), int(cust_raw), rev_delta, ord_delta, cust_delta

rev, ords, custs, rev_delta, ord_delta, cust_delta = get_kpis_and_trends()

col1, col2, col3 = st.columns(3)
vnd_revenue = rev * 4500
col1.metric(label="💰 Tổng Doanh Thu", value=f"${rev:,.2f} BRL", delta=f"≈ {vnd_revenue:,.0f} VNĐ ({rev_delta:.2f}% MoM)")
col2.metric(label="📦 Tổng Đơn Hàng", value=f"{ords:,}", delta=f"{ord_delta:.2f}% MoM")
col3.metric(label="👥 Tổng Khách Hàng", value=f"{custs:,}", delta=f"{cust_delta:.2f}% MoM")
st.divider()

st.subheader("📊 Phân tích Tổng quan Nền tảng")

@st.cache_data(ttl=300)
def get_chart_data():
    raw_conn = engine.raw_connection()
    try:
        df_trend = pd.read_sql("""
            SELECT TO_CHAR(o.order_purchase_timestamp, 'YYYY-MM') as month, SUM(p.payment_value) as raw_revenue
            FROM orders o JOIN order_payments p ON o.order_id = p.order_id
            WHERE o.order_status = 'delivered' GROUP BY month ORDER BY month
        """, raw_conn)

        df_cat = pd.read_sql("""
            SELECT t.product_category_name_english as category, COUNT(i.order_item_id) as total_sold
            FROM order_items i JOIN products p ON i.product_id = p.product_id
            JOIN category_translation t ON TRIM(p.product_category_name) = TRIM(t.product_category_name)
            GROUP BY category ORDER BY total_sold DESC LIMIT 10
        """, raw_conn)
        
        df_status = pd.read_sql("SELECT order_status, COUNT(order_id) as total FROM orders GROUP BY order_status", raw_conn)
    finally:
        raw_conn.close()

    df_cat['category'] = df_cat['category'].str.replace('_', ' ').str.title()
    df_cat = df_cat.sort_values('total_sold', ascending=True)
    return df_trend, df_cat, df_status

df_trend, df_cat, df_status = get_chart_data()

col_chart1, col_chart2 = st.columns([2, 1])
with col_chart1:
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=df_trend['month'].tolist(), y=(df_trend['raw_revenue'].astype(float) / 1000000.0).tolist(),
        mode='lines+markers', line=dict(color='#00E396', width=4), marker=dict(size=8, color='#008FFB')
    ))
    fig_trend.update_layout(title="📈 Xu hướng Doanh thu theo tháng", xaxis_title="Tháng", yaxis_title="Doanh thu (Triệu BRL)")
    st.plotly_chart(fig_trend, use_container_width=True)

with col_chart2:
    fig_status = go.Figure(data=[go.Pie(
        labels=df_status['order_status'].astype(str).tolist(), values=df_status['total'].astype(int).tolist(),
        hole=0.75, marker=dict(colors=['#008FFB', '#FF4560', '#00E396', '#FEB019', '#775DD0'])
    )])
    fig_status.update_layout(title_text="📦 Trạng thái Đơn hàng", annotations=[dict(text='Status', x=0.5, y=0.5, font_size=16, showarrow=False)])
    fig_status.update_traces(textposition='inside', textinfo='percent')
    st.plotly_chart(fig_status, use_container_width=True)

fig_cat = go.Figure(go.Bar(
    x=df_cat['total_sold'].astype(int).tolist(), y=df_cat['category'].astype(str).tolist(),
    orientation='h', marker=dict(color=df_cat['total_sold'].astype(int).tolist(), colorscale=[[0, '#64B5F6'], [1, '#0D47A1']], showscale=False)
))
fig_cat.update_layout(title="🏆 Top 10 Danh mục Bán chạy nhất", xaxis_title="Số lượng bán ra (Sản phẩm)", yaxis_title="Danh mục", xaxis=dict(showgrid=True, gridcolor='#E0E0E0'), yaxis=dict(showgrid=False))
st.plotly_chart(fig_cat, use_container_width=True)

st.divider()
st.subheader("🚨 Cảnh báo Thời gian Thực (AI Monitor)")

risk_count = 0
churn_count = 0
scan_time = "Chưa có dữ liệu"

if r:
    raw = r.get('dashboard_kpi')
    if raw:
        kpi = json.loads(raw)
        risk_count, churn_count, scan_time = kpi.get('risk_count', 0), kpi.get('churn_count', 0), kpi.get('scan_time', '')

kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
kpi_col1.metric(label="🚚 Đơn hàng Rủi ro Giao trễ", value=f"{risk_count} đơn", delta="Risk Score > 70%" if risk_count > 0 else "Không có rủi ro", delta_color="inverse")
kpi_col2.metric(label="💔 Khách hàng Sắp Rời bỏ", value=f"{churn_count} khách", delta="Churn Prob > 50%" if churn_count > 0 else "Ổn định", delta_color="inverse")
kpi_col3.metric(label="🕐 Lần quét gần nhất", value=scan_time if scan_time != "Chưa có dữ liệu" else "N/A", delta="Monitor Agent đang chạy" if r else "⚠️ Redis offline")

if not r:
    st.warning("⚠️ Redis chưa kết nối. Chạy docker-compose up để kích hoạt Monitor Agent.")

st.divider()
st.subheader("📰 AI Narrator — Báo cáo Tóm tắt Tự động")

@st.cache_data(ttl=1800)
def generate_narrator_report(risk_count, churn_count, top_cat, total_rev):
    """
    [PLACEHOLDER] Sinh prompt tom tat tinh hinh kinh doanh va goi LLM (qua
    OpenRouter, co fallback nhieu model) de tra ve bao cao AI Narrator.
    Da luoc bo noi dung prompt template va danh sach model uu tien vi ly
    do bao mat chat xam.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key: return "⚠️ Chưa cấu hình OPENROUTER_API_KEY."
    return "🚨 AI Narrator tạm thời không khả dụng (bản rút gọn, xem source gốc của chủ repo)."

top_category = df_cat['category'].iloc[-1] if not df_cat.empty else "N/A"

if 'ai_report_content' not in st.session_state:
    st.session_state['ai_report_content'] = None
if 'is_generating' not in st.session_state:
    st.session_state['is_generating'] = False

if st.button("🤖 Tạo Báo cáo AI Narrator", use_container_width=True):
    st.session_state['is_generating'] = True

if st.session_state['is_generating']:
    with st.spinner("⏳ AI đang suy nghĩ và viết báo cáo (Sẽ mất khoảng 5-7 giây, xin đừng chuyển trang)..."):
        st.session_state['ai_report_content'] = generate_narrator_report(risk_count, churn_count, top_category, rev)
        st.session_state['is_generating'] = False
        st.rerun()

if st.session_state['ai_report_content'] and not st.session_state['is_generating']:
    st.info(f"📋 **Tóm tắt tình hình:** {st.session_state['ai_report_content']}")


# --- 6. ALERT FEED (ĐÃ CHIA 3 TABS THÔNG MINH) ---
st.divider()

col_title, col_btn = st.columns([5, 1])
with col_title:
    st.subheader("📡 Alert Feed — Phân loại Cảnh báo")
with col_btn:
    if st.button("🧹 Làm mới Hệ thống"):
        if r: r.flushdb() 
        st.rerun()

if r:
    # 🛠 Lấy hết 500 cái để không bị lọt bất kỳ cái nào
    raw_alerts = r.lrange('alert_history', 0, 499)
    if raw_alerts:
        delivery_alerts = []
        seller_alerts = []
        churn_alerts = []
        
        # 🛠 DÙNG LỆNH ELSE ĐỂ TÓM GỌN MỌI CẢNH BÁO ĐƠN HÀNG
        for raw in raw_alerts:
            try:
                alert = json.loads(raw)
                msg = alert.get('message', '')
                if "[CHURN]" in msg or "Khách" in msg:
                    churn_alerts.append(alert)
                elif "Seller" in msg:
                    seller_alerts.append(alert)
                else: 
                    # Bất kể thông báo thời tiết, bottleneck hay gì đi nữa, tống hết vào đây
                    delivery_alerts.append(alert)
            except: continue
        
        # 🛠 UI CHUẨN: Tiêu đề hiển thị TỔNG SỐ, nhưng render chỉ render 10 dòng
        tab1, tab2, tab3 = st.tabs([f"📦 Rủi ro Giao hàng ({len(delivery_alerts)})", 
                                    f"🏪 Quản trị Seller ({len(seller_alerts)})", 
                                    f"💔 Khách hàng Rời bỏ ({len(churn_alerts)})"])
                                    
        def render_alert_list(a_list, list_type):
            if not a_list:
                st.info("Không có cảnh báo nào trong mục này.")
                return
            for i, alert in enumerate(a_list):
                ts    = alert.get('timestamp', '')
                atype = alert.get('type', 'warning')
                msg   = alert.get('message', 'Không có nội dung') 
                
                col_a, col_b = st.columns([5, 1])
                with col_a:
                    if atype == 'critical': st.error(f"🔴 **[{ts}]** {msg}")
                    else: st.warning(f"🟡 **[{ts}]** {msg}")
                
                with col_b:
                    # Logic cắt ID thông minh cho nhảy trang
                    if list_type == "churn" and "Khách" in msg:
                        match = re.search(r"Khách\s+`?([A-Za-z0-9_-]+)`?", msg)
                        if match and st.button("Xử lý", key=f"btn_{list_type}_{i}"):
                            st.session_state['target_cust_id'] = match.group(1)
                            st.switch_page("pages/2_Churn_Management.py")
                            
                    elif list_type == "seller" and "Seller" in msg:
                        match = re.search(r"Seller\s+`?([A-Za-z0-9_-]+)`?", msg)
                        if match and st.button("Xử lý", key=f"btn_{list_type}_{i}"):
                            st.session_state['target_seller_id'] = match.group(1)
                            st.switch_page("pages/3_Seller_Intelligence.py")
                            
                    elif list_type == "delivery" and "Đơn" in msg:
                        match = re.search(r"Đơn\s+`?([A-Za-z0-9_-]+)`?", msg)
                        if match and st.button("Xử lý", key=f"btn_{list_type}_{i}"):
                            st.session_state['target_order_id'] = match.group(1)
                            st.switch_page("pages/1_AI_Risk_Predictor.py")

        # TRUYỀN ĐÚNG 10 DÒNG MỚI NHẤT VÀO ĐỂ KHÔNG BỊ LAG MÀN HÌNH
        with tab1: render_alert_list(delivery_alerts[:10], "delivery")
        with tab2: render_alert_list(seller_alerts[:10], "seller")
        with tab3: render_alert_list(churn_alerts[:10], "churn")

    else: 
        st.info("🔄 Đã xóa bộ nhớ tạm. Xin chờ tối đa 10 giây để AI Monitor Agent cào dữ liệu mới...")
else: 
    st.error("Redis chưa kết nối — Alert Feed không khả dụng.")



# Auto-refresh không cần iframe
st.markdown("""
    <meta http-equiv="refresh" content="18000">
""", unsafe_allow_html=True)