#!/usr/bin/env python3
"""
Yandex Image Scraper
Download images from Yandex Images using text search or reverse image search
"""

import os
import sys
import time
import argparse
import requests
import json
import urllib.parse
from pathlib import Path
from urllib.parse import urlencode, quote
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import re


class YandexImageScraper:
    """Scraper for downloading images from Yandex Images"""

    def __init__(self, headless=True, debug=False, disable_filters=False):
        """
        Initialize the scraper

        Args:
            headless (bool): Run browser in headless mode
            debug (bool): Enable debug mode (saves screenshots, prints HTML)
            disable_filters (bool): Disable SafeSearch/content filtering
        """
        self.headless = headless
        self.debug = debug
        self.disable_filters = disable_filters
        self.driver = None

    def _init_driver(self):
        """Initialize the Selenium WebDriver"""
        if self.driver is not None:
            return

        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        # Additional options to avoid detection
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        except Exception as e:
            print(f"Error initializing Chrome driver: {e}")
            print("Make sure chromedriver is installed and in PATH")
            sys.exit(1)

    def _debug_save_screenshot(self, name="debug"):
        """Save a screenshot for debugging"""
        if self.debug and self.driver:
            try:
                filename = f"{name}_{int(time.time())}.png"
                self.driver.save_screenshot(filename)
                print(f"[DEBUG] Screenshot saved: {filename}")
            except Exception as e:
                print(f"[DEBUG] Failed to save screenshot: {e}")

    def _debug_print_page_info(self):
        """Print page information for debugging"""
        if self.debug and self.driver:
            try:
                print(f"[DEBUG] Current URL: {self.driver.current_url}")
                print(f"[DEBUG] Page title: {self.driver.title}")

                # Save page source
                filename = f"page_source_{int(time.time())}.html"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source)
                print(f"[DEBUG] Page source saved: {filename}")
            except Exception as e:
                print(f"[DEBUG] Failed to print page info: {e}")

    def _create_folder(self, folder_name):
        """
        Create a folder for storing images

        Args:
            folder_name (str): Name of the folder

        Returns:
            Path: Path object for the folder
        """
        # Sanitize folder name
        folder_name = re.sub(r'[<>:"/\\|?*]', '_', folder_name)
        folder_path = Path(folder_name)
        folder_path.mkdir(exist_ok=True)
        return folder_path

    def _download_image(self, url, filepath):
        """
        Download an image from URL

        Args:
            url (str): Image URL
            filepath (Path): Path to save the image

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10, stream=True)
            response.raise_for_status()

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except Exception as e:
            print(f"Error downloading {url}: {e}")
            return False

    def _scroll_page(self, scroll_pause_time=2):
        """Scroll down the page to load more images"""
        last_height = self.driver.execute_script("return document.body.scrollHeight")

        while True:
            # Scroll down
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause_time)

            # Calculate new scroll height
            new_height = self.driver.execute_script("return document.body.scrollHeight")

            if new_height == last_height:
                break
            last_height = new_height

    def _extract_image_urls(self, num_images):
        """
        Extract image URLs from the page

        Args:
            num_images (int): Number of images to extract

        Returns:
            list: List of image URLs
        """
        image_urls = set()
        scroll_attempts = 0
        max_scroll_attempts = 15

        while len(image_urls) < num_images and scroll_attempts < max_scroll_attempts:
            if self.debug:
                print(f"[DEBUG] Scroll attempt {scroll_attempts + 1}, found {len(image_urls)} images so far")

            # Scroll to load more images
            if scroll_attempts > 0:
                self._scroll_page(scroll_pause_time=1.5)

            time.sleep(1)  # Give page time to load

            # NEW APPROACH: Get ALL img tags and ALL links, then filter
            if scroll_attempts == 1 and self.debug:
                # Count all images on page for debugging
                all_imgs = self.driver.find_elements(By.TAG_NAME, 'img')
                all_links = self.driver.find_elements(By.TAG_NAME, 'a')
                print(f"[DEBUG] Total <img> tags on page: {len(all_imgs)}")
                print(f"[DEBUG] Total <a> tags on page: {len(all_links)}")

            # Method 1: Extract from link hrefs (Yandex often stores URLs in links)
            try:
                links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="img_url="]')
                if self.debug and scroll_attempts == 1:
                    print(f"[DEBUG] Found {len(links)} links with img_url parameter")

                for idx, link in enumerate(links):
                    try:
                        href = link.get_attribute('href')
                        if href and 'img_url=' in href:
                            parsed = urllib.parse.urlparse(href)
                            params = urllib.parse.parse_qs(parsed.query)
                            if 'img_url' in params:
                                img_url = params['img_url'][0]
                                if img_url.startswith('http') and len(img_url) > 30:
                                    image_urls.add(img_url)
                                    if self.debug and len(image_urls) <= 5:
                                        print(f"[DEBUG] Extracted from link href: {img_url[:100]}")

                        if len(image_urls) >= num_images:
                            break
                    except Exception as e:
                        if self.debug:
                            print(f"[DEBUG] Error parsing link: {e}")
            except Exception as e:
                if self.debug:
                    print(f"[DEBUG] Error finding links: {e}")

            # Method 2: Try broad img selector, filter out unwanted ones
            for selector in ['img', 'a img', 'div[class*="serp"] img', 'div[class*="item"] img']:
                try:
                    images = self.driver.find_elements(By.CSS_SELECTOR, selector)

                    if self.debug and images:
                        print(f"[DEBUG] Selector '{selector}' found {len(images)} elements")

                    for idx, img in enumerate(images):
                        try:
                            # Skip the reverse image search button
                            img_class = img.get_attribute('class') or ''
                            if 'cbir-intent__thumb' in img_class:
                                if self.debug and scroll_attempts == 1 and idx < 5:
                                    print(f"[DEBUG] Skipping cbir-intent button")
                                continue

                            # Debug: Print all attributes for first few REAL elements
                            if self.debug and len(image_urls) < 3 and scroll_attempts == 1:
                                print(f"[DEBUG] Examining element {idx} (class: {img_class[:50]}):")

                                # Get all possible attributes
                                attrs_to_check = ['src', 'data-src', 'data-bem', 'data-image',
                                                 'data-url', 'srcset', 'data-lazy-src']
                                for attr in attrs_to_check:
                                    val = img.get_attribute(attr)
                                    if val:
                                        print(f"[DEBUG]   {attr}: {val[:150]}")

                                # Check parent element href
                                try:
                                    parent = img.find_element(By.XPATH, '..')
                                    parent_href = parent.get_attribute('href')
                                    if parent_href:
                                        print(f"[DEBUG]   Parent href: {parent_href[:150]}")
                                except:
                                    pass

                            # Try different attributes for the image URL
                            src = None

                            # Try standard attributes
                            for attr in ['src', 'data-src', 'data-image', 'data-url', 'data-lazy-src']:
                                src = img.get_attribute(attr)
                                if src and src.startswith('http'):
                                    break

                            # Try srcset
                            if not src:
                                srcset = img.get_attribute('srcset')
                                if srcset:
                                    urls = [u.strip().split()[0] for u in srcset.split(',')]
                                    if urls and urls[0].startswith('http'):
                                        src = urls[0]

                            # Try data-bem (JSON attribute)
                            if not src:
                                data_bem = img.get_attribute('data-bem')
                                if data_bem:
                                    try:
                                        bem_data = json.loads(data_bem)
                                        if isinstance(bem_data, dict):
                                            for key in ['url', 'img_url', 'origin_url', 'preview_url']:
                                                if key in bem_data:
                                                    src = bem_data[key]
                                                    if src:
                                                        break
                                    except:
                                        pass

                            # Try parent element href
                            if not src:
                                try:
                                    parent = img.find_element(By.XPATH, '..')
                                    href = parent.get_attribute('href')
                                    if href and 'img_url=' in href:
                                        parsed = urllib.parse.urlparse(href)
                                        params = urllib.parse.parse_qs(parsed.query)
                                        if 'img_url' in params:
                                            src = params['img_url'][0]
                                except:
                                    pass

                            # Validate and add URL
                            if src and src.startswith('http') and len(src) > 30:
                                # Filter out unwanted URLs
                                if not any(x in src.lower() for x in ['avatar', 'logo', 'icon', 'button']):
                                    image_urls.add(src)
                                    if self.debug and len(image_urls) <= 5:
                                        print(f"[DEBUG] Added image URL {len(image_urls)}: {src[:100]}")

                            if len(image_urls) >= num_images:
                                break
                        except Exception as e:
                            if self.debug:
                                print(f"[DEBUG] Error processing image element: {e}")
                            continue

                    if len(image_urls) >= num_images:
                        break

                except Exception as e:
                    if self.debug:
                        print(f"[DEBUG] Error with selector '{selector}': {e}")

            scroll_attempts += 1

            # If still no images found on first attempt, try clicking on an image
            if len(image_urls) == 0 and scroll_attempts == 1:
                if self.debug:
                    print("[DEBUG] No images found, trying to click on first search result")
                try:
                    clickable_items = self.driver.find_elements(By.CSS_SELECTOR,
                        '.serp-item, .serp-item__link, a[class*="serp"]')
                    if clickable_items:
                        clickable_items[0].click()
                        time.sleep(2)
                        if self.debug:
                            self._debug_save_screenshot("after_click")
                except Exception as e:
                    if self.debug:
                        print(f"[DEBUG] Failed to click on item: {e}")

        if self.debug:
            print(f"[DEBUG] Extraction complete. Found {len(image_urls)} total images")

        return list(image_urls)[:num_images]

    def search_and_download(self, search_term, num_images=10, folder_name=None):
        """
        Search for images by text and download them

        Args:
            search_term (str): Search query
            num_images (int): Number of images to download
            folder_name (str): Custom folder name (default: search_term)

        Returns:
            int: Number of images successfully downloaded
        """
        self._init_driver()

        # Create folder
        if folder_name is None:
            folder_name = search_term
        folder_path = self._create_folder(folder_name)

        # Build Yandex Images search URL
        search_url = f"https://yandex.com/images/search?text={quote(search_term)}"

        # Disable SafeSearch/filtering if requested
        if self.disable_filters:
            search_url += "&family=no"
            if self.debug:
                print("[DEBUG] SafeSearch disabled (family=no)")

        print(f"Searching Yandex Images for: {search_term}")
        print(f"URL: {search_url}")
        self.driver.get(search_url)

        # Wait for page to load with multiple possible selectors
        selectors_to_wait = [
            '.serp-item',
            '.SimpleImage',
            'img[class*="serp"]',
            'img[class*="thumb"]',
            '.gallery',
            'div[class*="serp"]'
        ]

        page_loaded = False
        for selector in selectors_to_wait:
            try:
                if self.debug:
                    print(f"[DEBUG] Waiting for selector: {selector}")
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                if self.debug:
                    print(f"[DEBUG] Found selector: {selector}")
                page_loaded = True
                break
            except TimeoutException:
                continue

        if not page_loaded:
            print("Timeout waiting for search results")
            print("The page structure might have changed or Yandex is blocking automated access.")
            print("Try running with --no-headless --debug to see what's happening.")

            if self.debug:
                self._debug_save_screenshot("timeout_error")
                self._debug_print_page_info()

            return 0

        # Additional wait for images to load
        time.sleep(2)

        if self.debug:
            self._debug_save_screenshot("after_page_load")

        # Extract image URLs
        print(f"Extracting image URLs...")
        image_urls = self._extract_image_urls(num_images)

        if not image_urls:
            print("No images found!")
            return 0

        print(f"Found {len(image_urls)} images. Starting download...")

        # Download images
        downloaded = 0
        for i, url in enumerate(image_urls, 1):
            # Determine file extension from URL
            ext = '.jpg'
            if '.png' in url.lower():
                ext = '.png'
            elif '.gif' in url.lower():
                ext = '.gif'
            elif '.webp' in url.lower():
                ext = '.webp'

            filepath = folder_path / f"image_{i:03d}{ext}"

            print(f"Downloading {i}/{len(image_urls)}: {url[:60]}...")
            if self._download_image(url, filepath):
                downloaded += 1

        print(f"\nSuccessfully downloaded {downloaded}/{num_images} images to {folder_path}/")
        return downloaded

    def reverse_image_search(self, image_path, num_images=10, folder_name=None):
        """
        Perform reverse image search and download similar images

        Args:
            image_path (str): Path to the image file
            num_images (int): Number of images to download
            folder_name (str): Custom folder name (default: 'reverse_search_results')

        Returns:
            int: Number of images successfully downloaded
        """
        self._init_driver()

        # Check if image exists
        image_path = Path(image_path)
        if not image_path.exists():
            print(f"Error: Image file not found: {image_path}")
            return 0

        # Create folder
        if folder_name is None:
            folder_name = f"reverse_search_{image_path.stem}"
        folder_path = self._create_folder(folder_name)

        print(f"Performing reverse image search for: {image_path}")

        # Go to Yandex Images
        if self.debug:
            print("[DEBUG] Loading Yandex Images homepage")

        # Build URL with optional filter disabling
        homepage_url = "https://yandex.com/images/"
        if self.disable_filters:
            homepage_url += "?family=no"
            if self.debug:
                print("[DEBUG] SafeSearch disabled (family=no)")

        self.driver.get(homepage_url)
        time.sleep(2)

        if self.debug:
            self._debug_save_screenshot("reverse_homepage")

        # Try to find and click the camera/upload button
        camera_button = None
        camera_selectors = [
            'button.CBIr',
            'button[class*="cbir"]',
            'button[class*="Cbir"]',
            'button[class*="CBIR"]',
            '.search-by-image__button',
            'button[aria-label*="image"]',
            'button[aria-label*="Search"]',
            '[class*="camera"]',
            'div.cbir-panel__button',
            'div[class*="CbirButton"]',
            '.SerpHeaderActions button',
            '.HeaderActions button',
            'button[type="button"]',
            'div[role="button"]',
            'span[role="button"]'
        ]

        if self.debug:
            print("[DEBUG] Looking for camera/upload button...")

        # Method 1: Try CSS selectors
        for selector in camera_selectors:
            try:
                if self.debug:
                    print(f"[DEBUG] Trying selector: {selector}")

                buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if buttons:
                    if self.debug:
                        print(f"[DEBUG] Found {len(buttons)} elements with selector: {selector}")
                    # Filter buttons that might be the camera button
                    for btn in buttons:
                        try:
                            btn_class = btn.get_attribute('class') or ''
                            btn_aria = btn.get_attribute('aria-label') or ''
                            btn_title = btn.get_attribute('title') or ''

                            if any(x in btn_class.lower() for x in ['cbir', 'camera', 'upload', 'image']) or \
                               any(x in btn_aria.lower() for x in ['image', 'camera', 'upload', 'search']) or \
                               any(x in btn_title.lower() for x in ['image', 'camera', 'upload']):
                                camera_button = btn
                                if self.debug:
                                    print(f"[DEBUG] Selected button with class='{btn_class[:50]}', aria-label='{btn_aria[:50]}'")
                                break
                        except:
                            continue

                    if camera_button:
                        break
            except Exception as e:
                if self.debug:
                    print(f"[DEBUG] Selector failed: {e}")
                continue

        # Method 2: Try to find by XPath looking for text/SVG icons
        if not camera_button and self.debug:
            print("[DEBUG] Trying XPath methods...")
            try:
                # Look for buttons/links that might contain camera icon or "search by image" text
                xpath_selectors = [
                    "//button[contains(@class, 'cbir') or contains(@class, 'Cbir')]",
                    "//button[contains(@aria-label, 'image')]",
                    "//div[@role='button' and contains(@class, 'cbir')]",
                    "//*[contains(text(), 'Search by image')]",
                    "//*[contains(text(), 'image search')]",
                    "//button[.//svg]"  # Buttons with SVG icons
                ]

                for xpath in xpath_selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, xpath)
                        if elements:
                            if self.debug:
                                print(f"[DEBUG] XPath found {len(elements)} elements: {xpath[:50]}")
                            camera_button = elements[0]
                            break
                    except:
                        continue
            except Exception as e:
                if self.debug:
                    print(f"[DEBUG] XPath search failed: {e}")

        # Method 3: Try finding file input directly (it might exist without clicking button)
        if not camera_button:
            if self.debug:
                print("[DEBUG] Camera button not found, looking for file input directly...")

            file_inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input[type="file"]')
            if file_inputs:
                if self.debug:
                    print(f"[DEBUG] Found {len(file_inputs)} file inputs already present")
                # Skip the camera button click and go directly to file upload
                camera_button = "skip"  # Special marker

        if not camera_button:
            print("Error: Could not find camera/upload button or file input")
            print("The page structure may have changed. Try running with --no-headless to see the page")
            if self.debug:
                # Save debug info
                self._debug_save_screenshot("camera_button_not_found")
                self._debug_print_page_info()

                # Try to list all buttons on the page
                try:
                    all_buttons = self.driver.find_elements(By.TAG_NAME, 'button')
                    print(f"[DEBUG] Total buttons on page: {len(all_buttons)}")
                    if all_buttons:
                        print("[DEBUG] First 5 buttons:")
                        for i, btn in enumerate(all_buttons[:5]):
                            print(f"[DEBUG]   Button {i}: class='{btn.get_attribute('class')}', aria-label='{btn.get_attribute('aria-label')}'")
                except:
                    pass
            return 0

        # Click the camera button (unless we're skipping it)
        if camera_button != "skip":
            try:
                if self.debug:
                    print("[DEBUG] Clicking camera button...")
                camera_button.click()
                time.sleep(2)

                if self.debug:
                    self._debug_save_screenshot("after_camera_click")

            except Exception as e:
                print(f"Error clicking camera button: {e}")
                if self.debug:
                    self._debug_save_screenshot("camera_click_error")
                return 0
        else:
            if self.debug:
                print("[DEBUG] Skipping camera button click (file input already available)")

        # Find the file input
        file_input = None
        file_input_selectors = [
            'input[type="file"]',
            'input[name="upfile"]',
            'input[class*="file"]'
        ]

        if self.debug:
            print("[DEBUG] Looking for file input...")

        for selector in file_input_selectors:
            try:
                inputs = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if inputs:
                    if self.debug:
                        print(f"[DEBUG] Found {len(inputs)} file inputs with selector: {selector}")
                    file_input = inputs[0]
                    break
            except Exception as e:
                if self.debug:
                    print(f"[DEBUG] File input selector failed: {e}")
                continue

        if not file_input:
            print("Error: Could not find file upload input")
            if self.debug:
                self._debug_save_screenshot("file_input_not_found")
                self._debug_print_page_info()
            return 0

        # Upload the file
        try:
            if self.debug:
                print(f"[DEBUG] Uploading file: {image_path.absolute()}")
            file_input.send_keys(str(image_path.absolute()))

            if self.debug:
                print("[DEBUG] File uploaded, waiting for results...")
            time.sleep(3)

            if self.debug:
                self._debug_save_screenshot("after_upload")

        except Exception as e:
            print(f"Error uploading file: {e}")
            if self.debug:
                self._debug_save_screenshot("upload_error")
                self._debug_print_page_info()
            return 0

        # Wait for results to load
        page_loaded = False
        selectors_to_wait = [
            '.serp-item',
            'img[class*="serp"]',
            'img[class*="thumb"]',
            'a[href*="img_url="]',
            'div[class*="serp"]'
        ]

        if self.debug:
            print("[DEBUG] Waiting for search results...")

        for selector in selectors_to_wait:
            try:
                if self.debug:
                    print(f"[DEBUG] Waiting for selector: {selector}")
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                if self.debug:
                    print(f"[DEBUG] Found selector: {selector}")
                page_loaded = True
                break
            except TimeoutException:
                continue

        if not page_loaded:
            print("Timeout waiting for reverse search results")
            if self.debug:
                self._debug_save_screenshot("reverse_timeout")
                self._debug_print_page_info()
            return 0

        # Extract image URLs
        print(f"Extracting similar images...")
        image_urls = self._extract_image_urls(num_images)

        if not image_urls:
            print("No similar images found!")
            return 0

        print(f"Found {len(image_urls)} similar images. Starting download...")

        # Download images
        downloaded = 0
        for i, url in enumerate(image_urls, 1):
            # Determine file extension
            ext = '.jpg'
            if '.png' in url.lower():
                ext = '.png'
            elif '.gif' in url.lower():
                ext = '.gif'
            elif '.webp' in url.lower():
                ext = '.webp'

            filepath = folder_path / f"similar_{i:03d}{ext}"

            print(f"Downloading {i}/{len(image_urls)}: {url[:60]}...")
            if self._download_image(url, filepath):
                downloaded += 1

        print(f"\nSuccessfully downloaded {downloaded}/{num_images} similar images to {folder_path}/")
        return downloaded

    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            self.driver = None


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Download images from Yandex Images',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search and download 20 images of cats
  python yandex_image_scraper.py -s "cats" -n 20

  # Reverse image search and download 15 similar images
  python yandex_image_scraper.py -r my_image.jpg -n 15

  # Custom folder name
  python yandex_image_scraper.py -s "sunset" -n 30 -o beautiful_sunsets

  # Disable SafeSearch to get unfiltered results
  python yandex_image_scraper.py -s "search term" -n 50 --no-filter
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-s', '--search', type=str,
                      help='Search term for image search')
    group.add_argument('-r', '--reverse', type=str,
                      help='Path to image file for reverse image search')

    parser.add_argument('-n', '--num-images', type=int, default=10,
                       help='Number of images to download (default: 10)')
    parser.add_argument('-o', '--output', type=str,
                       help='Output folder name (default: search term or reverse_search_<filename>)')
    parser.add_argument('--no-headless', action='store_true',
                       help='Show browser window (default: headless mode)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug mode (saves screenshots and page source)')
    parser.add_argument('--no-filter', action='store_true',
                       help='Disable SafeSearch/content filtering (unfiltered results)')

    args = parser.parse_args()

    # Create scraper
    scraper = YandexImageScraper(headless=not args.no_headless, debug=args.debug, disable_filters=args.no_filter)

    try:
        if args.search:
            # Text search
            scraper.search_and_download(
                search_term=args.search,
                num_images=args.num_images,
                folder_name=args.output
            )
        elif args.reverse:
            # Reverse image search
            scraper.reverse_image_search(
                image_path=args.reverse,
                num_images=args.num_images,
                folder_name=args.output
            )
    finally:
        scraper.close()


if __name__ == '__main__':
    main()
