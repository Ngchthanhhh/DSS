"""
PHASE 2 - TUẦN 4: RANDOM FOREST CHURN MODEL [VERSION 2 - ÉP XUNG]
- Bổ sung Features mới: avg_delivery_delay (Độ trễ giao hàng), avg_freight_value (Phí ship).
- Xóa phao thi: recency_days (Chống Data Leakage).
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
import shap
import pickle
import time
import warnings
warnings.filterwarnings('ignore')

def train_churn_model_v2():
    print("🚀 [VERSION 2] Ép xung AI Random Forest - Dự đoán khách hàng rời bỏ (Churn)...")
    start_time = time.time()

    # 1. Kết nối Database
    engine = create_engine("postgresql://dss_user:CHANGE_ME_PASSWORD@postgres_db:5432/omnisense")
    
    # 2. Extract Data (Bơm thêm Phí Ship và Lịch sử Giao hàng)
    print("⏳ Đang truy xuất dữ liệu nâng cao từ PostgreSQL...")
    query = """
        SELECT 
            o.customer_id,
            MAX(o.order_purchase_timestamp) as last_purchase_date,
            COUNT(DISTINCT o.order_id) as frequency,
            SUM(p.payment_value) as monetary,
            AVG(r.review_score) as avg_review_score,
            AVG(i.freight_value) as avg_freight_value,
            AVG(EXTRACT(DAY FROM (o.order_delivered_customer_date - o.order_estimated_delivery_date))) as avg_delivery_delay
        FROM orders o
        JOIN order_payments p ON o.order_id = p.order_id
        JOIN order_items i ON o.order_id = i.order_id
        LEFT JOIN order_reviews r ON o.order_id = r.order_id
        WHERE o.order_status = 'delivered'
        GROUP BY o.customer_id
    """
    df = pd.read_sql(query, engine)
    df['last_purchase_date'] = pd.to_datetime(df['last_purchase_date'])

    # 3. Kỹ nghệ đặc trưng (Feature Engineering)
    print("⏳ Đang xử lý Missing Data...")
    current_date = df['last_purchase_date'].max()
    df['recency_days'] = (current_date - df['last_purchase_date']).dt.days
    
    # Fill các giá trị NaN bằng Median
    df['avg_review_score'] = df['avg_review_score'].fillna(df['avg_review_score'].median())
    df['avg_delivery_delay'] = df['avg_delivery_delay'].fillna(df['avg_delivery_delay'].median())
    df['avg_freight_value'] = df['avg_freight_value'].fillna(df['avg_freight_value'].median())

    # 4. GÁN NHÃN (LABELING)
    df['is_churn'] = np.where(df['recency_days'] > 180, 1, 0)
    
    # 5. CHUẨN BỊ TẬP HUẤN LUYỆN (ĐÃ CẤT PHAO THI)
    features = ['frequency', 'monetary', 'avg_review_score', 'avg_freight_value', 'avg_delivery_delay']
    X = df[features].copy()
    y = df['is_churn']

    # 6. Train/Test Split
    print("✂️ Chia tập dữ liệu 80% Train - 20% Test...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    neg_class = len(y_train[y_train == 0])
    pos_class = len(y_train[y_train == 1])
    class_weight = {0: 1, 1: neg_class / pos_class}

    # 7. Huấn luyện Random Forest (Tăng cây, Tăng chiều sâu)
    print("🧠 Đang huấn luyện Rừng ngẫu nhiên (Random Forest) Version 2...")
    model = RandomForestClassifier(
        n_estimators=200, # Tăng số lượng cây quyết định
        max_depth=8,      # Tăng độ sâu cho AI tư duy
        class_weight=class_weight,
        random_state=42,
        n_jobs=-1 
    )
    model.fit(X_train, y_train)

    # 8. Đánh giá
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    
    print("\n📊 KẾT QUẢ ĐÁNH GIÁ (EVALUATION METRICS):")
    print(classification_report(y_test, y_pred))
    print(f"🎯 AUC-ROC Score: {roc_auc_score(y_test, y_prob):.4f}")

    # 9. Tích hợp SHAP Explainer
    explainer = shap.TreeExplainer(model, feature_perturbation="tree_path_dependent")
    
    # 10. Lưu Model
    print("💾 Đang xuất file model .pkl...")
    with open('rf_churn_model.pkl', 'wb') as f:
        pickle.dump({
            'model': model,
            'features': features,
            'explainer': explainer
        }, f)
    
    end_time = time.time()
    print(f"🎉 HOÀN THÀNH HUẤN LUYỆN V2! Tổng thời gian: {round(end_time - start_time, 2)} giây.")

if __name__ == "__main__":
    train_churn_model_v2()