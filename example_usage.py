#!/usr/bin/env python3
"""
Example usage of the YandexImageScraper class
"""

from yandex_image_scraper import YandexImageScraper


def example_text_search():
    """Example: Search and download images by text"""
    print("=== Example 1: Text Search ===")

    scraper = YandexImageScraper(headless=True)

    try:
        # Download 15 images of cats
        scraper.search_and_download(
            search_term="cute cats",
            num_images=15,
            folder_name="cat_images"
        )
    finally:
        scraper.close()


def example_reverse_search():
    """Example: Reverse image search"""
    print("\n=== Example 2: Reverse Image Search ===")

    scraper = YandexImageScraper(headless=True)

    try:
        # Replace 'sample_image.jpg' with your image path
        scraper.reverse_image_search(
            image_path="sample_image.jpg",
            num_images=10,
            folder_name="similar_images"
        )
    finally:
        scraper.close()


def example_multiple_searches():
    """Example: Multiple searches with one scraper instance"""
    print("\n=== Example 3: Multiple Searches ===")

    scraper = YandexImageScraper(headless=True)

    try:
        # Search for different topics
        topics = ["mountains", "ocean", "forest"]

        for topic in topics:
            print(f"\nSearching for: {topic}")
            scraper.search_and_download(
                search_term=topic,
                num_images=5
            )
    finally:
        scraper.close()


if __name__ == "__main__":
    # Run the examples
    example_text_search()

    # Uncomment to run other examples:
    # example_reverse_search()
    # example_multiple_searches()
