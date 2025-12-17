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
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Crawler:
    def __init__(self, driver_path, excel_path, restart_interval=100):
        self.driver_path = Path(driver_path)
        self.excel_path = Path(excel_path)
        # Thư mục output tường minh
        self.excel_folder = Path("Output_Designs")
        self.excel_folder.mkdir(exist_ok=True)
        self.excel_file_path = self.excel_folder / "designs_data.xlsx"
        self.data = []
        self.restart_interval = restart_interval
        self.search_count = 0
        self.load_existing_data()
        self.init_driver()

    def init_driver(self):
        self.chrome_options = Options()
        # self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--incognito")
        self.chrome_options.add_argument("--disable-extensions")
        self.chrome_options.add_argument("--window-size=1920,1080")
        # Bỏ qua cảnh báo bảo mật HTTPS
        self.chrome_options.add_argument("--ignore-certificate-errors")
        self.chrome_options.add_argument("--ignore-ssl-errors")
        self.chrome_options.add_argument("--allow-insecure-localhost")
        self.chrome_options.add_argument("--disable-web-security")
        self.chrome_options.add_argument("--allow-running-insecure-content")
        # Thêm preferences để tắt cảnh báo bảo mật
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
        self.chrome_options.add_experimental_option("prefs", {
            "profile.default_content_setting_values.mixed_content": 1,
            "profile.default_content_setting_values.protocol_handlers": 1,
        })
        # Sử dụng ChromeDriver local đã cập nhật
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

    def bypass_security_warning(self):
        """Tự động click qua trang cảnh báo bảo mật nếu có"""
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                time.sleep(1)
                # Kiểm tra xem có đang ở trang cảnh báo không
                if "doesn't support a secure connection" in self.driver.page_source or \
                   "Continue to site" in self.driver.page_source:
                    logger.info(f"Phát hiện trang cảnh báo bảo mật, đang thử click 'Continue to site' (lần {attempt + 1})...")

                    # Phương pháp 1: Tìm button bằng text
                    try:
                        button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Continue to site')]")
                        button.click()
                        logger.info("Đã click 'Continue to site' thành công!")
                        time.sleep(2)
                        return
                    except:
                        pass

                    # Phương pháp 2: Dùng JavaScript để click
                    try:
                        self.driver.execute_script("""
                            var buttons = document.querySelectorAll('button');
                            for (var i = 0; i < buttons.length; i++) {
                                if (buttons[i].textContent.includes('Continue to site')) {
                                    buttons[i].click();
                                    break;
                                }
                            }
                        """)
                        logger.info("Đã click 'Continue to site' bằng JavaScript!")
                        time.sleep(2)
                        return
                    except:
                        pass

                    # Phương pháp 3: Thử các ID thông dụng
                    for element_id in ["proceed-button", "proceed-link", "details-button"]:
                        try:
                            elem = self.driver.find_element(By.ID, element_id)
                            elem.click()
                            time.sleep(1)
                        except:
                            pass
                else:
                    # Không còn trang cảnh báo
                    return
            except Exception as e:
                logger.debug(f"Lỗi khi bypass cảnh báo bảo mật: {e}")
                pass

        logger.warning("Không thể bypass trang cảnh báo bảo mật sau 5 lần thử")

    def search_and_click(self, search_value):
        logger.info(f"=" * 80)
        logger.info(f"BẮT ĐẦU XỬ LÝ SỐ ĐƠN: {search_value}")
        logger.info(f"=" * 80)

        try:
            self.driver.get(
                "http://wipopublish.ipvietnam.gov.vn/wopublish-search/public/designs?1&query=*:*"
            )
            logger.info(f"✓ Đã truy cập trang tìm kiếm Designs (Kiểu dáng công nghiệp)")

            # Thử bypass cảnh báo bảo mật nếu có
            self.bypass_security_warning()

            # Đợi ô tìm kiếm xuất hiện
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
            logger.info(f"✓ Tìm thấy ô tìm kiếm, đang nhập số đơn: {search_value}")
            input_field.send_keys(search_value)
            input_field.send_keys(Keys.RETURN)
            logger.info(f"✓ Đã gửi yêu cầu tìm kiếm, đang chờ kết quả...")

            # Thử click vào link chi tiết - 5 lần thử
            max_click_attempts = 5
            clicked_successfully = False

            for attempt in range(max_click_attempts):
                try:
                    logger.info(f"Đang thử click vào link chi tiết (lần {attempt + 1}/{max_click_attempts})...")

                    # Đợi link xuất hiện
                    a_tag = WebDriverWait(self.driver, 15).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "a.fa-file-text.fa-lg"))
                    )

                    # Phương pháp 1: JavaScript click (nhanh nhất)
                    try:
                        self.driver.execute_script("arguments[0].click();", a_tag)
                        time.sleep(2)
                    except:
                        pass

                    # Phương pháp 2: Click thông thường
                    try:
                        a_tag.click()
                        time.sleep(2)
                    except:
                        pass

                    # Kiểm tra xem đã vào trang chi tiết chưa
                    time.sleep(3)

                    # Kiểm tra xem có lỗi Internal Server Error không
                    if "Internal Server Error" in self.driver.page_source:
                        logger.error(f"❌ Server trả về Internal Server Error (lỗi 500)")
                        logger.error(f"⚠️ Đây là lỗi từ phía server NOIP, không phải lỗi code")
                        logger.error(f"🔄 Sẽ restart driver và skip record này...")
                        self.restart_driver()
                        raise Exception(f"Server Internal Error - skip record {search_value}")

                    try:
                        self.driver.find_element(By.XPATH, "//div[contains(@class, 'detail-container')]")
                        logger.info(f"✓ Đã vào trang chi tiết thành công sau {attempt + 1} lần thử!")
                        clicked_successfully = True
                        break
                    except:
                        logger.warning(f"Chưa vào được trang chi tiết, thử lại...")
                        time.sleep(1)

                except TimeoutException:
                    logger.warning(f"Timeout khi tìm link chi tiết lần {attempt + 1}")
                    time.sleep(2)
                except Exception as e:
                    logger.warning(f"Lỗi khi thử click lần {attempt + 1}: {type(e).__name__}")
                    time.sleep(2)

            if not clicked_successfully:
                logger.error(f"⚠️ Không thể vào trang chi tiết sau {max_click_attempts} lần thử!")
                logger.error(f"🔄 Sẽ restart driver và thử lại từ đầu...")
                self.restart_driver()
                raise Exception(f"Không thể click vào link chi tiết sau {max_click_attempts} lần thử")

        except TimeoutException as e:
            logger.error(f"⏱️ TIMEOUT: {str(e)}")
            logger.error(f"🔄 Restart driver do timeout...")
            self.restart_driver()
            raise

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

    def process_search(self, search_value):
        start_time = time.time()

        # Thư mục output tường minh
        base_folder = Path("Output_Designs/Images")
        error_folder = Path("Output_Designs/Errors")
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

        folder_name = base_folder / search_value.replace("/", "_")
        folder_name.mkdir(exist_ok=True)

        retry_attempts = 2
        while retry_attempts > 0:
            try:
                self.search_and_click(search_value)
                logger.info(f"⏳ Đang chờ tải trang chi tiết...")
                detail_container = WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located(
                        (
                            By.XPATH,
                            "//div[contains(@class, 'detail-container') and contains(@class, 'col-md-12')]",
                        )
                    )
                )
                logger.info(f"✓ Trang chi tiết đã tải xong!")

                logger.info(f"📝 Đang trích xuất dữ liệu...")
                row_data = self.extract_data(detail_container)
                self.data.append(row_data)
                logger.info(f"✓ Đã trích xuất {len(row_data)} trường dữ liệu")

                logger.info(f"🖼️  Đang tải ảnh...")
                image_paths = self.save_images(folder_name, search_value)
                logger.info(f"✓ Đã lưu {len(image_paths)} ảnh vào: {folder_name}")
                break
            except TimeoutException as e:
                error_file = error_folder_phase_2 / f"{search_value.replace('/', '_')}_error.png"
                logger.error(f"❌ TIMEOUT: Không tìm thấy kết quả cho {search_value}")
                logger.error(f"📸 Screenshot lỗi đã lưu: {error_file}")
                self.driver.save_screenshot(str(error_file))
                retry_attempts -= 1
                if retry_attempts > 0:
                    logger.warning(f"🔄 Thử lại lần {3 - retry_attempts}/2...")
                else:
                    logger.error(f"⚠️ Hết số lần retry, đang restart driver...")
                    self.restart_driver()
            except Exception as e:
                error_file = error_folder_phase_1 / f"{search_value.replace('/', '_')}_error.png"
                logger.error(f"❌ LỖI: {type(e).__name__} - {str(e)}")
                logger.error(f"📸 Screenshot lỗi đã lưu: {error_file}")
                self.driver.save_screenshot(str(error_file))
                retry_attempts -= 1
                if retry_attempts > 0:
                    logger.warning(f"🔄 Thử lại lần {3 - retry_attempts}/2...")
                else:
                    logger.error(f"⚠️ Hết số lần retry, đang restart driver...")
                    self.restart_driver()

        self.search_count += 1
        if self.search_count >= self.restart_interval:
            logger.info(f"🔄 Đã xử lý {self.search_count} số đơn, đang khởi động lại driver...")
            self.restart_driver()

        self.save_data_to_excel()

        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f"⏱️  Thời gian xử lý: {elapsed_time:.2f} giây")
        logger.info(f"=" * 80)
        logger.info("")
