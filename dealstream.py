import seleniumwire.undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import os
import time
import random

# --- Configuration ---
OUTPUT_DIR = "dealstream_articles"
ARTICLES_TO_SCRAPE = 10
WAIT_TIMEOUT = 25
MAX_RETRIES = 3 # How many times to retry a failed article

# --- Rotating Proxy Service Credentials ---
PROXY_HOST = "p.webshare.io"
PROXY_PORT = "80"
PROXY_USER = "jphsuydv-rotate"
PROXY_PASS = "2t7lijya16wu"

os.makedirs(OUTPUT_DIR, exist_ok=True)
driver = None

try:
    # --- Part 1: Initial setup to get the list of article URLs ---
    print("🚀 Configuring initial browser to fetch article URLs...")
    temp_options = uc.ChromeOptions()
    temp_options.add_argument('--ignore-certificate-errors')
    temp_sw_options = {
        'proxy': {
            'http': f'http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}',
            'https': f'https://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}',
        },
    }

    driver = uc.Chrome(options=temp_options, seleniumwire_options=temp_sw_options)
    wait = WebDriverWait(driver, WAIT_TIMEOUT)

    driver.get("http://httpbin.org/ip")
    print(f"Initial IP check: {driver.find_element(By.TAG_NAME, 'body').text}")

    target_url = "https://dealstream.com/businesses-for-sale"
    print(f"Navigating to listings page: {target_url}")
    driver.get(target_url)
    time.sleep(random.uniform(3, 6))

    article_urls = []
    article_links_elements = wait.until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.list-group-item.post"))
    )
    for link_element in article_links_elements:
        article_urls.append(link_element.get_attribute("href"))

    print(f"✅ Found {len(article_urls)} articles.")
    driver.quit()
    driver = None

    # --- Part 2: Loop through articles with session and retry logic ---
    print("\n--- Starting to scrape articles with session rotation ---")
    for i, article_url in enumerate(article_urls[:ARTICLES_TO_SCRAPE], start=1):

        if driver is None:
            print("="*30)
            print(f"🚀 Starting new browser session for articles #{i} and #{i+1}...")
            options = uc.ChromeOptions()
            options.add_argument('--ignore-certificate-errors')
            seleniumwire_options = {
                'proxy': { 'http': f'http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}', 'https': f'https://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}'},
            }
            driver = uc.Chrome(options=options, seleniumwire_options=seleniumwire_options)
            wait = WebDriverWait(driver, WAIT_TIMEOUT)
            driver.get("http://httpbin.org/ip")
            print(f"Session IP check: {driver.find_element(By.TAG_NAME, 'body').text}")

        print("-" * 20)
        print(f"Scraping article {i}/{ARTICLES_TO_SCRAPE}: {article_url}")

        # --- NEW: Retry loop for each article ---
        for attempt in range(MAX_RETRIES):
            try:
                driver.get(article_url)
                time.sleep(random.uniform(5, 10))

                article_heading = wait.until(EC.visibility_of_element_located((By.TAG_NAME, "h1")))
                page_body = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "body")))
                text_to_save = f"URL: {article_url}\n\nHEADING: {article_heading.text}\n\nBODY CONTENT:\n{page_body.text}"

                file_path = os.path.join(OUTPUT_DIR, f"article_{i}.txt")
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(text_to_save)
                print(f"📄 Saved article {i} to {file_path}")
                
                # If successful, break out of the retry loop
                break 

            except TimeoutException:
                print(f"❌ Timed out on attempt {attempt + 1}/{MAX_RETRIES}. Retrying with a new IP...")
                if attempt + 1 == MAX_RETRIES:
                    print(f"🚨 Failed to scrape article {i} after {MAX_RETRIES} attempts. Moving on.")
                    error_screenshot_path = os.path.join(OUTPUT_DIR, f"error_page_article_{i}.png")
                    driver.save_screenshot(error_screenshot_path)
                    print(f"📸 Screenshot saved.")
                else:
                    # Optional: a small delay before retrying
                    time.sleep(5)
        
        # This block closes the driver after the 2nd article, 4th, 6th, etc.
        if i % 2 == 0 and i < ARTICLES_TO_SCRAPE:
            print(f"✅ Closing browser session after article #{i} to get a new identity.")
            driver.quit()
            driver = None

except Exception as e:
    print(f"\nAn unexpected error occurred: {e}")

finally:
    if driver:
        driver.quit()
    print("\n✅ Script finished.")