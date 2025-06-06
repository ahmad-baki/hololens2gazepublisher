import threading
import time
from typing import Tuple

import cv2
from GazeTrackerDevice import GazeTracker
import GazeTrackerDevice
from zmq_server import ZMQServer


PUBLISH_HZ: float = 30.0
# half to prevent overloading the Buffer
REC_HZ: float = 15.0



def img_rec_and_pub(server: ZMQServer) -> None:
    """
    Thread function to handle image capture and publishing.
    """
    step:int = 0  # message index for ZMQ
    cap: cv2.VideoCapture = cv2.VideoCapture(0)
    server.init_pub_socket() 
    while True:
        try:
            
            # TODO: saving image to file

            # Capture from the default camera (index=0)
            if not cap.isOpened():
                print("[PC][ERROR] Could not open camera. Exiting image publisher.")
                return
            server.zmq_image_publisher(step, cap)
            step += 1
            cap.release()  # release the camera after publishing
            time.sleep(1.0 / PUBLISH_HZ)  # wait for the next publish cycle
        except Exception as e:
            print(f"[PC][ERROR] Exception in image publisher: {e}")
            time.sleep(1.0)
            cap.release()

def gaze_rec(server: ZMQServer) -> GazeTrackerDevice.GazeTrackerDevice:
    """
    Thread function to handle gaze data subscription.
    """
    gaze_tracker = GazeTrackerDevice.GazeTrackerDevice(server)
    gaze_tracker._setup_connect()
    return gaze_tracker


if __name__ == "__main__":
    server = ZMQServer()

    # 1) Run discovery listener in main thread (blocks until HL2 pings)
    server.udp_discovery_listener()
    print(f"[PC] Discovery complete. HoloLens is at {server.hololens_address}.")
    print("[PC] Starting ZMQ threads...")

    # 2) Launch the PUB/SUB threads for image/gaze
    img_rec_and_pub_thread: threading.Thread = threading.Thread(target=server.zmq_image_publisher, daemon=True)
    gaze_tracker: GazeTrackerDevice = gaze_rec(server)
    img_rec_and_pub_thread.start()
    gaze_rec_thread.start()

    # Keep main alive
    try:
        while True :
            in_str = input("e to exit, r to restart: ")
            match in_str:
                case "e":
                    print("[PC] Exiting...")
                    break
                    
                case "r":
                    print("[PC] Restarting image and gaze threads...")
                   
    except Exception as e:
        print("[PC] Shutting down.")
    server.close()
