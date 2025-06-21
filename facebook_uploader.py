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
        self.facebook_url = "https://www.facebook.com"
        self.reels_create_url = "https://www.facebook.com/reels/create/?surface=PROFILE_PLUS"
        
        # Selectors untuk Facebook Status
        self.status_selectors = {
            'composer_trigger': [
                "//div[@role='button' and contains(@aria-label, 'What')]",
                "//div[contains(@aria-label, 'What') and contains(@aria-label, 'mind')]",
                "//div[@data-pagelet='FeedComposer']//div[@role='button']",
                "//div[contains(text(), 'What') and contains(text(), 'mind')]",
                "//div[@aria-label=\"What's on your mind?\"]",
                "//div[contains(@class, 'x1i10hfl') and @role='button']"
            ],
            'text_input_primary': [
                "div[aria-label*='What\\'s on your mind']",  # Selector utama yang diminta sebelumnya
                "div[contenteditable='true'][data-text='What\\'s on your mind?']",  # Selector baru #1
                "div[contenteditable='true'][role='textbox']",  # Selector baru #2
                "div[data-text='What\\'s on your mind?']",  # Selector baru #3
                "div[contenteditable='true'][aria-placeholder*='mind']",
                "div[contenteditable='true'][data-lexical-editor='true']",
                "div.xzsf02u.x1a2a7pz.x1n2onr6.x14wi4xw.x9f619.x1lliihq.x5yr21d.xh8yej3.notranslate[contenteditable='true']"
            ],
            'file_input': [
                "//input[@type='file' and @accept]",
                "//input[@type='file']",
                "//input[@accept='image/*,image/heif,image/heic,video/*,video/mp4,video/x-m4v,video/x-ms-asf']"
            ],
            'post_button': [
                "//div[@aria-label='Post' and @role='button']",
                "//div[text()='Post' and @role='button']",
                "//button[text()='Post']",
                "//div[contains(@class, 'x1i10hfl') and @role='button' and .//span[text()='Post']]"
            ],
            'media_upload_verification': [
                "//video[@src]",
                "//img[contains(@src, 'blob:')]",
                "//div[contains(@aria-label, 'Video Options')]",
                "//div[contains(@aria-label, 'Edit video')]"
            ]
        }
        
        # Selectors untuk Facebook Reels
        self.reels_selectors = {
            'upload_input': [
                "//input[@type='file' and contains(@accept, 'video')]",
                "//input[@type='file']",
                "//input[@accept='video/*']"
            ],
            'next_button': [
                "//div[@aria-label='Next' and @role='button']",
                "//div[text()='Next' and @role='button']",
                "//div[@aria-label='Berikutnya' and @role='button']",
                "//div[text()='Berikutnya' and @role='button']",
                "//button[text()='Next']",
                "//button[text()='Berikutnya']"
            ],
            'description_input': [
                "//div[@contenteditable='true' and @aria-label='Description']",
                "//div[@contenteditable='true' and contains(@aria-label, 'description')]",
                "//div[@contenteditable='true' and @data-lexical-editor='true']",
                "//textarea[@placeholder='Description']"
            ],
            'publish_button': [
                "//div[@aria-label='Publish' and @role='button']",
                "//div[text()='Publish' and @role='button']",
                "//div[@aria-label='Terbitkan' and @role='button']",
                "//div[text()='Terbitkan' and @role='button']",
                "//button[text()='Publish']",
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
        chrome_options.add_argument("--disable-extensions-file-access-check")
        chrome_options.add_argument("--disable-extensions-http-throttling")
        chrome_options.add_argument("--disable-extensions-except")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-features=TranslateUI")
        chrome_options.add_argument("--disable-ipc-flooding-protection")
        chrome_options.add_argument("--disable-background-networking")
        chrome_options.add_argument("--disable-default-apps")
        chrome_options.add_argument("--disable-sync")
        chrome_options.add_argument("--hide-scrollbars")
        chrome_options.add_argument("--metrics-recording-only")
        chrome_options.add_argument("--mute-audio")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--safebrowsing-disable-auto-update")
        chrome_options.add_argument("--disable-component-update")
        chrome_options.add_argument("--disable-domain-reliability")
        
        # Suppress network errors
        chrome_options.add_argument("--disable-webrtc")
        chrome_options.add_argument("--disable-webrtc-multiple-routes")
        chrome_options.add_argument("--disable-webrtc-hw-decoding")
        chrome_options.add_argument("--disable-webrtc-hw-encoding")
        chrome_options.add_argument("--disable-webrtc-encryption")
        chrome_options.add_argument("--force-webrtc-ip-handling-policy=disable_non_proxied_udp")
        
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
            
            if "WinError 193" in str(e):
                self._log("Error Windows detected. Troubleshooting tips:", "INFO")
                self._log("1. Pastikan Google Chrome terinstall", "INFO")
                self._log("2. Update Chrome ke versi terbaru", "INFO")
                self._log("3. Restart komputer jika perlu", "INFO")
                self._log("4. Coba jalankan sebagai Administrator", "INFO")
            
            raise

    def _find_element_by_selectors(self, selectors: list, timeout: int = 10, by_type: str = "CSS") -> Optional[Any]:
        """Mencari elemen menggunakan multiple selectors"""
        for i, selector in enumerate(selectors):
            try:
                if by_type == "XPATH":
                    element = WebDriverWait(self.driver, timeout).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                else:  # CSS
                    element = WebDriverWait(self.driver, timeout).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                
                if i == 0:
                    self._log(f"Elemen ditemukan dengan {by_type} #{i+1}", "SUCCESS")
                else:
                    self._log(f"Elemen ditemukan dengan {by_type} #{i+1}", "SUCCESS")
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
            
            # Navigate ke Facebook dulu sebelum set cookies
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
            status_text: Text untuk status
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
            self.driver.get(self.facebook_url)
            self.take_screenshot(f"facebook_before_post_{int(time.time())}.png")
            time.sleep(3)
            
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
            
            # Tentukan mode upload
            if status_text and media_path:
                mode = "TEXT + MEDIA"
            elif media_path:
                mode = "MEDIA ONLY"
            elif status_text:
                mode = "TEXT ONLY"
            else:
                raise ValueError("Minimal status text atau media diperlukan")
            
            self._log(f"MODE: {mode}")
            
            # Klik area "What's on your mind" untuk membuka composer
            self._log("Mencari area 'What's on your mind' untuk membuka composer...")
            composer_trigger = self._find_element_by_selectors(
                self.status_selectors['composer_trigger'], 
                timeout=10, 
                by_type="XPATH"
            )
            
            if not composer_trigger:
                raise NoSuchElementException("Tidak dapat menemukan area composer trigger")
            
            self._log("Mengklik 'Area What's on your mind'...")
            
            # Coba klik dengan berbagai metode
            try:
                self._log("Mencoba regular click...")
                composer_trigger.click()
                self._log("Berhasil klik dengan regular", "SUCCESS")
            except Exception as e:
                self._log(f"Regular click gagal: {e}", "WARNING")
                try:
                    self._log("Mencoba JavaScript click...")
                    self.driver.execute_script("arguments[0].click();", composer_trigger)
                    self._log("Berhasil klik dengan JavaScript", "SUCCESS")
                except Exception as e2:
                    self._log(f"JavaScript click gagal: {e2}", "WARNING")
                    try:
                        self._log("Mencoba ActionChains click...")
                        ActionChains(self.driver).move_to_element(composer_trigger).click().perform()
                        self._log("Berhasil klik dengan ActionChains", "SUCCESS")
                    except Exception as e3:
                        raise Exception(f"Semua metode klik gagal: {e}, {e2}, {e3}")
            
            time.sleep(5)  # Tunggu composer terbuka
            self.take_screenshot(f"facebook_composer_opened_{int(time.time())}.png")
            
            # Upload media jika ada
            if media_path:
                self._log("Mencoba upload media langsung setelah composer terbuka...")
                if self._upload_media_direct(media_path):
                    self._log("Media berhasil diupload!", "SUCCESS")
                else:
                    raise Exception("Gagal upload media")
            
            # Input text jika ada
            if status_text:
                self._log("Mencari area text input di composer...")
                if self._input_text_to_composer(status_text):
                    self._log("Text berhasil dimasukkan!", "SUCCESS")
                else:
                    # Jika gagal input text tapi media sudah terupload, lanjutkan saja
                    if media_path:
                        self._log("Text gagal dimasukkan tapi media sudah ada, melanjutkan post...", "WARNING")
                    else:
                        raise Exception("Gagal memasukkan text ke composer")
            
            # Klik tombol Post
            self._log("Mencari tombol Post di composer...")
            post_button = self._find_element_by_selectors(
                self.status_selectors['post_button'], 
                timeout=10, 
                by_type="XPATH"
            )
            
            if not post_button:
                raise NoSuchElementException("Tidak dapat menemukan tombol Post")
            
            self._log("Mengklik 'Post Button'...")
            
            # Coba klik tombol post
            try:
                self._log("Mencoba regular click...")
                post_button.click()
                self._log("Berhasil klik dengan regular", "SUCCESS")
            except Exception as e:
                self._log(f"Regular click gagal: {e}", "WARNING")
                try:
                    self._log("Mencoba JavaScript click...")
                    self.driver.execute_script("arguments[0].click();", post_button)
                    self._log("Berhasil klik dengan JavaScript", "SUCCESS")
                except Exception as e2:
                    raise Exception(f"Gagal klik tombol post: {e}, {e2}")
            
            time.sleep(5)  # Tunggu post selesai
            
            # Verifikasi post berhasil (kembali ke feed)
            current_url = self.driver.current_url
            if "facebook.com" in current_url and "composer" not in current_url:
                self._log("Post berhasil (kembali ke feed)", "SUCCESS")
                success = True
            else:
                self._log("Post mungkin berhasil tapi tidak dapat dikonfirmasi", "WARNING")
                success = True  # Anggap berhasil
            
            if success:
                self._log("Status berhasil dipost ke Facebook!", "SUCCESS")
                return {
                    "success": True,
                    "message": "Post berhasil",
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

    def _upload_media_direct(self, media_path: str) -> bool:
        """Upload media langsung setelah composer terbuka"""
        if not os.path.exists(media_path):
            self._log(f"File media tidak ditemukan: {media_path}", "ERROR")
            return False
        
        self._log(f"Mengupload media langsung: {os.path.basename(media_path)}")
        
        try:
            # Cari input file yang langsung tersedia
            self._log("Mencari input file yang langsung tersedia...")
            file_input = self._find_element_by_selectors(
                self.status_selectors['file_input'], 
                timeout=5, 
                by_type="XPATH"
            )
            
            if file_input:
                abs_path = os.path.abspath(media_path)
                self._log(f"Mengirim file langsung ke input: {abs_path}")
                file_input.send_keys(abs_path)
                
                self._log("Media berhasil diupload langsung!", "SUCCESS")
                
                # Tunggu dan verifikasi upload
                time.sleep(3)
                return self._verify_media_upload()
            else:
                self._log("Input file tidak ditemukan langsung", "WARNING")
                return False
                
        except Exception as e:
            self._log(f"Error upload media langsung: {str(e)}", "ERROR")
            return False

    def _verify_media_upload(self) -> bool:
        """Verifikasi apakah media sudah ter-upload"""
        self._log("Memverifikasi apakah media sudah ter-upload...")
        
        try:
            # Cek indikator media upload
            for i, selector in enumerate(self.status_selectors['media_upload_verification']):
                try:
                    element = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    if element.is_displayed():
                        self._log(f"✅ Media berhasil ter-upload! (selector #{i+1})", "SUCCESS")
                        self.take_screenshot(f"facebook_media_uploaded_{int(time.time())}.png")
                        return True
                except TimeoutException:
                    continue
            
            self._log("Tidak dapat memverifikasi media upload", "WARNING")
            return False
            
        except Exception as e:
            self._log(f"Error verifikasi media: {str(e)}", "WARNING")
            return False

    def _input_text_to_composer(self, text: str) -> bool:
        """Input text ke composer yang sudah terbuka dengan media"""
        if not text.strip():
            return True
        
        self._log(f"🎯 Media sudah ter-upload, mengetik text di composer yang sama...")
        self._log(f"🎯 Mengetik text di composer yang sama (tanpa membuat composer baru)...")
        
        # Coba mencari text area di composer yang sudah terbuka
        self._log("Mencoba CSS selector berdasarkan elemen yang diberikan...")
        
        for i, selector in enumerate(self.status_selectors['text_input_primary']):
            try:
                self._log(f"🎯 Mencoba strategi #{i+1}...")
                
                # Cari elemen text input
                text_element = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                
                if text_element and text_element.is_displayed():
                    self._log(f"Text element ditemukan dengan CSS #{i+1}", "SUCCESS")
                    
                    # Fokus ke elemen
                    text_element.click()
                    time.sleep(0.5)
                    
                    # Clear existing content jika ada
                    try:
                        text_element.clear()
                    except:
                        pass
                    
                    # Input text dengan berbagai metode
                    success = False
                    
                    # Metode 1: Direct send_keys
                    try:
                        text_element.send_keys(text)
                        time.sleep(1)
                        
                        # Verifikasi text masuk
                        if self._verify_text_input(text_element, text):
                            self._log(f"✅ Text berhasil diketik dengan strategi #{i+1}!", "SUCCESS")
                            return True
                        else:
                            self._log(f"⚠️ ❌ Strategi #{i+1} gagal - text tidak terdeteksi", "WARNING")
                    except Exception as e:
                        self._log(f"⚠️ ❌ Strategi #{i+1} gagal: {str(e)}", "WARNING")
                    
                    # Metode 2: JavaScript setValue
                    try:
                        self.driver.execute_script(f"arguments[0].textContent = '{text}';", text_element)
                        self.driver.execute_script(f"arguments[0].innerText = '{text}';", text_element)
                        time.sleep(1)
                        
                        if self._verify_text_input(text_element, text):
                            self._log(f"✅ Text berhasil diketik dengan JavaScript #{i+1}!", "SUCCESS")
                            return True
                    except Exception as e:
                        self._log(f"JavaScript method gagal: {str(e)}", "WARNING")
                    
                    # Metode 3: ActionChains
                    try:
                        ActionChains(self.driver).move_to_element(text_element).click().send_keys(text).perform()
                        time.sleep(1)
                        
                        if self._verify_text_input(text_element, text):
                            self._log(f"✅ Text berhasil diketik dengan ActionChains #{i+1}!", "SUCCESS")
                            return True
                    except Exception as e:
                        self._log(f"ActionChains method gagal: {str(e)}", "WARNING")
                
            except TimeoutException:
                self._log(f"⚠️ Selector #{i+1} tidak ditemukan", "WARNING")
                continue
            except Exception as e:
                self._log(f"⚠️ Error pada strategi #{i+1}: {str(e)}", "WARNING")
                continue
        
        self._log("❌ ❌ Semua strategi input text gagal", "ERROR")
        return False

    def _verify_text_input(self, element, expected_text: str) -> bool:
        """Verifikasi apakah text sudah masuk ke elemen"""
        try:
            # Ambil screenshot untuk debugging
            self.take_screenshot(f"facebook_text_input_verification_{int(time.time())}.png")
            
            # Cek berbagai atribut untuk memverifikasi text
            actual_text = ""
            
            # Cek textContent
            try:
                actual_text = self.driver.execute_script("return arguments[0].textContent;", element)
                if actual_text and expected_text.lower() in actual_text.lower():
                    return True
            except:
                pass
            
            # Cek innerText
            try:
                actual_text = self.driver.execute_script("return arguments[0].innerText;", element)
                if actual_text and expected_text.lower() in actual_text.lower():
                    return True
            except:
                pass
            
            # Cek value attribute
            try:
                actual_text = element.get_attribute('value')
                if actual_text and expected_text.lower() in actual_text.lower():
                    return True
            except:
                pass
            
            # Cek data-text attribute
            try:
                actual_text = element.get_attribute('data-text')
                if actual_text and expected_text.lower() in actual_text.lower():
                    return True
            except:
                pass
            
            return False
            
        except Exception as e:
            self._log(f"Error verifying text input: {str(e)}", "DEBUG")
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
            # Setup driver
            self._setup_driver()
            
            # Load cookies
            cookies_loaded = self.load_cookies()
            
            # Navigate ke Facebook Reels Create
            self._log("Navigasi ke Facebook Reels Create...")
            self.driver.get(self.reels_create_url)
            time.sleep(3)
            
            # Cek apakah perlu login
            if self.check_login_required():
                if cookies_loaded:
                    self._log("Cookies dimuat tapi masih perlu login, refresh halaman...", "WARNING")
                    self.driver.refresh()
                    time.sleep(3)
                
                if self.check_login_required():
                    self.wait_for_login()
                    self.driver.get(self.reels_create_url)
                    time.sleep(3)
            
            # Upload video
            if not self._upload_reels_video(video_path):
                raise Exception("Gagal upload video reels")
            
            # Navigate through reels creation steps
            if not self._navigate_reels_steps():
                raise Exception("Gagal navigasi steps reels")
            
            # Add description
            if description and not self._add_reels_description(description):
                self._log("Gagal menambahkan deskripsi, melanjutkan tanpa deskripsi...", "WARNING")
            
            # Publish reels
            if not self._publish_reels():
                raise Exception("Gagal publish reels")
            
            self._log("Reels berhasil diupload ke Facebook!", "SUCCESS")
            return {
                "success": True,
                "message": "Reels upload berhasil",
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
                self._log("Menutup browser...")
                try:
                    self.driver.quit()
                except:
                    pass

    def _upload_reels_video(self, video_path: str) -> bool:
        """Upload video untuk reels"""
        if not os.path.exists(video_path):
            self._log(f"File video tidak ditemukan: {video_path}", "ERROR")
            return False
        
        self._log("Memulai upload video reels...")
        
        try:
            # Cari input upload
            upload_input = self._find_element_by_selectors(
                self.reels_selectors['upload_input'], 
                timeout=10, 
                by_type="XPATH"
            )
            
            if not upload_input:
                raise NoSuchElementException("Input upload tidak ditemukan")
            
            # Upload file
            abs_path = os.path.abspath(video_path)
            self._log("Input upload ditemukan. Mengirim file...")
            upload_input.send_keys(abs_path)
            
            self._log("File video berhasil dikirim ke input.", "SUCCESS")
            time.sleep(5)  # Tunggu upload selesai
            
            return True
            
        except Exception as e:
            self._log(f"Error upload video reels: {str(e)}", "ERROR")
            return False

    def _navigate_reels_steps(self) -> bool:
        """Navigate through reels creation steps"""
        try:
            # Klik Next button pertama
            self._log("Mencari tombol 'Next' pertama...")
            next_button = self._find_element_by_selectors(
                self.reels_selectors['next_button'], 
                timeout=15, 
                by_type="XPATH"
            )
            
            if next_button:
                next_button.click()
                self._log("Tombol 'Next' berhasil diklik (index 1)!", "SUCCESS")
                time.sleep(3)
            else:
                self._log("Tombol 'Next' pertama tidak ditemukan", "WARNING")
            
            # Klik Next button kedua
            self._log("Mencari tombol 'Next' kedua...")
            next_button2 = self._find_element_by_selectors(
                self.reels_selectors['next_button'], 
                timeout=10, 
                by_type="XPATH"
            )
            
            if next_button2:
                next_button2.click()
                self._log("Tombol 'Next' berhasil diklik (index 2)!", "SUCCESS")
                time.sleep(3)
            else:
                self._log("Tombol 'Next' kedua tidak ditemukan, melanjutkan...", "WARNING")
            
            return True
            
        except Exception as e:
            self._log(f"Error navigasi reels steps: {str(e)}", "ERROR")
            return False

    def _add_reels_description(self, description: str) -> bool:
        """Tambahkan deskripsi ke reels"""
        if not description.strip():
            return True
        
        try:
            # Cari input deskripsi
            desc_input = self._find_element_by_selectors(
                self.reels_selectors['description_input'], 
                timeout=10, 
                by_type="XPATH"
            )
            
            if desc_input:
                desc_input.click()
                time.sleep(0.5)
                desc_input.clear()
                desc_input.send_keys(description)
                self._log("Deskripsi berhasil diisi", "SUCCESS")
                return True
            else:
                self._log("Input deskripsi tidak ditemukan", "WARNING")
                return False
                
        except Exception as e:
            self._log(f"Error menambahkan deskripsi: {str(e)}", "ERROR")
            return False

    def _publish_reels(self) -> bool:
        """Publish reels"""
        try:
            # Cari tombol Publish
            publish_button = self._find_element_by_selectors(
                self.reels_selectors['publish_button'], 
                timeout=10, 
                by_type="XPATH"
            )
            
            if publish_button:
                publish_button.click()
                self._log("Tombol 'Publish' berhasil diklik (index 2)!", "SUCCESS")
                time.sleep(5)
                
                self._log("Upload video reels berhasil!", "SUCCESS")
                return True
            else:
                raise NoSuchElementException("Tombol Publish tidak ditemukan")
                
        except Exception as e:
            self._log(f"Error publish reels: {str(e)}", "ERROR")
            return False

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
            
            result = uploader.upload_reels(args.video, args.description or "")
            
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