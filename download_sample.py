
import urllib.request
import os

VIDEO_URL = "https://download.blender.org/peach/bigbuckbunny_movies/BigBuckBunny_320x180.mp4"

CROWD_URLS = [
    "https://www.pexels.com/download/video/3045076/",
    "https://www.pexels.com/download/video/2670345/",
]

def download_video():
    os.makedirs("data", exist_ok=True)
    output_path = os.path.join("data", "video.mp4")

    if os.path.exists(output_path):
        print(f"[INFO] Video already exists: {output_path}")
        return

    print("=" * 50)
    print("  VIDEO DOWNLOAD HELPER")
    print("=" * 50)
    print()
    print("  No video file found at data/video.mp4")
    print()
    print("  Please download a crowd/pedestrian video manually:")
    print()
    print("  FREE SOURCES:")
    print("  1. https://www.pexels.com/search/videos/crowd/")
    print("  2. https://www.pexels.com/search/videos/pedestrian/")
    print("  3. https://pixabay.com/videos/search/crowd/")
    print()
    print("  STEPS:")
    print("  1. Download any video with people walking")
    print("  2. Rename it to 'video.mp4'")
    print(f"  3. Place it in: {os.path.abspath('data')}")
    print()
    print("  OR use your webcam instead:")
    print("    python backend/tracker.py --source 0")
    print()
    print("=" * 50)


if __name__ == "__main__":
    download_video()
