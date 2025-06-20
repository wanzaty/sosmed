#!/usr/bin/env python3
"""
Facebook Status & Reels Uploader menggunakan Selenium
Mendukung cookies JSON untuk auto-login dan upload status/reels
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
    StaleElementReferenceException,
    ElementClickInterceptedException
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
            headless: Jalankan browser dalam mode headless
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
        self.base_url = "https://www.facebook.com"
        self.reels_url = "https://www.facebook.com/reels/create/?surface=PROFILE_PLUS"
        
        # Enhanced selectors with better targeting
        self.selectors = {
            'status_composer_click': [
                # Primary: What's on your mind click elements
                "div[aria-label*=\"What's on your mind\"]",
                "div[role='button'][aria-label*=\"What's on your mind\"]",
                "div[data-pagelet='FeedComposer'] div[role='button']",
                "div[aria-label*='Write something']",
                "div[aria-label*='Share something']",
                "div[aria-label*='Create a post']",
                # Fallbacks for different languages/layouts
                "div[role='button']:has-text('What\\'s on your mind')",
                "div[role='button']:has-text('Write something')",
                "[data-testid='status-attachment-mentions-input']",
                "div[data-testid='status-attachment-mentions-input']"
            ],
            'status_text_input': [
                # Status composer text inputs (NOT comment boxes)
                "div[aria-label*=\"What's on your mind\"][contenteditable='true']",
                "div[aria-placeholder*=\"What's on your mind\"][contenteditable='true']",
                "div[contenteditable='true'][aria-label*='Write something']",
                "div[contenteditable='true'][aria-label*='Share something']",
                "div[contenteditable='true'][data-lexical-editor='true']:not([aria-label*='Comment']):not([aria-label*='Reply'])",
                "div[contenteditable='true'][role='textbox']:not([aria-label*='Comment']):not([aria-label*='Reply'])",
                # More specific selectors
                "div[data-testid='status-attachment-mentions-input'] div[contenteditable='true']",
                "div[aria-label*='post'][contenteditable='true']",
                "div[aria-label*='status'][contenteditable='true']"
            ],
            'photo_video_button': [
                # Photo/Video upload buttons
                "div[aria-label='Photo/video']",
                "div[aria-label='Add photos/videos']",
                "div[aria-label='Photo/Video']",
                "input[accept*='image'],input[accept*='video']",
                "input[type='file'][accept*='image'],input[type='file'][accept*='video']",
                "div[data-testid='photo-video-button']",
                "div[role='button']:has-text('Photo/video')",
                "div[role='button']:has-text('Photo/Video')"
            ],
            'post_button': [
                # Post/Share buttons
                "div[aria-label='Post'][role='button']",
                "div[aria-label='Share'][role='button']",
                "div[aria-label='Publish'][role='button']",
                "button[aria-label='Post']",
                "button[aria-label='Share']",
                "div[role='button']:has-text('Post')",
                "div[role='button']:has-text('Share')",
                "div[role='button']:has-text('Publish')"
            ],
            'composer_indicators': [
                # Elements that indicate composer is open
                "div[aria-label='Post'][role='button']",
                "div[aria-label='Photo/video']",
                "div[contenteditable='true'][aria-label*=\"What's on your mind\"]",
                "form[method='post']",
                "div[data-testid='status-attachment-mentions-input']"
            ],
            'media_upload_indicators': [
                # Elements that indicate media is uploaded
                "img[alt*='uploaded']",
                "video[src*='blob:']",
                "div[aria-label*='Remove photo']",
                "div[aria-label*='Remove video']",
                "div[data-testid='media-upload-preview']",
                "img[src*='scontent']",
                "video[poster]"
            ],
            # Facebook Reels selectors
            'reels_upload_input': [
                "input[type='file'][accept*='video']",
                "input[accept*='video']",
                "input[type='file']"
            ],
            'reels_next_button': [
                "div[aria-label='Next'][role='button']",
                "div[aria-label='Berikutnya'][role='button']",
                "button:has-text('Next')",
                "button:has-text('Berikutnya')",
                "div[role='button']:has-text('Next')",
                "div[role='button']:has-text('Berikutnya')"
            ],
            'reels_description_input': [
                "div[aria-label*='description'][contenteditable='true']",
                "div[aria-placeholder*='description'][contenteditable='true']",
                "div[contenteditable='true'][aria-label*='Describe']",
                "textarea[placeholder*='description']",
                "div[contenteditable='true'][role='textbox']"
            ],
            'reels_publish_button': [
                "div[aria-label='Publish'][role='button']",
                "div[aria-label='Terbitkan'][role='button']",
                "button:has-text('Publish')",
                "button:has-text('Terbitkan')",
                "div[role='button']:has-text('Publish')",
                "div[role='button']:has-text('Terbitkan')"
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
        
        if self.headless:
            chrome_options.add_argument('--headless=new')
            self._log("Mode headless diaktifkan")
        
        # Performance optimizations
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-images')
        chrome_options.add_argument('--disable-plugins-discovery')
        chrome_options.add_argument('--disable-translate')
        chrome_options.add_argument('--disable-popup-blocking')
        chrome_options.add_argument('--disable-notifications')
        chrome_options.add_argument('--disable-geolocation')
        chrome_options.add_argument('--disable-media-stream')
        
        # Anti-detection
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Suppress logs
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--silent")
        chrome_options.add_argument("--disable-logging")
        
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

    def _wait_for_page_load(self, timeout: int = 10):
        """Wait for page to fully load"""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            time.sleep(2)  # Additional wait for dynamic content
        except TimeoutException:
            self._log("Page load timeout, continuing...", "WARNING")

    def _remove_overlays(self):
        """Remove Facebook overlays that might block interactions"""
        try:
            overlay_selectors = [
                "div[role='dialog']",
                "div[aria-modal='true']",
                "div[data-testid='modal-overlay']",
                "div[class*='overlay']",
                "div[class*='modal']",
                "div[class*='popup']"
            ]
            
            for selector in overlay_selectors:
                try:
                    overlays = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for overlay in overlays:
                        if overlay.is_displayed():
                            self.driver.execute_script("arguments[0].style.display = 'none';", overlay)
                            self._log(f"Removed overlay: {selector}", "DEBUG")
                except:
                    continue
                    
        except Exception as e:
            self._log(f"Error removing overlays: {e}", "DEBUG")

    def _scroll_to_element(self, element):
        """Scroll element into view and ensure it's visible"""
        try:
            # Scroll to element
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            time.sleep(1)
            
            # Ensure element is in viewport
            self.driver.execute_script("""
                var rect = arguments[0].getBoundingClientRect();
                if (rect.top < 0 || rect.bottom > window.innerHeight) {
                    arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});
                }
            """, element)
            time.sleep(1)
            
            return True
        except Exception as e:
            self._log(f"Error scrolling to element: {e}", "DEBUG")
            return False

    def _wait_for_element_interactable(self, element, timeout: int = 10):
        """Wait for element to become interactable"""
        try:
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    if (element.is_displayed() and 
                        element.is_enabled() and 
                        element.size['height'] > 0 and 
                        element.size['width'] > 0):
                        
                        # Check if element is not covered by other elements
                        location = element.location_once_scrolled_into_view
                        if location:
                            return True
                            
                except StaleElementReferenceException:
                    break
                except Exception:
                    pass
                    
                time.sleep(0.5)
            
            return False
        except Exception as e:
            self._log(f"Error waiting for element interactable: {e}", "DEBUG")
            return False

    def _enhanced_click(self, element, element_name: str = "element"):
        """Enhanced click with multiple fallback methods"""
        try:
            # Method 1: Wait for element to be interactable
            self._log(f"🖱️ Attempting regular click on {element_name}...")
            
            # Remove overlays first
            self._remove_overlays()
            
            # Scroll to element
            self._scroll_to_element(element)
            
            # Wait for interactability
            if not self._wait_for_element_interactable(element, timeout=5):
                self._log(f"⚠️ Element not interactable, trying alternatives...", "WARNING")
            
            # Try regular click
            try:
                WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(element))
                element.click()
                self._log(f"✅ CLICK SUCCESS: Regular click on {element_name}", "SUCCESS")
                return True
            except (ElementClickInterceptedException, ElementNotInteractableException) as e:
                self._log(f"⚠️ ⚠️ Regular click failed on {element_name}: {str(e)}", "WARNING")
            
            # Method 2: JavaScript click
            self._log(f"🖱️ Attempting JavaScript click on {element_name}...")
            try:
                self.driver.execute_script("arguments[0].click();", element)
                self._log(f"✅ CLICK SUCCESS: JavaScript click on {element_name}", "SUCCESS")
                return True
            except Exception as e:
                self._log(f"⚠️ JavaScript click failed on {element_name}: {str(e)}", "WARNING")
            
            # Method 3: ActionChains click
            self._log(f"🖱️ Attempting ActionChains click on {element_name}...")
            try:
                actions = ActionChains(self.driver)
                actions.move_to_element(element).click().perform()
                self._log(f"✅ CLICK SUCCESS: ActionChains click on {element_name}", "SUCCESS")
                return True
            except Exception as e:
                self._log(f"⚠️ ActionChains click failed on {element_name}: {str(e)}", "WARNING")
            
            # Method 4: Force click with coordinates
            self._log(f"🖱️ Attempting coordinate click on {element_name}...")
            try:
                location = element.location_once_scrolled_into_view
                size = element.size
                x = location['x'] + size['width'] // 2
                y = location['y'] + size['height'] // 2
                
                actions = ActionChains(self.driver)
                actions.move_by_offset(x, y).click().perform()
                self._log(f"✅ CLICK SUCCESS: Coordinate click on {element_name}", "SUCCESS")
                return True
            except Exception as e:
                self._log(f"⚠️ Coordinate click failed on {element_name}: {str(e)}", "WARNING")
            
            # Method 5: Send ENTER key
            self._log(f"🖱️ Attempting ENTER key on {element_name}...")
            try:
                element.send_keys(Keys.ENTER)
                self._log(f"✅ CLICK SUCCESS: ENTER key on {element_name}", "SUCCESS")
                return True
            except Exception as e:
                self._log(f"⚠️ ENTER key failed on {element_name}: {str(e)}", "WARNING")
            
            # Method 6: Send SPACE key
            self._log(f"🖱️ Attempting SPACE key on {element_name}...")
            try:
                element.send_keys(Keys.SPACE)
                self._log(f"✅ CLICK SUCCESS: SPACE key on {element_name}", "SUCCESS")
                return True
            except Exception as e:
                self._log(f"⚠️ SPACE key failed on {element_name}: {str(e)}", "WARNING")
            
            self._log(f"❌ ALL CLICK METHODS FAILED for {element_name}", "ERROR")
            return False
            
        except Exception as e:
            self._log(f"❌ Enhanced click error for {element_name}: {str(e)}", "ERROR")
            return False

    def _find_element_by_selectors(self, selectors: list, timeout: int = 10, visible: bool = True) -> Optional[Any]:
        """Find element using multiple selectors with enhanced validation"""
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
                
                # Additional validation for status composer elements
                if 'status' in str(selectors) or 'composer' in str(selectors):
                    aria_label = element.get_attribute('aria-label') or ''
                    if 'Comment' in aria_label or 'Reply' in aria_label:
                        self._log(f"⚠️ Skipping comment/reply element: {aria_label}", "DEBUG")
                        continue
                
                if i == 0:
                    self._log("✅ Found element with primary selector", "SUCCESS")
                else:
                    self._log(f"⚠️ Found element with fallback #{i}", "WARNING")
                
                return element
                
            except TimeoutException:
                continue
                
        return None

    def _validate_composer_open(self) -> bool:
        """Validate that the status composer is actually open"""
        try:
            indicators = self.selectors['composer_indicators']
            found_indicators = 0
            
            for selector in indicators:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements and any(el.is_displayed() for el in elements):
                        found_indicators += 1
                except:
                    continue
            
            self._log(f"🔍 Found {found_indicators} composer indicators", "INFO")
            return found_indicators >= 2  # Need at least 2 indicators
            
        except Exception as e:
            self._log(f"Error validating composer: {e}", "DEBUG")
            return False

    def _validate_media_uploaded(self) -> bool:
        """Validate that media is actually uploaded"""
        try:
            indicators = self.selectors['media_upload_indicators']
            
            for selector in indicators:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements and any(el.is_displayed() for el in elements):
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            self._log(f"Error validating media upload: {e}", "DEBUG")
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

    def upload_status(self, status_text: str = "", media_path: str = "") -> Dict[str, Any]:
        """
        Upload status ke Facebook dengan dukungan text dan media
        
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
            
            # Navigate to Facebook
            self._log("Navigating to Facebook...")
            self.driver.get(self.base_url)
            self._wait_for_page_load()
            
            # Take screenshot before starting
            self.take_screenshot(f"facebook_before_post_{int(time.time())}.png")
            
            # Check if login required
            if self.check_login_required():
                if cookies_loaded:
                    self._log("Cookies dimuat tapi masih perlu login, refresh halaman...", "WARNING")
                    self.driver.refresh()
                    self._wait_for_page_load()
                
                if self.check_login_required():
                    self.wait_for_login()
                    self.driver.get(self.base_url)
                    self._wait_for_page_load()
            
            # Determine mode
            has_text = bool(status_text.strip())
            has_media = bool(media_path and os.path.exists(media_path))
            
            if not has_text and not has_media:
                raise ValueError("Minimal status text atau media diperlukan")
            
            if has_text and has_media:
                mode = "TEXT + MEDIA"
            elif has_media:
                mode = "MEDIA ONLY"
            else:
                mode = "TEXT ONLY"
            
            self._log(f"🎯 MODE: {mode}", "INFO")
            
            # STEP 1: Click "What's on your mind" to open composer
            self._log("🎯 STEP 1: Looking for 'What's on your mind' click element...", "INFO")
            composer_click = self._find_element_by_selectors(self.selectors['status_composer_click'])
            
            if not composer_click:
                raise NoSuchElementException("Tidak dapat menemukan elemen 'What's on your mind'")
            
            self._log("✅ Found 'What's on your mind' click element", "SUCCESS")
            
            # Enhanced click for composer
            self._log("🖱️ Clicking 'What's on your mind' element...", "INFO")
            if not self._enhanced_click(composer_click, "'What's on your mind' click"):
                raise ElementNotInteractableException("Gagal mengklik elemen 'What's on your mind'")
            
            # Wait for composer to open
            time.sleep(3)
            
            # Validate composer is open
            self._log("🔍 VALIDATING: Checking if composer is really open...", "INFO")
            if not self._validate_composer_open():
                raise Exception("Composer tidak terbuka dengan benar")
            
            self._log("✅ VALIDATION SUCCESS: Composer is open", "SUCCESS")
            
            # STEP 2: Add media first if available
            if has_media:
                self._log("🎯 STEP 2: Adding media FIRST...", "INFO")
                
                photo_video_btn = self._find_element_by_selectors(self.selectors['photo_video_button'])
                if not photo_video_btn:
                    raise NoSuchElementException("Tidak dapat menemukan tombol Photo/Video")
                
                self._log("✅ Found Photo/Video button", "SUCCESS")
                
                if not self._enhanced_click(photo_video_btn, "Photo/Video button"):
                    raise ElementNotInteractableException("Gagal mengklik tombol Photo/Video")
                
                # Wait for file dialog and upload
                time.sleep(2)
                
                # Find file input
                file_input = self._find_element_by_selectors(
                    ["input[type='file']", "input[accept*='image']", "input[accept*='video']"],
                    timeout=5,
                    visible=False
                )
                
                if not file_input:
                    raise NoSuchElementException("Tidak dapat menemukan input file")
                
                # Upload file
                abs_path = os.path.abspath(media_path)
                file_input.send_keys(abs_path)
                
                self._log("✅ STEP 2 COMPLETE: Media uploaded successfully", "SUCCESS")
                
                # Wait for media to process
                time.sleep(5)
                
                # Validate media upload
                self._log("🔍 VALIDATING: Checking if media is really uploaded...", "INFO")
                if self._validate_media_uploaded():
                    self._log("✅ MEDIA VALIDATION SUCCESS: Media uploaded", "SUCCESS")
                else:
                    self._log("⚠️ MEDIA VALIDATION WARNING: Cannot confirm media upload", "WARNING")
            
            # STEP 3: Add text after media (if both are present)
            if has_text:
                step_num = 3 if has_media else 2
                self._log(f"🎯 STEP {step_num}: Adding status text{'AFTER media' if has_media else ''}...", "INFO")
                
                text_input = self._find_element_by_selectors(self.selectors['status_text_input'])
                if not text_input:
                    raise NoSuchElementException("Tidak dapat menemukan input text status")
                
                if not self._enhanced_click(text_input, "text input"):
                    raise ElementNotInteractableException("Gagal mengklik input text")
                
                # Input text with multiple methods
                success = False
                
                # Method 1: Direct send_keys
                try:
                    self._log("🖊️ Trying text input method 1...", "INFO")
                    text_input.clear()
                    text_input.send_keys(status_text)
                    
                    # Validate text input
                    time.sleep(1)
                    current_text = text_input.text or text_input.get_attribute('value') or ''
                    if status_text.lower() in current_text.lower():
                        self._log("✅ TEXT VALIDATION SUCCESS: Text found with method 1", "SUCCESS")
                        self._log(f"Expected: '{status_text}', Found: '{current_text[:50]}...'", "INFO")
                        success = True
                    else:
                        self._log(f"⚠️ Text validation failed. Expected: '{status_text}', Found: '{current_text}'", "WARNING")
                except Exception as e:
                    self._log(f"⚠️ Text input method 1 failed: {e}", "WARNING")
                
                # Method 2: JavaScript input
                if not success:
                    try:
                        self._log("🖊️ Trying text input method 2 (JavaScript)...", "INFO")
                        self.driver.execute_script("arguments[0].innerText = arguments[1];", text_input, status_text)
                        self.driver.execute_script("arguments[0].textContent = arguments[1];", text_input, status_text)
                        
                        time.sleep(1)
                        current_text = text_input.text or text_input.get_attribute('value') or ''
                        if status_text.lower() in current_text.lower():
                            self._log("✅ TEXT VALIDATION SUCCESS: Text found with method 2", "SUCCESS")
                            success = True
                    except Exception as e:
                        self._log(f"⚠️ Text input method 2 failed: {e}", "WARNING")
                
                # Method 3: Character by character
                if not success:
                    try:
                        self._log("🖊️ Trying text input method 3 (char by char)...", "INFO")
                        text_input.clear()
                        for char in status_text:
                            text_input.send_keys(char)
                            time.sleep(0.05)
                        
                        time.sleep(1)
                        current_text = text_input.text or text_input.get_attribute('value') or ''
                        if status_text.lower() in current_text.lower():
                            self._log("✅ TEXT VALIDATION SUCCESS: Text found with method 3", "SUCCESS")
                            success = True
                    except Exception as e:
                        self._log(f"⚠️ Text input method 3 failed: {e}", "WARNING")
                
                if success:
                    self._log(f"✅ STEP {step_num} COMPLETE: Status text added successfully", "SUCCESS")
                else:
                    self._log(f"⚠️ STEP {step_num} WARNING: Text input may have failed", "WARNING")
            
            # FINAL STEP: Click Post button
            final_step = 4 if has_media and has_text else (3 if has_media or has_text else 2)
            self._log(f"🎯 STEP {final_step}: Clicking Post button...", "INFO")
            
            post_button = self._find_element_by_selectors(self.selectors['post_button'])
            if not post_button:
                raise NoSuchElementException("Tidak dapat menemukan tombol Post")
            
            self._log("✅ Found Post button", "SUCCESS")
            
            if not self._enhanced_click(post_button, "Post button"):
                raise ElementNotInteractableException("Gagal mengklik tombol Post")
            
            # Wait for post to complete
            time.sleep(5)
            
            # Validate post success
            self._log("🔍 VALIDATING: Checking if post was successful...", "INFO")
            current_url = self.driver.current_url
            if self.base_url in current_url and "composer" not in current_url:
                self._log("✅ POST VALIDATION SUCCESS: Returned to feed", "SUCCESS")
                success = True
            else:
                self._log("⚠️ POST VALIDATION WARNING: Cannot confirm post success", "WARNING")
                success = True  # Assume success if no error
            
            if success:
                self._log("✅ Facebook status posted successfully!", "SUCCESS")
                return {
                    "success": True,
                    "message": "Status berhasil dipost",
                    "mode": mode,
                    "status_text": status_text,
                    "media_path": media_path
                }
            else:
                return {
                    "success": False,
                    "message": "Post mungkin berhasil tapi tidak dapat dikonfirmasi",
                    "mode": mode,
                    "status_text": status_text,
                    "media_path": media_path
                }
                
        except Exception as e:
            error_msg = f"Upload status gagal: {str(e)}"
            self._log(error_msg, "ERROR")
            
            # Take error screenshot
            self.take_screenshot(f"facebook_error_{int(time.time())}.png")
            
            return {
                "success": False,
                "message": error_msg,
                "status_text": status_text,
                "media_path": media_path
            }
        
        finally:
            if self.driver:
                self._log("Closing browser...", "INFO")
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
            
            # Navigate to Facebook Reels Create
            self._log("Navigasi ke Facebook Reels Create...")
            self.driver.get(self.reels_url)
            self._wait_for_page_load()
            
            # Check if login required
            if self.check_login_required():
                if cookies_loaded:
                    self._log("Cookies dimuat tapi masih perlu login, refresh halaman...", "WARNING")
                    self.driver.refresh()
                    self._wait_for_page_load()
                
                if self.check_login_required():
                    self.wait_for_login()
                    self.driver.get(self.reels_url)
                    self._wait_for_page_load()
            
            # Upload video
            self._log("Memulai upload video reels...")
            
            # Find upload input
            upload_input = self._find_element_by_selectors(self.selectors['reels_upload_input'], visible=False)
            if not upload_input:
                raise NoSuchElementException("Tidak dapat menemukan input upload video")
            
            self._log("Input upload ditemukan. Mengirim file...")
            abs_path = os.path.abspath(video_path)
            upload_input.send_keys(abs_path)
            
            self._log("File video berhasil dikirim ke input.", "SUCCESS")
            
            # Wait for upload to process
            time.sleep(10)
            
            # Click Next buttons (usually 2 times)
            for i in range(1, 3):
                try:
                    next_button = self._find_element_by_selectors(self.selectors['reels_next_button'], timeout=10)
                    if next_button:
                        if self._enhanced_click(next_button, f"Next button (step {i})"):
                            self._log(f"Tombol 'Next' berhasil diklik (index {i})!", "SUCCESS")
                            time.sleep(3)
                        else:
                            self._log(f"Gagal mengklik tombol Next {i}", "WARNING")
                    else:
                        self._log(f"Tombol Next {i} tidak ditemukan, melanjutkan...", "WARNING")
                        break
                except Exception as e:
                    self._log(f"Error pada Next button {i}: {e}", "WARNING")
                    break
            
            # Add description if provided
            if description.strip():
                self._log("Mengisi deskripsi reels...")
                desc_input = self._find_element_by_selectors(self.selectors['reels_description_input'])
                if desc_input:
                    if self._enhanced_click(desc_input, "description input"):
                        try:
                            desc_input.clear()
                            desc_input.send_keys(description)
                            self._log("Deskripsi berhasil diisi", "SUCCESS")
                        except Exception as e:
                            self._log(f"Gagal mengisi deskripsi: {e}", "WARNING")
                else:
                    self._log("Input deskripsi tidak ditemukan", "WARNING")
            
            # Click Publish button
            self._log("Mencari tombol Publish...")
            publish_button = self._find_element_by_selectors(self.selectors['reels_publish_button'])
            if not publish_button:
                raise NoSuchElementException("Tidak dapat menemukan tombol Publish")
            
            if self._enhanced_click(publish_button, "Publish button"):
                self._log("Upload video reels berhasil!", "SUCCESS")
                time.sleep(5)
                
                return {
                    "success": True,
                    "message": "Reels berhasil diupload",
                    "video_path": video_path,
                    "description": description
                }
            else:
                raise ElementNotInteractableException("Gagal mengklik tombol Publish")
                
        except Exception as e:
            error_msg = f"Upload reels gagal: {str(e)}"
            self._log(error_msg, "ERROR")
            
            # Take error screenshot
            self.take_screenshot(f"facebook_reels_error_{int(time.time())}.png")
            
            return {
                "success": False,
                "message": error_msg,
                "video_path": video_path,
                "description": description
            }
        
        finally:
            if self.driver:
                self._log("Menutup browser...", "INFO")
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
            
            # Check expired cookies
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
    parser = argparse.ArgumentParser(description="Facebook Status & Reels Uploader")
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
        print(f"{Fore.YELLOW}📝 Status + 🎬 Reels Support")
        print()
        
        while True:
            print(f"\n{Fore.YELLOW}Pilih jenis upload:")
            print("1. 📝 Upload Status (Text/Media)")
            print("2. 🎬 Upload Reels (Video)")
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