import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px

st.set_page_config(page_title="Debug Mode", layout="wide")
st.title("🛠️ OMNISENSE DEBUG MODE")
st.write("File này bỏ qua toàn bộ Cache để ép chọc trực tiếp vào Database.")

# 1. KẾT NỐI KHÔNG CACHE
engine = create_engine("postgresql://dss_user:CHANGE_ME_PASSWORD@localhost:5432/omnisense")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Test Trạng thái Đơn hàng")
    # Lấy data
    df_status = pd.read_sql("SELECT order_status, COUNT(order_id) as total_orders FROM orders GROUP BY order_status", engine)
    
    # Ép kiểu dữ liệu bằng tay cho chắc cú 100%
    df_status['total_orders'] = df_status['total_orders'].astype(int)
    
    # In cái bảng số liệu thật ra màn hình
    st.write("👉 Bảng Data gốc từ PostgreSQL:")
    st.dataframe(df_status)
    
    # Vẽ thử Pie Chart
    fig_status = px.pie(df_status, values='total_orders', names='order_status', title="Pie Chart Debug")
    fig_status.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig_status, use_container_width=True)

with col2:
    st.subheader("2. Test Doanh thu")
    # Lấy data
    df_trend = pd.read_sql("""
        SELECT SUBSTRING(o.order_purchase_timestamp, 1, 7) as month, 
               SUM(p.payment_value) as raw_revenue
        FROM orders o 
        JOIN order_payments p ON o.order_id = p.order_id
        WHERE o.order_status = 'delivered'
        GROUP BY month 
        ORDER BY month
    """, engine)
    
    # Xử lý phép chia 1 triệu bằng Python (Pandas) thay vì SQL để tránh lỗi float
    df_trend['raw_revenue'] = df_trend['raw_revenue'].astype(float)
    df_trend['revenue_millions'] = df_trend['raw_revenue'] / 1000000.0
    
    # In cái bảng số liệu thật ra màn hình
    st.write("👉 Bảng Data gốc từ PostgreSQL:")
    st.dataframe(df_trend)
    
    # Vẽ thử Line Chart
    fig_trend = px.line(df_trend, x='month', y='revenue_millions', title="Line Chart Debug", markers=True)
    st.plotly_chart(fig_trend, use_container_width=True)