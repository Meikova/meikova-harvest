import json
import os
import sys
import time

# Add root folder to sys.path so app.py can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, TEMP_DOWNLOAD_DIR

def run_integration_tests():
    client = app.test_client()
    
    # ----------------------------------------------------
    # TEST 1: Subtitle Translation
    # ----------------------------------------------------
    print("\n" + "="*50)
    print("TEST 1: Subtitle Translation to Vietnamese")
    url_sub = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    payload_sub = {
        "url": url_sub,
        "format_id": "en",  # Request English captions
        "ext": "vtt",
        "title": "RickRoll_Subs",
        "client_id": "test_phase3",
        "translate_subs": "vi"  # Request auto-translation to Vietnamese
    }
    
    response = client.post('/api/download', json=payload_sub)
    print("Test 1 Enqueue Response Status:", response.status_code)
    data = response.get_json()
    print("Response payload:", data)
    
    if response.status_code == 200 and data.get("status") == "success":
        download_id = data["download_id"]
        # Poll for status
        while True:
            status_res = client.get(f'/api/download/status/{download_id}')
            status_data = status_res.get_json()
            status = status_data.get("status")
            print(f"Test 1 status: {status} | progress: {status_data.get('progress')}% | message: {status_data.get('message')}")
            
            if status in ["complete", "error"]:
                if status == "complete":
                    # Check if the output file exists in temp dir
                    temp_dir = os.path.join(TEMP_DOWNLOAD_DIR, f"temp_{download_id}")
                    files = os.listdir(temp_dir) if os.path.exists(temp_dir) else []
                    print("Test 1 files on disk:", files)
                    vtt_files = [f for f in files if f.endswith(".vtt")]
                    if vtt_files:
                        print("SUCCESS: Translated subtitle file found:", vtt_files[0])
                        # Print first few lines of the VTT file to verify it exists and contains subtitles
                        with open(os.path.join(temp_dir, vtt_files[0]), 'r', encoding='utf-8') as vf:
                            lines = vf.readlines()
                            print("VTT Preview:")
                            print("".join(lines[:15]))
                    else:
                        print("FAILURE: No VTT file found on disk.")
                else:
                    print("FAILURE: Task ended with error:", status_data.get("error"))
                break
            time.sleep(2)
            
    # ----------------------------------------------------
    # TEST 2: Video Trimming (Standard YouTube Video)
    # ----------------------------------------------------
    print("\n" + "="*50)
    print("TEST 2: Video Trimming (Download first 3 seconds of a fast video)")
    # We use a short/fast loading video
    url_vid = "https://www.youtube.com/watch?v=aqz-KE-bpKQ"
    payload_vid = {
        "url": url_vid,
        "format_id": "18",  # Standard 360p mp4 format
        "ext": "mp4",
        "title": "Mẹo tải nhạc test trim",
        "client_id": "test_phase3",
        "trim_start": "00:00:01",
        "trim_end": "00:00:04"
    }
    
    response = client.post('/api/download', json=payload_vid)
    print("Test 2 Enqueue Response Status:", response.status_code)
    data = response.get_json()
    print("Response payload:", data)
    
    if response.status_code == 200 and data.get("status") == "success":
        download_id = data["download_id"]
        # Poll for status
        while True:
            status_res = client.get(f'/api/download/status/{download_id}')
            status_data = status_res.get_json()
            status = status_data.get("status")
            print(f"Test 2 status: {status} | progress: {status_data.get('progress')}% | message: {status_data.get('message')}")
            
            if status in ["complete", "error"]:
                if status == "complete":
                    temp_dir = os.path.join(TEMP_DOWNLOAD_DIR, f"temp_{download_id}")
                    files = os.listdir(temp_dir) if os.path.exists(temp_dir) else []
                    print("Test 2 files on disk:", files)
                    mp4_files = [f for f in files if f.endswith(".mp4")]
                    if mp4_files:
                        file_path = os.path.join(temp_dir, mp4_files[0])
                        size_mb = os.path.getsize(file_path) / (1024 * 1024)
                        print(f"SUCCESS: Trimmed video file found: {mp4_files[0]} ({size_mb:.2f} MB)")
                    else:
                        print("FAILURE: No MP4 file found on disk.")
                else:
                    print("FAILURE: Task ended with error:", status_data.get("error"))
                break
            time.sleep(2)

if __name__ == "__main__":
    run_integration_tests()
