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
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DesignCrawler:
    def __init__(self, driver_path, excel_path):
        self.driver_path = Path(driver_path)
        self.excel_path = Path(excel_path)
        # Thư mục output
        self.excel_folder = Path("Output_Designs_Direct")
        self.excel_folder.mkdir(exist_ok=True)
        self.excel_file_path = self.excel_folder / "designs_data.xlsx"
        self.data = []
        self.load_existing_data()
        self.init_driver()

    def init_driver(self):
        self.chrome_options = Options()
        # self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--disable-gpu")

        # TẠO PROFILE RIÊNG CHO SELENIUM (tab mới, không conflict với Chrome đang mở)
        # Profile này sẽ nằm trong thư mục project
        selenium_profile = Path("selenium_chrome_profile")
        selenium_profile.mkdir(exist_ok=True)

        self.chrome_options.add_argument(f"--user-data-dir={selenium_profile.absolute()}")

        self.chrome_options.add_argument("--disable-extensions")
        self.chrome_options.add_argument("--window-size=1920,1080")

        # Bỏ qua cảnh báo bảo mật HTTPS
        self.chrome_options.add_argument("--ignore-certificate-errors")
        self.chrome_options.add_argument("--ignore-ssl-errors")
        self.chrome_options.add_argument("--allow-insecure-localhost")
        self.chrome_options.add_argument("--disable-web-security")
        self.chrome_options.add_argument("--allow-running-insecure-content")

        # Disable thông báo automation (giống người dùng thật)
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        self.chrome_options.add_experimental_option("useAutomationExtension", False)

        # Ẩn dấu hiệu automation
        self.chrome_options.add_argument("--disable-blink-features=AutomationControlled")

        self.chrome_options.add_experimental_option("prefs", {
            "profile.default_content_setting_values.mixed_content": 1,
            "profile.default_content_setting_values.protocol_handlers": 1,
        })

        # Sử dụng ChromeDriver local
        self.service = Service(executable_path=self.driver_path)
        self.driver = webdriver.Chrome(
            service=self.service, options=self.chrome_options
        )

        # Ẩn thông tin "Chrome is being controlled by automated test software"
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

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
        logger.info("Driver đã được khởi động lại.")

    def handle_recaptcha(self):
        """Tự động click vào checkbox reCAPTCHA của Google"""
        try:
            logger.info("Đang tìm kiếm reCAPTCHA...")

            # Đợi iframe reCAPTCHA xuất hiện
            WebDriverWait(self.driver, 10).until(
                EC.frame_to_be_available_and_switch_to_it(
                    (By.XPATH, "//iframe[contains(@src, 'recaptcha')]")
                )
            )
            logger.info("✓ Đã tìm thấy iframe reCAPTCHA")

            # Tìm và click vào checkbox
            checkbox = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "recaptcha-checkbox-border"))
            )
            checkbox.click()
            logger.info("✓ Đã click vào checkbox reCAPTCHA")

            # Switch về main content
            self.driver.switch_to.default_content()

            # Đợi reCAPTCHA verify xong (tối đa 15 giây)
            logger.info("⏳ Đang đợi reCAPTCHA verify...")
            max_wait = 15
            verified = False

            for i in range(max_wait):
                time.sleep(1)
                try:
                    # Kiểm tra xem checkbox đã checked chưa
                    self.driver.switch_to.frame(
                        self.driver.find_element(By.XPATH, "//iframe[contains(@src, 'recaptcha')]")
                    )
                    # Nếu checkbox đã checked thì sẽ có class recaptcha-checkbox-checked
                    checkbox_div = self.driver.find_element(By.CLASS_NAME, "recaptcha-checkbox")
                    if "recaptcha-checkbox-checked" in checkbox_div.get_attribute("class"):
                        logger.info(f"✓ reCAPTCHA đã verify thành công sau {i+1} giây!")
                        verified = True
                        self.driver.switch_to.default_content()
                        break
                except:
                    pass
                finally:
                    self.driver.switch_to.default_content()

            if not verified:
                logger.warning("⚠️ reCAPTCHA chưa verify xong sau 15 giây, có thể cần giải thủ công")
                logger.warning("⏸️ Đang dừng 30 giây để bạn giải captcha thủ công (nếu cần)...")
                time.sleep(30)

            return True

        except TimeoutException:
            logger.warning("Không tìm thấy reCAPTCHA hoặc đã được bypass")
            self.driver.switch_to.default_content()
            return False
        except Exception as e:
            logger.error(f"Lỗi khi xử lý reCAPTCHA: {e}")
            self.driver.switch_to.default_content()
            return False

    def click_next_button(self):
        """Click vào nút Next sau khi xử lý reCAPTCHA"""
        try:
            logger.info("Đang tìm nút Next...")

            # Tìm nút Next
            next_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div/div/form/div[3]/div/input"))
            )
            logger.info("✓ Đã tìm thấy nút Next")

            # Click vào nút Next
            try:
                # Phương pháp 1: JavaScript click
                self.driver.execute_script("arguments[0].click();", next_button)
                logger.info("✓ Đã click vào nút Next (JavaScript)")
            except:
                # Phương pháp 2: Click thông thường
                next_button.click()
                logger.info("✓ Đã click vào nút Next (Regular)")

            # Đợi trang chuyển
            time.sleep(2)

            return True

        except TimeoutException:
            logger.warning("Không tìm thấy nút Next (có thể đã qua bước này)")
            return False
        except Exception as e:
            logger.error(f"Lỗi khi click nút Next: {e}")
            return False

    def wait_for_recaptcha_or_detail(self, url, max_attempts=20):
        """F5 liên tục cho đến khi xuất hiện reCAPTCHA HOẶC trang chi tiết"""
        logger.info("🔄 Bắt đầu F5 liên tục để đợi reCAPTCHA hoặc trang chi tiết...")

        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"🔄 F5 lần {attempt}/{max_attempts}...")

                # Refresh trang
                if attempt == 1:
                    self.driver.get(url)
                else:
                    self.driver.refresh()

                # Đợi trang load
                time.sleep(2)

                # Kiểm tra Internal Server Error
                if "Internal Server Error" in self.driver.page_source:
                    logger.warning(f"⚠️ Server trả về lỗi 500, tiếp tục F5...")
                    continue

                # Kiểm tra trang có bị lỗi template không (có ${...})
                if "${" in self.driver.page_source and "appltype" in self.driver.page_source:
                    logger.warning(f"⚠️ Trang bị lỗi template (có ${{...}}), tiếp tục F5...")
                    continue

                # Kiểm tra xem có iframe reCAPTCHA không
                try:
                    self.driver.find_element(By.XPATH, "//iframe[contains(@src, 'recaptcha')]")
                    logger.info(f"✓ Đã phát hiện reCAPTCHA sau {attempt} lần F5!")
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

    def load_design_detail(self, filing_number):
        """Load trang chi tiết design và xử lý reCAPTCHA"""
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

            # Tạo URL từ filing_number - DESIGNS không phải TRADEMARKS
            url = f"https://wipopublish.ipvietnam.gov.vn/wopublish-search/public/detail/designs?id={processed_id}"

            logger.info(f"✓ Đang truy cập: {url}")

            # F5 liên tục cho đến khi xuất hiện reCAPTCHA HOẶC trang chi tiết
            result = self.wait_for_recaptcha_or_detail(url, max_attempts=20)

            if result == None:
                logger.error(f"❌ Không tìm thấy captcha hay trang chi tiết sau nhiều lần F5")
                raise Exception(f"Không load được trang - {filing_number}")

            elif result == "captcha":
                # Xử lý reCAPTCHA khi đã xuất hiện
                logger.info("Đang xử lý reCAPTCHA...")
                self.handle_recaptcha()

                # Click vào nút Next sau khi xử lý reCAPTCHA
                logger.info("Đang kiểm tra nút Next...")
                self.click_next_button()

                # Sau khi click Next, F5 liên tục cho đến khi thấy trang chi tiết
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
            logger.error(f"❌ Lỗi khi load trang: {type(e).__name__} - {str(e)}")
            raise

    def extract_data(self, detail_container):
        """Trích xuất dữ liệu từ trang chi tiết design"""
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
        """Lưu ảnh từ trang chi tiết design"""
        # Tìm ảnh với class DRAWING-detail (cho trang designs)
        images = self.driver.find_elements(By.CSS_SELECTOR, "img.DRAWING-detail")

        # Nếu không tìm thấy, thử selector cũ (cho trademarks nếu cần)
        if len(images) == 0:
            logger.info(f"   Không tìm thấy ảnh với selector 'img.DRAWING-detail', thử selector khác...")
            images = self.driver.find_elements(By.CSS_SELECTOR, "img.detail-img")

        # Nếu vẫn không có, thử selector chung
        if len(images) == 0:
            logger.info(f"   Thử tìm tất cả ảnh trong detail-container...")
            images = self.driver.find_elements(By.CSS_SELECTOR, "img.img-responsive-drawing")

        image_paths = []
        total_images = len(images)

        if total_images == 0:
            logger.warning(f"⚠️ Không tìm thấy ảnh nào cho số đơn {search_value}")
            return image_paths

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

    def process_design(self, filing_number):
        """Xử lý một filing number (số đơn designs)"""
        start_time = time.time()

        # Thư mục output
        base_folder = Path("Output_Designs_Direct/Images")
        error_folder = Path("Output_Designs_Direct/Errors")
        error_folder_phase_1 = error_folder / "phase_1_exception"
        error_folder_phase_2 = error_folder / "phase_2_timeout"
        error_folder_phase_3 = error_folder / "phase_3_other"

        for folder in [
            base_folder,
            error_folder,
            error_folder_phase_1,
            error_folder_phase_2,
            error_folder_phase_3,
        ]:
            folder.mkdir(parents=True, exist_ok=True)

        folder_name = base_folder / filing_number.replace("/", "_")
        folder_name.mkdir(exist_ok=True)

        retry_attempts = 2
        while retry_attempts > 0:
            try:
                # Load trang chi tiết và xử lý reCAPTCHA
                detail_container = self.load_design_detail(filing_number)

                # Trích xuất dữ liệu
                logger.info(f"📝 Đang trích xuất dữ liệu...")
                row_data = self.extract_data(detail_container)
                self.data.append(row_data)
                logger.info(f"✓ Đã trích xuất {len(row_data)} trường dữ liệu")

                # Lưu ảnh
                logger.info(f"🖼️  Đang tải ảnh...")
                image_paths = self.save_images(folder_name, filing_number)
                logger.info(f"✓ Đã lưu {len(image_paths)} ảnh vào: {folder_name}")
                break

            except TimeoutException as e:
                error_file = error_folder_phase_2 / f"{filing_number.replace('/', '_')}_error.png"
                logger.error(f"❌ TIMEOUT: Không tìm thấy kết quả cho {filing_number}")
                logger.error(f"📸 Screenshot lỗi đã lưu: {error_file}")
                self.driver.save_screenshot(str(error_file))
                retry_attempts -= 1
                if retry_attempts > 0:
                    logger.warning(f"🔄 Thử lại lần {3 - retry_attempts}/2...")
                else:
                    logger.error(f"⚠️ Hết số lần retry, đang restart driver...")
                    self.restart_driver()
            except Exception as e:
                error_file = error_folder_phase_1 / f"{filing_number.replace('/', '_')}_error.png"
                logger.error(f"❌ LỖI: {type(e).__name__} - {str(e)}")
                logger.error(f"📸 Screenshot lỗi đã lưu: {error_file}")
                self.driver.save_screenshot(str(error_file))
                retry_attempts -= 1
                if retry_attempts > 0:
                    logger.warning(f"🔄 Thử lại lần {3 - retry_attempts}/2...")
                else:
                    logger.error(f"⚠️ Hết số lần retry, đang restart driver...")
                    self.restart_driver()

        self.save_data_to_excel()

        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f"⏱️  Thời gian xử lý: {elapsed_time:.2f} giây")
        logger.info(f"=" * 80)
        logger.info("")

    def run(self, filing_numbers):
        """Chạy crawler cho danh sách filing numbers (số đơn designs)"""
        logger.info(f"🚀 BẮT ĐẦU CRAWL {len(filing_numbers)} SỐ ĐƠN DESIGNS")
        logger.info(f"=" * 80)

        for idx, filing_number in enumerate(filing_numbers, start=1):
            logger.info(f"📍 Đang xử lý {idx}/{len(filing_numbers)}: {filing_number}")
            try:
                self.process_design(filing_number)
            except Exception as e:
                logger.error(f"Lỗi nghiêm trọng khi xử lý {filing_number}: {e}")
                logger.info("Thử restart driver và tiếp tục...")
                self.restart_driver()

        logger.info(f"✅ HOÀN THÀNH! Đã xử lý {len(filing_numbers)} số đơn designs")
        self.close_driver()
