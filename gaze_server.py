import re
import socket
import threading
import time
import cv2
import zmq
import json
from typing import Optional, Tuple, Any, Dict
import sys


def get_wlan_ip() -> str:
    if(sys.platform.startswith("win")):
        # Windows version
        print("[PC] Detecting WLAN IP address on Windows...")
        import subprocess
        result = subprocess.run('ipconfig', stdout=subprocess.PIPE, text=True).stdout.lower()
        scan = 0
        for i in result.split('\n'):
            if 'wireless' in i:
                scan = 1
            if scan:
                if 'ipv4' in i:
                    return i.split(':')[1].strip()
    elif(sys.platform.startswith("linux")):
        print("[PC] Detecting WLAN IP address on Linux...")
        import pyric.pyw as pyw

        wlan_interfaces: list = pyw.winterfaces()
        if len(wlan_interfaces) == 0:
            raise RuntimeError("No WLAN interfaces found. Please ensure you have a Wi-Fi adapter connected.")

        wlan_interface_name: str = wlan_interfaces[0]  # Use the first WLAN interface found
        wlan_interface = pyw.getcard(wlan_interface_name)
        ip, mask, bcast = pyw.ifaddrget(wlan_interface)
        return ip

    else:
        raise Exception("Unsupported platform for WLAN IP detection.")
    raise Exception("Could not determine WLAN IP address.")

class GazeServer(object):
    DISCOVERY_PORT: int     = 5005
    DISCOVERY_MESSAGE: bytes= b"DISCOVER_PC"
    DISCOVERY_REPLY: bytes  = b"PC_HERE"
    BUFFER_SIZE: int        = 1024
    ZMQ_IMAGE_PUB_PORT: int = 5006
    ZMQ_GAZE_SUB_PORT: int  = 5007
    PC_WIFI_IP: str = get_wlan_ip()

    def __init__(self) -> None:
        # We'll store the HoloLens's IP once discovered:
        self.hololens_address: Optional[str] = None

    def setup_connection(self) -> None:
        """
        Sets up the connection by starting the UDP discovery listener.
        This will block until a HoloLens sends a DISCOVER_PC message.
        """
        self._udp_discovery_listener()
        self._init_pub_socket()
        self._init_sub_socket()

    def _udp_discovery_listener(self) -> None:
        """
        Listens for a UDP broadcast from HoloLens. When it receives
        DISCOVER_PC, it replies with PC_HERE, so the HoloLens knows our IP.
        """
        global hololens_address

        sock: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.PC_WIFI_IP, self.DISCOVERY_PORT))
        print(f"[PC][UDP] Listening for discovery on {self.PC_WIFI_IP}:{self.DISCOVERY_PORT}...")

        while True:
            data: bytes
            addr: Tuple[str, int]
            data, addr = sock.recvfrom(self.BUFFER_SIZE)
            print(f"[PC][UDP] Received data: {data} from {addr}")
            if data == self.DISCOVERY_MESSAGE:
                self.hololens_address = addr[0]
                print(f"[PC][UDP] Received discovery ping from HoloLens @ {self.hololens_address}.")
                # Reply back so HoloLens knows our IP
                sock.sendto(self.DISCOVERY_REPLY, addr)
                break  # we only need one discovery

    def zmq_image_publisher(self, step: int, image: cv2.typing.MatLike) -> None:
        """
        Captures frames from the default camera (index=0), encodes as JPEG,
        and publishes them over ZMQ PUB socket at tcp://*:5556.
        """
        try:
            
            image_bytes: bytes = image.tobytes()
            # Publish as a single ZMQ message
            step_bytes: bytes = step.to_bytes(4, byteorder="big")
            self.image_pub.send_multipart([step_bytes, image_bytes])
            print(f"[PC][ZMQ] Published image with step={step} | size={len(image_bytes)} bytes")

        except Exception as e:
            print(f"[PC][ERROR] Exception in image publisher: {e}")
            return

    def zmq_gaze_subscriber(self) -> Tuple[float, float, int]:
        """
        Subscribes to gaze‐coordinate messages (as JSON strings) on tcp://*:5557.
        Each message could look like: { "x": 123, "y": 456, "step": 1234 }
        """
        msg: str = self.gaze_sub.recv_string()
        try:
            fixed = re.sub(r'(\d),(\d)', r'\1.\2', msg)
            gaze: Dict[str, Any] = json.loads(fixed)
            x: Any = gaze.get("x")
            y: Any = gaze.get("y")
            step: Any = gaze.get("step")
            return (float(x), float(y), int(step))
        except Exception as e:
            print(f"[PC][ERROR] Could not parse gaze JSON: {e} | raw: {msg}")
            return (0.0, 0.0, -1)

    def close(self) -> None:
        """
        Closes the ZeroMQ sockets and contexts.
        """
        self._close_pub()
        self._close_sub()
        print("[PC][ZMQ] Closed all sockets and contexts.")


    def _init_pub_socket(self) -> None:
        # init pub for gaze data
        self.pub_context = zmq.Context()
        self.image_pub = self.pub_context.socket(zmq.PUB)
        self.image_pub.bind(f"tcp://*:{self.ZMQ_IMAGE_PUB_PORT}")
        print(f"[PC][ZMQ] Image PUB bound on tcp://*:{self.ZMQ_IMAGE_PUB_PORT}")


    def _init_sub_socket(self) -> None:
        # init sub for gaze data
        self.sub_context = zmq.Context()
        self.gaze_sub = self.sub_context.socket(zmq.PULL)
        self.gaze_sub.bind(f"tcp://*:{self.ZMQ_GAZE_SUB_PORT}")
        print(f"[PC][ZMQ] Gaze SUB bound on tcp://*:{self.ZMQ_GAZE_SUB_PORT}")

    def _close_sub(self) -> None:
        self.sub_context.term()
        self.gaze_sub.close()

    def _close_pub(self) -> None:
        self.pub_context.term()
        self.image_pub.close()
