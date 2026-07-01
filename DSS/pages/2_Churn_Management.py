import ui_utils
import streamlit as st
import pandas as pd
import pickle
import shap
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import sys
import os
import json
import redis
import re
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
import streamlit.components.v1 as components  # <-- Đã thêm thư viện nhúng WebGL

# 🛠 Nhổ Agent cũ, cắm Kho đạn llm_router SIÊU TỐC vào
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from llm_router import generate_with_fallback
except ImportError:
    st.error("⚠️ Không tìm thấy file `llm_router.py`. Vui lòng tạo file này ở thư mục gốc.")

plt.switch_backend('Agg')
VN_TZ = timezone(timedelta(hours=7))

st.set_page_config(page_title="Churn Management", page_icon="💔", layout="wide")
st.title("💔 Retention: Churn Risk Management")
st.markdown("Hệ thống quản trị rủi ro mất khách & Phân tích nguyên nhân rời bỏ bằng AI")
st.divider()
ui_utils.render_full_churn()



# ── 1. LOAD MODEL ─────────────────────────────────────────────────────────────
@st.cache_resource
def load_churn_model():
    with open('rf_churn_model.pkl', 'rb') as f:
        data = pickle.load(f)
    return data

try:
    ai_data  = load_churn_model()
    model    = ai_data['model']
    features = ai_data['features']
    explainer = shap.TreeExplainer(model)
except FileNotFoundError:
    st.error("Không tìm thấy rf_churn_model.pkl. Chạy train_rf_churn.py trước!")
    st.stop()

# Khởi tạo Session State
if 'churn_preview_action' not in st.session_state: st.session_state.churn_preview_action = None
if 'churn_ai_draft' not in st.session_state: st.session_state.churn_ai_draft = {}

# ==========================================
# 2. XÂY DỰNG FORM NHẬP LIỆU (LIVE DATABASE)
# ==========================================
st.subheader("👤 Tra cứu Hồ sơ Khách hàng (Live DB)")

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

# 🛠 CƠ CHẾ MỚI: LẤY TOP 5 KHÁCH HÀNG (Ưu tiên Alert Redis, thiếu thì đắp thêm từ Database)
@st.cache_data(ttl=60)
def get_top_5_churn_ids():
    churn_ids = []
    if r:
        raw_alerts = r.lrange('alert_history', 0, 499)
        for raw in raw_alerts:
            try:
                alert = json.loads(raw)
                msg = alert.get('message', '')
                if "[CHURN]" in msg or "Khách" in msg:
                    match = re.search(r"Khách\s+`?([A-Za-z0-9_-]+)`?", msg)
                    if match:
                        churn_ids.append(str(match.group(1))[:12])
            except: continue
    
    unique_ids = list(dict.fromkeys(churn_ids))
    
    if len(unique_ids) < 5:
        needed = 5 - len(unique_ids)
        try:
            conn = engine.raw_connection()
            query = f"""
                SELECT customer_id FROM orders 
                ORDER BY order_purchase_timestamp DESC LIMIT {needed + 20}
            """
            df = pd.read_sql(query, conn)
            conn.close()
            
            db_ids = [str(x)[:12] for x in df['customer_id'].tolist()]
            for did in db_ids:
                if did not in unique_ids:
                    unique_ids.append(did)
                if len(unique_ids) >= 5:
                    break
        except:
            pass 
            
    if not unique_ids:
        unique_ids = ["053fbd86c4da"] # Fallback an toàn
        
    return unique_ids[:5]

real_cust_ids = get_top_5_churn_ids()

# Hứng Deep Link từ trang chủ
if 'target_cust_id' in st.session_state: 
    st.session_state['widget_cust_id'] = st.session_state.pop('target_cust_id')

if 'widget_cust_id' not in st.session_state or st.session_state['widget_cust_id'] == "CUST-8888": 
    st.session_state['widget_cust_id'] = real_cust_ids[0]

if st.session_state['widget_cust_id'] not in real_cust_ids:
    real_cust_ids.insert(0, st.session_state['widget_cust_id'])

# --- KÉO DATA THẬT TỪ POSTGRESQL ---
current_c = {"freq": 1, "monetary": 500, "score": 3.0, "freight": 25.0, "delay": 2, "last": 95, "deliv": 3, "cat": 0} 

try:
    query_cust = f"""
        SELECT 
            COUNT(DISTINCT o.order_id) as frequency, SUM(p.payment_value) as monetary,
            AVG(r.review_score) as avg_review_score, AVG(i.freight_value) as avg_freight_value,
            AVG(EXTRACT(DAY FROM (o.order_delivered_customer_date - o.order_estimated_delivery_date))) as avg_delivery_delay
        FROM orders o 
        JOIN order_payments p ON o.order_id = p.order_id
        JOIN order_items i ON o.order_id = i.order_id 
        LEFT JOIN order_reviews r ON o.order_id = r.order_id
        WHERE o.customer_id LIKE '{st.session_state['widget_cust_id']}%%'
        GROUP BY o.customer_id
    """
    raw_conn = engine.raw_connection()
    try:
        df_c = pd.read_sql(query_cust, raw_conn)
    finally:
        raw_conn.close()
        
    if not df_c.empty:
        current_c["freq"]     = int(df_c.iloc[0]["frequency"])
        current_c["monetary"] = float(df_c.iloc[0]["monetary"]) if pd.notnull(df_c.iloc[0]["monetary"]) else 500.0
        current_c["score"]    = float(df_c.iloc[0]["avg_review_score"]) if pd.notnull(df_c.iloc[0]["avg_review_score"]) else 3.0
        current_c["freight"]  = float(df_c.iloc[0]["avg_freight_value"]) if pd.notnull(df_c.iloc[0]["avg_freight_value"]) else 50.0
        current_c["delay"]    = float(df_c.iloc[0]["avg_delivery_delay"]) if pd.notnull(df_c.iloc[0]["avg_delivery_delay"]) else 0.0
except Exception as e:
    st.sidebar.warning(f"Lỗi kéo DB: {e}")

col1, col2, col3, col4 = st.columns(4)
with col1:
    customer_id        = st.selectbox("Mã KH (Top 5 Rủi ro & Mới nhất)", options=real_cust_ids, key='widget_cust_id')
    frequency          = st.number_input("Tần suất mua", min_value=1, max_value=50, value=current_c["freq"], step=1)
with col2:
    monetary           = st.number_input("Tổng chi tiêu (BRL - 1 BRL ≈ 4,500 VNĐ)", min_value=1, max_value=20000, value=int(current_c["monetary"]), step=10)
    avg_review_score   = st.slider("Điểm đánh giá TB", min_value=0.0, max_value=5.0, value=float(current_c["score"]), step=0.5)
with col3:
    avg_freight_value  = st.number_input("Phí ship TB (BRL - 1 BRL ≈ 4,500 VNĐ)", min_value=0.0, max_value=1000.0, value=float(current_c["freight"]), step=5.0)
    avg_delivery_delay = st.number_input("Độ trễ TB (Ngày)", min_value=-20, max_value=100, value=int(current_c["delay"]), step=1)
with col4:
    days_since_last    = st.number_input("Lặn mất tăm (Ngày)", min_value=0, value=current_c["last"])
    days_since_deliv   = st.number_input("Đã nhận hàng (Ngày)", min_value=0, value=current_c["deliv"])
    fav_category       = st.selectbox("Danh mục yêu thích", ["Thời trang", "Công nghệ", "Gia dụng", "Không có"], index=current_c["cat"])

# ── 3. NÚT PHÂN TÍCH ──────────────────────────────────────────────────────────
if st.button("🔍 Phân tích Rủi ro Rời bỏ", type="primary", use_container_width=True):
    input_data = pd.DataFrame({
        'frequency':          [frequency],
        'monetary':           [monetary],
        'avg_review_score':   [avg_review_score],
        'avg_freight_value':  [avg_freight_value],
        'avg_delivery_delay': [avg_delivery_delay]
    })
    st.session_state['prob_churn']         = model.predict_proba(input_data)[0][1] * 100
    st.session_state['input_data']         = input_data
    st.session_state['churn_preview_action'] = None 
    st.session_state['churn_ai_draft']       = {} 

# ── 4. HIỂN THỊ KẾT QUẢ & ACTION CENTER THEO 7 RULES ────────────────────────
if 'prob_churn' in st.session_state:
    prob_churn = st.session_state['prob_churn']
    input_data = st.session_state['input_data']

    st.divider()
    res_col1, res_col2 = st.columns([1, 2])

    with res_col1:
        st.subheader("📊 Mức độ Rủi ro")
        if prob_churn >= 70: st.error(f"🚨 BÁO ĐỘNG ĐỎ: {prob_churn:.2f}%")
        elif prob_churn >= 40: st.warning(f"⚠️ NGUY CƠ TRUNG BÌNH: {prob_churn:.2f}%")
        else: st.success(f"✅ KHÁCH TRUNG THÀNH: {prob_churn:.2f}%")
        
        st.markdown("---")
        st.markdown("⚡ **Action Center (Tự động kích hoạt theo Rule)**")
        
        rules_triggered = []
        if prob_churn > 70 and monetary > 2000:
            rules_triggered.append(("rule1_vip", "Tặng FreeShip 3 tháng [Rule 1]"))
        elif prob_churn > 70:
            rules_triggered.append(("rule2_comeback", "Gửi Voucher COMEBACK20 [Rule 2]"))
            
        if 50 <= prob_churn <= 70:
            rules_triggered.append(("rule3_survey", "SMS/Zalo Khảo sát [Rule 3]"))
            
        if frequency == 1 and days_since_last > 90:
            rules_triggered.append(("rule4_missyou", "Chiến dịch We Miss You [Rule 4]"))
            
        if avg_review_score == 1.0:
            rules_triggered.append(("rule5_refund", "Xin lỗi & Hoàn tiền tự động [Rule 5]"))
            
        if days_since_last > 60 and fav_category != "Không có":
            rules_triggered.append(("rule6_suggest", f"Email gợi ý {fav_category} [Rule 6]"))
            
        if days_since_deliv == 3 and avg_review_score == 0.0:
            rules_triggered.append(("rule7_review", "Nhắc Review nhẹ nhàng [Rule 7]"))

        if not rules_triggered:
            st.info("Không có Kịch bản Rule nào bị vi phạm.")
        else:
            for rule_code, btn_label in rules_triggered:
                if st.button(f"🤖 {btn_label}", use_container_width=True):
                    st.session_state.churn_preview_action = rule_code

    with res_col2:
        st.subheader("🔍 Phân tích Nguyên nhân (SHAP)")
        try:
            raw_shap = explainer.shap_values(input_data)
            if isinstance(raw_shap, list) and len(raw_shap) == 2:
                shap_vals = np.array(raw_shap[1][0], dtype=float)   
                base_val  = float(explainer.expected_value[1])
            else:
                shap_vals = np.array(raw_shap[0], dtype=float)
                ev = explainer.expected_value
                base_val = float(ev[0]) if hasattr(ev, '__len__') else float(ev)

            feature_dict = {
                "frequency": "frequency (Tần suất mua hàng)",
                "monetary": "monetary (Tổng chi tiêu - BRL - 1 BRL ≈ 4,500 VNĐ)",
                "avg_review_score": "avg_review_score (Điểm đánh giá TB)",
                "avg_freight_value": "avg_freight_value (Phí ship TB - BRL - 1 BRL ≈ 4,500 VNĐ)",
                "avg_delivery_delay": "avg_delivery_delay (Độ trễ giao hàng TB - Ngày)"
            }
            vietnamese_features = [feature_dict.get(f, f) for f in features]

            explanation = shap.Explanation(
                values        = shap_vals,
                base_values   = base_val,
                data          = input_data.iloc[0].values.astype(float),
                feature_names = vietnamese_features
            )
            fig, ax = plt.subplots(figsize=(8, 4))
            shap.plots.waterfall(explanation, show=False)
            plt.tight_layout()
            st.pyplot(fig)
            plt.close(fig)
        except Exception as e:
            st.error(f"Không thể vẽ SHAP: {e}")

# ── 5. AGENTIC PREVIEW & PDPA AUDIT (Lõi LLM Router) ──────────────────────────
def fetch_churn_agent_proposal(rule_code, customer_id, fav_cat):
    """
    [PLACEHOLDER] Sinh prompt theo rule_code (VIP, comeback, survey, miss-you,
    refund, suggest, review) va goi LLM qua llm_router de soan email/tin nhan
    cham soc khach hang. Da luoc bo noi dung system_rules va prompt template
    chi tiet vi ly do bao mat chat xam.
    """
    raise NotImplementedError("Xem ban day du o source goc cua chu repo.")

if st.session_state.get('churn_preview_action'):
    st.divider()
    st.subheader("📨 Trạm xử lý AI (Agentic Action Center)")
    
    action = st.session_state.churn_preview_action
    cache_key = f"churn_{action}_{customer_id}"
    
    ecol1, ecol2 = st.columns([2, 1])
    with ecol1:
        with st.container(border=True):
            st.markdown(f"**Nội dung AI đề xuất cho Kịch bản: `{action.upper()}`**")
            
            if cache_key not in st.session_state.churn_ai_draft:
                with st.spinner("🤖 Agent đang suy luận và soạn thảo thông điệp..."):
                    draft = fetch_churn_agent_proposal(action, customer_id, fav_category)
                    st.session_state.churn_ai_draft[cache_key] = draft
            
            st.text_area("Bản nháp (Có thể chỉnh sửa):", value=st.session_state.churn_ai_draft[cache_key], height=150)
            
            btn_col1, btn_col2 = st.columns([1, 4])
            with btn_col1:
                if st.button("✅ DUYỆT & THỰC THI", type="primary"):
                    st.success(f"🎉 Lệnh `{action}` đã được bắn vào chuỗi thực thi tự động!")
                    st.balloons()
            with btn_col2:
                if st.button("❌ Hủy bỏ"):
                    st.session_state.churn_preview_action = None
                    st.rerun()

    with ecol2:
        st.warning("🔐 **Hệ Thống PDPA - Audit Trail**")
        st.code(f"USER: {customer_id}\nACTION: {action}\nTIMESTAMP: {datetime.now(VN_TZ).strftime('%Y-%m-%d %H:%M:%S')}\nSTATUS: AWAITING_APPROVAL", language="yaml")
        st.info("💡 Hệ thống sử dụng Multi-LLM Router. Content đã được kiểm duyệt tuân thủ PDPA.")