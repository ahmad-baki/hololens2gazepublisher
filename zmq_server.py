import socket
import threading
import time
import cv2
import zmq
import json
from typing import Optional, Tuple, Any, Dict


class ZMQServer(object):
    # ------------------------------------------------------------
    # 1) Discovery via UDP
    # ------------------------------------------------------------
    DISCOVERY_PORT: int     = 5005
    DISCOVERY_MESSAGE: bytes= b"DISCOVER_PC"
    DISCOVERY_REPLY: bytes  = b"PC_HERE"
    BUFFER_SIZE: int        = 1024

    def __init__(self) -> None:
        # We'll store the HoloLens's IP once discovered:
        self.hololens_address: Optional[str] = None



    def udp_discovery_listener(self) -> None:
        """
        Listens for a UDP broadcast from HoloLens. When it receives
        DISCOVER_PC, it replies with PC_HERE, so the HoloLens knows our IP.
        """
        global hololens_address

        sock: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", self.DISCOVERY_PORT))
        print(f"[PC][UDP] Listening for discovery on UDP port {self.DISCOVERY_PORT}...")

        while True:
            data: bytes
            addr: Tuple[str, int]
            data, addr = sock.recvfrom(self.BUFFER_SIZE)
            if data == self.DISCOVERY_MESSAGE:
                hololens_address = addr[0]
                print(f"[PC][UDP] Received discovery ping from HoloLens @ {hololens_address}.")
                # Reply back so HoloLens knows our IP
                sock.sendto(self.DISCOVERY_REPLY, addr)
                break  # we only need one discovery

    def init_pub_socket(self) -> None:
        # init pub for gaze data
        self.pub_context = zmq.Context()
        self.image_pub = self.pub_context.socket(zmq.PUB)
        self.image_pub.bind(f"tcp://*:{self.ZMQ_IMAGE_PUB_PORT}")
        print(f"[PC][ZMQ] Image PUB bound on tcp://*:{self.ZMQ_IMAGE_PUB_PORT}")


    def init_sub_socket(self) -> None:
        # init sub for gaze data
        self.sub_context = zmq.Context()
        self.gaze_sub = self.sub_context.socket(zmq.SUB)
        # subscribe to everything:
        self.gaze_sub.setsockopt_string(zmq.SUBSCRIBE, "")
        self.gaze_sub.bind(f"tcp://*:{self.ZMQ_GAZE_SUB_PORT}")
        print(f"[PC][ZMQ] Gaze SUB bound on tcp://*:{self.ZMQ_GAZE_SUB_PORT}")


    # ------------------------------------------------------------
    # 2) ZeroMQ Setup: PUB for images, SUB for gaze
    # ------------------------------------------------------------
    ZMQ_IMAGE_PUB_PORT: int = 5556
    ZMQ_GAZE_SUB_PORT: int  = 5557

    def zmq_image_publisher(self, step: int, cap: cv2.VideoCapture) -> None:
        """
        Captures frames from the default camera (index=0), encodes as JPEG,
        and publishes them over ZMQ PUB socket at tcp://*:5556.
        """

        # cap: cv2.VideoCapture = cv2.VideoCapture(0)  # open default camera
        #if not cap.isOpened():
        #    print("[PC][ERROR] Could not open camera. Exiting image publisher.")
        #    return

        # get image from "./test_image.jpg" for testing:

        try:
            ret: bool
            frame: Any
            ret, frame = cap.read()
            if not ret:
                print("[PC][ERROR] Failed to grab frame. Retrying...")
                return

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
                return

            jpg_bytes: bytes = encoded.tobytes()
            # Publish as a single ZMQ message
            # send 'step' as a single-byte header, then image bytes
            header: bytes = step.to_bytes(1, byteorder="big")
            self.image_pub.send_multipart([header, jpg_bytes])

        except Exception as e:
            print(f"[PC][ERROR] Exception in image publisher: {e}")
            return

    def zmq_gaze_subscriber(self) -> Tuple[float, float, int]:
        """
        Subscribes to gaze‐coordinate messages (as JSON strings) on tcp://*:5557.
        Each message could look like: { "x": 123, "y": 456, "step": 1234 }
        """
        msg: str = self.gaze_sub.recv_string()  # HoloLens will send a UTF-8 JSON
        try:
            gaze: Dict[str, Any] = json.loads(msg)
            x: Any = gaze.get("x")
            y: Any = gaze.get("y")
            step: Any = gaze.get("step")
            print(f"[PC][ZMQ] Received gaze: x={x}, y={y}, s={step}")
            return (float(x), float(y), int(step))
        except Exception as e:
            print(f"[PC][ERROR] Could not parse gaze JSON: {e} | raw: {msg}")
            return (0.0, 0.0, -1)

    def close_sub(self) -> None:
        self.sub_context.term()
        self.gaze_sub.close()

    def close_pub(self) -> None:
        self.pub_context.term()
        self.image_pub.close()