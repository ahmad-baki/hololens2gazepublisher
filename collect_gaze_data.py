import sys
import threading
import time
from typing import Tuple

import cv2
import zmq
# from GazeTrackerDevice import GazeTracker
# import GazeTrackerDevice
from zmq_server import ZMQServer


PUBLISH_HZ: float = 1.0
# half to prevent overloading the Buffer
REC_HZ: float = 15.0



def img_rec_and_pub(server: ZMQServer) -> None:
    """
    Thread function to handle image capture and publishing.
    """
    step:int = 0  # message index for ZMQ
    # cap: cv2.VideoCapture = cv2.VideoCapture(0)
    # read a test image for debugging

    # chatgpt ---->
    context = zmq.Context()
    socket = context.socket(zmq.PUSH)
    bind_address = f"tcp://*:{server.ZMQ_IMAGE_PUB_PORT}"
    socket.bind(bind_address)
    print(f"[Sender] ZMQ PUSH gebunden an {bind_address}")

    img = cv2.imread("C:/Users/Ahmad/Desktop/hololens2gazepublisher/sehtest.jpg")
    if img is None:
        print(f"Fehler: Bild '{"C:/Users/Ahmad/Desktop/hololens2gazepublisher/sehtest.jpg"}' konnte nicht geladen werden.")
        sys.exit(1)

    # OpenCV liefert BGR; wir kodieren direkt als JPEG, das funktioniert
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]  # Qualität: 0–100
    success, img_encoded = cv2.imencode('.jpg', img, encode_param)
    if not success:
        print("Fehler: Bild konnte nicht als JPEG kodiert werden.")
        sys.exit(1)

    img_bytes = img_encoded.tobytes()
    print(f"[Sender] Bild geladen ({len(img_bytes)} Bytes). Starte Sendeschleife.")

    # 3. Optional: in einer Schleife senden, sonst nur einmal
    try:
        while True:
            time.sleep(1)
            # Sende das Byte‐Array in einer ZeroMQ‐Nachricht
            socket.send(img_bytes)
            print("[Sender] Bild gesendet.")
    except KeyboardInterrupt:
        print("[Sender] Abbruch durch Benutzer.")
    
    # chatgpt <----


    # Commented just for testing with a static image

    # cap = cv2.VideoCapture("C:/Users/Ahmad/Desktop/hololens2gazepublisher/sehtest.jpg")  # for testing with a static image
    # server.init_pub_socket()
    # if not cap.isOpened():
    #     print("[PC][ERROR] Could not open camera. Exiting image publisher.")
    #     return  
    # while True:
    #     try:
            
    #         # TODO: saving image to file

    #         # Capture from the default camera (index=0)

    #         server.zmq_image_publisher(step, cap)
    #         step += 1
    #         cap.release()  # release the camera after publishing
    #         time.sleep(1.0 / PUBLISH_HZ)  # wait for the next publish cycle
    #     except Exception as e:
    #         print(f"[PC][ERROR] Exception in image publisher: {e}")
    #         time.sleep(1.0)
    #         cap.release()

def gaze_rec(server: ZMQServer) -> None:
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
    server = ZMQServer()

    # 1) Run discovery listener in main thread (blocks until HL2 pings)
    server.udp_discovery_listener()
    print(f"[PC] Discovery complete. HoloLens is at {server.hololens_address}.")
    print("[PC] Starting ZMQ threads...")

    # 2) Launch the PUB/SUB threads for image/gaze
    img_rec_and_pub_thread: threading.Thread = threading.Thread(target=img_rec_and_pub, args=(server,), daemon=True)
    gaze_rec_thread: threading.Thread = threading.Thread(target=gaze_rec, args=(server,), daemon=True)

    img_rec_and_pub_thread.start()
    gaze_rec_thread.start()
    print("[PC] ZMQ threads started.")


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
    server.close_pub()
    server.close_sub()
    print("[PC] Closed ZMQ sockets.")