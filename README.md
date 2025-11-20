# Yandex Image Scraper

A Python script for downloading images from Yandex Images using text-based search or reverse image search.

## Features

- **Text Search**: Search Yandex Images with any search term and download results
- **Reverse Image Search**: Upload an image and find similar images
- **Customizable**: Specify number of images to download
- **Organized**: Automatically creates folders named after your search term
- **Headless Mode**: Runs in background by default (can be disabled)

## Requirements

- Python 3.7+
- Chrome/Chromium browser
- ChromeDriver (must be in PATH)

## Installation

1. Clone this repository or download the script:
```bash
git clone <repository-url>
cd yandex_scraper
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Install ChromeDriver:

   **Ubuntu/Debian:**
   ```bash
   sudo apt-get update
   sudo apt-get install chromium-chromedriver
   ```

   **macOS:**
   ```bash
   brew install chromedriver
   ```

   **Windows:**
   - Download from [ChromeDriver Downloads](https://chromedriver.chromium.org/downloads)
   - Add to PATH

## Usage

### Text-based Image Search

Download images based on a search term:

```bash
# Basic usage - download 10 images (default)
python yandex_image_scraper.py -s "cats"

# Download 25 images
python yandex_image_scraper.py -s "mountain landscape" -n 25

# Custom output folder
python yandex_image_scraper.py -s "sunset" -n 20 -o beautiful_sunsets
```

### Reverse Image Search

Find and download similar images:

```bash
# Basic reverse search
python yandex_image_scraper.py -r path/to/image.jpg

# Download 30 similar images
python yandex_image_scraper.py -r my_photo.png -n 30

# Custom output folder
python yandex_image_scraper.py -r sample.jpg -n 15 -o similar_images
```

### Command Line Arguments

```
Options:
  -s, --search TERM          Search term for image search
  -r, --reverse PATH         Path to image file for reverse image search
  -n, --num-images NUM       Number of images to download (default: 10)
  -o, --output FOLDER        Output folder name (default: search term)
  --no-headless              Show browser window (default: headless mode)
  --debug                    Enable debug mode (saves screenshots and page source)
  -h, --help                 Show help message
```

## Examples

```bash
# Download 50 images of "golden retriever puppies"
python yandex_image_scraper.py -s "golden retriever puppies" -n 50

# Reverse search with visible browser window
python yandex_image_scraper.py -r my_image.jpg -n 20 --no-headless

# Search with custom folder name
python yandex_image_scraper.py -s "abstract art" -n 30 -o art_collection

# Debug mode - see what's happening and save screenshots
python yandex_image_scraper.py -s "cats" -n 10 --debug --no-headless
```

## Output

- Images are saved in folders named after the search term (or custom name)
- Files are numbered sequentially: `image_001.jpg`, `image_002.jpg`, etc.
- For reverse search: `similar_001.jpg`, `similar_002.jpg`, etc.
- Folder names automatically sanitize invalid characters

## Troubleshooting

### ChromeDriver Issues

If you get a ChromeDriver error:
1. Check ChromeDriver is installed: `chromedriver --version`
2. Ensure ChromeDriver version matches your Chrome browser version
3. Verify ChromeDriver is in your system PATH

### "Timeout waiting for search results" Error

If you encounter timeout errors:

1. **Enable debug mode** to see what's happening:
   ```bash
   python yandex_image_scraper.py -s "cats" --debug --no-headless
   ```
   This will:
   - Show the browser window
   - Save screenshots at key points
   - Save the HTML page source for inspection
   - Print detailed debugging information

2. **Check the saved files**:
   - Look at `timeout_error_*.png` screenshot to see what Yandex displayed
   - Check `page_source_*.html` to see if there's a CAPTCHA or blocking message
   - Review debug output for which selectors failed

3. **Common causes**:
   - Yandex may be showing a CAPTCHA (visible in screenshots)
   - Your IP might be temporarily blocked (try again later)
   - Yandex changed their page structure (selectors may need updating)
   - Network connectivity issues

4. **Workarounds**:
   - Try again after a few minutes
   - Use a VPN if available
   - Check if you can access Yandex Images normally in your browser

### No Images Found

- Try reducing the number of requested images
- Use more specific search terms
- Check your internet connection
- Run with `--no-headless --debug` to see what's happening
- The script tries multiple CSS selectors automatically

### Download Failures

- Some images may fail to download due to:
  - Broken links
  - Access restrictions
  - Network timeouts
- The script will continue downloading remaining images

## Notes

- Respects Yandex's page structure (may need updates if Yandex changes their layout)
- Downloads run in headless mode by default for better performance
- Network requests include proper User-Agent headers
- Images are downloaded in their original format when possible

## Legal & Ethical Use

- This tool is for educational and personal use
- Respect copyright and image usage rights
- Follow Yandex's Terms of Service
- Don't overwhelm servers with excessive requests
- Use downloaded images responsibly

## License

This project is provided as-is for educational purposes.

## Contributing

Feel free to submit issues and enhancement requests!
