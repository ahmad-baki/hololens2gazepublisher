import sys
import threading
import time
from typing import Tuple

import cv2
import zmq
# from GazeTrackerDevice import GazeTracker
# import GazeTrackerDevice
from gaze_server import GazeServer


PUBLISH_HZ: float = 1.0
# half to prevent overloading the Buffer
REC_HZ: float = 15.0



def img_rec_and_pub(server: GazeServer) -> None:
    """
    Thread function to handle image capture and publishing.
    """
    step:int = 0  # message index for ZMQ
    context = zmq.Context()
    socket = context.socket(zmq.PUSH)
    bind_address = f"tcp://*:{server.ZMQ_IMAGE_PUB_PORT}"
    socket.bind(bind_address)
    print(f"[PC][ZMQ] PUSH bind at {bind_address}")

    img = cv2.imread("C:/Users/Ahmad/Desktop/hololens2gazepublisher/sehtest.jpg")
    if img is None:
        print(f"[PC] Error: Image '{'C:/Users/Ahmad/Desktop/hololens2gazepublisher/sehtest.jpg'}' could not be loaded.")
        sys.exit(1)

    # OpenCV liefert BGR; wir kodieren direkt als JPEG, das funktioniert
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]  # Qualität: 0–100
    success, img_encoded = cv2.imencode('.jpg', img, encode_param)
    if not success:
        print("[PC] Error: Image could not be encoded as JPEG.")
        sys.exit(1)

    img_bytes = img_encoded.tobytes()
    print(f"[PC] Image loaded ({len(img_bytes)} Bytes). Starting send loop.")

    # 3. Optional: in einer Schleife senden, sonst nur einmal
    try:
        while True:
            time.sleep(1)
            # Sende das Byte‐Array in einer ZeroMQ‐Nachricht
            socket.send_multipart([step.to_bytes(4), img_bytes])
            step += 1
    except KeyboardInterrupt:
        print("[PC][ZMQ] Interrupted by user.")


def gaze_rec(server: GazeServer) -> None:
    """
    Thread function to handle gaze data subscription.
    """
    server.init_sub_socket()
    while True:
        try:
            gaze_data: Tuple[float, float, int] = server.zmq_gaze_subscriber()
            if gaze_data is not None:
                print(f"[PC] Gaze data received: {gaze_data}")
            else:
                print("[PC] No gaze data received.")
            time.sleep(1.0 / REC_HZ)  # wait for the next subscription cycle
        except Exception as e:
            print(f"[PC][ERROR] Exception in gaze subscriber: {e}")
            time.sleep(1.0)


if __name__ == "__main__":
    server = GazeServer()

    # 1) Run discovery listener in main thread (blocks until HL2 pings)

    server._udp_discovery_listener()
    print(f"[PC] Discovery complete. HoloLens is at {server.hololens_address}.")
    print("[PC][ZMQ] Starting threads...")

    # 2) Launch the PUB/SUB threads for image/gaze
    img_rec_and_pub_thread: threading.Thread = threading.Thread(target=img_rec_and_pub, args=(server,), daemon=True)
    gaze_rec_thread: threading.Thread = threading.Thread(target=gaze_rec, args=(server,), daemon=True)

    img_rec_and_pub_thread.start()
    gaze_rec_thread.start()
    print("[PC][ZMQ] Threads started.")


    # Keep main alive
    try:
        while True :
            in_str = input("e to exit, r to restart: ")
            # match in_str:
            #     case "e":
            #         print("[PC] Exiting...")
            #         break
            #     case "r":
            #         print("[PC] Restarting image and gaze threads...")
            if in_str == "e":
                print("[PC] Exiting...")
                break
            elif in_str == "r":
                print("[PC] Restarting image and gaze threads...")
                   
    except Exception as e:
        print("[PC] Shutting down.")
    server.close_pub()
    server.close_sub()
    print("[PC] Closed ZMQ sockets.")