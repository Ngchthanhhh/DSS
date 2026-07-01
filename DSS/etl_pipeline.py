import pandas as pd
from sqlalchemy import create_engine
import os
import time

def run_etl():
    print("🚀 Bắt đầu quá trình ETL Pipeline...")
    start_time = time.time()
    
    # 1. Kết nối DB bằng tên service 'postgres_db'
    engine = create_engine("postgresql://dss_user:CHANGE_ME_PASSWORD@postgres_db:5432/omnisense")
    
    # Thư mục chứa các file CSV của Olist (nhớ để file csv vào thư mục data/)
    data_dir = "data/" 
    
    # Mapping tên file CSV thành tên bảng trong PostgreSQL
    tables = {
        "olist_customers_dataset.csv": "customers",
        "olist_geolocation_dataset.csv": "geolocation",
        "olist_order_items_dataset.csv": "order_items",
        "olist_order_payments_dataset.csv": "order_payments",
        "olist_order_reviews_dataset.csv": "order_reviews",
        "olist_orders_dataset.csv": "orders",
        "olist_products_dataset.csv": "products",
        "olist_sellers_dataset.csv": "sellers",
        "product_category_name_translation.csv": "category_translation"
    }

    for file_name, table_name in tables.items():
        file_path = os.path.join(data_dir, file_name)
        if os.path.exists(file_path):
            print(f"⏳ Đang xử lý bảng: {table_name}...")
            df = pd.read_csv(file_path)
            
            # FIX BUG DATATYPE THEO LỜI CLAUDE: Ép kiểu thời gian trước khi đưa vào DB
            if table_name == "orders":
                timestamp_cols = [
                    'order_purchase_timestamp', 'order_approved_at',
                    'order_delivered_carrier_date', 'order_delivered_customer_date',
                    'order_estimated_delivery_date'
                ]
                for col in timestamp_cols:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col], errors='coerce')
            elif table_name == "order_reviews":
                review_time_cols = ['review_creation_date', 'review_answer_timestamp']
                for col in review_time_cols:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col], errors='coerce')

            # Loại bỏ dòng trùng lặp
            df.drop_duplicates(inplace=True)
            
            # Đẩy vào PostgreSQL
            # Lưu ý cho Báo cáo: Dùng "replace" cho giai đoạn Seed Data (Init). Khi lên Production thực tế sẽ dùng "append"
            df.to_sql(table_name, engine, if_exists="replace", index=False)
            print(f"✅ Đã nạp xong {len(df)} dòng vào bảng {table_name}")
        else:
            print(f"❌ Không tìm thấy file: {file_path}")

    end_time = time.time()
    print(f"🎉 HOÀN THÀNH ETL! Tổng thời gian: {round(end_time - start_time, 2)} giây.")

if __name__ == "__main__":
    run_etl()