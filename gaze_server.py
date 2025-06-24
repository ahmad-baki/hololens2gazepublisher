import re
import socket
import struct
import time
import cv2
import zmq
import json
from typing import Optional, Tuple, Any, Dict
import sys


def get_wlan_ip() -> str:
    ip: str = ""
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
                    ip = i.split(':')[1].strip()
                    break
    elif(sys.platform.startswith("linux")):
        print("[PC] Detecting WLAN IP address on Linux...")
        import pyric.pyw as pyw

        wlan_interfaces: list = pyw.winterfaces()
        if len(wlan_interfaces) == 0:
            raise RuntimeError("No WLAN interfaces found. Please ensure you have a Wi-Fi adapter connected.")

        wlan_interface_name: str = wlan_interfaces[0]  # Use the first WLAN interface found
        wlan_interface = pyw.getcard(wlan_interface_name)
        ip, mask, bcast = pyw.ifaddrget(wlan_interface)
    else:
        raise Exception("Unsupported platform for WLAN IP detection.")
    if ip == "":
        raise RuntimeError("Could not detect WLAN IP address. Please ensure you are connected to a Wi-Fi network.")
    print(f"[PC] WLAN-IP address: {ip}")
    return ip

class GazeServer(object):
    DISCOVERY_PORT: int     = 5005
    DISCOVERY_MESSAGE: bytes= b"DISCOVER_PC"
    DISCOVERY_REPLY: bytes  = b"PC_HERE"
    BUFFER_SIZE: int        = 1024
    ZMQ_IMG_PORT: int = 5006
    ZMQ_GAZE_PORT: int  = 5007
    PC_WIFI_IP: str = ""
    # Set False if working on linux, idk why
    bind_to_wifi: bool = False  # Set to False if you want to bind to all interfaces, 

    def __init__(self) -> None:
        # We'll store the HoloLens's IP once discovered:
        self.hololens_address: Optional[str] = None

    def setup_connection(self) -> None:
        """
        Sets up the connection by starting the UDP discovery listener.
        This will block until a HoloLens sends a DISCOVER_PC message.
        """
        self._udp_discovery_listener()
        self._init_img_socket()
        self._init_gaze_socket()

    def _udp_discovery_listener(self) -> None:
        """
        Listens for a UDP broadcast from HoloLens. When it receives
        DISCOVER_PC, it replies with PC_HERE, so the HoloLens knows our IP.
        """
        global hololens_address

        sock: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        bind_address: Tuple[str, int]
        if self.bind_to_wifi:
            self.PC_WIFI_IP = get_wlan_ip()
            print(f"[PC][UDP] Binding to WLAN IP: {self.PC_WIFI_IP}")
            bind_address = (self.PC_WIFI_IP, self.DISCOVERY_PORT)
        else:
            bind_address = ('', self.DISCOVERY_PORT)

        print(f"[PC][UDP] Binding to {bind_address} for discovery...")
        sock.bind(bind_address)
        print(f"[PC][UDP] Listening for discovery on {bind_address}...")
        # hacky
        # self.hololens_address = "10.68.147.179"
        # sock.sendto(self.DISCOVERY_REPLY, ('10.68.147.179', 55538))
        # print(f"[PC][UDP] Sent discovery reply to HoloLens @ {self.hololens_address}:{55538}.")

        while True:
            data: bytes
            addr: Tuple[str, int]
            data, addr = sock.recvfrom(self.BUFFER_SIZE)
            print(f"[PC][UDP] Received data: {data} from {addr}")
            print(f"[PC][UDP] Received data: {data} from {addr[0]}:{addr[1]}")
            if data == self.DISCOVERY_MESSAGE:
                self.hololens_address = addr[0]
                print(f"[PC][UDP] Received discovery ping from HoloLens @ {addr}.")
                # Reply back so HoloLens knows our IP
                for _ in range(10):
                    sock.sendto(self.DISCOVERY_REPLY, addr)
                    time.sleep(0.05)
                break  # we only need one discovery

    def zmq_publish_image(self, timestamp: str, image: cv2.typing.MatLike) -> None:
        """
        Captures frames from the default camera (index=0), encodes as JPEG,
        and publishes them over ZMQ PUB socket at tcp://*:5556.
        """
        try:
            # Convert the timestamp to bytes
            timestamp_bytes: bytes = timestamp.encode('utf-8')

            # Convert the image to JPEG format and encode it
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]  # Quality: 0–100
            success, img_encoded = cv2.imencode('.jpg', image, encode_param)
            if not success:
                print("[PC][ERROR] Image could not be encoded as JPEG.")
                return
            # Convert the encoded image to bytes
            image_bytes: bytes = img_encoded.tobytes()

            self.image_pub.send_multipart([timestamp_bytes, image_bytes])
            print(f"[PC][ZMQ] Published image with step={timestamp} | size={len(image_bytes)} bytes")

        except Exception as e:
            print(f"[PC][ERROR] Exception in image publisher: {e}")
            return

    def zmq_get_gaze(self) -> Dict[str, Any]:
        """
        Subscribes to gaze‐coordinate messages (as JSON strings) on tcp://*:5557.
        Each message could look like: { "x": 123, "y": 456, "time": 123325.4545 }
        """
        self.gaze_req.send_string("")
        msg: str = self.gaze_req.recv_string()
        gaze = json.loads(msg)
        print(f"[PC][ZMQ] Received gaze data: {gaze}")
        return gaze

    def close(self) -> None:
        """
        Closes the ZeroMQ sockets and contexts.
        """
        self._close_gaze()
        self._close_img()
        print("[PC][ZMQ] Closed all sockets and contexts.")


    def _init_img_socket(self) -> None:
        # init pub for gaze data
        self.pub_context = zmq.Context()
        self.image_pub = self.pub_context.socket(zmq.PUB)
        self.image_pub.bind(f"tcp://*:{self.ZMQ_IMG_PORT}")
        print(f"[PC][ZMQ] Image PUB bound on tcp://*:{self.ZMQ_IMG_PORT}")


    def _init_gaze_socket(self) -> None:
        # init sub for gaze data
        self.sub_context = zmq.Context()
        self.gaze_req = self.sub_context.socket(zmq.REQ)
        self.gaze_req.connect(f"tcp://{self.hololens_address}:{self.ZMQ_GAZE_PORT}")
        print(f"[PC][ZMQ] Gaze SUB bound on tcp://*:{self.ZMQ_GAZE_PORT}")

    def _close_img(self) -> None:
        self.sub_context.term()
        self.gaze_req.close()

    def _close_gaze(self) -> None:
        self.pub_context.term()
        self.image_pub.close()
