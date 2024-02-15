import dearpygui.dearpygui as dpg
from viewmodels.data_files_viewmodel import DataFileViewModel
from models.data_file_manager import File, Directory, GaussianLog, FileType
from utility.icons import Icons


class FileExplorer:
    def __init__(self, viewmodel: DataFileViewModel):
        self.viewmodel = viewmodel
        self.viewmodel.set_callback("populate file explorer", self.update_file_explorer)
        self.viewmodel.set_callback("update file", self.update_file)
        self.icons = Icons()
        self.item_padding = 3
        self._resizing_column = None  # column number currently being resized
        self._dragging_button = None  # tag of resizer button being dragged
        self._table_columns = [["Icons", 16, 16], ["File", 372, 200], ["Status", 60, 50]]  # (Label, start/current width, min width)
        self._file_rows = []
        self._file_tables = []
        self._directory_nodes = {}
        self._last_delta = 0

        # TODO: Keep track of open/closed status of folders;

        with dpg.theme() as self.invisible_button_theme:
            with dpg.theme_component(dpg.mvImageButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, [11, 11, 36, 0])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [11, 11, 36, 0])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [11, 11, 36, 0])

        sep = []
        for i in range(24):
            sep.extend([0.8, 0.8, 1, 0.4])
        # long_sep = []
        # for i in range(500):
        #     long_sep.extend([0.8, 0.8, 1, 0.4])
        with dpg.texture_registry(show=False):
            dpg.add_static_texture(width=1, height=24, default_value=sep, tag="pixel")
            # dpg.add_static_texture(width=1, height=500, default_value=long_sep, tag="long separator")

        with dpg.item_handler_registry() as self.node_handlers:
            dpg.add_item_clicked_handler(callback=self._toggle_directory_node_labels)
        with dpg.item_handler_registry() as self.table_handlers:
            dpg.add_item_clicked_handler(callback=self._start_table_mouse_drag)
        with dpg.handler_registry() as self.mouse_handlers:
            dpg.add_mouse_release_handler(dpg.mvMouseButton_Left, callback=self._on_mouse_left_release)

        with dpg.child_window(tag="action bar", width=-1, height=32):
            with dpg.group(horizontal=True):
                self.icons.insert(dpg.add_button(height=32, width=32, callback=self._add_data_folder), Icons.folder_plus, size=16)
                self.icons.insert(dpg.add_button(height=32, width=32, callback=self._add_data_files), Icons.file_plus, size=16)
                s = dpg.add_image_button("pixel", width=1, height=24)
                dpg.bind_item_theme(s, self.invisible_button_theme)
                self.icons.insert(dpg.add_button(height=32, width=32), Icons.filter, size=16)
                self.icons.insert(dpg.add_button(height=32, width=32), Icons.eye, size=16)

        with dpg.group(horizontal=True, tag="file table header"):
            for i in range(1, len(self._table_columns)):
                column = self._table_columns[i]
                dpg.add_button(label=column[0], width=column[1], height=24, tag=f"table header {i}")
                dpg.bind_item_handler_registry(dpg.add_image_button("pixel", width=1, height=24, user_data=i, tag=f"sep-button-{i}"), self.table_handlers)
                # with dpg.tooltip(f"sep-button-{i}"):  # Technically it works but it's wonky
                #     dpg.add_image("long separator")
            dpg.add_button(label="", width=-1, height=24)

        with dpg.child_window(tag="file explorer panel"):
            dpg.add_spacer(height=16)
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=1)
                dpg.add_group(horizontal=False, tag="file explorer group")

        self.configure_theme()

    def _tables_resize(self):
        column = self._resizing_column
        if column:
            delta = dpg.get_mouse_drag_delta()[0]
            if delta != self._last_delta:  # Necessary to avoid bug where delta is last drag's delta when it should be 0
                item = f"table header {column}"
                header_width = max(self._table_columns[column][2], self._table_columns[column][1] + delta)
                dpg.set_item_width(item, header_width)
                for file in self._file_rows:
                    item = f"{file.tag}-c{column}"
                    if column == 1:
                        width = header_width - 52 - file.depth * 20
                    else:
                        width = header_width
                    dpg.set_item_width(item, width)
                self._last_delta = delta

            with dpg.mutex():
                dpg.set_frame_callback(dpg.get_frame_count() + 1, self._tables_resize)

    def _start_table_mouse_drag(self, sender, app_data, handler_user_data):
        if dpg.is_mouse_button_dragging(dpg.mvMouseButton_Left, threshold=0):
            # resize_cursor = ctypes.windll.user32.LoadCursorW(0, 32644)
            # ctypes.windll.user32.SetCursor(resize_cursor)
            self._dragging_button = app_data[1]
            self._resizing_column = dpg.get_item_user_data(self._dragging_button)
            self._table_columns[self._resizing_column][1] = dpg.get_item_width(f"table header {self._resizing_column}")
            self._tables_resize()

    def _on_mouse_left_release(self):
        column = self._resizing_column
        if column:
            # arrow_cursor = ctypes.windll.user32.LoadCursorW(0, 32512)
            # ctypes.windll.user32.SetCursor(arrow_cursor)
            self._table_columns[column][1] = dpg.get_item_width(f"table header {column}")
            self._resizing_column = None  # Reset

    def _toggle_directory_node_labels(self, sender, app_data, handler_user_data):
        item_tag = dpg.get_item_user_data(app_data[1])
        label = dpg.get_item_label(item_tag)
        if self._directory_nodes[item_tag]:  # label[0] == u'\u00a4':
            label = u'\u00a3' + label[1:len(label)]  # TODO: Fails due to window minimizing bug. Check for coming into view or something?
        else:
            label = u'\u00a4' + label[1:len(label)]
        dpg.set_item_label(item_tag, label)
        self._directory_nodes[item_tag] = not self._directory_nodes[item_tag]
        self.viewmodel.toggle_directory(item_tag, self._directory_nodes[item_tag])

    def _add_data_folder(self):
        self.viewmodel.inquire_open_data_directory()

    def _add_data_files(self):
        self.viewmodel.inquire_open_data_files()

    def reset_file_explorer(self, directories, files):
        self._file_rows = []
        self._file_tables = []
        self._directory_nodes = {}
        dpg.delete_item("file explorer group", children_only=True)
        self.update_file_explorer(directories, files)

    def update_file_explorer(self, directories, files):
        for directory_tag in directories.keys():
            directory = directories[directory_tag]
            self._display_directory(directory, parent="file explorer group")
        self._display_files(files, parent="file explorer group")

    def _display_directory(self, directory: Directory, parent: str):
        # if directory.tag in self._directory_nodes.keys():
        #     is_open = self._directory_nodes.get(directory.tag, True)  # nothing to change really; just updating open-ness
        #     icon = u"\u00a4  " if is_open else u"\u00a3  "
        #     dpg.configure_item(directory.tag, label=icon + directory.name, default_open=is_open)
        if directory.tag not in self._directory_nodes.keys():
            dpg.add_spacer(height=self.item_padding, parent=parent)
            is_open = self.viewmodel.get_dir_state(directory.tag)  # TODO> Save as directory.start_open in project file (for top level dirs)
            print(f"Open? {directory.name, is_open}")
            icon = u"\u00a4  " if is_open else u"\u00a3  "
            with dpg.tree_node(label=icon + directory.name, parent=parent, tag=directory.tag, default_open=is_open, user_data=directory.tag):
                dpg.bind_item_handler_registry(directory.tag, self.node_handlers)
                dpg.add_spacer(height=self.item_padding)
                for dir_tag in directory.content_dirs.keys():
                    d = directory.content_dirs[dir_tag]
                    self._display_directory(d, parent=directory.tag)
                self._display_files(directory.content_files, parent=directory.tag)
                self._directory_nodes[directory.tag] = is_open

    def _display_files(self, files: dict, parent: str):
        tag = f"{parent}-files table"
        if tag not in self._file_tables:
            self._file_tables.append(tag)
            with dpg.group(horizontal=True, parent=parent):
                dpg.add_spacer(width=22)
                with dpg.table(width=-1, tag=tag, header_row=False, policy=dpg.mvTable_SizingFixedFit):
                    dpg.add_table_column(label="Icon")
                    # dpg.add_table_column(label="File Name",  init_width_or_weight=320-depth*20)
                    dpg.add_table_column(label="File Name")
                    dpg.add_table_column(label="status")
        for file_tag in files.keys():
            self.update_file(files[file_tag], table=f"{parent}-files table")

    def update_file(self, file: File, table=None):
        if file.tag not in [f.tag for f in self._file_rows]:  # construct dpg items for this row
            dpg.add_table_row(tag=file.tag, parent=table)
            dpg.add_button(width=self._table_columns[0][1], parent=file.tag, tag=f"{file.tag}-c0")
            dpg.add_selectable(label=file.name, width=self._table_columns[1][1] - 52 - file.depth * 20, span_columns=True,
                               parent=file.tag, tag=f"{file.tag}-c1")
            dpg.add_button(width=self._table_columns[2][1], parent=file.tag, tag=f"{file.tag}-c2")
            self._file_rows.append(file)

        # Gather file info # TODO: Decide on file icon: Chk, input, log-freq-ground/excited, log-FC-up/down
        file_icon = Icons.file
        if file.type == FileType.GAUSSIAN_INPUT:
            file_icon = Icons.file_code

        status_icon = ""
        color = None
        if file.type == FileType.GAUSSIAN_LOG:  # TODO: These decisions should be made in the viewmodel.
            if file.properties[GaussianLog.STATUS] == GaussianLog.FINISHED:
                status_icon = Icons.check
                color = [0, 200, 0]
                with dpg.tooltip(f"{file.tag}-c2"):
                    dpg.add_text("Calculation finished successfully.")
            elif file.properties[GaussianLog.STATUS] == GaussianLog.NEGATIVE_FREQUENCY:
                status_icon = Icons.exclamation_triangle
                color = [200, 0, 0]
                with dpg.tooltip(f"{file.tag}-c2"):
                    dpg.add_text("Negative frequencies detected!")
            elif file.properties[GaussianLog.STATUS] == GaussianLog.ERROR:
                status_icon = Icons.x
                color = [200, 0, 0]
                with dpg.tooltip(f"{file.tag}-c2"):
                    dpg.add_text("Calculation terminated with an error!")
            else:
                status_icon = Icons.hourglass_start
                with dpg.tooltip(f"{file.tag}-c2"):
                    dpg.add_text("Calculation running...")

        # Insert file info
        self.icons.insert(f"{file.tag}-c0", file_icon, 16, solid=False)
        self.icons.insert(f"{file.tag}-c2", icon=status_icon, size=16, color=color)

        # TODO: Right-click menu on file.tag row: Open in os file explorer, open in [data analysis tab showing data read from file]

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
                dpg.add_theme_color(dpg.mvThemeCol_Text, [255, 255, 255, 200])
            with dpg.theme_component(dpg.mvButton):
                # dpg.add_theme_color(dpg.mvThemeCol_Text, [255, 255, 255, 150])
                dpg.add_theme_color(dpg.mvThemeCol_Button, [0, 0, 0, 0])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [0, 0, 0, 0])
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
