import pandas as pd
from crawler import Crawler


def main():
    driver_path = "chromedriver-win64/chromedriver.exe"  # Đường dẫn đến ChromeDriver
    excel_path = "excel.xls"  # Đường dẫn đến file Excel

    # Tạo đối tượng Crawler cho cả dữ liệu và ảnh
    crawler = Crawler(driver_path, excel_path)
    sheet_name = 0  # Số thứ tự sheet bắt đầu từ 0

# Đọc chỉ cột U từ sheet thứ 3
    data = pd.read_excel(excel_path, sheet_name=sheet_name)

# Hiển thị dữ liệu
    for index, row in data.iterrows():
        # Gọi phương thức để xử lý dữ liệu
        
        search_value = row[1]  # Số đơn từ file Excel
            # print(search_value)
        crawler.process_search(search_value)

        # Gọi phương thức để tải ảnh (giả sử phương thức là `download_images`)

    # Đóng trình điều khiển
    crawler.stop_driver()


if __name__ == "__main__":
    main()
