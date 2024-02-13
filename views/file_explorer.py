import time

import dearpygui.dearpygui as dpg
from viewmodels.data_files_viewmodel import DataFileViewModel
from models.data_file_manager import File, Directory
from utility.icons import Icons

import win32con
import win32api
import win32gui
import ctypes

class FileExplorer:
    def __init__(self, viewmodel: DataFileViewModel):
        self.viewmodel = viewmodel
        self.viewmodel.set_callback("populate file explorer", self.populate_file_explorer)
        self.viewmodel.set_callback("update file", self.update_file)
        self.icons = Icons()
        self.item_padding = 3
        self._dragging_resizer_button = None
        self._table_columns = [("Icons", 16, 16), ("File", 372, 200), ("Status", 60, 50)]  # (Label, start width, min width)
        self._file_rows = []

        sep = []
        for i in range(24):
            sep.extend([0.8, 0.8, 1, 0.4])
        with dpg.texture_registry(show=False):
            dpg.add_static_texture(width=1, height=24, default_value=sep, tag="pixel")

        with dpg.item_handler_registry() as self.node_handlers:
            dpg.add_item_clicked_handler(callback=self._togge_directory_node_labels)
        with dpg.item_handler_registry() as self.table_handlers:
            dpg.add_item_clicked_handler(callback=self._check_for_mouse_drag)
        with dpg.handler_registry() as self.mouse_handlers:
            dpg.add_mouse_release_handler(dpg.mvMouseButton_Left, callback=self._on_mouse_left_release)

        with dpg.child_window(tag="action bar", width=-1, height=32):
            with dpg.group(horizontal=True):
                self.icons.insert(dpg.add_button(height=32, width=32), Icons.plus, size=16)
                self.icons.insert(dpg.add_button(height=32, width=32), Icons.filter, size=16)

        with dpg.child_window(tag="file explorer panel"):
            with dpg.group(horizontal=True, tag="file table header"):
                for i in range(1, len(self._table_columns)):
                    column = self._table_columns[i]
                    dpg.add_button(label=column[0], width=column[1], height=24, tag=f"table header {i}")
                    dpg.bind_item_handler_registry(dpg.add_image_button("pixel", width=1, height=24, user_data=i), self.table_handlers)
                dpg.add_button(label="", width=-1, height=24)
            dpg.add_spacer(height=16)


        self.configure_theme()

    def _check_for_mouse_drag(self, sender, app_data, handler_user_data):
        if dpg.is_mouse_button_dragging(dpg.mvMouseButton_Left, threshold=0):
            dragging_button = app_data[1]
            print(f"dragging {dragging_button}...")
            self._dragging_resizer_button = dpg.get_item_user_data(dragging_button)

            # Todo: Set system cursor (or hide a resizable table) to rezize/drag; drag vertical line with mouse.

    def _on_mouse_left_release(self):
        dragged_button = self._dragging_resizer_button
        if dragged_button:
            self._dragging_resizer_button = None  # Reset
            delta = dpg.get_mouse_drag_delta()[0]
            print(f"Released: {dragged_button, delta}")
            item = f"table header {dragged_button}"
            header_width = max(self._table_columns[dragged_button][2], dpg.get_item_width(item)+delta)
            dpg.set_item_width(item, header_width)
            for file in self._file_rows:
                item = f"{file.tag}-c{dragged_button}"
                if dragged_button == 1:
                    width = header_width-52-file.depth*20
                else:
                    width = header_width
                dpg.set_item_width(item, width)



    def _togge_directory_node_labels(self, sender, app_data, handler_user_data):
        item_tag = dpg.get_item_user_data(app_data[1])
        label = dpg.get_item_label(item_tag)
        if label[0] == u'\u00a4':
            label = u'\u00a3' + label[1:len(label)]  # TODO: Fails due to window minimizing bug
        else:
            label = u'\u00a4' + label[1:len(label)]
        dpg.set_item_label(item_tag, label)

    def populate_file_explorer(self, directories, files):
        self._file_rows = []
        with dpg.group(horizontal=True, parent="file explorer panel"):
            dpg.add_spacer(width=1)
            dpg.delete_item("file explorer group")
            with dpg.group(horizontal=False, tag="file explorer group") as file_explorer_group:
                for directory in directories:
                    self._display_directory(directory, parent=file_explorer_group)
                self._display_files(files, parent=file_explorer_group)

    def _display_directory(self, directory: Directory, parent: str):
        dpg.add_spacer(height=self.item_padding)
        with dpg.tree_node(label=u"\u00a4  " + directory.name, parent=parent, tag=directory.tag, default_open=True, user_data=directory.tag):
            dpg.bind_item_handler_registry(directory.tag, self.node_handlers)
            dpg.add_spacer(height=self.item_padding)
            for item in directory.content_dirs:
                self._display_directory(item, parent=directory.tag)
            self._display_files(directory.content_files, parent=directory.tag)

    def _display_files(self, files: list, parent: str):
        with dpg.group(horizontal=True):
            dpg.add_spacer(width=22)
            with dpg.table(width=-1, tag=f"{parent}-files table", header_row=False, policy=dpg.mvTable_SizingFixedFit):
                dpg.add_table_column(label="Icon")
                # dpg.add_table_column(label="File Name",  init_width_or_weight=320-depth*20)
                dpg.add_table_column(label="File Name")
                dpg.add_table_column(label="status")
                for file in files:
                    dpg.add_table_row(tag=file.tag)
                    self.update_file(file)

    def update_file(self, file: File):
        dpg.delete_item(file.tag, children_only=True)
        self.icons.insert(dpg.add_button(width=self._table_columns[0][1], parent=file.tag, tag=f"{file.tag}-c0"), Icons.file_code_o, 16)
        dpg.add_selectable(label=file.name, width=self._table_columns[1][1]-52-file.depth*20, span_columns=True, parent=file.tag, tag=f"{file.tag}-c1")
        if file.type:
            self.icons.insert(dpg.add_button(width=self._table_columns[2][1], parent=file.tag, tag=f"{file.tag}-c2"), Icons.check, 16)
        else:
            self.icons.insert(dpg.add_button(width=self._table_columns[2][1], parent=file.tag, tag=f"{file.tag}-c2"), Icons.x, 16)
        if file.tag not in self._file_rows:
            self._file_rows.append(file)

    def configure_theme(self):
        with dpg.theme() as file_explorer_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 8, 0)
                # dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 12, 8)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 0, 0)
                # dpg.add_theme_style(dpg.mvStyleVar_ItemInnerSpacing, 0)
                # dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 0)
                # dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0)
                dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 0)
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, [200, 200, 255, 30])
            with dpg.theme_component(dpg.mvTreeNode):
                dpg.add_theme_color(dpg.mvThemeCol_Text, [255, 255, 255, 200])
            with dpg.theme_component(dpg.mvButton):
                # dpg.add_theme_color(dpg.mvThemeCol_Text, [255, 255, 255, 150])
                dpg.add_theme_color(dpg.mvThemeCol_Button, [0, 0, 0, 0])
                # dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [0, 0, 0, 0])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [0, 0, 0, 0])
                dpg.add_theme_style(dpg.mvStyleVar_ButtonTextAlign, 0.5, 0.5)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, 0)
            with dpg.theme_component(dpg.mvTable):
                dpg.add_theme_style(dpg.mvStyleVar_CellPadding, 4, self.item_padding)


        dpg.bind_item_theme("file explorer panel", file_explorer_theme)

        with dpg.theme() as action_bar_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Button, [0, 0, 0, 0])
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 0, 0)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 4, 4)
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, [200, 200, 255, 80])

        dpg.bind_item_theme("action bar", action_bar_theme)

        with dpg.theme() as table_header_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, [11, 11, 36, 200])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [11, 11, 36, 200])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [11, 11, 36, 200])
                dpg.add_theme_style(dpg.mvStyleVar_ButtonTextAlign, 0.5, 0.5)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, 0)
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 0, 0)
            with dpg.theme_component(dpg.mvImageButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, [11, 11, 36, 200])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [200, 200, 255, 120])
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 10)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 3, 0)

        dpg.bind_item_theme("file table header", table_header_theme)
