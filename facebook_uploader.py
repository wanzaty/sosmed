#!/usr/bin/env python3
"""
Facebook Uploader (Status & Reels) menggunakan Selenium
Dengan XPath selector yang valid untuk Facebook
"""

import os
import sys
import json
import time
import platform
from pathlib import Path
from typing import Optional, Dict, Any

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    WebDriverException,
    ElementNotInteractableException,
    StaleElementReferenceException
)
from webdriver_manager.chrome import ChromeDriverManager
from colorama import init, Fore, Style, Back
import argparse

# Initialize colorama untuk Windows compatibility
init(autoreset=True)

class FacebookUploader:
    def __init__(self, headless: bool = False, debug: bool = False):
        """
        Initialize Facebook Uploader
        
        Args:
            headless: Jalankan browser dalam mode headless
            debug: Enable debug logging
        """
        self.headless = headless
        self.debug = debug
        self.driver = None
        self.wait = None
        
        # Setup paths - menggunakan folder cookies dengan file JSON
        self.base_dir = Path(__file__).parent
        self.cookies_dir = self.base_dir / "cookies"
        self.cookies_dir.mkdir(exist_ok=True)
        self.cookies_path = self.cookies_dir / "facebook_cookies.json"
        self.screenshots_dir = self.base_dir / "screenshots"
        self.screenshots_dir.mkdir(exist_ok=True)
        
        # Facebook URLs
        self.base_url = "https://www.facebook.com"
        self.reels_url = "https://www.facebook.com/reels/create/?surface=PROFILE_PLUS"
        
        # XPath Selectors yang VALID - berdasarkan screenshot yang benar
        self.selectors = {
            # XPath untuk area "What's on your mind" yang benar
            'status_trigger_xpath': [
                # Berdasarkan screenshot - area yang tepat
                "//span[contains(text(), \"What's on your mind\")]",
                "//div[@role='button']//span[contains(text(), \"What's on your mind\")]",
                "//div[contains(@aria-label, 'Create a post')]",
                "//div[@data-pagelet='FeedUnit_0']//div[@role='button']"
            ],
            
            # XPath untuk text area di dalam composer yang sudah terbuka
            'composer_text_area': [
                # Area text yang benar di dalam composer - SEBELUM media upload
                "//div[@contenteditable='true' and @role='textbox']",
                "//div[@contenteditable='true' and contains(@aria-placeholder, \"What's on your mind\")]",
                "//div[@data-lexical-editor='true']",
                "//div[@contenteditable='true']//p",
                "//div[contains(@class, 'notranslate') and @contenteditable='true']"
            ],
            
            # XPath untuk text area SETELAH media diupload - berdasarkan screenshot
            'composer_text_area_after_media': [
                # Berdasarkan screenshot: area text di atas video dengan placeholder "What's on your mind, Kurniawan?"
                "//div[@contenteditable='true' and contains(@data-text, \"What's on your mind\")]",
                "//div[@contenteditable='true' and @data-text]",
                "//div[@contenteditable='true' and contains(@aria-label, 'What\\'s on your mind')]",
                "//div[@contenteditable='true' and @role='textbox' and @data-text]",
                # Selector berdasarkan posisi di atas media
                "//div[contains(@class, 'x1ed109x')]//div[@contenteditable='true']",
                "//div[contains(@class, 'x1swvt13')]//div[@contenteditable='true']",
                # Fallback umum
                "//div[@contenteditable='true' and @role='textbox']",
                "//div[@contenteditable='true']"
            ],
            
            # XPath untuk tombol Post di composer
            'post_button_composer': [
                "//div[@aria-label='Post' and @role='button']",
                "//div[@role='button']//span[text()='Post']",
                "//button//span[text()='Post']",
                "//div[contains(@class, 'x1i10hfl')]//span[text()='Post']"
            ],
            
            # XPath untuk input file - LANGSUNG TERSEDIA setelah klik "What's on your mind"
            'media_input_direct': [
                # Input file yang langsung tersedia di composer
                "//input[@type='file' and contains(@accept, 'image')]",
                "//input[@type='file' and contains(@accept, 'video')]", 
                "//input[@type='file' and contains(@accept, '.jpg')]",
                "//input[@type='file' and contains(@accept, '.mp4')]",
                "//input[@type='file' and @multiple]",
                "//input[@type='file']",
                # Alternatif dengan berbagai kombinasi accept
                "//input[@accept and @type='file']",
                "//input[@multiple and @type='file' and contains(@accept, 'image')]",
                "//input[@multiple and @type='file' and contains(@accept, 'video')]"
            ],
            
            # Selector untuk verifikasi media upload
            'media_verification': [
                # Video element yang menunjukkan media sudah ter-upload
                "//video",
                "//img[contains(@src, 'blob:')]",
                "//div[contains(@aria-label, 'Video')]",
                "//div[contains(@class, 'x1lliihq')]//video",
                "//div[contains(text(), 'Video Options')]",
                "//button[contains(text(), 'Video Options')]"
            ]
        }

    def _log(self, message: str, level: str = "INFO"):
        """Enhanced logging dengan warna"""
        colors = {
            "INFO": Fore.CYAN,
            "SUCCESS": Fore.GREEN,
            "WARNING": Fore.YELLOW,
            "ERROR": Fore.RED,
            "DEBUG": Fore.MAGENTA
        }
        
        if level == "DEBUG" and not self.debug:
            return
            
        color = colors.get(level, Fore.WHITE)
        icons = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "DEBUG": "🔍"
        }
        
        icon = icons.get(level, "📝")
        print(f"{color}{icon} {message}{Style.RESET_ALL}")

    def _get_chromedriver_path(self):
        """Get ChromeDriver path dengan fallback untuk Windows"""
        try:
            self._log("Mendownload ChromeDriver terbaru...")
            driver_path = ChromeDriverManager().install()
            
            if os.path.exists(driver_path):
                if platform.system() == "Windows" and not driver_path.endswith('.exe'):
                    driver_dir = os.path.dirname(driver_path)
                    for file in os.listdir(driver_dir):
                        if file.endswith('.exe') and 'chromedriver' in file.lower():
                            driver_path = os.path.join(driver_dir, file)
                            break
                
                self._log(f"ChromeDriver ditemukan: {driver_path}", "SUCCESS")
                return driver_path
            else:
                raise FileNotFoundError("ChromeDriver tidak ditemukan setelah download")
                
        except Exception as e:
            self._log(f"Error downloading ChromeDriver: {e}", "WARNING")
            
            self._log("Mencari ChromeDriver di sistem PATH...")
            chrome_names = ['chromedriver', 'chromedriver.exe']
            for name in chrome_names:
                import shutil
                path = shutil.which(name)
                if path:
                    self._log(f"ChromeDriver ditemukan di PATH: {path}", "SUCCESS")
                    return path
            
            if platform.system() == "Windows":
                common_paths = [
                    r"C:\Program Files\Google\Chrome\Application\chromedriver.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chromedriver.exe",
                    r"C:\chromedriver\chromedriver.exe",
                    r"C:\tools\chromedriver.exe"
                ]
                
                for path in common_paths:
                    if os.path.exists(path):
                        self._log(f"ChromeDriver ditemukan: {path}", "SUCCESS")
                        return path
            
            raise FileNotFoundError("ChromeDriver tidak ditemukan. Silakan install Chrome dan ChromeDriver.")

    def _setup_driver(self):
        """Setup Chrome WebDriver dengan konfigurasi optimal untuk Facebook"""
        self._log("Menyiapkan browser untuk Facebook...")
        
        chrome_options = Options()
        
        # Basic options
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--window-size=1280,800")
        
        # Chrome options yang aman untuk Facebook
        if self.headless:
            chrome_options.add_argument('--headless=new')
            self._log("Mode headless diaktifkan", "WARNING")
        else:
            self._log("Mode normal (dengan gambar) diaktifkan", "SUCCESS")
        
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-plugins-discovery')
        chrome_options.add_argument('--disable-translate')
        chrome_options.add_argument('--disable-popup-blocking')
        chrome_options.add_argument('--disable-notifications')
        chrome_options.add_argument('--disable-geolocation')
        chrome_options.add_argument('--disable-media-stream')
        
        # User agent yang realistis
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Suppress logs tapi tetap izinkan gambar
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--silent")
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument("--disable-gpu-logging")
        
        # Anti-detection options
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--disable-web-security")
        
        # Prefs untuk memastikan gambar dimuat
        prefs = {
            "profile.managed_default_content_settings.images": 1,  # 1 = allow images
            "profile.default_content_setting_values.notifications": 2,  # 2 = block notifications
            "profile.default_content_settings.popups": 0  # 0 = allow popups (untuk composer)
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        try:
            driver_path = self._get_chromedriver_path()
            
            service = Service(
                driver_path,
                log_path=os.devnull,
                service_args=['--silent']
            )
            
            os.environ['WDM_LOG_LEVEL'] = '0'
            os.environ['WDM_PRINT_FIRST_LINE'] = 'False'
            
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Anti-detection script
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Setup wait
            self.wait = WebDriverWait(self.driver, 30)
            
            self._log("Browser siap digunakan", "SUCCESS")
            
        except Exception as e:
            self._log(f"Gagal menyiapkan browser: {str(e)}", "ERROR")
            raise

    def _find_element_by_xpath_list(self, xpath_list: list, timeout: int = 10) -> Optional[Any]:
        """Mencari elemen menggunakan multiple XPath selectors"""
        for i, xpath in enumerate(xpath_list):
            try:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                self._log(f"Elemen ditemukan dengan XPath #{i+1}", "SUCCESS")
                return element
            except TimeoutException:
                continue
        
        self._log("Semua XPath selector gagal", "WARNING")
        return None

    def _find_text_element_by_xpath_list(self, xpath_list: list, timeout: int = 10) -> Optional[Any]:
        """Mencari text element yang bisa menerima input"""
        for i, xpath in enumerate(xpath_list):
            try:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
                
                # Cek apakah element bisa menerima input
                if element.is_displayed() and element.is_enabled():
                    # Cek apakah contenteditable
                    if element.get_attribute('contenteditable') == 'true':
                        self._log(f"Text element ditemukan dengan XPath #{i+1}", "SUCCESS")
                        return element
                    
            except TimeoutException:
                continue
        
        self._log("Semua text XPath selector gagal", "WARNING")
        return None

    def _find_file_input_direct(self, timeout: int = 10) -> Optional[Any]:
        """Mencari input file yang langsung tersedia setelah composer terbuka"""
        self._log("Mencari input file yang langsung tersedia...")
        
        for i, xpath in enumerate(self.selectors['media_input_direct']):
            try:
                # Cari input file yang sudah ada (tidak perlu clickable, cukup present)
                element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
                
                # Cek apakah element adalah input file yang valid
                if (element.tag_name.lower() == 'input' and 
                    element.get_attribute('type') == 'file'):
                    
                    self._log(f"Input file ditemukan langsung dengan XPath #{i+1}", "SUCCESS")
                    return element
                    
            except TimeoutException:
                continue
        
        self._log("Input file tidak ditemukan", "WARNING")
        return None

    def _verify_media_upload(self, timeout: int = 10) -> bool:
        """Verifikasi apakah media sudah ter-upload dengan benar"""
        self._log("Memverifikasi apakah media sudah ter-upload...")
        
        for i, xpath in enumerate(self.selectors['media_verification']):
            try:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
                
                if element.is_displayed():
                    self._log(f"✅ ✅ Media berhasil ter-upload! (selector #{i+1})", "SUCCESS")
                    return True
                    
            except TimeoutException:
                continue
        
        self._log("❌ Media upload tidak dapat diverifikasi", "WARNING")
        return False

    def _input_text_in_same_composer(self, text: str) -> bool:
        """Input text di composer yang sama setelah media upload - TANPA membuat composer baru"""
        self._log("🎯 Mengetik text di composer yang sama (tanpa membuat composer baru)...")
        
        strategies = [
            # Strategy 1: Cari elemen contenteditable yang visible di composer yang sudah terbuka
            lambda t: self._strategy_find_contenteditable_in_current_composer(t),
            
            # Strategy 2: Klik di area atas video dan ketik
            lambda t: self._strategy_click_above_video_and_type(t),
            
            # Strategy 3: Focus pada form dan ketik
            lambda t: self._strategy_focus_form_and_type(t),
            
            # Strategy 4: JavaScript injection langsung ke elemen yang tepat
            lambda t: self._strategy_javascript_injection(t),
            
            # Strategy 5: Simulasi Tab dan ketik
            lambda t: self._strategy_tab_and_type(t)
        ]
        
        for i, strategy in enumerate(strategies, 1):
            try:
                self._log(f"🎯 Mencoba strategi #{i}...")
                
                if strategy(text):
                    # Verifikasi dengan mencari text di halaman
                    time.sleep(2)
                    page_source = self.driver.page_source
                    if text.lower() in page_source.lower():
                        self._log(f"✅ ✅ Text berhasil diketik dengan strategi #{i}!", "SUCCESS")
                        return True
                    else:
                        self._log(f"⚠️ Strategi #{i} tidak terverifikasi", "WARNING")
                        
            except Exception as e:
                self._log(f"❌ Strategi #{i} gagal: {str(e)}", "DEBUG")
                continue
        
        self._log("❌ ❌ Semua strategi input text di composer yang sama gagal", "ERROR")
        return False

    def _strategy_find_contenteditable_in_current_composer(self, text: str) -> bool:
        """Strategy 1: Cari elemen contenteditable di composer yang sudah terbuka"""
        try:
            # Cari semua elemen contenteditable yang visible
            elements = self.driver.find_elements(By.CSS_SELECTOR, "div[contenteditable='true']")
            
            for element in elements:
                if element.is_displayed() and element.is_enabled():
                    # Cek apakah elemen ini ada di dalam composer (form)
                    parent_form = element.find_element(By.XPATH, "./ancestor::form")
                    if parent_form:
                        self._log("Menemukan text area di dalam composer yang sudah terbuka")
                        element.click()
                        time.sleep(0.5)
                        element.clear()
                        element.send_keys(text)
                        return True
                        
        except Exception as e:
            self._log(f"Strategy 1 error: {str(e)}", "DEBUG")
            return False
        
        return False

    def _strategy_click_above_video_and_type(self, text: str) -> bool:
        """Strategy 2: Klik di area atas video dan ketik"""
        try:
            # Cari video element
            video = self.driver.find_element(By.TAG_NAME, "video")
            if video.is_displayed():
                # Klik di area atas video (kemungkinan ada text area di sana)
                video_location = video.location
                video_size = video.size
                
                # Klik di atas video
                click_x = video_location['x'] + (video_size['width'] // 2)
                click_y = video_location['y'] - 50  # 50px di atas video
                
                ActionChains(self.driver).move_by_offset(click_x, click_y).click().perform()
                time.sleep(0.5)
                
                # Ketik text
                ActionChains(self.driver).send_keys(text).perform()
                return True
                
        except Exception as e:
            self._log(f"Strategy 2 error: {str(e)}", "DEBUG")
            return False
        
        return False

    def _strategy_focus_form_and_type(self, text: str) -> bool:
        """Strategy 3: Focus pada form dan ketik"""
        try:
            # Cari form composer
            form = self.driver.find_element(By.TAG_NAME, "form")
            if form.is_displayed():
                form.click()
                time.sleep(0.5)
                
                # Tab untuk focus ke text area
                ActionChains(self.driver).send_keys(Keys.TAB).perform()
                time.sleep(0.5)
                
                # Ketik text
                ActionChains(self.driver).send_keys(text).perform()
                return True
                
        except Exception as e:
            self._log(f"Strategy 3 error: {str(e)}", "DEBUG")
            return False
        
        return False

    def _strategy_javascript_injection(self, text: str) -> bool:
        """Strategy 4: JavaScript injection langsung"""
        try:
            script = """
            // Cari elemen contenteditable yang visible di dalam form
            var forms = document.querySelectorAll('form');
            for (var f = 0; f < forms.length; f++) {
                var editables = forms[f].querySelectorAll('div[contenteditable="true"]');
                for (var i = 0; i < editables.length; i++) {
                    var el = editables[i];
                    if (el.offsetParent !== null && el.offsetHeight > 0) { // visible
                        el.focus();
                        el.innerHTML = '<p>' + arguments[0] + '</p>';
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                        return true;
                    }
                }
            }
            return false;
            """
            
            result = self.driver.execute_script(script, text)
            return bool(result)
            
        except Exception as e:
            self._log(f"Strategy 4 error: {str(e)}", "DEBUG")
            return False

    def _strategy_tab_and_type(self, text: str) -> bool:
        """Strategy 5: Simulasi Tab dan ketik"""
        try:
            # Klik di body untuk focus
            body = self.driver.find_element(By.TAG_NAME, "body")
            body.click()
            time.sleep(0.5)
            
            # Tab beberapa kali untuk mencari text area
            for i in range(5):
                ActionChains(self.driver).send_keys(Keys.TAB).perform()
                time.sleep(0.3)
                
                # Coba ketik
                ActionChains(self.driver).send_keys(text).perform()
                time.sleep(0.5)
                
                # Cek apakah text muncul
                page_source = self.driver.page_source
                if text.lower() in page_source.lower():
                    return True
                
                # Hapus text yang mungkin salah tempat
                ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
                ActionChains(self.driver).send_keys(Keys.BACKSPACE).perform()
            
            return False
            
        except Exception as e:
            self._log(f"Strategy 5 error: {str(e)}", "DEBUG")
            return False

    def _input_text_safely(self, element, text: str) -> bool:
        """Input text dengan berbagai metode yang aman - Enhanced untuk Facebook"""
        self._log(f"Memasukkan text: {text[:50]}...")
        
        strategies = [
            # Strategy 1: Click + clear + send_keys
            lambda e, t: (e.click(), time.sleep(0.5), e.clear(), e.send_keys(t)),
            
            # Strategy 2: Focus + select all + type
            lambda e, t: (
                e.click(),
                time.sleep(0.5),
                e.send_keys(Keys.CONTROL + "a"),
                time.sleep(0.2),
                e.send_keys(t)
            ),
            
            # Strategy 3: ActionChains click + type
            lambda e, t: (
                ActionChains(self.driver).move_to_element(e).click().perform(),
                time.sleep(0.5),
                ActionChains(self.driver).send_keys(Keys.CONTROL + "a").perform(),
                time.sleep(0.2),
                ActionChains(self.driver).send_keys(t).perform()
            ),
            
            # Strategy 4: JavaScript innerHTML
            lambda e, t: self.driver.execute_script("arguments[0].innerHTML = arguments[1];", e, t),
            
            # Strategy 5: JavaScript textContent
            lambda e, t: self.driver.execute_script("arguments[0].textContent = arguments[1];", e, t),
            
            # Strategy 6: JavaScript focus + value (untuk input elements)
            lambda e, t: (
                self.driver.execute_script("arguments[0].focus();", e),
                time.sleep(0.3),
                self.driver.execute_script("arguments[0].value = arguments[1];", e, t),
                self.driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", e)
            ),
            
            # Strategy 7: JavaScript dengan data-text attribute (khusus Facebook)
            lambda e, t: (
                self.driver.execute_script("arguments[0].setAttribute('data-text', arguments[1]);", e, t),
                self.driver.execute_script("arguments[0].textContent = arguments[1];", e, t),
                self.driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", e)
            )
        ]
        
        for i, strategy in enumerate(strategies, 1):
            try:
                self._log(f"Mencoba strategi input #{i}...")
                strategy(element, text)
                
                # Verifikasi apakah text berhasil dimasukkan
                time.sleep(1)
                current_text = (element.get_attribute('textContent') or 
                              element.get_attribute('innerHTML') or 
                              element.get_attribute('value') or 
                              element.text or "")
                
                if text.lower() in current_text.lower() or len(current_text.strip()) > 0:
                    self._log(f"Text berhasil dimasukkan dengan strategi #{i}", "SUCCESS")
                    return True
                    
            except Exception as e:
                self._log(f"Strategi #{i} gagal: {str(e)}", "DEBUG")
                continue
        
        self._log("Semua strategi input text gagal", "ERROR")
        return False

    def _click_element_with_retry(self, element, description: str = "element") -> bool:
        """Click element dengan multiple strategies dan retry"""
        self._log(f"Mengklik '{description}'...")
        
        strategies = [
            ("regular", lambda e: e.click()),
            ("javascript", lambda e: self.driver.execute_script("arguments[0].click();", e)),
            ("action_chains", lambda e: ActionChains(self.driver).move_to_element(e).click().perform()),
            ("send_enter", lambda e: e.send_keys(Keys.ENTER)),
            ("send_space", lambda e: e.send_keys(Keys.SPACE))
        ]
        
        for strategy_name, strategy_func in strategies:
            try:
                self._log(f"Mencoba {strategy_name} click...")
                strategy_func(element)
                self._log(f"Berhasil klik dengan {strategy_name}", "SUCCESS")
                time.sleep(2)
                return True
                
            except Exception as e:
                self._log(f"{strategy_name} click gagal: {str(e)}", "DEBUG")
                continue
        
        self._log(f"Semua strategi klik gagal untuk '{description}'", "ERROR")
        return False

    def _upload_media_direct(self, media_path: str) -> bool:
        """Upload media langsung ke input file yang sudah tersedia"""
        self._log(f"Mengupload media langsung: {os.path.basename(media_path)}")
        
        try:
            # Cari input file yang langsung tersedia setelah composer terbuka
            file_input = self._find_file_input_direct(timeout=10)
            
            if file_input:
                abs_path = os.path.abspath(media_path)
                self._log(f"Mengirim file langsung ke input: {abs_path}")
                
                # Kirim file ke input
                file_input.send_keys(abs_path)
                
                self._log("Media berhasil diupload langsung!", "SUCCESS")
                time.sleep(5)  # Wait for upload to process
                return True
            else:
                self._log("Input file tidak ditemukan untuk upload langsung", "ERROR")
                return False
                
        except Exception as e:
            self._log(f"Gagal mengupload media langsung: {str(e)}", "ERROR")
            return False

    def load_cookies(self) -> bool:
        """Load cookies dari file JSON"""
        if not self.cookies_path.exists():
            self._log("File cookies tidak ditemukan", "WARNING")
            return False
            
        try:
            with open(self.cookies_path, 'r', encoding='utf-8') as f:
                cookies_data = json.load(f)
            
            if isinstance(cookies_data, dict):
                cookies = cookies_data.get('cookies', [])
            else:
                cookies = cookies_data
            
            if not cookies:
                self._log("File cookies kosong", "WARNING")
                return False
            
            # Navigate ke Facebook dulu sebelum set cookies
            self.driver.get(self.base_url)
            time.sleep(2)
            
            # Add cookies
            cookies_added = 0
            for cookie in cookies:
                try:
                    if 'name' in cookie and 'value' in cookie:
                        clean_cookie = {
                            'name': cookie['name'],
                            'value': cookie['value'],
                            'domain': cookie.get('domain', '.facebook.com'),
                            'path': cookie.get('path', '/'),
                        }
                        
                        if 'expiry' in cookie:
                            clean_cookie['expiry'] = int(cookie['expiry'])
                        elif 'expires' in cookie:
                            clean_cookie['expiry'] = int(cookie['expires'])
                        
                        if 'secure' in cookie:
                            clean_cookie['secure'] = cookie['secure']
                        if 'httpOnly' in cookie:
                            clean_cookie['httpOnly'] = cookie['httpOnly']
                        
                        self.driver.add_cookie(clean_cookie)
                        cookies_added += 1
                        
                except Exception as e:
                    if self.debug:
                        self._log(f"Gagal menambahkan cookie {cookie.get('name', 'unknown')}: {e}", "DEBUG")
            
            self._log(f"Cookies dimuat: {cookies_added}/{len(cookies)}", "SUCCESS")
            return cookies_added > 0
            
        except Exception as e:
            self._log(f"Gagal memuat cookies: {str(e)}", "ERROR")
            return False

    def save_cookies(self):
        """Simpan cookies ke file JSON"""
        try:
            cookies = self.driver.get_cookies()
            
            cookies_data = {
                "timestamp": int(time.time()),
                "cookies": cookies
            }
            
            with open(self.cookies_path, 'w', encoding='utf-8') as f:
                json.dump(cookies_data, f, indent=2, ensure_ascii=False)
            
            self._log(f"Cookies disimpan: {len(cookies)} item", "SUCCESS")
            
        except Exception as e:
            self._log(f"Gagal menyimpan cookies: {str(e)}", "ERROR")

    def clear_cookies(self):
        """Hapus file cookies"""
        try:
            if self.cookies_path.exists():
                self.cookies_path.unlink()
                self._log("Cookies berhasil dihapus", "SUCCESS")
            else:
                self._log("Tidak ada cookies untuk dihapus", "WARNING")
        except Exception as e:
            self._log(f"Gagal menghapus cookies: {str(e)}", "ERROR")

    def check_login_required(self) -> bool:
        """Cek apakah perlu login"""
        current_url = self.driver.current_url
        return "login" in current_url or "checkpoint" in current_url

    def wait_for_login(self, timeout: int = 180):
        """Tunggu user login manual"""
        self._log("Silakan login secara manual di browser...", "WARNING")
        self._log(f"Menunggu login selesai (timeout {timeout} detik)...", "INFO")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            current_url = self.driver.current_url
            
            if not ("login" in current_url or "checkpoint" in current_url):
                self._log("Login berhasil!", "SUCCESS")
                self.save_cookies()
                return True
            
            time.sleep(2)
        
        raise TimeoutException("Timeout menunggu login")

    def take_screenshot(self, filename: str = None):
        """Ambil screenshot untuk debugging"""
        if not filename:
            filename = f"facebook_{int(time.time())}.png"
        
        screenshot_path = self.screenshots_dir / filename
        
        try:
            if self.driver:
                self.driver.save_screenshot(str(screenshot_path))
                self._log(f"Screenshot saved: {screenshot_path.name}", "INFO")
                return str(screenshot_path)
            else:
                self._log("Driver tidak tersedia untuk screenshot", "WARNING")
                return None
        except Exception as e:
            self._log(f"Gagal menyimpan screenshot: {str(e)}", "WARNING")
            return None

    def upload_status(self, status_text: str = "", media_path: str = "") -> Dict[str, Any]:
        """
        Upload status ke Facebook dengan pendekatan yang lebih robust
        
        Args:
            status_text: Text status
            media_path: Path ke file media (video/gambar)
            
        Returns:
            Dict dengan status upload
        """
        try:
            # Setup driver
            self._setup_driver()
            
            # Load cookies
            cookies_loaded = self.load_cookies()
            
            # Navigate ke Facebook
            self._log("Navigating to Facebook...")
            self.driver.get(self.base_url)
            time.sleep(5)
            
            # Take screenshot before starting
            self.take_screenshot(f"facebook_before_post_{int(time.time())}.png")
            
            # Cek apakah perlu login
            if self.check_login_required():
                if cookies_loaded:
                    self._log("Cookies dimuat tapi masih perlu login, refresh halaman...", "WARNING")
                    self.driver.refresh()
                    time.sleep(5)
                
                if self.check_login_required():
                    self.wait_for_login()
                    self.driver.get(self.base_url)
                    time.sleep(5)
            
            # Determine mode
            if status_text and media_path:
                mode = "TEXT + MEDIA"
            elif media_path:
                mode = "MEDIA ONLY"
            elif status_text:
                mode = "TEXT ONLY"
            else:
                raise ValueError("Minimal status text atau media diperlukan")
            
            self._log(f"MODE: {mode}")
            
            # Step 1: Klik area "What's on your mind" untuk membuka composer SEKALI SAJA
            self._log("Mencari area 'What's on your mind' untuk membuka composer...")
            
            trigger_element = self._find_element_by_xpath_list(self.selectors['status_trigger_xpath'])
            
            if not trigger_element:
                raise NoSuchElementException("Area 'What's on your mind' tidak ditemukan")
            
            # Klik area trigger untuk membuka composer
            if not self._click_element_with_retry(trigger_element, "Area What's on your mind"):
                raise Exception("Gagal mengklik area 'What's on your mind'")
            
            time.sleep(3)  # Wait for composer to open
            
            # Take screenshot after composer opens
            self.take_screenshot(f"facebook_composer_opened_{int(time.time())}.png")
            
            # Step 2: Handle media upload LANGSUNG jika ada (input file sudah tersedia)
            media_uploaded = False
            if media_path and os.path.exists(media_path):
                self._log("Mencoba upload media langsung setelah composer terbuka...")
                
                if self._upload_media_direct(media_path):
                    # Verifikasi media upload
                    if self._verify_media_upload():
                        self._log("✅ ✅ Media upload berhasil diverifikasi!", "SUCCESS")
                        media_uploaded = True
                        # Take screenshot after media upload
                        self.take_screenshot(f"facebook_media_uploaded_{int(time.time())}.png")
                    else:
                        self._log("⚠️ Media upload tidak dapat diverifikasi", "WARNING")
                else:
                    self._log("Media upload gagal, melanjutkan tanpa media...", "WARNING")
            
            # Step 3: Input text - PENTING: JANGAN BUAT COMPOSER BARU!
            if status_text:
                if media_uploaded:
                    # 🎯 JIKA MEDIA SUDAH DIUPLOAD, KETIK DI COMPOSER YANG SAMA!
                    self._log("🎯 Media sudah ter-upload, mengetik text di composer yang sama...")
                    
                    if not self._input_text_in_same_composer(status_text):
                        # Fallback: cari elemen text area setelah media upload
                        self._log("Fallback: Mencari area text input setelah media upload...")
                        text_element = self._find_text_element_by_xpath_list(self.selectors['composer_text_area_after_media'])
                        
                        if text_element:
                            if not self._input_text_safely(text_element, status_text):
                                raise Exception("Gagal memasukkan text ke composer")
                        else:
                            raise Exception("Text area tidak ditemukan setelah media upload")
                else:
                    # Jika tidak ada media, gunakan selector biasa
                    self._log("Mencari area text input di composer...")
                    text_element = self._find_text_element_by_xpath_list(self.selectors['composer_text_area'])
                    
                    if not text_element:
                        raise NoSuchElementException("Text area di composer tidak ditemukan")
                    
                    # Input text dengan metode yang aman
                    if not self._input_text_safely(text_element, status_text):
                        raise Exception("Gagal memasukkan text ke composer")
                
                time.sleep(2)
            
            # Step 4: Klik tombol Post
            self._log("Mencari tombol Post di composer...")
            
            post_element = self._find_element_by_xpath_list(self.selectors['post_button_composer'])
            if not post_element:
                raise NoSuchElementException("Tombol Post tidak ditemukan")
            
            if self._click_element_with_retry(post_element, "Post Button"):
                self._log("Post berhasil diklik", "SUCCESS")
                time.sleep(5)
                
                # Take screenshot after post
                self.take_screenshot(f"facebook_after_post_{int(time.time())}.png")
                
                # Cek apakah kembali ke feed (indikasi sukses)
                current_url = self.driver.current_url
                if self.base_url in current_url and "composer" not in current_url:
                    self._log("Status berhasil dipost ke Facebook!", "SUCCESS")
                    return {
                        "success": True,
                        "message": "Status berhasil dipost",
                        "status_text": status_text,
                        "media_path": media_path,
                        "mode": mode
                    }
                else:
                    return {
                        "success": False,
                        "message": "Post mungkin berhasil tapi tidak dapat dikonfirmasi",
                        "status_text": status_text,
                        "media_path": media_path,
                        "mode": mode
                    }
            else:
                raise Exception("Gagal mengklik tombol Post")
                
        except Exception as e:
            error_msg = f"Facebook status upload gagal: {str(e)}"
            self._log(error_msg, "ERROR")
            
            # Ambil screenshot untuk debugging
            self.take_screenshot(f"facebook_error_{int(time.time())}.png")
            
            return {
                "success": False,
                "message": error_msg,
                "status_text": status_text,
                "media_path": media_path
            }
        
        finally:
            if self.driver:
                self._log("Closing browser...")
                try:
                    self.driver.quit()
                except:
                    pass

    def upload_reels(self, video_path: str, description: str = "") -> Dict[str, Any]:
        """
        Upload reels ke Facebook
        
        Args:
            video_path: Path ke file video
            description: Deskripsi reels
            
        Returns:
            Dict dengan status upload
        """
        try:
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"File video tidak ditemukan: {video_path}")
            
            # Setup driver
            self._setup_driver()
            
            # Load cookies
            cookies_loaded = self.load_cookies()
            
            # Navigate ke Facebook Reels Create
            self._log("Navigasi ke Facebook Reels Create...")
            self.driver.get(self.reels_url)
            time.sleep(3)
            
            # Cek apakah perlu login
            if self.check_login_required():
                if cookies_loaded:
                    self._log("Cookies dimuat tapi masih perlu login, refresh halaman...", "WARNING")
                    self.driver.refresh()
                    time.sleep(3)
                
                if self.check_login_required():
                    self.wait_for_login()
                    self.driver.get(self.reels_url)
                    time.sleep(3)
            
            self._log("Memulai upload video reels...")
            
            # Upload video
            try:
                upload_input = self.driver.find_element(By.XPATH, "//input[@type='file' and contains(@accept, 'video')]")
                abs_path = os.path.abspath(video_path)
                upload_input.send_keys(abs_path)
                self._log("File video berhasil dikirim ke input.", "SUCCESS")
                time.sleep(5)
            except Exception as e:
                raise Exception(f"Gagal mengupload video: {str(e)}")
            
            # Click Next buttons (bisa ada beberapa step)
            for i in range(1, 4):  # Max 3 next buttons
                try:
                    # Cari tombol Next/Berikutnya
                    next_buttons = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Next') or contains(text(), 'Berikutnya')]")
                    if next_buttons:
                        next_buttons[0].click()
                        self._log(f"Tombol 'Next' berhasil diklik (step {i})!", "SUCCESS")
                        time.sleep(3)
                    else:
                        break
                except:
                    break
            
            # Add description jika ada
            if description:
                self._log("Mengisi deskripsi reels...")
                try:
                    desc_inputs = self.driver.find_elements(By.XPATH, "//div[@contenteditable='true']")
                    if desc_inputs:
                        desc_inputs[0].clear()
                        desc_inputs[0].send_keys(description)
                        self._log("Deskripsi berhasil diisi", "SUCCESS")
                        time.sleep(1)
                except:
                    self._log("Gagal mengisi deskripsi", "WARNING")
            
            # Publish reels
            self._log("Mencari tombol publish...")
            try:
                publish_buttons = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Publish') or contains(text(), 'Terbitkan')]")
                if publish_buttons:
                    publish_buttons[0].click()
                    self._log("Tombol 'Publish' berhasil diklik!", "SUCCESS")
                    time.sleep(5)
                else:
                    raise Exception("Tombol publish tidak ditemukan")
            except Exception as e:
                raise Exception(f"Gagal mengklik tombol publish: {str(e)}")
            
            self._log("Upload video reels berhasil!", "SUCCESS")
            self._log("Reels berhasil diupload ke Facebook!", "SUCCESS")
            
            return {
                "success": True,
                "message": "Reels berhasil diupload",
                "video_path": video_path,
                "description": description
            }
            
        except Exception as e:
            error_msg = f"Facebook reels upload gagal: {str(e)}"
            self._log(error_msg, "ERROR")
            
            # Ambil screenshot untuk debugging
            self.take_screenshot(f"facebook_reels_error_{int(time.time())}.png")
            
            return {
                "success": False,
                "message": error_msg,
                "video_path": video_path,
                "description": description
            }
        
        finally:
            if self.driver:
                self._log("Menutup browser...")
                try:
                    self.driver.quit()
                except:
                    pass

    def check_cookies_status(self):
        """Cek status cookies"""
        if not self.cookies_path.exists():
            self._log("File cookies tidak ditemukan", "WARNING")
            return {"exists": False, "count": 0}
        
        try:
            with open(self.cookies_path, 'r', encoding='utf-8') as f:
                cookies_data = json.load(f)
            
            if isinstance(cookies_data, dict):
                cookies = cookies_data.get('cookies', [])
                timestamp = cookies_data.get('timestamp', 0)
            else:
                cookies = cookies_data if isinstance(cookies_data, list) else []
                timestamp = 0
            
            # Cek cookies yang expired
            current_time = time.time()
            valid_cookies = []
            expired_cookies = []
            
            for cookie in cookies:
                if 'expiry' in cookie:
                    if cookie['expiry'] > current_time:
                        valid_cookies.append(cookie)
                    else:
                        expired_cookies.append(cookie)
                elif 'expires' in cookie:
                    if cookie['expires'] > current_time:
                        valid_cookies.append(cookie)
                    else:
                        expired_cookies.append(cookie)
                else:
                    valid_cookies.append(cookie)  # Session cookies
            
            self._log(f"Total cookies: {len(cookies)}", "INFO")
            self._log(f"Valid cookies: {len(valid_cookies)}", "SUCCESS")
            
            if expired_cookies:
                self._log(f"Expired cookies: {len(expired_cookies)}", "WARNING")
            
            if timestamp:
                import datetime
                saved_time = datetime.datetime.fromtimestamp(timestamp)
                self._log(f"Cookies disimpan: {saved_time.strftime('%Y-%m-%d %H:%M:%S')}", "INFO")
            
            return {
                "exists": True,
                "total": len(cookies),
                "valid": len(valid_cookies),
                "expired": len(expired_cookies),
                "timestamp": timestamp
            }
            
        except Exception as e:
            self._log(f"Error membaca cookies: {str(e)}", "ERROR")
            return {"exists": True, "error": str(e)}


def main():
    """Main function untuk CLI"""
    parser = argparse.ArgumentParser(description="Facebook Uploader (Status & Reels)")
    parser.add_argument("--type", "-t", choices=['status', 'reels'], help="Jenis upload (status/reels)")
    parser.add_argument("--status", "-s", help="Status text untuk Facebook")
    parser.add_argument("--media", "-m", help="Path ke file media (video/gambar) untuk status")
    parser.add_argument("--video", "-v", help="Path ke file video untuk reels")
    parser.add_argument("--description", "-d", default="", help="Deskripsi untuk reels")
    parser.add_argument("--headless", action="store_true", help="Jalankan dalam mode headless")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--clear-cookies", action="store_true", help="Hapus cookies")
    parser.add_argument("--check-cookies", action="store_true", help="Cek status cookies")
    
    args = parser.parse_args()
    
    uploader = FacebookUploader(headless=args.headless, debug=args.debug)
    
    # Handle different actions
    if args.clear_cookies:
        uploader.clear_cookies()
        return
    
    if args.check_cookies:
        uploader.check_cookies_status()
        return
    
    if args.type:
        if args.type == 'status':
            if not args.status and not args.media:
                print(f"{Fore.RED}❌ Status text atau media diperlukan untuk Facebook status")
                sys.exit(1)
            
            if args.media and not os.path.exists(args.media):
                print(f"{Fore.RED}❌ File media tidak ditemukan: {args.media}")
                sys.exit(1)
            
            result = uploader.upload_status(args.status or "", args.media or "")
            
            if result["success"]:
                print(f"{Fore.GREEN}🎉 Facebook status berhasil!")
            else:
                print(f"{Fore.RED}❌ Facebook status gagal: {result['message']}")
                sys.exit(1)
        
        elif args.type == 'reels':
            if not args.video:
                print(f"{Fore.RED}❌ Video path diperlukan untuk Facebook Reels")
                sys.exit(1)
            if not os.path.exists(args.video):
                print(f"{Fore.RED}❌ File video tidak ditemukan: {args.video}")
                sys.exit(1)
            
            result = uploader.upload_reels(args.video, args.description)
            
            if result["success"]:
                print(f"{Fore.GREEN}🎉 Facebook Reels berhasil!")
            else:
                print(f"{Fore.RED}❌ Facebook Reels gagal: {result['message']}")
                sys.exit(1)
    else:
        # Interactive mode
        print(f"{Fore.BLUE}📘 Facebook Uploader")
        print("=" * 40)
        print(f"{Fore.YELLOW}🔥 Status & Reels Support")
        print()
        
        while True:
            print(f"\n{Fore.YELLOW}Pilih jenis upload:")
            print("1. 📝 Facebook Status (Text/Media)")
            print("2. 🎬 Facebook Reels (Video)")
            print("3. 🍪 Cek status cookies")
            print("4. 🗑️ Hapus cookies")
            print("5. ❌ Keluar")
            
            choice = input(f"\n{Fore.WHITE}Pilihan (1-5): ").strip()
            
            if choice == "1":
                print(f"\n{Fore.YELLOW}📝 Facebook Status Options:")
                print("1. Text Only")
                print("2. Text + Media")
                print("3. Media Only")
                
                status_choice = input(f"{Fore.WHITE}Pilihan (1-3): ").strip()
                
                status_text = ""
                media_path = ""
                
                if status_choice in ["1", "2"]:
                    status_text = input(f"{Fore.CYAN}Status Facebook: ").strip()
                    if not status_text and status_choice == "1":
                        print(f"{Fore.RED}❌ Status text tidak boleh kosong untuk text only!")
                        continue
                
                if status_choice in ["2", "3"]:
                    media_path = input(f"{Fore.CYAN}Path ke file media (video/gambar): ").strip()
                    if not os.path.exists(media_path):
                        print(f"{Fore.RED}❌ File media tidak ditemukan!")
                        continue
                
                if not status_text and not media_path:
                    print(f"{Fore.RED}❌ Minimal status text atau media diperlukan!")
                    continue
                
                result = uploader.upload_status(status_text, media_path)
                
                if result["success"]:
                    print(f"{Fore.GREEN}🎉 Facebook status berhasil!")
                else:
                    print(f"{Fore.RED}❌ Facebook status gagal: {result['message']}")
            
            elif choice == "2":
                video_path = input(f"{Fore.CYAN}Path ke file video: ").strip()
                if not os.path.exists(video_path):
                    print(f"{Fore.RED}❌ File tidak ditemukan!")
                    continue
                
                description = input(f"{Fore.CYAN}Deskripsi Facebook Reels (opsional): ").strip()
                
                result = uploader.upload_reels(video_path, description)
                
                if result["success"]:
                    print(f"{Fore.GREEN}🎉 Facebook Reels berhasil!")
                else:
                    print(f"{Fore.RED}❌ Facebook Reels gagal: {result['message']}")
            
            elif choice == "3":
                uploader.check_cookies_status()
            
            elif choice == "4":
                confirm = input(f"{Fore.YELLOW}Yakin ingin menghapus cookies? (y/N): ").strip().lower()
                if confirm == 'y':
                    uploader.clear_cookies()
            
            elif choice == "5":
                print(f"{Fore.YELLOW}👋 Sampai jumpa!")
                break
            
            else:
                print(f"{Fore.RED}❌ Pilihan tidak valid!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}👋 Program dihentikan oleh user")
    except Exception as e:
        print(f"{Fore.RED}💥 Error fatal: {str(e)}")
        sys.exit(1)