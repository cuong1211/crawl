"""
Script test crawl 1 số đơn để debug
"""
import pandas as pd
from pathlib import Path
from crawler_trademarks import DesignCrawler

def main():
    print("=" * 80)
    print("TEST CRAWL 1 SỐ ĐƠN")
    print("=" * 80)
    print()

    # Cấu hình
    driver_path = "chromedriver-win64/chromedriver.exe"
    excel_path = "data_kdcn_bo_sung.xlsx"

    # Khởi tạo crawler
    print("Đang khởi tạo crawler...")
    try:
        crawler = DesignCrawler(driver_path, excel_path)
        print("✓ Khởi tạo crawler thành công!")
        print()

        # Test với 1 số đơn
        test_filing_number = "3-1993-01426"
        print(f"🧪 Test crawl số đơn: {test_filing_number}")
        print()

        crawler.process_design(test_filing_number)

        print()
        print("✅ Test hoàn thành!")

    except Exception as e:
        print(f"❌ LỖI: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'crawler' in locals():
            crawler.close_driver()

if __name__ == "__main__":
    main()
