import os
# import pyjsonviewer
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog, Tk
from tkinter import font
from tkinter import messagebox
import json
from FdLevelDB import leveldb
import shutil, tempfile
import binascii
try:
    from .fdtkhexviewer import HexViewer
except:
    from fdtkhexviewer import HexViewer

MAX_N_SHOW_ITEM = 300
MAX_HISTORY = 10
FILETYPES = [("WMIC Log files", "*.txt"), ("All Files", "*.*")]
HISTORY_FILE_PATH = os.path.join(os.path.expanduser('~'),
                                 ".fdpylistiewer_history")
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
VERSION = '1.0.0'
PROGRAM_NAME = f'FD PyDBViewer'
def removeChars(text):
    return ''.join([i if (ord(i) > 31 and ord(i) < 128) else '' for i in text])

class TreeviewSorter:
    def __init__(self, treeview):
        self.treeview = treeview
        self.sort_column = None
        self.sort_order = "asc"  # 기본 정렬 순서: 오름차순
        
        # 열 헤더 클릭 이벤트 바인딩
        for col in treeview["columns"]:
            treeview.heading(col, command=lambda c=col: self.sort_column_clicked(c))

    def sort_column_clicked(self, event):
        if type(event) == str or self.treeview.identify_row(str(event.y)):
            return

        _col = self.treeview.identify_column(str(event.x))
        col = int(_col[1:]) - 1
        # col = self.treeview.heading(int(_col[1:]) - 1,'text')
        # 현재 정렬된 열이 클릭되면 정렬 순서를 토글
        if col == self.sort_column:
            self.sort_order = "desc" if self.sort_order == "asc" else "asc"
        else:
            self.sort_order = "asc"
            self.sort_column = col
        
        # 데이터를 정렬하고 Treeview 업데이트
        self.sort_data(col, self.sort_order)

    def sort_data(self, col, sort_order):
        # 데이터 가져오기
        items = [(self.treeview.item(item_id)['values'], item_id) for item_id in self.treeview.get_children()]
        if len(items) == 0:
            return
                
        # 열 인덱스 찾기
        col_index = col  #self.treeview["columns"].index(col)
        
        if type(items[0][0][col_index]) == int:
            sort_fn = lambda x: float(x[0][col_index])
        else:
            if col_index == -1: # 숫자로된 문자열일 때
                # sorted(items, key=lambda item: float(item[-1]), reverse=True)
                sort_fn = lambda x: float(x[col_index])
            else:
                sort_fn = lambda x: str(x[0][col_index])
        # 데이터를 정렬
        items.sort(key=sort_fn, reverse=(sort_order == "desc"))
        
        # 정렬된 데이터로 Treeview 업데이트
        for item in items:
            self.treeview.move(item[1], '', 'end')

class FDTreeFrame(ttk.Frame):
    class Listbox(tk.Listbox):
        """
            auto width list box container
        """
        def auto_width(self, max_width):
            f = font.Font(font=self.cget("font"))
            pixels = 0
            for item in self.get(0, "end"):
                pixels = max(pixels, f.measure(item))
            # bump listbox size until all entries fit
            pixels = pixels + 10
            width = int(self.cget("width"))
            for w in range(0, max_width + 1, 5):
                if self.winfo_reqwidth() >= pixels:
                    break
                self.config(width=width + w)

    def __init__(self, master, json_path=None, json_data=None, initial_dir="~/"):
        super().__init__(master)
        self.master = master
        self.tree = ttk.Treeview(self)
        data = json_data        
        if json_path:
            self.set_table_data_from_json_path(json_path)
        else:
            if isinstance(data, list):
                self.columns = data[0]
                self.set_columns(self.columns)    
            else:
                self.set_columns({})
            self.create_widgets()
        self.sub_win = None
        self.initial_dir = initial_dir
        self.search_box = None
        self.bottom_frame = None
        self.search_box = None
        self.search_label = None
        self.item_found = []
        self.item_idx = 0
        self.tree_sort = None
        if data:
            self.set_table_data_from_json(data)
            if initial_dir != "~/":
                self.master.title(f'{PROGRAM_NAME} - {initial_dir}')

    def set_columns(self, columns: dict):
        idx = 1
        self.columns = {}
        for k in columns:
            self.columns['c' + str(idx)] = {'label': k, 'width': 150}
            idx += 1

    def sort_column(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region != "heading":
            return
        if not self.tree_sort:
            self.tree_sort = TreeviewSorter(self.tree)
        if self.tree_sort:
            self.tree_sort.sort_column_clicked(event)
            self.tree = self.tree_sort.treeview

    def on_column_resize(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region == "separator":
            pass

    def create_widgets(self):
        # https://stackoverflow.com/questions/69223318/using-multiple-tkinter-treeview-styles-in-same-program
        # style_wear = ttk.Style()
        # style_wear.configure("fortree1.Treeview",background="yellow", foreground="black",fieldbackground="red")
        # style_wear.map('fortree1.Treeview', background=[('selected','green')], foreground=[('selected','black')])

        # self.columns = {
        #     "c1": {'label': "InstallDate", 'width': 50}, 
        #     "c2": {'label': "Name", 'width': 300},
        #     "c3": {'label': "Vendor", 'width': 50},
        #     "c4": {'label': "Version", 'width': 50}
        #     }
        # display_orders = list(self.columns.keys())
        self.tree=None
        self.tree=ttk.Treeview(self, columns=list(self.columns.keys())
                            , height=5)
                            #    style="fortree1.Treeview") #, displaycolumns=display_orders)
        self.tree.bind('<Double-1>', self.click_item)
        self.tree.bind('<ButtonRelease-1>', self.on_column_resize)
        self.tree.bind('<Button-1>', self.sort_column)

        # 각 컬럼 설정. 컬럼 이름, 컬럼 넓이, 정렬 등
        if len(self.columns) > 0:
            self.tree.column("#0", width=10,)
            self.tree.heading("#0", text="index")
        idx = 1
        for k, v in self.columns.items():
            self.tree.column(f'#{idx}', width=v['width'], anchor='w')
            self.tree.heading(k, text=v['label'], anchor='w')
            idx += 1
        
        self.ysb = tk.Scrollbar(
            self, orient=tk.VERTICAL, command=self.tree.yview)

        self.xsb =  tk.Scrollbar(
            self, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscroll=self.ysb.set, xscroll=self.xsb.set)

        self.tree.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.ysb.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.xsb.grid(row=1, column=0, sticky=(tk.E, tk.W))
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

    def init_search_box(self):
        # s=ttk.Separator(self, orient="vertical")	
        # s.grid(row=1,column=0, sticky='ns')

        self.bottom_frame = tk.Frame(self)
        self.bottom_frame.grid(row=2, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))


        self.search_label = tk.Label(self.bottom_frame, text="Search:")
        self.search_label.pack(side=tk.LEFT)

        self.search_next = tk.Button(self.bottom_frame, text='Find Next', command=self.goto_item)
        self.search_next.pack(side='right')
        self.search_next.config(state=tk.DISABLED)

        self.search_box = tk.Entry(self.bottom_frame)
        self.search_box.pack(fill='x')
        self.search_box.bind('<Key>', self.find_word)
        

    def insert_node_new(self, parent, key, value):
        if isinstance(value, dict):
            v = tuple(value.values())
            self.tree.insert('', 'end', text=str(key), values=v, iid=key, tags = ('normal',))

    def insert_node_old(self, parent, key, value):

        node = self.tree.insert(parent, 'end', text=key, open=False)

        if value is None:
            return

        if type(value) in (list, tuple):
            for index, item in enumerate(value[:MAX_N_SHOW_ITEM]):
                self.insert_node_old(node, index, item)
        elif isinstance(value, dict):
            for key, item in value.items():
                self.insert_node_old(node, key, item)
        else:
            self.tree.insert(node, 'end', text=value, open=False)
    
    def get_column_idx(self, x):
        _col = self.tree.identify_column(str(x))
        label = self.columns['c' + _col[1:]]['label']
        col = int(_col[1:]) - 1
        return col, label
    
    def click_item(self, event=None):
        """
        Callback function when an item is clicked

        :param event: event arg (not used)
        """
        selected_item = self.tree.focus()  # 현재 선택된 아이템의 ID를 가져옵니다.
        if not selected_item:
            return  # 선택된 아이템이 없으면 함수 종료
        
        # item_id = self.tree.selection()
        # item_text = self.tree.item(item_id, 'text')
        try:
            col, label = self.get_column_idx(event.x)
            item_text = self.tree.item(selected_item)['values'][col]
            # messagebox.showinfo("Info", item_text)
            if '(Hex)' in label and len(item_text) > 3 and item_text[0] == 'b':
                item_bin = binascii.unhexlify(item_text[2:][:-1])
                HexViewer().display_hex(data=item_bin, title=f'#{selected_item}->{label}')
            else:
                HexViewer().display_hex(data=item_text)
        except Exception as e:
            print(e)
            pass

        # if self.is_url(item_text):
        #     webbrowser.open(item_text)

    def select_log_file(self, event=None):
        """
        :param event: event arg (not used)
        """
        file_path = filedialog.askopenfilename(
            initialdir=self.initial_dir,
            filetypes=FILETYPES)
        self.set_table_data_from_json_path(file_path)
    
    def select_log_dir(self, event=None):
        """
        :param event: event arg (not used)
        """
        file_path = filedialog.askdirectory(
            initialdir=self.initial_dir,
            title='Select a Level DB directory')
        self.set_table_data_from_leveldb(file_path)
    
    def expand_all(self, event=None):
        """
        :param event: event arg (not used)
        """
        for item in self.get_all_children(self.tree):
            self.tree.item(item, open=True)

    def search_clear(self, event=None):
        """
        :param event: event arg (not used)
        """
        # for item in self.get_all_children(self.tree):
        for item in self.tree.get_children():
            self.tree.item(item, tags=())

        self.button_disable(self.search_next)

    def copy_to_clipboard(self, event=None):
        selected_item = self.tree.focus()  # 현재 선택된 아이템의 ID를 가져옵니다.
        if not selected_item:
            return  # 선택된 아이템이 없으면 함수 종료

        # 선택된 아이템의 값을 가져옵니다.
        values = self.tree.item(selected_item, "values")
        
        # 값들을 문자열로 변환하고 탭으로 구분하여 클립보드에 저장합니다.
        # clipboard_data = "\t".join(map(str, values))
        result = []
        idx = 1
        for item_text in values:
            label = self.columns['c' + str(idx)]['label']
            result.append({label: item_text})
            idx += 1

        clipboard_data = json.dumps(result)
        
        # 클립보드에 데이터를 복사합니다.
        self.master.clipboard_clear()
        self.master.clipboard_append(clipboard_data)

    def find_word(self, event=None):
        """
        :param event: event arg (not used)
        """
        search_text = self.search_box.get()
        self.find(search_text)

    def button_disable(self, btn, text="Find Next"):
        btn.config(text=text)
        btn.config(state=tk.DISABLED)

    def goto_item(self, _idx=-1):
        if len(self.item_found) == 0:
            self.button_disable(self.search_next, text=f"Find Next")
            return
        idx  = _idx
        if self.item_idx >= 0 and idx == -1:
            if self.item_idx < len(self.item_found) - 1:
                self.item_idx += 1
            else:
                self.item_idx = 0
            try:
                idx = self.item_found[self.item_idx]
            except IndexError:
                self.item_idx = 0
                idx = self.item_found[self.item_idx]
        
        if int(idx) >= 0:
            item_id = idx
            self.tree.see(item_id)
            self.tree.selection_set(item_id)
            self.tree.focus(item_id)
            self.search_next.config(text=f"({self.item_idx + 1}/{len(self.item_found)}) Find Next")
    
    def find(self, search_text):
        if not search_text:
            return
        self.item_found = []
        self.search_clear(None)
        for item_id in self.tree.get_children():
            item = self.tree.item(item_id)
            item_values = item['values']
            for item_text in item_values:
                item_text = str(item_text)
                if search_text.lower() in item_text.lower():
                    try:
                        self.tree.item(item_id, tags = ('highlight',))
                    except Exception as e:
                        item = self.tree.item(item_id)
                        pass
                    self.item_found.append(item_id)
                    break
        # print(f'found: {found_cnt}')
        self.tree.tag_configure('highlight', background='yellow')
        found_first_item = -1
        if len(self.item_found) > 0:
            found_first_item = self.item_found[0]            
        if found_first_item != -1:
            self.goto_item(found_first_item)
            self.search_next.config(state=tk.NORMAL)

    def get_all_children(self, tree, item=""):
        children = tree.get_children(item)
        for child in children:
            children += self.get_all_children(tree, child)
        return children

    def select_listbox_item(self, event):
        """
        :param event: event arg (not used)
        """
        w = event.widget
        index = int(w.curselection()[0])
        value = w.get(index)
        if os.path.isdir(value):
            self.set_table_data_from_leveldb(value)
        else:
            self.set_table_data_from_json_path(value)
        self.sub_win.destroy()  # close window

    def select_json_file_from_history(self, event=None):
        """
        :param event: event arg (not used)
        """
        self.sub_win = tk.Toplevel()
        lb = self.Listbox(self.sub_win)
        with open(HISTORY_FILE_PATH) as f:
            lines = self.get_unique_list(reversed(f.readlines()))
            for ln, line in enumerate(lines):
                lb.insert(ln, line.replace("\n", ""))
        lb.bind('<Double-1>', self.select_listbox_item)
        maximum_width = 250
        lb.auto_width(maximum_width)
        lb.pack()

    def save_json_history(self, file_path):
        lines = []
        try:
            with open(HISTORY_FILE_PATH, "r") as f:
                lines = self.get_unique_list(f.readlines())
        except FileNotFoundError:
            print("created:" + HISTORY_FILE_PATH)

        lines.append(file_path)

        with open(HISTORY_FILE_PATH, "w") as f:
            lines = lines[max(0, len(lines) - MAX_HISTORY):]
            for line in lines:
                f.write(line.replace("\n", "") + "\n")

    def set_table_data_from_json(self, json_data):
        assert type(json_data) in (list, dict)
        self.delete_all_nodes()
        self.insert_nodes(json_data)
        self.tree_sort = None

    @staticmethod
    def load_json_data(file_path):
        try:
            with open(file_path, encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            return load_wmic_output(file_path=file_path)

    def set_table_data_from_json00_path_old(self, file_path):
        data = self.load_json_data(file_path)
        self.save_json_history(file_path)
        self.set_table_data_from_json(data)
        return data

    def set_table_data_from_json_path(self, file_path):
        data = self.load_json_data(file_path)
        self.save_json_history(file_path)
        # self.set_table_data_from_json(data)
        if isinstance(data, list):
            self.columns = data[0]
            self.set_columns(self.columns)    
        else:
            self.set_columns({})
        self.create_widgets()
        self.set_table_data_from_json(data)
        return data

    def set_table_data_from_leveldb(self, file_path):
        if not file_path:
            self.master.title(PROGRAM_NAME)
            data = None
        else:
            data = load_leveldb_data(file_path)
            self.save_json_history(file_path)
        try:
            if isinstance(data, list):
                self.columns = data[0]
                self.set_columns(self.columns)    
            else:
                self.set_columns({})
            self.create_widgets()
            self.set_table_data_from_json(data)
            self.master.title(f'{PROGRAM_NAME} - {file_path}')
            return data
        except AssertionError:
            return

    def delete_all_nodes(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

    def insert_nodes(self, data):
        parent = ""
        if isinstance(data, list):
            for index, value in enumerate(data):
                self.insert_node_new(parent, index+1, value)
        elif isinstance(data, dict):
            for (key, value) in data.items():
                self.insert_node_old(parent, key, value)

    def open_url(self, url):
        return
        # if self.is_url(url):
        #     pass #webbrowser.open(url)
        # else:
        #     print("Error: this is not url:", url)

    # @staticmethod
    # def is_url(text):
    #     """check input text is url or not

    #     :param text: input text
    #     :return: url or not
    #     """
    #     # parsed = urlparse(text)
    #     # return all([parsed.scheme, parsed.netloc, parsed.path])
    #     return False

    @staticmethod
    def get_unique_list(seq):
        seen = []
        return [x for x in seq if x not in seen and not seen.append(x)]

    # @staticmethod
    # def load_json_data(file_path):
    #     with open(file_path, encoding='utf-8') as f:
    #         return json.load(f)

    @staticmethod
    def show_info_window():
        msg = f"""
        {PROGRAM_NAME}
        by Kate Choi
        : referenced from pyjsonviewer

        Ver.{VERSION}\n
        """
        messagebox.showinfo("About", msg)

def load_wmic_output(file_path):
    programs = []
    offsets = {}
    base_line_length = 0
    if not file_path:
        return
    # UTF-16 인코딩으로 파일을 읽기 시도
    try:
        with open(file_path, 'r', encoding='utf-16') as file:
            line_no = 0
            for line in file:
                # 첫번째 라인에서 offset을 추출한다.
                if len(offsets) == 0:
                    base_line_length = len(line)
                    # InstallDate  Name Vendor Version           
                    for name in line.split():
                        offsets[name] = line.find(name)
                    continue
                # 나머지 줄을 읽기
                line_no += 1
                idx_name = offsets['Name']
                idx_vendor = offsets['Vendor']
                idx_version = offsets['Version']
                idx_gap = 0
                
                # 각 필드를 추출
                install_date = line[0:idx_name].strip()
                if install_date == '':
                    continue
                if len(line) < base_line_length:
                    idx_gap = base_line_length - len(line)
                
                if idx_gap > 0:
                    idx_vendor -= idx_gap
                    idx_version -= idx_gap

                name    = line[idx_name:idx_vendor].strip()
                vendor  = line[idx_vendor:idx_version].strip()
                version = line[idx_version:].strip()

                # 딕셔너리에 추가
                program = {
                    'InstallDate': install_date,
                    'Name': name,
                    'Vendor': vendor,
                    'Version': version
                }
                programs.append(program)
    except UnicodeDecodeError:
        print(f"파일을 읽을 수 없습니다: {file_path}")    
    return programs

def load_leveldb_data(file_dir,prefix='FDCache_Data', cleanup_dir=True):
    list_data = []
    if not os.path.isdir(file_dir):
        return
    try:
        target_dir = ''
        with tempfile.TemporaryDirectory(prefix=prefix) as temp_dir:
            try:
                shutil.copytree(src=file_dir, dst=temp_dir, dirs_exist_ok=True)
                print(f'copy path into: {temp_dir}')
                target_dir = temp_dir
            except Exception as e:
                print(e)
                return
            levelDb = None
            try:
                levelDb = leveldb.LevelDB(temp_dir)
            except:
                # Repair db in dbdir, eg:
                # Corruption: corrupted compressed block contents
                print ('Repairing db...\n')
                leveldb.RepairDB(temp_dir)

            try:
                if levelDb is None:
                    levelDb = leveldb.LevelDB(temp_dir)
                numRecords = 0
                for key, value in levelDb.RangeIter():
                    # key2 = str(key, 'utf-8', 'ignore')
                    keyd16 = key.decode('utf-8', "ignore")
                    vald16 = value.decode('utf-8', 'ignore')
                    newKey = removeChars(keyd16)
                    newVal = removeChars(vald16)
                    if len(str(newKey)) > 1 and (len(str(newVal)) > 0 or len(value) > 0):
                        list_data.append({'Key': newKey, 'Value': newVal, 'Key(Hex)':binascii.hexlify(key),'Value(Hex)': binascii.hexlify(value)})
                        numRecords = numRecords + 1
                print ("Number of records dumped are ==> " + str(numRecords))
                levelDb = None
                return list_data
            except: 
                return
    except Exception as e:
        print(e)
    finally:
        if os.path.isdir(target_dir) and len(target_dir) > 4 and 'FDCache_Data' in target_dir: # root folder 삭제 방지
            try:
                if cleanup_dir:
                    shutil.rmtree(target_dir)
                    print(f'Temp folder removed: {e}')
            except Exception as e:
                print(f'Remove folder failed: {e}')

def adjust_column_widths(tree, columns, data):
    for col in columns:
        max_width = max([len(str(item)) for item in data] + [len(col)])
        max_width = min(20, max_width)
        tree.column(col, width=max_width * 10)  # 10: font width
        tree.heading(col, text=columns[col]['label'], anchor='w')

def view_data(json_file=None, json_data=None, initial_dir=None):
    root: Tk = tk.Tk()
    root.title(PROGRAM_NAME)
    root.geometry("1024x768")
    try:
        root.tk.call('wm', 'iconphoto', root._w,
                 tk.PhotoImage(file=PROJECT_DIR + '/icon.png'))
    except:
        pass
    menubar = tk.Menu(root)
    # "displayName": "KBSKong 2.0.4",
    #       "displayVersion": "2.0.4",
    #       "estimatedSize": "447309",
    #       "installDate": "2024-05-21 15:48:04",
    #       "publisher": "KBSmedia devteam"
    if json_file:
        app = FDTreeFrame(root, json_path=json_file, initial_dir=initial_dir)
    elif json_data:
        app = FDTreeFrame(root, json_data=json_data, initial_dir=initial_dir)
        adjust_column_widths(app.tree, app.columns, json_data)
    else:
        app = FDTreeFrame(root)

    file_menu = tk.Menu(menubar, tearoff=0)
    file_menu.add_command(label="Open", accelerator='Ctrl+O',
                          command=app.select_log_file)
    file_menu.add_command(label="Open Directory", accelerator='Ctrl+F',
                          command=app.select_log_dir)
    file_menu.add_command(label="Open from History", accelerator='Ctrl+H',
                          command=app.select_json_file_from_history)
    menubar.add_cascade(label="File", menu=file_menu)

    tool_menu = tk.Menu(menubar, tearoff=0)
    tool_menu.add_command(label="Clear search",
                          accelerator='Ctrl+L', command=app.search_clear)
    tool_menu.add_command(label="Copy row",
                          accelerator='Ctrl+C', command=app.copy_to_clipboard)
    menubar.add_cascade(label="Tools", menu=tool_menu)

    help_menu = tk.Menu(menubar, tearoff=0)
    help_menu.add_command(label="About", command=app.show_info_window)
    menubar.add_cascade(label="Help", menu=help_menu)

    app.grid(column=0, row=0, sticky=(tk.N, tk.S, tk.E, tk.W))
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    
    app.init_search_box()

    root.config(menu=menubar)
    root.bind_all("<Control-o>", lambda e: app.select_log_file(event=e))
    root.bind_all("<Control-f>", lambda e: app.select_log_dir(event=e))
    root.bind_all("<Control-h>",
                  lambda e: app.select_json_file_from_history(event=e))
    root.bind_all("<Control-e>", lambda e: app.expand_all(event=e))
    root.bind_all("<Control-l>", lambda e: app.search_clear(event=e))
    root.bind_all("<Control-c>", lambda e: app.copy_to_clipboard(event=e))

    root.mainloop()

if __name__ == "__main__":
    programs = [{'InstallDate': '20240429', 'Name': 'Python 3.12.3 Core Interpreter (64-bit symbols)', 'Vendor': 'Python Software Foundation', 'Version': '3.12.3150.0'}]
    view_data(json_data=programs)