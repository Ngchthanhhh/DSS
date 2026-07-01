import os
import re

def audit_agents_only():
    print("🔍 [CHẾ ĐỘ KIỂM TRA - DRY RUN] Đang quét toàn bộ dự án...")
    print("⚠️ Yên tâm, script này CHỈ ĐỌC và BÁO CÁO, tuyệt đối không sửa/ghi đè 1 dòng code nào!\n")
    
    found_files = []
    
    # Bắt đầu quét lùng sục mọi ngóc ngách trong thư mục hiện tại
    for root, dirs, files in os.walk('.'):
        
        # 🛠 TỐI ƯU HÓA: Bỏ qua các thư mục lõi hệ thống và môi trường ảo để quét nhanh hơn
        if any(ignored in root for ignored in ['venv', '.git', '__pycache__', '.pytest_cache']):
            continue
            
        for file in files:
            # Chỉ check các file python và chừa mấy file cấu hình LLM ra
            if file.endswith('.py') and file not in ['llm_router.py', 'auto_sync_agents.py', 'check_models.py']:
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # 🎯 Kiểm tra xem file này có đang import thằng ChatOpenAI cũ rích không
                    if 'ChatOpenAI' in content and 'langchain_openai' in content:
                        found_files.append(filepath)
                        
                except Exception as e:
                    print(f"⚠️ Bỏ qua file {filepath} (Lỗi đọc file: {e})")
    
    # IN BÁO CÁO TỔNG KẾT
    print("-" * 60)
    if len(found_files) == 0:
        print("✅ Tuyệt vời! Không tìm thấy file nào đang xài thư viện Agent cũ.")
    else:
        print(f"🚨 PHÁT HIỆN {len(found_files)} FILE ĐANG XÀI API CŨ CẦN ĐƯỢC NÂNG CẤP:")
        for idx, fpath in enumerate(found_files, 1):
            print(f"   ➤ {idx}. {fpath}")
            
    print("-" * 60)
    print("\n💡 Sếp hãy check kỹ danh sách các file trên.")
    print("Nếu danh sách này hoàn toàn chuẩn xác và không bị dính file lạ, sếp cứ hú một tiếng tui sẽ bật CÔNG TẮC GHI (WRITE MODE) để nó tự động thay máu hàng loạt nhé!")

if __name__ == '__main__':
    audit_agents_only()