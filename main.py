import pandas as pd
from crawler import Crawler
import logging
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    # Banner khởi động
    logger.info("=" * 100)
    logger.info("🚀 KHỞI ĐỘNG CHƯƠNG TRÌNH CRAWL KIỂU DÁNG CÔNG NGHIỆP - NOIP VIETNAM")
    logger.info("=" * 100)

    driver_path = "chromedriver-win64/chromedriver.exe"
    excel_path = "data_kdcn_bo_sung.xlsx"
    restart_interval = 100  # Khởi động lại driver sau mỗi 100 lần tìm kiếm

    logger.info(f"⚙️  CẤU HÌNH:")
    logger.info(f"   • ChromeDriver: {driver_path}")
    logger.info(f"   • File input: {excel_path}")
    logger.info(f"   • Restart interval: {restart_interval} lần tìm kiếm")
    logger.info(f"   • Loại crawl: DESIGNS (Kiểu dáng công nghiệp)")
    logger.info("")
    logger.info(f"📂 CẤU TRÚC THƯ MỤC OUTPUT:")
    logger.info(f"   Output_Designs/")
    logger.info(f"   ├── designs_data.xlsx          (File Excel chứa dữ liệu)")
    logger.info(f"   ├── Images/                    (Thư mục ảnh kiểu dáng)")
    logger.info(f"   │   ├── [Số đơn 1]/")
    logger.info(f"   │   ├── [Số đơn 2]/")
    logger.info(f"   │   └── ...")
    logger.info(f"   └── Errors/                    (Screenshot lỗi - nếu có)")
    logger.info(f"       ├── phase_1_exception/")
    logger.info(f"       ├── phase_2_timeout/")
    logger.info(f"       └── phase_3_other/")
    logger.info("")

    crawler = Crawler(driver_path, excel_path, restart_interval)

    try:
        sheet_name = 0
        data = pd.read_excel(excel_path, sheet_name=sheet_name)
        column_name = "filing_number"  # Đảm bảo đây là tên cột chính xác

        logger.info(f"📖 ĐỌC DỮ LIỆU INPUT:")
        logger.info(f"   • Sheet: {sheet_name}")
        logger.info(f"   • Cột số đơn: {column_name}")
        logger.info(f"   • Tổng số dòng trong file: {len(data)}")

        start_index = 0
        if crawler.last_so_don:
            start_index = data[data[column_name] == crawler.last_so_don].index[0] + 1
            logger.info(f"   • Tiếp tục từ số đơn: {crawler.last_so_don}")
            logger.info(f"   • Bắt đầu từ dòng: {start_index + 1}")

        total_searches = len(data) - start_index
        logger.info(f"   • Số đơn cần crawl: {total_searches}")
        logger.info("")
        logger.info("=" * 100)
        logger.info("🎯 BẮT ĐẦU CRAWL DỮ LIỆU")
        logger.info("=" * 100)
        logger.info("")

        with tqdm(
            total=total_searches, desc="⏳ Tiến trình crawl", unit=" đơn"
        ) as pbar:
            for index in range(start_index, len(data)):
                row = data.iloc[index]
                search_value = row[column_name]
                logger.info(f"📌 Đơn {index + 1 - start_index}/{total_searches}")
                crawler.process_search(search_value)
                pbar.update(1)

    finally:
        logger.info("")
        logger.info("=" * 100)
        logger.info("🏁 ĐÓNG TRÌNH DUYỆT")
        logger.info("=" * 100)
        crawler.close_driver()

    logger.info("")
    logger.info("=" * 100)
    logger.info("✅ HOÀN TẤT! Quá trình crawl đã kết thúc.")
    logger.info(f"📁 KIỂM TRA KẾT QUẢ TẠI THỦ MỤC: Output_Designs/")
    logger.info(f"   • File Excel dữ liệu: Output_Designs/designs_data.xlsx")
    logger.info(f"   • Thư mục ảnh kiểu dáng: Output_Designs/Images/")
    logger.info(f"   • Screenshot lỗi (nếu có): Output_Designs/Errors/")
    logger.info(f"     - phase_1_exception: Lỗi exception chung")
    logger.info(f"     - phase_2_timeout: Lỗi timeout không tìm thấy")
    logger.info(f"     - phase_3_other: Lỗi khác")
    logger.info("=" * 100)


if __name__ == "__main__":
    main()
