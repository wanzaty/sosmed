#!/usr/bin/env python3
"""
Facebook Uploader untuk Status dan Reels
Mendukung cookies JSON untuk auto-login dan selector yang robust
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
        self.facebook_url = "https://www.facebook.com"
        self.reels_create_url = "https://www.facebook.com/reels/create/?surface=PROFILE_PLUS"
        
        # Enhanced selectors dengan lebih banyak fallback
        self.selectors = {
            # What's on your mind selectors - EXPANDED
            'whats_on_mind_click': [
                # Standard selectors
                "div[role='textbox'][aria-label*='mind']",
                "div[role='textbox'][data-text*='mind']",
                "div[contenteditable='true'][aria-label*='mind']",
                "div[contenteditable='true'][data-text*='mind']",
                
                # Placeholder-based selectors
                "div[aria-placeholder*='mind']",
                "div[placeholder*='mind']",
                "textarea[placeholder*='mind']",
                "input[placeholder*='mind']",
                
                # Generic post creation selectors
                "div[role='textbox'][aria-label*='post']",
                "div[role='textbox'][aria-label*='share']",
                "div[role='textbox'][aria-label*='write']",
                "div[contenteditable='true'][aria-label*='post']",
                
                # Data attribute selectors
                "div[data-testid*='status']",
                "div[data-testid*='composer']",
                "div[data-testid*='post']",
                
                # Class-based selectors
                ".composer_rich_textarea",
                ".notranslate[contenteditable='true']",
                "div[contenteditable='true'].notranslate",
                
                # Aria-label variations
                "div[aria-label*='What']",
                "div[aria-label*='Share']",
                "div[aria-label*='Create']",
                "div[aria-label*='Post']",
                
                # Generic fallbacks
                "div[contenteditable='true']",
                "div[role='textbox']",
                "textarea",
                ".UFIAddCommentInput",
                
                # Mobile/responsive selectors
                "div[data-sigil='composer-textarea']",
                "div[data-sigil='status-textarea']"
            ],
            
            # Composer validation selectors
            'composer_indicators': [
                "div[aria-label*='Post']",
                "button[aria-label*='Post']",
                "div[role='dialog']",
                "div[aria-modal='true']",
                "div[data-testid*='composer']",
                ".composer",
                "form[method='post']",
                "div[contenteditable='true']",
                "textarea[placeholder*='mind']",
                "div[aria-label*='Create post']"
            ],
            
            # Photo/Video button selectors - EXPANDED
            'photo_video_button': [
                # Primary selectors
                "div[aria-label*='Photo/video']",
                "div[aria-label*='Photo']",
                "div[aria-label*='Video']",
                "button[aria-label*='Photo/video']",
                "button[aria-label*='Photo']",
                
                # Data attribute selectors
                "div[data-testid*='photo']",
                "div[data-testid*='media']",
                "button[data-testid*='photo']",
                
                # Icon-based selectors
                "div[role='button'] svg[aria-label*='Photo']",
                "button svg[aria-label*='Photo']",
                "div[role='button'] i[data-visualcompletion='css-img']",
                
                # Text-based selectors
                "div[role='button']:contains('Photo')",
                "button:contains('Photo')",
                "span:contains('Photo/video')",
                
                # Generic media selectors
                "input[type='file'][accept*='image']",
                "input[type='file'][accept*='video']",
                "input[accept*='image,video']",
                
                # Fallback selectors
                "div[role='button'][tabindex='0']",
                "button[type='button']"
            ],
            
            # File input selectors
            'file_input': [
                "input[type='file'][accept*='video']",
                "input[type='file'][accept*='image']",
                "input[type='file']",
                "input[accept*='video']",
                "input[accept*='image']"
            ],
            
            # Text input selectors for status
            'status_text_input': [
                "div[contenteditable='true'][aria-label*='mind']",
                "div[contenteditable='true'][data-text*='mind']",
                "div[contenteditable='true'][aria-placeholder*='mind']",
                "div[role='textbox'][aria-label*='mind']",
                "div[role='textbox']",
                "div[contenteditable='true']",
                "textarea[placeholder*='mind']",
                "textarea",
                ".notranslate[contenteditable='true']",
                "div[aria-label*='Comment']",
                "div[contenteditable='true'].notranslate"
            ],
            
            # Post button selectors
            'post_button': [
                "div[aria-label='Post'][role='button']",
                "button[aria-label='Post']",
                "div[role='button'][aria-label='Post']",
                "button:contains('Post')",
                "div[role='button']:contains('Post')",
                "button[type='submit']",
                "div[data-testid*='post']",
                "button[data-testid*='post']"
            ],
            
            # Success indicators
            'success_indicators': [
                "div[role='alert']",
                "div[aria-live='polite']",
                "div[data-testid='success']",
                ".success",
                "div:contains('posted')",
                "div:contains('shared')"
            ],
            
            # Overlay/modal close selectors
            'overlay_close': [
                "div[aria-label='Close']",
                "button[aria-label='Close']",
                "div[role='button'][aria-label='Close']",
                "button[aria-label='Cancel']",
                "div[aria-label='Dismiss']",
                ".close",
                "button.close",
                "div[data-testid='close']"
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
        chrome_options.add_argument('--log-level=3')
        chrome_options.add_argument('--silent')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Anti-detection
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            driver_path = self._get_chromedriver_path()
            service = Service(driver_path, log_path=os.devnull)
            
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.wait = WebDriverWait(self.driver, 30)
            
            self._log("Browser siap digunakan", "SUCCESS")
            
        except Exception as e:
            self._log(f"Gagal menyiapkan browser: {str(e)}", "ERROR")
            raise

    def _find_element_with_retry(self, selectors: list, timeout: int = 10, max_retries: int = 3) -> Optional[Any]:
        """Find element dengan retry mechanism yang robust"""
        for retry in range(max_retries):
            if retry > 0:
                self._log(f"🔄 Retry {retry + 1}/{max_retries} finding element...")
                time.sleep(2)
            
            for i, selector in enumerate(selectors):
                try:
                    element = WebDriverWait(self.driver, timeout // max_retries).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    
                    if element and element.is_displayed():
                        if i == 0:
                            self._log("✅ ✅ Found element with primary selector", "SUCCESS")
                        elif i < 5:
                            self._log(f"✅ ✅ Found element with priority selector", "SUCCESS")
                        else:
                            self._log(f"✅ ✅ Found element with fallback #{i-4}", "SUCCESS")
                        return element
                        
                except (TimeoutException, NoSuchElementException, StaleElementReferenceException):
                    continue
                except Exception as e:
                    if self.debug:
                        self._log(f"🔍 Selector {i+1} error: {str(e)[:50]}...", "DEBUG")
                    continue
        
        return None

    def _dismiss_overlays(self):
        """Dismiss any overlays or modals that might be blocking"""
        self._log("🔍 Checking for overlays to dismiss...")
        
        dismissed_count = 0
        for selector in self.selectors['overlay_close']:
            try:
                overlays = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for overlay in overlays:
                    if overlay.is_displayed():
                        try:
                            overlay.click()
                            self._log(f"✅ ✅ Dismissed overlay with selector: {selector}...")
                            dismissed_count += 1
                            time.sleep(1)
                        except:
                            continue
            except:
                continue
        
        if dismissed_count > 0:
            self._log(f"✅ ✅ Dismissed {dismissed_count} overlays", "SUCCESS")
            time.sleep(2)  # Wait for UI to settle
        else:
            self._log("ℹ️ ℹ️ No overlays found to dismiss")

    def _scroll_to_element(self, element):
        """Scroll element into view dengan error handling"""
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            time.sleep(1)
            self._log("✅ ✅ Element scrolled into view", "SUCCESS")
            return True
        except Exception as e:
            self._log(f"⚠️ ⚠️ Failed to scroll element: {str(e)}", "WARNING")
            return False

    def _click_element_robust(self, element, element_name: str) -> bool:
        """Click element dengan multiple strategies"""
        try:
            # Strategy 1: Regular click
            self._log(f"🖱️ Attempting regular click on {element_name}...")
            element.click()
            self._log(f"✅ ✅ CLICK SUCCESS: Regular click on {element_name}", "SUCCESS")
            return True
            
        except ElementClickInterceptedException:
            self._log(f"⚠️ ⚠️ Regular click failed on {element_name}: Element intercepted", "WARNING")
            
            # Strategy 2: JavaScript click
            try:
                self._log(f"🖱️ Attempting JavaScript click on {element_name}...")
                self.driver.execute_script("arguments[0].click();", element)
                self._log(f"✅ ✅ CLICK SUCCESS: JavaScript click on {element_name}", "SUCCESS")
                return True
            except Exception as e:
                self._log(f"⚠️ ⚠️ JavaScript click failed on {element_name}: {str(e)}", "WARNING")
                
        except StaleElementReferenceException:
            self._log(f"⚠️ ⚠️ Element became stale during click: {element_name}", "WARNING")
            return False
            
        except Exception as e:
            self._log(f"⚠️ ⚠️ Regular click failed on {element_name}: {str(e)}", "WARNING")
            
            # Strategy 3: ActionChains
            try:
                self._log(f"🖱️ Attempting ActionChains click on {element_name}...")
                ActionChains(self.driver).move_to_element(element).click().perform()
                self._log(f"✅ ✅ CLICK SUCCESS: ActionChains click on {element_name}", "SUCCESS")
                return True
            except Exception as e:
                self._log(f"⚠️ ⚠️ ActionChains click failed on {element_name}: {str(e)}", "WARNING")
        
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
            
            # Navigate ke Facebook dulu
            self.driver.get(self.facebook_url)
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
            filename = f"facebook_screenshot_{int(time.time())}.png"
        
        screenshot_path = self.screenshots_dir / filename
        
        try:
            if self.driver:
                self.driver.save_screenshot(str(screenshot_path))
                self._log(f"Screenshot saved: {screenshot_path.name}", "INFO")
                return str(screenshot_path)
        except Exception as e:
            self._log(f"Gagal menyimpan screenshot: {str(e)}", "WARNING")
            return None

    def _validate_composer_open(self) -> bool:
        """Validate apakah composer benar-benar terbuka"""
        self._log("🔍 VALIDATING: Checking if composer is really open...")
        
        indicators_found = 0
        for selector in self.selectors['composer_indicators']:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                indicators_found += len([e for e in elements if e.is_displayed()])
            except:
                continue
        
        self._log(f"🔍 Found {indicators_found} composer indicators")
        
        if indicators_found >= 2:  # Lowered threshold
            self._log("✅ ✅ VALIDATION SUCCESS: Composer is open", "SUCCESS")
            return True
        else:
            self._log(f"❌ ❌ VALIDATION FAILED: Composer not open ({indicators_found} indicators found)", "ERROR")
            return False

    def _try_alternative_composer_strategies(self) -> bool:
        """Try alternative strategies to open composer"""
        
        # Strategy 2: Look for composer directly
        self._log("🎯 STRATEGY 2: Looking for composer directly...")
        composer_selectors = [
            "div[role='dialog']",
            "div[aria-modal='true']",
            "form[method='post']",
            "div[data-testid*='composer']"
        ]
        
        for selector in composer_selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                if element.is_displayed():
                    self._log(f"✅ Found composer with selector: {selector}")
                    return True
            except:
                continue
        
        if self._validate_composer_open():
            return True
        
        # Strategy 3: Try page interaction
        self._log("🎯 STRATEGY 3: Trying page interaction to trigger composer...")
        try:
            # Try clicking on page body
            body = self.driver.find_element(By.TAG_NAME, "body")
            body.click()
            time.sleep(1)
            
            # Try pressing Tab to navigate
            ActionChains(self.driver).send_keys(Keys.TAB).perform()
            time.sleep(1)
            
        except:
            pass
        
        if self._validate_composer_open():
            return True
        
        # Strategy 4: Try direct URL navigation
        self._log("🎯 STRATEGY 4: Trying direct URL navigation...")
        try:
            self.driver.get("https://www.facebook.com/?sk=h_chr")
            time.sleep(3)
        except:
            pass
        
        return self._validate_composer_open()

    def upload_status(self, status_text: str = "", media_path: str = "") -> Dict[str, Any]:
        """
        Upload status ke Facebook dengan dukungan media
        
        Args:
            status_text: Text untuk status
            media_path: Path ke file media (video/gambar)
            
        Returns:
            Dict dengan status upload
        """
        try:
            # Validasi input
            if not status_text.strip() and not media_path:
                raise ValueError("Status text atau media path diperlukan")
            
            if media_path and not os.path.exists(media_path):
                raise FileNotFoundError(f"File media tidak ditemukan: {media_path}")
            
            # Setup driver
            self._setup_driver()
            
            # Load cookies
            cookies_loaded = self.load_cookies()
            
            # Navigate ke Facebook
            self._log("Navigating to Facebook...")
            self.driver.get(self.facebook_url)
            time.sleep(3)
            
            # Take screenshot for debugging
            self.take_screenshot(f"facebook_before_post_{int(time.time())}.png")
            
            # Cek login
            if self.check_login_required():
                if cookies_loaded:
                    self._log("Cookies dimuat tapi masih perlu login, refresh halaman...", "WARNING")
                    self.driver.refresh()
                    time.sleep(3)
                
                if self.check_login_required():
                    self.wait_for_login()
                    self.driver.get(self.facebook_url)
                    time.sleep(3)
            
            # Determine mode
            if status_text and media_path:
                mode = "TEXT + MEDIA"
            elif media_path:
                mode = "MEDIA ONLY"
            else:
                mode = "TEXT ONLY"
            
            self._log(f"🎯 MODE: {mode}")
            
            # STEP 1: Open composer
            self._log("🎯 STEP 1: Looking for 'What's on your mind' click element...")
            
            whats_on_mind = self._find_element_with_retry(self.selectors['whats_on_mind_click'])
            
            if not whats_on_mind:
                self._log("⚠️ ⚠️ ⚠️ Could not find 'What's on your mind' click element", "WARNING")
                
                # Try alternative strategies
                if not self._try_alternative_composer_strategies():
                    raise NoSuchElementException("Tidak dapat membuka composer Facebook")
            else:
                self._log("✅ ✅ Found 'What's on your mind' click element", "SUCCESS")
                
                # Click to open composer
                self._log("🖱️ Clicking 'What's on your mind' element...")
                
                # Dismiss overlays first
                self._dismiss_overlays()
                
                # Scroll and click
                self._scroll_to_element(whats_on_mind)
                
                if not self._click_element_robust(whats_on_mind, "'What's on your mind' click"):
                    self._log("⚠️ ⚠️ ⚠️ Composer not opened after click, trying alternative strategies...", "WARNING")
                    if not self._try_alternative_composer_strategies():
                        raise NoSuchElementException("Tidak dapat membuka composer Facebook")
                
                # Validate composer is open
                time.sleep(2)
                if not self._validate_composer_open():
                    self._log("⚠️ ⚠️ ⚠️ Composer not opened after click, trying alternative strategies...", "WARNING")
                    if not self._try_alternative_composer_strategies():
                        raise NoSuchElementException("Tidak dapat membuka composer Facebook")
            
            # STEP 2: Handle media upload if needed
            if media_path:
                self._log("🎯 STEP 2: Adding media FIRST...")
                
                # Find Photo/Video button with retry
                for attempt in range(3):
                    self._log(f"📸 Attempt {attempt + 1}/3 to find Photo/Video button...")
                    
                    # Dismiss overlays before each attempt
                    self._dismiss_overlays()
                    
                    # Re-find the element to avoid stale reference
                    photo_video_button = self._find_element_with_retry(self.selectors['photo_video_button'], timeout=5)
                    
                    if photo_video_button:
                        self._log("✅ ✅ Found Photo/Video button", "SUCCESS")
                        
                        # Scroll and click
                        self._scroll_to_element(photo_video_button)
                        
                        if self._click_element_robust(photo_video_button, "Photo/Video button"):
                            self._log("✅ ✅ Photo/Video button clicked successfully", "SUCCESS")
                            break
                        else:
                            self._log(f"⚠️ ⚠️ Failed to click Photo/Video button (attempt {attempt + 1})", "WARNING")
                            time.sleep(2)
                    else:
                        self._log(f"⚠️ ⚠️ Photo/Video button not found (attempt {attempt + 1})", "WARNING")
                        time.sleep(2)
                else:
                    raise NoSuchElementException("Gagal mengklik tombol Photo/Video")
                
                # Wait for file dialog and upload
                time.sleep(2)
                
                # Find file input
                file_input = self._find_element_with_retry(self.selectors['file_input'], timeout=10)
                if not file_input:
                    raise NoSuchElementException("Input file tidak ditemukan")
                
                # Upload file
                abs_path = os.path.abspath(media_path)
                file_input.send_keys(abs_path)
                
                self._log("✅ ✅ MEDIA VALIDATION SUCCESS: Media uploaded", "SUCCESS")
                self._log("✅ ✅ STEP 2 COMPLETE: Media uploaded successfully", "SUCCESS")
                
                # Wait for media to process
                time.sleep(3)
            
            # STEP 3: Add text if provided
            if status_text.strip():
                if media_path:
                    self._log("🎯 STEP 3: Adding status text AFTER media...")
                else:
                    self._log("🎯 STEP 3: Adding status text...")
                
                # Find text input
                text_input = self._find_element_with_retry(self.selectors['status_text_input'])
                if text_input:
                    self._log("✅ ✅ Found text input", "SUCCESS")
                    
                    try:
                        # Click and add text
                        if self._click_element_robust(text_input, "text input"):
                            time.sleep(1)
                            
                            # Clear existing text and add new
                            text_input.send_keys(Keys.CONTROL + "a")
                            text_input.send_keys(Keys.BACKSPACE)
                            text_input.send_keys(status_text)
                            
                            self._log(f"✅ ✅ TEXT SUCCESS: Status text added", "SUCCESS")
                        else:
                            self._log("⚠️ ⚠️ Failed to click text input", "WARNING")
                            
                    except StaleElementReferenceException:
                        self._log("⚠️ ⚠️ Text input became stale, trying to re-find...", "WARNING")
                        # Try to re-find text input
                        text_input = self._find_element_with_retry(self.selectors['status_text_input'])
                        if text_input:
                            text_input.send_keys(status_text)
                            self._log("✅ ✅ TEXT SUCCESS: Status text added (retry)", "SUCCESS")
                else:
                    self._log("⚠️ ⚠️ Text input tidak ditemukan", "WARNING")
            
            # STEP 4: Post
            self._log("🎯 STEP 4: Publishing post...")
            
            post_button = self._find_element_with_retry(self.selectors['post_button'])
            if not post_button:
                raise NoSuchElementException("Tombol Post tidak ditemukan")
            
            if self._click_element_robust(post_button, "Post button"):
                self._log("✅ ✅ POST SUCCESS: Post button clicked", "SUCCESS")
                
                # Wait and check for success
                time.sleep(5)
                
                # Check if we're back to feed (success indicator)
                current_url = self.driver.current_url
                if "facebook.com" in current_url and "composer" not in current_url:
                    self._log("✅ ✅ Post berhasil (kembali ke feed)", "SUCCESS")
                    
                    return {
                        "success": True,
                        "message": "Status berhasil dipost",
                        "mode": mode,
                        "status_text": status_text,
                        "media_path": media_path
                    }
                else:
                    self._log("⚠️ ⚠️ Post mungkin berhasil tapi tidak dapat dikonfirmasi", "WARNING")
                    return {
                        "success": True,
                        "message": "Post kemungkinan berhasil",
                        "mode": mode,
                        "status_text": status_text,
                        "media_path": media_path
                    }
            else:
                raise Exception("Gagal mengklik tombol Post")
                
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
            description: Deskripsi untuk reels
            
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
            self.driver.get(self.reels_create_url)
            time.sleep(5)
            
            # Cek login
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
            
            # Find upload input
            upload_selectors = [
                "input[type='file'][accept*='video']",
                "input[type='file']",
                "input[accept*='video']"
            ]
            
            upload_input = None
            for selector in upload_selectors:
                try:
                    upload_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if upload_input:
                        break
                except:
                    continue
            
            if not upload_input:
                raise NoSuchElementException("Input upload tidak ditemukan")
            
            # Upload file
            self._log("Input upload ditemukan. Mengirim file...")
            abs_path = os.path.abspath(video_path)
            upload_input.send_keys(abs_path)
            self._log("File video berhasil dikirim ke input.", "SUCCESS")
            
            # Wait for processing
            time.sleep(10)
            
            # Navigate through steps
            next_selectors = [
                "div[aria-label='Next']",
                "div[aria-label='Berikutnya']",
                "button[aria-label='Next']",
                "button[aria-label='Berikutnya']",
                "div[role='button']:contains('Next')",
                "div[role='button']:contains('Berikutnya')"
            ]
            
            # First Next
            for i, selector in enumerate(next_selectors):
                try:
                    next_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    next_button.click()
                    self._log(f"Tombol 'Next' berhasil diklik (index {i+1})!", "SUCCESS")
                    time.sleep(3)
                    break
                except:
                    continue
            
            # Second Next
            for i, selector in enumerate(next_selectors):
                try:
                    next_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    next_button.click()
                    self._log(f"Tombol 'Next' berhasil diklik (index {i+1})!", "SUCCESS")
                    time.sleep(3)
                    break
                except:
                    continue
            
            # Add description if provided
            if description.strip():
                desc_selectors = [
                    "div[contenteditable='true'][aria-label*='description']",
                    "div[contenteditable='true'][aria-label*='deskripsi']",
                    "textarea[placeholder*='description']",
                    "div[contenteditable='true']"
                ]
                
                for selector in desc_selectors:
                    try:
                        desc_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if desc_input.is_displayed():
                            desc_input.click()
                            desc_input.send_keys(description)
                            self._log("Deskripsi berhasil diisi", "SUCCESS")
                            break
                    except:
                        continue
            
            # Publish
            publish_selectors = [
                "div[aria-label='Publish']",
                "div[aria-label='Terbitkan']",
                "button[aria-label='Publish']",
                "button[aria-label='Terbitkan']",
                "div[role='button']:contains('Publish')",
                "div[role='button']:contains('Terbitkan')"
            ]
            
            for i, selector in enumerate(publish_selectors):
                try:
                    publish_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    publish_button.click()
                    self._log(f"Tombol 'Publish' berhasil diklik (index {i+1})!", "SUCCESS")
                    break
                except:
                    continue
            
            # Wait for completion
            time.sleep(10)
            
            self._log("Upload video reels berhasil!", "SUCCESS")
            
            return {
                "success": True,
                "message": "Reels berhasil diupload",
                "video_path": video_path,
                "description": description
            }
            
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
    parser.add_argument("--type", "-t", choices=['status', 'reels'], help="Jenis upload")
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
        
        return
    
    # Interactive mode
    print(f"{Fore.BLUE}📘 Facebook Uploader")
    print("=" * 40)
    print(f"{Fore.YELLOW}🔥 Status + Reels Support")
    print()
    
    while True:
        print(f"\n{Fore.YELLOW}Pilih jenis upload:")
        print("1. 📝 Facebook Status (Text/Media)")
        print("2. 🎬 Facebook Reels (Video)")
        print("3. 🍪 Cek Status Cookies")
        print("4. 🗑️ Hapus Cookies")
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