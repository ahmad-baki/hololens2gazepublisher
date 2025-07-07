import sys
import threading
import time
from typing import Dict, Any

import cv2
from gaze_server import GazeServer

PUBLISH_HZ: float = 1.0
REC_HZ: float = 15.0


def img_rec_and_pub(server: GazeServer) -> None:
    """
    Thread function to handle image capture and publishing.
    """
    step: int = 0
    img = cv2.imread("/home/abaki/Desktop/hololens2gazepublisher/sehtest.jpg")
    if img is None:
        print(f"[PC] Error: Image './sehtest.jpg' could not be loaded.")
        sys.exit(1)

    try:
        while True:
            time.sleep(1.0 / PUBLISH_HZ)
            server.zmq_publish_image(str(step), img)
            step += 1
    except KeyboardInterrupt:
        print("[PC][ZMQ] Interrupted by user.")


def gaze_rec(server: GazeServer) -> None:
    """
    Thread function to handle gaze data requests via REQ/REP.
    """
    while True:
        try:
            gaze_data: Dict[str, Any] = server.zmq_get_gaze()
            print(f"[PC] Gaze data received: {gaze_data}")
            time.sleep(1.0 / REC_HZ)
        except Exception as e:
            print(f"[PC][ERROR] Exception in gaze subscriber: {e}")
            time.sleep(1.0)


if __name__ == "__main__":
    server = GazeServer()
    # perform discovery + ZMQ socket setup
    server.setup_connection()

    print(f"[PC] Discovery complete. HoloLens is at {server.hololens_address}.")
    print("[PC][ZMQ] Starting threads...")

    img_thread = threading.Thread(target=img_rec_and_pub, args=(server,), daemon=True)
    gaze_thread = threading.Thread(target=gaze_rec, args=(server,), daemon=True)

    img_thread.start()
    gaze_thread.start()
    print("[PC][ZMQ] Threads started.")

    try:
        while True:
            cmd = input("e to exit, r to restart: ").strip().lower()
            if cmd == "e":
                print("[PC] Exiting...")
                break
            elif cmd == "r":
                print("[PC] Restarting threads not yet implemented.")
    except KeyboardInterrupt:
        print("\n[PC] Shutting down.")

    server.close()
    print("[PC] Closed ZMQ sockets.")