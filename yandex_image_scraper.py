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

    def __init__(self, headless=True):
        """
        Initialize the scraper

        Args:
            headless (bool): Run browser in headless mode
        """
        self.headless = headless
        self.driver = None

    def _init_driver(self):
        """Initialize the Selenium WebDriver"""
        if self.driver is not None:
            return

        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            print(f"Error initializing Chrome driver: {e}")
            print("Make sure chromedriver is installed and in PATH")
            sys.exit(1)

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
        max_scroll_attempts = 10

        while len(image_urls) < num_images and scroll_attempts < max_scroll_attempts:
            # Scroll to load more images
            self._scroll_page(scroll_pause_time=1.5)

            # Find all image elements
            try:
                # Try multiple selectors for Yandex images
                images = self.driver.find_elements(By.CSS_SELECTOR,
                    '.serp-item__thumb, .SimpleImage, .ContentImage-Image, img.MMImage-Origin')

                for img in images:
                    try:
                        # Get the src or data-bem attribute
                        src = img.get_attribute('src')
                        if not src:
                            src = img.get_attribute('data-src')

                        if src and src.startswith('http') and 'avatar' not in src.lower():
                            image_urls.add(src)

                        if len(image_urls) >= num_images:
                            break
                    except:
                        continue

            except Exception as e:
                print(f"Error extracting images: {e}")

            scroll_attempts += 1

            if len(image_urls) == 0:
                # Try clicking on first image to get larger versions
                try:
                    first_item = self.driver.find_element(By.CSS_SELECTOR, '.serp-item')
                    first_item.click()
                    time.sleep(2)

                    # Now try to get the full-size image
                    full_img = self.driver.find_element(By.CSS_SELECTOR, '.MMImage-Origin')
                    src = full_img.get_attribute('src')
                    if src:
                        image_urls.add(src)
                except:
                    pass

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

        print(f"Searching Yandex Images for: {search_term}")
        self.driver.get(search_url)

        # Wait for page to load
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.serp-item, .SimpleImage'))
            )
        except TimeoutException:
            print("Timeout waiting for search results")
            return 0

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
        self.driver.get("https://yandex.com/images/")

        # Wait and click on camera icon for reverse search
        try:
            # Wait for the search by image button
            camera_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '.CBIr3, .search-by-image__button, [aria-label*="Search by image"]'))
            )
            camera_button.click()
            time.sleep(1)

            # Find and click file upload option
            file_input = self.driver.find_element(By.CSS_SELECTOR, 'input[type="file"]')
            file_input.send_keys(str(image_path.absolute()))

            # Wait for results to load
            time.sleep(3)
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.serp-item, .SimpleImage'))
            )

        except Exception as e:
            print(f"Error performing reverse image search: {e}")
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

    args = parser.parse_args()

    # Create scraper
    scraper = YandexImageScraper(headless=not args.no_headless)

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
