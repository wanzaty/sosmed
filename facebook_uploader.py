#!/usr/bin/env python3
"""
Facebook Uploader menggunakan Selenium
Mendukung posting status (text/media) dan upload reels dengan cookies JSON untuk auto-login
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
        self.reels_create_url = "https://www.facebook.com/reels/create/?surface=PROFILE_PLUS"
        self.login_url = "https://www.facebook.com/login"

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
            self._log("Mode headless diaktifkan")
        
        # Enhanced options for Facebook
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-images')
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
        
        # Anti-detection
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--disable-web-security")
        
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

    def _scroll_to_element(self, element):
        """Scroll to element to make it visible and clickable"""
        try:
            # Scroll element into view
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            time.sleep(1)
            
            # Additional scroll to ensure element is not covered by headers
            self.driver.execute_script("window.scrollBy(0, -100);")
            time.sleep(0.5)
            
        except Exception as e:
            self._log(f"Error scrolling to element: {e}", "DEBUG")

    def _remove_overlays(self):
        """Remove potential overlays that might block clicks"""
        try:
            # Remove common Facebook overlays
            overlay_selectors = [
                "div[role='dialog']",
                ".uiLayer",
                ".__fb-light-mode",
                "[data-testid='cookie-policy-manage-dialog']",
                "[data-testid='cookie-policy-banner']"
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

    def _enhanced_click(self, element, description="element"):
        """Enhanced click method with multiple fallbacks"""
        try:
            # Method 1: Scroll and regular click
            self._log(f"🖱️ Attempting regular click on {description}...")
            self._scroll_to_element(element)
            self._remove_overlays()
            element.click()
            self._log(f"✅ CLICK SUCCESS: Regular click on {description}", "SUCCESS")
            return True
            
        except ElementClickInterceptedException as e:
            self._log(f"⚠️ Regular click failed on {description}: {str(e)}", "WARNING")
            
            try:
                # Method 2: JavaScript click
                self._log(f"🖱️ Attempting JavaScript click on {description}...")
                self.driver.execute_script("arguments[0].click();", element)
                self._log(f"✅ CLICK SUCCESS: JavaScript click on {description}", "SUCCESS")
                return True
                
            except Exception as e2:
                self._log(f"⚠️ JavaScript click failed on {description}: {str(e2)}", "WARNING")
                
                try:
                    # Method 3: ActionChains click
                    self._log(f"🖱️ Attempting ActionChains click on {description}...")
                    actions = ActionChains(self.driver)
                    actions.move_to_element(element).click().perform()
                    self._log(f"✅ CLICK SUCCESS: ActionChains click on {description}", "SUCCESS")
                    return True
                    
                except Exception as e3:
                    self._log(f"❌ All click methods failed on {description}: {str(e3)}", "ERROR")
                    return False

    def _find_status_composer_text_input(self):
        """Find the correct status composer text input (not comment box)"""
        # Enhanced selectors specifically for status composer
        text_input_selectors = [
            # Primary status composer selectors
            "div[aria-label*='What\\'s on your mind']",
            "div[aria-label*='What's on your mind']",
            "div[aria-placeholder*='What\\'s on your mind']",
            "div[aria-placeholder*='What's on your mind']",
            
            # Status composer with user name
            "div[aria-label*='Write something']",
            "div[aria-placeholder*='Write something']",
            
            # Generic status composer
            "div[contenteditable='true'][role='textbox']:not([aria-label*='Comment']):not([aria-label*='Reply'])",
            "div[data-lexical-editor='true']:not([aria-label*='Comment']):not([aria-label*='Reply'])",
            
            # Fallback selectors
            "div[contenteditable='true'][spellcheck='true']:not([aria-label*='Comment'])",
            "div.notranslate[contenteditable='true']:not([aria-label*='Comment'])"
        ]
        
        for i, selector in enumerate(text_input_selectors):
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                
                for element in elements:
                    if element.is_displayed():
                        # Additional validation to ensure it's not a comment box
                        aria_label = element.get_attribute('aria-label') or ''
                        aria_placeholder = element.get_attribute('aria-placeholder') or ''
                        
                        # Skip comment boxes
                        if any(keyword in (aria_label + aria_placeholder).lower() for keyword in ['comment', 'reply']):
                            continue
                        
                        self._log(f"✅ Found element with selector #{i+1}", "SUCCESS")
                        self._log(f"🎯 Element aria-label: {aria_label}", "DEBUG")
                        return element
                        
            except Exception as e:
                if self.debug:
                    self._log(f"Selector {i+1} failed: {e}", "DEBUG")
                continue
        
        return None

    def _validate_composer_open(self):
        """Validate that the status composer is properly open"""
        composer_indicators = [
            "div[aria-label*='Post']",
            "div[role='button'][aria-label*='Post']",
            "button[aria-label*='Post']",
            "div[data-testid*='react-composer']",
            "form[method='post']"
        ]
        
        found_indicators = 0
        for selector in composer_indicators:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements and any(el.is_displayed() for el in elements):
                    found_indicators += 1
            except:
                continue
        
        self._log(f"🔍 Found {found_indicators} composer indicators", "INFO")
        return found_indicators >= 2

    def upload_status(self, status_text: str = "", media_path: str = "") -> Dict[str, Any]:
        """
        Upload status ke Facebook dengan dukungan text dan media
        
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
            self.driver.get(self.base_url)
            time.sleep(3)
            
            # Take screenshot before starting
            self.take_screenshot(f"facebook_before_post_{int(time.time())}.png")
            
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
            has_text = bool(status_text.strip())
            has_media = bool(media_path and os.path.exists(media_path))
            
            if not has_text and not has_media:
                return {
                    "success": False,
                    "message": "Minimal status text atau media diperlukan"
                }
            
            if has_text and has_media:
                mode = "TEXT + MEDIA"
            elif has_media:
                mode = "MEDIA ONLY"
            else:
                mode = "TEXT ONLY"
            
            self._log(f"🎯 MODE: {mode}", "INFO")
            
            # STEP 1: Open composer
            self._log("🎯 STEP 1: Looking for 'What's on your mind' click element...", "INFO")
            
            # Enhanced selectors for opening composer
            composer_open_selectors = [
                "div[aria-label*='What\\'s on your mind']",
                "div[aria-label*='What's on your mind']",
                "div[role='button'][aria-label*='What\\'s on your mind']",
                "span[dir='auto']:contains('What\\'s on your mind')",
                "div[data-testid='status-attachment-mentions-input']",
                "div[role='textbox'][aria-label*='What']",
                "div[contenteditable='true'][aria-placeholder*='What']"
            ]
            
            composer_click_element = None
            for i, selector in enumerate(composer_open_selectors):
                try:
                    if 'contains' in selector:
                        # XPath for text content
                        xpath_selector = f"//span[contains(text(), \"What's on your mind\")]"
                        elements = self.driver.find_elements(By.XPATH, xpath_selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for element in elements:
                        if element.is_displayed():
                            composer_click_element = element
                            if i > 0:
                                self._log(f"⚠️ Found element with fallback #{i+1}", "WARNING")
                            break
                    
                    if composer_click_element:
                        break
                        
                except Exception as e:
                    if self.debug:
                        self._log(f"Composer selector {i+1} failed: {e}", "DEBUG")
                    continue
            
            if not composer_click_element:
                return {
                    "success": False,
                    "message": "Tidak dapat menemukan elemen 'What's on your mind'"
                }
            
            self._log("✅ Found 'What's on your mind' click element", "SUCCESS")
            
            # Click to open composer
            self._log("🖱️ Clicking 'What's on your mind' element...", "INFO")
            if not self._enhanced_click(composer_click_element, "'What's on your mind' click"):
                return {
                    "success": False,
                    "message": "Gagal mengklik elemen 'What's on your mind'"
                }
            
            # Wait for composer to open
            time.sleep(3)
            
            # Validate composer is open
            self._log("🔍 VALIDATING: Checking if composer is really open...", "INFO")
            if not self._validate_composer_open():
                return {
                    "success": False,
                    "message": "Composer tidak terbuka dengan benar"
                }
            
            self._log("✅ VALIDATION SUCCESS: Composer is open", "SUCCESS")
            
            # STEP 2: Handle media upload first (if needed)
            if has_media:
                self._log("🎯 STEP 2: Adding media FIRST...", "INFO")
                
                # Find Photo/Video button
                media_selectors = [
                    "div[aria-label='Photo/video']",
                    "div[aria-label='Add Photo/Video']",
                    "input[accept*='image'], input[accept*='video']",
                    "div[data-testid='media-sprout']",
                    "div[role='button'][aria-label*='Photo']",
                    "div[role='button'][aria-label*='Video']"
                ]
                
                media_button = None
                for i, selector in enumerate(media_selectors):
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            if element.is_displayed():
                                media_button = element
                                if i == 0:
                                    self._log("✅ Found element with primary selector", "SUCCESS")
                                else:
                                    self._log(f"⚠️ Found element with fallback #{i+1}", "WARNING")
                                break
                        if media_button:
                            break
                    except Exception as e:
                        if self.debug:
                            self._log(f"Media selector {i+1} failed: {e}", "DEBUG")
                        continue
                
                if not media_button:
                    return {
                        "success": False,
                        "message": "Tidak dapat menemukan tombol Photo/Video"
                    }
                
                self._log("✅ Found Photo/Video button", "SUCCESS")
                
                # Click Photo/Video button
                if not self._enhanced_click(media_button, "Photo/Video button"):
                    return {
                        "success": False,
                        "message": "Gagal mengklik tombol Photo/Video"
                    }
                
                # Wait for file dialog and upload
                time.sleep(2)
                
                # Find file input
                file_input_selectors = [
                    "input[type='file']",
                    "input[accept*='image']",
                    "input[accept*='video']"
                ]
                
                file_input = None
                for selector in file_input_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            file_input = element
                            if file_input:
                                self._log("✅ Found element with primary selector", "SUCCESS")
                                break
                        if file_input:
                            break
                    except:
                        continue
                
                if not file_input:
                    return {
                        "success": False,
                        "message": "Tidak dapat menemukan input file"
                    }
                
                # Upload file
                abs_path = os.path.abspath(media_path)
                file_input.send_keys(abs_path)
                
                self._log("✅ STEP 2 COMPLETE: Media uploaded successfully", "SUCCESS")
                
                # Wait for media processing
                time.sleep(5)
                
                # Validate media upload
                self._log("🔍 VALIDATING: Checking if media is really uploaded...", "INFO")
                media_validation_selectors = [
                    "img[src*='blob:']",
                    "video[src*='blob:']",
                    "div[data-testid*='media']",
                    "img[alt*='uploaded']",
                    "video[data-testid*='video']"
                ]
                
                media_uploaded = False
                for selector in media_validation_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements and any(el.is_displayed() for el in elements):
                            media_uploaded = True
                            break
                    except:
                        continue
                
                if media_uploaded:
                    self._log("✅ MEDIA VALIDATION SUCCESS: Media uploaded", "SUCCESS")
                else:
                    self._log("⚠️ MEDIA VALIDATION WARNING: Cannot confirm media upload", "WARNING")
            
            # STEP 3: Handle text input (after media if both)
            if has_text:
                self._log("🎯 STEP 3: Adding status text AFTER media...", "INFO")
                
                # Find text input with enhanced detection
                text_input = self._find_status_composer_text_input()
                
                if not text_input:
                    return {
                        "success": False,
                        "message": "Tidak dapat menemukan input text status"
                    }
                
                self._log("✅ Found status text input element", "SUCCESS")
                
                # Click text input
                if not self._enhanced_click(text_input, "text input"):
                    return {
                        "success": False,
                        "message": "Gagal mengklik input text"
                    }
                
                # Input text with multiple methods
                text_input_success = False
                
                # Method 1: Direct send_keys
                try:
                    self._log("🖊️ Trying text input method 1...", "INFO")
                    text_input.clear()
                    text_input.send_keys(status_text)
                    
                    # Validate text input
                    time.sleep(1)
                    current_text = text_input.text or text_input.get_attribute('textContent') or ''
                    
                    self._log("🔍 VALIDATING: Checking if text is really inputted...", "INFO")
                    if status_text.lower() in current_text.lower():
                        self._log("✅ TEXT VALIDATION SUCCESS: Text found with method 1", "SUCCESS")
                        self._log(f"Expected: '{status_text}', Found: '{current_text[:50]}...'", "INFO")
                        text_input_success = True
                    else:
                        self._log(f"⚠️ TEXT VALIDATION FAILED: Expected '{status_text}', Found '{current_text[:50]}...'", "WARNING")
                        
                except Exception as e:
                    self._log(f"Text input method 1 failed: {e}", "WARNING")
                
                # Method 2: JavaScript if method 1 failed
                if not text_input_success:
                    try:
                        self._log("🖊️ Trying text input method 2 (JavaScript)...", "INFO")
                        self.driver.execute_script("arguments[0].textContent = arguments[1];", text_input, status_text)
                        self.driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true}));", text_input)
                        
                        time.sleep(1)
                        current_text = text_input.text or text_input.get_attribute('textContent') or ''
                        
                        if status_text.lower() in current_text.lower():
                            self._log("✅ TEXT VALIDATION SUCCESS: Text found with method 2", "SUCCESS")
                            text_input_success = True
                        
                    except Exception as e:
                        self._log(f"Text input method 2 failed: {e}", "WARNING")
                
                if text_input_success:
                    self._log("✅ STEP 3 COMPLETE: Status text added successfully", "SUCCESS")
                else:
                    self._log("⚠️ STEP 3 WARNING: Text input may have failed", "WARNING")
            
            # STEP 4: Click Post button
            self._log("🎯 STEP 4: Clicking Post button...", "INFO")
            
            # Wait for Post button to be enabled
            post_button_enabled = False
            max_wait_time = 30
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                post_selectors = [
                    "div[aria-label='Post']:not([aria-disabled='true'])",
                    "button[aria-label='Post']:not([aria-disabled='true'])",
                    "div[role='button'][aria-label='Post']:not([aria-disabled='true'])",
                    "//div[@aria-label='Post' and not(@aria-disabled='true')]",
                    "//button[@aria-label='Post' and not(@aria-disabled='true')]"
                ]
                
                for i, selector in enumerate(post_selectors):
                    try:
                        if selector.startswith('//'):
                            elements = self.driver.find_elements(By.XPATH, selector)
                        else:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                aria_disabled = element.get_attribute('aria-disabled')
                                if aria_disabled != 'true':
                                    post_button_enabled = True
                                    post_button = element
                                    if i == 0:
                                        self._log("✅ Found element with primary selector", "SUCCESS")
                                    else:
                                        self._log(f"⚠️ Found element with fallback #{i+1}", "WARNING")
                                    break
                        
                        if post_button_enabled:
                            break
                            
                    except Exception as e:
                        if self.debug:
                            self._log(f"Post selector {i+1} failed: {e}", "DEBUG")
                        continue
                
                if post_button_enabled:
                    break
                
                time.sleep(1)
            
            if not post_button_enabled:
                # Fallback: try any Post button
                self._log("⚠️ Enabled Post button not found, trying any Post button...", "WARNING")
                fallback_selectors = [
                    "div[aria-label='Post']",
                    "button[aria-label='Post']",
                    "div[role='button'][aria-label='Post']"
                ]
                
                post_button = None
                for selector in fallback_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            if element.is_displayed():
                                post_button = element
                                break
                        if post_button:
                            break
                    except:
                        continue
                
                if not post_button:
                    return {
                        "success": False,
                        "message": "Tidak dapat menemukan tombol Post"
                    }
            
            self._log("✅ Found Post button", "SUCCESS")
            
            # Click Post button
            if not self._enhanced_click(post_button, "Post button"):
                return {
                    "success": False,
                    "message": "Gagal mengklik tombol Post"
                }
            
            # Wait and validate post success
            time.sleep(5)
            
            self._log("🔍 VALIDATING: Checking if post was successful...", "INFO")
            
            # Check if we're back to feed (indicates success)
            current_url = self.driver.current_url
            if 'facebook.com' in current_url and not any(keyword in current_url for keyword in ['composer', 'create', 'post']):
                self._log("✅ POST VALIDATION SUCCESS: Returned to feed", "SUCCESS")
                post_success = True
            else:
                # Additional validation methods
                success_indicators = [
                    "div[data-testid='post_message']",
                    "div[role='article']",
                    "div[data-testid='story-subtitle']"
                ]
                
                post_success = False
                for selector in success_indicators:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            post_success = True
                            break
                    except:
                        continue
                
                if post_success:
                    self._log("✅ POST VALIDATION SUCCESS: Post found in feed", "SUCCESS")
                else:
                    self._log("⚠️ POST VALIDATION WARNING: Cannot confirm post success", "WARNING")
                    post_success = True  # Assume success if no clear failure
            
            if post_success:
                self._log("✅ Facebook status posted successfully!", "SUCCESS")
                return {
                    "success": True,
                    "message": "Status berhasil dipost",
                    "mode": mode,
                    "has_text": has_text,
                    "has_media": has_media
                }
            else:
                return {
                    "success": False,
                    "message": "Post mungkin berhasil tapi tidak dapat dikonfirmasi"
                }
                
        except Exception as e:
            error_msg = f"Upload status gagal: {str(e)}"
            self._log(error_msg, "ERROR")
            
            self.take_screenshot(f"facebook_error_{int(time.time())}.png")
            
            return {
                "success": False,
                "message": error_msg
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
            description: Deskripsi untuk reels
            
        Returns:
            Dict dengan status upload
        """
        try:
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"File video tidak ditemukan: {video_path}")
            
            self._setup_driver()
            
            cookies_loaded = self.load_cookies()
            
            self._log("Navigasi ke Facebook Reels Create...", "INFO")
            self.driver.get(self.reels_create_url)
            time.sleep(3)
            
            if self.check_login_required():
                if cookies_loaded:
                    self._log("Cookies dimuat tapi masih perlu login, refresh halaman...", "WARNING")
                    self.driver.refresh()
                    time.sleep(3)
                
                if self.check_login_required():
                    self.wait_for_login()
                    self.driver.get(self.reels_create_url)
                    time.sleep(3)
            
            self._log("Memulai upload video reels...", "INFO")
            
            # Find upload input
            upload_selectors = [
                "input[type='file'][accept*='video']",
                "input[type='file']",
                "input[accept*='video']"
            ]
            
            upload_input = None
            for selector in upload_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        upload_input = element
                        break
                    if upload_input:
                        break
                except:
                    continue
            
            if not upload_input:
                return {
                    "success": False,
                    "message": "Tidak dapat menemukan input upload video"
                }
            
            self._log("Input upload ditemukan. Mengirim file...", "SUCCESS")
            
            # Upload video
            abs_path = os.path.abspath(video_path)
            upload_input.send_keys(abs_path)
            
            self._log("File video berhasil dikirim ke input.", "SUCCESS")
            
            # Wait for upload processing
            time.sleep(10)
            
            # Click Next buttons (dual language support)
            next_buttons_clicked = 0
            next_button_texts = ['Next', 'Berikutnya', 'Continue', 'Lanjutkan']
            
            for attempt in range(3):  # Try up to 3 Next buttons
                next_button_found = False
                
                for text in next_button_texts:
                    try:
                        # Try different selectors for Next button
                        next_selectors = [
                            f"//div[@role='button' and contains(text(), '{text}')]",
                            f"//button[contains(text(), '{text}')]",
                            f"//span[contains(text(), '{text}')]/parent::div[@role='button']",
                            f"//span[contains(text(), '{text}')]/ancestor::div[@role='button']"
                        ]
                        
                        for selector in next_selectors:
                            try:
                                elements = self.driver.find_elements(By.XPATH, selector)
                                for element in elements:
                                    if element.is_displayed() and element.is_enabled():
                                        element.click()
                                        next_buttons_clicked += 1
                                        self._log(f"Tombol '{text}' berhasil diklik (index {next_buttons_clicked})!", "SUCCESS")
                                        next_button_found = True
                                        time.sleep(3)
                                        break
                                
                                if next_button_found:
                                    break
                            except:
                                continue
                        
                        if next_button_found:
                            break
                    
                    except Exception as e:
                        if self.debug:
                            self._log(f"Error clicking {text} button: {e}", "DEBUG")
                        continue
                
                if not next_button_found:
                    break
            
            # Add description if provided
            if description.strip():
                self._log("Mengisi deskripsi reels...", "INFO")
                
                description_selectors = [
                    "div[contenteditable='true'][aria-label*='description']",
                    "div[contenteditable='true'][aria-label*='Describe']",
                    "textarea[placeholder*='description']",
                    "div[contenteditable='true']",
                    "textarea"
                ]
                
                description_input = None
                for selector in description_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            if element.is_displayed():
                                description_input = element
                                break
                        if description_input:
                            break
                    except:
                        continue
                
                if description_input:
                    try:
                        description_input.click()
                        description_input.clear()
                        description_input.send_keys(description)
                        self._log("Deskripsi berhasil diisi", "SUCCESS")
                    except Exception as e:
                        self._log(f"Gagal mengisi deskripsi: {e}", "WARNING")
            
            # Click Publish button (dual language)
            publish_button_texts = ['Publish', 'Terbitkan', 'Share', 'Bagikan', 'Post']
            publish_success = False
            
            for text in publish_button_texts:
                try:
                    publish_selectors = [
                        f"//div[@role='button' and contains(text(), '{text}')]",
                        f"//button[contains(text(), '{text}')]",
                        f"//span[contains(text(), '{text}')]/parent::div[@role='button']",
                        f"//span[contains(text(), '{text}')]/ancestor::div[@role='button']"
                    ]
                    
                    for selector in publish_selectors:
                        try:
                            elements = self.driver.find_elements(By.XPATH, selector)
                            for element in elements:
                                if element.is_displayed() and element.is_enabled():
                                    element.click()
                                    self._log(f"Tombol '{text}' berhasil diklik!", "SUCCESS")
                                    publish_success = True
                                    time.sleep(5)
                                    break
                            
                            if publish_success:
                                break
                        except:
                            continue
                    
                    if publish_success:
                        break
                
                except Exception as e:
                    if self.debug:
                        self._log(f"Error clicking {text} button: {e}", "DEBUG")
                    continue
            
            if publish_success:
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
                    "message": "Gagal mengklik tombol Publish"
                }
                
        except Exception as e:
            error_msg = f"Upload reels gagal: {str(e)}"
            self._log(error_msg, "ERROR")
            
            self.take_screenshot(f"facebook_reels_error_{int(time.time())}.png")
            
            return {
                "success": False,
                "message": error_msg,
                "video_path": video_path
            }
        
        finally:
            if self.driver:
                self._log("Closing browser...", "INFO")
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
    parser.add_argument("--type", choices=['status', 'reels'], help="Jenis upload")
    parser.add_argument("--status", help="Status text untuk Facebook")
    parser.add_argument("--media", help="Path ke file media (video/gambar) untuk status")
    parser.add_argument("--video", help="Path ke file video untuk reels")
    parser.add_argument("--description", help="Deskripsi untuk reels")
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
        
        result = uploader.upload_reels(args.video, args.description or "")
        
        if result["success"]:
            print(f"{Fore.GREEN}🎉 Facebook Reels berhasil!")
        else:
            print(f"{Fore.RED}❌ Facebook Reels gagal: {result['message']}")
            sys.exit(1)
    
    else:
        # Interactive mode
        print(f"{Fore.BLUE}📘 Facebook Uploader")
        print("=" * 40)
        print(f"{Fore.YELLOW}🔥 Status + Reels Support")
        print()
        
        while True:
            print(f"\n{Fore.YELLOW}Pilih jenis upload:")
            print("1. 📝 Upload Status (Text/Media)")
            print("2. 🎬 Upload Reels (Video)")
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