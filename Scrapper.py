# ── Python 3.12+ Compatibility Patch ─────────────────────────────────────────
import sys
import types
import re

try:
    __import__('distutils.version')
except ImportError:
    dummy_distutils = types.ModuleType("distutils")
    sys.modules["distutils"] = dummy_distutils
    
    dummy_distutils_version = types.ModuleType("distutils.version")
    sys.modules["distutils.version"] = dummy_distutils_version
    
    class LooseVersion:
        def __init__(self, vstring):
            self.vstring = vstring
            self.version = [int(x) if x.isdigit() else x for x in re.split(r'(\d+)', vstring) if x]
            
        def __lt__(self, other): return self.version < other.version
        def __le__(self, other): return self.version <= other.version
        def __eq__(self, other): return self.version == other.version
        def __ge__(self, other): return self.version >= other.version
        def __gt__(self, other): return self.version > other.version
        def __ne__(self, other): return self.version != other.version
        def __repr__(self): return f"LooseVersion('{self.vstring}')"
        
    dummy_distutils_version.LooseVersion = LooseVersion
# ─────────────────────────────────────────────────────────────────────────────

import os
import time
import random
import urllib.parse
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

# Automatic dependency resolver for 'requests'
try:
    import requests
except ImportError:
    print("❌ The 'requests' library is missing. Installing it automatically...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

# ── Configuration ─────────────────────────────────────────────────────────────
OUTPUT_DIR = "papers"
DELAY_ON_SUCCESS = 1.0  # Pause after a successful download to avoid rate limits
BASE_URL = "https://pastpapers.papacambridge.com/papers/caie/o-level-biology-5090?theme=lightTheme"

# Year boundaries for filtering
START_YEAR = 2000
END_YEAR = 2026


# ── Step 1: Filename Normalization Helper ────────────────────────────────────
def extract_filename_from_url(url, subject_code="5090"):
    """Isolates and normalizes the target past paper filename from complex URL strings."""
    decoded_url = urllib.parse.unquote(url)
    
    # Check for direct file paths first
    parsed = urllib.parse.urlparse(decoded_url)
    last_segment = parsed.path.split("/")[-1]
    if last_segment.lower().endswith(".pdf"):
        return last_segment
        
    # Check for concatenated patterns (e.g. ...-5090-s24-ms-21-pdf)
    for sep in [f"-{subject_code}-", f"_{subject_code}_", f"-{subject_code}_", f"_{subject_code}-"]:
        if sep in decoded_url:
            parts = decoded_url.rsplit(sep, 1)
            file_part = parts[-1]
            
            # Normalize dashes to underscores
            file_part_normalized = file_part.replace("-", "_")
            filename = f"{subject_code}_{file_part_normalized}"
            
            # Convert ending _pdf or -pdf to .pdf
            if filename.lower().endswith("_pdf"):
                filename = filename[:-4] + ".pdf"
            elif filename.lower().endswith("-pdf"):
                filename = filename[:-4] + ".pdf"
                
            if not filename.lower().endswith(".pdf"):
                filename += ".pdf"
            return filename
            
    # Fallback to general segment split
    filename = last_segment
    if filename.lower().endswith("_pdf"):
        filename = filename[:-4] + ".pdf"
    elif filename.lower().endswith("-pdf"):
        filename = filename[:-4] + ".pdf"
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"
    return filename


# ── Step 2: Initialize Undetected Driver ──────────────────────────────────────
def init_driver():
    print("🚀 Launching Chrome instance (Undetected Chromedriver)...")
    options = uc.ChromeOptions()
    options.add_argument("--disable-popup-blocking")
    
    # Explicitly set version_main to 148 to match your local browser version
    driver = uc.Chrome(options=options, version_main=148)
    driver.implicitly_wait(10)
    return driver


# ── Step 3: Cloudflare Guard (Only run once on start) ──────────────────────────
def wait_for_cloudflare(driver):
    """Waits until the initial Cloudflare screen is solved."""
    print("⏳ Checking for Cloudflare challenge...")
    print("👉 (If a 'Verify you are human' checkbox appears, please click it to start.)")
    
    start_time = time.time()
    while True:
        try:
            title = driver.title.lower()
            html = driver.page_source.lower()
            
            is_cf_title = any(t in title for t in ["just a moment", "cloudflare", "attention required"])
            is_cf_html = any(t in html for t in ["cf-challenge", "cf-wrapper", "ray id:", "challenges.cloudflare.com"])
            
            if is_cf_title or is_cf_html or not title.strip():
                time.sleep(1.5)
                if time.time() - start_time > 120:
                    print("⚠️ Timeout waiting for Cloudflare. Moving forward...")
                    break
            else:
                break
        except Exception:
            time.sleep(1.5)
            
    print(f"🎉 Session validated! Current browser title: '{driver.title}'")


# ── Step 4: Scan Page for green "View File" Elements ─────────────────────────
def find_viewer_elements_on_page(driver):
    """Parses current page to retrieve relevant green 'View File' links and map them to clean filenames."""
    viewer_elements = []
    
    # XPath targets only the green "View File" buttons
    xpath_selector = "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'view file')]"
    all_links = driver.find_elements(By.XPATH, xpath_selector)
    
    for link in all_links:
        try:
            href = link.get_attribute("href")
            if not href:
                continue
                
            absolute_href = urllib.parse.urljoin(driver.current_url, href)
            
            # Extract clean filename using our normalized helper
            filename = extract_filename_from_url(absolute_href, "5090")
            lower_name = filename.lower()
            is_valid = False
            
            # Target Question Papers (qp) and Mark Schemes (ms)
            if ("_qp_" in lower_name or "-qp-" in lower_name or "_qp." in lower_name or
                "_ms_" in lower_name or "-ms-" in lower_name or "_ms." in lower_name):
                if not any(x in lower_name for x in ["_gt", "-gt", "_er", "-er", "_ci", "-ci", "_ir", "-ir"]):
                    is_valid = True
                    
            if is_valid:
                # Store the absolute URL of the "View File" button
                if not any(filename == item[0] for item in viewer_elements):
                    viewer_elements.append((filename, absolute_href))
        except Exception:
            continue
    return viewer_elements


# ── Step 5: Folder Sessions Discovery ──────────────────────────────────────────
def discover_folder_sessions(driver):
    """Extracts valid year/session URLs from the landing page."""
    print("🔍 Scanning landing page for year/session folders...")
    folder_urls = []
    
    base_path_lower = urllib.parse.urlparse(BASE_URL).path.lower().rstrip('/')
    
    try:
        all_links = driver.find_elements(By.TAG_NAME, "a")
        for link in all_links:
            try:
                href = link.get_attribute("href")
                if not href:
                    continue
                
                parsed = urllib.parse.urlparse(href)
                path_lower = parsed.path.lower().rstrip('/')
                
                if path_lower.startswith(base_path_lower + "-"):
                    suffix = path_lower[len(base_path_lower)+1:]
                    
                    year_match = re.search(r'\b(20\d{2}|19\d{2})\b', suffix)
                    if year_match:
                        year = int(year_match.group(1))
                        
                        session_raw = suffix.replace(str(year), "").strip("-")
                        session_raw = re.sub(r'-+', '-', session_raw)
                        
                        session_name = "-".join([word.capitalize() for word in session_raw.split("-") if word])
                        if not session_name:
                            session_name = "Other"
                        
                        if START_YEAR <= year <= END_YEAR:
                            if not any(f["url"] == href for f in folder_urls):
                                folder_urls.append({
                                    "url": href,
                                    "year": str(year),
                                    "session": session_name
                                })
            except Exception:
                continue
    except Exception as e:
        print(f"⚠️ Error while scanning folders: {e}")
        
    print(f"\n📋 Discovered {len(folder_urls)} folder sessions matching years {START_YEAR}-{END_YEAR}.")
    return folder_urls


# ── Step 6: Self-Healing Hybrid Viewer Parser & Downloader ───────────────────
def download_file_with_requests(driver, viewer_url, dest_path, filename):
    """Downloads the document by retrieving the viewer page and parsing it for the direct PDF URL."""
    session = requests.Session()
    
    # Sync all cookies from the active Selenium session
    for cookie in driver.get_cookies():
        session.cookies.set(cookie['name'], cookie['value'])
        
    # Synchronize User-Agent to match Selenium precisely
    user_agent = driver.execute_script("return navigator.userAgent;")
    
    headers = {
        "User-Agent": user_agent,
        "Referer": driver.current_url,  # Bypasses direct-hotlink security gates
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive"
    }
    
    try:
        # Fetch the Viewer HTML Page
        response = session.get(viewer_url, headers=headers, stream=True, timeout=15)
        if response.status_code == 200:
            chunk_iterator = response.iter_content(chunk_size=2048)
            try:
                first_chunk = next(chunk_iterator)
            except StopIteration:
                first_chunk = b""
                
            # If the response is directly a PDF (unlikely for a viewer link, but handled as fallback)
            if first_chunk.startswith(b"%PDF"):
                with open(dest_path, 'wb') as f:
                    f.write(first_chunk)
                    for chunk in chunk_iterator:
                        f.write(chunk)
                return True
                
            # Parse the viewer page HTML content
            elif b"<html" in first_chunk.lower() or b"<!doctype" in first_chunk.lower():
                html_content = first_chunk + response.content
                html_text = html_content.decode('utf-8', errors='ignore')
                
                # Scan HTML text for embedded PDF paths using non-capturing groups
                pdf_urls_raw = re.findall(r'(https?://[^\s"\'<>]+?\.(?:pdf|PDF)(?:[a-zA-Z0-9_-]+\?[^\s"\'<>]+)?)', html_text)
                pdf_urls_raw += re.findall(r'(https?:\\/\\/[^\s"\'<>]+?\.(?:pdf|PDF))', html_text)
                pdf_urls_raw += re.findall(r'(/[^\s"\'<>]+?\.(?:pdf|PDF))', html_text)
                
                # Broaden search to include API download endpoints or directory files
                pdf_urls_raw += re.findall(r'(https?://[^\s"\'<>]+)', html_text)
                pdf_urls_raw += re.findall(r'(https?:\\/\\/[^\s"\'<>]+)', html_text)
                pdf_urls_raw += re.findall(r'(/[^\s"\'<>]+)', html_text)
                
                # Sanitize re.findall outputs: convert any matching tuples safely into strings
                pdf_urls = []
                for item in pdf_urls_raw:
                    u = item[0] if isinstance(item, tuple) else item
                    u_lower = u.lower()
                    
                    is_pdf_target = (
                        ".pdf" in u_lower or 
                        "_pdf" in u_lower or 
                        "/download/" in u_lower or 
                        "/directories/" in u_lower
                    )
                    if is_pdf_target:
                        absolute_u = urllib.parse.urljoin(viewer_url, u)
                        absolute_u = absolute_u.replace("\\/", "/") # Clean up JSON escaped slashes
                        if absolute_u not in pdf_urls:
                            pdf_urls.append(absolute_u)
                
                # Filter and Rank candidate URLs to identify the correct target paper
                # Normalizing separator differences (dashes/underscores) during verification
                target_base_name = filename.split(".")[0].lower()  # e.g., "5090_w25_ms_11"
                target_clean = target_base_name.replace("-", "").replace("_", "")  # e.g., "5090s24ms21"
                valid_pdf_urls = []
                
                for u in pdf_urls:
                    u_clean = urllib.parse.unquote(u).lower()
                    u_clean_stripped = u_clean.replace("-", "").replace("_", "")
                    
                    if "5090" in u_clean or "biology" in u_clean:
                        # Match scoring calculation
                        score = 0
                        if target_clean in u_clean_stripped:
                            score += 10
                        subsegments = filename.split(".")[0].replace("-", "_").split("_")
                        for sub in subsegments:
                            if len(sub) >= 2 and sub in u_clean_stripped:
                                score += 2
                                
                        if score > 0:
                            valid_pdf_urls.append((score, u))
                            
                # Sort candidate links by score (highest matching confidence first)
                valid_pdf_urls.sort(key=lambda x: x[0], reverse=True)
                
                if valid_pdf_urls:
                    # Attempt to download candidates in order of score
                    for score, real_pdf_url in valid_pdf_urls[:3]:
                        try:
                            sub_response = session.get(real_pdf_url, headers=headers, stream=True, timeout=15)
                            if sub_response.status_code == 200:
                                sub_iterator = sub_response.iter_content(chunk_size=2048)
                                try:
                                    sub_chunk = next(sub_iterator)
                                except StopIteration:
                                    sub_chunk = b""
                                    
                                if sub_chunk.startswith(b"%PDF"):
                                    with open(dest_path, 'wb') as f:
                                        f.write(sub_chunk)
                                        for chunk in sub_iterator:
                                            f.write(chunk)
                                    return True
                        except Exception:
                            continue
                            
                # Diagnostics printout if extraction fails
                print(f"      ⚠️  Could not extract direct PDF from HTML. HTML Preview: '{html_text[:120].strip()}...'")
                return False
            else:
                preview = first_chunk[:150].decode('utf-8', errors='ignore').strip()
                print(f"      ⚠️  Not a valid PDF file. Server returned: '{preview[:80]}...'")
                return False
        else:
            print(f"      ❌ HTTP connection failed with status code {response.status_code}")
            return False
    except Exception as e:
        print(f"      ❌ Connection error: {str(e)}")
        return False


def download_pdfs_on_page(driver, year, session):
    """Gathers Viewer elements and routes streaming actions to the Requests layer."""
    abs_output_path = os.path.abspath(OUTPUT_DIR)
    folder_dest = os.path.join(abs_output_path, str(year), session)
    os.makedirs(folder_dest, exist_ok=True)
    
    driver.switch_to.default_content()
    
    viewer_elements = []
    for attempt in range(4):
        viewer_elements = find_viewer_elements_on_page(driver)
        if viewer_elements:
            break
        time.sleep(2.0)
        
    if not viewer_elements:
        print(f"  ⚠️  No target View File buttons found in {year} -> {session}.")
        return 0
        
    print(f"  🔍 Found {len(viewer_elements)} matching papers on screen. Downloading...")
    
    successful_downloads = 0
    for filename, viewer_url in viewer_elements:
        dest = os.path.join(folder_dest, filename)
        
        # If successfully downloaded previously, skip
        if os.path.exists(dest) and os.path.getsize(dest) > 1000:
            continue
            
        # Download by parsing the viewer layout directly via the Python requests layer
        success = download_file_with_requests(driver, viewer_url, dest, filename)
        if success:
            print(f"    ✅ Saved: {filename}")
            successful_downloads += 1
            time.sleep(DELAY_ON_SUCCESS + random.uniform(0.1, 0.3))
        else:
            # Clean up corrupted file remnants if any were left over
            if os.path.exists(dest):
                try:
                    os.remove(dest)
                except Exception:
                    pass
            print(f"    ❌ Download failed for: {filename}")
            
    return successful_downloads


# ── Downloader Engine ─────────────────────────────────────────────────────────
def run_downloader(driver, folder_urls):
    abs_output_path = os.path.abspath(OUTPUT_DIR)
    os.makedirs(abs_output_path, exist_ok=True)
    
    print(f"\n📂 Files will be saved to: {abs_output_path}")
    
    total_downloads = 0
    
    for folder_info in folder_urls:
        url = folder_info["url"]
        year = folder_info["year"]
        session = folder_info["session"]
        
        print(f"\n📂 Entering directory: {year} -> {session}")
        
        try:
            driver.get(url)
            # No sub-directory wait_for_cloudflare call is needed anymore since the session cookies are validated.
            time.sleep(1.5)
            
            downloads = download_pdfs_on_page(driver, year, session)
            total_downloads += downloads
            
        except Exception as e:
            print(f"⚠️ Error processing session folder {year} {session}: {e}")
            
    print(f"\n📊 Process complete. Total new files downloaded: {total_downloads}")


# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  BioSearch — 5090 Dynamic Crawler & Downloader")
    print("=" * 60)

    driver = init_driver()
    try:
        driver.get(BASE_URL)
        wait_for_cloudflare(driver)
        
        print("⏳ Waiting for directories to render on the page...")
        time.sleep(5.0)
        
        folder_urls = discover_folder_sessions(driver)
        
        if folder_urls:
            folder_urls.sort(key=lambda x: (int(x["year"]), x["session"]), reverse=True)
            run_downloader(driver, folder_urls)
        else:
            print("❌ No matching directory folders were identified on the landing page.")

    finally:
        try:
            if driver:
                driver.quit()
        except Exception:
            pass
        print("Browser session ended.")
    print("=" * 60)