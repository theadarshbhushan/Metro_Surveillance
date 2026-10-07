"""One-command demo: sample video -> YOLO -> tracking -> seat polygons -> telemetry -> Flask -> React.

    python run_demo.py                    # starts the backend itself if it is not running
    python run_demo.py --video my.mp4     # use your own recording
    python run_demo.py --no-window        # headless

Then open the React dashboard (npm run dev in frontend/) to watch the live result.
If videos/demo.mp4 does not exist it is generated from videos/bus.jpg (pipeline demo only).
"""

import argparse
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))


def backend_alive(url: str) -> bool:
    import requests
    try:
        return requests.get(f"{url}/api/health", timeout=1).ok
    except requests.RequestException:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--video", default=os.path.join(ROOT, "videos", "demo.mp4"))
    ap.add_argument("--backend-url", default=os.environ.get("BACKEND_URL", "http://localhost:5000"))
    ap.add_argument("--no-window", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.video):
        image = os.path.join(ROOT, "videos", "bus.jpg")
        if not os.path.exists(image):
            print(f"No video at {args.video} and no sample image to build one from.")
            return 1
        subprocess.check_call([sys.executable, os.path.join(ROOT, "tools", "make_demo_video.py"),
                               "--image", image, "--out", args.video])

    backend = None
    if not backend_alive(args.backend_url):
        print("Backend not running - starting it ...")
        env = dict(os.environ, DATA_SOURCE=os.environ.get("DATA_SOURCE", "auto"))
        backend = subprocess.Popen([sys.executable, os.path.join(ROOT, "backend", "app.py")], env=env)
        for _ in range(30):
            if backend_alive(args.backend_url):
                break
            time.sleep(0.5)
        else:
            print("Backend did not start.")
            backend.terminate()
            return 1

    model = os.path.join(ROOT, "models", "yolov8n.pt")
    cmd = [sys.executable, os.path.join(ROOT, "run_vision.py"), "--source", args.video, "--loop", "--realtime",
           "--backend-url", args.backend_url, "--coach-id", "C1"]
    if os.path.exists(model):
        cmd += ["--model", model]
    if not args.no_window:
        cmd.append("--show")
    print("Dashboard: run `npm run dev` in frontend/ and open http://localhost:5173")
    try:
        return subprocess.call(cmd)
    except KeyboardInterrupt:
        return 0
    finally:
        if backend is not None:
            backend.terminate()


if __name__ == "__main__":
    raise SystemExit(main())
