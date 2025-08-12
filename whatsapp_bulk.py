import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import os
import random
import threading
from concurrent.futures import ThreadPoolExecutor
import json

CSV_FILE = "contacts.csv"
MESSAGE = "*Hello*, here is the *image* you requested! _Thank you_ for waiting."

POSSIBLE_IMAGE_PATHS = [
    "/home/kusal/Pictures/Screenshots/log.png",
    os.path.join(os.path.expanduser("~"), "Pictures", "Screenshots", "log.png"),
    os.path.join(os.path.dirname(__file__), "log.png"),
    os.path.join(os.path.dirname(__file__), "images", "log.png"),
]

IMAGE_PATH = None
for path in POSSIBLE_IMAGE_PATHS:
    if os.path.exists(path):
        IMAGE_PATH = path
        break

if IMAGE_PATH is None:
    print("ERROR: Could not find image file. Checked these paths:")
    for path in POSSIBLE_IMAGE_PATHS:
        print(f"  - {path}")
    exit(1)

print(f"Using image: {IMAGE_PATH}")

DELAY_BETWEEN_MESSAGES = random.randint(2, 3)
BATCH_SIZE = 50
MAX_RETRIES = 2
FAST_MODE = True

PROGRESS_FILE = "whatsapp_progress.json"

def save_progress(sent_contacts, failed_contacts, current_index):
    progress = {
        'sent': sent_contacts,
        'failed': failed_contacts,
        'current_index': current_index,
        'timestamp': time.time()
    }
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f)

def load_progress():
    try:
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {'sent': [], 'failed': [], 'current_index': 0}

def setup_driver():
    options = Options()
    
    profile_path = os.path.expanduser("~/chrome-whatsapp-profile")
    options.add_argument(f"--user-data-dir={profile_path}")
    options.add_argument("--profile-directory=Default")
    
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-breakpad")
    options.add_argument("--disable-component-extensions-with-background-pages")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-desktop-notifications")
    options.add_argument("--disable-domain-reliability")
    options.add_argument("--disable-features=TranslateUI")
    options.add_argument("--disable-hang-monitor")
    options.add_argument("--disable-ipc-flooding-protection")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-prompt-on-repost")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-sync")
    options.add_argument("--force-color-profile=srgb")
    options.add_argument("--metrics-recording-only")
    options.add_argument("--no-crash-upload")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--no-first-run")
    options.add_argument("--no-pings")
    options.add_argument("--password-store=basic")
    options.add_argument("--use-mock-keychain")
    options.add_argument("--window-size=1200,800")
    
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    try:
        print("Setting up optimized Chrome driver...")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        driver.set_page_load_timeout(15)
        driver.implicitly_wait(2)
        
        print("Chrome driver setup successful")
        return driver
    except Exception as e:
        print(f"Failed to setup driver: {e}")
        return None

def send_message_fast(driver, wait, phone_number, message, image_path):
    try:
        print(f"Sending to {phone_number}...")
        
        driver.get(f"https://web.whatsapp.com/send?phone={phone_number}")
        
        time.sleep(2)
        
        try:
            attach_btn = WebDriverWait(driver, 4).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[title="Attach"]'))
            )
            attach_btn.click()
            time.sleep(0.8)
            print(f"  Attach clicked")
        except:
            try:
                attach_btn = driver.find_element(By.CSS_SELECTOR, 'div[title="Attach"]')
                attach_btn.click()
                time.sleep(0.8)
                print(f"  Attach clicked (fallback)")
            except:
                print(f"Attach failed for {phone_number}")
                return False
        
        print(f"  Fast-track: Going directly to file input...")
        
        try:
            file_input = WebDriverWait(driver, 4).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"][accept*="image"]'))
            )
            
            file_input.send_keys(image_path)
            print(f"  Image uploaded")
            
            time.sleep(1.5)
            
            try:
                driver.find_element(By.CSS_SELECTOR, 'img[src*="blob:"]')
                print(f"  Preview ready")
            except:
                pass
                
        except Exception as e:
            print(f"Upload failed for {phone_number}")
            return False
        
        if message and message.strip():
            try:
                caption_input = driver.find_element(By.CSS_SELECTOR, 'div[contenteditable="true"][aria-label*="caption"]')
                caption_input.click()
                caption_input.clear()
                caption_input.send_keys(message)
                time.sleep(0.3)
                print(f"  Caption added")
            except:
                print(f"  Caption skipped")
        
        try:
            send_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[aria-label="Send"]'))
            )
            send_btn.click()
            
            time.sleep(1.5)
            
            print(f"Sent to {phone_number}")
            return True
            
        except Exception as e:
            print(f"Send failed for {phone_number}")
            return False
        
    except Exception as e:
        print(f"Error for {phone_number}: {str(e)[:30]}...")
        return False

def process_batch(driver, contacts_batch, start_index):
    wait = WebDriverWait(driver, 10)
    successful = []
    failed = []
    
    for i, contact in enumerate(contacts_batch):
        current_index = start_index + i
        print(f"\n[{current_index + 1}/500] Processing: {contact}")
        
        success = False
        for attempt in range(MAX_RETRIES):
            if attempt > 0:
                print(f"  Retry {attempt}/{MAX_RETRIES-1}")
                time.sleep(2)
            
            try:
                if send_message_fast(driver, wait, contact, MESSAGE, IMAGE_PATH):
                    successful.append(contact)
                    success = True
                    break
            except Exception as e:
                print(f"  Attempt {attempt + 1} failed: {str(e)[:30]}...")
                continue
        
        if not success:
            failed.append(contact)
            print(f"Failed permanently: {contact}")
        
        if (current_index + 1) % 10 == 0:
            save_progress(successful, failed, current_index + 1)
            print(f"Progress saved. Success: {len(successful)}, Failed: {len(failed)}")
        
        if success:
            delay = random.randint(1, 2) if FAST_MODE else random.randint(2, 3)
        else:
            delay = random.randint(2, 4)
        
        if i < len(contacts_batch) - 1:
            print(f"Waiting {delay}s...")
            time.sleep(delay)
        else:
            if current_index == start_index + len(contacts_batch) - 1:
                print(f"Final message - waiting {delay + 2}s to ensure delivery...")
                time.sleep(delay + 2)
            else:
                print(f"Last in batch - waiting {delay}s...")
                time.sleep(delay)
    
    return successful, failed

def main():
    print("WhatsApp Bulk Sender - FIXED VERSION for Images + Messages")
    print("=" * 70)
    
    try:
        all_contacts = pd.read_csv(CSV_FILE)["phone"].tolist()
        print(f"Loaded {len(all_contacts)} contacts")
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return
    
    progress = load_progress()
    start_index = progress.get('current_index', 0)
    already_sent = set(progress.get('sent', []))
    already_failed = set(progress.get('failed', []))
    
    print(f"Previous Progress: Sent: {len(already_sent)}, Failed: {len(already_failed)}")
    print(f"Message: '{MESSAGE}'")
    print(f"Image: {IMAGE_PATH}")
    
    if len(already_sent) > 0 or len(already_failed) > 0:
        print(f"\nFound previous progress:")
        print(f"   Previously sent: {len(already_sent)} contacts")
        print(f"   Previously failed: {len(already_failed)} contacts")
        print(f"   Last position: {start_index}")
        
        choice = input(f"\nChoose an option:\n1. Resume from where you left off\n2. Start fresh (reset all progress)\n3. Exit\nEnter choice (1/2/3): ").strip()
        
        if choice == '3':
            print("Exiting...")
            return
        elif choice == '2':
            print("Resetting progress...")
            start_index = 0
            already_sent = set()
            already_failed = set()
            try:
                if os.path.exists(PROGRESS_FILE):
                    os.remove(PROGRESS_FILE)
                    print("Progress file deleted")
            except:
                pass
        elif choice == '1':
            print("Resuming from previous progress...")
        else:
            print("Invalid choice, starting fresh...")
            start_index = 0
            already_sent = set()
            already_failed = set()
    
    remaining_contacts = [c for c in all_contacts[start_index:] if c not in already_sent and c not in already_failed]
    
    if not remaining_contacts:
        if len(already_sent) > 0 or len(already_failed) > 0:
            print("All contacts have been processed based on saved progress!")
            restart = input("Would you like to start fresh and process all contacts again? (y/n): ").lower().strip()
            if restart == 'y':
                start_index = 0
                already_sent = set()
                already_failed = set()
                remaining_contacts = all_contacts
                try:
                    if os.path.exists(PROGRESS_FILE):
                        os.remove(PROGRESS_FILE)
                except:
                    pass
                print("Starting fresh with all contacts...")
            else:
                print("Exiting...")
                return
        else:
            print("All contacts have been processed!")
            return
    
    print(f"Remaining: {len(remaining_contacts)} contacts to process")
    
    driver = setup_driver()
    if not driver:
        return
    
    try:
        print("Opening WhatsApp Web...")
        driver.get("https://web.whatsapp.com")
        
        print("\nPlease ensure:")
        print("1. Scan QR code if needed")
        print("2. WhatsApp Web is fully loaded")
        print("3. You can see your chat list")
        print("4. Image will be sent as PHOTO (not document)")
        print("5. Message text will be included as caption")
        print(f"6. Ready to send to {len(remaining_contacts)} contacts")
        
        input("\nPress Enter when ready to start bulk sending...")
        
        total_successful = list(already_sent)
        total_failed = list(already_failed)
        
        for batch_start in range(0, len(remaining_contacts), BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, len(remaining_contacts))
            batch = remaining_contacts[batch_start:batch_end]
            actual_index = start_index + batch_start
            
            print(f"\nProcessing batch {batch_start//BATCH_SIZE + 1}/{(len(remaining_contacts)-1)//BATCH_SIZE + 1}")
            print(f"Contacts {actual_index + 1}-{actual_index + len(batch)}")
            
            try:
                batch_successful, batch_failed = process_batch(driver, batch, actual_index)
                total_successful.extend(batch_successful)
                total_failed.extend(batch_failed)
                
                save_progress(total_successful, total_failed, actual_index + len(batch))
                
                print(f"\nBatch Summary:")
                print(f"   Success: {len(batch_successful)}")
                print(f"   Failed: {len(batch_failed)}")
                print(f"   Total Success: {len(total_successful)}")
                print(f"   Total Failed: {len(total_failed)}")
                
                if batch_end < len(remaining_contacts):
                    rest_time = random.randint(15, 25)
                    print(f"Resting {rest_time}s between batches...")
                    time.sleep(rest_time)
                
            except KeyboardInterrupt:
                print("\nBatch interrupted by user")
                save_progress(total_successful, total_failed, actual_index + len(batch))
                break
            except Exception as e:
                print(f"Batch error: {e}")
                continue
        
        print(f"\nFINAL SUMMARY:")
        print(f"   Total Sent: {len(total_successful)}")
        print(f"   Total Failed: {len(total_failed)}")
        print(f"   Success Rate: {len(total_successful)/(len(total_successful)+len(total_failed))*100:.1f}%")
        print(f"   Total Contacts: {len(total_successful)+len(total_failed)}")
        
        with open('final_results.json', 'w') as f:
            json.dump({
                'successful': total_successful,
                'failed': total_failed,
                'timestamp': time.time(),
                'success_rate': len(total_successful)/(len(total_successful)+len(total_failed))*100 if (len(total_successful)+len(total_failed)) > 0 else 0
            }, f, indent=2)
        
        print("Final results saved to final_results.json")
        
        if len(total_successful) > 0:
            print(f"\nWaiting 10 seconds to ensure all messages are delivered...")
            time.sleep(10)
            
            try:
                keep_open = input("Keep browser open to verify messages were sent? (y/n): ").lower().strip()
                if keep_open == 'y':
                    print("Browser will stay open. Close manually when done.")
                    input("Press Enter when you want to close the browser...")
            except:
                pass
        
    except KeyboardInterrupt:
        print("\nScript interrupted by user")
    except Exception as e:
        print(f"Script error: {e}")
    finally:
        driver.quit()
        print("Browser closed")

if __name__ == "__main__":
    main()