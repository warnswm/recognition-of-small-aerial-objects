import os
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
import mss
import pygetwindow as gw
from PIL import ImageGrab, Image, ImageTk
import cv2
import numpy as np
from moviepy import VideoFileClip

from capture import start_capture
from process import process_frame

try:
    from tkinterdnd2 import DND_FILES
    dnd_available = True
except ImportError:
    dnd_available = False

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class VideoProcessingAppToplevel(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Проверка видео через модель")
        self.geometry("500x300")
        self.video_path = None
        self.cap = None
        self.out = None
        self.output_file_name = None
        self.current_imgtk = None
        self.create_widgets()

    def create_widgets(self):
        self.info_label = ctk.CTkLabel(
            self,
            text="Выберите видео для проверки через модель",
            font=("Helvetica", 16)
        )
        self.info_label.pack(pady=10)

        self.select_button = ctk.CTkButton(
            self,
            text="Выбрать видео",
            command=self.select_file
        )
        self.select_button.pack(pady=5)

        self.live_button = ctk.CTkButton(
            self,
            text="Просмотр и запись видео с моделью",
            command=self.start_video_processing
        )
        self.live_button.pack(pady=5)

        self.status_label = ctk.CTkLabel(self, text="")
        self.status_label.pack(pady=5)

        self.video_label = ctk.CTkLabel(self, text="")
        self.video_label.pack(pady=10, fill="both", expand=True, anchor="nw")

    def select_file(self):
        file_path = filedialog.askopenfilename(
            title="Выберите видеофайл",
            filetypes=[("Видео файлы", "*.mp4 *.avi *.mov *.mkv")]
        )
        if file_path:
            self.video_path = file_path
            self.status_label.configure(text=f"Выбрано видео: {os.path.basename(file_path)}")
            self.change_window_size(file_path)

    def change_window_size(self, video_path):
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        else:
            video_width, video_height = 640, 480
        cap.release()
        new_width = max(video_width, 500)
        new_height = video_height + 150
        self.geometry(f"{new_width}x{new_height}")

    def start_video_processing(self, mode="normal"):
        if not self.video_path:
            messagebox.showerror("Ошибка", "Видео не выбрано!")
            return

        if self.cap:
            self.cap.release()
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            messagebox.showerror("Ошибка", "Не удалось открыть видеофайл.")
            return

        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self.cap.get(cv2.CAP_PROP_FPS)

        downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
        base_name = os.path.basename(self.video_path)
        self.output_file_name = os.path.join(downloads_path, f"processed_{base_name}")

        fourcc = cv2.VideoWriter.fourcc(*'mp4v')
        self.out = cv2.VideoWriter(self.output_file_name, fourcc, fps, (width, height))

        self.status_label.configure(text="Воспроизведение и запись видео с моделью...")
        self.process_video_live(mode)

    def process_video_live(self, mode="normal"):
        ret, frame = self.cap.read()
        if ret:
            processed_frame = process_frame(frame, mode=mode)
            self.out.write(processed_frame)  # запись кадра
            rgb_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb_frame)
            self.current_imgtk = ImageTk.PhotoImage(image=image)
            self.video_label.configure(image=self.current_imgtk)
            self.after(30, self.process_video_live, mode)
        else:
            self.cap.release()
            if self.out:
                self.out.release()
            self.status_label.configure(text=f"Видео завершено. Сохранено: {self.output_file_name}")
            messagebox.showinfo("Готово", f"Обработанное видео сохранено:\n{self.output_file_name}")


def start_interface():
    root = ctk.CTk()
    root.title("Выбор источника съёмки")
    root.geometry("600x500")

    root.clipboard_image = None
    mode_var = tk.StringVar(value="phone")

    label_select = ctk.CTkLabel(root, text="Выберите источник съёмки:", font=("Helvetica", 16))
    label_select.grid(row=0, column=0, columnspan=2, pady=10, padx=20)

    radio_phone = ctk.CTkRadioButton(root, text="Съемка с телефона", variable=mode_var, value="phone")
    radio_phone.grid(row=1, column=0, sticky="w", padx=20, pady=5)
    radio_pc = ctk.CTkRadioButton(root, text="Съемка с ПК (веб-камера)", variable=mode_var, value="pc")
    radio_pc.grid(row=2, column=0, sticky="w", padx=20, pady=5)
    radio_screen = ctk.CTkRadioButton(root, text="Трансляция экрана", variable=mode_var, value="screen")
    radio_screen.grid(row=3, column=0, sticky="w", padx=20, pady=5)
    radio_window = ctk.CTkRadioButton(root, text="Захват окна", variable=mode_var, value="window")
    radio_window.grid(row=4, column=0, sticky="w", padx=20, pady=5)
    radio_aerial = ctk.CTkRadioButton(root, text="Картинка с воздуха", variable=mode_var, value="aerial")
    radio_aerial.grid(row=5, column=0, sticky="w", padx=20, pady=5)

    phone_frame = ctk.CTkFrame(root)
    phone_frame.grid(row=1, column=1, padx=20, pady=5, sticky="w")
    label_ip = ctk.CTkLabel(phone_frame, text="IP телефона:")
    label_ip.pack(side=tk.LEFT, padx=5)
    ip_entry = ctk.CTkEntry(phone_frame, width=150)
    ip_entry.insert(0, "192.168.1.38")
    ip_entry.pack(side=tk.LEFT, padx=5)

    screen_frame = ctk.CTkFrame(root)
    screen_frame.grid(row=3, column=1, padx=20, pady=5, sticky="w")
    label_monitor = ctk.CTkLabel(screen_frame, text="Выберите монитор:")
    label_monitor.pack(side=tk.LEFT, padx=5)
    try:
        with mss.mss() as sct:
            num_monitors = len(sct.monitors)
            monitor_options = ["Full Screen (0)"]
            for i in range(1, num_monitors):
                monitor_options.append(f"Monitor {i}")
    except Exception:
        monitor_options = ["Monitor 1"]
    monitor_var = tk.StringVar(value=monitor_options[0])
    monitor_menu = ctk.CTkOptionMenu(screen_frame, variable=monitor_var, values=monitor_options)
    monitor_menu.pack(side=tk.LEFT, padx=5)

    window_frame = ctk.CTkFrame(root)
    window_frame.grid(row=4, column=1, padx=20, pady=5, sticky="w")
    label_window = ctk.CTkLabel(window_frame, text="Выберите окно:")
    label_window.pack(side=tk.LEFT, padx=5)
    try:
        window_titles = [w.title for w in gw.getAllWindows() if w.title.strip() != ""]
        if not window_titles:
            window_titles = ["Нет доступных окон"]
    except Exception:
        window_titles = ["Ошибка получения окон"]
    window_var = tk.StringVar(value=window_titles[0])
    window_menu = ctk.CTkOptionMenu(window_frame, variable=window_var, values=window_titles)
    window_menu.pack(side=tk.LEFT, padx=5)

    aerial_frame = ctk.CTkFrame(root)
    aerial_frame.grid(row=5, column=1, padx=20, pady=5, sticky="w")
    label_aerial = ctk.CTkLabel(aerial_frame, text="Нажмите Ctrl+V для вставки изображения")
    label_aerial.pack(side=tk.TOP, pady=5)
    preview_label = ctk.CTkLabel(aerial_frame, text="Превью изображения")
    preview_label.pack(side=tk.TOP, pady=5)

    frame_size_frame = ctk.CTkFrame(root)
    frame_size_frame.grid(row=6, column=0, columnspan=2, pady=10, padx=20)
    label_frame_width = ctk.CTkLabel(frame_size_frame, text="Ширина рамки:")
    label_frame_width.pack(side=tk.LEFT, padx=5)
    frame_width_entry = ctk.CTkEntry(frame_size_frame, width=50)
    frame_width_entry.insert(0, "1280")
    frame_width_entry.pack(side=tk.LEFT, padx=5)
    label_frame_height = ctk.CTkLabel(frame_size_frame, text="Высота рамки:")
    label_frame_height.pack(side=tk.LEFT, padx=5)
    frame_height_entry = ctk.CTkEntry(frame_size_frame, width=50)
    frame_height_entry.insert(0, "960")
    frame_height_entry.pack(side=tk.LEFT, padx=5)

    def update_fields(*args):
        current_mode = mode_var.get()
        if current_mode == "phone":
            phone_frame.grid()
        else:
            phone_frame.grid_remove()
        if current_mode == "screen":
            screen_frame.grid()
        else:
            screen_frame.grid_remove()
        if current_mode == "window":
            window_frame.grid()
        else:
            window_frame.grid_remove()
        if current_mode == "aerial":
            aerial_frame.grid()
        else:
            aerial_frame.grid_remove()

    mode_var.trace("w", update_fields)
    update_fields()

    def on_paste(event):
        pasted = ImageGrab.grabclipboard()
        if pasted is not None:
            root.clipboard_image = pasted
            pil_image = pasted.convert("RGB")
            pil_image.thumbnail((200, 200))
            tk_image = ImageTk.PhotoImage(pil_image)
            preview_label.configure(image=tk_image, text="")
            preview_label.image = tk_image
            messagebox.showinfo("Информация", "Изображение успешно вставлено!")
        else:
            messagebox.showerror("Ошибка", "В буфере обмена не найдено изображения!")

    root.bind("<Control-v>", on_paste)

    def on_start():
        mode = mode_var.get()
        phone_ip = ip_entry.get().strip()
        monitor_id = 0

        if mode == "screen":
            selection = monitor_var.get()
            if selection.startswith("Full Screen"):
                monitor_id = 0
            else:
                try:
                    monitor_id = int(selection.split()[1])
                except Exception:
                    monitor_id = 0

        window_title = window_var.get() if mode == "window" else ""

        try:
            frame_width = int(frame_width_entry.get().strip())
            frame_height = int(frame_height_entry.get().strip())
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректные числовые значения для размера окна!")
            return

        if mode == "phone" and not phone_ip:
            messagebox.showerror("Ошибка", "Введите IP телефона!")
            return

        if mode not in ["aerial"]:
            root.destroy()

        if mode == "aerial":
            if not hasattr(root, 'clipboard_image') or root.clipboard_image is None:
                messagebox.showerror("Ошибка",
                                     "В буфере обмена нет изображения! Скопируйте изображение и нажмите Ctrl+V.")
                return
            pil_image = root.clipboard_image.convert("RGB")
            cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            cv_image = cv2.resize(cv_image, (frame_width, frame_height))
            processed_image = process_frame(cv_image, mode="aerial")
            processed_rgb = cv2.cvtColor(processed_image, cv2.COLOR_BGR2RGB)
            pil_processed = Image.fromarray(processed_rgb)
            tk_processed = ImageTk.PhotoImage(pil_processed)
            preview_label.configure(image=tk_processed)
            preview_label.image = tk_processed
        else:
            start_capture(mode, phone_ip, monitor_id, window_title, frame_width, frame_height)
            start_interface()

    start_button = ctk.CTkButton(root, text="Start", command=on_start, width=200)
    start_button.grid(row=7, column=0, columnspan=2, pady=20)

    def open_video_editor():
        VideoProcessingAppToplevel(root)

    video_editor_button = ctk.CTkButton(root, text="Загрузить видео", command=open_video_editor, width=200)
    video_editor_button.grid(row=8, column=0, columnspan=2, pady=10)

    root.mainloop()

if __name__ == "__main__":
    start_interface()
