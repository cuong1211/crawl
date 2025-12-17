"""
Crawler cho Nhãn hiệu - Sử dụng Direct URL
Kết hợp logic từ crawler_trademarks.py (captcha, F5 retry) và backup3.py (extract data)
"""
import os
import re
import time
import logging
import requests
import pandas as pd
from pathlib import Path
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TrademarkCrawler:
    def __init__(self, driver_path, excel_path):
        self.driver_path = driver_path
        self.excel_path = excel_path
        self.excel_file_path = Path("Output_Trademarks_Direct/trademarks_data.xlsx")
        self.existing_data = pd.DataFrame()
        self.data = []
        self.load_existing_data()
        self.init_driver()

    def init_driver(self):
        self.chrome_options = Options()
        # self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--disable-gpu")

        # TẠO PROFILE RIÊNG CHO SELENIUM (tab mới, không conflict với Chrome đang mở)
        selenium_profile = Path("selenium_chrome_profile")
        selenium_profile.mkdir(exist_ok=True)

        self.chrome_options.add_argument(f"--user-data-dir={selenium_profile.absolute()}")

        self.chrome_options.add_argument("--disable-extensions")
        self.chrome_options.add_argument("--window-size=1920,1080")

        # Tắt cờ automation
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)

        self.service = Service(executable_path=self.driver_path)
        self.driver = webdriver.Chrome(service=self.service, options=self.chrome_options)

        # Tắt thuộc tính webdriver
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    def load_existing_data(self):
        """Load dữ liệu cũ từ file Excel nếu có"""
        if self.excel_file_path.exists():
            self.existing_data = pd.read_excel(self.excel_file_path)
            logger.info(f"📂 Đã load {len(self.existing_data)} bản ghi từ file cũ")
        else:
            logger.info(f"📂 Chưa có file Excel, sẽ tạo mới")

    def close_driver(self):
        if self.driver:
            self.driver.quit()
            logger.info("Browser đã đóng")

    def handle_security_warning(self):
        """Xử lý cảnh báo bảo mật nếu có"""
        try:
            advanced_button = self.driver.find_element(By.ID, "details-button")
            advanced_button.click()
            time.sleep(1)
            proceed_link = self.driver.find_element(By.ID, "proceed-link")
            proceed_link.click()
            time.sleep(2)
            logger.info("✓ Đã vượt qua cảnh báo bảo mật")
            return True
        except:
            return False

    def handle_recaptcha(self):
        """Xử lý reCAPTCHA thủ công"""
        try:
            logger.info("🔍 Đang tìm reCAPTCHA checkbox...")

            # Đợi iframe reCAPTCHA xuất hiện
            WebDriverWait(self.driver, 15).until(
                EC.frame_to_be_available_and_switch_to_it(
                    (By.XPATH, "//iframe[contains(@src, 'google.com/recaptcha')]")
                )
            )

            # Tìm checkbox
            checkbox = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.recaptcha-checkbox-border"))
            )

            logger.info("✓ Đã tìm thấy checkbox reCAPTCHA")
            checkbox.click()
            logger.info("✓ Đã click vào checkbox")

            # Đợi 2 giây để xem captcha có verified không
            time.sleep(2)

            # Kiểm tra xem captcha đã verified chưa (không có challenge)
            try:
                # Tìm element với aria-checked="true" nghĩa là đã verified
                checkbox_checked = self.driver.find_element(
                    By.CSS_SELECTOR, "div.recaptcha-checkbox-checkmark"
                )
                logger.info("✓ Captcha đã verified ngay (không có challenge)!")

                # Switch về main content
                self.driver.switch_to.default_content()

                # Click nút Next luôn
                logger.info("🔘 Đang tìm và click nút Next...")
                self.click_next_button()

                return True

            except:
                # Có challenge, cần user giải
                logger.info("⏳ Captcha có challenge, chờ 20 giây để user giải và click Next...")

                # Switch về main content
                self.driver.switch_to.default_content()

                # Chờ lâu hơn để user kịp giải challenge và click Next
                time.sleep(20)

                return True

        except Exception as e:
            logger.error(f"❌ Lỗi xử lý captcha: {e}")
            self.driver.switch_to.default_content()
            return False

    def click_next_button(self):
        """Click nút Next sau khi giải captcha"""
        try:
            # Tìm và click nút Next
            next_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'btn-primary') and contains(text(), 'Next')]"))
            )
            next_button.click()
            logger.info("✓ Đã click nút Next")
            time.sleep(3)
            return True
        except Exception as e:
            logger.warning(f"⚠️ Không tìm thấy nút Next: {e}")
            return False

    def wait_for_recaptcha_or_detail(self, url, max_attempts=20):
        """
        F5 liên tục cho đến khi xuất hiện reCAPTCHA HOẶC trang chi tiết
        Return: 'captcha' nếu thấy captcha, 'detail' nếu thấy trang chi tiết, None nếu timeout
        """
        logger.info(f"🔄 Đang F5 để chờ captcha hoặc trang chi tiết...")

        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"🔄 F5 lần {attempt}/{max_attempts}...")

                if attempt == 1:
                    self.driver.get(url)
                else:
                    self.driver.refresh()

                time.sleep(2)

                # Kiểm tra lỗi template
                if "${" in self.driver.page_source and "appltype" in self.driver.page_source:
                    logger.warning(f"⚠️ Trang bị lỗi template, tiếp tục F5...")
                    continue

                # Kiểm tra Internal Server Error
                if "Internal Server Error" in self.driver.page_source:
                    logger.warning(f"⚠️ Server lỗi 500, tiếp tục F5...")
                    continue

                # Kiểm tra xem có captcha không
                try:
                    self.driver.find_element(By.XPATH, "//iframe[contains(@src, 'google.com/recaptcha')]")
                    logger.info(f"✓ Đã tìm thấy reCAPTCHA sau {attempt} lần F5!")
                    return "captcha"
                except:
                    pass

                # Nếu không có captcha, kiểm tra xem có trang chi tiết không
                try:
                    self.driver.find_element(By.XPATH, "//div[contains(@class, 'detail-container') and contains(@class, 'col-md-12')]")
                    logger.info(f"✓ Đã vào thẳng trang chi tiết sau {attempt} lần F5 (không cần captcha)!")
                    return "detail"
                except:
                    logger.info(f"   Chưa thấy captcha hay trang chi tiết, tiếp tục F5...")
                    continue

            except Exception as e:
                logger.warning(f"Lỗi khi F5 lần {attempt}: {e}")
                continue

        # Sau max_attempts lần vẫn không thấy gì
        logger.warning(f"⚠️ Đã F5 {max_attempts} lần nhưng không thấy captcha hay trang chi tiết")
        return None

    def load_trademark_detail(self, filing_number):
        """Load trang chi tiết trademark và xử lý reCAPTCHA"""
        logger.info(f"=" * 80)
        logger.info(f"BẮT ĐẦU XỬ LÝ SỐ ĐƠN: {filing_number}")
        logger.info(f"=" * 80)

        try:
            # Xử lý filing_number: thêm VN đằng trước và bỏ dấu -
            processed_id = filing_number.replace("-", "")
            if not processed_id.upper().startswith("VN"):
                processed_id = "VN" + processed_id

            logger.info(f"📝 Filing number gốc: {filing_number}")
            logger.info(f"📝 ID đã xử lý: {processed_id}")

            # Tạo URL từ filing_number - TRADEMARKS
            url = f"https://wipopublish.ipvietnam.gov.vn/wopublish-search/public/detail/trademarks?id={processed_id}"

            logger.info(f"✓ Đang truy cập: {url}")

            # F5 liên tục cho đến khi xuất hiện reCAPTCHA HOẶC trang chi tiết
            result = self.wait_for_recaptcha_or_detail(url, max_attempts=20)

            if result == None:
                logger.error(f"❌ Không tìm thấy captcha hay trang chi tiết sau nhiều lần F5")
                raise Exception("Timeout: Không load được trang")

            elif result == "captcha":
                # Xử lý reCAPTCHA khi đã xuất hiện (handle_recaptcha sẽ tự động click Next)
                logger.info("Đang xử lý reCAPTCHA...")
                self.handle_recaptcha()

                # Sau khi xử lý captcha và click Next, F5 liên tục cho đến khi thấy trang chi tiết
                logger.info("⏳ Đang F5 để tải trang chi tiết...")
                max_f5_after_captcha = 20
                detail_found = False

                for f5_attempt in range(1, max_f5_after_captcha + 1):
                    try:
                        logger.info(f"🔄 F5 sau captcha lần {f5_attempt}/{max_f5_after_captcha}...")

                        if f5_attempt > 1:
                            self.driver.refresh()
                            time.sleep(2)

                        # Kiểm tra lỗi template
                        if "${" in self.driver.page_source and "appltype" in self.driver.page_source:
                            logger.warning(f"⚠️ Trang bị lỗi template, tiếp tục F5...")
                            continue

                        # Kiểm tra Internal Server Error
                        if "Internal Server Error" in self.driver.page_source:
                            logger.warning(f"⚠️ Server lỗi 500, tiếp tục F5...")
                            continue

                        # Tìm trang chi tiết với col-md-12
                        self.driver.find_element(By.XPATH, "//div[contains(@class, 'detail-container') and contains(@class, 'col-md-12')]")
                        logger.info(f"✓ Đã tìm thấy trang chi tiết sau {f5_attempt} lần F5!")
                        detail_found = True
                        break

                    except:
                        logger.info(f"   Chưa thấy trang chi tiết, tiếp tục F5...")
                        continue

                if not detail_found:
                    raise Exception(f"Không tìm thấy trang chi tiết sau {max_f5_after_captcha} lần F5")

                # Lấy detail container có data (col-md-12)
                detail_container = self.driver.find_element(
                    By.XPATH, "//div[contains(@class, 'detail-container') and contains(@class, 'col-md-12')]"
                )
                logger.info(f"✓ Trang chi tiết đã tải xong!")

            elif result == "detail":
                # Đã vào thẳng trang chi tiết (không cần captcha)
                logger.info("⏳ Đang lấy detail container...")
                detail_container = self.driver.find_element(
                    By.XPATH, "//div[contains(@class, 'detail-container') and contains(@class, 'col-md-12')]"
                )
                logger.info(f"✓ Trang chi tiết đã sẵn sàng!")

            return detail_container

        except Exception as e:
            logger.error(f"❌ Lỗi load_trademark_detail: {e}")
            raise

    def extract_data(self, filing_number):
        """Extract dữ liệu từ trang chi tiết trademark - Logic từ backup3.py"""
        try:
            detail_container = self.load_trademark_detail(filing_number)

            html = detail_container.get_attribute("outerHTML")
            soup = BeautifulSoup(html, "html.parser")
            rows = soup.find_all("div", class_="row")

            row_data = {}

            for row in rows:
                # Tìm tất cả các div có class "product-form-label" và "product-form-details"
                label_divs = row.find_all("div", class_="product-form-label")
                details_divs = row.find_all("div", class_="product-form-details")

                # Ghép cặp các div lại với nhau và xử lý
                for label_div, details_div in zip(label_divs, details_divs):
                    if label_div and details_div:
                        # Xử lý label text
                        if label_div.get_text(strip=True) == "(541) Nhãn hiệu":
                            label_text = "Nhãn hiệu gốc"
                        else:
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
                            if len(spans) >= 2:
                                row_data["Số bằng"] = spans[0].get_text(strip=True)
                                row_data["Ngày cấp"] = spans[1].get_text(strip=True)
                        elif label_text == "Số đơn và Ngày nộp đơn":
                            spans = details_div.find_all("span")
                            if len(spans) == 2:
                                row_data["Số đơn"] = spans[0].get_text(strip=True)
                                row_data["Ngày nộp đơn"] = spans[1].get_text(strip=True)
                        elif label_text == "Số công bố và ngày công bố":
                            details_text_row = details_div.find("div", class_="row")
                            if details_text_row:
                                content = details_text_row.find_all("div", class_="col-md-4")
                                if len(content) >= 2:
                                    row_data["Số công bố"] = content[0].get_text(strip=True)
                                    row_data["Ngày công bố"] = content[1].get_text(strip=True)
                        elif label_text == "Chủ đơn/Chủ bằng":
                            contents = details_div.find_all("div", id="apnaDiv")
                            for idx, content in enumerate(contents, start=1):
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
                        elif label_text == "Đại diện SHCN":
                            contents = details_div.find("div", class_="row")
                            if contents:
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
                        elif label_text == "Nhãn hiệu gốc":
                            row_data[label_text] = re.sub(
                                r"^\([^)]*\)\s*",
                                "",
                                details_text,
                            )
                        elif label_text == "Nhóm sản phẩm/dịch vụ":
                            content_text = details_div.find("div", class_="col-md-10")
                            if content_text:
                                row_data[label_text] = content_text.get_text(strip=True)
                            else:
                                row_data[label_text] = details_text
                        else:
                            row_data[label_text] = details_text

            logger.info(f"✓ Đã extract {len(row_data)} trường dữ liệu")
            return row_data

        except Exception as e:
            logger.error(f"❌ Lỗi extract_data: {e}")
            raise

    def save_images(self, folder_name, search_value):
        """Lưu ảnh từ trang chi tiết - cho TRADEMARKS"""
        # Tìm ảnh với class detail-img (cho trademarks)
        images = self.driver.find_elements(By.CSS_SELECTOR, "img.detail-img")

        # Nếu không tìm thấy, thử selector khác
        if len(images) == 0:
            logger.info(f"   Không tìm thấy ảnh với selector 'img.detail-img', thử selector khác...")
            images = self.driver.find_elements(By.CSS_SELECTOR, "img.img-responsive")

        image_paths = []
        total_images = len(images)

        logger.info(f"   Tìm thấy {total_images} ảnh")
        for idx, img in enumerate(images, start=1):
            img_url = img.get_attribute("src")
            if img_url:
                try:
                    img_data = requests.get(img_url).content
                    img_name = f"{search_value.replace('/', '_')}_{idx}.jpg"
                    img_path = folder_name / img_name
                    image_paths.append(str(img_path))
                    with open(img_path, "wb") as f:
                        f.write(img_data)
                    logger.info(f"  ✓ Ảnh {idx}/{total_images}: {img_name}")
                except Exception as e:
                    logger.error(f"  ✗ Lỗi tải ảnh {idx}/{total_images}: {e}")

        return image_paths

    def save_data_to_excel(self):
        """Lưu dữ liệu vào file Excel"""
        if self.data:
            logger.info(f"📊 Đang lưu dữ liệu vào Excel...")
            for index, row in enumerate(self.data, start=1):
                row["STT"] = index + len(self.existing_data)
            df = pd.DataFrame(self.data)
            columns = ["STT"] + [col for col in df.columns if col != "STT"]
            df = df[columns]
            combined_data = pd.concat([self.existing_data, df], ignore_index=True)
            combined_data.to_excel(self.excel_file_path, index=False)

            total_records = len(combined_data)
            new_records = len(self.data)
            logger.info(f"✅ THÀNH CÔNG! Đã lưu {new_records} bản ghi mới")
            logger.info(f"📈 Tổng số bản ghi trong file: {total_records}")
            logger.info(f"💾 File output: {self.excel_file_path}")
        else:
            logger.warning("⚠️ Không có dữ liệu để lưu.")

    def process_trademark(self, filing_number):
        """Xử lý một filing number (số đơn trademarks)"""
        start_time = time.time()

        # Thư mục output
        base_folder = Path("Output_Trademarks_Direct/Images")
        error_folder = Path("Output_Trademarks_Direct/Errors")
        error_folder_phase_1 = error_folder / "phase_1_exception"
        error_folder_phase_2 = error_folder / "phase_2_timeout"
        error_folder_phase_3 = error_folder / "phase_3_other"

        for folder in [base_folder, error_folder_phase_1, error_folder_phase_2, error_folder_phase_3]:
            folder.mkdir(parents=True, exist_ok=True)

        folder_name = base_folder / filing_number.replace("/", "_")
        folder_name.mkdir(exist_ok=True)

        try:
            # Extract dữ liệu
            logger.info("📊 Đang extract dữ liệu...")
            row_data = self.extract_data(filing_number)

            # Lưu ảnh
            logger.info("🖼️  Đang lưu ảnh...")
            image_paths = self.save_images(folder_name, filing_number)

            # Thêm data vào list
            self.data.append(row_data)

            elapsed_time = time.time() - start_time
            logger.info(f"✅ THÀNH CÔNG! Xử lý xong {filing_number} trong {elapsed_time:.2f}s")
            logger.info(f"=" * 80)

        except Exception as e:
            logger.error(f"❌ LỖI khi xử lý {filing_number}: {e}")
            # Screenshot lỗi
            screenshot_path = error_folder_phase_1 / f"{filing_number.replace('/', '_')}_error.png"
            self.driver.save_screenshot(str(screenshot_path))
            logger.info(f"📸 Screenshot lỗi: {screenshot_path}")
