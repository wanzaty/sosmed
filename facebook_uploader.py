#!/usr/bin/env python3
"""
Facebook Uploader - Simplified approach using Creator Studio
Lebih reliable daripada main Facebook feed
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
        
        # Facebook URLs - SIMPLIFIED
        self.login_url = "https://www.facebook.com/login"
        self.creator_studio_url = "https://business.facebook.com/creatorstudio"
        self.pages_url = "https://www.facebook.com/pages"
        
        # SUPER SIMPLE selectors
        self.selectors = {
            # Creator Studio selectors
            'create_post_button': [
                "button[data-testid='create_post_button']",
                "div[aria-label='Create post']",
                "button:contains('Create post')",
                "a[href*='create']",
                "[data-testid*='create']"
            ],
            
            # Simple text input
            'text_input': [
                "div[contenteditable='true']",
                "textarea",
                "div[role='textbox']",
                "[data-testid*='text']",
                "[aria-label*='text']"
            ],
            
            # File upload
            'file_input': [
                "input[type='file']",
                "input[accept*='video']",
                "input[accept*='image']"
            ],
            
            # Publish button
            'publish_button': [
                "button:contains('Publish')",
                "button:contains('Post')",
                "button:contains('Share')",
                "[data-testid*='publish']",
                "[data-testid*='post']"
            ]
        }

    def _log(self, message: str, level: str = "INFO"):
        """Simple logging"""
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

    def _setup_driver(self):
        """Setup Chrome WebDriver - SIMPLE"""
        self._log("Setting up browser...")
        
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1280,800")
        chrome_options.add_argument("--log-level=3")
        
        if self.headless:
            chrome_options.add_argument('--headless=new')
        
        try:
            driver_path = ChromeDriverManager().install()
            service = Service(driver_path, log_path=os.devnull)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 30)
            self._log("Browser ready!", "SUCCESS")
        except Exception as e:
            self._log(f"Browser setup failed: {str(e)}", "ERROR")
            raise

    def load_cookies(self) -> bool:
        """Load cookies - SIMPLE"""
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
            
            for cookie in cookies:
                try:
                    self.driver.add_cookie({
                        'name': cookie['name'],
                        'value': cookie['value'],
                        'domain': cookie.get('domain', '.facebook.com'),
                        'path': cookie.get('path', '/')
                    })
                except:
                    continue
            
            self._log(f"Cookies loaded: {len(cookies)}", "SUCCESS")
            return True
            
        except Exception as e:
            self._log(f"Cookie load failed: {str(e)}", "ERROR")
            return False

    def save_cookies(self):
        """Save cookies - SIMPLE"""
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

    def simple_upload_status(self, status_text: str = "", media_path: str = "") -> Dict[str, Any]:
        """SUPER SIMPLE status upload"""
        try:
            self._log("🚀 SIMPLE APPROACH: Using Creator Studio...")
            
            # Go to Creator Studio
            self.driver.get(self.creator_studio_url)
            time.sleep(5)
            
            # Check if login needed
            if "login" in self.driver.current_url:
                self.wait_for_login()
                self.driver.get(self.creator_studio_url)
                time.sleep(5)
            
            # Take screenshot
            self.take_screenshot("creator_studio.png")
            
            # Method 1: Try Creator Studio
            try:
                self._log("Method 1: Creator Studio approach...")
                
                # Look for create post button
                for selector in self.selectors['create_post_button']:
                    try:
                        button = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if button.is_displayed():
                            button.click()
                            self._log("Create post button clicked!", "SUCCESS")
                            time.sleep(3)
                            break
                    except:
                        continue
                
                # Add text if provided
                if status_text:
                    for selector in self.selectors['text_input']:
                        try:
                            text_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                            if text_input.is_displayed():
                                text_input.click()
                                text_input.send_keys(status_text)
                                self._log("Text added!", "SUCCESS")
                                break
                        except:
                            continue
                
                # Add media if provided
                if media_path and os.path.exists(media_path):
                    for selector in self.selectors['file_input']:
                        try:
                            file_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                            file_input.send_keys(os.path.abspath(media_path))
                            self._log("Media uploaded!", "SUCCESS")
                            time.sleep(5)
                            break
                        except:
                            continue
                
                # Publish
                for selector in self.selectors['publish_button']:
                    try:
                        publish_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if publish_btn.is_displayed() and publish_btn.is_enabled():
                            publish_btn.click()
                            self._log("Published!", "SUCCESS")
                            time.sleep(3)
                            return {"success": True, "message": "Posted via Creator Studio"}
                    except:
                        continue
                        
            except Exception as e:
                self._log(f"Creator Studio failed: {e}", "WARNING")
            
            # Method 2: Try Facebook Pages
            try:
                self._log("Method 2: Facebook Pages approach...")
                
                self.driver.get(self.pages_url)
                time.sleep(5)
                
                # Simple approach - just find any text input and post button
                text_inputs = self.driver.find_elements(By.CSS_SELECTOR, "div[contenteditable='true'], textarea")
                if text_inputs:
                    text_input = text_inputs[0]
                    text_input.click()
                    if status_text:
                        text_input.send_keys(status_text)
                    
                    # Look for file input if media provided
                    if media_path and os.path.exists(media_path):
                        file_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                        if file_inputs:
                            file_inputs[0].send_keys(os.path.abspath(media_path))
                            time.sleep(5)
                    
                    # Find and click post button
                    post_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Post') or contains(text(), 'Share') or contains(text(), 'Publish')]")
                    if post_buttons:
                        post_buttons[0].click()
                        self._log("Posted via Pages!", "SUCCESS")
                        return {"success": True, "message": "Posted via Facebook Pages"}
                        
            except Exception as e:
                self._log(f"Pages approach failed: {e}", "WARNING")
            
            # Method 3: Direct Facebook with simple approach
            try:
                self._log("Method 3: Direct Facebook simple approach...")
                
                self.driver.get("https://www.facebook.com")
                time.sleep(5)
                
                # Just find ANY text input and try to post
                all_inputs = self.driver.find_elements(By.CSS_SELECTOR, "div[contenteditable='true'], textarea, div[role='textbox']")
                
                for text_input in all_inputs:
                    try:
                        if text_input.is_displayed():
                            text_input.click()
                            time.sleep(1)
                            
                            if status_text:
                                text_input.send_keys(status_text)
                                time.sleep(2)
                            
                            # Try to find post button nearby
                            post_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Post') or contains(text(), 'Share')]")
                            for btn in post_buttons:
                                if btn.is_displayed() and btn.is_enabled():
                                    btn.click()
                                    self._log("Posted via direct Facebook!", "SUCCESS")
                                    return {"success": True, "message": "Posted via direct Facebook"}
                            break
                    except:
                        continue
                        
            except Exception as e:
                self._log(f"Direct Facebook failed: {e}", "WARNING")
            
            return {"success": False, "message": "All methods failed - Facebook might have changed"}
            
        except Exception as e:
            error_msg = f"Upload failed: {str(e)}"
            self._log(error_msg, "ERROR")
            self.take_screenshot("error.png")
            return {"success": False, "message": error_msg}

    def upload_status(self, status_text: str = "", media_path: str = "") -> Dict[str, Any]:
        """Main upload method"""
        try:
            self._setup_driver()
            self.load_cookies()
            
            return self.simple_upload_status(status_text, media_path)
            
        finally:
            if self.driver:
                self._log("Closing browser...")
                try:
                    self.driver.quit()
                except:
                    pass

    def upload_reels(self, video_path: str, description: str = "") -> Dict[str, Any]:
        """Upload reels - simplified"""
        self._log("Reels upload - using simple video upload method...")
        return self.upload_status(description, video_path)

    def take_screenshot(self, filename: str):
        """Take screenshot"""
        try:
            screenshot_path = self.screenshots_dir / filename
            self.driver.save_screenshot(str(screenshot_path))
            self._log(f"Screenshot: {filename}", "INFO")
        except:
            pass

    def clear_cookies(self):
        """Clear cookies"""
        try:
            if self.cookies_path.exists():
                self.cookies_path.unlink()
                self._log("Cookies cleared", "SUCCESS")
        except Exception as e:
            self._log(f"Clear cookies failed: {str(e)}", "ERROR")

    def check_cookies_status(self):
        """Check cookies status"""
        if self.cookies_path.exists():
            try:
                with open(self.cookies_path, 'r') as f:
                    data = json.load(f)
                cookies = data.get('cookies', [])
                self._log(f"Cookies found: {len(cookies)}", "SUCCESS")
            except:
                self._log("Cookies file corrupted", "ERROR")
        else:
            self._log("No cookies found", "WARNING")


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(description="Facebook Uploader - SIMPLE")
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
        
        result = uploader.upload_status(args.status or "", args.media or "")
        
        if result["success"]:
            print(f"{Fore.GREEN}🎉 Status posted successfully!")
        else:
            print(f"{Fore.RED}❌ Status failed: {result['message']}")
    
    elif args.type == 'reels':
        if not args.video:
            print(f"{Fore.RED}❌ Need video file for reels")
            return
        
        result = uploader.upload_reels(args.video, args.description or "")
        
        if result["success"]:
            print(f"{Fore.GREEN}🎉 Reels posted successfully!")
        else:
            print(f"{Fore.RED}❌ Reels failed: {result['message']}")
    
    else:
        # Interactive mode
        print(f"{Fore.CYAN}📘 Facebook Uploader - SIMPLE VERSION")
        print("=" * 50)
        
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
                
                result = uploader.upload_status(status_text, media_path)
                
                if result["success"]:
                    print(f"{Fore.GREEN}🎉 Status posted!")
                else:
                    print(f"{Fore.RED}❌ Failed: {result['message']}")
            
            elif choice == "2":
                video_path = input(f"{Fore.CYAN}Video file path: ").strip()
                if not os.path.exists(video_path):
                    print(f"{Fore.RED}❌ Video file not found!")
                    continue
                
                description = input(f"{Fore.CYAN}Description (optional): ").strip()
                
                result = uploader.upload_reels(video_path, description)
                
                if result["success"]:
                    print(f"{Fore.GREEN}🎉 Reels uploaded!")
                else:
                    print(f"{Fore.RED}❌ Failed: {result['message']}")
            
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