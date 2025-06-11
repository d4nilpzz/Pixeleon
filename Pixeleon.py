import json
import os
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, colorchooser
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw, ImageFilter
from colorsys import rgb_to_hsv as cs_rgb_to_hsv, hsv_to_rgb as cs_hsv_to_rgb
import webbrowser

from tkcolorpicker import askcolor

DEFAULT_CONFIG = {
    "keybinds": {
        "load": "Ctrl+O",
        "save": "Ctrl+S",
        "undo": "Ctrl+Z",
        "redo": "Ctrl+Y"
    }
}

class PixeleonApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pixeleon")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.config_path = "config.json"
        self.config = self.load_or_create_config()

        icon_path = "icon.ico"
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)

        def parse_binding(s):
            s = s.lower()
            s = s.replace("ctrl", "Control")
            s = s.replace("+", "-")
            return f"<{s}>"

        self.root.bind(parse_binding(self.config['keybinds']['save']), lambda event: self.save_image())
        self.root.bind(parse_binding(self.config['keybinds']['undo']), lambda event: self.undo())
        self.root.bind(parse_binding(self.config['keybinds']['redo']), lambda event: self.redo())
        self.root.bind(parse_binding(self.config['keybinds']['load']), lambda event: self.load_image())

        self.max_display_size = 512
        self.current_color = "#000000"
        self.tool = "brush"
        self.brush_size = 1
        self.history = []
        self.redo_stack = []

        self.image = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.image)

        self.create_menu()
        self.create_main_layout()
        self.refresh()
        self.save_history()

        self.is_drawing = False

    def load_or_create_config(self):
        if not os.path.exists(self.config_path):
            with open(self.config_path, "w") as f:
                json.dump(DEFAULT_CONFIG, f, indent=4)
            return DEFAULT_CONFIG.copy()
        else:
            with open(self.config_path, "r") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    # Si hay un error de parseo, volver a crear con default
                    with open(self.config_path, "w") as fw:
                        json.dump(DEFAULT_CONFIG, fw, indent=4)
                    return DEFAULT_CONFIG.copy()

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
        tools_menu.add_command(label="Flip x", command=self.flip_x)
        tools_menu.add_command(label="Flip y", command=self.flip_y)
        tools_menu.add_command(label="Rotate 90°", command=self.rotate_90)
        tools_menu.add_command(label="Blur", command=self.apply_blur)
        menu.add_cascade(label="Tools", menu=tools_menu)

        module_menu = tk.Menu(menu, tearoff=0)
        module_menu.add_command(label="Change Global Color", command=self.change_global_color)
        menu.add_cascade(label="Module", menu=module_menu)

        help_menu = tk.Menu(menu, tearoff=0)
        help_menu.add_command(label="Discord", command=self.discord_link)
        help_menu.add_command(label="Open Folder", command=self.open_current_directory)
        menu.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menu)

    def discord_link(self):
        webbrowser.open("https://discord.gg/RqTdkE9aYW")

    def flip_x(self):
        if self.image:
            self.save_history()
            self.image = self.image.transpose(Image.FLIP_LEFT_RIGHT)
            self.refresh()

    def flip_y(self):
        if self.image:
            self.save_history()
            self.image = self.image.transpose(Image.FLIP_TOP_BOTTOM)
            self.refresh()

    def rotate_90(self):
        if self.image:
            self.save_history()
            self.image = self.image.rotate(-90, expand=True)
            self.refresh()

    def apply_blur(self):
        if self.image:
            self.save_history()
            self.image = self.image.filter(ImageFilter.BLUR)
            self.refresh()

    def open_current_directory(self):
        path = os.path.abspath(os.getcwd())
        if sys.platform == "win32":
            subprocess.Popen(f'explorer "{path}"')
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def create_main_layout(self):
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(self.main_frame, bg="#1f1f1f", bd=0, highlightthickness=0)
        self.canvas.pack(side="left", expand=True, fill="both", padx=10, pady=10)
        self.canvas.bind("<Button-1>", self.on_draw_start)
        self.canvas.bind("<B1-Motion>", self.on_draw)
        self.canvas.bind("<ButtonRelease-1>", self.on_draw_end)

        self.sidebar = ctk.CTkFrame(self.main_frame, width=220)
        self.sidebar.pack(side="right", fill="y", padx=10, pady=10)

        brush_frame = ctk.CTkFrame(self.sidebar)
        brush_frame.pack(pady=5)

        brush_label2 = ctk.CTkLabel(brush_frame, text="Brush Size     ", bg_color="#333333")
        brush_label2.pack(side="left")

        brush_sizes = ["1", "2", "4", "6", "8", "10"]
        self.brush_size_combobox = ctk.CTkComboBox(
            brush_frame,
            values=brush_sizes,
            fg_color="#2b2b2b",
            bg_color="#333333",
            button_color="#2b2b2b",
            border_color="#2b2b2b",
            width=60,
            command=lambda value: self.set_brush_size(value)
        )
        self.brush_size_combobox.set("1")
        self.brush_size_combobox.pack(side="left")

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

        btn_undo = ctk.CTkButton(undo_redo_frame, text="Undo", width=70, command=self.undo, bg_color="#333333")
        btn_undo.pack(side="left")

        ctk.CTkFrame(undo_redo_frame, width=10, height=30, bg_color="#333333").pack(side="left")

        btn_redo = ctk.CTkButton(undo_redo_frame, text="Redo", width=70, command=self.redo, bg_color="#333333")
        btn_redo.pack(side="left")

    def update_brush_size(self):
        try:
            self.brush_size = int(self.brush_size)
        except Exception:
            self.brush_size = 1

    def set_brush_size(self, value):
        try:
            self.brush_size = int(value)
        except Exception:
            pass

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
                        self.draw.point((i, j), fill=(0, 0, 0, 0))
        elif self.tool == "picker":
            r, g, b, a = self.image.getpixel((x, y))
            self.current_color = '#%02x%02x%02x' % (r, g, b)

        self.refresh()

    def select_color_with_alpha(parent):
        color = askcolor(with_alpha=True, parent=parent)
        if color and color[1]:
            return color[1]  # Retorna color en formato #RRGGBBAA
        return None

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
        self.image = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
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
                icons = [self.image.resize(size, Image.NEAREST) for size in sizes]
                icons[0].save(file, format="ICO", sizes=sizes)
            else:
                self.image.save(file, fmt)

    def load_image(self):
        file = filedialog.askopenfilename(filetypes=[
            ("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.ico"),
            ("All files", "*.*")
        ])
        if file:
            loaded = Image.open(file).convert("RGBA")
            self.image = loaded
            self.draw = ImageDraw.Draw(self.image)
            self.history.clear()
            self.redo_stack.clear()
            self.save_history()
            self.refresh()

    def save_history(self):
        if self.image:
            if self.history and self.history[-1] == self.image.tobytes():
                return
            self.history.append(self.image.copy())
            if len(self.history) > 50:
                self.history.pop(0)
            self.redo_stack.clear()

    def undo(self):
        if len(self.history) > 1:
            last = self.history.pop()
            self.redo_stack.append(last)
            self.image = self.history[-1].copy()
            self.draw = ImageDraw.Draw(self.image)
            self.refresh()

    def redo(self):
        if self.redo_stack:
            redo_img = self.redo_stack.pop()
            self.history.append(redo_img)
            self.image = redo_img.copy()
            self.draw = ImageDraw.Draw(self.image)
            self.refresh()

    def hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def rgb_to_hsv(self, r, g, b):
        r_norm, g_norm, b_norm = r/255.0, g/255.0, b/255.0
        h, s, v = cs_rgb_to_hsv(r_norm, g_norm, b_norm)
        return h, s, v

    def hsv_to_rgb(self, h, s, v):
        r, g, b = cs_hsv_to_rgb(h, s, v)
        return int(r*255), int(g*255), int(b*255)

    def change_global_color(self):
        color = colorchooser.askcolor(title="Select Target Color")[1]
        if color and self.image:
            self.save_history()
            target_hue = self.rgb_to_hsv(*self.hex_to_rgb(color))[0]
            pixels = self.image.load()
            for y in range(self.image.height):
                for x in range(self.image.width):
                    px = pixels[x, y]
                    if len(px) == 4:
                        r, g, b, a = px
                        h, s, v = self.rgb_to_hsv(r, g, b)
                        new_r, new_g, new_b = self.hsv_to_rgb(target_hue, s, v)
                        pixels[x, y] = (new_r, new_g, new_b, a)
                    else:
                        r, g, b = px
                        h, s, v = self.rgb_to_hsv(r, g, b)
                        new_r, new_g, new_b = self.hsv_to_rgb(target_hue, s, v)
                        pixels[x, y] = (new_r, new_g, new_b)
            self.refresh()

    @staticmethod
    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip('#')
        lv = len(hex_color)
        return tuple(int(hex_color[i:i+lv//3], 16) for i in range(0, lv, lv//3))


if __name__ == "__main__":
    root = ctk.CTk()
    root.resizable(False, False)
    app = PixeleonApp(root)
    root.mainloop()
