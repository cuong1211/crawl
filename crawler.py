import os
import re
import time
import pandas as pd
import requests
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
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--incognito")
        self.chrome_options.add_argument("--disable-extensions")
        self.chrome_options.add_argument("--window-size=1920,1080")
        # Cập nhật Service và WebDriver
        self.service = Service(executable_path=self.driver_path)
        self.driver = webdriver.Chrome(
            service=self.service, options=self.chrome_options
        )
        self.excel_folder = "ExcelFiles"
        os.makedirs(self.excel_folder, exist_ok=True)

        # Đặt tên file Excel
        self.excel_file_path = os.path.join(self.excel_folder, "nh.xlsx")

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
        error_folder = "Errors"
        error_folder_phase_1 = os.path.join(error_folder, "phase_1")
        error_folder_phase_2 = os.path.join(error_folder, "phase_2")
        error_folder_phase_3 = os.path.join(error_folder, "phase_3")

        # Đảm bảo tất cả các thư mục đều tồn tại
        os.makedirs(base_folder, exist_ok=True)
        os.makedirs(error_folder, exist_ok=True)
        os.makedirs(error_folder_phase_1, exist_ok=True)
        os.makedirs(error_folder_phase_2, exist_ok=True)
        os.makedirs(error_folder_phase_3, exist_ok=True)
        folder_name = os.path.join(base_folder, search_value.replace("/", "_"))
        os.makedirs(folder_name, exist_ok=True)

        image_paths = []  # Danh sách để lưu đường dẫn ảnh

        retry_attempts = 2
        while retry_attempts > 0:
            try:
                self.driver.get(
                    "http://wipopublish.ipvietnam.gov.vn/wopublish-search/public/trademarks?1&query=*:*"
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

                try:
                    a_tag = WebDriverWait(self.driver, 20).until(
                        EC.element_to_be_clickable(
                            (By.CSS_SELECTOR, "a.fa-file-text.fa-lg")
                        )
                    )
                    print(f"Đã tìm thấy thẻ liên kết")

                    if a_tag:
                        first_link = a_tag
                        first_link.click()
                        print("Đã nhấp vào liên kết đầu tiên")

                        try:
                            # Crawl dữ liệu chi tiết
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
                                        if (
                                            label_div.get_text(strip=True)
                                            == "(541) Nhãn hiệu"
                                        ):
                                            label_text = "Nhãn hiệu gốc"
                                        else:
                                            label_text = re.sub(
                                                r"^\([^)]*\)\s*",
                                                "",
                                                label_div.get_text(strip=True),
                                            )
                                        details_text = details_div.get_text(strip=True)

                                        # Xử lý các trường hợp đặc biệt
                                        if label_text == "Số bằng và ngày cấp":
                                            spans = details_div.find_all("span")
                                            if (
                                                len(spans) >= 2
                                            ):  # Kiểm tra danh sách trước khi truy cập
                                                row_data["Số bằng"] = spans[0].get_text(
                                                    strip=True
                                                )
                                                row_data["Ngày cấp"] = spans[
                                                    1
                                                ].get_text(strip=True)
                                            else:
                                                print(
                                                    f"Không đủ dữ liệu trong spans: {spans}"
                                                )
                                        elif label_text == "Số đơn và Ngày nộp đơn":
                                            spans = details_div.find_all("span")
                                            if len(spans) == 2:
                                                row_data["Số đơn"] = spans[0].get_text(
                                                    strip=True
                                                )
                                                row_data["Ngày nộp đơn"] = spans[
                                                    1
                                                ].get_text(strip=True)
                                        elif label_text == "Số công bố và ngày công bố":
                                            details_text = details_div.find(
                                                "div", class_="row"
                                            )
                                            content = details_text.find_all(
                                                "div", class_="col-md-4"
                                            )

                                            row_data["Số công bố"] = content[
                                                0
                                            ].get_text(strip=True)
                                            row_data["Ngày công bố"] = content[
                                                1
                                            ].get_text(strip=True)
                                        elif label_text == "Chủ đơn/Chủ bằng":
                                            contents = details_div.find_all("div", id="apnaDiv")
                                            
                                            # Đặt trước số cột là 5
                                            for idx in range(1, 6):
                                                if idx <= len(contents):
                                                    content = contents[idx - 1]
                                                    first_row = content.find("div", class_="row")
                                                    
                                                    if first_row:
                                                        raw_text = "".join(
                                                            [
                                                                text
                                                                for text in first_row.stripped_strings
                                                                if not text.startswith("(")
                                                            ]
                                                        )
                                                        parts = raw_text.split(":", 1)
                                                        
                                                        if len(parts) == 2:
                                                            row_data[f"Chủ đơn_{idx}"] = parts[0].strip()
                                                            row_data[f"Địa chỉ Chủ đơn_{idx}"] = parts[1].strip()
                                                        elif len(parts) == 1:
                                                            row_data[f"Chủ đơn_{idx}"] = parts[0].strip()
                                                            row_data[f"Địa chỉ Chủ đơn_{idx}"] = ""
                                                    else:
                                                        # Nếu không tìm thấy first_row, điền chuỗi rỗng
                                                        row_data[f"Chủ đơn_{idx}"] = ""
                                                        row_data[f"Địa chỉ Chủ đơn_{idx}"] = ""
                                                else:
                                                    # Nếu không đủ số lượng, điền chuỗi rỗng
                                                    row_data[f"Chủ đơn_{idx}"] = ""
                                                    row_data[f"Địa chỉ Chủ đơn_{idx}"] = ""
                                        elif label_text == "Đại diện SHCN":
                                            contents = details_div.find(
                                                "div", class_="row"
                                            )
                                            for content in contents:
                                                raw_text = "".join(
                                                    [
                                                        text
                                                        for text in content.stripped_strings
                                                        if not text.startswith("(")
                                                    ]
                                                )
                                                parts = raw_text.split(":", 1)
                                                if len(parts) == 2:
                                                    row_data["Đại diện SHCN"] = parts[
                                                        0
                                                    ].strip()
                                                    row_data["Địa chỉ đại diện"] = (
                                                        parts[1].strip()
                                                    )
                                        elif label_text == "Nhãn hiệu gốc":
                                            row_data[label_text] = re.sub(
                                                r"^\([^)]*\)\s*",
                                                "",
                                                details_text,
                                            )
                                        elif label_text == "Nhóm sản phẩm/dịch vụ":
                                            # Tìm tất cả các div có class là "row"
                                            rows = details_div.find_all("div", class_="row")
                                            
                                            # Đặt trước số cột là 5
                                            for idx in range(1, 10):
                                                if idx <= len(rows):
                                                    row = rows[idx - 1]
                                                    group_div = row.find("div", class_="col-md-2")
                                                    service_div = row.find("div", class_="col-md-10")
                                                    
                                                    if group_div and service_div:
                                                        group_text = group_div.get_text(strip=True)
                                                        service_text = service_div.get_text(strip=True)
                                                        
                                                        row_data[f"Nhóm sản phẩm_{idx}"] = group_text
                                                        row_data[f"Dịch vụ_{idx}"] = service_text
                                                    else:
                                                        # Nếu không có dữ liệu, điền vào chuỗi rỗng
                                                        row_data[f"Nhóm sản phẩm_{idx}"] = ""
                                                        row_data[f"Dịch vụ_{idx}"] = ""
                                                else:
                                                    # Nếu số lượng rows ít hơn 5, điền vào chuỗi rỗng
                                                    row_data[f"Nhóm sản phẩm_{idx}"] = ""
                                                    row_data[f"Dịch vụ_{idx}"] = ""
                                        else:
                                            row_data[label_text] = details_text
                                            # Chỉ thêm vào danh sách nếu có dữ liệu
                            if row_data:
                                self.data.append(row_data)

                            # Crawl ảnh
                            try:
                                WebDriverWait(self.driver, 10).until(
                                    EC.presence_of_element_located(
                                        (By.CSS_SELECTOR, "img.detail-img")
                                    )
                                )
                                print("Tìm thấy ảnh chi tiết!")

                                images = self.driver.find_elements(
                                    By.CSS_SELECTOR, "img.detail-img"
                                )
                                print(f"Đã tìm thấy {len(images)} ảnh")

                                for idx, img in enumerate(images):
                                    img_url = img.get_attribute("src")
                                    if img_url:
                                        try:
                                            img_data = requests.get(img_url).content
                                            img_name = f"{search_value}_{idx+1}.jpg"
                                            img_path = os.path.join(
                                                folder_name, img_name
                                            )
                                            image_paths.append(
                                                img_path
                                            )  # Thêm đường dẫn ảnh vào danh sách

                                            with open(img_path, "wb") as f:
                                                f.write(img_data)
                                            print(
                                                f"Đã lưu ảnh {img_name} tại {img_path}"
                                            )
                                        except Exception as e:
                                            print(f"Không thể tải ảnh {img_url}: {e}")
                                    else:
                                        print("URL ảnh không hợp lệ")
                                break
                            except Exception as e:
                                print(
                                    "Không tìm thấy ảnh chi tiết trong thời gian chờ."
                                )
                                break
                        except Exception as e:
                            print(f"Đã xảy ra lỗi khi crawl dữ liệu: {e}")
                            retry_attempts -= 1
                            self.driver.save_screenshot(
                                os.path.join(
                                    error_folder_phase_3,
                                    f"{search_value}_data_error.png",
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
                        os.path.join(error_folder_phase_2, f"{search_value}_error.png")
                    )
                    retry_attempts -= 1
                    self.driver.quit()
                    self.driver = webdriver.Chrome(
                        service=self.service, options=self.chrome_options
                    )
            except Exception as e:
                print(f"Đã xảy ra lỗi: {e}")
                retry_attempts -= 1
                self.driver.save_screenshot(
                    os.path.join(error_folder_phase_1, f"{search_value}_error.png")
                )
                self.driver.quit()
                self.driver = webdriver.Chrome(
                    service=self.service, options=self.chrome_options
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
                    # Thêm cột "STT" và "images" vào dữ liệu
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
