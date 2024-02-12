import dearpygui.dearpygui as dpg
from viewmodels.data_files_viewmodel import DataFileViewModel


class FileExplorer:
    def __init__(self, viewmodel: DataFileViewModel):
        self.viewmodel = viewmodel
