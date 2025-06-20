#!/usr/bin/env python3
"""
Facebook Uploader untuk Status dan Reels menggunakan Selenium
Mendukung cookies JSON untuk auto-login dan upload berbagai jenis konten
Unified approach untuk text dan media menggunakan selector yang sama
URUTAN: Text dahulu, lalu Media
"""

import os
import sys
import json
import time
import random
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
        self.home_url = "https://www.facebook.com"
        self.reels_url = "https://www.facebook.com/reel/create"
        self.login_url = "https://www.facebook.com/login"
        
        # 🎯 OPTIMIZED SELECTORS - Berdasarkan gambar yang diberikan
        self.selectors = {
            # ✅ "What's on your mind" detection - DUAL LANGUAGE
            'whats_on_mind_text': [
                "//*[contains(text(), \"What's on your mind\")]",
                "//*[contains(text(), \"Apa yang Anda pikirkan\")]",  # Indonesian
                "//*[contains(text(), \"What's on your mind?\")]"
            ],
            
            # ✅ Text input - UNIFIED untuk text dan media
            'status_text_input': [
                # Berdasarkan gambar: input text yang sama untuk text dan media
                "div[contenteditable='true'][data-testid*='status']",
                "div[contenteditable='true'][aria-label*='What']",
                "div[contenteditable='true'][role='textbox']",
                "//*[contains(text(), \"What's on your mind\")]/following::div[@contenteditable='true'][1]",
                "//*[contains(text(), \"Apa yang Anda pikirkan\")]/following::div[@contenteditable='true'][1]",
                "div[contenteditable='true']"
            ],
            
            # ✅ Photo/Video button - untuk membuka media selector
            'photo_video_button': [
                # Berdasarkan gambar: tombol "Photo/video" 
                "//*[contains(text(), 'Photo/video')]",
                "//*[contains(text(), 'Foto/video')]",  # Indonesian
                "div[aria-label*='Photo']",
                "div[aria-label*='Foto']",
                "[data-testid*='photo']",
                "[data-testid*='media']"
            ],
            
            # ✅ Direct file upload input
            'media_upload_input': [
                "input[type='file'][accept*='image']",
                "input[type='file'][accept*='video']", 
                "input[type='file'][accept*='*']",
                "input[type='file']",
                "//input[@type='file']"
            ],
            
            # ✅ Post button - FIXED berdasarkan gambar
            'post_button': [
                # Berdasarkan gambar: tombol "Post" (bukan "Posting")
                "//*[text()='Post' and @role='button']",
                "//*[contains(text(), 'Post') and @role='button']",
                "//*[text()='Posting' and @role='button']",  # Indonesian
                "//*[contains(text(), 'Posting') and @role='button']",  # Indonesian
                "div[aria-label='Post'][role='button']",
                "button[aria-label='Post']",
                "[data-testid*='post-button']"
            ],
            
            # ✅ Reels specific selectors - DUAL LANGUAGE
            'reels_upload_input': [
                "input[type='file'][accept*='video']",
                "input[type='file']",
                "//input[@type='file']"
            ],
            
            'reels_next_button': [
                "//*[contains(text(), 'Next') and @role='button']",
                "//*[contains(text(), 'Berikutnya') and @role='button']",  # Indonesian
                "button[aria-label='Next']",
                "div[aria-label='Next'][role='button']"
            ],
            
            'reels_publish_button': [
                "//*[contains(text(), 'Publish') and @role='button']",
                "//*[contains(text(), 'Terbitkan') and @role='button']",  # Indonesian
                "//*[contains(text(), 'Share') and @role='button']",
                "button[aria-label='Publish']",
                "div[aria-label='Publish'][role='button']"
            ]
        }

    def _log(self, message: str, level: str = "INFO"):
        """Enhanced logging with colors"""
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
        """Get ChromeDriver path with Windows compatibility fix"""
        try:
            self._log("Downloading ChromeDriver...")
            
            # Force download fresh ChromeDriver
            driver_path = ChromeDriverManager().install()
            
            # Windows compatibility check
            if platform.system() == "Windows":
                # Ensure we have the .exe file
                if not driver_path.endswith('.exe'):
                    # Look for .exe in the same directory
                    driver_dir = os.path.dirname(driver_path)
                    exe_files = [f for f in os.listdir(driver_dir) if f.endswith('.exe') and 'chromedriver' in f.lower()]
                    
                    if exe_files:
                        driver_path = os.path.join(driver_dir, exe_files[0])
                    else:
                        # Try adding .exe extension
                        exe_path = driver_path + '.exe'
                        if os.path.exists(exe_path):
                            driver_path = exe_path
                
                # Verify the file is executable
                if not os.path.exists(driver_path):
                    raise FileNotFoundError(f"ChromeDriver not found at: {driver_path}")
                
                # Check if file is valid executable
                try:
                    import subprocess
                    result = subprocess.run([driver_path, '--version'], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode != 0:
                        raise Exception("ChromeDriver is not a valid executable")
                except Exception as e:
                    self._log(f"ChromeDriver validation failed: {e}", "WARNING")
                    # Try alternative download
                    return self._download_chromedriver_alternative()
            
            self._log(f"ChromeDriver ready: {driver_path}", "SUCCESS")
            return driver_path
            
        except Exception as e:
            self._log(f"ChromeDriver download failed: {e}", "ERROR")
            return self._download_chromedriver_alternative()

    def _download_chromedriver_alternative(self):
        """Alternative ChromeDriver download method for Windows"""
        self._log("Trying alternative ChromeDriver download...", "WARNING")
        
        try:
            # Clear webdriver-manager cache
            import shutil
            cache_dir = os.path.expanduser("~/.wdm")
            if os.path.exists(cache_dir):
                shutil.rmtree(cache_dir)
                self._log("Cleared ChromeDriver cache", "INFO")
            
            # Try fresh download
            from webdriver_manager.chrome import ChromeDriverManager
            from webdriver_manager.core.utils import ChromeType
            
            driver_path = ChromeDriverManager(chrome_type=ChromeType.GOOGLE).install()
            
            # Windows path fix
            if platform.system() == "Windows" and not driver_path.endswith('.exe'):
                driver_path += '.exe'
            
            if os.path.exists(driver_path):
                self._log(f"Alternative download successful: {driver_path}", "SUCCESS")
                return driver_path
            else:
                raise FileNotFoundError("Alternative download failed")
                
        except Exception as e:
            self._log(f"Alternative download failed: {e}", "ERROR")
            
            # Final fallback: check system PATH
            import shutil
            system_chrome = shutil.which('chromedriver') or shutil.which('chromedriver.exe')
            if system_chrome:
                self._log(f"Using system ChromeDriver: {system_chrome}", "SUCCESS")
                return system_chrome
            
            # Last resort: manual instructions
            self._log("ChromeDriver auto-download failed. Manual setup required:", "ERROR")
            self._log("1. Download ChromeDriver from: https://chromedriver.chromium.org/", "INFO")
            self._log("2. Extract to a folder in your PATH", "INFO")
            self._log("3. Or place in the same folder as this script", "INFO")
            
            raise FileNotFoundError("ChromeDriver not available. Please install manually.")

    def _setup_driver(self):
        """Setup Chrome WebDriver with optimal configuration"""
        self._log("Setting up browser for Facebook...")
        
        chrome_options = Options()
        
        # Basic options
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--window-size=1280,800")
        
        if self.headless:
            chrome_options.add_argument('--headless=new')
        
        # Additional options for Facebook
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-gpu')
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
        
        try:
            # Get ChromeDriver with Windows fix
            driver_path = self._get_chromedriver_path()
            
            service = Service(
                driver_path,
                log_path=os.devnull,
                service_args=['--silent']
            )
            
            # Suppress logs
            os.environ['WDM_LOG_LEVEL'] = '0'
            os.environ['WDM_PRINT_FIRST_LINE'] = 'False'
            
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Anti-detection scripts
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.wait = WebDriverWait(self.driver, 30)
            
            self._log("Browser ready for Facebook", "SUCCESS")
            
        except Exception as e:
            self._log(f"Failed to setup browser: {str(e)}", "ERROR")
            
            # Additional Windows troubleshooting
            if platform.system() == "Windows":
                self._log("Windows troubleshooting tips:", "INFO")
                self._log("1. Make sure Google Chrome is installed", "INFO")
                self._log("2. Update Chrome to the latest version", "INFO")
                self._log("3. Run as Administrator", "INFO")
                self._log("4. Disable antivirus temporarily", "INFO")
                self._log("5. Check Windows Defender exclusions", "INFO")
            
            raise

    def load_cookies(self) -> bool:
        """Load cookies from JSON file"""
        if not self.cookies_path.exists():
            self._log("Facebook cookies file not found", "WARNING")
            return False
            
        try:
            with open(self.cookies_path, 'r', encoding='utf-8') as f:
                cookies_data = json.load(f)
            
            if isinstance(cookies_data, dict):
                cookies = cookies_data.get('cookies', [])
            else:
                cookies = cookies_data
            
            if not cookies:
                self._log("Cookies file is empty", "WARNING")
                return False
            
            # Navigate to Facebook first
            self.driver.get(self.home_url)
            time.sleep(3)
            
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
                        self._log(f"Failed to add cookie {cookie.get('name', 'unknown')}: {e}", "DEBUG")
            
            self._log(f"Cookies loaded: {cookies_added}/{len(cookies)}", "SUCCESS")
            return cookies_added > 0
            
        except Exception as e:
            self._log(f"Failed to load cookies: {str(e)}", "ERROR")
            return False

    def save_cookies(self):
        """Save cookies to JSON file"""
        try:
            cookies = self.driver.get_cookies()
            
            cookies_data = {
                "timestamp": int(time.time()),
                "cookies": cookies
            }
            
            with open(self.cookies_path, 'w', encoding='utf-8') as f:
                json.dump(cookies_data, f, indent=2, ensure_ascii=False)
            
            self._log(f"Cookies saved: {len(cookies)} items", "SUCCESS")
            
        except Exception as e:
            self._log(f"Failed to save cookies: {str(e)}", "ERROR")

    def clear_cookies(self):
        """Clear cookies file"""
        try:
            if self.cookies_path.exists():
                self.cookies_path.unlink()
                self._log("Facebook cookies cleared", "SUCCESS")
            else:
                self._log("No Facebook cookies to clear", "WARNING")
        except Exception as e:
            self._log(f"Failed to clear cookies: {str(e)}", "ERROR")

    def check_login_required(self) -> bool:
        """Check if login is required"""
        current_url = self.driver.current_url
        return "login" in current_url or "checkpoint" in current_url

    def wait_for_login(self, timeout: int = 180):
        """Wait for user to login manually"""
        self._log("Please login manually in the browser...", "WARNING")
        self._log(f"Waiting for login completion (timeout {timeout} seconds)...", "INFO")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            current_url = self.driver.current_url
            
            # Check if no longer on login page
            if not ("login" in current_url or "checkpoint" in current_url):
                if "facebook.com" in current_url:
                    self._log("Login successful!", "SUCCESS")
                    self.save_cookies()
                    return True
            
            time.sleep(2)
        
        raise TimeoutException("Timeout waiting for login")

    def safe_click(self, element, method_name="click"):
        """🎯 UNIFIED SAFE CLICK - Same method for all elements"""
        try:
            # Method 1: Regular click
            element.click()
            self._log(f"Element clicked successfully with regular click", "SUCCESS")
            return True
        except ElementClickInterceptedException:
            self._log("Regular click intercepted, trying JavaScript click...", "WARNING")
            
            try:
                # Method 2: JavaScript click
                self.driver.execute_script("arguments[0].click();", element)
                self._log("Element clicked successfully with JavaScript", "SUCCESS")
                return True
            except Exception as e:
                self._log(f"JavaScript click failed: {e}", "WARNING")
                
                try:
                    # Method 3: Scroll into view and try again
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                    time.sleep(1)
                    self.driver.execute_script("arguments[0].click();", element)
                    self._log("Element clicked after scrolling into view", "SUCCESS")
                    return True
                except Exception as e2:
                    self._log(f"Scroll and click failed: {e2}", "WARNING")
                    
                    try:
                        # Method 4: Move to element and click
                        actions = ActionChains(self.driver)
                        actions.move_to_element(element).click().perform()
                        self._log("Element clicked with ActionChains", "SUCCESS")
                        return True
                    except Exception as e3:
                        self._log(f"ActionChains click failed: {e3}", "ERROR")
                        return False
        except Exception as e:
            self._log(f"All click methods failed: {e}", "ERROR")
            return False

    def find_whats_on_mind_element(self):
        """🎯 UNIFIED ELEMENT FINDER - Same method for text and media"""
        self._log("Looking for 'What's on your mind' element...")
        
        # Wait for page to load
        time.sleep(3)
        
        # Try to find the text first
        for xpath in self.selectors['whats_on_mind_text']:
            try:
                elements = self.driver.find_elements(By.XPATH, xpath)
                
                for element in elements:
                    if element.is_displayed():
                        # Check if this element is in the main feed area (not in comments)
                        try:
                            # Look for comment indicators in parent elements
                            parent_html = element.find_element(By.XPATH, "./ancestor::div[5]").get_attribute('outerHTML')
                            
                            # Skip if this appears to be in a comment section
                            if any(indicator in parent_html.lower() for indicator in ['comment', 'reply', 'response']):
                                self._log("Skipping element in comment section", "DEBUG")
                                continue
                            
                            # Find the clickable parent (usually a div with role="button" or tabindex)
                            clickable_parent = None
                            
                            # Try to find clickable parent
                            for i in range(1, 6):  # Check up to 5 levels up
                                try:
                                    parent = element.find_element(By.XPATH, f"./ancestor::*[@role='button' or @tabindex='0'][{i}]")
                                    if parent.is_displayed() and parent.is_enabled():
                                        clickable_parent = parent
                                        break
                                except NoSuchElementException:
                                    continue
                            
                            if not clickable_parent:
                                # Try to find any clickable ancestor
                                try:
                                    clickable_parent = element.find_element(By.XPATH, "./ancestor::*[@role='button'][1]")
                                except NoSuchElementException:
                                    try:
                                        clickable_parent = element.find_element(By.XPATH, "./ancestor::div[@tabindex='0'][1]")
                                    except NoSuchElementException:
                                        # Use the element itself if no clickable parent found
                                        clickable_parent = element
                            
                            self._log("Found 'What's on your mind' element", "SUCCESS")
                            return clickable_parent
                            
                        except Exception as e:
                            self._log(f"Error analyzing element: {e}", "DEBUG")
                            continue
                            
            except Exception as e:
                self._log(f"Error with xpath {xpath}: {e}", "DEBUG")
                continue
        
        return None

    def find_element_by_selectors(self, selectors_list, timeout=10):
        """🎯 UNIFIED ELEMENT FINDER - Same method for all selectors"""
        for selector in selectors_list:
            try:
                if selector.startswith('/'):
                    # XPath selector
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed() or element.get_attribute('type') == 'file':
                            self._log(f"Found element with selector: {selector[:50]}...", "SUCCESS")
                            return element
                else:
                    # CSS selector
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() or element.get_attribute('type') == 'file':
                            self._log(f"Found element with selector: {selector[:50]}...", "SUCCESS")
                            return element
                    
            except Exception as e:
                self._log(f"Error with selector {selector[:30]}...: {e}", "DEBUG")
                continue
        
        return None

    def add_status_text_with_validation(self, status_text: str) -> bool:
        """🎯 ADD STATUS TEXT WITH PROPER VALIDATION - STEP 1"""
        if not status_text.strip():
            self._log("No status text provided", "INFO")
            return True
        
        self._log("STEP 1: Adding status text first...")
        
        try:
            # Find text input using unified approach
            text_input = self.find_element_by_selectors(self.selectors['status_text_input'], timeout=10)
            
            if not text_input:
                self._log("Text input not found", "ERROR")
                return False
            
            # Click to focus the input
            if not self.safe_click(text_input):
                self._log("Failed to click text input", "ERROR")
                return False
            
            time.sleep(1)
            
            # Clear any existing text
            try:
                text_input.send_keys(Keys.CONTROL + "a")
                text_input.send_keys(Keys.BACKSPACE)
                time.sleep(0.5)
            except:
                pass
            
            # Try multiple methods to enter text
            methods = [
                # Method 1: Direct send_keys
                lambda: text_input.send_keys(status_text),
                # Method 2: JavaScript setValue
                lambda: self.driver.execute_script("arguments[0].textContent = arguments[1];", text_input, status_text),
                # Method 3: JavaScript innerHTML
                lambda: self.driver.execute_script("arguments[0].innerHTML = arguments[1];", text_input, status_text),
                # Method 4: Character by character
                lambda: self._type_text_slowly(text_input, status_text),
                # Method 5: Focus and type
                lambda: self._focus_and_type(text_input, status_text)
            ]
            
            for i, method in enumerate(methods, 1):
                try:
                    self._log(f"Trying text input method {i}...", "INFO")
                    method()
                    
                    # Validate if text was entered correctly
                    if self.validate_text_input(text_input, status_text):
                        self._log(f"✅ STEP 1 COMPLETE: Status text added successfully with method {i}", "SUCCESS")
                        return True
                    else:
                        self._log(f"Method {i} failed validation, trying next...", "WARNING")
                        
                        # Clear and try next method
                        try:
                            text_input.send_keys(Keys.CONTROL + "a")
                            text_input.send_keys(Keys.BACKSPACE)
                            time.sleep(0.5)
                        except:
                            pass
                        
                except Exception as e:
                    self._log(f"Method {i} failed: {e}", "WARNING")
                    continue
            
            self._log("All text input methods failed", "ERROR")
            return False
            
        except Exception as e:
            self._log(f"Failed to add status text: {e}", "ERROR")
            return False

    def add_media_after_text(self, media_path: str) -> bool:
        """🎯 ADD MEDIA AFTER TEXT - STEP 2"""
        if not media_path or not os.path.exists(media_path):
            self._log("No valid media file provided", "INFO")
            return True
        
        self._log("STEP 2: Adding media after text...")
        
        try:
            # First, try to find Photo/Video button
            photo_video_button = self.find_element_by_selectors(self.selectors['photo_video_button'], timeout=5)
            
            if photo_video_button:
                self._log("Found Photo/Video button, clicking...", "INFO")
                if self.safe_click(photo_video_button):
                    time.sleep(2)  # Wait for file dialog or input to appear
                else:
                    self._log("Failed to click Photo/Video button", "WARNING")
            
            # Find file input (might be hidden)
            file_input = self.find_element_by_selectors(self.selectors['media_upload_input'], timeout=5)
            
            if file_input:
                # Make the input visible if it's hidden
                self.driver.execute_script("""
                    arguments[0].style.display = 'block';
                    arguments[0].style.visibility = 'visible';
                    arguments[0].style.opacity = '1';
                    arguments[0].style.position = 'static';
                """, file_input)
                
                # Upload file directly
                abs_path = os.path.abspath(media_path)
                file_input.send_keys(abs_path)
                
                self._log("✅ STEP 2 COMPLETE: Media uploaded successfully", "SUCCESS")
                time.sleep(3)  # Wait for upload to process
                return True
            else:
                self._log("No file input found for media upload", "WARNING")
                return False
                
        except Exception as e:
            self._log(f"Media upload failed: {e}", "WARNING")
            return False

    def validate_text_input(self, text_input, expected_text: str) -> bool:
        """🎯 VALIDATE TEXT INPUT - Check if text was actually entered"""
        try:
            # Wait a moment for text to be processed
            time.sleep(1)
            
            # Get the actual text content
            actual_text = ""
            
            # Try different methods to get text content
            methods = [
                lambda: text_input.get_attribute('value'),
                lambda: text_input.get_attribute('textContent'),
                lambda: text_input.get_attribute('innerText'),
                lambda: text_input.text,
                lambda: self.driver.execute_script("return arguments[0].textContent;", text_input),
                lambda: self.driver.execute_script("return arguments[0].innerText;", text_input),
                lambda: self.driver.execute_script("return arguments[0].value;", text_input)
            ]
            
            for method in methods:
                try:
                    result = method()
                    if result and result.strip():
                        actual_text = result.strip()
                        break
                except:
                    continue
            
            # Check if expected text is in actual text
            if expected_text.strip() in actual_text:
                self._log(f"Text validation SUCCESS: '{actual_text[:50]}...'", "SUCCESS")
                return True
            else:
                self._log(f"Text validation FAILED: Expected '{expected_text[:30]}...', Got '{actual_text[:30]}...'", "ERROR")
                return False
                
        except Exception as e:
            self._log(f"Text validation error: {e}", "ERROR")
            return False

    def _type_text_slowly(self, element, text: str):
        """Type text character by character"""
        for char in text:
            element.send_keys(char)
            time.sleep(0.05)  # Small delay between characters

    def _focus_and_type(self, element, text: str):
        """Focus element and type text"""
        # Focus the element
        self.driver.execute_script("arguments[0].focus();", element)
        time.sleep(0.5)
        
        # Clear and type
        element.send_keys(Keys.CONTROL + "a")
        element.send_keys(Keys.BACKSPACE)
        time.sleep(0.5)
        element.send_keys(text)

    def upload_status(self, status_text: str = "", media_path: str = "") -> Dict[str, Any]:
        """
        🎯 UNIFIED STATUS UPLOAD - TEXT FIRST, MEDIA SECOND
        
        Args:
            status_text: Text content for status
            media_path: Path to media file (image/video)
            
        Returns:
            Dict with upload status
        """
        try:
            # Setup driver
            self._setup_driver()
            
            # Load cookies
            cookies_loaded = self.load_cookies()
            
            # Navigate to Facebook
            self._log("Navigating to Facebook...")
            self.driver.get(self.home_url)
            time.sleep(5)
            
            # Check if login required
            if self.check_login_required():
                if cookies_loaded:
                    self._log("Cookies loaded but still need login, refreshing...", "WARNING")
                    self.driver.refresh()
                    time.sleep(5)
                
                if self.check_login_required():
                    self.wait_for_login()
                    self.driver.get(self.home_url)
                    time.sleep(5)
            
            # Take screenshot before attempting to find elements
            self.take_screenshot(f"facebook_before_post_{int(time.time())}.png")
            
            # 🎯 STEP 1: Find the "What's on your mind" element (SAME FOR ALL)
            whats_on_mind = self.find_whats_on_mind_element()
            
            if not whats_on_mind:
                self.take_screenshot(f"facebook_no_whats_on_mind_{int(time.time())}.png")
                raise NoSuchElementException("Could not find 'What's on your mind' element")
            
            # 🎯 STEP 2: Click the "What's on your mind" element (SAME FOR ALL)
            self._log("Clicking 'What's on your mind' element...")
            if not self.safe_click(whats_on_mind):
                raise Exception("Failed to click 'What's on your mind' element")
            
            time.sleep(3)
            self._log("Post composer should now be open", "SUCCESS")
            
            # 🎯 STEP 3: Add status text FIRST (if provided)
            text_added = False
            if status_text.strip():
                text_added = self.add_status_text_with_validation(status_text)
                if not text_added:
                    self._log("Failed to add status text", "ERROR")
            else:
                text_added = True  # No text to add, consider success
            
            # 🎯 STEP 4: Add media SECOND (if provided)
            media_uploaded = False
            if media_path and os.path.exists(media_path):
                media_uploaded = self.add_media_after_text(media_path)
                if not media_uploaded:
                    self._log("Failed to add media", "WARNING")
            else:
                media_uploaded = True  # No media to add, consider success
            
            # 🎯 STEP 5: Validate we have content to post
            if not text_added and not media_uploaded:
                raise Exception("Neither text nor media was successfully added")
            
            # 🎯 STEP 6: Find and click post button (SAME FOR ALL)
            self._log("Looking for post button...")
            post_button = self.find_element_by_selectors(self.selectors['post_button'], timeout=10)
            
            if not post_button:
                self.take_screenshot(f"facebook_no_post_button_{int(time.time())}.png")
                raise NoSuchElementException("Post button not found")
            
            # Click post button safely
            self._log("Clicking post button...")
            if not self.safe_click(post_button):
                raise Exception("Failed to click post button")
            
            # ✅ SUCCESS: Content was added and post button was clicked
            success_message = []
            if text_added and status_text.strip():
                success_message.append("text")
            if media_uploaded and media_path:
                success_message.append("media")
            
            content_type = " + ".join(success_message) if success_message else "content"
            self._log(f"Facebook status with {content_type} posted successfully!", "SUCCESS")
            
            return {
                "success": True,
                "message": f"Status with {content_type} posted successfully",
                "status_text": status_text,
                "media_path": media_path,
                "text_added": text_added,
                "media_uploaded": media_uploaded
            }
            
        except Exception as e:
            error_msg = f"Facebook status upload failed: {str(e)}"
            self._log(error_msg, "ERROR")
            
            # Take screenshot for debugging
            self.take_screenshot(f"facebook_status_error_{int(time.time())}.png")
            
            return {
                "success": False,
                "message": error_msg,
                "status_text": status_text,
                "media_path": media_path
            }
        
        finally:
            if self.driver:
                self._log("Closing browser...")
                self.driver.quit()

    def upload_reels(self, video_path: str, description: str = "") -> Dict[str, Any]:
        """
        Upload reels to Facebook
        
        Args:
            video_path: Path to video file
            description: Description for the reel
            
        Returns:
            Dict with upload status
        """
        try:
            # Setup driver
            self._setup_driver()
            
            # Load cookies
            cookies_loaded = self.load_cookies()
            
            # Navigate to Facebook Reels creation
            self._log("Navigating to Facebook Reels...")
            self.driver.get(self.reels_url)
            time.sleep(5)
            
            # Check if login required
            if self.check_login_required():
                if cookies_loaded:
                    self._log("Cookies loaded but still need login, refreshing...", "WARNING")
                    self.driver.refresh()
                    time.sleep(5)
                
                if self.check_login_required():
                    self.wait_for_login()
                    self.driver.get(self.reels_url)
                    time.sleep(5)
            
            # Upload video file
            self._log("Uploading video file...")
            
            # Find file input
            file_input = self.find_element_by_selectors(self.selectors['reels_upload_input'], timeout=10)
            
            if not file_input:
                raise NoSuchElementException("Video upload element not found")
            
            # Upload video
            abs_path = os.path.abspath(video_path)
            file_input.send_keys(abs_path)
            self._log("Video file uploaded", "SUCCESS")
            
            # Wait for video processing
            self._log("Waiting for video processing...")
            time.sleep(15)
            
            # Navigate through reels creation steps
            # Step 1: First Next button
            next_button = self.find_element_by_selectors(self.selectors['reels_next_button'], timeout=10)
            if next_button:
                if self.safe_click(next_button):
                    self._log("First 'Next' button clicked", "SUCCESS")
                    time.sleep(3)
            
            # Step 2: Second Next button (if exists)
            next_button = self.find_element_by_selectors(self.selectors['reels_next_button'], timeout=5)
            if next_button:
                if self.safe_click(next_button):
                    self._log("Second 'Next' button clicked", "SUCCESS")
                    time.sleep(3)
            
            # Add description if provided
            if description.strip():
                self._log("Adding description...")
                
                # Look for description input
                description_inputs = self.driver.find_elements(By.CSS_SELECTOR, "div[contenteditable='true']")
                
                for desc_input in description_inputs:
                    if desc_input.is_displayed():
                        try:
                            desc_input.click()
                            time.sleep(1)
                            desc_input.send_keys(description)
                            self._log("Description added", "SUCCESS")
                            break
                        except:
                            continue
            
            # Find and click publish button
            self._log("Looking for publish button...")
            publish_button = self.find_element_by_selectors(self.selectors['reels_publish_button'], timeout=10)
            
            if not publish_button:
                raise NoSuchElementException("Publish button not found")
            
            # Click publish button safely
            self._log("Clicking publish button...")
            if not self.safe_click(publish_button):
                raise Exception("Failed to click publish button")
            
            # ✅ IMPORTANT: If we reach here with successful click, consider it successful
            self._log("Publish button clicked successfully - Reels upload completed!", "SUCCESS")
            
            return {
                "success": True,
                "message": "Reels uploaded successfully",
                "video_path": video_path,
                "description": description
            }
            
        except Exception as e:
            error_msg = f"Facebook Reels upload failed: {str(e)}"
            self._log(error_msg, "ERROR")
            
            # Take screenshot for debugging
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
                self.driver.quit()

    def take_screenshot(self, filename: str = None):
        """Take screenshot for debugging"""
        if not filename:
            filename = f"facebook_screenshot_{int(time.time())}.png"
        
        screenshot_path = self.screenshots_dir / filename
        
        try:
            if self.driver:
                self.driver.save_screenshot(str(screenshot_path))
                self._log(f"Screenshot saved: {screenshot_path.name}", "INFO")
                return str(screenshot_path)
            else:
                self._log("Driver not available for screenshot", "WARNING")
                return None
        except Exception as e:
            self._log(f"Failed to save screenshot: {str(e)}", "WARNING")
            return None

    def check_cookies_status(self):
        """Check Facebook cookies status"""
        if not self.cookies_path.exists():
            self._log("Facebook cookies file not found", "WARNING")
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
            
            self._log(f"Total Facebook cookies: {len(cookies)}", "INFO")
            self._log(f"Valid cookies: {len(valid_cookies)}", "SUCCESS")
            
            if expired_cookies:
                self._log(f"Expired cookies: {len(expired_cookies)}", "WARNING")
            
            if timestamp:
                import datetime
                saved_time = datetime.datetime.fromtimestamp(timestamp)
                self._log(f"Cookies saved: {saved_time.strftime('%Y-%m-%d %H:%M:%S')}", "INFO")
            
            return {
                "exists": True,
                "total": len(cookies),
                "valid": len(valid_cookies),
                "expired": len(expired_cookies),
                "timestamp": timestamp
            }
            
        except Exception as e:
            self._log(f"Error reading Facebook cookies: {str(e)}", "ERROR")
            return {"exists": True, "error": str(e)}


def main():
    """Main function for CLI"""
    parser = argparse.ArgumentParser(description="Facebook Uploader")
    parser.add_argument("--type", choices=['status', 'reels'], help="Upload type")
    parser.add_argument("--video", "-v", help="Path to video file (for reels)")
    parser.add_argument("--status", "-s", help="Status text")
    parser.add_argument("--media", "-m", help="Path to media file (for status)")
    parser.add_argument("--description", "-d", default="", help="Description for reels")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--clear-cookies", action="store_true", help="Clear cookies")
    parser.add_argument("--check-cookies", action="store_true", help="Check cookies status")

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
            print(f"{Fore.RED}❌ Status text or media required for status upload")
            sys.exit(1)
        
        if args.media and not os.path.exists(args.media):
            print(f"{Fore.RED}❌ Media file not found: {args.media}")
            sys.exit(1)
        
        result = uploader.upload_status(args.status or "", args.media or "")
        
        if result["success"]:
            print(f"{Fore.GREEN}🎉 Facebook status uploaded successfully!")
            if result.get("text_added"):
                print(f"{Fore.CYAN}📝 Text: Added")
            if result.get("media_uploaded"):
                print(f"{Fore.CYAN}📷 Media: Uploaded")
        else:
            print(f"{Fore.RED}❌ Facebook status upload failed: {result['message']}")
            sys.exit(1)

    elif args.type == 'reels':
        if not args.video:
            print(f"{Fore.RED}❌ Video path required for reels upload")
            sys.exit(1)
        
        if not os.path.exists(args.video):
            print(f"{Fore.RED}❌ Video file not found: {args.video}")
            sys.exit(1)
        
        result = uploader.upload_reels(args.video, args.description)
        
        if result["success"]:
            print(f"{Fore.GREEN}🎉 Facebook Reels uploaded successfully!")
        else:
            print(f"{Fore.RED}❌ Facebook Reels upload failed: {result['message']}")
            sys.exit(1)

    else:
        # Interactive mode
        print(f"{Fore.BLUE}📘 Facebook Uploader")
        print("=" * 40)
        print(f"{Fore.YELLOW}🔄 NEW: Text First, Media Second")
        print()
        
        while True:
            print(f"\n{Fore.YELLOW}Choose action:")
            print("1. 📝 Upload Status (Text Only)")
            print("2. 🖼️ Upload Status (Media Only)")
            print("3. 📝🖼️ Upload Status (Text + Media)")
            print("4. 🎬 Upload Reels")
            print("5. 🍪 Check cookies status")
            print("6. 🗑️ Clear cookies")
            print("7. ❌ Exit")
            
            choice = input(f"\n{Fore.WHITE}Choice (1-7): ").strip()
            
            if choice == "1":
                status_text = input(f"{Fore.CYAN}Status text: ").strip()
                if not status_text:
                    print(f"{Fore.RED}❌ Status text cannot be empty!")
                    continue
                
                result = uploader.upload_status(status_text)
                
                if result["success"]:
                    print(f"{Fore.GREEN}🎉 Facebook status uploaded successfully!")
                else:
                    print(f"{Fore.RED}❌ Facebook status upload failed: {result['message']}")
            
            elif choice == "2":
                media_path = input(f"{Fore.CYAN}Media file path: ").strip()
                if not os.path.exists(media_path):
                    print(f"{Fore.RED}❌ Media file not found!")
                    continue
                
                result = uploader.upload_status("", media_path)
                
                if result["success"]:
                    print(f"{Fore.GREEN}🎉 Facebook status with media uploaded successfully!")
                else:
                    print(f"{Fore.RED}❌ Facebook status upload failed: {result['message']}")
            
            elif choice == "3":
                status_text = input(f"{Fore.CYAN}Status text: ").strip()
                if not status_text:
                    print(f"{Fore.RED}❌ Status text cannot be empty for text + media!")
                    continue
                
                media_path = input(f"{Fore.CYAN}Media file path: ").strip()
                if not os.path.exists(media_path):
                    print(f"{Fore.RED}❌ Media file not found!")
                    continue
                
                print(f"{Fore.YELLOW}🔄 Order: Text first, then media")
                result = uploader.upload_status(status_text, media_path)
                
                if result["success"]:
                    print(f"{Fore.GREEN}🎉 Facebook status with text + media uploaded successfully!")
                    print(f"{Fore.CYAN}📝 Text: {result.get('text_added', False)}")
                    print(f"{Fore.CYAN}📷 Media: {result.get('media_uploaded', False)}")
                else:
                    print(f"{Fore.RED}❌ Facebook status upload failed: {result['message']}")
            
            elif choice == "4":
                video_path = input(f"{Fore.CYAN}Video file path: ").strip()
                if not os.path.exists(video_path):
                    print(f"{Fore.RED}❌ Video file not found!")
                    continue
                
                description = input(f"{Fore.CYAN}Description (optional): ").strip()
                
                result = uploader.upload_reels(video_path, description)
                
                if result["success"]:
                    print(f"{Fore.GREEN}🎉 Facebook Reels uploaded successfully!")
                else:
                    print(f"{Fore.RED}❌ Facebook Reels upload failed: {result['message']}")
            
            elif choice == "5":
                uploader.check_cookies_status()
            
            elif choice == "6":
                confirm = input(f"{Fore.YELLOW}Clear Facebook cookies? (y/N): ").strip().lower()
                if confirm == 'y':
                    uploader.clear_cookies()
            
            elif choice == "7":
                print(f"{Fore.YELLOW}👋 Goodbye!")
                break
            
            else:
                print(f"{Fore.RED}❌ Invalid choice!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}👋 Program stopped by user")
    except Exception as e:
        print(f"{Fore.RED}💥 Fatal error: {str(e)}")
        sys.exit(1)