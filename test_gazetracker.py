import sys

sys.path.insert(0, "/home/abaki/Desktop/hololens2gazepublisher/real_robot")
from real_robot.real_robot_env.robot.hardware_depthai_pointcloud import DepthAIPointCloud
from real_robot.real_robot_env.robot.hardware_gazetracker import GazeTracker
from pathlib import Path


from real_robot.real_robot_env.robot.hardware_depthai import DepthAI, DAICameraType
import time



cam = DepthAIPointCloud(
    device_id = "1844301021D9BF1200",
    name = "top_cam",
    height= 512,
    width= 512,
    camera_type= DAICameraType.OAK_D_LITE
)

gaze_device = GazeTracker("")

gaze_device.connect()
while (True):
    gaze_device.store_last_frame(Path("/home/abaki/Desktop/hololens2gazepublisher/data/test"), "")
    # time.sleep(0.1)