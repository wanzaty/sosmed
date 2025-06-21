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
        
        # AGGRESSIVE SELECTORS - Multiple strategies untuk membuka composer
        self.whats_on_mind_selectors = {
            'exact_selectors': [
                "#mount_0_0_oA > div > div:nth-child(1) > div > div.x9f619.x1n2onr6.x1ja2u2z > div > div > div.x78zum5.xdt5ytf.x1t2pt76.x1n2onr6.x1ja2u2z.x10cihs4 > div.x9f619.x1ja2u2z.x78zum5.x2lah0s.x1n2onr6.xl56j7k.x1qjc9v5.xozqiw3.x1q0g3np.x1t2pt76.x17upfok > div > div.x9f619.x1ja2u2z.x78zum5.x1n2onr6.x1iyjqo2.xs83m0k.xeuugli.xl56j7k.x1qjc9v5.xozqiw3.x1q0g3np.x1iplk16.x1mfogq2.xsfy40s.x1wi7962.xpi1e93 > div > div > div > div.x78zum5.x1q0g3np.xl56j7k > div > div.x1yztbdb > div > div > div > div.x1cy8zhl.x78zum5.x1iyjqo2.xs83m0k.xh8yej3 > div > div.xi81zsa.x1lkfr7t.xkjl1po.x1mzt3pk.xh8yej3.x13faqbe > span"
            ],
            'fallback_selectors': [
                "span[class*='x1lliihq'][class*='x6ikm8r'][class*='x10wlt62'][class*='x1n2onr6']",
                "div[class*='xi81zsa'][class*='x1lkfr7t']",
                "div[role='button'][aria-label*='What']",
                "div[role='button'][aria-label*='Apa yang']",
                "span:contains('What\\'s on your mind')",
                "span:contains('Apa yang Anda pikirkan')",
                "div[data-pagelet='FeedComposer'] div[role='button']",
                "[data-testid='status-attachment-mentions-input']",
                "div[contenteditable='true'][role='textbox']"
            ],
            'xpath_selectors': [
                "//span[contains(text(), 'What\\'s on your mind')]",
                "//span[contains(text(), 'Apa yang Anda pikirkan')]",
                "//div[@role='button' and contains(@aria-label, 'What')]",
                "//div[@role='button' and contains(@aria-label, 'Apa yang')]",
                "//div[contains(@class, 'xi81zsa') and contains(@class, 'x1lkfr7t')]",
                "//div[@data-pagelet='FeedComposer']//div[@role='button']"
            ]
        }
        
        # COMPOSER VALIDATION SELECTORS
        self.composer_indicators = [
            "div[contenteditable='true'][role='textbox']",
            "form[method='post']",
            "div[aria-label='Post'][role='button']",
            "div[aria-label='Posting'][role='button']",
            "textarea[placeholder*='mind']",
            "textarea[placeholder*='pikirkan']",
            "div[data-testid='status-attachment-mentions-input']",
            "#mount_0_0_oA > div > div:nth-child(1) > div > div:nth-child(5) > div > div > div.x9f619.x1n2onr6.x1ja2u2z > div > div.x1uvtmcs.x4k7w5x.x1h91t0o.x1beo9mf.xaigb6o.x12ejxvf.x3igimt.xarpa2k.xedcshv.x1lytzrv.x1t2pt76.x7ja8zs.x1n2onr6.x1qrby5j.x1jfb8zj > div > div > div > form"
        ]
        
        # TEXT INPUT SELECTORS
        self.text_input_selectors = [
            "#mount_0_0_oA > div > div:nth-child(1) > div > div:nth-child(5) > div > div > div.x9f619.x1n2onr6.x1ja2u2z > div > div.x1uvtmcs.x4k7w5x.x1h91t0o.x1beo9mf.xaigb6o.x12ejxvf.x3igimt.xarpa2k.xedcshv.x1lytzrv.x1t2pt76.x7ja8zs.x1n2onr6.x1qrby5j.x1jfb8zj > div > div > div > form > div > div.x9f619.x1ja2u2z.x1k90msu.x6o7n8i.x1qfuztq.x1o0tod.x10l6tqk.x13vifvy.x1hc1fzr.x71s49j > div > div > div > div.xb57i2i.x1q594ok.x5lxg6s.x6ikm8r.x1ja2u2z.x1pq812k.x1rohswg.xfk6m8.x1yqm8si.xjx87ck.xx8ngbg.xwo3gff.x1n2onr6.x1oyok0e.x1odjw0f.x1e4zzel.x78zum5.xdt5ytf.x1iyjqo2 > div.x78zum5.xdt5ytf.x1iyjqo2.x1n2onr6 > div.x1ed109x.x1iyjqo2.x5yr21d.x1n2onr6.xh8yej3 > div.x9f619.x1iyjqo2.xg7h5cd.xv54qhq.xf7dkkf.x1n2onr6.xh8yej3.x1ja2u2z.x1t1ogtf > div > div > div.xzsf02u.x1a2a7pz.x1n2onr6.x14wi4xw.x9f619.x1lliihq.x5yr21d.xh8yej3.notranslate > p",
            "div[contenteditable='true'][role='textbox']",
            "div[contenteditable='true'][data-text*='What']",
            "div[contenteditable='true'][data-text*='Apa yang']",
            "textarea[placeholder*='mind']",
            "textarea[placeholder*='pikirkan']",
            "div[data-testid='status-attachment-mentions-input']"
        ]
        
        # POST BUTTON SELECTORS
        self.post_button_selectors = [
            "#mount_0_0_oA > div > div:nth-child(1) > div > div:nth-child(5) > div > div > div.x9f619.x1n2onr6.x1ja2u2z > div > div.x1uvtmcs.x4k7w5x.x1h91t0o.x1beo9mf.xaigb6o.x12ejxvf.x3igimt.xarpa2k.xedcshv.x1lytzrv.x1t2pt76.x7ja8zs.x1n2onr6.x1qrby5j.x1jfb8zj > div > div > div > form > div > div.x9f619.x1ja2u2z.x1k90msu.x6o7n8i.x1qfuztq.x1o0tod.x10l6tqk.x13vifvy.x1hc1fzr.x71s49j > div > div > div > div.x1l90r2v.xyamay9.x1n2onr6 > div.x9f619.x1ja2u2z.x78zum5.x1n2onr6.x1r8uery.x1iyjqo2.xs83m0k.xeuugli.x1qughib.x6s0dn4.xozqiw3.x1q0g3np.xv54qhq.xf7dkkf.xyamay9.x1lxpwgx.x165d6jo.x4vbgl9.x1rdy4ex > div > div > div > div.html-div.xdj266r.xat24cr.xexx8yu.xyri2b.x18d9i69.x1c1uobl.x6s0dn4.x78zum5.xl56j7k.x14ayic.xwyz465.x1e0frkt > div > span > span",
            "div[aria-label='Post'][role='button']",
            "div[aria-label='Posting'][role='button']",
            "button[data-testid='react-composer-post-button']",
            "div[role='button'][aria-label*='Post']",
            "div[role='button'][aria-label*='Posting']"
        ]

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

    def _validate_composer_opened(self) -> bool:
        """Validasi ketat apakah composer benar-benar terbuka"""
        self._log("🔍 🔍 VALIDATING: Checking if composer is really open...", "INFO")
        
        found_indicators = 0
        
        for selector in self.composer_indicators:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                visible_elements = [elem for elem in elements if elem.is_displayed()]
                
                if visible_elements:
                    found_indicators += 1
                    if self.debug:
                        self._log(f"Found composer indicator: {selector[:50]}...", "DEBUG")
                        
            except Exception as e:
                if self.debug:
                    self._log(f"Error checking indicator {selector[:30]}...: {e}", "DEBUG")
        
        self._log(f"🔍 Found {found_indicators} composer indicators", "INFO")
        
        if found_indicators >= 2:
            self._log("✅ ✅ ✅ VALIDATION SUCCESS: Composer is open", "SUCCESS")
            return True
        else:
            self._log(f"❌ ❌ ❌ VALIDATION FAILED: Composer not open ({found_indicators} indicators found)", "ERROR")
            return False

    def _validate_text_input_success(self, expected_text: str, text_element) -> bool:
        """Validasi ketat apakah text benar-benar terinput"""
        self._log("🔍 🔍 VALIDATING: Checking if text is really inputted...", "INFO")
        
        # Multiple methods untuk mendapatkan text content
        text_methods = [
            lambda: text_element.get_attribute('textContent'),
            lambda: text_element.get_attribute('innerText'),
            lambda: text_element.get_attribute('value'),
            lambda: text_element.text,
            lambda: self.driver.execute_script("return arguments[0].textContent;", text_element),
            lambda: self.driver.execute_script("return arguments[0].innerText;", text_element)
        ]
        
        for i, method in enumerate(text_methods, 1):
            try:
                current_text = method()
                if current_text and expected_text.strip() in current_text:
                    self._log(f"✅ ✅ ✅ TEXT VALIDATION SUCCESS: Text found with method {i}", "SUCCESS")
                    self._log(f"Expected: '{expected_text}', Found: '{current_text[:100]}...'", "INFO")
                    return True
            except Exception as e:
                if self.debug:
                    self._log(f"Text validation method {i} failed: {e}", "DEBUG")
        
        self._log(f"❌ ❌ ❌ TEXT VALIDATION FAILED: Text not found", "ERROR")
        return False

    def _validate_post_click_success(self) -> bool:
        """Validasi ketat apakah post benar-benar berhasil"""
        self._log("🔍 🔍 VALIDATING: Checking if post was successful...", "INFO")
        
        # Tunggu sebentar untuk perubahan URL
        time.sleep(3)
        
        current_url = self.driver.current_url
        
        # Cek apakah URL berubah atau kembali ke feed
        if 'facebook.com' in current_url and not any(keyword in current_url for keyword in ['composer', 'create', 'post']):
            self._log("✅ ✅ ✅ POST VALIDATION SUCCESS: Returned to feed", "SUCCESS")
            return True
        
        # Cek apakah composer masih ada
        try:
            composer_elements = self.driver.find_elements(By.CSS_SELECTOR, "div[contenteditable='true'][role='textbox']")
            visible_composers = [elem for elem in composer_elements if elem.is_displayed()]
            
            if not visible_composers:
                self._log("✅ ✅ ✅ POST VALIDATION SUCCESS: Composer closed", "SUCCESS")
                return True
            else:
                self._log(f"❌ ❌ ❌ POST VALIDATION FAILED: Composer still open ({len(visible_composers)} found)", "ERROR")
                return False
                
        except Exception as e:
            self._log(f"Error validating post: {e}", "WARNING")
            return False

    def _click_element_safely(self, element, description: str = "element"):
        """Click element dengan multiple fallback methods dan validasi ketat"""
        
        # VALIDASI SEBELUM KLIK
        if not element.is_displayed():
            self._log(f"❌ Element {description} not visible", "ERROR")
            return False
        
        if not element.is_enabled():
            self._log(f"❌ Element {description} not enabled", "ERROR")
            return False
        
        # Method 1: Regular click
        try:
            self._log(f"🖱️ Attempting regular click on {description}...", "INFO")
            element.click()
            self._log(f"✅ ✅ ✅ CLICK SUCCESS: Regular click on {description}", "SUCCESS")
            return True
        except Exception as e:
            self._log(f"⚠️ Regular click failed on {description}: {str(e)}", "WARNING")
        
        # Method 2: JavaScript click
        try:
            self._log(f"🖱️ Attempting JavaScript click on {description}...", "INFO")
            self.driver.execute_script("arguments[0].click();", element)
            self._log(f"✅ ✅ ✅ CLICK SUCCESS: JavaScript click on {description}", "SUCCESS")
            return True
        except Exception as e:
            self._log(f"⚠️ JavaScript click failed on {description}: {str(e)}", "WARNING")
        
        # Method 3: ActionChains
        try:
            self._log(f"🖱️ Attempting ActionChains click on {description}...", "INFO")
            ActionChains(self.driver).move_to_element(element).click().perform()
            self._log(f"✅ ✅ ✅ CLICK SUCCESS: ActionChains click on {description}", "SUCCESS")
            return True
        except Exception as e:
            self._log(f"⚠️ ActionChains click failed on {description}: {str(e)}", "WARNING")
        
        # Method 4: Send ENTER key
        try:
            self._log(f"🖱️ Attempting ENTER key on {description}...", "INFO")
            element.send_keys(Keys.ENTER)
            self._log(f"✅ ✅ ✅ CLICK SUCCESS: ENTER key on {description}", "SUCCESS")
            return True
        except Exception as e:
            self._log(f"⚠️ ENTER key failed on {description}: {str(e)}", "WARNING")
        
        # Method 5: Send SPACE key
        try:
            self._log(f"🖱️ Attempting SPACE key on {description}...", "INFO")
            element.send_keys(Keys.SPACE)
            self._log(f"✅ ✅ ✅ CLICK SUCCESS: SPACE key on {description}", "SUCCESS")
            return True
        except Exception as e:
            self._log(f"⚠️ SPACE key failed on {description}: {str(e)}", "WARNING")
        
        self._log(f"❌ ❌ ❌ ALL CLICK METHODS FAILED for {description}", "ERROR")
        return False

    def _find_whats_on_mind_element(self):
        """Aggressive search untuk 'What's on your mind' element"""
        self._log("🎯 🎯 STEP 1: Looking for 'What's on your mind' click element...", "INFO")
        
        # Try exact selectors first
        for i, selector in enumerate(self.whats_on_mind_selectors['exact_selectors']):
            try:
                element = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                self._log(f"✅ ✅ ✅ Found element with EXACT selector (priority {i+1})", "SUCCESS")
                return element
            except TimeoutException:
                continue
        
        self._log("⚠️ ⚠️ ⚠️ Exact selector not found, trying fallbacks...", "WARNING")
        
        # Try fallback CSS selectors
        for i, selector in enumerate(self.whats_on_mind_selectors['fallback_selectors']):
            try:
                element = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                self._log(f"⚠️ ⚠️ ⚠️ Exact selector not found, using fallback #{i+1}", "WARNING")
                return element
            except TimeoutException:
                continue
        
        self._log("⚠️ ⚠️ ⚠️ CSS selectors failed, trying XPath...", "WARNING")
        
        # Try XPath selectors
        for i, xpath in enumerate(self.whats_on_mind_selectors['xpath_selectors']):
            try:
                element = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                self._log(f"⚠️ ⚠️ ⚠️ Found with XPath #{i+1}", "WARNING")
                return element
            except TimeoutException:
                continue
        
        # Last resort: Find by text content
        self._log("⚠️ ⚠️ ⚠️ XPath failed, trying text search...", "WARNING")
        
        try:
            # Find all clickable elements
            all_elements = self.driver.find_elements(By.CSS_SELECTOR, "*[role='button'], span, div")
            
            for element in all_elements:
                try:
                    text = element.text.lower()
                    if any(phrase in text for phrase in ["what's on your mind", "apa yang anda pikirkan", "what's on", "apa yang"]):
                        if element.is_displayed() and element.is_enabled():
                            self._log("⚠️ ⚠️ ⚠️ Found with text search", "WARNING")
                            return element
                except:
                    continue
        except Exception as e:
            self._log(f"Text search failed: {e}", "ERROR")
        
        return None

    def _open_composer_aggressively(self):
        """Aggressive method untuk membuka composer dengan multiple strategies"""
        
        # Strategy 1: Find and click "What's on your mind"
        whats_on_mind = self._find_whats_on_mind_element()
        
        if whats_on_mind:
            self._log("✅ ℹ️ ✅ Found 'What's on your mind' click element", "SUCCESS")
            self._log("ℹ️ ℹ️ 🖱️ Clicking 'What's on your mind' element...", "INFO")
            
            if self._click_element_safely(whats_on_mind, "'What's on your mind' click"):
                time.sleep(2)  # Wait for composer to load
                
                if self._validate_composer_opened():
                    return True
                else:
                    self._log("⚠️ ⚠️ Composer not opened after click, trying alternative strategies...", "WARNING")
        else:
            self._log("❌ ❌ 'What's on your mind' element not found", "ERROR")
        
        # Strategy 2: Try to find composer directly (maybe it's already open)
        self._log("🎯 🎯 STRATEGY 2: Looking for composer directly...", "INFO")
        
        for selector in self.text_input_selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                if element.is_displayed():
                    self._log("✅ ✅ Found composer directly!", "SUCCESS")
                    return True
            except:
                continue
        
        # Strategy 3: Try keyboard shortcut (Ctrl+Shift+P for Facebook post)
        self._log("🎯 🎯 STRATEGY 3: Trying keyboard shortcut...", "INFO")
        
        try:
            body = self.driver.find_element(By.TAG_NAME, "body")
            body.send_keys(Keys.CONTROL + Keys.SHIFT + "p")
            time.sleep(2)
            
            if self._validate_composer_opened():
                self._log("✅ ✅ Composer opened with keyboard shortcut!", "SUCCESS")
                return True
        except Exception as e:
            self._log(f"Keyboard shortcut failed: {e}", "WARNING")
        
        # Strategy 4: Navigate to specific URL
        self._log("🎯 🎯 STRATEGY 4: Trying direct URL navigation...", "INFO")
        
        try:
            self.driver.get("https://www.facebook.com/?sk=h_chr")
            time.sleep(3)
            
            if self._validate_composer_opened():
                self._log("✅ ✅ Composer opened with URL navigation!", "SUCCESS")
                return True
        except Exception as e:
            self._log(f"URL navigation failed: {e}", "WARNING")
        
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
        Upload status ke Facebook dengan dukungan text + media
        
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
            if status_text.strip() and media_path and os.path.exists(media_path):
                mode = "TEXT + MEDIA"
            elif status_text.strip():
                mode = "TEXT ONLY"
            elif media_path and os.path.exists(media_path):
                mode = "MEDIA ONLY"
            else:
                raise ValueError("Minimal status text atau media diperlukan")
            
            self._log(f"🎯 🎯 MODE: {mode}", "INFO")
            
            # STEP 1: Open composer aggressively
            if not self._open_composer_aggressively():
                raise Exception("Composer tidak terbuka setelah semua strategi dicoba")
            
            # STEP 2: Input text if provided
            if status_text.strip():
                self._log("🎯 🎯 STEP 2: Adding status text...", "INFO")
                
                text_input = None
                for selector in self.text_input_selectors:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if element.is_displayed():
                            text_input = element
                            self._log(f"✅ ✅ Found text input with selector: {selector[:50]}...", "SUCCESS")
                            break
                    except:
                        continue
                
                if not text_input:
                    raise NoSuchElementException("Tidak dapat menemukan text input")
                
                # Click text input
                if not self._click_element_safely(text_input, "text input"):
                    raise Exception("Gagal mengklik text input")
                
                time.sleep(1)
                
                # Input text with multiple methods
                success = False
                methods = [
                    lambda: self._input_text_method_1(text_input, status_text),
                    lambda: self._input_text_method_2(text_input, status_text),
                    lambda: self._input_text_method_3(text_input, status_text)
                ]
                
                for i, method in enumerate(methods, 1):
                    try:
                        self._log(f"🖊️ Trying text input method {i}...", "INFO")
                        if method():
                            time.sleep(1)
                            if self._validate_text_input_success(status_text, text_input):
                                self._log(f"✅ ✅ ✅ STEP 2 COMPLETE: Status text added successfully with method {i}", "SUCCESS")
                                success = True
                                break
                    except Exception as e:
                        self._log(f"Method {i} failed: {str(e)}", "WARNING")
                        continue
                
                if not success:
                    raise Exception("Gagal menambahkan status text setelah semua method dicoba")
            
            # STEP 3: Add media if provided
            if media_path and os.path.exists(media_path):
                self._log("🎯 🎯 STEP 3: Adding media...", "INFO")
                
                # Find Photo/Video button
                photo_video_selectors = [
                    "//div[contains(text(), 'Photo/video')]",
                    "//div[contains(text(), 'Foto/video')]",
                    "//div[@aria-label='Photo/video']",
                    "//div[@aria-label='Foto/video']",
                    "//div[@role='button' and contains(@aria-label, 'Photo')]",
                    "//div[@role='button' and contains(@aria-label, 'Foto')]"
                ]
                
                photo_video_button = None
                for xpath in photo_video_selectors:
                    try:
                        element = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, xpath))
                        )
                        photo_video_button = element
                        self._log(f"✅ ✅ Found Photo/Video button", "SUCCESS")
                        break
                    except TimeoutException:
                        continue
                
                if not photo_video_button:
                    raise NoSuchElementException("Tidak dapat menemukan tombol Photo/Video")
                
                if not self._click_element_safely(photo_video_button, "Photo/Video button"):
                    raise Exception("Gagal mengklik tombol Photo/Video")
                
                time.sleep(2)
                
                # Find file input
                file_input_selectors = [
                    "input[type='file'][accept*='image']",
                    "input[type='file'][accept*='video']",
                    "input[type='file']"
                ]
                
                file_input = None
                for selector in file_input_selectors:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        file_input = element
                        self._log(f"✅ ✅ Found file input", "SUCCESS")
                        break
                    except:
                        continue
                
                if not file_input:
                    raise NoSuchElementException("Tidak dapat menemukan file input")
                
                # Upload file
                abs_path = os.path.abspath(media_path)
                file_input.send_keys(abs_path)
                
                self._log("✅ ✅ ✅ STEP 3 COMPLETE: Media uploaded successfully", "SUCCESS")
                time.sleep(3)  # Wait for media processing
            
            # STEP 4: Click Post button
            self._log("🎯 🎯 STEP 4: Clicking Post button...", "INFO")
            
            post_button = None
            for selector in self.post_button_selectors:
                try:
                    element = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    post_button = element
                    self._log(f"✅ ✅ Found Post button", "SUCCESS")
                    break
                except TimeoutException:
                    continue
            
            if not post_button:
                raise NoSuchElementException("Tidak dapat menemukan tombol Post")
            
            if not self._click_element_safely(post_button, "Post button"):
                raise Exception("Gagal mengklik tombol Post")
            
            # Validate post success
            if self._validate_post_click_success():
                self._log("✅ ✅ ✅ ✅ Facebook status posted successfully!", "SUCCESS")
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
                    "message": "Post mungkin gagal - tidak dapat dikonfirmasi",
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
            
            upload_input = None
            for selector in upload_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    upload_input = element
                    break
                except:
                    continue
            
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
                    next_button = None
                    for xpath in next_selectors:
                        try:
                            element = WebDriverWait(self.driver, 10).until(
                                EC.element_to_be_clickable((By.XPATH, xpath))
                            )
                            next_button = element
                            break
                        except TimeoutException:
                            continue
                    
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
                
                desc_input = None
                for selector in description_selectors:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if element.is_displayed():
                            desc_input = element
                            break
                    except:
                        continue
                
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
                    publish_button = None
                    for xpath in publish_selectors:
                        try:
                            element = WebDriverWait(self.driver, 10).until(
                                EC.element_to_be_clickable((By.XPATH, xpath))
                            )
                            publish_button = element
                            break
                        except TimeoutException:
                            continue
                    
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
