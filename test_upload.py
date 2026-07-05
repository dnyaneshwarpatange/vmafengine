import requests
import time
import os
import secrets

BASE_URL = "http://api:8000"

def main():
    # 1. Login as Admin
    print("Logging in as Admin...")
    res = requests.post(f"{BASE_URL}/v1/auth/login", json={"email": "admin@vmaf.local", "password": "admin"})
    if res.status_code != 200:
        print(f"Login failed: {res.text}")
        return
    token = res.json()["access_token"]
    
    # 2. Generate a dummy video using ffmpeg
    print("Generating a 5-second test video...")
    test_vid = "test_extreme.mp4"
    os.system(f"ffmpeg -y -f lavfi -i testsrc=duration=5:size=1280x720:rate=30 -c:v libx264 {test_vid}")
    
    # 3. Upload
    print("Uploading video...")
    headers = {"Authorization": f"Bearer {token}"}
    with open(test_vid, "rb") as f:
        res = requests.post(f"{BASE_URL}/v1/optimize/free", files={"file": f}, data={"target_vmaf": "93.0"}, headers=headers)
    
    if res.status_code != 200:
        print(f"Upload failed: {res.text}")
        return
        
    job_id = res.json()["job_id"]
    print(f"Job started: {job_id}")
    
    # 4. Poll
    start_time = time.time()
    while True:
        res = requests.get(f"{BASE_URL}/v1/status/{job_id}", headers=headers)
        status = res.json()["status"]
        if status in ["completed", "failed"]:
            print(f"Final Status: {status}")
            print(f"Response: {res.json()}")
            break
        print(f"Status: {status} (elapsed: {int(time.time() - start_time)}s)")
        time.sleep(2)
        
    print(f"Total processing time: {time.time() - start_time:.2f} seconds")

if __name__ == "__main__":
    main()
