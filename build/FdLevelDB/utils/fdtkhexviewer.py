import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog, scrolledtext
import os

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

class TextViewer(ttk.Frame):
    def __init__(self, data):
        root = tk.Tk()

        self.root = root
        self.root.title("FDPy Text Viewer")
        self.file_path = ''
        self.data = data

        # grid layout for sticky
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)        

        # 스크롤된 텍스트 영역 생성
        self.text_area = scrolledtext.ScrolledText(root, wrap=tk.WORD)
        self.text_area.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        # 폰트 설정
        self.text_area.config(font=('Consolas', 11))
        
        # 프로그램 아이콘
        try:
            self.root.tk.call('wm', 'iconphoto', root._w,
                    tk.PhotoImage(file=PROJECT_DIR + '/icon.png'))
        except:
            pass
    
    def display_text(self):
        data = str(self.data).replace(",", ",\n")
        data = str(data).replace("{", "{\n")
        data = str(data).replace("}", "\n}")
        self.text_area.insert(tk.END, data)

class HexViewer(ttk.Frame):
    ASCII = 0
    UTF8 = 1
    UTF16 = 2
    def __init__(self, root=None, data=None, useMenu=False):
        if root is None:
            root = tk.Tk()

        self.root = root
        self.root.title("FDPy Hex Viewer")
        self.encode_mode = self.ASCII
        self.file_path = ''
        self.data = data

        # grid layout for sticky
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)

        # Menubar
        self.menu = tk.Menu(root)
        self.root.config(menu=self.menu)
        if useMenu:
            self.file_menu = tk.Menu(self.menu)
            self.menu.add_cascade(label="File", menu=self.file_menu)
            self.file_menu.add_command(label="Open", command=self.open_file)
            self.file_menu.add_command(label="Exit", command=root.quit)

        self.tool_menu = tk.Menu(self.menu)
        self.menu.add_cascade(label="Tools", menu=self.tool_menu)

        # radio button for Text Encoding
        radio_var = tk.IntVar()
        radio_var.set(self.ASCII)  # 기본값 설정

        self.tool_menu.add_radiobutton(label="Encode ASCII", variable=radio_var, value=self.ASCII, command=lambda c=self.ASCII: self.encode_text(c))
        self.tool_menu.add_radiobutton(label="Encode UTF-8", variable=radio_var, value=self.UTF8, command=lambda c=self.UTF8: self.encode_text(c))
        self.tool_menu.add_radiobutton(label="Encode UTF-16", variable=radio_var, value=self.UTF16, command=lambda c=self.UTF8: self.encode_text(c))

        self.view_menu = tk.Menu(self.menu)
        self.menu.add_cascade(label="View", menu=self.view_menu)
        self.view_menu.add_command(label="on Text Viewer", command=self.on_view_data)

        # 스크롤된 텍스트 영역 생성
        self.text_area = scrolledtext.ScrolledText(root, wrap=tk.NONE)
        # self.text_area.pack(expand=True, fill='both')
        self.text_area.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        # 폰트 설정
        self.text_area.config(font=('Consolas', 11))

        # 스크롤된 텍스트 영역 - 미리보기 (가로폭 지정)
        self.text_area_preview = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=120)
        self.text_area_preview.grid(row=0, column=1, sticky=(tk.N, tk.S, tk.E, tk.W))
        # 폰트 설정
        self.text_area_preview.configure(font=('Consolas', 11))

        # 프로그램 아이콘
        try:
            self.root.tk.call('wm', 'iconphoto', root._w,
                    tk.PhotoImage(file=PROJECT_DIR + '/icon.png'))
        except:
            pass

    def open_file(self):
        self.file_path = filedialog.askopenfilename(title="Select a File")
        if self.file_path:
            self.display_hex(file_path=self.file_path, data=None)

    def open_file(self):
        self.file_path = filedialog.askopenfilename(title="Select a File")
        if self.file_path:
            with open(self.file_path, 'rb') as file:
                self.display_hex(file.read())

    def encode_text(self, mode):
        self.encode_mode = mode
        self.display_hex()
    
    def on_view_data(self):
        data = self.data
        TextViewer(data=data).display_text()

    def display_hex(self, data=None, title=None):
        hex_lines = []
        ascii_lines = []
        
        if data is None and self.data:
            data = self.data
        elif data is None and self.file_path:
            with open(self.file_path, 'rb') as file:
                data = file.read()
        if data is None:
            return
        
        self.data = data
        
        if type(data) == str:
            data = data.encode('utf-8')
        
        for i in range(0, len(data), 16):
            offset = 16
            if len(data[i:]) < 16:
                offset = len(data[i:])
            hex_part = data[i:i+offset]
            hex_str = ' '.join(f'{byte:02X}' for byte in hex_part)
            ascii_str = ''.join(chr(byte) if 32 <= byte <= 126 else '.' for byte in hex_part)
            try:
                utf16_str = hex_part.decode('utf-16')
            except:
                utf16_str = ascii_str
            try:
                utf8_str = hex_part.decode('utf-8')
            except:
                utf8_str = ascii_str
            if self.encode_mode == self.ASCII:
                utf16_str = ascii_str
            elif self.encode_mode == self.UTF8:
                utf16_str = utf8_str
            hex_lines.append(f'{i:08X}  {hex_str:<48}  {utf16_str}')
        
        self.text_area.delete(1.0, tk.END)
        self.text_area.insert(tk.END, '\n'.join(hex_lines))
        if title:
            self.root.title(f'FDPy Hex Viewer - {title}')
        data = str(self.data).replace(",", ",\n")
        data = str(data).replace("{", "{\n")
        data = str(data).replace("}", "\n}")
        self.text_area_preview.insert(tk.END, data)


if __name__ == "__main__":
    root = tk.Tk()
    app = HexViewer(root, useMenu=True)
    root.mainloop()
