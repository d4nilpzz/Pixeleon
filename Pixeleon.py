import os
import tkinter as tk
from tkinter import filedialog, colorchooser
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw


class PixeleonApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pixeleon")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        icon_path = "resources/Pixeleon.ico"
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)

        # Key bindings
        self.root.bind("<Control-s>", lambda event: self.save_image())
        self.root.bind("<Control-z>", lambda event: self.undo())
        self.root.bind("<Control-y>", lambda event: self.redo())

        self.max_display_size = 512
        self.current_color = "#000000"
        self.tool = "brush"
        self.brush_size = 1
        self.history = []
        self.redo_stack = []

        self.image = Image.new("RGB", (32, 32), "white")
        self.draw = ImageDraw.Draw(self.image)

        self.create_menu()
        self.create_main_layout()
        self.refresh()
        self.save_history()

        self.is_drawing = False

    def create_menu(self):
        menu = tk.Menu(self.root)

        file_menu = tk.Menu(menu, tearoff=0)
        file_menu.add_command(label="New", command=self.new_image)
        file_menu.add_command(label="Open", command=self.load_image)
        file_menu.add_command(label="Save", command=self.save_image)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menu.add_cascade(label="File", menu=file_menu)

        tools_menu = tk.Menu(menu, tearoff=0)
        tools_menu.add_command(label="Change Global Color", command=self.change_global_color)
        menu.add_cascade(label="Tools", menu=tools_menu)

        self.root.config(menu=menu)

    def create_main_layout(self):
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(self.main_frame, bg="#1f1f1f", bd=0, highlightthickness=0)
        self.canvas.pack(side="left", expand=True, fill="both", padx=10, pady=10)
        self.canvas.bind("<Button-1>", self.on_draw_start)
        self.canvas.bind("<B1-Motion>", self.on_draw)
        self.canvas.bind("<ButtonRelease-1>", self.on_draw_end)

        self.sidebar = ctk.CTkFrame(self.main_frame, width=200)
        self.sidebar.pack(side="right", fill="y", padx=10, pady=10)

        brush_frame = ctk.CTkFrame(self.sidebar)
        brush_frame.pack(pady=5)
        brush_label2 = ctk.CTkLabel(brush_frame, text="Brush Size (px):")
        brush_label2.pack(side="left")
        self.brush_slider = tk.Spinbox(brush_frame, from_=1, to=10, width=5, command=self.update_brush_size)
        self.brush_slider.delete(0, "end")
        self.brush_slider.insert(0, "1")
        self.brush_slider.pack(side="left", padx=(5, 0))

        tools = [
            ("Brush", lambda: self.set_tool("brush")),
            ("Eraser", lambda: self.set_tool("eraser")),
            ("Pick Color", lambda: self.set_tool("picker")),
            ("Select Color", self.choose_color)
        ]
        for label, cmd in tools:
            btn = ctk.CTkButton(self.sidebar, text=label, command=cmd)
            btn.pack(pady=4, fill="x")

        undo_redo_frame = ctk.CTkFrame(self.sidebar)
        undo_redo_frame.pack(pady=10)

        btn_undo = ctk.CTkButton(undo_redo_frame, text="Undo", width=70, command=self.undo)
        btn_undo.pack(side="left", padx=(0, 5))

        btn_redo = ctk.CTkButton(undo_redo_frame, text="Redo", width=70, command=self.redo)
        btn_redo.pack(side="left")

    def update_brush_size(self):
        try:
            self.brush_size = int(self.brush_slider.get())
        except ValueError:
            self.brush_size = 1

    def set_tool(self, tool_name):
        self.tool = tool_name

    def choose_color(self):
        color = colorchooser.askcolor(initialcolor=self.current_color)[1]
        if color:
            self.current_color = color

    def on_draw_start(self, event):
        self.is_drawing = True
        self.update_brush_size()
        self.draw_point(event)

    def on_draw(self, event):
        if self.is_drawing:
            self.update_brush_size()
            self.draw_point(event)

    def on_draw_end(self, event):
        if self.is_drawing:
            self.is_drawing = False
            self.save_history()

    def draw_point(self, event):
        if not hasattr(self, 'tk_image'):
            return
        x = int(event.x / self.scale)
        y = int(event.y / self.scale)
        if x < 0 or y < 0 or x >= self.image.width or y >= self.image.height:
            return

        size = self.brush_size
        box = [x - size // 2, y - size // 2, x + size // 2 + 1, y + size // 2 + 1]

        if self.tool == "brush":
            for i in range(box[0], box[2]):
                for j in range(box[1], box[3]):
                    if 0 <= i < self.image.width and 0 <= j < self.image.height:
                        self.draw.point((i, j), fill=self.current_color)
        elif self.tool == "eraser":
            for i in range(box[0], box[2]):
                for j in range(box[1], box[3]):
                    if 0 <= i < self.image.width and 0 <= j < self.image.height:
                        self.draw.point((i, j), fill="white")
        elif self.tool == "picker":
            self.current_color = '#%02x%02x%02x' % self.image.getpixel((x, y))

        self.refresh()

    def refresh(self):
        w, h = self.image.size
        ratio = min(self.max_display_size / w, self.max_display_size / h)
        self.scale = ratio
        canvas_w = int(w * self.scale)
        canvas_h = int(h * self.scale)

        resized = self.image.resize((canvas_w, canvas_h), Image.NEAREST)
        self.tk_image = ImageTk.PhotoImage(resized)
        self.canvas.config(width=canvas_w, height=canvas_h)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)

    def new_image(self):
        self.image = Image.new("RGB", (32, 32), "white")
        self.draw = ImageDraw.Draw(self.image)
        self.refresh()
        self.history.clear()
        self.redo_stack.clear()
        self.save_history()

    def save_image(self):
        file = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[
            ("PNG", "*.png"),
            ("JPEG", "*.jpg;*.jpeg"),
            ("ICO", "*.ico"),
            ("BMP", "*.bmp"),
            ("GIF", "*.gif"),
            ("All files", "*.*")
        ])
        if file:
            ext = os.path.splitext(file)[1].lower()
            format_map = {
                ".png": "PNG",
                ".jpg": "JPEG",
                ".jpeg": "JPEG",
                ".ico": "ICO",
                ".bmp": "BMP",
                ".gif": "GIF"
            }
            fmt = format_map.get(ext, "PNG")

            if fmt == "ICO":
                sizes = [(16, 16), (32, 32), (48, 48)]
                icons = []
                for size in sizes:
                    icon_img = self.image.resize(size, Image.NEAREST)
                    icons.append(icon_img)
                icons[0].save(file, format="ICO", sizes=[size for size in sizes])
            else:
                self.image.save(file, format=fmt)

    def load_image(self):
        file = filedialog.askopenfilename(filetypes=[
            ("Image files", "*.png;*.jpg;*.jpeg;*.ico;*.bmp;*.gif"),
            ("All files", "*.*")
        ])
        if file:
            self.image = Image.open(file).convert("RGB")
            self.draw = ImageDraw.Draw(self.image)
            self.refresh()
            self.history.clear()
            self.redo_stack.clear()
            self.save_history()

    def save_history(self):
        self.history.append(self.image.copy())
        if len(self.history) > 50:
            self.history.pop(0)
        self.redo_stack.clear()

    def undo(self):
        if len(self.history) > 1:
            self.redo_stack.append(self.image.copy())
            self.history.pop()
            self.image = self.history[-1].copy()
            self.draw = ImageDraw.Draw(self.image)
            self.refresh()

    def redo(self):
        if self.redo_stack:
            self.history.append(self.image.copy())
            self.image = self.redo_stack.pop()
            self.draw = ImageDraw.Draw(self.image)
            self.refresh()

    def change_global_color(self):
        color = colorchooser.askcolor(title="Select Target Color")[1]
        if color:
            self.save_history()
            target_hue = self.rgb_to_hsv(*self.hex_to_rgb(color))[0]
            pixels = self.image.load()
            for y in range(self.image.height):
                for x in range(self.image.width):
                    r, g, b = pixels[x, y]
                    h, s, v = self.rgb_to_hsv(r, g, b)
                    new_r, new_g, new_b = self.hsv_to_rgb(target_hue, s, v)
                    pixels[x, y] = (int(new_r), int(new_g), int(new_b))
            self.refresh()

    def hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def rgb_to_hsv(self, r, g, b):
        r, g, b = r/255, g/255, b/255
        mx = max(r, g, b)
        mn = min(r, g, b)
        diff = mx - mn
        if diff == 0:
            h = 0
        elif mx == r:
            h = (60 * ((g - b) / diff) + 360) % 360
        elif mx == g:
            h = (60 * ((b - r) / diff) + 120) % 360
        else:
            h = (60 * ((r - g) / diff) + 240) % 360
        s = 0 if mx == 0 else diff / mx
        v = mx
        return h, s, v

    def hsv_to_rgb(self, h, s, v):
        c = v * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = v - c
        if h < 60:
            rp, gp, bp = c, x, 0
        elif h < 120:
            rp, gp, bp = x, c, 0
        elif h < 180:
            rp, gp, bp = 0, c, x
        elif h < 240:
            rp, gp, bp = 0, x, c
        elif h < 300:
            rp, gp, bp = x, 0, c
        else:
            rp, gp, bp = c, 0, x
        r, g, b = (rp + m) * 255, (gp + m) * 255, (bp + m) * 255
        return r, g, b


if __name__ == "__main__":
    root = ctk.CTk()
    app = PixeleonApp(root)
    root.mainloop()
