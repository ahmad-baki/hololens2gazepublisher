from pathlib import Path
from real_robot.real_robot_env.robot.hardware_devices import AsynchronousDevice, ContinuousDevice, DiscreteDevice
from zmq_server import ZMQServer


class GazeTrackerDevice(DiscreteDevice):

    def __init(self, server: ZMQServer, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.server = server
        self._setup_connect()

    def _setup_connect(self):
        self.server.init_sub_socket()

    
    def close(self) -> bool:
        self.server.close_sub()

    def start_recording(self) -> bool:
        return super().start_recording()
    
    def stop_recording(self) -> bool:
        return super().stop_recording()
    
    def store_recording(self, directory: Path, filename: str | None = None, timestamps: list | None = None) -> bool:
        return super().store_recording(directory, filename, timestamps)
    
    def get_devices(
        amount: int, type: str = "gaze_tracker", **kwargs
    ) -> list["GazeTrackerDevice"]:
        return super().get_devices(amount, type=type, **kwargs)
    
    def delete_recording(self) -> bool:
        return super().delete_recording()