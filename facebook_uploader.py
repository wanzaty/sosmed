#!/usr/bin/env python3
"""
Facebook Uploader (Status & Reels) menggunakan Selenium
Dengan dukungan cookies JSON untuk auto-login dan selector yang dioptimasi
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
        
        # Selectors yang diperbarui untuk Facebook
        self.selectors = {
            # Status selectors - UPDATED dengan lebih banyak fallback
            'status_click_triggers': [
                # Primary selectors
                "[data-pagelet='FeedComposer'] [role='button'][aria-label*='mind']",
                "[data-pagelet='FeedComposer'] [role='button'][aria-label*='thinking']",
                "[data-pagelet='FeedComposer'] [role='button'][aria-label*='share']",
                
                # Fallback selectors
                "div[role='button'][aria-label*='mind']",
                "div[role='button'][aria-label*='thinking']",
                "div[role='button'][aria-label*='share']",
                
                # Text-based selectors
                "div[role='button']:has-text('What\\'s on your mind')",
                "div[role='button']:has-text('What are you thinking')",
                
                # Generic composer triggers
                "[data-testid='status-attachment-mentions-input']",
                "[data-testid='composer-input']",
                "div[contenteditable='true'][role='textbox']",
                
                # More generic fallbacks
                "div[role='button'][tabindex='0']:contains('mind')",
                "div[role='button'][tabindex='0']:contains('thinking')",
                "div[aria-label*='Create a post']",
                "div[aria-label*='Write a post']",
                
                # Last resort
                "div[role='button'][data-testid*='composer']",
                "div[role='button'][data-testid*='status']"
            ],
            
            'composer_indicators': [
                # Primary indicators
                "form[method='POST'] div[contenteditable='true']",
                "div[data-testid='composer-input']",
                "div[role='textbox'][contenteditable='true']",
                
                # Secondary indicators
                "div[aria-label*='What\\'s on your mind']",
                "div[aria-label*='Write something']",
                "textarea[placeholder*='mind']",
                
                # Generic indicators
                "div[contenteditable='true'][data-testid]",
                "div[contenteditable='true'][aria-multiline='true']",
                "form div[contenteditable='true']"
            ],
            
            'status_input': [
                # Primary input selectors
                "div[data-testid='composer-input'] div[contenteditable='true']",
                "form[method='POST'] div[contenteditable='true'][role='textbox']",
                "div[role='textbox'][contenteditable='true'][aria-multiline='true']",
                
                # Fallback input selectors
                "div[contenteditable='true'][data-testid]",
                "div[contenteditable='true'][aria-label*='mind']",
                "div[contenteditable='true'][aria-label*='thinking']",
                "div[contenteditable='true'][aria-label*='Write']",
                
                # Generic fallbacks
                "div[contenteditable='true'][role='textbox']",
                "div[contenteditable='true'][tabindex='0']",
                "textarea[placeholder*='mind']"
            ],
            
            'media_upload_input': [
                "input[type='file'][accept*='image']",
                "input[type='file'][accept*='video']",
                "input[type='file'][multiple]",
                "input[type='file'][data-testid*='composer']",
                "input[type='file'][data-testid*='photo']"
            ],
            
            'post_button': [
                # Primary post buttons
                "div[aria-label='Post'][role='button']",
                "div[aria-label='Share'][role='button']",
                "button[data-testid='react-composer-post-button']",
                
                # Fallback post buttons
                "div[role='button']:has-text('Post')",
                "div[role='button']:has-text('Share')",
                "button:has-text('Post')",
                "button:has-text('Share')",
                
                # Generic post buttons
                "div[role='button'][tabindex='0']:contains('Post')",
                "div[role='button'][tabindex='0']:contains('Share')",
                "button[type='submit']"
            ],
            
            # Reels selectors
            'reels_upload_input': [
                "input[type='file'][accept*='video']",
                "input[type='file'][data-testid*='reels']",
                "input[type='file'][multiple]"
            ],
            
            'reels_next_buttons': [
                # English
                "div[role='button']:has-text('Next')",
                "button:has-text('Next')",
                "div[aria-label='Next']",
                
                # Indonesian
                "div[role='button']:has-text('Berikutnya')",
                "button:has-text('Berikutnya')",
                "div[aria-label='Berikutnya']"
            ],
            
            'reels_description_input': [
                "div[contenteditable='true'][aria-label*='description']",
                "div[contenteditable='true'][aria-label*='deskripsi']",
                "textarea[placeholder*='description']",
                "div[contenteditable='true'][role='textbox']"
            ],
            
            'reels_publish_buttons': [
                # English
                "div[role='button']:has-text('Publish')",
                "button:has-text('Publish')",
                "div[aria-label='Publish']",
                
                # Indonesian
                "div[role='button']:has-text('Terbitkan')",
                "button:has-text('Terbitkan')",
                "div[aria-label='Terbitkan']"
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
        """Setup Chrome WebDriver dengan konfigurasi optimal"""
        self._log("Menyiapkan browser untuk Facebook...")
        
        chrome_options = Options()
        
        # Basic options
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--window-size=1280,800")
        
        # Additional Chrome options
        if self.headless:
            chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-images')
        chrome_options.add_argument('--blink-settings=imagesEnabled=false')
        chrome_options.add_argument('--disable-plugins-discovery')
        chrome_options.add_argument('--disable-translate')
        chrome_options.add_argument('--disable-popup-blocking')
        chrome_options.add_argument('--disable-notifications')
        chrome_options.add_argument('--disable-geolocation')
        chrome_options.add_argument('--disable-media-stream')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Suppress logs
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--silent")
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument("--disable-gpu-logging")
        
        # Anti-detection options
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--disable-web-security")
        
        if self.headless:
            self._log("Mode headless diaktifkan")
        
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

    def _find_element_by_selectors(self, selectors: list, timeout: int = 10, visible: bool = True) -> Optional[Any]:
        """Mencari elemen menggunakan multiple selectors dengan improved logic"""
        for i, selector in enumerate(selectors):
            try:
                if visible:
                    element = WebDriverWait(self.driver, timeout).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                else:
                    element = WebDriverWait(self.driver, timeout).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                
                if i == 0:
                    self._log("✅ ✅ ℹ️ ✅ Found element with primary selector", "SUCCESS")
                else:
                    self._log(f"⚠️ ⚠️ ⚠️ ⚠️ Exact selector not found, using fallback #{i}", "WARNING")
                return element
                
            except TimeoutException:
                if i == 0:
                    self._log("⚠️ ⚠️ ⚠️ ⚠️ Exact selector not found, trying fallbacks...", "WARNING")
                continue
                
        return None

    def _click_element_with_retry(self, element, description: str = "element") -> bool:
        """Click element dengan multiple strategies dan retry"""
        self._log(f"ℹ️ ℹ️ ℹ️ 🖱️ Clicking '{description}' element...")
        
        strategies = [
            ("regular", lambda e: e.click()),
            ("javascript", lambda e: self.driver.execute_script("arguments[0].click();", e)),
            ("action_chains", lambda e: ActionChains(self.driver).move_to_element(e).click().perform()),
            ("send_enter", lambda e: e.send_keys(Keys.ENTER)),
            ("send_space", lambda e: e.send_keys(Keys.SPACE))
        ]
        
        for strategy_name, strategy_func in strategies:
            try:
                self._log(f"ℹ️ 🖱️ Attempting {strategy_name} click on '{description}' click...")
                strategy_func(element)
                self._log(f"✅ ✅ ✅ ✅ CLICK SUCCESS: {strategy_name.title()} click on '{description}' click", "SUCCESS")
                time.sleep(2)  # Wait for action to take effect
                return True
                
            except Exception as e:
                self._log(f"❌ {strategy_name.title()} click failed: {str(e)}", "DEBUG")
                continue
        
        self._log(f"❌ ❌ ❌ All click strategies failed for '{description}'", "ERROR")
        return False

    def _validate_composer_open(self) -> bool:
        """Validate apakah composer benar-benar terbuka"""
        self._log("ℹ️ 🔍 🔍 VALIDATING: Checking if composer is really open...")
        
        indicators_found = 0
        for selector in self.selectors['composer_indicators']:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            indicators_found += 1
                            break
            except:
                continue
        
        self._log(f"ℹ️ 🔍 Found {indicators_found} composer indicators")
        
        if indicators_found >= 1:
            self._log("✅ ✅ ✅ ✅ VALIDATION SUCCESS: Composer is open!", "SUCCESS")
            return True
        else:
            self._log("❌ ❌ ❌ ❌ VALIDATION FAILED: Composer not open ({} indicators found)".format(indicators_found), "ERROR")
            return False

    def _open_composer_with_strategies(self) -> bool:
        """Buka composer dengan multiple strategies"""
        
        # Strategy 1: Click "What's on your mind" trigger
        self._log("ℹ️ 🎯 🎯 STEP 1: Looking for 'What's on your mind' click element...")
        click_element = self._find_element_by_selectors(self.selectors['status_click_triggers'], timeout=10)
        
        if click_element:
            if self._click_element_with_retry(click_element, "What's on your mind"):
                if self._validate_composer_open():
                    return True
        
        self._log("⚠️ ⚠️ ⚠️ Composer not opened after click, trying alternative strategies...", "WARNING")
        
        # Strategy 2: Look for composer directly
        self._log("ℹ️ 🎯 🎯 STRATEGY 2: Looking for composer directly...")
        composer_input = self._find_element_by_selectors(self.selectors['status_input'], timeout=5)
        if composer_input:
            try:
                composer_input.click()
                if self._validate_composer_open():
                    return True
            except:
                pass
        
        # Strategy 3: Try keyboard shortcut
        self._log("ℹ️ 🎯 🎯 STRATEGY 3: Trying keyboard shortcut...")
        try:
            ActionChains(self.driver).send_keys(Keys.TAB).send_keys(Keys.ENTER).perform()
            time.sleep(2)
            if self._validate_composer_open():
                return True
        except:
            pass
        
        # Strategy 4: Try direct URL navigation to force composer
        self._log("ℹ️ 🎯 🎯 STRATEGY 4: Trying direct URL navigation...")
        try:
            self.driver.get(f"{self.base_url}/?sk=h_chr")  # Home with composer focus
            time.sleep(3)
            if self._validate_composer_open():
                return True
        except:
            pass
        
        # Strategy 5: Try scrolling and looking again
        self._log("ℹ️ 🎯 🎯 STRATEGY 5: Scrolling and looking for composer...")
        try:
            self.driver.execute_script("window.scrollTo(0, 0);")  # Scroll to top
            time.sleep(2)
            
            # Try clicking again after scroll
            click_element = self._find_element_by_selectors(self.selectors['status_click_triggers'], timeout=5)
            if click_element:
                if self._click_element_with_retry(click_element, "What's on your mind (after scroll)"):
                    if self._validate_composer_open():
                        return True
        except:
            pass
        
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
        Upload status ke Facebook dengan dukungan media
        
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
            time.sleep(3)
            
            # Take screenshot before starting
            self.take_screenshot(f"facebook_before_post_{int(time.time())}.png")
            
            # Cek apakah perlu login
            if self.check_login_required():
                if cookies_loaded:
                    self._log("Cookies dimuat tapi masih perlu login, refresh halaman...", "WARNING")
                    self.driver.refresh()
                    time.sleep(3)
                
                if self.check_login_required():
                    self.wait_for_login()
                    self.driver.get(self.base_url)
                    time.sleep(3)
            
            # Determine mode
            if status_text and media_path:
                mode = "TEXT + MEDIA"
            elif media_path:
                mode = "MEDIA ONLY"
            elif status_text:
                mode = "TEXT ONLY"
            else:
                raise ValueError("Minimal status text atau media diperlukan")
            
            self._log(f"🎯 🎯 MODE: {mode}")
            
            # Open composer dengan improved strategies
            if not self._open_composer_with_strategies():
                raise Exception("Composer tidak terbuka setelah semua strategi dicoba")
            
            # Input status text jika ada
            if status_text:
                self._log(f"Memposting status: {status_text[:50]}...")
                
                status_input = self._find_element_by_selectors(self.selectors['status_input'])
                if not status_input:
                    raise NoSuchElementException("Input status tidak ditemukan")
                
                # Clear dan input text
                status_input.clear()
                status_input.send_keys(status_text)
                self._log("Status text berhasil dimasukkan", "SUCCESS")
                time.sleep(1)
            
            # Upload media jika ada
            if media_path and os.path.exists(media_path):
                self._log(f"Mengupload media: {os.path.basename(media_path)}")
                
                media_input = self._find_element_by_selectors(self.selectors['media_upload_input'])
                if not media_input:
                    raise NoSuchElementException("Input media tidak ditemukan")
                
                abs_path = os.path.abspath(media_path)
                media_input.send_keys(abs_path)
                self._log("Media berhasil diupload", "SUCCESS")
                time.sleep(3)  # Wait for media processing
            
            # Post status
            self._log("Mencari tombol post...")
            post_button = self._find_element_by_selectors(self.selectors['post_button'])
            
            if not post_button:
                raise NoSuchElementException("Tombol post tidak ditemukan")
            
            if self._click_element_with_retry(post_button, "Post"):
                self._log("Post berhasil (kembali ke feed)", "SUCCESS")
                time.sleep(5)
                
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
                raise Exception("Gagal mengklik tombol post")
                
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
            upload_input = self._find_element_by_selectors(self.selectors['reels_upload_input'])
            if not upload_input:
                raise NoSuchElementException("Input upload reels tidak ditemukan")
            
            self._log("Input upload ditemukan. Mengirim file...")
            abs_path = os.path.abspath(video_path)
            upload_input.send_keys(abs_path)
            self._log("File video berhasil dikirim ke input.", "SUCCESS")
            
            # Wait for upload processing
            time.sleep(5)
            
            # Click Next buttons (bisa ada beberapa step)
            for i in range(1, 4):  # Max 3 next buttons
                try:
                    next_button = self._find_element_by_selectors(self.selectors['reels_next_buttons'], timeout=10)
                    if next_button:
                        next_button.click()
                        self._log(f"Tombol 'Next' berhasil diklik (index {i})!", "SUCCESS")
                        time.sleep(3)
                    else:
                        break
                except:
                    break
            
            # Add description jika ada
            if description:
                self._log("Mengisi deskripsi reels...")
                desc_input = self._find_element_by_selectors(self.selectors['reels_description_input'])
                if desc_input:
                    desc_input.clear()
                    desc_input.send_keys(description)
                    self._log("Deskripsi berhasil diisi", "SUCCESS")
                    time.sleep(1)
            
            # Publish reels
            self._log("Mencari tombol publish...")
            publish_button = self._find_element_by_selectors(self.selectors['reels_publish_buttons'])
            
            if not publish_button:
                raise NoSuchElementException("Tombol publish tidak ditemukan")
            
            publish_button.click()
            self._log("Tombol 'Publish' berhasil diklik!", "SUCCESS")
            time.sleep(5)
            
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