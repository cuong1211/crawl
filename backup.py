import os
import requests
import time
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
        self.chrome_options.add_argument("--disable-gpu")  # Tắt GPU
        self.service = Service(executable_path=self.driver_path)
        self.driver = webdriver.Chrome(service=self.service, options=self.chrome_options)
    
    def stop_driver(self):
        if self.driver is not None:
            self.driver.quit()
            self.driver = None

    def process_search(self, search_value):
        start_time = time.time()
        print(f"Đang tìm kiếm số đơn {search_value}")

        base_folder = "Images"
        error_folder = os.path.join(base_folder, "Errors")

        os.makedirs(base_folder, exist_ok=True)
        os.makedirs(error_folder, exist_ok=True)

        folder_name = os.path.join(base_folder, search_value.replace("/", "_"))
        os.makedirs(folder_name, exist_ok=True)

        try:
            self.driver.get("http://wipopublish.ipvietnam.gov.vn/wopublish-search/public/designs?18&query=*:*")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.NAME, "advancedInputWrapper:advancedInputsList:1:advancedInputSearchPanel:input")
                )
            )
            print("Đã mở trang web")

            input_field = self.driver.find_element(
                By.NAME, "advancedInputWrapper:advancedInputsList:1:advancedInputSearchPanel:input"
            )
            input_field.send_keys(search_value)
            input_field.send_keys(Keys.RETURN)

            retry_attempts = 3
            while retry_attempts > 0:
                try:
                    WebDriverWait(self.driver, 20).until(
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
                            WebDriverWait(self.driver, 20).until(
                                EC.presence_of_element_located(
                                    (By.CSS_SELECTOR, "img.DRAWING-detail")
                                )
                            )
                            print("Tìm thấy ảnh chi tiết!")

                            images = self.driver.find_elements(
                                By.CSS_SELECTOR, "img.DRAWING-detail"
                            )
                            print(f"Đã tìm thấy {len(images)} ảnh")

                            for idx, img in enumerate(images):
                                img_url = img.get_attribute("src")
                                if img_url:
                                    try:
                                        img_data = requests.get(img_url).content
                                        img_name = f"{search_value}_{idx+1}.jpg"
                                        img_path = os.path.join(folder_name, img_name)

                                        with open(img_path, "wb") as f:
                                            f.write(img_data)
                                        print(f"Đã lưu ảnh {img_name} tại {img_path}")
                                    except Exception as e:
                                        print(f"Không thể tải ảnh {img_url}: {e}")
                                else:
                                    print("URL ảnh không hợp lệ")
                            break

                        except TimeoutException as e:
                            print(f"Không tìm thấy ảnh: {e}")
                            self.driver.save_screenshot(
                                os.path.join(error_folder, f"{search_value}_error.png")
                            )
                            retry_attempts -= 1
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
            print(f"Quá trình xử lý mất: {elapsed_time:.2f} giây cho số đơn {search_value}")
            print("-" * 40)
