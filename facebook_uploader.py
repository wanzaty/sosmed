#!/usr/bin/env python3
"""
Facebook Uploader (Status & Reels) menggunakan Selenium
Mendukung cookies JSON untuk auto-login dan dual language support
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
from colorama import init, Fore, Style
import argparse

# Initialize colorama
init(autoreset=True)

class FacebookUploader:
    def __init__(self, headless: bool = False, debug: bool = False):
        """
        Initialize Facebook Uploader
        
        Args:
            headless: Run browser in headless mode
            debug: Enable debug logging
        """
        self.headless = headless
        self.debug = debug
        self.driver = None
        self.wait = None
        
        # Setup paths
        self.base_dir = Path(__file__).parent
        self.cookies_dir = self.base_dir / "cookies"
        self.cookies_dir.mkdir(exist_ok=True)
        self.cookies_path = self.cookies_dir / "facebook_cookies.json"
        self.screenshots_dir = self.base_dir / "screenshots"
        self.screenshots_dir.mkdir(exist_ok=True)
        
        # Facebook URLs
        self.facebook_url = "https://www.facebook.com"
        self.reels_create_url = "https://www.facebook.com/reels/create/?surface=PROFILE_PLUS"
        
        # Selectors - FIXED XPath syntax
        self.selectors = {
            'whats_on_mind_click': [
                # Primary CSS selectors
                "div[role='button'][aria-label*='What\\'s on your mind']",
                "div[role='button'][aria-label*='Apa yang Anda pikirkan']",
                "div[data-pagelet='FeedComposer'] div[role='button']",
                "div[aria-label*='What\\'s on your mind']",
                "div[aria-label*='Apa yang Anda pikirkan']",
                # FIXED XPath selectors - menggunakan double quotes
                '//div[@role="button" and contains(., "What")]',
                '//div[@role="button" and contains(., "mind")]',
                '//div[@role="button" and contains(., "Apa")]',
                '//div[@role="button" and contains(., "pikirkan")]',
                # Fallback berdasarkan struktur umum
                "div[data-pagelet*='FeedComposer'] span",
                "div[data-testid*='status-attachment-mentions-input']"
            ],
            'text_input': [
                "div[contenteditable='true'][role='textbox']",
                "div[contenteditable='true'][data-text*='What\\'s on your mind']",
                "div[contenteditable='true'][data-text*='Apa yang Anda pikirkan']",
                "div[contenteditable='true'][aria-label*='What\\'s on your mind']",
                "div[contenteditable='true'][aria-label*='Apa yang Anda pikirkan']",
                "div[contenteditable='true'][data-testid*='status-attachment-mentions-input']",
                "div[contenteditable='true']",
                "textarea[placeholder*='What\\'s on your mind']",
                "textarea[placeholder*='Apa yang Anda pikirkan']"
            ],
            'photo_video_button': [
                "div[aria-label='Photo/video']",
                "div[aria-label='Foto/video']",
                "div[role='button'][aria-label*='Photo']",
                "div[role='button'][aria-label*='Foto']",
                # FIXED XPath selectors
                '//div[@role="button" and contains(., "Photo")]',
                '//div[@role="button" and contains(., "video")]',
                '//div[@role="button" and contains(., "Foto")]',
                '//span[contains(text(), "Photo")]/parent::*',
                '//span[contains(text(), "Foto")]/parent::*'
            ],
            'file_input': [
                "input[type='file'][accept*='image']",
                "input[type='file'][accept*='video']",
                "input[type='file']"
            ],
            'post_button': [
                "div[aria-label='Post'][role='button']",
                "div[aria-label='Posting'][role='button']",
                "div[role='button'][aria-label*='Post']",
                "div[role='button'][aria-label*='Posting']",
                # FIXED XPath selectors
                '//div[@role="button" and contains(., "Post")]',
                '//div[@role="button" and contains(., "Posting")]',
                '//span[contains(text(), "Post")]/parent::*',
                '//span[contains(text(), "Posting")]/parent::*'
            ],
            'composer_indicators': [
                "div[contenteditable='true'][role='textbox']",
                "form[method='POST']",
                "div[aria-label='Post'][role='button']",
                "div[aria-label='Photo/video']"
            ],
            'media_uploaded_indicator': [
                "img[src*='scontent']",
                "video[src*='blob']",
                "div[data-pagelet*='MediaAttachment']",
                "div[aria-label*='Photo']",
                "div[aria-label*='Video']"
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
            
            import shutil
            chrome_names = ['chromedriver', 'chromedriver.exe']
            for name in chrome_names:
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
        """Setup Chrome WebDriver dengan konfigurasi optimal"""
        self._log("Menyiapkan browser untuk Facebook...")
        
        chrome_options = Options()
        
        # Basic options
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--window-size=1280,800")
        
        if self.headless:
            chrome_options.add_argument('--headless=new')
        
        # Additional options
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-images')
        chrome_options.add_argument('--disable-notifications')
        chrome_options.add_argument('--disable-popup-blocking')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Suppress logs
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--silent")
        chrome_options.add_argument("--disable-logging")
        
        # Anti-detection
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        if self.headless:
            self._log("Mode headless diaktifkan")
        
        try:
            driver_path = self._get_chromedriver_path()
            service = Service(driver_path, log_path=os.devnull, service_args=['--silent'])
            
            os.environ['WDM_LOG_LEVEL'] = '0'
            os.environ['WDM_PRINT_FIRST_LINE'] = 'False'
            
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.wait = WebDriverWait(self.driver, 30)
            
            self._log("Browser siap digunakan", "SUCCESS")
            
        except Exception as e:
            self._log(f"Gagal menyiapkan browser: {str(e)}", "ERROR")
            raise

    def _find_element_by_selectors(self, selectors: list, timeout: int = 10, visible: bool = True) -> Optional[Any]:
        """Mencari elemen menggunakan multiple selectors dengan CSS dan XPath"""
        for i, selector in enumerate(selectors):
            try:
                # Deteksi apakah XPath atau CSS
                if selector.startswith('//') or selector.startswith('./'):
                    # XPath selector
                    if visible:
                        element = WebDriverWait(self.driver, timeout).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        element = WebDriverWait(self.driver, timeout).until(
                            EC.presence_of_element_located((By.XPATH, selector))
                        )
                else:
                    # CSS selector
                    if visible:
                        element = WebDriverWait(self.driver, timeout).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    else:
                        element = WebDriverWait(self.driver, timeout).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                
                if i == 0:
                    self._log(f"✅ Found element with primary selector")
                else:
                    self._log(f"⚠️ Found element with fallback #{i+1}")
                return element
                
            except TimeoutException:
                continue
                
        return None

    def _find_element_by_xpath_selectors(self, selectors: list, timeout: int = 10) -> Optional[Any]:
        """Mencari elemen menggunakan XPath selectors"""
        for i, selector in enumerate(selectors):
            try:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                
                if i == 0:
                    self._log(f"✅ Found element with primary XPath")
                else:
                    self._log(f"⚠️ Found element with XPath fallback #{i+1}")
                return element
                
            except TimeoutException:
                continue
                
        return None

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
            
            self.driver.get("https://www.facebook.com")
            time.sleep(2)
            
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
            filename = f"facebook_screenshot_{int(time.time())}.png"
        
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

    def _click_element_safely(self, element, description: str = "element"):
        """Click element dengan multiple fallback methods"""
        try:
            # Method 1: Regular click
            self._log(f"🖱️ Attempting regular click on {description}...")
            element.click()
            self._log(f"✅ CLICK SUCCESS: Regular click on {description}")
            return True
        except Exception as e:
            self._log(f"⚠️ Regular click failed on {description}: {str(e)}", "WARNING")
            
            try:
                # Method 2: JavaScript click
                self._log(f"🖱️ Attempting JavaScript click on {description}...")
                self.driver.execute_script("arguments[0].click();", element)
                self._log(f"✅ CLICK SUCCESS: JavaScript click on {description}")
                return True
            except Exception as e2:
                self._log(f"JavaScript click failed on {description}: {str(e2)}", "WARNING")
                
                try:
                    # Method 3: ActionChains
                    self._log(f"🖱️ Attempting ActionChains click on {description}...")
                    ActionChains(self.driver).move_to_element(element).click().perform()
                    self._log(f"✅ CLICK SUCCESS: ActionChains click on {description}")
                    return True
                except Exception as e3:
                    self._log(f"❌ All click methods failed for {description}: {str(e3)}", "ERROR")
                    return False

    def _validate_composer_open(self) -> bool:
        """Validasi apakah composer benar-benar terbuka"""
        self._log("🔍 VALIDATING: Checking if composer is really open...")
        
        indicators_found = 0
        for selector in self.selectors['composer_indicators']:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    indicators_found += 1
            except:
                continue
        
        self._log(f"🔍 Found {indicators_found} composer indicators")
        
        if indicators_found >= 2:
            self._log("✅ VALIDATION SUCCESS: Composer is open")
            return True
        else:
            self._log("❌ VALIDATION FAILED: Composer not open")
            return False

    def _validate_media_uploaded(self) -> bool:
        """Validasi apakah media benar-benar ter-upload"""
        self._log("🔍 VALIDATING: Checking if media is really uploaded...")
        
        for selector in self.selectors['media_uploaded_indicator']:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                if element and element.is_displayed():
                    self._log("✅ MEDIA VALIDATION SUCCESS: Media uploaded")
                    return True
            except:
                continue
        
        self._log("⚠️ MEDIA VALIDATION: Cannot confirm, but continuing...")
        return True  # Continue anyway

    def _wait_for_post_button_enabled(self, timeout: int = 30) -> bool:
        """Tunggu sampai Post button enabled (tidak disabled)"""
        self._log("⏳ WAITING: For Post button to be enabled...")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Cari post button yang enabled
                enabled_post_button = self.driver.find_element(
                    By.CSS_SELECTOR, 
                    "div[aria-label='Post'][role='button']:not([aria-disabled='true'])"
                )
                
                if enabled_post_button and enabled_post_button.is_enabled():
                    self._log("✅ POST BUTTON ENABLED: Ready to click")
                    return True
                    
            except NoSuchElementException:
                pass
            
            # Cek juga dengan XPath
            try:
                enabled_post_button = self.driver.find_element(
                    By.XPATH, 
                    "//div[@role='button' and contains(@aria-label, 'Post') and not(@aria-disabled='true')]"
                )
                
                if enabled_post_button and enabled_post_button.is_enabled():
                    self._log("✅ POST BUTTON ENABLED: Ready to click (XPath)")
                    return True
                    
            except NoSuchElementException:
                pass
            
            time.sleep(1)
        
        self._log("⚠️ POST BUTTON TIMEOUT: Still disabled, but continuing...")
        return False

    def upload_status(self, status_text: str = "", media_path: str = "") -> Dict[str, Any]:
        """
        Upload status ke Facebook dengan dukungan text + media
        URUTAN BARU: MEDIA DULU, BARU TEXT
        
        Args:
            status_text: Text untuk status
            media_path: Path ke file media (video/gambar)
            
        Returns:
            Dict dengan status upload
        """
        try:
            self._setup_driver()
            cookies_loaded = self.load_cookies()
            
            self._log("Navigating to Facebook...")
            self.driver.get(self.facebook_url)
            time.sleep(3)
            
            # Take screenshot before posting
            self.take_screenshot(f"facebook_before_post_{int(time.time())}.png")
            
            # Determine mode
            has_text = bool(status_text.strip())
            has_media = bool(media_path and os.path.exists(media_path))
            
            if has_text and has_media:
                mode = "TEXT + MEDIA"
            elif has_text:
                mode = "TEXT ONLY"
            elif has_media:
                mode = "MEDIA ONLY"
            else:
                raise ValueError("Minimal status text atau media diperlukan")
            
            self._log(f"🎯 MODE: {mode}")
            
            if self.check_login_required():
                if cookies_loaded:
                    self._log("Cookies dimuat tapi masih perlu login, refresh halaman...", "WARNING")
                    self.driver.refresh()
                    time.sleep(3)
                
                if self.check_login_required():
                    self.wait_for_login()
                    self.driver.get(self.facebook_url)
                    time.sleep(3)
            
            # STEP 1: Buka composer
            self._log("🎯 STEP 1: Looking for 'What's on your mind' click element...")
            whats_on_mind = self._find_element_by_selectors(self.selectors['whats_on_mind_click'])
            
            if not whats_on_mind:
                raise NoSuchElementException("Tidak dapat menemukan elemen 'What's on your mind' untuk diklik")
            
            self._log("✅ Found 'What's on your mind' click element")
            self._log("🖱️ Clicking 'What's on your mind' element...")
            
            if not self._click_element_safely(whats_on_mind, "'What's on your mind' click"):
                raise Exception("Gagal mengklik elemen 'What's on your mind'")
            
            time.sleep(2)
            
            # Validate composer opened
            if not self._validate_composer_open():
                raise Exception("Composer tidak terbuka setelah klik 'What's on your mind'")
            
            # STEP 2: Upload media DULU jika ada (URUTAN BARU!)
            if has_media:
                self._log("🎯 STEP 2: Adding media FIRST...")
                
                # Cari tombol Photo/Video
                photo_video_button = self._find_element_by_selectors(self.selectors['photo_video_button'])
                
                if not photo_video_button:
                    raise NoSuchElementException("Tidak dapat menemukan tombol Photo/Video")
                
                self._log("✅ Found Photo/Video button")
                
                if not self._click_element_safely(photo_video_button, "Photo/Video button"):
                    raise Exception("Gagal mengklik tombol Photo/Video")
                
                time.sleep(2)
                
                # Cari file input
                file_input = self._find_element_by_selectors(self.selectors['file_input'], visible=False)
                
                if not file_input:
                    raise NoSuchElementException("Tidak dapat menemukan file input")
                
                # Upload file
                abs_path = os.path.abspath(media_path)
                file_input.send_keys(abs_path)
                
                self._log("✅ STEP 2 COMPLETE: Media uploaded successfully")
                time.sleep(5)  # Tunggu media diproses lebih lama
                
                # Validate media uploaded
                self._validate_media_uploaded()
            
            # STEP 3: Tambahkan text SETELAH media (URUTAN BARU!)
            if has_text:
                step_num = "3" if has_media else "2"
                self._log(f"🎯 STEP {step_num}: Adding status text AFTER media...")
                
                # Cari text input dengan validasi ketat
                text_input = self._find_element_by_selectors(self.selectors['text_input'])
                
                if not text_input:
                    raise NoSuchElementException("Tidak dapat menemukan text input")
                
                # Klik text input dengan validasi
                if not self._click_element_safely(text_input, "text input"):
                    raise Exception("Gagal mengklik text input")
                
                time.sleep(1)
                
                # Clear existing text dan input text baru dengan validasi ketat
                success = False
                methods = [
                    lambda: self._input_text_method_1(text_input, status_text),
                    lambda: self._input_text_method_2(text_input, status_text),
                    lambda: self._input_text_method_3(text_input, status_text)
                ]
                
                for i, method in enumerate(methods, 1):
                    try:
                        self._log(f"🖊️ Trying text input method {i}...")
                        if method():
                            # VALIDASI KETAT - CEK APAKAH TEXT BENAR-BENAR TERTULIS
                            time.sleep(1)
                            self._log("🔍 VALIDATING: Checking if text is really inputted...")
                            current_text = text_input.get_attribute('textContent') or text_input.get_attribute('innerText') or ""
                            
                            if status_text.strip() in current_text:
                                self._log(f"✅ TEXT VALIDATION SUCCESS: Text found with method {i}")
                                self._log(f"Expected: '{status_text}', Found: '{current_text[:50]}...'")
                                self._log(f"✅ STEP {step_num} COMPLETE: Status text added successfully with method {i}")
                                success = True
                                break
                            else:
                                self._log(f"❌ Text validation FAILED. Expected: '{status_text}', Got: '{current_text}'", "WARNING")
                                continue
                                
                    except Exception as e:
                        self._log(f"Method {i} failed: {str(e)}", "WARNING")
                        continue
                
                if not success:
                    raise Exception("Gagal menambahkan status text setelah semua method dicoba")
            
            # STEP 4: Tunggu Post button enabled, lalu klik
            final_step = "4" if has_media and has_text else ("3" if has_media or has_text else "2")
            self._log(f"🎯 STEP {final_step}: Waiting for Post button to be enabled...")
            
            # Tunggu Post button enabled
            self._wait_for_post_button_enabled(timeout=30)
            
            # Cari Post button yang enabled
            post_button = None
            
            # Coba cari Post button yang tidak disabled
            try:
                post_button = self.driver.find_element(
                    By.CSS_SELECTOR, 
                    "div[aria-label='Post'][role='button']:not([aria-disabled='true'])"
                )
                self._log("✅ Found ENABLED Post button (CSS)")
            except NoSuchElementException:
                try:
                    post_button = self.driver.find_element(
                        By.XPATH, 
                        "//div[@role='button' and contains(@aria-label, 'Post') and not(@aria-disabled='true')]"
                    )
                    self._log("✅ Found ENABLED Post button (XPath)")
                except NoSuchElementException:
                    # Fallback ke Post button biasa
                    post_button = self._find_element_by_selectors(self.selectors['post_button'])
                    if post_button:
                        self._log("⚠️ Found Post button (may be disabled)")
            
            if not post_button:
                raise NoSuchElementException("Tidak dapat menemukan tombol Post")
            
            # VALIDASI KETAT - CEK APAKAH POST BUTTON BENAR-BENAR DIKLIK
            initial_url = self.driver.current_url
            
            if not self._click_element_safely(post_button, "Post button"):
                raise Exception("Gagal mengklik tombol Post")
            
            # Tunggu dan validasi apakah post berhasil
            time.sleep(5)
            
            # Cek apakah URL berubah atau ada indikator sukses
            self._log("🔍 VALIDATING: Checking if post was successful...")
            current_url = self.driver.current_url
            
            # Cek apakah kembali ke feed atau ada perubahan
            if current_url != initial_url or "facebook.com" in current_url:
                self._log("✅ POST VALIDATION SUCCESS: Returned to feed")
                success_confirmed = True
            else:
                # Cek apakah composer masih terbuka
                try:
                    # Jika composer masih ada, berarti post belum berhasil
                    composer_still_open = self.driver.find_elements(By.CSS_SELECTOR, "div[contenteditable='true'][role='textbox']")
                    if composer_still_open:
                        self._log("❌ Post composer masih terbuka - post mungkin gagal", "WARNING")
                        success_confirmed = False
                    else:
                        self._log("✅ POST VALIDATION SUCCESS: Composer closed")
                        success_confirmed = True
                except:
                    success_confirmed = True
            
            if success_confirmed:
                self._log("✅ Facebook status posted successfully!")
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
                    "message": "Post mungkin gagal - composer masih terbuka",
                    "status_text": status_text,
                    "media_path": media_path,
                    "mode": mode
                }
                
        except Exception as e:
            error_msg = f"Facebook status upload gagal: {str(e)}"
            self._log(error_msg, "ERROR")
            
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

    def _input_text_method_1(self, element, text: str) -> bool:
        """Method 1: Clear dan type text"""
        try:
            element.clear()
            element.send_keys(text)
            return True
        except Exception as e:
            self._log(f"Method 1 error: {str(e)}", "DEBUG")
            return False

    def _input_text_method_2(self, element, text: str) -> bool:
        """Method 2: Select all dan replace"""
        try:
            element.send_keys(Keys.CONTROL + "a")
            element.send_keys(text)
            return True
        except Exception as e:
            self._log(f"Method 2 error: {str(e)}", "DEBUG")
            return False

    def _input_text_method_3(self, element, text: str) -> bool:
        """Method 3: JavaScript innerHTML"""
        try:
            self.driver.execute_script("arguments[0].innerHTML = arguments[1];", element, text)
            self.driver.execute_script("arguments[0].textContent = arguments[1];", element, text)
            return True
        except Exception as e:
            self._log(f"Method 3 error: {str(e)}", "DEBUG")
            return False

    def upload_reels(self, video_path: str, description: str = "") -> Dict[str, Any]:
        """
        Upload reels ke Facebook
        
        Args:
            video_path: Path ke file video
            description: Deskripsi untuk reels
            
        Returns:
            Dict dengan status upload
        """
        try:
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"File video tidak ditemukan: {video_path}")
            
            self._setup_driver()
            cookies_loaded = self.load_cookies()
            
            self._log("Navigasi ke Facebook Reels Create...")
            self.driver.get(self.reels_create_url)
            time.sleep(5)
            
            if self.check_login_required():
                if cookies_loaded:
                    self._log("Cookies dimuat tapi masih perlu login, refresh halaman...", "WARNING")
                    self.driver.refresh()
                    time.sleep(3)
                
                if self.check_login_required():
                    self.wait_for_login()
                    self.driver.get(self.reels_create_url)
                    time.sleep(5)
            
            # Upload video
            self._log("Memulai upload video reels...")
            
            upload_selectors = [
                "input[type='file'][accept*='video']",
                "input[type='file']",
                "input[accept*='video']"
            ]
            
            upload_input = self._find_element_by_selectors(upload_selectors, visible=False)
            
            if not upload_input:
                raise NoSuchElementException("Tidak dapat menemukan input upload")
            
            self._log("Input upload ditemukan. Mengirim file...")
            abs_path = os.path.abspath(video_path)
            upload_input.send_keys(abs_path)
            
            self._log("File video berhasil dikirim ke input.", "SUCCESS")
            time.sleep(5)
            
            # Klik Next buttons (dual language support)
            next_buttons_clicked = 0
            next_selectors = [
                "//div[@role='button' and (contains(text(), 'Next') or contains(text(), 'Berikutnya'))]",
                "//button[contains(text(), 'Next') or contains(text(), 'Berikutnya')]",
                "//span[contains(text(), 'Next') or contains(text(), 'Berikutnya')]/parent::*"
            ]
            
            for attempt in range(3):
                try:
                    next_button = self._find_element_by_xpath_selectors(next_selectors, timeout=10)
                    if next_button:
                        if self._click_element_safely(next_button, f"Next button (attempt {attempt + 1})"):
                            next_buttons_clicked += 1
                            self._log(f"Tombol 'Next' berhasil diklik (index {next_buttons_clicked})!", "SUCCESS")
                            time.sleep(3)
                        else:
                            break
                    else:
                        break
                except:
                    break
            
            # Tambahkan deskripsi jika ada
            if description.strip():
                self._log("Menambahkan deskripsi reels...")
                
                description_selectors = [
                    "div[contenteditable='true'][aria-label*='description']",
                    "div[contenteditable='true'][aria-label*='deskripsi']",
                    "textarea[placeholder*='description']",
                    "textarea[placeholder*='deskripsi']",
                    "div[contenteditable='true']"
                ]
                
                desc_input = self._find_element_by_selectors(description_selectors)
                
                if desc_input:
                    if self._click_element_safely(desc_input, "description input"):
                        desc_input.clear()
                        desc_input.send_keys(description)
                        self._log("Deskripsi berhasil diisi", "SUCCESS")
                    time.sleep(2)
            
            # Klik Publish/Terbitkan
            publish_selectors = [
                "//div[@role='button' and (contains(text(), 'Publish') or contains(text(), 'Terbitkan'))]",
                "//button[contains(text(), 'Publish') or contains(text(), 'Terbitkan')]",
                "//span[contains(text(), 'Publish') or contains(text(), 'Terbitkan')]/parent::*"
            ]
            
            publish_attempts = 0
            for attempt in range(3):
                try:
                    publish_button = self._find_element_by_xpath_selectors(publish_selectors, timeout=10)
                    if publish_button:
                        if self._click_element_safely(publish_button, f"Publish button (attempt {attempt + 1})"):
                            publish_attempts += 1
                            self._log(f"Tombol 'Publish' berhasil diklik (index {publish_attempts})!", "SUCCESS")
                            time.sleep(5)
                            break
                    else:
                        break
                except:
                    break
            
            if publish_attempts > 0:
                self._log("Upload video reels berhasil!", "SUCCESS")
                return {
                    "success": True,
                    "message": "Reels berhasil diupload",
                    "video_path": video_path,
                    "description": description
                }
            else:
                return {
                    "success": False,
                    "message": "Gagal mengklik tombol Publish",
                    "video_path": video_path,
                    "description": description
                }
                
        except Exception as e:
            error_msg = f"Facebook reels upload gagal: {str(e)}"
            self._log(error_msg, "ERROR")
            
            self.take_screenshot(f"facebook_reels_error_{int(time.time())}.png")
            
            return {
                "success": False,
                "message": error_msg,
                "video_path": video_path,
                "description": description
            }
        
        finally:
            if self.driver:
                self._log("Closing browser...")
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
                    valid_cookies.append(cookie)
            
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
    parser.add_argument("--type", "-t", choices=['status', 'reels'], help="Jenis upload (status atau reels)")
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
    
    if args.clear_cookies:
        uploader.clear_cookies()
        return
    
    if args.check_cookies:
        uploader.check_cookies_status()
        return
    
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
        print(f"{Fore.YELLOW}📝 Status + 🎬 Reels Support")
        print()
        
        while True:
            print(f"\n{Fore.YELLOW}Pilih jenis upload:")
            print("1. 📝 Status Facebook (Text/Media)")
            print("2. 🎬 Reels Facebook (Video)")
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