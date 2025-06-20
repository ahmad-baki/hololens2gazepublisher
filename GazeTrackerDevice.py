import cv2
from gaze_server import GazeServer
from real_robot.real_robot_env.robot.hardware_cameras import DiscreteCamera
from real_robot.real_robot_env.robot.hardware_devices import DiscreteDevice
from pathlib import Path
from multiprocessing import Pipe

class GazeTrackerDevice(DiscreteDevice):

    def __init__(
        self,
        device_id,
        camera: DiscreteCamera,
        name=None,
        start_frame_latency=0,
        gaze_server=GazeServer()
    ):
        super().__init__(
            device_id,
            name if name else f"GazeTrackerDevice_{device_id}",
            start_frame_latency
        )
        self.writer = Pipe(False)
        self.formats = ['.png', '.json'] # e.g. ['.png']
        # if your device stores several files per frame, make sure the
        # suffix of each output file is distinct and considered in the
        # formats array: e.g. self.formats = ['_img.png', '_depth.png']
        
        ### INITIALIZE OBJECT HERE
        self.gaze_server = gaze_server
        self.camera = camera
        self.step = 0

    def _setup_connect(self):
        self.gaze_server.setup_connection()
        self.camera.connect()


    
    def close(self) -> bool:
        """
        Closes the connection to the device.
        """
        self.gaze_server.close()
        return self.camera.close()
    
    def store_last_frame(self, directory: Path, filename: str):
        data = self.get_sensors()
        rgb = data["camera_image"]["rgb"]
        self.writer.send((rgb, str(directory / f"{filename}") + self.formats[0])) # type: ignore

        gaze = data["gaze_data"]
        self.writer.send((gaze, str(directory / f"{filename}") + self.formats[1])) # type: ignore
        
    
    def get_sensors(self) -> dict:
        """
        Returns the latest sensor data as a dictionary.
        """
        # Example structure, adapt to your device's data
        camera_data = self.camera.get_sensors()
        camera_image: cv2.typing.MatLike = camera_data.get('camera_image', None) # type: ignore
        if camera_image is None:
            raise RuntimeError("Camera image data is not available. Ensure the camera is connected and capturing images.")

        self.gaze_server.zmq_image_publisher(self.step, camera_image)
        self.step += 1
        camera_data_new = { 'camera_image': camera_data, 'step': self.step }
        return {
            'gaze_data': self.gaze_server.zmq_gaze_subscriber(),
            'camera_image': camera_data_new,
        }
	  
    @staticmethod
    def get_devices(amount: int = -1, **kwargs) -> list['GazeTrackerDevice']:
        super(GazeTrackerDevice, GazeTrackerDevice).get_devices(
            amount, device_type="GazeTrackerDevice", **kwargs
        )
        ### FIND CONNECTED SENSORS OF YOUR TYPE HERE
        raise NotImplementedError
