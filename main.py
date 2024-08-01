import pandas as pd
from crawler import Crawler


def main():
    driver_path = "chromedriver-win64/chromedriver.exe"  # Đường dẫn đến ChromeDriver
    excel_path = "excel.xls"  # Đường dẫn đến file Excel

    # Tạo đối tượng Crawler
    crawler = Crawler(driver_path, excel_path)
    # search_value = "3-2020-02667"
    # Đọc file Excel
    data = pd.read_excel(excel_path)
    for index, row in data.iterrows():
        search_value = row[1]  # Số đơn từ file Excel
        crawler.process_search(search_value)

        # Đóng trình điều khiển
    crawler.stop_driver()


if __name__ == "__main__":
    main()
