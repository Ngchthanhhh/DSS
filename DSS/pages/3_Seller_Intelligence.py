import ui_utils
import streamlit as st
import pandas as pd
import numpy as np
import pickle
import shap
import matplotlib.pyplot as plt
import sys
import os
import redis
import json
import re
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
import streamlit.components.v1 as components  # <-- Đã thêm thư viện nhúng WebGL

# 🛠 CẮM ỐNG DẪN LLM ROUTER SIÊU TỐC VÀO
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from llm_router import generate_with_fallback
except ImportError:
    st.error("⚠️ Không tìm thấy file `llm_router.py`. Vui lòng tạo file này ở thư mục gốc.")

# Tránh lỗi vẽ biểu đồ trên luồng web
plt.switch_backend('Agg')
VN_TZ = timezone(timedelta(hours=7))

# Cấu hình trang
st.set_page_config(page_title="Seller Intelligence", page_icon="🏪", layout="wide")
st.title("🏪 Vendor Analytics: Seller Intelligence")
st.markdown("Hệ thống phân cụm đối tác & Đánh giá hiệu suất bán hàng bằng thuật toán KMeans")
st.divider()

ui_utils.render_full_seller()


# 1. Tải lõi Model KMeans & Scaler
@st.cache_resource
def load_seller_model():
    with open('kmeans_seller_model.pkl', 'rb') as f:
        data = pickle.load(f)
    return data

try:
    ai_data = load_seller_model()
    kmeans = ai_data['model']
    scaler = ai_data['scaler']
    features = ai_data['features']
    explainer = ai_data.get('explainer', None)
except FileNotFoundError:
    st.error("🚨 Không tìm thấy file 'kmeans_seller_model.pkl'. Vui lòng chạy file train_kmeans_seller.py trước!")
    st.stop()

# 🛠 TỪ ĐIỂN CHỐT HẠ (Đã map chuẩn 100% với file train)
CLUSTER_NAMES = {
    0: ("💎 Premium Seller (Xa xỉ)", "Đưa vào danh mục hiển thị hàng cao cấp", "success"),
    1: ("☠️ Toxic Seller (Báo thủ)", "Khóa tài khoản / Ngừng hợp tác ngay", "error"),
    2: ("⚖️ Average Seller (Bình dân)", "Gửi email hướng dẫn tối ưu doanh thu", "info"),
    3: ("🌟 Star Seller (Ngôi sao)", "Cấp thẻ VIP / Tặng voucher trợ giá", "success")
}

# Khởi tạo Session State
if 'seller_preview_action' not in st.session_state: st.session_state.seller_preview_action = None
if 'seller_ai_draft' not in st.session_state: st.session_state.seller_ai_draft = {}

# ==========================================
# 2. XÂY DỰNG FORM NHẬP LIỆU (LIVE DATABASE)
# ==========================================
st.subheader("🕵️ Tra cứu & Đánh giá Đối tác (Live DB)")

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

# 🛠 CƠ CHẾ MỚI: LẤY TOP 5 SELLER (Ưu tiên Alert Redis, thiếu thì đắp thêm từ Database)
@st.cache_data(ttl=60)
def get_top_5_seller_ids():
    seller_ids = []
    if r:
        raw_alerts = r.lrange('alert_history', 0, 499)
        for raw in raw_alerts:
            try:
                alert = json.loads(raw)
                msg = alert.get('message', '')
                if "Seller" in msg:
                    match = re.search(r"Seller\s+`?([A-Za-z0-9_-]+)`?", msg)
                    if match:
                        seller_ids.append(str(match.group(1))[:8])
            except: continue
    
    unique_ids = list(dict.fromkeys(seller_ids))
    
    if len(unique_ids) < 5:
        needed = 5 - len(unique_ids)
        try:
            conn = engine.raw_connection()
            query = f"""
                SELECT i.seller_id FROM order_items i
                JOIN orders o ON i.order_id = o.order_id
                ORDER BY o.order_purchase_timestamp DESC LIMIT {needed + 20}
            """
            df = pd.read_sql(query, conn)
            conn.close()
            
            db_ids = [str(x)[:8] for x in df['seller_id'].tolist()]
            for did in db_ids:
                if did not in unique_ids:
                    unique_ids.append(did)
                if len(unique_ids) >= 5:
                    break
        except:
            pass 
            
    if not unique_ids:
        unique_ids = ["729f0699"] # Fallback an toàn
        
    return unique_ids[:5]

real_seller_ids = get_top_5_seller_ids()

# Hứng Deep Link từ trang chủ
if 'target_seller_id' in st.session_state: 
    st.session_state['widget_seller_id'] = st.session_state.pop('target_seller_id')

if 'widget_seller_id' not in st.session_state or st.session_state['widget_seller_id'] == "SEL-8888": 
    st.session_state['widget_seller_id'] = real_seller_ids[0]
    
if st.session_state['widget_seller_id'] not in real_seller_ids:
    real_seller_ids.insert(0, st.session_state['widget_seller_id'])

# --- KÉO DATA THẬT TỪ POSTGRESQL ---
current_s = {"orders": 50, "rating": 4.0, "val": 150.0, "inc": 5, "delay": -5.0, "cancel": 0.02, "ret": 0.01, "days": 45} 

try:
    query_seller = f"""
        SELECT 
            COUNT(DISTINCT o.order_id) as total_orders,
            AVG(r.review_score) as avg_rating,
            AVG(i.price) as avg_order_value,
            AVG(EXTRACT(EPOCH FROM (o.order_delivered_customer_date - o.order_estimated_delivery_date))/86400.0) as avg_delay_days,
            SUM(CASE WHEN o.order_status = 'canceled' THEN 1 ELSE 0 END) * 1.0 / NULLIF(COUNT(o.order_id), 0) as cancellation_rate
        FROM order_items i
        JOIN orders o ON i.order_id = o.order_id
        LEFT JOIN order_reviews r ON o.order_id = r.order_id
        WHERE i.seller_id LIKE '{st.session_state['widget_seller_id']}%%'
        GROUP BY i.seller_id
    """
    raw_conn = engine.raw_connection()
    try:
        df_s = pd.read_sql(query_seller, raw_conn)
    finally:
        raw_conn.close()
        
    if not df_s.empty:
        current_s["orders"] = int(df_s.iloc[0]["total_orders"])
        current_s["rating"] = float(df_s.iloc[0]["avg_rating"]) if pd.notnull(df_s.iloc[0]["avg_rating"]) else 4.0
        current_s["val"]    = float(df_s.iloc[0]["avg_order_value"]) if pd.notnull(df_s.iloc[0]["avg_order_value"]) else 150.0
        current_s["delay"]  = float(df_s.iloc[0]["avg_delay_days"]) if pd.notnull(df_s.iloc[0]["avg_delay_days"]) else 0.0
        current_s["cancel"] = float(df_s.iloc[0]["cancellation_rate"]) if pd.notnull(df_s.iloc[0]["cancellation_rate"]) else 0.0
except Exception as e:
    st.sidebar.warning(f"Lỗi kéo DB: {e}")

col1, col2, col3, col4 = st.columns(4)

with col1:
    seller_id = st.selectbox("Mã Seller (Top 5 Rủi ro & Mới nhất)", options=real_seller_ids, key='widget_seller_id')
    total_orders = st.number_input("Tổng đơn hàng", min_value=0, max_value=10000, value=current_s["orders"], step=10)
    days_on_platform = st.number_input("Thời gian tham gia (Ngày)", min_value=1, value=current_s["days"])
with col2:
    avg_rating = st.slider("Điểm đánh giá TB", min_value=1.0, max_value=5.0, value=float(current_s["rating"]), step=0.1)
    rating_drop_weeks = st.number_input("Rating giảm liên tiếp (Tuần)", min_value=0, value=3 if current_s["rating"] < 3.0 else 0)
with col3:
    avg_order_value = st.number_input("Giá trị đơn TB (BRL - 1 BRL ≈ 4,500 VNĐ)", min_value=1.0, max_value=5000.0, value=float(current_s["val"]), step=10.0)
    price_increase = st.number_input("Tăng giá tuần trước (%)", min_value=0, value=current_s["inc"])
with col4:
    avg_delay_days = st.number_input("Tốc độ giao (Ngày trễ)", min_value=-30.0, max_value=30.0, value=float(current_s["delay"]), step=1.0)
    cancellation_rate = st.slider("Tỷ lệ hủy đơn", min_value=0.0, max_value=1.0, value=float(current_s["cancel"]), step=0.01)
    return_rate = st.slider("Tỷ lệ hoàn hàng", min_value=0.0, max_value=1.0, value=float(current_s["ret"]), step=0.01)

# ==========================================
# 3. XỬ LÝ NÚT BẤM
# ==========================================
if st.button("🔮 Phân loại Seller", type="primary", use_container_width=True):
    # Dữ liệu chuẩn đưa vào Model (Phải đúng 5 biến đã train)
    input_data = pd.DataFrame({
        'avg_rating': [avg_rating],
        'total_orders': [total_orders],
        'avg_delay_days': [avg_delay_days],
        'cancellation_rate': [cancellation_rate],
        'avg_order_value': [avg_order_value]
    })

    input_scaled = scaler.transform(input_data)
    cluster_id = kmeans.predict(input_scaled)[0]
    
    st.session_state['seller_cluster_id'] = cluster_id
    st.session_state['seller_input_data'] = input_data
    st.session_state['seller_input_scaled'] = input_scaled
    st.session_state['seller_revenue'] = total_orders * avg_order_value
    st.session_state.seller_preview_action = None
    st.session_state.seller_ai_draft = {}

# ==========================================
# 4. HIỂN THỊ KẾT QUẢ & ACTION CENTER (6 RULES)
# ==========================================
if 'seller_cluster_id' in st.session_state:
    cluster_id = st.session_state['seller_cluster_id']
    input_data = st.session_state['seller_input_data']
    
    cluster_name, action_desc, alert_type = CLUSTER_NAMES[cluster_id]
    
    st.divider()
    res_col1, res_col2 = st.columns([1, 1.5])
    
    with res_col1:
        st.subheader("📊 Kết quả Phân Cụm")
        st.markdown(f"### Nhóm: **{cluster_name}**")
        
        st.markdown("---")
        st.markdown("⚡ **Action Center (Tự động kích hoạt theo Rule)**")
        
        # 🛠 CƠ CHẾ ĐÁNH GIÁ 6 RULES TỰ ĐỘNG CHO SELLER
        rules_triggered = []
        
        # 🛠 CƠ CHẾ PHỦ QUYẾT: Đang có vi phạm thì cấm được nhận thưởng
        is_violating = (cancellation_rate > 0.15) or (price_increase > 30) or (return_rate > 0.10) or (rating_drop_weeks >= 3)
        
        if cancellation_rate > 0.15:
            rules_triggered.append(("rule1_toxic", "Cảnh cáo tỷ lệ Hủy đơn >15% [Rule 1]", "error"))
            
        if price_increase > 30:
            rules_triggered.append(("rule2_price", "Yêu cầu giải trình Tăng giá >30% [Rule 2]", "error"))
            
        if return_rate > 0.10: 
            rules_triggered.append(("rule3_return", "Điều tra Hoàn trả tăng đột biến [Rule 3]", "warning"))
            
        if rating_drop_weeks >= 3:
            rules_triggered.append(("rule4_rating", "Cảnh báo sớm Rating giảm liên tiếp [Rule 4]", "warning"))
            
        # Kích hoạt thưởng nếu là Cụm 0 (Premium) hoặc Cụm 3 (Star)
        if cluster_id in [0, 3]: 
            if not is_violating:
                rules_triggered.append(("rule5_star", "Đề xuất Tăng Visibility trên sàn [Rule 5]", "success"))
            else:
                st.warning("⚠️ Hệ thống AI xếp hạng Seller này vào nhóm xuất sắc, nhưng quyền lợi đã bị TƯỚC BỎ do có vi phạm vận hành!")
            
        if days_on_platform < 30 and total_orders == 0:
            rules_triggered.append(("rule6_newbie", "Gửi Chuỗi Email Onboarding [Rule 6]", "info"))

        # Render nút bấm + Nút mặc định Báo cáo tuần
        if not rules_triggered:
            st.info("Seller hoạt động ổn định, không vi phạm hay thỏa mãn điều kiện đặc biệt.")
        else:
            for rule_code, btn_label, btn_type in rules_triggered:
                if st.button(f"🤖 {btn_label}", use_container_width=True):
                    st.session_state.seller_preview_action = rule_code
                    
        st.markdown("---")
        if st.button("🧠 Tạo Báo Cáo Kinh Doanh Tuần (Tổng hợp)", use_container_width=True):
             st.session_state.seller_preview_action = "weekly_report"

    with res_col2:
        if explainer is not None:
            st.markdown("**Bóc tách nguyên nhân phân cụm (SHAP):**")
            input_scaled = st.session_state['seller_input_scaled']
            shap_values = explainer.shap_values(input_scaled)
            try:
                feature_dict = {
                    "avg_rating": "Điểm đánh giá TB",
                    "total_orders": "Tổng đơn hàng",
                    "avg_delay_days": "Tốc độ giao hàng (Ngày)",
                    "cancellation_rate": "Tỷ lệ hủy đơn",
                    "avg_order_value": "Giá trị đơn TB (BRL - 1 BRL ≈ 4,500 VNĐ)"
                }
                vietnamese_features = [feature_dict.get(f, f) for f in features]
                
                shap_val_to_plot = shap_values[cluster_id][0] if isinstance(shap_values, list) else shap_values[0]
                exp = shap.Explanation(values=shap_val_to_plot, 
                                       base_values=explainer.expected_value[cluster_id] if isinstance(explainer.expected_value, list) else explainer.expected_value, 
                                       data=input_data.iloc[0].values, 
                                       feature_names=vietnamese_features)
                fig, ax = plt.subplots(figsize=(8, 4))
                shap.plots.waterfall(exp, show=False)
                plt.tight_layout()
                st.pyplot(fig)
            except Exception as e:
                st.error(f"🚨 Lỗi hiển thị SHAP: {e}")

# ==========================================
# 5. AGENTIC PREVIEW & PDPA AUDIT 
# ==========================================
def fetch_seller_agent_proposal(rule_code, ctx_seller, ctx_cluster):
    """
    [PLACEHOLDER] Sinh prompt theo rule_code (toxic, price, return, rating,
    star, newbie, weekly_report) va goi LLM qua llm_router de soan
    email/ticket quan tri seller. Da luoc bo noi dung system_rules va
    prompt template chi tiet vi ly do bao mat chat xam.
    """
    raise NotImplementedError("Xem ban day du o source goc cua chu repo.")

if st.session_state.get('seller_preview_action'):
    st.divider()
    st.subheader("📨 Trạm xử lý AI (Agentic Hub)")
    
    action = st.session_state.seller_preview_action
    cache_key = f"seller_{action}_{seller_id}"
    
    ecol1, ecol2 = st.columns([2, 1])
    with ecol1:
        with st.container(border=True):
            if cache_key not in st.session_state.seller_ai_draft:
                with st.spinner("🤖 Agent đang phân tích dữ liệu và soạn thảo văn bản..."):
                    draft = fetch_seller_agent_proposal(action, seller_id, cluster_name)
                    st.session_state.seller_ai_draft[cache_key] = draft
            
            st.text_area("Bản nháp (Có thể chỉnh sửa trước khi gửi):", value=st.session_state.seller_ai_draft[cache_key], height=200)
            
            btn_col1, btn_col2 = st.columns([1, 4])
            with btn_col1:
                if st.button("✅ DUYỆT & GỬI LỆNH", type="primary"):
                    st.success(f"🎉 Lệnh cho kịch bản `{action}` đã được phân phối thành công!")
                    st.balloons()
            with btn_col2:
                if st.button("❌ Hủy bỏ"):
                    st.session_state.seller_preview_action = None
                    st.rerun()

    with ecol2:
        st.warning("🔐 **Hệ Thống PDPA & Audit Log**")
        st.code(f"SELLER: {seller_id}\nACTION: {action}\nTIMESTAMP: {datetime.now(VN_TZ).strftime('%Y-%m-%d %H:%M:%S')}\nSTATUS: PENDING", language="yaml")
        st.info("💡 **Kiến trúc Hệ thống Agent:** \nChạy trên Multi-LLM Router (Zero-Shot Output). Không lưu trữ PII.")