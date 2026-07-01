"""
PHASE 2 - TUẦN 3: XGBOOST DELIVERY RISK MODEL (THEO ROADMAP OMNISENSE)
- Chuẩn bị data: Join orders, order_items, order_reviews, order_payments, products.
- Label: 1 nếu (giao trễ > 0 ngày VÀ review_score <= 2), ngược lại 0.
- Features: product_weight_g, payment_type, order_value, day_of_week, v.v.
- Model: XGBoost Classifier (80/20 split).
- Explainability: SHAP TreeExplainer.
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import shap
import pickle
import time
import warnings
warnings.filterwarnings('ignore')

def train_delivery_risk_model():
    print("🚀 Bắt đầu quá trình huấn luyện AI XGBoost - Delivery Risk...")
    start_time = time.time()

    # 1. Kết nối Database
    engine = create_engine("postgresql://dss_user:CHANGE_ME_PASSWORD@postgres_db:5432/omnisense")
    
    # 2. Extract & Join
    print("⏳ Đang truy xuất và Join dữ liệu từ PostgreSQL...")
    query = """
        SELECT 
            o.order_id,
            o.order_purchase_timestamp,
            o.order_estimated_delivery_date,
            o.order_delivered_customer_date,
            p.payment_type,
            p.payment_value AS order_value,
            pr.product_weight_g,
            r.review_score
        FROM orders o
        JOIN order_items i ON o.order_id = i.order_id
        JOIN order_payments p ON o.order_id = p.order_id
        JOIN products pr ON i.product_id = pr.product_id
        LEFT JOIN order_reviews r ON o.order_id = r.order_id
        WHERE o.order_status = 'delivered'
    """
    df = pd.read_sql(query, engine)
    
    df['order_purchase_timestamp'] = pd.to_datetime(df['order_purchase_timestamp'])
    df['order_estimated_delivery_date'] = pd.to_datetime(df['order_estimated_delivery_date'])
    df['order_delivered_customer_date'] = pd.to_datetime(df['order_delivered_customer_date'])

    # 3. Kỹ nghệ đặc trưng
    print("⏳ Đang kỹ nghệ đặc trưng (Feature Engineering)...")
    df['delivery_delay_days'] = (df['order_delivered_customer_date'] - df['order_estimated_delivery_date']).dt.days
    df['day_of_week'] = df['order_purchase_timestamp'].dt.dayofweek
    df['review_score'] = df['review_score'].fillna(5)
    df['product_weight_g'] = df['product_weight_g'].fillna(df['product_weight_g'].median())

    # 4. Labeling
    print("🏷️ Đang gán nhãn dữ liệu Risk (0 - Bình thường, 1 - Rủi ro cao)...")
    df['is_risk'] = np.where((df['delivery_delay_days'] > 0) & (df['review_score'] <= 2), 1, 0)
    
    features = ['product_weight_g', 'order_value', 'day_of_week', 'payment_type']
    X = df[features].copy()
    y = df['is_risk']

    le = LabelEncoder()
    X['payment_type'] = le.fit_transform(X['payment_type'])

    print("✂️ Chia tập dữ liệu 80% Train - 20% Test...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    # TÍNH TOÁN LẠI TỶ LỆ CÂN BẰNG DATA (FIX LỖI RECALL THẤP)
    neg_class = len(y_train[y_train == 0])
    pos_class = len(y_train[y_train == 1])
    dynamic_spw = neg_class / pos_class
    print(f"⚖️ Tỷ lệ mất cân bằng (Negative/Positive) là: {dynamic_spw:.2f}")

    print("🧠 Đang huấn luyện Mô hình XGBoost Classifier...")
    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        random_state=42,
        scale_pos_weight=dynamic_spw # Ép thuật toán phải học kỹ các đơn rủi ro
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    
    print("\n📊 KẾT QUẢ ĐÁNH GIÁ (EVALUATION METRICS):")
    print(classification_report(y_test, y_pred))
    print(f"🎯 AUC-ROC Score: {roc_auc_score(y_test, y_prob):.4f}")

    print("🔍 Khởi tạo SHAP TreeExplainer...")
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test.iloc[:50])
    
    print("💾 Đang xuất file model .pkl...")
    with open('xgboost_delivery_risk.pkl', 'wb') as f:
        pickle.dump({
            'model': model,
            'encoder': le,
            'features': features,
            'explainer': explainer # Lưu luôn explainer để web load nhanh hơn
        }, f)
    
    end_time = time.time()
    print(f"🎉 HOÀN THÀNH HUẤN LUYỆN! Tổng thời gian: {round(end_time - start_time, 2)} giây.")

if __name__ == "__main__":
    train_delivery_risk_model()