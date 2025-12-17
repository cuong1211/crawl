"""
Main script để crawl Nhãn hiệu từ file Excel
"""
import pandas as pd
from pathlib import Path
from crawler_nhan_hieu import TrademarkCrawler
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    # Cấu hình
    driver_path = "chromedriver-win64/chromedriver.exe"
    excel_path = "data_kdcn_bo_sung.xlsx"  # File Excel chứa danh sách số đơn

    logger.info("=" * 80)
    logger.info("BẮT ĐẦU CRAWL NHÃN HIỆU")
    logger.info("=" * 80)

    try:
        # Đọc file Excel
        df = pd.read_excel(excel_path)
        filing_numbers = df['filing_number'].tolist()

        logger.info(f"📋 Tổng số đơn cần crawl: {len(filing_numbers)}")
        logger.info("")

        # Khởi tạo crawler
        crawler = TrademarkCrawler(driver_path, excel_path)

        # Crawl từng số đơn
        for idx, filing_number in enumerate(filing_numbers, start=1):
            logger.info(f"📌 [{idx}/{len(filing_numbers)}] Đang xử lý: {filing_number}")
            crawler.process_trademark(filing_number)

        # Lưu dữ liệu vào Excel
        crawler.save_data_to_excel()

        logger.info("")
        logger.info("=" * 80)
        logger.info("✅ HOÀN THÀNH TẤT CẢ!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ LỖI: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if 'crawler' in locals():
            crawler.close_driver()


if __name__ == "__main__":
    main()
