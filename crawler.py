import os
import re
import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException


class Crawler:
    def __init__(self, driver_path, excel_path):
        self.driver_path = driver_path
        self.excel_path = excel_path
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless")  # Chạy chế độ ẩn
        # Cập nhật Service và WebDriver
        self.service = Service(executable_path=self.driver_path)
        self.driver = webdriver.Chrome(
            service=self.service, options=self.chrome_options
        )
        self.excel_folder = "ExcelFiles"
        os.makedirs(self.excel_folder, exist_ok=True)

        # Đặt tên file Excel
        self.excel_file_path = os.path.join(self.excel_folder, "kdcn.xlsx")

        # Khởi tạo danh sách dữ liệu
        self.data = []

    def stop_driver(self):
        if self.driver is not None:
            self.driver.quit()
            self.driver = None

    def process_search(self, search_value):
        start_time = time.time()
        print(f"Đang tìm kiếm số đơn {search_value}")

        base_folder = "Images"
        error_folder = os.path.join(base_folder, "Errors")
        text_folder = "TextFiles"

        # Đảm bảo tất cả các thư mục đều tồn tại
        os.makedirs(base_folder, exist_ok=True)
        os.makedirs(error_folder, exist_ok=True)
        os.makedirs(
            text_folder, exist_ok=True
        )  # Tạo thư mục text_folder nếu chưa tồn tại

        folder_name = os.path.join(base_folder, search_value.replace("/", "_"))
        os.makedirs(folder_name, exist_ok=True)
        text_file_path = os.path.join(text_folder, f"{search_value}.txt")

        try:
            self.driver.get(
                "http://wipopublish.ipvietnam.gov.vn/wopublish-search/public/designs?18&query=*:*"
            )
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.NAME,
                        "advancedInputWrapper:advancedInputsList:1:advancedInputSearchPanel:input",
                    )
                )
            )
            print("Đã mở trang web")

            input_field = self.driver.find_element(
                By.NAME,
                "advancedInputWrapper:advancedInputsList:1:advancedInputSearchPanel:input",
            )
            input_field.send_keys(search_value)
            input_field.send_keys(Keys.RETURN)

            retry_attempts = 3
            while retry_attempts > 0:
                try:
                    WebDriverWait(self.driver, 30).until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//a[.//img[contains(@class, 'rs-DRAWING')]]")
                        )
                    )
                    link_elements = self.driver.find_elements(
                        By.XPATH, "//a[.//img[contains(@class, 'rs-DRAWING')]]"
                    )
                    print(f"Đã tìm thấy {len(link_elements)} liên kết")

                    if link_elements:
                        first_link = link_elements[0]
                        first_link.click()
                        print("Đã nhấp vào liên kết đầu tiên")

                        try:
                            detail_container = WebDriverWait(self.driver, 30).until(
                                EC.presence_of_element_located(
                                    (
                                        By.XPATH,
                                        "//div[contains(@class, 'detail-container') and contains(@class, 'col-md-12')]",
                                    )
                                )
                            )
                            html = detail_container.get_attribute("outerHTML")
                            soup = BeautifulSoup(html, "html.parser")

                            rows = soup.find_all("div", class_="row")
                            # Tạo từ điển để lưu trữ dữ liệu
                            row_data = {}
                            for row in rows:
                                # Tìm tất cả các div có class "product-form-label" và "product-form-details"
                                label_divs = row.find_all(
                                    "div", class_="product-form-label"
                                )
                                details_divs = row.find_all(
                                    "div", class_="product-form-details"
                                )
                                # Ghép cặp các div lại với nhau và xử lý
                                for label_div, details_div in zip(
                                    label_divs, details_divs
                                ):
                                    if label_div and details_div:
                                        # Loại bỏ ký tự trong ngoặc ở đầu
                                        label_text = re.sub(
                                            r"^\([^)]*\)\s*",
                                            "",
                                            label_div.get_text(strip=True),
                                        )
                                        details_text = details_div.get_text(strip=True)

                                        # Xử lý các trường hợp đặc biệt
                                        if label_text == "Số bằng và ngày cấp":
                                            spans = details_div.find_all("span")
                                            if len(spans) == 2:
                                                row_data["Số bằng"] = spans[0].get_text(
                                                    strip=True
                                                )
                                                row_data["Ngày cấp"] = spans[
                                                    1
                                                ].get_text(strip=True)
                                        elif label_text == "Số đơn và Ngày nộp đơn":
                                            spans = details_div.find_all("span")
                                            if len(spans) == 2:
                                                row_data["Số đơn"] = (
                                                    spans[0]
                                                    .get_text(strip=True)
                                                    .lstrip("VN")
                                                )
                                                row_data["Ngày nộp đơn"] = spans[
                                                    1
                                                ].get_text(strip=True)
                                        else:
                                            row_data[label_text] = details_text
                            # Chỉ thêm vào danh sách nếu có dữ liệu
                            if row_data:
                                self.data.append(row_data)

                            break
                        except Exception as e:
                            print(f"Đã xảy ra lỗi khi crawl dữ liệu: {e}")
                            retry_attempts -= 1
                            self.driver.save_screenshot(
                                os.path.join(
                                    error_folder, f"{search_value}_data_error.png"
                                )
                            )
                            time.sleep(5)
                    else:
                        print("Không tìm thấy liên kết có ảnh 'rs-DRAWING'")
                        retry_attempts -= 1
                        time.sleep(5)

                except TimeoutException as e:
                    print(f"Không tìm thấy kết quả tìm kiếm: {e}")
                    self.driver.save_screenshot(
                        os.path.join(error_folder, f"{search_value}_error.png")
                    )
                    retry_attempts -= 1
                    time.sleep(5)
        except Exception as e:
            print(f"Đã xảy ra lỗi: {e}")
            self.driver.save_screenshot(
                os.path.join(error_folder, f"{search_value}_error.png")
            )

        finally:
            end_time = time.time()
            elapsed_time = end_time - start_time
            print("-" * 40)
            print(
                f"Quá trình xử lý mất: {elapsed_time:.2f} giây cho số đơn {search_value}"
            )
            print("-" * 40)

            if self.data:
                # Thêm cột "STT" vào dữ liệu
                for index, row in enumerate(self.data, start=1):
                    row["STT"] = index

                # Đổi vị trí cột "STT" để nó nằm ở đầu
                df = pd.DataFrame(self.data)
                columns = ["STT"] + [col for col in df.columns if col != "STT"]
                df = df[columns]

                df.to_excel(self.excel_file_path, index=False)
                print(f"Dữ liệu đã được lưu vào {self.excel_file_path}")
            else:
                print("Không có dữ liệu để lưu.")
            self.stop_driver()
