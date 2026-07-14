import requests
import json
import os

# API configuration
API_URL = "https://api.ppv.st/api/streams"
OUTPUT_FILE = "playlist.m3u"

def fetch_streams():
    try:
        response = requests.get(API_URL, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching API: {e}")
        return None

def build_m3u(data):
    if not data or not data.get("success"):
        print("Invalid or unsuccessful API response.")
        return None
    
    # Initialize the M3U playlist header
    m3u_lines = ["#EXTM3U"]
    
    for category_group in data.get("streams", []):
        category_name = category_group.get("category", "Uncategorized")
        
        for stream in category_group.get("streams", []):
            name = stream.get("name", "Unknown Event")
            stream_id = stream.get("id")
            logo = stream.get("poster", "")
            
            # Use iframe embed if present; otherwise fallback to constructing a URI
            # Note: Since IPTV players require raw video streams (.m3u8, etc.), 
            # if the API only provides page URLs, players might not be able to play them directly.
            # We will use the 'iframe' source if available, or fall back to a constructed link.
            iframe_src = stream.get("iframe", "")
            uri_name = stream.get("uri_name", "")
            
            # Parse stream URL source
            stream_url = ""
            if iframe_src:
                # Basic attempt to extract src from iframe if it's a raw string
                if 'src="' in iframe_src:
                    stream_url = iframe_src.split('src="')[1].split('"')[0]
                else:
                    stream_url = iframe_src
            else:
                stream_url = f"https://ppv.st/{uri_name}" # Example fallback structure
            
            # Write M3U metadata line
            # tvg-logo: Poster image, group-title: Stream category
            m3u_lines.append(f'#EXTINF:-1 tvg-id="{stream_id}" tvg-logo="{logo}" group-title="{category_name}",{name}')
            m3u_lines.append(stream_url)
            
    return "\n".join(m3u_lines)

def main():
    print("Fetching streams from API...")
    data = fetch_streams()
    
    if data:
        playlist_content = build_m3u(data)
        if playlist_content:
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                f.write(playlist_content)
            print(f"Successfully generated {OUTPUT_FILE}")
        else:
            print("Failed to parse streams into M3U.")

if __name__ == "__main__":
    main()
