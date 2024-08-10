import os
import re
import time
import pandas as pd
import requests
import logging
from pathlib import Path
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Crawler:
    def __init__(self, driver_path, excel_path, restart_interval=100):
        self.driver_path = Path(driver_path)
        self.excel_path = Path(excel_path)
        self.excel_folder = Path("ExcelFiles")
        self.excel_folder.mkdir(exist_ok=True)
        self.excel_file_path = self.excel_folder / "nh.xlsx"
        self.data = []
        self.restart_interval = restart_interval
        self.search_count = 0
        self.load_existing_data()
        self.init_driver()

    def init_driver(self):
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--incognito")
        self.chrome_options.add_argument("--disable-extensions")
        self.chrome_options.add_argument("--window-size=1920,1080")
        self.service = Service(executable_path=self.driver_path)
        self.driver = webdriver.Chrome(
            service=self.service, options=self.chrome_options
        )

    def load_existing_data(self):
        if self.excel_file_path.exists():
            self.existing_data = pd.read_excel(self.excel_file_path)
            self.last_so_don = (
                self.existing_data["Số công bố"].iloc[-1]
                if not self.existing_data.empty
                else None
            )
        else:
            self.existing_data = pd.DataFrame()
            self.last_so_don = None

    def close_driver(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

    def restart_driver(self):
        self.close_driver()
        self.init_driver()
        self.search_count = 0
        logger.info("Driver đã được khởi động lại.")

    def search_and_click(self, search_value):
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
        input_field = self.driver.find_element(
            By.NAME,
            "advancedInputWrapper:advancedInputsList:1:advancedInputSearchPanel:input",
        )
        input_field.send_keys(search_value)
        input_field.send_keys(Keys.RETURN)
        a_tag = WebDriverWait(self.driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.fa-file-text.fa-lg"))
        )
        a_tag.click()

    def extract_data(self, detail_container):
        html = detail_container.get_attribute("outerHTML")
        soup = BeautifulSoup(html, "html.parser")
        rows = soup.find_all("div", class_="row")
        row_data = {}

        for row in rows:
            label_divs = row.find_all("div", class_="product-form-label")
            details_divs = row.find_all("div", class_="product-form-details")
            for label_div, details_div in zip(label_divs, details_divs):
                if label_div and details_div:
                    label_text = re.sub(
                        r"^\([^)]*\)\s*", "", label_div.get_text(strip=True)
                    )
                    details_text = details_div.get_text(strip=True)

                    if label_text == "Số bằng và ngày cấp":
                        spans = details_div.find_all("span")
                        if len(spans) >= 2:
                            row_data["Số bằng"] = spans[0].get_text(strip=True)
                            row_data["Ngày cấp"] = spans[1].get_text(strip=True)
                    elif label_text == "Số đơn và Ngày nộp đơn":
                        spans = details_div.find_all("span")
                        if len(spans) == 2:
                            row_data["Số đơn"] = spans[0].get_text(strip=True)
                            row_data["Ngày nộp đơn"] = spans[1].get_text(strip=True)
                    elif label_text == "Số công bố và ngày công bố":
                        details_text = details_div.find("div", class_="row")
                        content = details_text.find_all("div", class_="col-md-4")
                        row_data["Số công bố"] = content[0].get_text(strip=True)
                        row_data["Ngày công bố"] = content[1].get_text(strip=True)
                    elif label_text == "Chủ đơn/Chủ bằng":
                        contents = details_div.find_all("div", id="apnaDiv")
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
                                        row_data[f"Địa chỉ Chủ đơn_{idx}"] = parts[
                                            1
                                        ].strip()
                                    elif len(parts) == 1:
                                        row_data[f"Chủ đơn_{idx}"] = parts[0].strip()
                                        row_data[f"Địa chỉ Chủ đơn_{idx}"] = ""
                            else:
                                row_data[f"Chủ đơn_{idx}"] = ""
                                row_data[f"Địa chỉ Chủ đơn_{idx}"] = ""
                    elif label_text == "Đại diện SHCN":
                        contents = details_div.find("div", class_="row")
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
                                row_data["Đại diện SHCN"] = parts[0].strip()
                                row_data["Địa chỉ đại diện"] = parts[1].strip()
                    elif label_text == "Nhóm sản phẩm/dịch vụ":
                        rows = details_div.find_all("div", class_="row")
                        for idx in range(1, 10):
                            if idx <= len(rows):
                                row = rows[idx - 1]
                                group_div = row.find("div", class_="col-md-2")
                                service_div = row.find("div", class_="col-md-10")
                                if group_div and service_div:
                                    row_data[f"Nhóm sản phẩm_{idx}"] = (
                                        group_div.get_text(strip=True)
                                    )
                                    row_data[f"Dịch vụ_{idx}"] = service_div.get_text(
                                        strip=True
                                    )
                            else:
                                row_data[f"Nhóm sản phẩm_{idx}"] = ""
                                row_data[f"Dịch vụ_{idx}"] = ""
                    else:
                        row_data[label_text] = details_text

        return row_data

    def save_images(self, folder_name, search_value):
        images = self.driver.find_elements(By.CSS_SELECTOR, "img.detail-img")
        image_paths = []
        for idx, img in enumerate(images):
            img_url = img.get_attribute("src")
            if img_url:
                try:
                    img_data = requests.get(img_url).content
                    img_name = f"{search_value}_{idx+1}.jpg"
                    img_path = folder_name / img_name
                    image_paths.append(str(img_path))
                    with open(img_path, "wb") as f:
                        f.write(img_data)
                    logger.info(f"Đã lưu ảnh {img_name} tại {img_path}")
                except Exception as e:
                    logger.error(f"Không thể tải ảnh {img_url}: {e}")
        return image_paths

    def save_data_to_excel(self):
        if self.data:
            for index, row in enumerate(self.data, start=1):
                row["STT"] = index + len(self.existing_data)
            df = pd.DataFrame(self.data)
            columns = ["STT"] + [col for col in df.columns if col != "STT"]
            df = df[columns]
            combined_data = pd.concat([self.existing_data, df], ignore_index=True)
            combined_data.to_excel(self.excel_file_path, index=False)
            logger.info(f"Dữ liệu đã được lưu vào {self.excel_file_path}")
        else:
            logger.warning("Không có dữ liệu để lưu.")

    def process_search(self, search_value):
        start_time = time.time()

        base_folder = Path("Images")
        error_folder = Path("Errors")
        error_folder_phase_1 = error_folder / "phase_1"
        error_folder_phase_2 = error_folder / "phase_2"
        error_folder_phase_3 = error_folder / "phase_3"

        for folder in [
            base_folder,
            error_folder,
            error_folder_phase_1,
            error_folder_phase_2,
            error_folder_phase_3,
        ]:
            folder.mkdir(parents=True, exist_ok=True)

        folder_name = base_folder / search_value.replace("/", "_")
        folder_name.mkdir(exist_ok=True)

        retry_attempts = 2
        while retry_attempts > 0:
            try:
                self.search_and_click(search_value)
                detail_container = WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located(
                        (
                            By.XPATH,
                            "//div[contains(@class, 'detail-container') and contains(@class, 'col-md-12')]",
                        )
                    )
                )
                row_data = self.extract_data(detail_container)
                self.data.append(row_data)
                image_paths = self.save_images(folder_name, search_value)
                break
            except TimeoutException as e:
                logger.error(f"Không tìm thấy kết quả tìm kiếm cho {search_value}: {e}")
                self.driver.save_screenshot(
                    str(error_folder_phase_2 / f"{search_value}_error.png")
                )
                retry_attempts -= 1
                if retry_attempts == 0:
                    self.restart_driver()
            except Exception as e:
                logger.error(f"Đã xảy ra lỗi khi tìm kiếm {search_value}: {e}")
                self.driver.save_screenshot(
                    str(error_folder_phase_1 / f"{search_value}_error.png")
                )
                retry_attempts -= 1
                if retry_attempts == 0:
                    self.restart_driver()

        self.search_count += 1
        if self.search_count >= self.restart_interval:
            self.restart_driver()

        self.save_data_to_excel()

        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.debug(
            f"Quá trình xử lý mất: {elapsed_time:.2f} giây cho số đơn {search_value}"
        )
