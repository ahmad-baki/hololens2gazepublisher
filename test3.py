import sys

sys.path.insert(0, "/home/abaki/Desktop/hololens2gazepublisher/real_robot")

from real_robot.real_robot_env.robot.hardware_depthai_pointcloud import DepthAIPointCloud, DAICameraType
from real_robot.real_robot_env.robot.hardware_devices import AsynchronousDevice
import time

cam = AsynchronousDevice[DepthAIPointCloud](
    device_class= DepthAIPointCloud,
    capture_interval=0.1,
    device_id = "1844301071E7AB1200",
    name = "side_cam",
    height= 512,
    width= 512,
    camera_type= DAICameraType.OAK_D_LITE
)

print(f"Connecting to DepthAI PointCloud camera with ID: {cam.device_id} ...")
cam.connect()
print(f"Now recording...")

cam.start_recording()
for i in range(10):
    time.sleep(1)
    print(f"Frame {i+1} captured.")
cam.stop_recording()
cam.delete_recording()
cam.close()