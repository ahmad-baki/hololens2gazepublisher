import sys

sys.path.insert(0, "/home/abaki/Desktop/hololens2gazepublisher/real_robot")

from GazeTrackerDevice import GazeTrackerDevice
from real_robot.real_robot_env.robot.hardware_depthai import DepthAI, DAICameraType
import time



cam = DepthAI(
    device_id = "1844301021D9BF1200",
    name = "top_cam",
    height= 512,
    width= 512,
    camera_type= DAICameraType.OAK_D_LITE
)

gaze_device = GazeTrackerDevice("", camera=cam)

gaze_device.connect()

counter = 0

while (True):
    gaze_device.store_last_frame("/home/abaki/Desktop/hololens2gazepublisher/data/test", f"{counter}")
    print(f"storing frame: {counter}")
    time.sleep(0.1)