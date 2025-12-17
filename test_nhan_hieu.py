"""
Script test crawl 1 số đơn nhãn hiệu để debug
"""
from crawler_nhan_hieu import TrademarkCrawler

def main():
    print("=" * 80)
    print("TEST CRAWL 1 SỐ ĐƠN NHÃN HIỆU")
    print("=" * 80)
    print()

    # Cấu hình
    driver_path = "chromedriver-win64/chromedriver.exe"
    excel_path = "data_kdcn_bo_sung.xlsx"

    # Khởi tạo crawler
    print("Đang khởi tạo crawler...")
    try:
        crawler = TrademarkCrawler(driver_path, excel_path)
        print("✓ Khởi tạo crawler thành công!")
        print()

        # Test với 1 số đơn nhãn hiệu
        # VD: "4-2025-45534" hoặc bất kỳ số đơn nào bạn muốn test
        test_filing_number = "4-2025-45534"  # Thay số này theo số đơn thực của bạn
        print(f"🧪 Test crawl số đơn: {test_filing_number}")
        print()

        crawler.process_trademark(test_filing_number)

        print()
        print("✅ Test hoàn thành!")
        print(f"💾 File Excel: {crawler.excel_file_path}")

    except Exception as e:
        print(f"❌ LỖI: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'crawler' in locals():
            crawler.close_driver()

if __name__ == "__main__":
    main()
