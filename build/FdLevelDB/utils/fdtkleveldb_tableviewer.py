__version__ = "1.0.1"
__author__ = "Kate Choi <sojins@finaldata.com>"

from ccl_chromium_reader import ccl_chromium_indexeddb
from FdLevelDB.utils.fdtklist import view_data

import tkinter as tk
from tkinter import filedialog
import tkinter.ttk as ttk
import os

TITLE="Select Level DB directory"

class DBSelector(ttk.Frame):
    def __init__(self, wrapper: None, data: list, cb):
        root = tk.Tk()

        self.root = root
        self.root.title(TITLE)
        self.initial_dir=''
        self.file_path = ''
        self.data = data
        self.wrapper = wrapper
        self.cb = cb

    def create_menubar(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open Directory", accelerator='Ctrl+F',
                            command=self.select_log_dir)
        menubar.add_cascade(label="File", menu=file_menu)
        self.root.config(menu=menubar)
    
    def get_tables(self, db_name):
        try:
            tables = [item for item in self.data if item['name'] == db_name][0]['tables']
            return tables
        except:
            pass

    def find_indexeddb_components(self, selected_dir):
        # 마지막 폴더 이름이 'IndexedDB'인지 확인
        if os.path.basename(selected_dir) != "IndexedDB":
            return None

        # 하위 폴더 중 '.blob', '.leveldb'로 끝나는 폴더 찾기
        blob_path = None
        leveldb_path = None

        for entry in os.listdir(selected_dir):
            full_path = os.path.join(selected_dir, entry)
            if os.path.isdir(full_path):
                if entry.endswith(".blob"):
                    blob_path = full_path
                elif entry.endswith(".leveldb"):
                    leveldb_path = full_path

        if blob_path and leveldb_path:
            return blob_path, leveldb_path
        else:
            return None

    def select_log_dir(self):
        """
        :param event: event arg (not used)
        """
        file_path = filedialog.askdirectory(
            initialdir=self.initial_dir,
            title=TITLE)
        (blob_path, leveldb_path) = self.find_indexeddb_components(file_path)
        if blob_path and leveldb_path:
            (wrapper, db_names) = load_data(db_dir=leveldb_path, blob_dir=blob_path)
            self.root.destroy()  # 또는 self.window.destroy()
            DBSelector(wrapper, data=db_names, cb=view_table_cb).select_db_by_tree()
            return
        (wrapper, db_names) = load_data(file_path)
        if db_names:
            self.root.title(file_path)
        self.insert_db_list(wrapper=wrapper, data=db_names)

    def get_rows(self, db_name:str, table_name:str):
        obj_store = self.wrapper[db_name][table_name]
        list_data = []
        for record in obj_store.iterate_records(
                errors_to_stdout=True, 
                bad_deserializer_data_handler= lambda k,v: print(f"error: {k}, {v}")):
            if record.value:
                list_data.append(record.value)
        return len(list_data)

    def select_db_by_tree(self):
        # self.sub_win = tk.Toplevel()
        self.root.geometry("640x480")
        # Grid 레이아웃에 맞게 row와 column 설정
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        self.sub_win = tk.Frame(self.root)
        frame = self.sub_win
        frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Frame 내에서도 행과 열 확장 가능 설정
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        
        # 스크롤바
        ysb = ttk.Scrollbar(frame, orient=tk.VERTICAL)
        ysb.grid(row=0, column=1, sticky="ns")

        tree = ttk.Treeview(frame, columns=('type', 'size'), show='tree headings', yscrollcommand=ysb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        tree.heading("#0", text="Name", anchor='w')
        tree.heading("type", text="Type", anchor='w')
        tree.heading("size", text="Size", anchor='w')

        # 고정 너비 설정
        tree.column("type", width=100, minwidth=100, stretch=False)
        tree.column("size", width=80, minwidth=100, stretch=False)

        ysb.config(command=tree.yview)

        # 스타일 지정
        tree.tag_configure('empty', foreground='grey')  # 또는 background, font 등

        # 메뉴바
        self.create_menubar()
        
        idx = 1
        for db_info in self.data:
            db_name = db_info['name']
            tables = self.get_tables(db_name)
            item_id = tree.insert('', 'end', text=db_name, values=['database', len(tables)])
            idx += 1

            if tables:
                for table in tables:
                    rows = self.get_rows(db_name, table)
                    tag = 'empty' if rows == 0 else ''
                    tree.insert(item_id, "end", text=table, values=['table', rows], tags=(tag,))
                    idx += 1

        tree.bind('<Double-1>', self.select_tree_item)
        self.tree = tree
        self.root.mainloop()

    def delete_all_nodes(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

    def insert_db_list(self, wrapper, data):
        self.delete_all_nodes()
        self.data = data
        self.wrapper = wrapper
        idx = 1
        for db_info in self.data:
            db_name = db_info['name']
            item_id = self.tree.insert('', 'end', text=db_name, values=['database'])
            idx += 1

            tables = self.get_tables(db_name)
            if tables:
                for table in tables:
                    self.tree.insert(item_id, "end", text=table, values=['table'])
                    idx += 1

    def select_tree_item(self, event):
        """
        :param event: event arg (not used)
        """
        index = self.tree.focus()
        item = self.tree.item(index)
        if item['values'][0] == 'table':
            db_name = self.tree.item(self.tree.parent(index))['text']
            table = item['text']
            self.cb(self.wrapper, db_name, table)
        else:
            db_name = item['text']
            tables = [item for item in self.data if item['name'] == db_name][0]['tables']
            if tables:
                self.cb(self.wrapper, db_name, tables[0])

def view_table_cb(wrapper, db_name, table_name):
    view_table_data(wrapper, db_name, table_name=table_name)

def view_table_data(wrapper, db_name=None, table_name=None):
    if not db_name or not table_name:
        return
    
    db = wrapper[db_name]

    # Object stores can be accessed from the database in a number of ways:
    # obj_store = db[1]  # accessing object store using id number
    obj_store = db[table_name]  # accessing object store using name
    
    list_data = []

    # By default, any errors in decoding records will bubble an exception 
    # which might be painful when iterating records in a for-loop, so either
    # passing True into the errors_to_stdout argument and/or by passing in an 
    # error handler function to bad_deserialization_data_handler, you can 
    # perform logging rather than crashing:

    for record in obj_store.iterate_records(
            errors_to_stdout=True, 
            bad_deserializer_data_handler= lambda k,v: print(f"error: {k}, {v}")):
        if record.value:
            list_data.append(record.value)
    view_data(json_data=list_data, initial_dir=table_name)

def load_data(db_dir, blob_dir=None):
    # assuming command line arguments are paths to the .leveldb and .blob folders
    leveldb_folder_path = db_dir
    blob_folder_path = blob_dir
    db_names = []
    if not db_dir:
        return (None, db_names)

    # open the indexedDB:
    wrapper = ccl_chromium_indexeddb.WrappedIndexDB(leveldb_folder_path, blob_folder_path)

    # You can check the databases present using `wrapper.database_ids`

    # Databases can be accessed from the wrapper in a number of ways:
    # db = wrapper[2]  # accessing database using id number
    # db = wrapper["MyTestDatabase"]  # accessing database using name (only valid for single origin indexedDB instances)
    # db = wrapper["MyTestDatabase", "file__0@1"]  # accessing the database using name and origin
    for name in wrapper._db_name_lookup:
        dict_table = {'name': name[0],
        'tables': wrapper[name[0]]._obj_store_names}
        db_names.append(dict_table)
    return (wrapper, db_names)

def run_gui(db_dir, blob_dir=None):
    # # assuming command line arguments are paths to the .leveldb and .blob folders
    # leveldb_folder_path = db_dir
    # blob_folder_path = blob_dir

    # # open the indexedDB:
    # wrapper = ccl_chromium_indexeddb.WrappedIndexDB(leveldb_folder_path, blob_folder_path)

    # # You can check the databases present using `wrapper.database_ids`

    # # Databases can be accessed from the wrapper in a number of ways:
    # # db = wrapper[2]  # accessing database using id number
    # # db = wrapper["MyTestDatabase"]  # accessing database using name (only valid for single origin indexedDB instances)
    # # db = wrapper["MyTestDatabase", "file__0@1"]  # accessing the database using name and origin
    # db_names = []
    # for name in wrapper._db_name_lookup:
    #     dict_table = {'name': name[0],
    #     'tables': wrapper[name[0]]._obj_store_names}
    #     db_names.append(dict_table)
    (wrapper, db_names) = load_data(db_dir=db_dir, blob_dir=blob_dir)
    DBSelector(wrapper, data=db_names, cb=view_table_cb).select_db_by_tree()

if __name__ == "__main__":
    db_dir=r'G:\Examples\~MSTeams\Lee'
    run_gui(db_dir=None)
