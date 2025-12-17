import pandas as pd
from pathlib import Path
from crawler_trademarks import DesignCrawler

def print_banner():
    banner = """
    ╔═══════════════════════════════════════════════════════════════╗
    ║              DESIGN CRAWLER (DIRECT URL) - NOIP               ║
    ║              Vietnam Intellectual Property Office             ║
    ║                 Kiểu dáng công nghiệp - Designs               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def main():
    print_banner()

    # Cấu hình
    driver_path = "chromedriver-win64/chromedriver.exe"
    excel_path = "data_kdcn_bo_sung.xlsx"  # File chứa danh sách filing numbers
    column_name = "filing_number"  # Tên cột chứa số đơn

    print("⚙️  CẤU HÌNH:")
    print(f"   - ChromeDriver: {driver_path}")
    print(f"   - Input Excel: {excel_path}")
    print(f"   - Column: {column_name}")
    print(f"   - Output Folder: Output_Designs_Direct/")
    print()

    # Khởi tạo crawler
    crawler = DesignCrawler(driver_path, excel_path)

    # Đọc danh sách filing numbers từ Excel
    try:
        if Path(excel_path).exists():
            df = pd.read_excel(excel_path)

            # Lọc ra các filing number chưa crawl (nếu có last_so_don)
            if crawler.last_so_don:
                print(f"📍 Tiếp tục từ số công bố cuối: {crawler.last_so_don}")
                # Tìm index của last_so_don trong df (giả sử có cột filing_number)
                # Nếu muốn auto-resume, có thể check trong existing_data
                filing_numbers = df[column_name].tolist()
            else:
                filing_numbers = df[column_name].tolist()

            print(f"📋 Đã đọc {len(filing_numbers)} số đơn designs từ file Excel")
        else:
            print(f"❌ Không tìm thấy file {excel_path}")
            print(f"Vui lòng tạo file Excel với cột '{column_name}' chứa các số đơn cần crawl")
            return

    except Exception as e:
        print(f"❌ Lỗi khi đọc file Excel: {e}")
        return

    print()
    print("🚀 BẮT ĐẦU CRAWL...")
    print("=" * 80)
    print()

    # Chạy crawler
    crawler.run(filing_numbers)

    print()
    print("✅ HOÀN THÀNH!")
    print(f"📊 Kết quả đã lưu tại: Output_Designs_Direct/designs_data.xlsx")
    print(f"🖼️  Ảnh đã lưu tại: Output_Designs_Direct/Images/")
    print(f"❌ Lỗi (nếu có) tại: Output_Designs_Direct/Errors/")
    print()

if __name__ == "__main__":
    main()
