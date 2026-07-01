import ui_utils
import streamlit as st
import pandas as pd
import pickle
import shap
import matplotlib.pyplot as plt
import numpy as np
import redis
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
import streamlit.components.v1 as components  # <-- Đã thêm thư viện nhúng WebGL

# Import kho đạn LLM Router
sys.path.append('.') 
try:
    from llm_router import generate_with_fallback
except ImportError:
    st.error("⚠️ Không tìm thấy file `llm_router.py`. Vui lòng tạo file này ở thư mục gốc.")

st.set_page_config(page_title="AI Risk Predictor", page_icon="🤖", layout="wide")
ui_utils.render_full_risk()

plt.switch_backend('Agg')
VN_TZ = timezone(timedelta(hours=7))

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

st.title("🤖 Aegis: AI Delivery Risk Predictor & What-If")
st.markdown("Hệ thống dự đoán rủi ro đơn hàng và mô phỏng kịch bản xử lý")
st.divider()

ui_utils.render_full_risk()

@st.cache_resource
def load_ai_model():
    with open('xgboost_delivery_risk.pkl', 'rb') as f:
        return pickle.load(f)

try:
    ai_data = load_ai_model()
    model = ai_data['model']
    encoder = ai_data['encoder']
    features = ai_data['features']
    explainer = shap.TreeExplainer(model)
except FileNotFoundError:
    st.error("🚨 Không tìm thấy file 'xgboost_delivery_risk.pkl'. Vui lòng chạy file train trước!")
    st.stop()

# Khởi tạo Session State
for key in ['analyzed', 'auto_optimized']:
    if key not in st.session_state: st.session_state[key] = False
if 'preview_action' not in st.session_state: st.session_state.preview_action = None
if 'action_success' not in st.session_state: st.session_state.action_success = None
if 'ai_drafts' not in st.session_state: st.session_state.ai_drafts = {}
if 'opt_reason' not in st.session_state: st.session_state.opt_reason = None

# ==========================================
# XÂY DỰNG FORM NHẬP LIỆU (LIVE DATABASE)
# ==========================================
st.subheader("📝 Nhập thông số Đơn hàng (Live DB)")

# 🛠 CƠ CHẾ MỚI: LẤY 5 MÃ (Ưu tiên Alert Redis, thiếu thì đắp thêm từ Database)
@st.cache_data(ttl=60)
def get_top_5_risk_ids():
    risk_ids = []
    if r:
        raw_alerts = r.lrange('alert_history', 0, 499)
        for raw in raw_alerts:
            try:
                alert = json.loads(raw)
                if 'order_id' in alert:
                    risk_ids.append(str(alert['order_id'])[:12])
            except: continue
    
    unique_ids = list(dict.fromkeys(risk_ids))
    
    # 🛠 LOGIC ĐẮP DATA CỦA SẾP: Nếu danh sách Alert chưa đủ 5 mã, kéo thêm từ DB
    if len(unique_ids) < 5:
        needed = 5 - len(unique_ids)
        try:
            conn = engine.raw_connection()
            query = f"""
                SELECT order_id FROM orders 
                WHERE order_status IN ('processing', 'shipped') 
                ORDER BY order_purchase_timestamp DESC LIMIT {needed + 10}
            """ # Lấy dư chút để trừ hao lỡ bị trùng
            df = pd.read_sql(query, conn)
            conn.close()
            
            db_ids = [str(x)[:12] for x in df['order_id'].tolist()]
            for did in db_ids:
                if did not in unique_ids:
                    unique_ids.append(did)
                if len(unique_ids) >= 5:
                    break
        except:
            pass # Nếu DB lỗi thì xài tạm cái list hiện tại
            
    if not unique_ids:
        unique_ids = ["e481f51cbdc5"] # Fallback cuối cùng
        
    return unique_ids[:5] # Chốt sổ cắt đúng 5 thằng

real_order_ids = get_top_5_risk_ids()

# Hứng Deep Link từ trang chủ
if 'target_order_id' in st.session_state: 
    st.session_state['widget_order_id'] = st.session_state.pop('target_order_id')
if 'target_seller_id' in st.session_state: 
    st.session_state['widget_seller_id'] = st.session_state.pop('target_seller_id')

if 'widget_order_id' not in st.session_state or st.session_state['widget_order_id'] == "ORD-SIM-9999":
    st.session_state['widget_order_id'] = real_order_ids[0]
if st.session_state['widget_order_id'] not in real_order_ids:
    real_order_ids.insert(0, st.session_state['widget_order_id'])

# --- KÉO DATA THẬT TỪ POSTGRESQL TRƯỚC KHI RENDER Ô CHỌN MÃ ---
current_o = {"weight": 1.5, "val": 150.0, "pay": "boleto", "day": 0, "cat": "Thời trang / Quần áo", "seller": "UNKNOWN"}

try:
    query_order = f"""
        SELECT 
            pr.product_weight_g, p.payment_value, p.payment_type, i.seller_id,
            EXTRACT(DOW FROM o.order_purchase_timestamp) as day_of_week
        FROM orders o
        JOIN order_items i ON o.order_id = i.order_id
        JOIN order_payments p ON o.order_id = p.order_id
        JOIN products pr ON i.product_id = pr.product_id
        WHERE o.order_id LIKE '{st.session_state['widget_order_id']}%%'
        LIMIT 1
    """
    raw_conn = engine.raw_connection()
    try:
        df_o = pd.read_sql(query_order, raw_conn)
    finally:
        raw_conn.close()
        
    if not df_o.empty:
        current_o["weight"] = float(df_o.iloc[0]["product_weight_g"]) / 1000.0 if pd.notnull(df_o.iloc[0]["product_weight_g"]) else 1.5
        current_o["val"]    = float(df_o.iloc[0]["payment_value"]) if pd.notnull(df_o.iloc[0]["payment_value"]) else 150.0
        current_o["seller"] = str(df_o.iloc[0]["seller_id"])
        db_pay = str(df_o.iloc[0]["payment_type"])
        current_o["pay"]    = db_pay if db_pay in encoder.classes_ else encoder.classes_[0]
        current_o["day"]    = int(df_o.iloc[0]["day_of_week"]) if pd.notnull(df_o.iloc[0]["day_of_week"]) else 0
        
        if current_o["weight"] >= 15.0:
            current_o["cat"] = "Điện lạnh / Gia dụng lớn (Nguyên khối)"
except Exception as e:
    st.sidebar.warning(f"Lỗi kéo DB: {e}")

st.session_state['widget_seller_id'] = current_o["seller"]

id_col1, id_col2 = st.columns(2)
with id_col1:
    # 🛠 UI CẬP NHẬT: Ghi rõ 5 ký tự để sếp dễ nhận biết
    order_id = st.selectbox("Mã Đơn Hàng (Top 5 Rủi ro & Mới nhất)", options=real_order_ids, key='widget_order_id')
with id_col2:
    st.text_input("Mã Nhà Bán (Đồng bộ theo đơn)", value=st.session_state['widget_seller_id'], disabled=True)
    seller_id = st.session_state['widget_seller_id']
    
st.markdown("---")

with st.form("baseline_form"):
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        weight_kg = st.number_input("Cân nặng (kg)", min_value=0.1, max_value=150.0, value=float(current_o["weight"]), step=0.5, format="%.1f")
    with col2:
        order_value = st.number_input("Giá trị (BRL - 1 BRL ≈ 4,500 VNĐ)", min_value=1.0, max_value=20000.0, value=float(current_o["val"]), step=10.0)
    with col3:
        try:
            pay_idx = list(encoder.classes_).index(current_o["pay"])
        except:
            pay_idx = 0
        payment_type = st.selectbox("Thanh toán", options=encoder.classes_, index=pay_idx)
    with col4:
        day_options = {0: "Thứ 2", 1: "Thứ 3", 2: "Thứ 4", 3: "Thứ 5", 4: "Thứ 6", 5: "Thứ 7", 6: "Chủ Nhật"}
        day_of_week = st.selectbox("Ngày đặt hàng", options=list(day_options.keys()), format_func=lambda x: day_options[x], index=current_o["day"])
    with col5:
        cat_options = ["Thời trang / Quần áo", "Tiêu dùng nhanh (FMCG)", "Hàng công nghệ nhỏ", "Điện lạnh / Gia dụng lớn (Nguyên khối)"]
        cat_idx = cat_options.index(current_o["cat"]) if current_o["cat"] in cat_options else 0
        category = st.selectbox("Danh mục Hàng", cat_options, index=cat_idx)

    submit_button = st.form_submit_button("🔮 Phân tích Rủi ro ngay", type="primary", use_container_width=True)

if submit_button:
    st.session_state.analyzed = True
    st.session_state.auto_optimized = False 
    st.session_state.weight_kg = weight_kg
    st.session_state.order_value = order_value
    st.session_state.payment_type = payment_type
    st.session_state.day_of_week = day_of_week
    st.session_state.category = category 
    st.session_state.order_id = order_id
    st.session_state.seller_id = seller_id
    st.session_state.action_success = None
    st.session_state.ai_drafts = {}
    st.session_state.opt_reason = None

feature_dict = {
    "product_weight_g": "product_weight_g (Trọng lượng sp - gram)",
    "order_value": "order_value (Giá trị đơn - BRL)",
    "day_of_week": "day_of_week (Ngày trong tuần)",
    "payment_type": "payment_type (Hình thức thanh toán)"
}

if st.session_state.analyzed:
    
    base_encoded_payment = encoder.transform([st.session_state.payment_type])[0]
    base_data = pd.DataFrame({
        'product_weight_g': [st.session_state.weight_kg * 1000],
        'order_value': [st.session_state.order_value],
        'day_of_week': [st.session_state.day_of_week],
        'payment_type': [base_encoded_payment]
    })
    base_data = base_data[features]
    base_prob = model.predict_proba(base_data)[0][1] * 100

    st.divider()
    st.subheader("📊 Kết quả Phân tích Gốc (Baseline)")
    
    base_col1, base_col2 = st.columns([1, 2])
    with base_col1:
        if base_prob >= 70: st.error(f"🚨 RỦI RO CỰC CAO: {base_prob:.2f}%")
        elif base_prob >= 40: st.warning(f"⚠️ RỦI RO TRUNG BÌNH: {base_prob:.2f}%")
        else: st.success(f"✅ AN TOÀN: {base_prob:.2f}%")
            
    with base_col2:
        st.markdown("**Nguyên nhân gốc (Baseline SHAP):**")
        base_shap_values = explainer(base_data)
        base_shap_values.feature_names = [feature_dict.get(f, f) for f in features]
        fig_base, ax_base = plt.subplots(figsize=(8, 4))
        shap.plots.waterfall(base_shap_values[0], show=False)
        plt.tight_layout()
        st.pyplot(fig_base)

    st.divider()
    st.subheader("🎛️ What-If Simulation & AI Auto-Optimizer")
    
    is_unbreakable_ui = (st.session_state.category == "Điện lạnh / Gia dụng lớn (Nguyên khối)") or (st.session_state.weight_kg >= 15.0)
    
    opt_col1, opt_col2 = st.columns([2, 1])
    with opt_col1:
        st.markdown("Kéo thanh trượt thủ công hoặc để Trợ lý AI tự động tìm kịch bản tốt nhất.")
    with opt_col2:
        if st.button("✨ Trợ lý AI: Tự động Tối ưu Hóa", use_container_width=True):
            best_risk = base_prob
            best_weight = st.session_state.weight_kg
            best_day = st.session_state.day_of_week
            
            weight_options = [st.session_state.weight_kg] if is_unbreakable_ui else np.arange(0.1, st.session_state.weight_kg + 0.1, 0.5)
            
            for test_w in weight_options:
                for test_d in range(7):
                    test_data = base_data.copy()
                    test_data['product_weight_g'] = test_w * 1000
                    test_data['day_of_week'] = test_d
                    test_prob = model.predict_proba(test_data)[0][1] * 100
                    
                    if test_prob < best_risk:
                        best_risk = test_prob
                        best_weight = test_w
                        best_day = test_d
            
            st.session_state.opt_weight = float(best_weight)
            st.session_state.opt_day = int(best_day)
            st.session_state.auto_optimized = True
            st.session_state.opt_reason = "unbreakable" if is_unbreakable_ui else "splittable"

    default_w = st.session_state.opt_weight if st.session_state.auto_optimized else float(st.session_state.weight_kg)
    default_d = st.session_state.opt_day if st.session_state.auto_optimized else int(st.session_state.day_of_week)

    if st.session_state.auto_optimized:
        if st.session_state.get('opt_reason') == "unbreakable":
            st.info("🤖 **AI Optimizer:** Phát hiện hàng nguyên khối/quá nặng! Đã khóa tính năng chia nhỏ, chỉ tối ưu Ngày vận hành để giảm rủi ro.")
        else:
            st.success("🤖 **AI Optimizer:** Đã tìm ra kịch bản chia nhỏ và đổi ngày vận hành tối ưu nhất!")

    sim_col1, sim_col2 = st.columns(2)
    with sim_col1:
        sim_weight_kg = st.slider("Thay đổi Trọng lượng (Chia nhỏ kiện hàng - kg)", 
                               min_value=0.1, max_value=max(50.0, float(st.session_state.weight_kg)), 
                               value=default_w, step=0.5, key='slider_w', disabled=is_unbreakable_ui)
    with sim_col2:
        sim_day = st.selectbox("Đổi Ngày Vận Hành (Tránh cao điểm)", 
                               options=list(day_options.keys()), 
                               format_func=lambda x: day_options[x], 
                               index=list(day_options.keys()).index(default_d), key='select_d')
    
    sim_data = base_data.copy()
    sim_data['product_weight_g'] = sim_weight_kg * 1000
    sim_data['day_of_week'] = sim_day
    
    sim_prob = model.predict_proba(sim_data)[0][1] * 100
    risk_diff = sim_prob - base_prob

    res_col1, res_col2 = st.columns([1, 2])
    with res_col1:
        st.metric(label="Rủi ro Mới (Simulated Risk)", value=f"{sim_prob:.2f}%", delta=f"{risk_diff:.2f}%", delta_color="inverse")
        if sim_prob >= 70: st.error("Trạng thái: NGUY HIỂM. Đổi kịch bản khác!")
        elif sim_prob >= 40: st.warning("Trạng thái: TẠM ỔN. Kiểm soát được.")
        else: st.success("Trạng thái: AN TOÀN. Đề xuất duyệt kịch bản này!")

    with res_col2:
        st.markdown("**Sự thay đổi mới (Simulated SHAP):**")
        sim_shap_values = explainer(sim_data)
        sim_shap_values.feature_names = [feature_dict.get(f, f) for f in features]
        fig_sim, ax_sim = plt.subplots(figsize=(8, 4))
        shap.plots.waterfall(sim_shap_values[0], show=False)
        plt.tight_layout()
        st.pyplot(fig_sim)

    st.divider()
    st.subheader("⚡ Action Center — Quyết định & Thực thi")
    
    if st.session_state.action_success:
        st.success(f"✅ **LỆNH THỰC THI THÀNH CÔNG:** Lệnh `{st.session_state.action_success}` đã được đẩy lên C-Suite Dashboard!")
    
    st.caption("Các hành động sẽ được OmniSense Agent phân tích và đề xuất trước khi thực thi.")

    act_col1, act_col2, act_col3, act_col4, act_col5 = st.columns(5)

    with act_col1:
        if st.button("🔒 Khóa Seller", use_container_width=True): st.session_state.preview_action = "lock_seller"
    with act_col2:
        if st.button("🔄 Đổi Hub/Carrier", use_container_width=True): st.session_state.preview_action = "change_hub"
    with act_col3:
        if st.button("🎫 Mở Ticket", use_container_width=True): st.session_state.preview_action = "open_ticket"
    with act_col4:
        if st.button("📧 Proactive Email", use_container_width=True): st.session_state.preview_action = "send_email"
    with act_col5:
        if st.button("✂️ Đề xuất chia nhỏ", use_container_width=True): st.session_state.preview_action = "split_order"

    def fetch_agent_proposal(action_type, ctx_order, ctx_category, ctx_weight, ctx_risk):
        """
        [PLACEHOLDER] Sinh prompt theo action_type (change_hub, open_ticket,
        send_email, split_order) va goi LLM qua llm_router de tao de xuat
        xu ly rui ro giao hang. Da luoc bo noi dung system_rules va prompt
        template chi tiet vi ly do bao mat chat xam.
        """
        raise NotImplementedError("Xem ban day du o source goc cua chu repo.")

    if st.session_state.preview_action:
        st.markdown("---")
        action = st.session_state.preview_action
        
        current_order_id = st.session_state.order_id
        current_seller_id = st.session_state.seller_id
        
        with st.container(border=True):
            st.markdown("### ⚠️ PREVIEW BEFORE EXECUTE")
            
            if action == "lock_seller":
                st.error(f"**Hành động [Priority 1]:** Tạm khóa Seller `{current_seller_id}` do rủi ro cực cao.")
                st.write("- **Tác động:** Toàn bộ sản phẩm của Seller sẽ bị ẩn khỏi sàn.")
                st.write("- **Thông báo:** Gửi email cảnh báo cấp 1 đến quản lý Seller.")
            else:
                cache_key = f"{action}_{current_order_id}"
                
                if cache_key not in st.session_state.ai_drafts:
                    with st.spinner("🤖 Agent đang suy luận và dọn mâm kịch bản..."):
                        draft = fetch_agent_proposal(
                            action, 
                            current_order_id, 
                            st.session_state.category, 
                            st.session_state.weight_kg, 
                            base_prob
                        )
                        st.session_state.ai_drafts[cache_key] = draft
                
                st.info(f"**🤖 Đề xuất từ OmniSense Agent:**\n\n{st.session_state.ai_drafts[cache_key]}")

            btn_col1, btn_col2 = st.columns([1, 4])
            with btn_col1:
                if st.button("✅ XÁC NHẬN THỰC THI", type="primary"):
                    if r:
                        payload = {
                            "order_id": current_order_id,
                            "risk_score": float(base_prob),
                            "type": "critical" if action in ["lock_seller", "change_hub"] else "warning",
                            "message": f"[CEO ACTION] Đã ra lệnh {action.upper()} cho Đơn `{current_order_id}` / Seller `{current_seller_id}`",
                            "timestamp": datetime.now(VN_TZ).strftime("%H:%M:%S")
                        }
                        r.lpush('alert_history', json.dumps(payload))
                        r.ltrim('alert_history', 0, 499) 
                    
                    st.session_state.action_success = action
                    st.session_state.preview_action = None
                    st.rerun()
            with btn_col2:
                if st.button("❌ Hủy bỏ"):
                    st.session_state.preview_action = None
                    st.rerun()