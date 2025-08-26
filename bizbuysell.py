
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import os
import time
import random
import base64 # <-- Import base64 for decoding document URLs

# --- OPTIONS ---
chrome_options = uc.ChromeOptions()
chrome_options.add_argument("start-maximized")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/5.37.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
)
chrome_options.add_argument("--disable-blink-features=AutomationControlled")

try:
    driver = uc.Chrome(options=chrome_options, use_subprocess=True)
except TypeError:
    driver = uc.Chrome(options=chrome_options)

wait = WebDriverWait(driver, 20) # Reduced wait time slightly
output_dir = "bizbuysell_articles"
os.makedirs(output_dir, exist_ok=True)

try:
    url = "https://www.bizbuysell.com/california-businesses-for-sale/?q=bHQ9MzAsNDAsODA%3D"
    print(f"Navigating to {url}")
    driver.get(url)
    time.sleep(random.uniform(2, 4))

    # Handle cookie consent banner once at the start
    try:
        cookie_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
        )
        driver.execute_script("arguments[0].click();", cookie_button)
        print("Cookie consent accepted.")
        time.sleep(random.uniform(1, 3))
    except TimeoutException:
        print("Cookie consent banner not found, proceeding...")

    # --- PAGINATION LOGIC ---
    page_counter = 1
    max_pages = 5
    all_article_urls = []

    while page_counter <= max_pages:
        print(f"\n--- Scraping Page {page_counter} ---")
        try:
            wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.diamond")))
            print("Listings found on this page.")
            listing_links = driver.find_elements(By.CSS_SELECTOR, "a.diamond")
            print(f"Found {len(listing_links)} listings on this page.")
            for link_element in listing_links:
                try:
                    link = link_element.get_attribute("href")
                    if link and "/business-opportunity/" in link and link not in all_article_urls:
                        all_article_urls.append(link)
                except Exception:
                    continue
            try:
                next_button = driver.find_element(By.CSS_SELECTOR, 'button[title="Next"]')
                if "disabled" in next_button.get_attribute("class"):
                    print("'Next' button is disabled. Reached the last page.")
                    break
                driver.execute_script("arguments[0].click();", next_button)
                print("Clicked 'Next' button. Loading next page...")
                page_counter += 1
                time.sleep(random.uniform(4, 7))
            except NoSuchElementException:
                print("No more 'Next' button found. Scraping finished.")
                break
        except TimeoutException:
            print(f"Timed out waiting for listings on page {page_counter}. Stopping.")
            break

    print(f"\n✅ Total unique article URLs extracted: {len(all_article_urls)}. Scraping the top 10.")

    # --- MODIFIED PART: DETAILED SCRAPING ---
    for i, article_url in enumerate(all_article_urls[:10], start=1):
        print(f"\n Scraping article {i}/10: {article_url}")
        driver.get(article_url)
        time.sleep(random.uniform(3, 5))

        try:
            output_lines = []
            
            # 1. Scrape Heading
            article_heading = wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
            heading_text = article_heading.text
            output_lines.append(f"TITLE: {heading_text}")
            output_lines.append("=" * 50)

            # 2. Scrape Financials Overview section
            output_lines.append("\nFINANCIAL OVERVIEW:")
            try:
                financials_container = driver.find_element(By.CSS_SELECTOR, "div.financials")
                financial_items = financials_container.find_elements(By.XPATH, ".//p[span[@class='title']]")
                for item in financial_items:
                    key = item.find_element(By.CSS_SELECTOR, "span.title").text.strip()
                    full_text = item.text.strip()
                    value = full_text.replace(key, "").strip()
                    output_lines.append(f"- {key} {value}")
            except NoSuchElementException:
                output_lines.append("- Financial overview section not found.")
            
            # 3. Scrape Business Description
            output_lines.append("\nBUSINESS DESCRIPTION:")
            try:
                page_body = driver.find_element(By.CSS_SELECTOR, "div.businessDescription")
                output_lines.append(page_body.text)
            except NoSuchElementException:
                output_lines.append("- Business description not found.")

            # 4. Scrape Detailed Information table
            output_lines.append("\nDETAILED INFORMATION:")
            try:
                details_dl = driver.find_element(By.CSS_SELECTOR, "dl.listingProfile_details")
                keys = details_dl.find_elements(By.TAG_NAME, "dt")
                values = details_dl.find_elements(By.TAG_NAME, "dd")
                for key, value in zip(keys, values):
                    key_text = key.text.strip()
                    value_text = value.text.replace("\n", ", ").strip() # Clean up multiline values
                    output_lines.append(f"- {key_text} {value_text}")
            except NoSuchElementException:
                output_lines.append("- Detailed information section not found.")

            # 5. Scrape Image URLs
            output_lines.append("\nIMAGE URLs:")
            try:
                image_elements = driver.find_elements(By.CSS_SELECTOR, "div#slider img.image")
                if not image_elements:
                    output_lines.append("- No images found in slider.")
                else:
                    unique_urls = set()
                    for img in image_elements:
                        url = img.get_attribute('src')
                        if url:
                            unique_urls.add(url)
                    for url in unique_urls:
                        output_lines.append(f"- {url}")
            except NoSuchElementException:
                output_lines.append("- Image section not found.")

            # 6. Scrape Attached Documents
            output_lines.append("\nATTACHED DOCUMENTS:")
            try:
                doc_links = driver.find_elements(By.CSS_SELECTOR, "a[class*='listingAttachment']")
                if not doc_links:
                    output_lines.append("- No attached documents found.")
                else:
                    for link in doc_links:
                        filename = link.text.strip()
                        encoded_url = link.get_attribute('data-url')
                        decoded_url = base64.b64decode(encoded_url).decode('utf-8')
                        output_lines.append(f"- {filename}: {decoded_url}")
            except Exception:
                 output_lines.append("- Attached documents section not found or failed to parse.")
            
            # Combine and save the scraped data
            text_to_save = "\n".join(output_lines)
            safe_filename = "".join([c for c in heading_text if c.isalnum() or c == " "]).rstrip()
            file_path = os.path.join(output_dir, f"{i}_{safe_filename}.txt")

            with open(file_path, "w", encoding="utf-8") as file:
                file.write(text_to_save)
            print(f"✅ Saved all details for article {i} to {file_path}")

        except Exception as e:
            print(f"❌ Failed to scrape/save article {i}: {e}")

except Exception as e:
    print(f"An unexpected error occurred: {e}")

finally:
    if "driver" in locals() and driver:
        driver.quit()
    print("\nScraping complete. Browser closed.")