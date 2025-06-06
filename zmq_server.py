import socket
import threading
import time
import cv2
import zmq
import json
from typing import Optional, Tuple, Any, Dict

# ------------------------------------------------------------
# 1) Discovery via UDP
# ------------------------------------------------------------
DISCOVERY_PORT: int     = 5005
DISCOVERY_MESSAGE: bytes= b"DISCOVER_PC"
DISCOVERY_REPLY: bytes  = b"PC_HERE"
BUFFER_SIZE: int        = 1024
PC_WIFI_IP: str =  "192.168.0.208"

# We'll store the HoloLens's IP once discovered:
hololens_address: Optional[str] = None

def udp_discovery_listener() -> None:
    """
    Listens for a UDP broadcast from HoloLens. When it receives
    DISCOVER_PC, it replies with PC_HERE, so the HoloLens knows our IP.
    """
    global hololens_address

    sock: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # sock.bind((PC_WIFI_IP, DISCOVERY_PORT))
    sock.bind(("", DISCOVERY_PORT))
    print(f"[PC][UDP] Listening for discovery on UDP port {DISCOVERY_PORT}...")

    while True:
        data: bytes
        addr: Tuple[str, int]
        data, addr = sock.recvfrom(BUFFER_SIZE)
        if data == DISCOVERY_MESSAGE:
            hololens_address = addr[0]
            print(f"[PC][UDP] Received discovery ping from HoloLens @ {hololens_address}.")
            # Reply back so HoloLens knows our IP
            sock.sendto(DISCOVERY_REPLY, addr)
            break  # we only need one discovery

# ------------------------------------------------------------
# 2) ZeroMQ Setup: PUB for images, SUB for gaze
# ------------------------------------------------------------
ZMQ_IMAGE_PUB_PORT: int = 5556
ZMQ_GAZE_SUB_PORT: int  = 5557
PUBLISH_HZ: float       = 30.0

def zmq_image_publisher() -> None:
    """
    Captures frames from the default camera (index=0), encodes as JPEG,
    and publishes them over ZMQ PUB socket at tcp://*:5556.
    """
    context = zmq.Context()
    image_pub = context.socket(zmq.PUB)
    image_pub.bind(f"tcp://{PC_WIFI_IP}:{ZMQ_IMAGE_PUB_PORT}")
    print(f"[PC][ZMQ] Image PUB bound on tcp://{PC_WIFI_IP}:{ZMQ_IMAGE_PUB_PORT}")

    # cap: cv2.VideoCapture = cv2.VideoCapture(0)  # open default camera
    #if not cap.isOpened():
    #    print("[PC][ERROR] Could not open camera. Exiting image publisher.")
    #    return

    # get image from "./test_image.jpg" for testing:
    cap: cv2.VideoCapture = cv2.VideoCapture("./test_image.jpg")
    if not cap.isOpened():
        print("[PC][ERROR] Could not open test image. Exiting image publisher.")
        return

    try:
        step:int = 0  # message index for ZMQ
        while True:
            ret: bool
            frame: Any
            ret, frame = cap.read()
            if not ret:
                print("[PC][ERROR] Failed to grab frame. Retrying...")
                time.sleep(0.1)
                continue

            # Resize if you want to reduce bandwidth:
            # frame = cv2.resize(frame, (640, 480))

            # Encode to JPEG in‐memory
            success: bool
            encoded: Any
            success, encoded = cv2.imencode(
                '.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70]
            )
            if not success:
                print("[PC][ERROR] JPEG encoding failed.")
                continue

            jpg_bytes: bytes = encoded.tobytes()
            # Publish as a single ZMQ message
            # send 'step' as a single-byte header, then image bytes
            header: bytes = step.to_bytes(1, byteorder="big")
            image_pub.send_multipart([header, jpg_bytes])
            step += 1
            # ~30 FPS max:
            time.sleep(1 / PUBLISH_HZ)

    except KeyboardInterrupt:
        print("[PC][ZMQ] Image publisher interrupted. Exiting.")
    finally:
        cap.release()
        image_pub.close()
        context.term()

def zmq_gaze_subscriber() -> None:
    """
    Subscribes to gaze‐coordinate messages (as JSON strings) on tcp://*:5557.
    Each message could look like: { "x": 123, "y": 456, "timestamp": 1234567890.0 }
    """
    context = zmq.Context()
    gaze_sub = context.socket(zmq.SUB)
    # subscribe to everything:
    gaze_sub.setsockopt_string(zmq.SUBSCRIBE, "")
    gaze_sub.bind(f"tcp://{PC_WIFI_IP}:{ZMQ_GAZE_SUB_PORT}")
    print(f"[PC][ZMQ] Gaze SUB bound on tcp://{PC_WIFI_IP}:{ZMQ_GAZE_SUB_PORT}")

    try:
        while True:
            msg: str = gaze_sub.recv_string()  # HoloLens will send a UTF-8 JSON
            try:
                gaze: Dict[str, Any] = json.loads(msg)
                x: Any = gaze.get("x")
                y: Any = gaze.get("y")
                ts: Any = gaze.get("timestamp")
                print(f"[PC][ZMQ] Received gaze: x={x}, y={y}, t={ts}")
                # TODO: you can store these into a CSV, database, etc.
            except Exception as e:
                print(f"[PC][ERROR] Could not parse gaze JSON: {e} | raw: {msg}")
    except KeyboardInterrupt:
        print("[PC][ZMQ] Gaze subscriber interrupted. Exiting.")
    finally:
        gaze_sub.close()
        context.term()

# ------------------------------------------------------------
# 3) Main: run discovery, then start both ZMQ threads
# ------------------------------------------------------------
if __name__ == "__main__":
    # 1) Run discovery listener in main thread (blocks until HL2 pings)
    udp_discovery_listener()
    print(f"[PC] Discovery complete. HoloLens is at {hololens_address}.")
    print("[PC] Starting ZMQ threads...")

    # 2) Launch the PUB/SUB threads for image/gaze
    t1: threading.Thread = threading.Thread(target=zmq_image_publisher, daemon=True)
    t2: threading.Thread = threading.Thread(target=zmq_gaze_subscriber, daemon=True)
    t1.start()
    t2.start()

    # Keep main alive
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("[PC] Shutting down.")