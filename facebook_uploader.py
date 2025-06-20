#!/usr/bin/env python3
"""
Facebook Uploader - With PROPER validation
Memastikan text benar-benar terisi dan media benar-benar terupload sebelum bilang sukses
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
        """Initialize Facebook Uploader"""
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
        self.login_url = "https://www.facebook.com/login"
        self.facebook_url = "https://www.facebook.com"

    def _log(self, message: str, level: str = "INFO"):
        """Enhanced logging dengan warna"""
        colors = {
            "INFO": Fore.CYAN,
            "SUCCESS": Fore.GREEN,
            "WARNING": Fore.YELLOW,
            "ERROR": Fore.RED,
            "DEBUG": Fore.MAGENTA,
            "VALIDATION": Fore.BLUE
        }
        
        if level == "DEBUG" and not self.debug:
            return
            
        color = colors.get(level, Fore.WHITE)
        icons = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "DEBUG": "🔍",
            "VALIDATION": "🔎"
        }
        
        icon = icons.get(level, "📝")
        print(f"{color}{icon} {message}{Style.RESET_ALL}")

    def _setup_driver(self):
        """Setup Chrome WebDriver"""
        self._log("Setting up browser...")
        
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1280,800")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        if self.headless:
            chrome_options.add_argument('--headless=new')
        
        try:
            driver_path = ChromeDriverManager().install()
            service = Service(driver_path, log_path=os.devnull)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.wait = WebDriverWait(self.driver, 30)
            self._log("Browser ready!", "SUCCESS")
        except Exception as e:
            self._log(f"Browser setup failed: {str(e)}", "ERROR")
            raise

    def load_cookies(self) -> bool:
        """Load cookies"""
        if not self.cookies_path.exists():
            self._log("No cookies found", "WARNING")
            return False
            
        try:
            with open(self.cookies_path, 'r') as f:
                cookies_data = json.load(f)
            
            cookies = cookies_data.get('cookies', [])
            if not cookies:
                return False
            
            self.driver.get("https://www.facebook.com")
            time.sleep(2)
            
            cookies_added = 0
            for cookie in cookies:
                try:
                    self.driver.add_cookie({
                        'name': cookie['name'],
                        'value': cookie['value'],
                        'domain': cookie.get('domain', '.facebook.com'),
                        'path': cookie.get('path', '/')
                    })
                    cookies_added += 1
                except:
                    continue
            
            self._log(f"Cookies loaded: {cookies_added}/{len(cookies)}", "SUCCESS")
            return cookies_added > 0
            
        except Exception as e:
            self._log(f"Cookie load failed: {str(e)}", "ERROR")
            return False

    def save_cookies(self):
        """Save cookies"""
        try:
            cookies = self.driver.get_cookies()
            cookies_data = {
                "timestamp": int(time.time()),
                "cookies": cookies
            }
            
            with open(self.cookies_path, 'w') as f:
                json.dump(cookies_data, f, indent=2)
            
            self._log(f"Cookies saved: {len(cookies)}", "SUCCESS")
        except Exception as e:
            self._log(f"Cookie save failed: {str(e)}", "ERROR")

    def wait_for_login(self, timeout: int = 180):
        """Wait for manual login"""
        self._log("Please login manually in the browser...", "WARNING")
        self._log(f"Waiting for login (timeout {timeout}s)...", "INFO")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            current_url = self.driver.current_url
            
            if not ("login" in current_url or "checkpoint" in current_url):
                self._log("Login successful!", "SUCCESS")
                self.save_cookies()
                return True
            
            time.sleep(2)
        
        raise TimeoutException("Login timeout")

    def validate_text_input(self, text_input, expected_text: str) -> bool:
        """VALIDASI PROPER: Cek apakah text benar-benar terisi"""
        try:
            # Method 1: Cek value attribute
            current_value = text_input.get_attribute('value')
            if current_value and expected_text in current_value:
                self._log(f"✅ VALIDATION: Text found in value: '{current_value[:50]}...'", "VALIDATION")
                return True
            
            # Method 2: Cek innerHTML/textContent
            current_text = text_input.get_attribute('textContent') or text_input.get_attribute('innerHTML')
            if current_text and expected_text in current_text:
                self._log(f"✅ VALIDATION: Text found in content: '{current_text[:50]}...'", "VALIDATION")
                return True
            
            # Method 3: Cek dengan JavaScript
            js_text = self.driver.execute_script("return arguments[0].textContent || arguments[0].value || arguments[0].innerHTML;", text_input)
            if js_text and expected_text in js_text:
                self._log(f"✅ VALIDATION: Text found via JS: '{js_text[:50]}...'", "VALIDATION")
                return True
            
            self._log(f"❌ VALIDATION FAILED: Text not found. Expected: '{expected_text[:30]}...'", "ERROR")
            self._log(f"   Current value: '{current_value}'", "DEBUG")
            self._log(f"   Current text: '{current_text}'", "DEBUG")
            self._log(f"   JS text: '{js_text}'", "DEBUG")
            return False
            
        except Exception as e:
            self._log(f"❌ VALIDATION ERROR: {str(e)}", "ERROR")
            return False

    def validate_media_upload(self, media_path: str) -> bool:
        """VALIDASI PROPER: Cek apakah media benar-benar terupload"""
        try:
            filename = os.path.basename(media_path)
            file_extension = os.path.splitext(filename)[1].lower()
            
            # Wait a bit for upload to process
            time.sleep(3)
            
            # Method 1: Cek preview image/video
            preview_selectors = [
                f"img[alt*='{filename}']",
                f"video[src*='{filename}']",
                "div[data-testid*='media']",
                "div[aria-label*='photo']",
                "div[aria-label*='video']",
                ".media-preview",
                "[data-testid='media-preview']"
            ]
            
            for selector in preview_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        self._log(f"✅ VALIDATION: Media preview found with selector: {selector}", "VALIDATION")
                        return True
                except:
                    continue
            
            # Method 2: Cek file input value
            file_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
            for file_input in file_inputs:
                try:
                    input_value = file_input.get_attribute('value')
                    if input_value and filename in input_value:
                        self._log(f"✅ VALIDATION: File found in input value: {input_value}", "VALIDATION")
                        return True
                except:
                    continue
            
            # Method 3: Cek dengan JavaScript untuk file objects
            try:
                js_result = self.driver.execute_script("""
                    var fileInputs = document.querySelectorAll('input[type="file"]');
                    for (var i = 0; i < fileInputs.length; i++) {
                        if (fileInputs[i].files && fileInputs[i].files.length > 0) {
                            return fileInputs[i].files[0].name;
                        }
                    }
                    return null;
                """)
                
                if js_result and filename in js_result:
                    self._log(f"✅ VALIDATION: File found via JS: {js_result}", "VALIDATION")
                    return True
            except:
                pass
            
            self._log(f"❌ VALIDATION FAILED: Media not uploaded. Expected: {filename}", "ERROR")
            return False
            
        except Exception as e:
            self._log(f"❌ MEDIA VALIDATION ERROR: {str(e)}", "ERROR")
            return False

    def upload_status(self, status_text: str = "", media_path: str = "") -> Dict[str, Any]:
        """Upload status dengan VALIDASI PROPER"""
        try:
            self._setup_driver()
            self.load_cookies()
            
            # Navigate to Facebook
            self._log("Navigating to Facebook...")
            self.driver.get(self.facebook_url)
            time.sleep(5)
            
            # Check if login needed
            if "login" in self.driver.current_url or "checkpoint" in self.driver.current_url:
                self.wait_for_login()
                self.driver.get(self.facebook_url)
                time.sleep(5)
            
            # Take screenshot
            self.take_screenshot("facebook_before_post.png")
            
            # STEP 1: Find and click "What's on your mind" area
            self._log("🎯 STEP 1: Looking for status composer...")
            
            composer_selectors = [
                "div[role='textbox'][data-testid='status-attachment-mentions-input']",
                "div[role='textbox'][aria-label*='mind']",
                "div[contenteditable='true'][data-testid*='status']",
                "div[data-testid='status-attachment-mentions-input']",
                "textarea[placeholder*='mind']",
                "div[aria-label*=\"What's on your mind\"]"
            ]
            
            composer_element = None
            for selector in composer_selectors:
                try:
                    element = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    if element.is_displayed():
                        composer_element = element
                        self._log(f"✅ Found composer with selector: {selector}", "SUCCESS")
                        break
                except TimeoutException:
                    continue
            
            if not composer_element:
                # Fallback: Click any visible text input
                self._log("⚠️ Composer not found, trying fallback...", "WARNING")
                text_inputs = self.driver.find_elements(By.CSS_SELECTOR, "div[contenteditable='true'], textarea")
                for text_input in text_inputs:
                    if text_input.is_displayed():
                        composer_element = text_input
                        self._log("✅ Found fallback text input", "SUCCESS")
                        break
            
            if not composer_element:
                raise NoSuchElementException("Cannot find status composer")
            
            # Click composer to open it
            self._log("🖱️ Clicking composer...")
            composer_element.click()
            time.sleep(3)
            
            # STEP 2: Add text if provided
            text_added = False
            if status_text:
                self._log("🎯 STEP 2: Adding status text...")
                
                # Try to add text to the composer
                try:
                    composer_element.clear()
                    composer_element.send_keys(status_text)
                    time.sleep(2)
                    
                    # VALIDASI: Cek apakah text benar-benar terisi
                    if self.validate_text_input(composer_element, status_text):
                        text_added = True
                        self._log("✅ Status text successfully added and validated!", "SUCCESS")
                    else:
                        self._log("❌ Status text validation failed!", "ERROR")
                        return {"success": False, "message": "Text validation failed - text not properly added"}
                        
                except Exception as e:
                    self._log(f"❌ Failed to add text: {str(e)}", "ERROR")
                    return {"success": False, "message": f"Failed to add text: {str(e)}"}
            
            # STEP 3: Add media if provided
            media_added = False
            if media_path and os.path.exists(media_path):
                self._log("🎯 STEP 3: Adding media...")
                
                # Look for photo/video button or file input
                media_selectors = [
                    "input[type='file'][accept*='image']",
                    "input[type='file'][accept*='video']",
                    "input[type='file']",
                    "div[aria-label*='Photo/video']",
                    "div[data-testid*='photo']"
                ]
                
                file_input = None
                for selector in media_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            if element.get_attribute('type') == 'file':
                                file_input = element
                                break
                        if file_input:
                            break
                    except:
                        continue
                
                if file_input:
                    try:
                        abs_path = os.path.abspath(media_path)
                        file_input.send_keys(abs_path)
                        self._log(f"📎 Media file sent: {os.path.basename(media_path)}", "INFO")
                        
                        # VALIDASI: Cek apakah media benar-benar terupload
                        if self.validate_media_upload(media_path):
                            media_added = True
                            self._log("✅ Media successfully uploaded and validated!", "SUCCESS")
                        else:
                            self._log("❌ Media validation failed!", "ERROR")
                            return {"success": False, "message": "Media validation failed - file not properly uploaded"}
                            
                    except Exception as e:
                        self._log(f"❌ Failed to upload media: {str(e)}", "ERROR")
                        return {"success": False, "message": f"Failed to upload media: {str(e)}"}
                else:
                    self._log("❌ File input not found for media upload", "ERROR")
                    return {"success": False, "message": "Cannot find file input for media upload"}
            
            # STEP 4: Validate we have content to post
            if not text_added and not media_added:
                self._log("❌ No content added - nothing to post!", "ERROR")
                return {"success": False, "message": "No content added - both text and media validation failed"}
            
            # STEP 5: Find and click Post button
            self._log("🎯 STEP 4: Looking for Post button...")
            
            post_selectors = [
                "div[aria-label='Post'][role='button']",
                "button[data-testid*='post']",
                "div[role='button'][aria-label='Post']",
                "button:contains('Post')",
                "div[data-testid='react-composer-post-button']"
            ]
            
            post_button = None
            for selector in post_selectors:
                try:
                    if ':contains(' in selector:
                        # Use XPath for text-based selection
                        xpath = f"//button[contains(text(), 'Post')] | //div[contains(text(), 'Post') and @role='button']"
                        elements = self.driver.find_elements(By.XPATH, xpath)
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                post_button = element
                                break
                    else:
                        element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if element.is_displayed() and element.is_enabled():
                            post_button = element
                            break
                except:
                    continue
                
                if post_button:
                    break
            
            if not post_button:
                self._log("❌ Post button not found!", "ERROR")
                return {"success": False, "message": "Post button not found"}
            
            # Click Post button
            self._log("🖱️ Clicking Post button...")
            try:
                post_button.click()
                time.sleep(5)
                self._log("✅ Post button clicked!", "SUCCESS")
                
                # FINAL VALIDATION: Check if we're back to feed or see success indicators
                current_url = self.driver.current_url
                if "facebook.com" in current_url and "login" not in current_url:
                    self._log("✅ Successfully posted to Facebook!", "SUCCESS")
                    
                    # Take final screenshot
                    self.take_screenshot("facebook_after_post.png")
                    
                    return {
                        "success": True,
                        "message": "Status posted successfully",
                        "text_added": text_added,
                        "media_added": media_added,
                        "status_text": status_text if text_added else "",
                        "media_path": media_path if media_added else ""
                    }
                else:
                    return {"success": False, "message": "Post may have failed - unexpected page redirect"}
                    
            except Exception as e:
                self._log(f"❌ Failed to click Post button: {str(e)}", "ERROR")
                return {"success": False, "message": f"Failed to click Post button: {str(e)}"}
            
        except Exception as e:
            error_msg = f"Upload failed: {str(e)}"
            self._log(error_msg, "ERROR")
            self.take_screenshot("facebook_error.png")
            return {"success": False, "message": error_msg}
        
        finally:
            if self.driver:
                self._log("Closing browser...")
                try:
                    self.driver.quit()
                except:
                    pass

    def upload_reels(self, video_path: str, description: str = "") -> Dict[str, Any]:
        """Upload reels - using status upload with video"""
        self._log("Uploading video as Facebook Reels/Post...")
        return self.upload_status(description, video_path)

    def take_screenshot(self, filename: str):
        """Take screenshot"""
        try:
            screenshot_path = self.screenshots_dir / filename
            self.driver.save_screenshot(str(screenshot_path))
            self._log(f"Screenshot saved: {filename}", "INFO")
        except Exception as e:
            self._log(f"Screenshot failed: {str(e)}", "WARNING")

    def clear_cookies(self):
        """Clear cookies"""
        try:
            if self.cookies_path.exists():
                self.cookies_path.unlink()
                self._log("Cookies cleared", "SUCCESS")
            else:
                self._log("No cookies to clear", "WARNING")
        except Exception as e:
            self._log(f"Clear cookies failed: {str(e)}", "ERROR")

    def check_cookies_status(self):
        """Check cookies status"""
        if self.cookies_path.exists():
            try:
                with open(self.cookies_path, 'r') as f:
                    data = json.load(f)
                cookies = data.get('cookies', [])
                timestamp = data.get('timestamp', 0)
                
                self._log(f"Cookies found: {len(cookies)}", "SUCCESS")
                
                if timestamp:
                    import datetime
                    saved_time = datetime.datetime.fromtimestamp(timestamp)
                    self._log(f"Saved: {saved_time.strftime('%Y-%m-%d %H:%M:%S')}", "INFO")
                    
            except Exception as e:
                self._log(f"Cookies file corrupted: {str(e)}", "ERROR")
        else:
            self._log("No cookies found", "WARNING")


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(description="Facebook Uploader - With Proper Validation")
    parser.add_argument("--type", choices=['status', 'reels'], default='status', help="Upload type")
    parser.add_argument("--status", help="Status text")
    parser.add_argument("--media", help="Media file path")
    parser.add_argument("--video", help="Video file path (for reels)")
    parser.add_argument("--description", help="Description (for reels)")
    parser.add_argument("--headless", action="store_true", help="Headless mode")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    parser.add_argument("--clear-cookies", action="store_true", help="Clear cookies")
    parser.add_argument("--check-cookies", action="store_true", help="Check cookies")
    
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
            print(f"{Fore.RED}❌ Need status text or media file")
            return
        
        if args.media and not os.path.exists(args.media):
            print(f"{Fore.RED}❌ Media file not found: {args.media}")
            return
        
        result = uploader.upload_status(args.status or "", args.media or "")
        
        if result["success"]:
            print(f"{Fore.GREEN}🎉 Status posted successfully!")
            if result.get("text_added"):
                print(f"{Fore.CYAN}📝 Text: {result.get('status_text', '')[:50]}...")
            if result.get("media_added"):
                print(f"{Fore.CYAN}📎 Media: {os.path.basename(result.get('media_path', ''))}")
        else:
            print(f"{Fore.RED}❌ Status failed: {result['message']}")
    
    elif args.type == 'reels':
        if not args.video:
            print(f"{Fore.RED}❌ Need video file for reels")
            return
        
        if not os.path.exists(args.video):
            print(f"{Fore.RED}❌ Video file not found: {args.video}")
            return
        
        result = uploader.upload_reels(args.video, args.description or "")
        
        if result["success"]:
            print(f"{Fore.GREEN}🎉 Reels posted successfully!")
        else:
            print(f"{Fore.RED}❌ Reels failed: {result['message']}")
    
    else:
        # Interactive mode
        print(f"{Fore.CYAN}📘 Facebook Uploader - PROPER VALIDATION")
        print("=" * 60)
        print(f"{Fore.YELLOW}✅ Text validation - memastikan text benar-benar terisi")
        print(f"{Fore.YELLOW}✅ Media validation - memastikan file benar-benar terupload")
        print(f"{Fore.YELLOW}✅ No false positives - hanya bilang sukses kalau bener-bener sukses")
        print()
        
        while True:
            print(f"\n{Fore.YELLOW}Choose option:")
            print("1. 📝 Post Status (Text/Media)")
            print("2. 🎬 Upload Reels")
            print("3. 🍪 Check Cookies")
            print("4. 🗑️ Clear Cookies")
            print("5. ❌ Exit")
            
            choice = input(f"\n{Fore.WHITE}Choice (1-5): ").strip()
            
            if choice == "1":
                status_text = input(f"{Fore.CYAN}Status text (optional): ").strip()
                media_path = input(f"{Fore.CYAN}Media file path (optional): ").strip()
                
                if not status_text and not media_path:
                    print(f"{Fore.RED}❌ Need at least text or media!")
                    continue
                
                if media_path and not os.path.exists(media_path):
                    print(f"{Fore.RED}❌ Media file not found!")
                    continue
                
                print(f"\n{Fore.MAGENTA}🚀 Starting upload with PROPER validation...")
                result = uploader.upload_status(status_text, media_path)
                
                if result["success"]:
                    print(f"\n{Fore.GREEN}🎉 Status posted successfully!")
                    print(f"{Fore.GREEN}✅ Text added: {result.get('text_added', False)}")
                    print(f"{Fore.GREEN}✅ Media added: {result.get('media_added', False)}")
                else:
                    print(f"\n{Fore.RED}❌ Failed: {result['message']}")
            
            elif choice == "2":
                video_path = input(f"{Fore.CYAN}Video file path: ").strip()
                if not os.path.exists(video_path):
                    print(f"{Fore.RED}❌ Video file not found!")
                    continue
                
                description = input(f"{Fore.CYAN}Description (optional): ").strip()
                
                print(f"\n{Fore.MAGENTA}🚀 Starting reels upload...")
                result = uploader.upload_reels(video_path, description)
                
                if result["success"]:
                    print(f"\n{Fore.GREEN}🎉 Reels uploaded successfully!")
                else:
                    print(f"\n{Fore.RED}❌ Failed: {result['message']}")
            
            elif choice == "3":
                uploader.check_cookies_status()
            
            elif choice == "4":
                confirm = input(f"{Fore.YELLOW}Clear cookies? (y/N): ").strip().lower()
                if confirm == 'y':
                    uploader.clear_cookies()
            
            elif choice == "5":
                print(f"{Fore.YELLOW}👋 Bye!")
                break
            
            else:
                print(f"{Fore.RED}❌ Invalid choice!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}👋 Stopped by user")
    except Exception as e:
        print(f"{Fore.RED}💥 Fatal error: {str(e)}")
        sys.exit(1)