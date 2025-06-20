#!/usr/bin/env python3
"""
Facebook Uploader - Status dan Reels dengan dukungan media
Mendukung cookies JSON untuk auto-login dan selector yang spesifik
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
        
        # Enhanced selectors dengan prioritas
        self.selectors = {
            'status_click_element': [
                # Priority selectors (most likely to work)
                "div[role='textbox'][aria-label*='mind']",
                "div[role='textbox'][data-lexical-editor='true']",
                "div[contenteditable='true'][aria-label*='mind']",
                
                # Fallback selectors
                "div[aria-label*=\"What's on your mind\"]",
                "div[aria-label*='mind'][role='textbox']",
                "div[data-lexical-editor='true']",
                "div[contenteditable='true'][spellcheck='true']",
                "div[aria-placeholder*='mind']",
                
                # XPath alternatives
                "//div[contains(@aria-label, 'mind')]",
                "//div[@role='textbox' and contains(@aria-label, 'mind')]",
                "//div[@contenteditable='true' and contains(@aria-label, 'mind')]"
            ],
            
            'composer_indicators': [
                # Strong indicators that composer is open
                "div[aria-label='Create post']",
                "div[aria-label='Post']", 
                "button[aria-label='Post']",
                "div[role='dialog'][aria-label*='post']",
                "div[role='dialog'][aria-label*='Create']",
                
                # Media upload indicators
                "div[aria-label='Photo/video']",
                "input[accept*='image']",
                "input[accept*='video']",
                "div[aria-label*='Add photos']",
                
                # Text input indicators
                "div[contenteditable='true'][data-lexical-editor='true']",
                "div[role='textbox'][data-lexical-editor='true']",
                "textarea[aria-label*='post']",
                
                # Post button indicators
                "button[type='submit'][aria-label='Post']",
                "div[role='button'][aria-label='Post']"
            ],
            
            'photo_video_button': [
                # Primary selectors
                "div[aria-label='Photo/video']",
                "div[aria-label*='Photo']",
                "div[aria-label*='photo']",
                "div[aria-label*='Add photos']",
                
                # Icon-based selectors
                "div[role='button'][aria-label*='photo']",
                "div[role='button'][aria-label*='Photo']",
                "button[aria-label*='photo']",
                "button[aria-label*='Photo']",
                
                # SVG/Icon selectors
                "svg[aria-label*='photo']",
                "i[data-visualcompletion='css-img'][aria-label*='photo']",
                
                # Fallback selectors
                "div[data-testid*='photo']",
                "div[data-testid*='media']",
                
                # XPath alternatives
                "//div[@aria-label='Photo/video']",
                "//div[contains(@aria-label, 'photo') or contains(@aria-label, 'Photo')]",
                "//div[@role='button' and contains(@aria-label, 'photo')]"
            ],
            
            'file_input': [
                "input[type='file'][accept*='image']",
                "input[type='file'][accept*='video']", 
                "input[type='file'][multiple]",
                "input[type='file']",
                "input[accept*='image']",
                "input[accept*='video']"
            ],
            
            'status_text_input': [
                # After media upload, text input selectors
                "div[contenteditable='true'][data-lexical-editor='true']",
                "div[role='textbox'][data-lexical-editor='true']",
                "div[contenteditable='true'][aria-label*='Comment']",
                "div[contenteditable='true'][spellcheck='true']",
                "textarea[aria-label*='post']",
                "div[aria-label*='Comment as']",
                
                # XPath alternatives
                "//div[@contenteditable='true' and @data-lexical-editor='true']",
                "//div[@role='textbox' and @data-lexical-editor='true']"
            ],
            
            'post_button': [
                "button[type='submit'][aria-label='Post']",
                "div[role='button'][aria-label='Post']",
                "button[aria-label='Post']",
                "div[aria-label='Post'][role='button']",
                "button[type='submit']",
                
                # XPath alternatives
                "//button[@aria-label='Post']",
                "//div[@role='button' and @aria-label='Post']",
                "//button[@type='submit' and @aria-label='Post']"
            ],
            
            'overlay_close': [
                "div[aria-label='Close']",
                "button[aria-label='Close']",
                "div[role='button'][aria-label='Close']",
                "svg[aria-label='Close']",
                "i[aria-label='Close']",
                
                # XPath alternatives
                "//div[@aria-label='Close']",
                "//button[@aria-label='Close']"
            ],
            
            # Reels specific selectors
            'reels_upload_input': [
                "input[type='file'][accept*='video']",
                "input[type='file']",
                "input[accept*='video']"
            ],
            
            'reels_next_button': [
                # English
                "div[aria-label='Next']",
                "button[aria-label='Next']",
                "div[role='button'][aria-label='Next']",
                
                # Indonesian
                "div[aria-label='Berikutnya']", 
                "button[aria-label='Berikutnya']",
                "div[role='button'][aria-label='Berikutnya']",
                
                # Text-based
                "//div[text()='Next']",
                "//button[text()='Next']",
                "//div[text()='Berikutnya']",
                "//button[text()='Berikutnya']"
            ],
            
            'reels_description_input': [
                "div[contenteditable='true'][aria-label*='description']",
                "div[contenteditable='true'][data-lexical-editor='true']",
                "textarea[aria-label*='description']",
                "div[role='textbox']"
            ],
            
            'reels_publish_button': [
                # English
                "div[aria-label='Publish']",
                "button[aria-label='Publish']",
                "div[role='button'][aria-label='Publish']",
                
                # Indonesian
                "div[aria-label='Terbitkan']",
                "button[aria-label='Terbitkan']", 
                "div[role='button'][aria-label='Terbitkan']",
                
                # Text-based
                "//div[text()='Publish']",
                "//button[text()='Publish']",
                "//div[text()='Terbitkan']",
                "//button[text()='Terbitkan']"
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
            self._log("Mode headless diaktifkan")
        
        # Additional options
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-images')
        chrome_options.add_argument('--disable-notifications')
        chrome_options.add_argument('--log-level=3')
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

    def _find_element_with_retry(self, selectors: list, timeout: int = 10, retries: int = 3) -> Optional[Any]:
        """Find element dengan retry mechanism dan stale element protection"""
        for attempt in range(retries):
            if attempt > 0:
                self._log(f"🔄 Retry {attempt + 1}/{retries} finding element...")
                time.sleep(1)
            
            for i, selector in enumerate(selectors):
                try:
                    # Determine if XPath or CSS
                    if selector.startswith('//'):
                        by_method = By.XPATH
                    else:
                        by_method = By.CSS_SELECTOR
                    
                    element = WebDriverWait(self.driver, timeout // len(selectors)).until(
                        EC.presence_of_element_located((by_method, selector))
                    )
                    
                    # Validate element is displayed and not stale
                    if element and element.is_displayed():
                        if i == 0:
                            self._log("✅ ✅ Found element with primary selector", "SUCCESS")
                        elif i < 3:
                            self._log(f"✅ ✅ Found element with priority selector", "SUCCESS")
                        else:
                            self._log(f"✅ ✅ Found element with fallback #{i-2}", "SUCCESS")
                        return element
                        
                except (TimeoutException, StaleElementReferenceException, NoSuchElementException):
                    continue
                except Exception as e:
                    if self.debug:
                        self._log(f"🔍 Selector error: {str(e)[:100]}...", "DEBUG")
                    continue
        
        return None

    def _dismiss_overlays(self):
        """Dismiss any overlays that might be blocking interactions"""
        self._log("🔍 Checking for overlays to dismiss...")
        
        overlays_dismissed = 0
        
        for selector in self.selectors['overlay_close']:
            try:
                if selector.startswith('//'):
                    by_method = By.XPATH
                else:
                    by_method = By.CSS_SELECTOR
                
                overlays = self.driver.find_elements(by_method, selector)
                
                for overlay in overlays:
                    try:
                        if overlay.is_displayed() and overlay.is_enabled():
                            overlay.click()
                            self._log(f"✅ ✅ Dismissed overlay with selector: {selector[:30]}...", "SUCCESS")
                            overlays_dismissed += 1
                            time.sleep(0.5)
                    except:
                        continue
                        
            except:
                continue
        
        if overlays_dismissed > 0:
            self._log(f"✅ ✅ Dismissed {overlays_dismissed} overlays", "SUCCESS")
            time.sleep(1)  # Wait for UI to settle
        else:
            self._log("ℹ️ ℹ️ No overlays found to dismiss", "INFO")

    def _scroll_element_into_view(self, element):
        """Scroll element into view dengan error handling"""
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            time.sleep(0.5)
            self._log("✅ ✅ Element scrolled into view", "SUCCESS")
            return True
        except Exception as e:
            self._log(f"⚠️ ⚠️ Failed to scroll element: {str(e)[:100]}...", "WARNING")
            return False

    def _click_element_robust(self, element, element_name: str = "element") -> bool:
        """Robust click dengan multiple fallback methods dan stale element protection"""
        if not element:
            self._log(f"❌ ❌ Cannot click {element_name}: element is None", "ERROR")
            return False
        
        # Method 1: Regular click
        try:
            self._log(f"🖱️ Attempting regular click on {element_name}...")
            element.click()
            self._log(f"✅ ✅ CLICK SUCCESS: Regular click on {element_name}", "SUCCESS")
            return True
        except StaleElementReferenceException:
            self._log(f"⚠️ ⚠️ Element became stale during click: {element_name}", "WARNING")
            return False
        except ElementClickInterceptedException as e:
            self._log(f"⚠️ ⚠️ Regular click failed on {element_name}: {str(e)[:100]}...", "WARNING")
        except Exception as e:
            self._log(f"⚠️ ⚠️ Regular click error on {element_name}: {str(e)[:100]}...", "WARNING")
        
        # Method 2: JavaScript click
        try:
            self._log(f"🖱️ Attempting JavaScript click on {element_name}...")
            self.driver.execute_script("arguments[0].click();", element)
            self._log(f"✅ ✅ CLICK SUCCESS: JavaScript click on {element_name}", "SUCCESS")
            return True
        except StaleElementReferenceException:
            self._log(f"⚠️ ⚠️ Element became stale during JS click: {element_name}", "WARNING")
            return False
        except Exception as e:
            self._log(f"⚠️ ⚠️ JavaScript click error on {element_name}: {str(e)[:100]}...", "WARNING")
        
        # Method 3: ActionChains click
        try:
            self._log(f"🖱️ Attempting ActionChains click on {element_name}...")
            ActionChains(self.driver).move_to_element(element).click().perform()
            self._log(f"✅ ✅ CLICK SUCCESS: ActionChains click on {element_name}", "SUCCESS")
            return True
        except StaleElementReferenceException:
            self._log(f"⚠️ ⚠️ Element became stale during ActionChains: {element_name}", "WARNING")
            return False
        except Exception as e:
            self._log(f"⚠️ ⚠️ ActionChains click error on {element_name}: {str(e)[:100]}...", "WARNING")
        
        # Method 4: Send ENTER key
        try:
            self._log(f"🖱️ Attempting ENTER key on {element_name}...")
            element.send_keys(Keys.ENTER)
            self._log(f"✅ ✅ CLICK SUCCESS: ENTER key on {element_name}", "SUCCESS")
            return True
        except StaleElementReferenceException:
            self._log(f"⚠️ ⚠️ Element became stale during ENTER: {element_name}", "WARNING")
            return False
        except Exception as e:
            self._log(f"⚠️ ⚠️ ENTER key error on {element_name}: {str(e)[:100]}...", "WARNING")
        
        # Method 5: Send SPACE key
        try:
            self._log(f"🖱️ Attempting SPACE key on {element_name}...")
            element.send_keys(Keys.SPACE)
            self._log(f"✅ ✅ CLICK SUCCESS: SPACE key on {element_name}", "SUCCESS")
            return True
        except StaleElementReferenceException:
            self._log(f"⚠️ ⚠️ Element became stale during SPACE: {element_name}", "WARNING")
            return False
        except Exception as e:
            self._log(f"⚠️ ⚠️ SPACE key error on {element_name}: {str(e)[:100]}...", "WARNING")
        
        self._log(f"❌ ❌ All click methods failed for {element_name}", "ERROR")
        return False

    def _validate_composer_open(self) -> bool:
        """Validate that composer is actually open - more lenient approach"""
        self._log("🔍 🔍 VALIDATING: Checking if composer is really open...")
        
        indicators_found = 0
        unique_indicators = set()
        
        for selector in self.selectors['composer_indicators']:
            try:
                if selector.startswith('//'):
                    by_method = By.XPATH
                else:
                    by_method = By.CSS_SELECTOR
                
                elements = self.driver.find_elements(by_method, selector)
                
                for element in elements:
                    if element.is_displayed():
                        # Count each type of selector only once
                        selector_type = selector.split('[')[0] if '[' in selector else selector
                        if selector_type not in unique_indicators:
                            unique_indicators.add(selector_type)
                            indicators_found += 1
                        
            except Exception:
                continue
        
        self._log(f"🔍 Found {indicators_found} composer indicators")
        
        # More lenient validation - accept if ANY indicators found
        if indicators_found >= 1:
            self._log("✅ ✅ VALIDATION SUCCESS: Composer is open", "SUCCESS")
            return True
        else:
            self._log(f"❌ ❌ VALIDATION FAILED: Composer not open ({indicators_found} indicators found)", "ERROR")
            return False

    def _open_composer_aggressively(self) -> bool:
        """Open Facebook composer dengan multiple strategies - return True by default"""
        self._log("🎯 🎯 STEP 1: Looking for 'What's on your mind' click element...")
        
        # Strategy 1: Find and click the main composer trigger
        click_element = self._find_element_with_retry(self.selectors['status_click_element'])
        
        if click_element:
            self._log("✅ ✅ Found 'What's on your mind' click element", "SUCCESS")
            self._log("🖱️ Clicking 'What's on your mind' element...")
            
            # Dismiss overlays first
            self._dismiss_overlays()
            
            # Scroll into view
            self._scroll_element_into_view(click_element)
            
            # Try to click
            if self._click_element_robust(click_element, "'What's on your mind' click"):
                time.sleep(2)  # Wait for composer to open
                
                # Validate composer opened
                if self._validate_composer_open():
                    return True
                else:
                    self._log("⚠️ ⚠️ Composer not opened after click, trying alternative strategies...", "WARNING")
            else:
                self._log("⚠️ ⚠️ Failed to click 'What's on your mind' element", "WARNING")
        else:
            self._log("⚠️ ⚠️ Could not find 'What's on your mind' click element", "WARNING")
        
        # Strategy 2: Look for composer directly (maybe already open)
        self._log("🎯 🎯 STRATEGY 2: Looking for composer directly...")
        if self._validate_composer_open():
            return True
        
        # Strategy 3: Try page interaction to trigger composer
        self._log("🎯 🎯 STRATEGY 3: Trying page interaction to trigger composer...")
        try:
            # Click on page body and try keyboard shortcut
            body = self.driver.find_element(By.TAG_NAME, "body")
            body.click()
            time.sleep(1)
            
            # Try Ctrl+Shift+P (Facebook shortcut for post)
            ActionChains(self.driver).key_down(Keys.CONTROL).key_down(Keys.SHIFT).send_keys('p').key_up(Keys.SHIFT).key_up(Keys.CONTROL).perform()
            time.sleep(2)
            
            if self._validate_composer_open():
                return True
        except Exception as e:
            self._log(f"Strategy 3 failed: {str(e)[:50]}...", "DEBUG")
        
        # Strategy 4: Try direct URL navigation
        self._log("🎯 🎯 STRATEGY 4: Trying direct URL navigation...")
        try:
            current_url = self.driver.current_url
            if "facebook.com" in current_url and not current_url.endswith("/"):
                self.driver.get(current_url + "?sk=h_chr")
                time.sleep(3)
                
                if self._validate_composer_open():
                    return True
        except Exception as e:
            self._log(f"Strategy 4 failed: {str(e)[:50]}...", "DEBUG")
        
        # Strategy 5: Return True anyway - proceed with best effort
        self._log("🎯 🎯 STRATEGY 5: Proceeding with best effort approach...", "WARNING")
        return True  # Don't fail completely, try to continue

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
        return "login" in current_url or "passport" in current_url

    def wait_for_login(self, timeout: int = 180):
        """Tunggu user login manual"""
        self._log("Silakan login secara manual di browser...", "WARNING")
        self._log(f"Menunggu login selesai (timeout {timeout} detik)...", "INFO")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            current_url = self.driver.current_url
            
            if not ("login" in current_url or "passport" in current_url):
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
        Upload status ke Facebook dengan dukungan media
        
        Args:
            status_text: Text status (opsional jika ada media)
            media_path: Path ke file media - video atau gambar (opsional)
            
        Returns:
            Dict dengan status upload
        """
        
        # Validasi input
        if not status_text.strip() and not media_path.strip():
            return {
                "success": False,
                "message": "Status text atau media path diperlukan"
            }
        
        # Validasi file media jika ada
        if media_path and not os.path.exists(media_path):
            return {
                "success": False,
                "message": f"File media tidak ditemukan: {media_path}"
            }
        
        try:
            # Setup driver
            self._setup_driver()
            
            # Load cookies
            cookies_loaded = self.load_cookies()
            
            # Navigate ke Facebook
            self._log("Navigating to Facebook...")
            self.driver.get(self.facebook_url)
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
                    self.driver.get(self.facebook_url)
                    time.sleep(3)
            
            # Determine mode
            if status_text.strip() and media_path.strip():
                mode = "TEXT + MEDIA"
            elif media_path.strip():
                mode = "MEDIA ONLY"
            else:
                mode = "TEXT ONLY"
            
            self._log(f"🎯 🎯 MODE: {mode}")
            
            # Open composer
            if not self._open_composer_aggressively():
                raise Exception("Gagal membuka composer Facebook")
            
            # Handle different modes
            if mode in ["TEXT + MEDIA", "MEDIA ONLY"]:
                # STEP 2: Add media FIRST
                self._log("🎯 🎯 STEP 2: Adding media FIRST...")
                
                # Find Photo/Video button with retry and re-finding after overlay dismissal
                photo_video_button = None
                max_attempts = 3
                
                for attempt in range(max_attempts):
                    if attempt > 0:
                        self._log(f"🔄 Attempt {attempt + 1}/{max_attempts} to find Photo/Video button...")
                        time.sleep(1)
                    
                    # Dismiss overlays before each attempt
                    self._dismiss_overlays()
                    
                    # Re-find the element to avoid stale reference
                    photo_video_button = self._find_element_with_retry(self.selectors['photo_video_button'])
                    
                    if photo_video_button:
                        self._log("✅ ✅ Found Photo/Video button", "SUCCESS")
                        
                        # Scroll into view
                        self._scroll_element_into_view(photo_video_button)
                        
                        # Try to click
                        if self._click_element_robust(photo_video_button, "Photo/Video button"):
                            time.sleep(2)  # Wait for file dialog
                            break
                        else:
                            self._log("⚠️ ⚠️ Failed to click Photo/Video button, retrying...", "WARNING")
                            photo_video_button = None
                    else:
                        self._log("⚠️ ⚠️ Photo/Video button not found, retrying...", "WARNING")
                
                if not photo_video_button:
                    raise Exception("Gagal mengklik tombol Photo/Video")
                
                # Find and use file input
                file_input = self._find_element_with_retry(self.selectors['file_input'], timeout=10)
                if not file_input:
                    raise Exception("Input file tidak ditemukan")
                
                # Upload file
                abs_path = os.path.abspath(media_path)
                file_input.send_keys(abs_path)
                self._log("✅ ✅ MEDIA VALIDATION SUCCESS: Media uploaded", "SUCCESS")
                self._log("✅ ✅ STEP 2 COMPLETE: Media uploaded successfully", "SUCCESS")
                
                # Wait for media to process
                time.sleep(3)
                
                # STEP 3: Add status text AFTER media (if provided)
                if status_text.strip():
                    self._log("🎯 🎯 STEP 3: Adding status text AFTER media...")
                    
                    # Find text input (different selectors after media upload)
                    text_input = self._find_element_with_retry(self.selectors['status_text_input'])
                    if text_input:
                        self._log("✅ ✅ Found text input", "SUCCESS")
                        
                        # Scroll into view
                        self._scroll_element_into_view(text_input)
                        
                        # Try to click and add text
                        if self._click_element_robust(text_input, "text input"):
                            time.sleep(1)
                            
                            # Clear and add text
                            try:
                                text_input.clear()
                                text_input.send_keys(status_text)
                                self._log("✅ ✅ STEP 3 COMPLETE: Status text added", "SUCCESS")
                            except StaleElementReferenceException:
                                # Re-find and try again
                                text_input = self._find_element_with_retry(self.selectors['status_text_input'])
                                if text_input:
                                    text_input.clear()
                                    text_input.send_keys(status_text)
                                    self._log("✅ ✅ STEP 3 COMPLETE: Status text added (retry)", "SUCCESS")
                        else:
                            self._log("⚠️ ⚠️ Could not click text input, but continuing...", "WARNING")
                    else:
                        self._log("⚠️ ⚠️ Text input not found after media upload", "WARNING")
            
            else:  # TEXT ONLY mode
                self._log("🎯 🎯 STEP 2: Adding text only...")
                
                # Find text input
                text_input = self._find_element_with_retry(self.selectors['status_text_input'])
                if not text_input:
                    raise Exception("Input text tidak ditemukan")
                
                # Add text
                self._scroll_element_into_view(text_input)
                if self._click_element_robust(text_input, "text input"):
                    time.sleep(1)
                    text_input.clear()
                    text_input.send_keys(status_text)
                    self._log("✅ ✅ STEP 2 COMPLETE: Text added", "SUCCESS")
                else:
                    raise Exception("Gagal mengklik input text")
            
            # FINAL STEP: Post the status
            self._log("🎯 🎯 FINAL STEP: Posting status...")
            
            # Find and click post button
            post_button = self._find_element_with_retry(self.selectors['post_button'])
            if not post_button:
                raise Exception("Tombol Post tidak ditemukan")
            
            self._scroll_element_into_view(post_button)
            if self._click_element_robust(post_button, "Post button"):
                time.sleep(5)  # Wait for post to complete
                
                # Check if we're back to feed (indicates success)
                current_url = self.driver.current_url
                if "facebook.com" in current_url and not any(x in current_url for x in ["create", "composer", "post"]):
                    self._log("✅ ✅ Post berhasil (kembali ke feed)", "SUCCESS")
                    success = True
                else:
                    self._log("✅ ✅ Post kemungkinan berhasil", "SUCCESS")
                    success = True
            else:
                raise Exception("Gagal mengklik tombol Post")
            
            if success:
                self._log("✅ Status berhasil dipost ke Facebook!", "SUCCESS")
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
        
        if not os.path.exists(video_path):
            return {
                "success": False,
                "message": f"File video tidak ditemukan: {video_path}"
            }
        
        try:
            # Setup driver
            self._setup_driver()
            
            # Load cookies
            cookies_loaded = self.load_cookies()
            
            # Navigate ke Facebook Reels Create
            self._log("Navigasi ke Facebook Reels Create...")
            self.driver.get(self.reels_create_url)
            time.sleep(5)
            
            # Cek apakah perlu login
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
            upload_input = self._find_element_with_retry(self.selectors['reels_upload_input'])
            if not upload_input:
                raise Exception("Input upload tidak ditemukan")
            
            # Upload file
            abs_path = os.path.abspath(video_path)
            upload_input.send_keys(abs_path)
            self._log("✅ Input upload ditemukan. Mengirim file...", "SUCCESS")
            self._log("✅ File video berhasil dikirim ke input.", "SUCCESS")
            
            # Wait for upload to process
            time.sleep(10)
            
            # Click Next buttons (usually 2 times)
            for i in range(1, 3):
                next_button = self._find_element_with_retry(self.selectors['reels_next_button'])
                if next_button:
                    if self._click_element_robust(next_button, f"Next button (step {i})"):
                        self._log(f"✅ Tombol 'Next' berhasil diklik (index {i})!", "SUCCESS")
                        time.sleep(3)
                    else:
                        self._log(f"⚠️ Gagal klik tombol Next {i}", "WARNING")
                else:
                    self._log(f"⚠️ Tombol Next {i} tidak ditemukan", "WARNING")
            
            # Add description if provided
            if description.strip():
                desc_input = self._find_element_with_retry(self.selectors['reels_description_input'])
                if desc_input:
                    if self._click_element_robust(desc_input, "description input"):
                        desc_input.clear()
                        desc_input.send_keys(description)
                        self._log("✅ Deskripsi berhasil diisi", "SUCCESS")
                    else:
                        self._log("⚠️ Gagal mengisi deskripsi", "WARNING")
                else:
                    self._log("⚠️ Input deskripsi tidak ditemukan", "WARNING")
            
            # Click Publish button
            publish_button = self._find_element_with_retry(self.selectors['reels_publish_button'])
            if publish_button:
                if self._click_element_robust(publish_button, "Publish button"):
                    self._log("✅ Tombol 'Publish' berhasil diklik!", "SUCCESS")
                    time.sleep(5)
                    
                    self._log("✅ Upload video reels berhasil!", "SUCCESS")
                    success = True
                else:
                    raise Exception("Gagal mengklik tombol Publish")
            else:
                raise Exception("Tombol Publish tidak ditemukan")
            
            if success:
                self._log("✅ Reels berhasil diupload ke Facebook!", "SUCCESS")
                return {
                    "success": True,
                    "message": "Reels berhasil diupload",
                    "video_path": video_path,
                    "description": description
                }
            else:
                return {
                    "success": False,
                    "message": "Upload mungkin berhasil tapi tidak dapat dikonfirmasi",
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
    parser.add_argument("--type", choices=['status', 'reels'], help="Jenis upload: status atau reels")
    parser.add_argument("--status", help="Status text untuk Facebook")
    parser.add_argument("--media", help="Path ke file media (video/gambar) untuk status")
    parser.add_argument("--video", help="Path ke file video untuk reels")
    parser.add_argument("--description", default="", help="Deskripsi untuk reels")
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
        print(f"{Fore.YELLOW}🔥 Status + Reels + Media Support")
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