FROM python:3.11-slim

WORKDIR /app

# Cài đặt trình biên dịch C++ lõi (nhẹ hều)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements trước để tận dụng cache
COPY requirements.txt .

# Nâng cấp pip lên bản mới nhất để chống lỗi Hash Mismatch
RUN pip install --upgrade pip

# Cài đặt thư viện (Đã tháo cờ no-cache-dir để an toàn hơn)
RUN pip install -r requirements.txt

# Copy phần code còn lại (đã bị chặn rác bởi .dockerignore)
COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]