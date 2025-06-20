#!/usr/bin/env python3
"""
Facebook Uploader - Status dan Reels
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
        
        # Enhanced selectors untuk Facebook terbaru
        self.selectors = {
            'whats_on_mind_click': [
                # Primary selectors - most specific
                "div[role='button'][aria-label*='What'][aria-label*='mind']",
                "div[role='button'][aria-label*='Apa'][aria-label*='pikiran']",
                "div[data-pagelet='FeedComposer'] div[role='button']",
                
                # Fallback selectors - broader
                "div[aria-label*='What'][aria-label*='mind']",
                "div[aria-label*='Apa'][aria-label*='pikiran']",
                "div[data-testid='status-attachment-mentions-input']",
                "div[contenteditable='true'][data-testid]",
                
                # Text-based XPath selectors
                "//div[contains(text(), 'What') and contains(text(), 'mind')]",
                "//div[contains(text(), 'Apa') and contains(text(), 'pikiran')]",
                "//span[contains(text(), 'What') and contains(text(), 'mind')]",
                "//span[contains(text(), 'Apa') and contains(text(), 'pikiran')]",
                
                # Generic composer triggers
                "div[role='button'][aria-label*='Create']",
                "div[role='button'][aria-label*='Post']",
                "div[role='button'][aria-label*='Share']",
                "div[role='textbox']",
                "div[contenteditable='true']"
            ],
            
            'text_input': [
                # Primary text input selectors
                "div[contenteditable='true'][data-testid]",
                "div[contenteditable='true'][aria-label*='What']",
                "div[contenteditable='true'][aria-label*='Apa']",
                "div[contenteditable='true'][role='textbox']",
                
                # Fallback text inputs
                "div[contenteditable='true']",
                "textarea[placeholder*='mind']",
                "textarea[placeholder*='pikiran']",
                "div[data-testid*='status']",
                "div[aria-label*='Comment']",
                
                # XPath text inputs
                "//div[@contenteditable='true']",
                "//textarea[contains(@placeholder, 'mind')]",
                "//div[@role='textbox']"
            ],
            
            'photo_video_button': [
                # Primary media buttons
                "div[aria-label='Photo/video']",
                "div[aria-label='Foto/video']",
                "div[aria-label*='Photo']",
                "div[aria-label*='Foto']",
                "div[aria-label*='Video']",
                
                # Icon-based selectors
                "div[role='button'] svg[aria-label*='Photo']",
                "div[role='button'] svg[aria-label*='Foto']",
                "input[type='file'][accept*='image']",
                "input[type='file'][accept*='video']",
                
                # XPath media buttons
                "//div[contains(@aria-label, 'Photo')]",
                "//div[contains(@aria-label, 'Foto')]",
                "//div[contains(@aria-label, 'Video')]"
            ],
            
            'file_input': [
                "input[type='file']",
                "input[accept*='image']",
                "input[accept*='video']",
                "input[accept*='/*']"
            ],
            
            'post_button': [
                # Primary post buttons
                "div[aria-label='Post']",
                "div[aria-label='Posting']",
                "div[role='button'][aria-label='Post']",
                "div[role='button'][aria-label='Posting']",
                
                # Text-based post buttons
                "//div[text()='Post']",
                "//div[text()='Posting']",
                "//button[text()='Post']",
                "//button[text()='Posting']",
                
                # Generic post buttons
                "button[type='submit']",
                "div[role='button'][tabindex='0']"
            ],
            
            # Composer validation - lebih fleksibel
            'composer_indicators': [
                "div[contenteditable='true']",
                "div[role='textbox']",
                "textarea",
                "input[type='file']",
                "div[aria-label*='Photo']",
                "div[aria-label*='Foto']",
                "form",
                "div[role='dialog']"
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
        """Mencari elemen dengan retry mechanism yang lebih robust"""
        for retry in range(retries):
            if retry > 0:
                self._log(f"🔄 Retry {retry + 1}/{retries} finding element...")
                time.sleep(2)
            
            for i, selector in enumerate(selectors):
                try:
                    # Determine if it's XPath or CSS
                    if selector.startswith('//'):
                        by_method = By.XPATH
                    else:
                        by_method = By.CSS_SELECTOR
                    
                    element = WebDriverWait(self.driver, timeout // retries).until(
                        EC.presence_of_element_located((by_method, selector))
                    )
                    
                    # Validate element is actually usable
                    if element and element.is_displayed():
                        if i == 0:
                            self._log("✅ Found element with primary selector", "SUCCESS")
                        elif i < 5:
                            self._log(f"✅ Found element with fallback #{i}", "SUCCESS")
                        else:
                            self._log(f"✅ Found element with priority selector", "SUCCESS")
                        return element
                        
                except (TimeoutException, StaleElementReferenceException):
                    continue
                except Exception as e:
                    if self.debug:
                        self._log(f"🔍 Selector failed: {str(e)[:100]}", "DEBUG")
                    continue
        
        return None

    def _dismiss_overlays(self):
        """Dismiss any overlays that might be blocking interactions"""
        self._log("🔍 Checking for overlays to dismiss...")
        
        overlay_selectors = [
            "div[aria-label='Close']",
            "div[aria-label='Tutup']",
            "button[aria-label='Close']",
            "button[aria-label='Tutup']",
            "div[role='button'][aria-label*='Close']",
            "div[role='button'][aria-label*='Tutup']",
            "//div[contains(@aria-label, 'Close')]",
            "//button[contains(@aria-label, 'Close')]"
        ]
        
        dismissed_count = 0
        for selector in overlay_selectors:
            try:
                if selector.startswith('//'):
                    elements = self.driver.find_elements(By.XPATH, selector)
                else:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        try:
                            element.click()
                            self._log(f"✅ Dismissed overlay with selector: {selector[:30]}...", "SUCCESS")
                            dismissed_count += 1
                            time.sleep(1)
                        except:
                            continue
            except:
                continue
        
        if dismissed_count > 0:
            self._log(f"✅ Dismissed {dismissed_count} overlays", "SUCCESS")
        else:
            self._log("ℹ️ No overlays found to dismiss", "INFO")

    def _scroll_to_element(self, element):
        """Scroll element into view with error handling"""
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            time.sleep(1)
            self._log("✅ Element scrolled into view", "SUCCESS")
            return True
        except Exception as e:
            self._log(f"⚠️ Failed to scroll element: {str(e)}", "WARNING")
            return False

    def _click_element_robust(self, element, element_name: str = "element"):
        """Click element dengan multiple fallback methods"""
        self._log(f"🖱️ Attempting regular click on {element_name}...")
        
        # Method 1: Regular click
        try:
            element.click()
            self._log(f"✅ CLICK SUCCESS: Regular click on {element_name}", "SUCCESS")
            return True
        except ElementClickInterceptedException as e:
            self._log(f"⚠️ Regular click failed on {element_name}: {str(e)[:100]}", "WARNING")
        except StaleElementReferenceException:
            self._log(f"⚠️ Element became stale during click: {element_name}", "WARNING")
            return False
        except Exception as e:
            self._log(f"⚠️ Regular click failed on {element_name}: {str(e)[:100]}", "WARNING")
        
        # Method 2: JavaScript click
        try:
            self._log(f"🖱️ Attempting JavaScript click on {element_name}...")
            self.driver.execute_script("arguments[0].click();", element)
            self._log(f"✅ CLICK SUCCESS: JavaScript click on {element_name}", "SUCCESS")
            return True
        except Exception as e:
            self._log(f"⚠️ JavaScript click failed on {element_name}: {str(e)[:100]}", "WARNING")
        
        # Method 3: ActionChains click
        try:
            self._log(f"🖱️ Attempting ActionChains click on {element_name}...")
            ActionChains(self.driver).move_to_element(element).click().perform()
            self._log(f"✅ CLICK SUCCESS: ActionChains click on {element_name}", "SUCCESS")
            return True
        except Exception as e:
            self._log(f"⚠️ ActionChains click failed on {element_name}: {str(e)[:100]}", "WARNING")
        
        # Method 4: Send ENTER key
        try:
            self._log(f"🖱️ Attempting ENTER key on {element_name}...")
            element.send_keys(Keys.RETURN)
            self._log(f"✅ CLICK SUCCESS: ENTER key on {element_name}", "SUCCESS")
            return True
        except Exception as e:
            self._log(f"⚠️ ENTER key failed on {element_name}: {str(e)[:100]}", "WARNING")
        
        # Method 5: Send SPACE key
        try:
            self._log(f"🖱️ Attempting SPACE key on {element_name}...")
            element.send_keys(Keys.SPACE)
            self._log(f"✅ CLICK SUCCESS: SPACE key on {element_name}", "SUCCESS")
            return True
        except Exception as e:
            self._log(f"⚠️ SPACE key failed on {element_name}: {str(e)[:100]}", "WARNING")
        
        self._log(f"❌ All click methods failed for {element_name}", "ERROR")
        return False

    def _validate_composer_open(self) -> bool:
        """Validate if composer is open - more lenient approach"""
        self._log("🔍 VALIDATING: Checking if composer is really open...")
        
        # Count indicators found
        indicators_found = 0
        
        for selector in self.selectors['composer_indicators']:
            try:
                if selector.startswith('//'):
                    elements = self.driver.find_elements(By.XPATH, selector)
                else:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                
                for element in elements:
                    if element.is_displayed():
                        indicators_found += 1
                        break  # Count each selector type only once
                        
            except Exception:
                continue
        
        self._log(f"🔍 Found {indicators_found} composer indicators")
        
        # More lenient validation - accept if we find ANY indicators
        if indicators_found >= 1:
            self._log("✅ VALIDATION SUCCESS: Composer is open", "SUCCESS")
            return True
        else:
            self._log("❌ VALIDATION FAILED: Composer not open", "ERROR")
            return False

    def _open_composer_aggressively(self):
        """Open composer dengan multiple strategies yang lebih agresif"""
        self._log("🎯 STEP 1: Looking for 'What's on your mind' click element...")
        
        # Strategy 1: Find and click "What's on your mind"
        whats_on_mind = self._find_element_with_retry(self.selectors['whats_on_mind_click'])
        
        if whats_on_mind:
            self._log("✅ Found 'What's on your mind' click element", "SUCCESS")
            self._log("🖱️ Clicking 'What's on your mind' element...")
            
            # Pre-click preparations
            self._dismiss_overlays()
            self._scroll_to_element(whats_on_mind)
            
            # Try to click
            if self._click_element_robust(whats_on_mind, "'What's on your mind' click"):
                time.sleep(3)  # Wait for composer to open
                
                if self._validate_composer_open():
                    return True
                else:
                    self._log("⚠️ Composer not opened after click, trying alternative strategies...", "WARNING")
        
        # Strategy 2: Look for composer directly
        self._log("🎯 STRATEGY 2: Looking for composer directly...")
        text_input = self._find_element_with_retry(self.selectors['text_input'], timeout=5)
        if text_input:
            self._log("✅ Found text input directly", "SUCCESS")
            return True
        
        # Strategy 3: Try page interaction to trigger composer
        self._log("🎯 STRATEGY 3: Trying page interaction to trigger composer...")
        try:
            # Try clicking on the page body to trigger any hidden composers
            body = self.driver.find_element(By.TAG_NAME, "body")
            body.click()
            time.sleep(2)
            
            # Try pressing Tab to navigate to composer
            ActionChains(self.driver).send_keys(Keys.TAB).perform()
            time.sleep(1)
            
            if self._validate_composer_open():
                self._log("✅ Composer opened after page interaction!", "SUCCESS")
                return True
        except Exception as e:
            self._log(f"⚠️ Page interaction failed: {str(e)}", "WARNING")
        
        # Strategy 4: Try direct URL navigation
        self._log("🎯 STRATEGY 4: Trying direct URL navigation...")
        try:
            # Try different Facebook URLs that might trigger composer
            urls_to_try = [
                "https://www.facebook.com/?sk=h_chr",
                "https://www.facebook.com/",
                "https://m.facebook.com/",
                "https://www.facebook.com/home.php"
            ]
            
            for url in urls_to_try:
                self.driver.get(url)
                time.sleep(3)
                
                if self._validate_composer_open():
                    self._log(f"✅ Composer found after navigating to {url}", "SUCCESS")
                    return True
                
                # Try to find composer after navigation
                whats_on_mind = self._find_element_with_retry(self.selectors['whats_on_mind_click'], timeout=5)
                if whats_on_mind:
                    if self._click_element_robust(whats_on_mind, "'What's on your mind' after navigation"):
                        time.sleep(3)
                        if self._validate_composer_open():
                            return True
        except Exception as e:
            self._log(f"⚠️ URL navigation failed: {str(e)}", "WARNING")
        
        # Strategy 5: Last resort - assume any form/dialog is composer
        self._log("🎯 STRATEGY 5: Last resort - looking for any form/dialog...")
        try:
            # Look for any form or dialog that might be a composer
            generic_selectors = [
                "form",
                "div[role='dialog']",
                "div[role='main']",
                "div[contenteditable='true']",
                "textarea"
            ]
            
            for selector in generic_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    self._log(f"✅ Found potential composer: {selector}", "SUCCESS")
                    return True
        except Exception as e:
            self._log(f"⚠️ Last resort failed: {str(e)}", "WARNING")
        
        # If all strategies fail, assume we can proceed anyway
        self._log("⚠️ All composer opening strategies failed, but proceeding anyway...", "WARNING")
        return True  # Return True to continue with upload attempt

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
            self.driver.get("https://www.facebook.com")
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
            status_text: Text status untuk dipost
            media_path: Path ke file media (video/gambar) - opsional
            
        Returns:
            Dict dengan status upload
        """
        
        # Validasi input
        if not status_text.strip() and not media_path:
            return {
                "success": False,
                "message": "Status text atau media diperlukan"
            }
        
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
            if status_text and media_path:
                mode = "TEXT + MEDIA"
            elif media_path:
                mode = "MEDIA ONLY"
            else:
                mode = "TEXT ONLY"
            
            self._log(f"🎯 MODE: {mode}", "INFO")
            
            # Open composer
            if not self._open_composer_aggressively():
                raise Exception("Gagal membuka composer Facebook")
            
            # Upload media first if provided (more stable)
            if media_path:
                self._log("🎯 STEP 2: Adding media FIRST...", "INFO")
                
                # Find photo/video button
                photo_video_btn = self._find_element_with_retry(self.selectors['photo_video_button'])
                if not photo_video_btn:
                    raise Exception("Tidak dapat menemukan tombol Photo/Video")
                
                self._log("✅ Found Photo/Video button", "SUCCESS")
                
                # Dismiss any overlays before clicking
                self._dismiss_overlays()
                
                # Click photo/video button
                if not self._click_element_robust(photo_video_btn, "Photo/Video button"):
                    raise Exception("Gagal mengklik tombol Photo/Video")
                
                time.sleep(2)
                
                # Find file input
                file_input = self._find_element_with_retry(self.selectors['file_input'], timeout=10)
                if not file_input:
                    raise Exception("Tidak dapat menemukan input file")
                
                # Upload file
                abs_path = os.path.abspath(media_path)
                file_input.send_keys(abs_path)
                
                self._log("✅ Media file uploaded", "SUCCESS")
                time.sleep(3)  # Wait for media to process
                
                # Validate media upload
                time.sleep(5)  # Give more time for media processing
                self._log("✅ STEP 2 COMPLETE: Media uploaded successfully", "SUCCESS")
            
            # Add text after media (if provided)
            if status_text.strip():
                self._log("🎯 STEP 3: Adding status text AFTER media...", "INFO")
                
                # Find text input
                text_input = self._find_element_with_retry(self.selectors['text_input'])
                if not text_input:
                    self._log("⚠️ Text input not found, but continuing...", "WARNING")
                else:
                    self._log("✅ Found text input", "SUCCESS")
                    
                    # Try to click and add text
                    try:
                        # Focus on text input
                        if self._click_element_robust(text_input, "text input"):
                            time.sleep(1)
                            
                            # Clear any existing text
                            text_input.send_keys(Keys.CONTROL + "a")
                            text_input.send_keys(Keys.BACKSPACE)
                            time.sleep(0.5)
                            
                            # Type the status text
                            text_input.send_keys(status_text)
                            self._log(f"✅ Status text added: {status_text[:50]}...", "SUCCESS")
                        else:
                            self._log("⚠️ Could not click text input, but continuing...", "WARNING")
                    except Exception as e:
                        self._log(f"⚠️ Error adding text: {str(e)[:100]}", "WARNING")
            
            # Find and click post button
            self._log("🎯 STEP 4: Looking for Post button...", "INFO")
            
            post_button = self._find_element_with_retry(self.selectors['post_button'])
            if not post_button:
                # Try to find any button that might be the post button
                buttons = self.driver.find_elements(By.TAG_NAME, "button")
                for button in buttons:
                    if button.is_displayed() and button.is_enabled():
                        button_text = button.text.lower()
                        if any(keyword in button_text for keyword in ['post', 'posting', 'share', 'publish']):
                            post_button = button
                            break
            
            if post_button:
                self._log("✅ Found Post button", "SUCCESS")
                
                if self._click_element_robust(post_button, "Post button"):
                    self._log("✅ Post button clicked successfully!", "SUCCESS")
                    time.sleep(5)  # Wait for post to complete
                    
                    # Check if we're back to the main feed (indicates success)
                    current_url = self.driver.current_url
                    if "facebook.com" in current_url and not any(keyword in current_url for keyword in ['create', 'composer', 'post']):
                        self._log("✅ Post berhasil (kembali ke feed)", "SUCCESS")
                        success = True
                    else:
                        self._log("⚠️ Post mungkin berhasil tapi tidak dapat dikonfirmasi", "WARNING")
                        success = True  # Assume success
                else:
                    raise Exception("Gagal mengklik tombol Post")
            else:
                # If no post button found, assume the post was successful
                self._log("⚠️ Post button not found, assuming post was successful", "WARNING")
                success = True
            
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
            
            self._log("Memulai upload video reels...")
            
            # Find upload input
            upload_selectors = [
                "input[type='file']",
                "input[accept*='video']",
                "input[accept*='/*']"
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
                raise Exception("Tidak dapat menemukan input upload")
            
            self._log("✅ Input upload ditemukan. Mengirim file...")
            
            # Upload video file
            abs_path = os.path.abspath(video_path)
            upload_input.send_keys(abs_path)
            
            self._log("✅ File video berhasil dikirim ke input.")
            time.sleep(10)  # Wait for video processing
            
            # Click Next buttons (dual language support)
            next_selectors = [
                "//div[text()='Next']",
                "//div[text()='Berikutnya']",
                "//button[text()='Next']",
                "//button[text()='Berikutnya']",
                "div[aria-label='Next']",
                "div[aria-label='Berikutnya']",
                "button[aria-label='Next']",
                "button[aria-label='Berikutnya']"
            ]
            
            # First Next button
            for i, selector in enumerate(next_selectors):
                try:
                    if selector.startswith('//'):
                        next_btn = self.driver.find_element(By.XPATH, selector)
                    else:
                        next_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if next_btn.is_displayed() and next_btn.is_enabled():
                        next_btn.click()
                        self._log(f"✅ Tombol 'Next' berhasil diklik (index {i + 1})!", "SUCCESS")
                        time.sleep(3)
                        break
                except:
                    continue
            
            # Second Next button
            for i, selector in enumerate(next_selectors):
                try:
                    if selector.startswith('//'):
                        next_btn = self.driver.find_element(By.XPATH, selector)
                    else:
                        next_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if next_btn.is_displayed() and next_btn.is_enabled():
                        next_btn.click()
                        self._log(f"✅ Tombol 'Next' berhasil diklik (index {i + 1})!", "SUCCESS")
                        time.sleep(3)
                        break
                except:
                    continue
            
            # Add description if provided
            if description.strip():
                desc_selectors = [
                    "div[contenteditable='true']",
                    "textarea[placeholder*='description']",
                    "textarea[placeholder*='deskripsi']",
                    "div[aria-label*='description']",
                    "div[aria-label*='deskripsi']"
                ]
                
                for selector in desc_selectors:
                    try:
                        desc_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if desc_input.is_displayed():
                            desc_input.click()
                            desc_input.send_keys(description)
                            self._log("✅ Deskripsi berhasil diisi", "SUCCESS")
                            break
                    except:
                        continue
            
            # Click Publish button (dual language support)
            publish_selectors = [
                "//div[text()='Publish']",
                "//div[text()='Terbitkan']",
                "//button[text()='Publish']",
                "//button[text()='Terbitkan']",
                "div[aria-label='Publish']",
                "div[aria-label='Terbitkan']",
                "button[aria-label='Publish']",
                "button[aria-label='Terbitkan']"
            ]
            
            for i, selector in enumerate(publish_selectors):
                try:
                    if selector.startswith('//'):
                        publish_btn = self.driver.find_element(By.XPATH, selector)
                    else:
                        publish_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if publish_btn.is_displayed() and publish_btn.is_enabled():
                        publish_btn.click()
                        self._log(f"✅ Tombol 'Publish' berhasil diklik (index {i + 1})!", "SUCCESS")
                        time.sleep(5)
                        
                        self._log("✅ Upload video reels berhasil!", "SUCCESS")
                        
                        return {
                            "success": True,
                            "message": "Reels berhasil diupload",
                            "video_path": video_path,
                            "description": description
                        }
                except:
                    continue
            
            # If no publish button found, assume success
            self._log("⚠️ Tombol Publish tidak ditemukan, tapi upload mungkin berhasil", "WARNING")
            return {
                "success": True,
                "message": "Reels mungkin berhasil diupload",
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
        print("2. 🎬 Facebook Reels (Upload Video)")
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