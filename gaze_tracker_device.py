import json
import cv2
from gaze_server import GazeServer
from real_robot.real_robot_env.robot.hardware_cameras import DiscreteCamera
from real_robot.real_robot_env.robot.hardware_devices import DiscreteDevice
from pathlib import Path
from multiprocessing import Process, Event, Pipe
import pickle 

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
        self.reader, self.writer = Pipe(False)
        self.stop_frame_storage_event = Event()
        self.write_process = Process(target=self.__store_frames, args=[self.reader, self.stop_frame_storage_event])
        self.formats = ['.png', '.json']
        
        ### INITIALIZE OBJECT HERE
        self.gaze_server = gaze_server
        self.camera = camera
        self.timestamp = 0

    def _setup_connect(self):
        assert self.camera.connect(), "Failed to connect to camera (maybe plug out and in again?)"
        self.gaze_server.setup_connection()
        self.write_process.start()
        print("[GazeTrackerDevice] Camera connected successfully.")


    
    def close(self) -> bool:
        """
        Closes the connection to the device.
        """
        self.stop_frame_storage_event.set()
        self.gaze_server.close()
        self.write_process.join()
        self.write_process.close()
        self.reader.close()
        self.writer.close()
        return self.camera.close()
    
    def store_last_frame(self, directory: Path, filename: str):
        data = self.get_sensors()
        rgb = data["camera_image"]["rgb"]
        gaze = data["gaze_data"]["gaze"]
        self.writer.send((rgb, 
                          f"{directory}/{data['camera_image']['time']}{self.formats[0]}", 
                          gaze, 
                          f"{directory}/{data['gaze_data']['time']}{self.formats[1]}"))

    @staticmethod
    def __store_frames(reader, stop_frame_storage_event):
        try:
            while not stop_frame_storage_event.is_set():

                if not reader.poll(0.1):
                    continue
                (img, img_path, gaze, gaze_path) = reader.recv()
                cv2.imwrite(
                    img_path,
                    img,
                )
                with open(gaze_path, 'w') as handle:
                    # print(f"[GazeTrackerDevice] Storing gaze data: {gaze}")
                    json.dump(gaze, handle)

        finally:
            reader.close()

    def get_sensors(self) -> dict:
        """
        Returns the latest sensor data as a dictionary.
        The dictionary is in the format:
        {
            'gaze_data': {'gaze': {'x': <int32>, 'y': <int32>}, 'time': <str>},
            'camera_image': {'rgb': <array>, 'time': <str>}
        }
        """
        # Example structure, adapt to your device's data
        camera_data = self.camera.get_sensors()

        if camera_data["rgb"] is None:
            raise RuntimeError("Camera image data is not available. Ensure the camera is connected and capturing images.")
        camera_data['time'] = str(camera_data['time'])

        self.gaze_server.zmq_publish_image(camera_data['time'], camera_data['rgb'])
        gaze = self.gaze_server.zmq_get_gaze()
        gaze_data = {
            'gaze': {'x': gaze['x'], 'y': gaze['y']},
            'time': gaze['time']
        }
        return {
            'gaze_data': gaze_data,
            'camera_image': camera_data,
        }
	  
    @staticmethod
    def get_devices(amount: int = -1, **kwargs) -> list['GazeTrackerDevice']:
        super(GazeTrackerDevice, GazeTrackerDevice).get_devices(
            amount, device_type="GazeTrackerDevice", **kwargs
        )
        ### FIND CONNECTED SENSORS OF YOUR TYPE HERE
        raise NotImplementedError
