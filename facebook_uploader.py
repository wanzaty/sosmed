#!/usr/bin/env python3
"""
Facebook Uploader untuk Status dan Reels menggunakan Selenium
Mendukung cookies JSON untuk auto-login dan upload berbagai jenis konten
Unified approach untuk text dan media menggunakan selector yang sama
Dengan selector optimization dan dual language support
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
        self.performance_path = self.base_dir / "facebook_selector_performance.json"
        
        # Facebook URLs
        self.home_url = "https://www.facebook.com"
        self.reels_url = "https://www.facebook.com/reel/create"
        self.login_url = "https://www.facebook.com/login"
        
        # 🎯 UNIFIED SELECTORS - Berdasarkan analisis gambar
        self.selectors = {
            # ✅ UNIFIED "What's on your mind" - SAMA untuk text dan media
            'whats_on_mind_trigger': [
                # Berdasarkan gambar: elemen yang sama untuk text dan media
                "div[role='button'][aria-label*='What\\'s on your mind']",
                "div[role='button'][data-testid*='status-attachment-mentions-input']",
                "div[contenteditable='true'][aria-label*='What\\'s on your mind']",
                "div[contenteditable='true'][data-testid*='status-attachment-mentions-input']",
                # XPath approach - lebih spesifik
                "//*[contains(text(), \"What's on your mind\")]/ancestor::div[@role='button'][1]",
                "//*[contains(text(), \"What's on your mind\")]/ancestor::div[@tabindex='0'][1]",
                "//*[contains(text(), \"Apa yang Anda pikirkan\")]/ancestor::div[@role='button'][1]",  # Indonesian - PROTECTED
                "//*[contains(text(), \"Apa yang Anda pikirkan\")]/ancestor::div[@tabindex='0'][1]",  # Indonesian - PROTECTED
                # Fallback selectors
                "div[data-testid='status-attachment-mentions-input']",
                "div[aria-label*='What\\'s on your mind']",
                "div[aria-label*='Apa yang Anda pikirkan']"  # Indonesian - PROTECTED
            ],
            
            # ✅ UNIFIED TEXT INPUT - Setelah klik "What's on your mind"
            'unified_text_input': [
                # Berdasarkan gambar: input text yang muncul setelah klik
                "div[contenteditable='true'][aria-label*='What\\'s on your mind']",
                "div[contenteditable='true'][aria-label*='Apa yang Anda pikirkan']",  # Indonesian - PROTECTED
                "div[contenteditable='true'][data-testid*='status-attachment-mentions-input']",
                "div[contenteditable='true'][role='textbox']",
                # XPath untuk text input dalam modal
                "//div[@aria-label='Create post']//div[@contenteditable='true']",
                "//div[contains(@aria-label, 'Create post')]//div[@contenteditable='true']",
                "//div[@role='dialog']//div[@contenteditable='true']",
                # Fallback
                "div[contenteditable='true']"
            ],
            
            # ✅ UNIFIED MEDIA UPLOAD - SAMA dengan text input area
            'unified_media_upload': [
                # Berdasarkan gambar: tombol Photo/video dalam "Add to your post"
                "div[aria-label='Photo/video']",
                "div[aria-label='Foto/video']",  # Indonesian - PROTECTED
                "input[type='file'][accept*='image']",
                "input[type='file'][accept*='video']",
                "input[type='file']",
                # XPath untuk media button
                "//div[contains(@aria-label, 'Photo/video')]",
                "//div[contains(@aria-label, 'Foto/video')]",  # Indonesian - PROTECTED
                "//div[contains(text(), 'Photo/video')]/ancestor::div[@role='button'][1]",
                "//div[contains(text(), 'Foto/video')]/ancestor::div[@role='button'][1]",  # Indonesian - PROTECTED
                # File input selectors
                "//input[@type='file']",
                "//input[@accept]"
            ],
            
            # ✅ POST BUTTON - Dalam modal Create post
            'post_button': [
                # Berdasarkan gambar: tombol Post biru di modal
                "div[aria-label='Post'][role='button']",
                "div[aria-label='Posting'][role='button']",  # Indonesian - PROTECTED
                "button[aria-label='Post']",
                "button[aria-label='Posting']",  # Indonesian - PROTECTED
                # XPath approach
                "//div[@role='dialog']//div[@role='button'][contains(text(), 'Post')]",
                "//div[@role='dialog']//div[@role='button'][contains(text(), 'Posting')]",  # Indonesian - PROTECTED
                "//div[@role='dialog']//button[contains(text(), 'Post')]",
                "//div[@role='dialog']//button[contains(text(), 'Posting')]",  # Indonesian - PROTECTED
                # Data testid approach
                "div[data-testid*='react-composer-post-button']",
                "button[data-testid*='react-composer-post-button']",
                # Generic fallback
                "div[role='button'][tabindex='0']"
            ],
            
            # ✅ REELS SPECIFIC SELECTORS
            'reels_upload_input': [
                "input[type='file'][accept*='video']",
                "input[type='file']",
                "//input[@type='file']"
            ],
            
            'reels_next_button': [
                "div[aria-label='Next'][role='button']",
                "div[aria-label='Berikutnya'][role='button']",  # Indonesian - PROTECTED
                "button[aria-label='Next']",
                "button[aria-label='Berikutnya']",  # Indonesian - PROTECTED
                "//div[@role='button'][contains(text(), 'Next')]",
                "//div[@role='button'][contains(text(), 'Berikutnya')]",  # Indonesian - PROTECTED
                "//button[contains(text(), 'Next')]",
                "//button[contains(text(), 'Berikutnya')]"  # Indonesian - PROTECTED
            ],
            
            'reels_publish_button': [
                "div[aria-label='Publish'][role='button']",
                "div[aria-label='Terbitkan'][role='button']",  # Indonesian - PROTECTED
                "div[aria-label='Share'][role='button']",
                "button[aria-label='Publish']",
                "button[aria-label='Terbitkan']",  # Indonesian - PROTECTED
                "button[aria-label='Share']",
                "//div[@role='button'][contains(text(), 'Publish')]",
                "//div[@role='button'][contains(text(), 'Terbitkan')]",  # Indonesian - PROTECTED
                "//div[@role='button'][contains(text(), 'Share')]",
                "//button[contains(text(), 'Publish')]",
                "//button[contains(text(), 'Terbitkan')]",  # Indonesian - PROTECTED
                "//button[contains(text(), 'Share')]"
            ]
        }
        
        # Load performance data
        self.selector_performance = self.load_performance_data()

    def load_performance_data(self) -> Dict[str, Any]:
        """Load selector performance data"""
        try:
            if self.performance_path.exists():
                with open(self.performance_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            if self.debug:
                self._log(f"Error loading performance data: {e}", "DEBUG")
        
        return {
            "selector_stats": {},
            "last_updated": time.time(),
            "total_operations": 0
        }

    def save_performance_data(self):
        """Save selector performance data"""
        try:
            self.selector_performance["last_updated"] = time.time()
            with open(self.performance_path, 'w', encoding='utf-8') as f:
                json.dump(self.selector_performance, f, indent=2, ensure_ascii=False)
        except Exception as e:
            if self.debug:
                self._log(f"Error saving performance data: {e}", "DEBUG")

    def is_protected_selector(self, selector: str) -> bool:
        """Check if selector is protected (Indonesian language)"""
        indonesian_keywords = [
            "Apa yang Anda pikirkan",
            "Berikutnya", 
            "Terbitkan",
            "Foto/video",
            "Posting"
        ]
        
        return any(keyword in selector for keyword in indonesian_keywords)

    def update_selector_performance(self, selector_type: str, selector: str, success: bool, response_time: float):
        """Update selector performance statistics"""
        if "selector_stats" not in self.selector_performance:
            self.selector_performance["selector_stats"] = {}
        
        if selector_type not in self.selector_performance["selector_stats"]:
            self.selector_performance["selector_stats"][selector_type] = {}
        
        if selector not in self.selector_performance["selector_stats"][selector_type]:
            self.selector_performance["selector_stats"][selector_type][selector] = {
                "success_count": 0,
                "fail_count": 0,
                "total_response_time": 0.0,
                "last_used": 0,
                "consecutive_fails": 0,
                "is_protected": self.is_protected_selector(selector)
            }
        
        stats = self.selector_performance["selector_stats"][selector_type][selector]
        
        if success:
            stats["success_count"] += 1
            stats["consecutive_fails"] = 0
        else:
            stats["fail_count"] += 1
            stats["consecutive_fails"] += 1
        
        stats["total_response_time"] += response_time
        stats["last_used"] = time.time()
        
        self.save_performance_data()

    def optimize_selectors(self, selector_type: str) -> list:
        """Optimize selector order based on performance"""
        if selector_type not in self.selectors:
            return []
        
        original_selectors = self.selectors[selector_type].copy()
        
        if selector_type not in self.selector_performance.get("selector_stats", {}):
            return original_selectors
        
        stats = self.selector_performance["selector_stats"][selector_type]
        
        # Remove selectors with too many consecutive failures (except protected ones)
        optimized_selectors = []
        removed_count = 0
        
        for selector in original_selectors:
            if selector in stats:
                selector_stats = stats[selector]
                
                # Don't remove protected selectors (Indonesian)
                if selector_stats.get("is_protected", False):
                    optimized_selectors.append(selector)
                    continue
                
                # Remove if too many consecutive failures
                if selector_stats.get("consecutive_fails", 0) >= 5:
                    removed_count += 1
                    if self.debug:
                        self._log(f"Removed poor performing selector: {selector[:50]}...", "DEBUG")
                    continue
            
            optimized_selectors.append(selector)
        
        # Sort by performance (success rate and response time)
        def selector_score(selector):
            if selector not in stats:
                return 0  # New selectors get neutral score
            
            s = stats[selector]
            total_attempts = s["success_count"] + s["fail_count"]
            
            if total_attempts == 0:
                return 0
            
            success_rate = s["success_count"] / total_attempts
            avg_response_time = s["total_response_time"] / total_attempts if total_attempts > 0 else 1.0
            
            # Higher score = better performance
            # Success rate (0-1) * 100 - response time penalty
            score = (success_rate * 100) - (avg_response_time * 10)
            
            # Boost for recently used selectors
            time_since_last_use = time.time() - s.get("last_used", 0)
            if time_since_last_use < 3600:  # Within last hour
                score += 10
            
            return score
        
        optimized_selectors.sort(key=selector_score, reverse=True)
        
        if removed_count > 0:
            self._log(f"Optimized {selector_type}: removed {removed_count} poor selectors", "INFO")
        
        return optimized_selectors

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

    def find_element_by_optimized_selectors(self, selector_type: str, timeout=10):
        """🎯 UNIFIED ELEMENT FINDER with Performance Optimization"""
        self._log(f"Looking for {selector_type} with optimized selectors...")
        
        # Get optimized selectors
        selectors_list = self.optimize_selectors(selector_type)
        
        if not selectors_list:
            self._log(f"No selectors available for {selector_type}", "ERROR")
            return None
        
        for i, selector in enumerate(selectors_list):
            start_time = time.time()
            
            try:
                if selector.startswith('/'):
                    # XPath selector
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed() or element.get_attribute('type') == 'file':
                            response_time = time.time() - start_time
                            self._log(f"✅ Found with selector #{i+1} ({response_time:.2f}s): {selector[:50]}...", "SUCCESS")
                            
                            # Update performance
                            self.update_selector_performance(selector_type, selector, True, response_time)
                            return element
                else:
                    # CSS selector
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() or element.get_attribute('type') == 'file':
                            response_time = time.time() - start_time
                            self._log(f"✅ Found with selector #{i+1} ({response_time:.2f}s): {selector[:50]}...", "SUCCESS")
                            
                            # Update performance
                            self.update_selector_performance(selector_type, selector, True, response_time)
                            return element
                    
            except Exception as e:
                response_time = time.time() - start_time
                self._log(f"❌ Selector #{i+1} failed ({response_time:.2f}s): {str(e)[:30]}...", "DEBUG")
                
                # Update performance
                self.update_selector_performance(selector_type, selector, False, response_time)
                continue
        
        self._log(f"No working selector found for {selector_type}", "ERROR")
        return None

    def find_whats_on_mind_element(self):
        """🎯 UNIFIED "What's on your mind" FINDER"""
        self._log("Looking for 'What's on your mind' trigger element...")
        
        # Wait for page to load
        time.sleep(3)
        
        # Use optimized selector finder
        element = self.find_element_by_optimized_selectors('whats_on_mind_trigger', timeout=10)
        
        if element:
            self._log("Found 'What's on your mind' trigger element", "SUCCESS")
            return element
        else:
            self._log("Could not find 'What's on your mind' trigger element", "ERROR")
            return None

    def direct_file_upload(self, media_path: str) -> bool:
        """🎯 DIRECT FILE UPLOAD - No file explorer popup"""
        self._log("Attempting direct file upload...")
        
        try:
            # Find any file input on the page (they're usually hidden)
            file_input = self.find_element_by_optimized_selectors('unified_media_upload', timeout=5)
            
            if file_input:
                # Check if it's a file input
                if file_input.get_attribute('type') == 'file':
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
                    
                    self._log("File uploaded directly without file explorer", "SUCCESS")
                    time.sleep(3)  # Wait for upload to process
                    return True
                else:
                    # It's a button, click it to trigger file dialog
                    if self.safe_click(file_input):
                        self._log("Media upload button clicked", "SUCCESS")
                        time.sleep(2)
                        
                        # Now look for the actual file input
                        file_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                        for inp in file_inputs:
                            try:
                                abs_path = os.path.abspath(media_path)
                                inp.send_keys(abs_path)
                                self._log("File uploaded via triggered input", "SUCCESS")
                                time.sleep(3)
                                return True
                            except:
                                continue
            
            self._log("No suitable media upload element found", "WARNING")
            return False
            
        except Exception as e:
            self._log(f"Direct file upload failed: {e}", "WARNING")
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

    def add_status_text_with_validation(self, status_text: str) -> bool:
        """🎯 ADD STATUS TEXT WITH PROPER VALIDATION"""
        if not status_text.strip():
            self._log("No status text provided", "INFO")
            return True
        
        self._log("Adding status text with validation...")
        
        try:
            # Find text input using unified approach
            text_input = self.find_element_by_optimized_selectors('unified_text_input', timeout=10)
            
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
                        self._log(f"Status text added successfully with method {i}", "SUCCESS")
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
        🎯 UNIFIED STATUS UPLOAD - Same approach for text and media
        
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
            
            # 🎯 STEP 1: Find the "What's on your mind" element (UNIFIED FOR ALL)
            whats_on_mind = self.find_whats_on_mind_element()
            
            if not whats_on_mind:
                self.take_screenshot(f"facebook_no_whats_on_mind_{int(time.time())}.png")
                raise NoSuchElementException("Could not find 'What's on your mind' element")
            
            # 🎯 STEP 2: Click the "What's on your mind" element (UNIFIED FOR ALL)
            self._log("Clicking 'What's on your mind' element...")
            if not self.safe_click(whats_on_mind):
                raise Exception("Failed to click 'What's on your mind' element")
            
            time.sleep(3)
            self._log("Post composer should now be open", "SUCCESS")
            
            # 🎯 STEP 3: Add media if provided (DIRECT UPLOAD - NO FILE EXPLORER)
            media_uploaded = False
            if media_path and os.path.exists(media_path):
                self._log("Adding media via direct upload...")
                
                # Try direct file upload first
                if self.direct_file_upload(media_path):
                    self._log("Media uploaded successfully via direct method", "SUCCESS")
                    media_uploaded = True
                    time.sleep(2)  # Wait for media to process
                else:
                    self._log("Direct upload failed, media not added", "WARNING")
            
            # 🎯 STEP 4: Add status text if provided (WITH PROPER VALIDATION)
            text_added = False
            if status_text.strip():
                text_added = self.add_status_text_with_validation(status_text)
                if not text_added:
                    self._log("Failed to add status text", "ERROR")
            else:
                text_added = True  # No text to add, consider success
            
            # 🎯 STEP 5: Validate we have content to post
            if not text_added and not media_uploaded:
                raise Exception("Neither text nor media was successfully added")
            
            # 🎯 STEP 6: Find and click post button (UNIFIED FOR ALL)
            self._log("Looking for post button...")
            post_button = self.find_element_by_optimized_selectors('post_button', timeout=10)
            
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
            if media_uploaded:
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
            file_input = self.find_element_by_optimized_selectors('reels_upload_input', timeout=10)
            
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
            next_button = self.find_element_by_optimized_selectors('reels_next_button', timeout=10)
            if next_button:
                if self.safe_click(next_button):
                    self._log("First 'Next' button clicked", "SUCCESS")
                    time.sleep(3)
            
            # Step 2: Second Next button (if exists)
            next_button = self.find_element_by_optimized_selectors('reels_next_button', timeout=5)
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
            publish_button = self.find_element_by_optimized_selectors('reels_publish_button', timeout=10)
            
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

    def show_performance_report(self):
        """Show detailed performance report"""
        self._log("📊 Facebook Selector Performance Report", "INFO")
        print("=" * 80)
        
        if not self.selector_performance.get("selector_stats"):
            self._log("No performance data available yet", "WARNING")
            return
        
        for selector_type, selectors in self.selector_performance["selector_stats"].items():
            print(f"\n🎯 {selector_type.upper()}:")
            print("-" * 60)
            
            # Sort by success rate
            sorted_selectors = sorted(
                selectors.items(),
                key=lambda x: x[1]["success_count"] / max(1, x[1]["success_count"] + x[1]["fail_count"]),
                reverse=True
            )
            
            for selector, stats in sorted_selectors:
                total_attempts = stats["success_count"] + stats["fail_count"]
                if total_attempts == 0:
                    continue
                
                success_rate = (stats["success_count"] / total_attempts) * 100
                avg_response_time = stats["total_response_time"] / total_attempts
                
                # Status indicators
                status = "✅" if success_rate > 80 else "⚠️" if success_rate > 50 else "❌"
                protected = "🛡️" if stats.get("is_protected", False) else ""
                removed = "🗑️" if stats.get("consecutive_fails", 0) >= 5 and not stats.get("is_protected", False) else ""
                
                print(f"{status} {protected} {removed} {success_rate:5.1f}% | {avg_response_time:5.2f}s | {selector[:50]}...")
                
                if self.debug:
                    print(f"    Success: {stats['success_count']}, Fails: {stats['fail_count']}, Consecutive Fails: {stats['consecutive_fails']}")
        
        print(f"\n📈 Total Operations: {self.selector_performance.get('total_operations', 0)}")
        
        if self.selector_performance.get("last_updated"):
            import datetime
            last_update = datetime.datetime.fromtimestamp(self.selector_performance["last_updated"])
            print(f"📅 Last Updated: {last_update.strftime('%Y-%m-%d %H:%M:%S')}")

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
    parser.add_argument("--show-performance", action="store_true", help="Show selector performance report")

    args = parser.parse_args()

    uploader = FacebookUploader(headless=args.headless, debug=args.debug)

    # Handle different actions
    if args.clear_cookies:
        uploader.clear_cookies()
        return

    if args.check_cookies:
        uploader.check_cookies_status()
        return

    if args.show_performance:
        uploader.show_performance_report()
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
        
        while True:
            print(f"\n{Fore.YELLOW}Choose action:")
            print("1. 📝 Upload Status (Text)")
            print("2. 🖼️ Upload Status (with Media)")
            print("3. 🎬 Upload Reels")
            print("4. 🍪 Check cookies status")
            print("5. 📊 Show performance report")
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
                
                status_text = input(f"{Fore.CYAN}Status text (optional): ").strip()
                
                result = uploader.upload_status(status_text, media_path)
                
                if result["success"]:
                    print(f"{Fore.GREEN}🎉 Facebook status with media uploaded successfully!")
                else:
                    print(f"{Fore.RED}❌ Facebook status upload failed: {result['message']}")
            
            elif choice == "3":
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
            
            elif choice == "4":
                uploader.check_cookies_status()
            
            elif choice == "5":
                uploader.show_performance_report()
            
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