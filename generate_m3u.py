import requests
import re
import os
from playwright.sync_api import sync_playwright

API_URL = "https://api.ppv.st/api/streams"
OUTPUT_FILE = "playlist.m3u"

def fetch_streams():
    try:
        response = requests.get(API_URL, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching API: {e}")
        return None

def extract_m3u8(iframe_html):
    """
    Launches a headless browser, loads the iframe player,
    and intercepts network requests to find the .m3u8 URL.
    """
    if not iframe_html:
        return None
    
    # Extract the URL from the iframe src attribute
    match = re.search(r'src=["\'](https?://[^"\']+)["\']', iframe_html)
    if not match:
        return None
    
    target_url = match.group(1)
    m3u8_url = None
    
    print(f"Scanning player page: {target_url}")
    
    with sync_playwright() as p:
        # Launch Chromium headlessly
        browser = p.chromium.launch(headless=True)
        # Emulate a real desktop browser to bypass simple bot checks
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # Intercept network requests
        def monitor_request(request):
            nonlocal m3u8_url
            url = request.url
            # Sniff for HLS video files (.m3u8)
            if ".m3u8" in url and "chunks.m3u8" not in url: 
                m3u8_url = url
                print(f" Found stream: {m3u8_url}")
        
        page.on("request", monitor_request)
        
        try:
            # Open the player page and wait up to 15 seconds for network traffic to settle
            page.goto(target_url, wait_until="networkidle", timeout=15000)
            # Give the player 3 extra seconds to fire off the media request
            page.wait_for_timeout(3000)
        except Exception as e:
            print(f"Note (page load): {e}")
        finally:
            browser.close()
            
    return m3u8_url

def build_m3u(data):
    if not data or not data.get("success"):
        print("Invalid API response structure.")
        return None
    
    m3u_lines = ["#EXTM3U"]
    
    for category_group in data.get("streams", []):
        category_name = category_group.get("category", "Uncategorized")
        
        for stream in category_group.get("streams", []):
            name = stream.get("name", "Unknown Event")
            stream_id = stream.get("id")
            logo = stream.get("poster", "")
            iframe_html = stream.get("iframe", "")
            
            # Try to grab the raw .m3u8 source
            m3u8_link = extract_m3u8(iframe_html)
            
            # If Playwright successfully extracted a stream URL, use it!
            # Otherwise, fall back to the embed/web page URL so the item isn't totally blank.
            if m3u8_link:
                stream_url = m3u8_link
            else:
                print(f"⚠️ Could not extract .m3u8 for '{name}'. Using web fallback.")
                # Fallback to src extract or uri_name
                match = re.search(r'src=["\'](https?://[^"\']+)["\']', iframe_html)
                stream_url = match.group(1) if match else f"https://ppv.st/{stream.get('uri_name', '')}"
            
            m3u_lines.append(f'#EXTINF:-1 tvg-id="{stream_id}" tvg-logo="{logo}" group-title="{category_name}",{name}')
            m3u_lines.append(stream_url)
            print("-" * 40)
            
    return "\n".join(m3u_lines)

def main():
    print("Fetching updated streams from API...")
    data = fetch_streams()
    
    if data:
        playlist_content = build_m3u(data)
        if playlist_content:
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                f.write(playlist_content)
            print(f"Successfully updated {OUTPUT_FILE}")
        else:
            print("Failed to build the playlist file.")

if __name__ == "__main__":
    main()
