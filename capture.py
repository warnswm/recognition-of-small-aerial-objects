import threading
import queue
import time
import cv2
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import messagebox
import mss
import pygetwindow as gw
from process import process_frame


class VideoSource:
    def __init__(self, mode, phone_ip, monitor_id, window_title):
        self.mode = mode
        self.phone_ip = phone_ip
        self.monitor_id = monitor_id
        self.window_title = window_title
        self.cap = None
        self.sct = None

        if self.mode in ["phone", "pc"]:
            if self.mode == "phone":
                url = f'http://{self.phone_ip}:8080/video'
                self.cap = cv2.VideoCapture(url)
            else:
                self.cap = cv2.VideoCapture(0)
        elif self.mode in ["screen", "window"]:
            self.sct = mss.mss()
            if self.mode == "screen":
                try:
                    self.monitor = self.sct.monitors[self.monitor_id]
                except IndexError:
                    self.monitor = self.sct.monitors[0]
            elif self.mode == "window":
                windows = gw.getWindowsWithTitle(self.window_title)
                if not windows:
                    raise ValueError("Окно с заданным названием не найдено!")
                w = windows[0]
                self.monitor = {'left': w.left, 'top': w.top, 'width': w.width, 'height': w.height}

    def get_frame(self):
        if self.mode in ["phone", "pc"]:
            ret, frame = self.cap.read()
            if not ret:
                return None
            return frame
        elif self.mode in ["screen", "window"]:
            screenshot = self.sct.grab(self.monitor)
            frame = np.array(screenshot)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            return frame

    def release(self):
        if self.cap is not None:
            self.cap.release()
        if self.sct is not None:
            self.sct.close()


class VideoProcessor:
    def __init__(self, source: VideoSource, skip_factor:int=2, target_size=(320,320)):
        self.source = source
        self.skip_factor = skip_factor
        self.target_size = target_size

        # очереди длины 1 → всегда самый свежий кадр
        self.cap_queue = queue.Queue(maxsize=1)
        self.proc_queue = queue.Queue(maxsize=1)

        self._stop = threading.Event()
        threading.Thread(target=self._capture_loop, daemon=True).start()
        threading.Thread(target=self._process_loop, daemon=True).start()

    def _capture_loop(self):
        while not self._stop.is_set():
            frame = self.source.get_frame()
            if frame is None:
                continue
            # сохраняем только последний
            if self.cap_queue.full():
                try: self.cap_queue.get_nowait()
                except queue.Empty: pass
            self.cap_queue.put(frame)

    def _process_loop(self):
        frame_count = 0
        while not self._stop.is_set():
            try:
                frame = self.cap_queue.get(timeout=1)
            except queue.Empty:
                continue

            frame_count += 1
            # пропускаем часть кадров
            if frame_count % self.skip_factor != 0:
                continue

            # предобработка: уменьшение разрешения
            small = cv2.resize(frame, self.target_size)
            processed = process_frame(small)
            processed = cv2.resize(processed, frame.shape[1::-1])

            if self.proc_queue.full():
                try: self.proc_queue.get_nowait()
                except queue.Empty: pass
            self.proc_queue.put(processed)

    def read(self, timeout=0):
        """Вернуть последний обработанный кадр или None."""
        try:
            return self.proc_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def stop(self):
        self._stop.set()
        self.source.release()


def start_capture(mode, phone_ip, monitor_id, window_title,
                  frame_width, frame_height):
    root = tk.Tk()
    root.title("Окно захвата")

    video_label = tk.Label(root)
    video_label.pack()

    source = VideoSource(mode, phone_ip, monitor_id, window_title)
    processor = VideoProcessor(source, skip_factor=3, target_size=(320, 320))

    def update_gui():
        # пытаемся получить обработанный кадр без задержки
        frame = processor.read(timeout=0)
        if frame is not None:
            # конвертация и отображение
            cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(cv2image)
            imgtk = ImageTk.PhotoImage(image=img.resize((frame_width, frame_height)))
            video_label.imgtk = imgtk
            video_label.configure(image=imgtk)
        # вызываем снова максимально быстро
        root.after(1, update_gui)

    def on_close():
        processor.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    update_gui()
    root.mainloop()