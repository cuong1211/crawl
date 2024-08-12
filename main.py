import pandas as pd
from crawler import Crawler
import logging
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    driver_path = "chromedriver-win64/chromedriver.exe"
    excel_path = "all.xls"
    restart_interval = 100  # Khởi động lại driver sau mỗi 100 lần tìm kiếm

    crawler = Crawler(driver_path, excel_path, restart_interval)

    try:
        sheet_name = 3
        data = pd.read_excel(excel_path, sheet_name=sheet_name)
        column_name = "Sốđơn"  # Đảm bảo đây là tên cột chính xác

        start_index = 0
        if crawler.last_so_don:
            start_index = data[data[column_name] == crawler.last_so_don].index[0] + 1

        total_searches = len(data) - start_index

        with tqdm(
            total=total_searches, desc="Tiến trình crawl", unit="tìm kiếm"
        ) as pbar:
            for index in range(start_index, len(data)):
                row = data.iloc[index]
                search_value = row[column_name]
                crawler.process_search(search_value)
                pbar.update(1)

    finally:
        crawler.close_driver()

    logger.info("Quá trình crawl đã hoàn tất.")


if __name__ == "__main__":
    main()
