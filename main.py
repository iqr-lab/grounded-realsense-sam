from PySide6.QtWidgets import QApplication
from main_window import MainWindow
import sys
import multiprocessing as mp

import pyrealsense2 as rs
import numpy as np

import cv2


# frame collection method -> place into q
def collect_frame(color_q, depth_q, lock, event=None):
    config = rs.config()
    pipeline = rs.pipeline()
    frames = rs.frame()

    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    pipeline.start(config)

    i = 0

    while not event.is_set():
        lock.acquire()
        try:
            frames = pipeline.wait_for_frames()
            color_frame = np.asanyarray(frames.get_color_frame().get_data())
            depth_image = np.asanyarray(frames.get_depth_frame().get_data())

            depth_colormap = cv2.applyColorMap(
                cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET
            )

            color_q.put(color_frame)
            depth_q.put(depth_colormap)

        finally:
            lock.release()
            i = i + 1

    pipeline.stop()


if __name__ == "__main__":
    # Starting the process method
    processes = []
    event = mp.Event()

    lock = mp.Lock()
    ctx = mp.get_context("spawn")
    color_q = ctx.Queue(maxsize=4)
    depth_q = ctx.Queue(maxsize=4)
    p = mp.Process(
        target=collect_frame,
        args=(
            color_q,
            depth_q,
            lock,
        ),
        kwargs={"event": event},
    )
    p.start()

    processes.append((p, event))

    # Starting Qt Application Window
    app = QApplication(sys.argv)

    window = MainWindow(color_q, depth_q, app)

    window.show()

    app.exec()

    for _, event in processes:
        event.set()

    # Now actually wait for them to shut down
    for p, _ in processes:
        print("Realsense Streams Closing...")
        p.join()
        print("Realsense Streams Closed")

    print("All processes cleaned up. Exited successfully.")