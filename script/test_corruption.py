from __future__ import annotations

from pathlib import Path
import sys

# Thêm thư mục src vào PATH của python
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root / "src"))
sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
from core.config import load_settings
from ingestion.corruption import corrupt_clean_dataframe
from core.utils import read_json

def main():
    print("====================================================")
    print("           KIỂM THỬ MÔ PHỎNG DỮ LIỆU LỖI            ")
    print("====================================================")
    
    settings = load_settings(project_root)
    clean_csv_path = settings.paths.clean_csv
    
    if not clean_csv_path.exists():
        print(f" [!] Không tìm thấy file dữ liệu sạch baseline: {clean_csv_path}")
        print(" Vui lòng chạy kiểm thử Ingestion & Cleaning trước.")
        return
        
    print(f"\n[Bước 1] Đọc dữ liệu sạch baseline...")
    df_clean = pd.read_csv(clean_csv_path)
    print(f"   => Kích thước gốc: {df_clean.shape}")
    
    print("\n[Bước 2] Chạy hàm mô phỏng dữ liệu lỗi (corruption)...")
    log_path = settings.paths.corruption_log
    df_corrupted = corrupt_clean_dataframe(df_clean, log_path)
    print(f"   => Kích thước sau phá hoại: {df_corrupted.shape}")
    
    print("\n[Bước 3] Kiểm định các lỗi dữ liệu đã tạo:")
    
    # 1. Kiểm tra Drop records
    dropped = len(df_clean) - (len(df_corrupted) - 2)  # -2 vì có thêm 2 dòng duplicate ở cuối
    print(f"   - Số dòng bị loại bỏ (drop latest): {dropped} dòng")
    
    # 2. Kiểm tra Blank summary
    blank_sums = (df_corrupted["summary"].isna() | (df_corrupted["summary"].astype(str).str.strip() == "")).sum()
    print(f"   - Số dòng bị làm trống summary     : {blank_sums} dòng")
    assert blank_sums > 0, "Không tạo được lỗi blank summary!"
    
    # 3. Kiểm tra Noise injection
    noise_rows = df_corrupted["summary"].str.contains("GIBBERISH_NOISE_123", na=False).sum()
    print(f"   - Số dòng bị gieo ký tự nhiễu       : {noise_rows} dòng")
    assert noise_rows > 0, "Không tạo được lỗi noise injection!"
    
    # 4. Kiểm tra Truncate title / Blank title
    blank_titles = (df_corrupted["title"].isna() | (df_corrupted["title"].astype(str).str.strip() == "")).sum()
    print(f"   - Số dòng bị làm trống/cắt ngắn title: {blank_titles} dòng")
    assert blank_titles > 0, "Không tạo được lỗi blank title!"
    
    # 5. Kiểm tra Stale published date
    stale_rows = (df_corrupted["published"] == "2000-01-01").sum()
    print(f"   - Số dòng bị đổi ngày xuất bản cũ đi: {stale_rows} dòng")
    assert stale_rows > 0, "Không tạo được lỗi stale publication date!"
    
    # 6. Kiểm tra Duplicate rows
    duplicates = len(df_corrupted) - df_corrupted["paper_id"].nunique()
    print(f"   - Số dòng trùng lặp khóa chính DOI   : {duplicates} dòng")
    assert duplicates > 0, "Không tạo được trùng lặp khóa chính!"
    
    print("\n[Bước 4] Kiểm tra tệp tin nhật ký phá hoại (corruption log)...")
    if log_path.exists():
        log_data = read_json(log_path)
        print(f"   => Đã ghi nhận log tại: {log_path.relative_to(project_root)}")
        print(f"   => Nội dung log: {log_data}")
    else:
        print(" [!] Thất bại: Không tìm thấy file log.")
        sys.exit(1)
        
    print("\n====================================================")
    print("    CHÚC MỪNG: KIỂM THỬ CORRUPTION THÀNH CÔNG!     ")
    print("====================================================")

if __name__ == "__main__":
    main()
