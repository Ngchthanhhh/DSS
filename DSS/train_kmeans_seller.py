"""
PHASE 2 - TUẦN 5: KMEANS SELLER CLUSTERING
- Thuật toán: Học không giám sát (KMeans) phân cụm 4 nhóm Seller[cite: 81].
- Features: avg_rating, total_orders, avg_delay_days, cancellation_rate, avg_order_value[cite: 80].
- Bổ sung: StandardScaler để chuẩn hóa dữ liệu & SHAP KernelExplainer[cite: 82].
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
import shap
import pickle
import time
import warnings
warnings.filterwarnings('ignore')

def train_seller_clustering():
    print("🚀 Bắt đầu huấn luyện AI KMeans - Phân loại Người bán (Seller Clustering)...")
    start_time = time.time()

    # 1. Kết nối Database
    engine = create_engine("postgresql://dss_user:CHANGE_ME_PASSWORD@postgres_db:5432/omnisense")
    
    # 2. Extract Data & Feature Engineering bằng SQL [cite: 80]
    print("⏳ Đang truy xuất và tính toán thông số Seller từ PostgreSQL...")
    query = """
        SELECT 
            i.seller_id,
            COUNT(DISTINCT o.order_id) as total_orders,
            AVG(i.price) as avg_order_value,
            AVG(r.review_score) as avg_rating,
            AVG(EXTRACT(EPOCH FROM (o.order_delivered_customer_date - o.order_estimated_delivery_date))/86400.0) as avg_delay_days,
            SUM(CASE WHEN o.order_status = 'canceled' THEN 1 ELSE 0 END) * 1.0 / COUNT(o.order_id) as cancellation_rate
        FROM order_items i
        JOIN orders o ON i.order_id = o.order_id
        LEFT JOIN order_reviews r ON o.order_id = r.order_id
        GROUP BY i.seller_id
        HAVING COUNT(DISTINCT o.order_id) > 5 -- Chỉ lấy những shop bán > 5 đơn để loại nhiễu
    """
    df = pd.read_sql(query, engine)

    # Xử lý Missing Data (Điền Median)
    print("⏳ Đang dọn dẹp dữ liệu (Handling Missing Values)...")
    df.fillna(df.median(numeric_only=True), inplace=True)

    # Chuẩn bị Features
    
    features = ['avg_rating', 'total_orders', 'avg_delay_days', 'cancellation_rate', 'avg_order_value']
    X = df[features].copy()

    # 3. Chuẩn hóa dữ liệu (Standardization) - Bước cực kỳ quan trọng cho KMeans
    print("⚖️ Đang chuẩn hóa dữ liệu bằng StandardScaler...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # 4. Huấn luyện KMeans (Tạo 4 cụm)
    print("🧠 Đang huấn luyện KMeans (Phân 4 cụm: Star, Average, At-Risk, Toxic)...")
    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
    df['cluster'] = kmeans.fit_predict(X_scaled)

    # 5. Đánh giá chất lượng phân cụm (Silhouette Score)
    score = silhouette_score(X_scaled, df['cluster'])
    print(f"\n📊 KẾT QUẢ ĐÁNH GIÁ:")
    print(f"🎯 Silhouette Score (Độ phân tách cụm): {score:.4f} (-1 đến 1, càng gần 1 càng tốt)")

    # 6. Hiển thị đặc điểm của từng cụm (Centroids) để gán nhãn sau này trên Web
    print("\n🔍 ĐẶC ĐIỂM TRUNG BÌNH CỦA TỪNG NHÓM (CENTROIDS):")
    cluster_summary = df.groupby('cluster')[features].mean().round(2)
    print(cluster_summary)

    # 7. Khởi tạo SHAP (Dùng KernelExplainer cho thuật toán học không giám sát) [cite: 82]
    print("\n🔍 Đang khởi tạo bộ giải thích SHAP KernelExplainer...")
    # Dùng một mẫu nhỏ (background data) để SHAP học tính toán cho nhanh
    background_data = shap.kmeans(X_scaled, 10)
    explainer = shap.KernelExplainer(kmeans.predict, background_data)

    # 8. Lưu Model, Scaler và Explainer
    print("💾 Đang xuất file model .pkl...")
    with open('kmeans_seller_model.pkl', 'wb') as f:
        pickle.dump({
            'model': kmeans,
            'scaler': scaler,
            'features': features,
            'explainer': explainer
        }, f)
    
    end_time = time.time()
    print(f"🎉 HOÀN THÀNH HUẤN LUYỆN KMEANS! Tổng thời gian: {round(end_time - start_time, 2)} giây.")

if __name__ == "__main__":
    train_seller_clustering()