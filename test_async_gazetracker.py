import sys

sys.path.insert(0, "/home/abaki/Desktop/hololens2gazepublisher/real_robot")

from gaze_tracker_device import GazeTrackerDevice
from real_robot.real_robot_env.robot.hardware_devices import AsynchronousDevice
import time
from pathlib import Path

gaze_device = AsynchronousDevice[GazeTrackerDevice](
    device_class=GazeTrackerDevice,
    capture_interval=0,
    device_id=""
)

gaze_device.connect()
gaze_device.start_recording()
print("Recording started...")
timestamps = []
for i in range(10):
    timestamps.append(time.time())
    time.sleep(1)
    print(f"Captured frame {i+1} at {timestamps[-1]}")
gaze_device.stop_recording()
print("Recording stopped.")
gaze_device.store_recording(
    directory=Path("/home/abaki/Desktop/hololens2gazepublisher/data/test"),
    timestamps=timestamps
)
print("Recording stored.")
gaze_device.close()