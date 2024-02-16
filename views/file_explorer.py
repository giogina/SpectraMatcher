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
        # [Label, start/current width, min width, default show value]
        # New columns: Just add here, then fill in display_file.
        # self._table_columns = [["Icons", 16, 16, True], ["File", 372, 200, True], ["Status", 60, 50, True]]
        self._table_columns = self.viewmodel.table_columns
        self._file_rows = []
        self._file_tables = []
        self._directory_nodes = {}
        self._last_delta = 0
        self._toggling_item = None
        self.filterable_extensions = [".log", ".gjf", ".com", ".chk", ".txt", ".*"]

        with dpg.theme() as self.invisible_button_theme:
            with dpg.theme_component(dpg.mvImageButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, [11, 11, 36, 0])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [11, 11, 36, 0])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [11, 11, 36, 0])
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, [11, 11, 36, 0])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [11, 11, 36, 0])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [11, 11, 36, 0])

        sep = []
        for i in range(24):
            sep.extend([0.8, 0.8, 1, 0.4])

        with dpg.texture_registry(show=False):
            dpg.add_static_texture(width=1, height=24, default_value=sep, tag="pixel")

        with dpg.item_handler_registry() as self.node_handlers:
            dpg.add_item_clicked_handler(callback=self._init_toggle_directory_node_labels)
        with dpg.item_handler_registry() as self.table_handlers:
            dpg.add_item_clicked_handler(callback=self._start_table_mouse_drag)
        with dpg.handler_registry() as self.mouse_handlers:
            dpg.add_mouse_release_handler(dpg.mvMouseButton_Left, callback=self._on_mouse_left_release)

        with dpg.child_window(tag="action bar", width=-1, height=32):
            with dpg.group(horizontal=True):
                self.icons.insert(dpg.add_button(height=32, width=32, callback=self._add_data_folder), Icons.folder_plus, size=16, tooltip="Import data folder")
                self.icons.insert(dpg.add_button(height=32, width=32, callback=self._add_data_files), Icons.file_plus, size=16, tooltip="Import data files")
                dpg.bind_item_theme(dpg.add_image_button("pixel", width=1, height=24), self.invisible_button_theme)
                self.icons.insert(dpg.add_button(height=32, width=32, tag="collapse all", callback=self._collapse_all, user_data=False), Icons.angle_double_up, size=16, tooltip="Collapse all folders")
                self.icons.insert(dpg.add_button(height=32, width=32, tag="expand all", callback=self._collapse_all, user_data=True), Icons.angle_double_down, size=16, tooltip="Expand all folders")
                dpg.bind_item_theme(dpg.add_image_button("pixel", width=1, height=24), self.invisible_button_theme)
                b = dpg.add_button(height=32, width=32)  # Todo: moving this to the right would be better window placement. Maybe put a search bar in the middle?
                self.icons.insert(b, Icons.filter, size=16, tooltip="Filter file types")
                self._setup_filter_popup(b)
                self.icons.insert(dpg.add_button(height=32, width=32, tag="file filter button"), Icons.eye, size=16, tooltip="Select visible columns")
                with dpg.popup("file filter button", tag="column selector popup", mousebutton=dpg.mvMouseButton_Left):
                    for i, column in enumerate(self._table_columns):
                        if i > 1:
                            dpg.add_checkbox(label=column[0], default_value=column[3], tag=f"file column {i}",
                                             callback=self._select_columns, user_data=i)

        with dpg.group(horizontal=True, tag="file table header"):
            for i in range(1, len(self._table_columns)):
                column = self._table_columns[i]
                dpg.add_button(label=column[0], width=column[1], height=24, tag=f"table header {i}", show=self._table_columns[i][3])
                dpg.bind_item_handler_registry(dpg.add_image_button("pixel", width=1, height=24, user_data=i, tag=f"sep-button-{i}", show=self._table_columns[i][3]), self.table_handlers)
            dpg.add_button(label="", width=-1, height=24)

        with dpg.child_window(tag="file explorer panel"):
            dpg.add_spacer(height=16)
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=1)
                dpg.add_group(horizontal=False, tag="file explorer group")

        self.configure_theme()

    def _setup_filter_popup(self, filter_button):
        with dpg.popup(filter_button, tag="file filter popup", mousebutton=dpg.mvMouseButton_Left, no_move=False):
            dpg.add_button(label="Filter file types", width=200)
            dpg.bind_item_theme(dpg.last_item(), self.invisible_button_theme)
            dpg.add_separator()
            for extension in self.filterable_extensions:
                dpg.add_checkbox(label=f"  *{extension}", default_value=True, tag=f"check {extension}",
                                 callback=self._update_filter)
            dpg.add_separator()
            dpg.add_checkbox(label="  Done", default_value=True, tag="check-done", callback=self._update_filter)
            dpg.add_checkbox(label="  Running", default_value=True, tag="check-running", callback=self._update_filter)
            dpg.add_checkbox(label="  Problematic", default_value=True, tag="check-problem",
                             callback=self._update_filter)
            dpg.add_separator()
            dpg.add_checkbox(label="  Frequency", default_value=True, tag="check-freq", callback=self._update_filter)
            dpg.add_checkbox(label="  Franck-Condon", default_value=True, tag="check-fc", callback=self._update_filter)
            dpg.add_checkbox(label="  Other .log", default_value=True, tag="check-other-log",
                             callback=self._update_filter)
            dpg.add_separator()
            dpg.add_checkbox(label="  Excitation", default_value=True, tag="check-excitation",
                             callback=self._update_filter)
            dpg.add_checkbox(label="  Emission", default_value=True, tag="check-emission", callback=self._update_filter)

    def _collapse_all(self, s, a, expand=False):
        print(expand)
        for directory in self._directory_nodes:
            dpg.set_value(directory, expand)
            self._toggle_directory_node_labels(directory)

    def _select_columns(self, s, show, i):
        self._table_columns[i][3] = show
        self.viewmodel.update_column_settings()
        dpg.configure_item(f"table header {i}", show=show)  # header
        dpg.configure_item(f"sep-button-{i}", show=show)
        for file in self._file_rows:                        # file rows
            dpg.configure_item(f"{file.tag}-c{i}", show=show)

    def _update_filter(self):
        for file in self._file_rows:
            if file.extension == ".log":
                status = file.properties.get(GaussianLog.STATUS, "")
                if not dpg.get_value(f'check {file.extension}'):
                    dpg.configure_item(file.tag, show=False)
                elif (status == GaussianLog.RUNNING and not dpg.get_value("check-running")) \
                            or (status == GaussianLog.FINISHED and not dpg.get_value("check-done")) \
                            or (status in [GaussianLog.ERROR, GaussianLog.NEGATIVE_FREQUENCY]
                                and not dpg.get_value("check-problem")):
                    dpg.configure_item(file.tag, show=False)
                elif file.type in [FileType.FREQ_GROUND, FileType.FREQ_EXCITED] and not dpg.get_value("check-freq") \
                    or (file.type in [FileType.FC_EXCITATION, FileType.FC_EMISSION] and not dpg.get_value("check-fc")) \
                    or (file.type == FileType.GAUSSIAN_LOG and not dpg.get_value("check-other-log")):
                    dpg.configure_item(file.tag, show=False)
                elif file.type in [FileType.FREQ_EXCITED, FileType.FC_EXCITATION] and not dpg.get_value("check-excitation") \
                    or (file.type in [FileType.FREQ_GROUND, FileType.FC_EMISSION] and not dpg.get_value("check-emission")):
                    dpg.configure_item(file.tag, show=False)
                else:
                    dpg.configure_item(file.tag, show=True)
            elif file.extension in self.filterable_extensions:
                dpg.configure_item(file.tag, show=dpg.get_value(f'check {file.extension}'))
            else:
                dpg.configure_item(file.tag, show=dpg.get_value(f'check .*'))

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
            self.viewmodel.update_column_settings()
        item_tag = self._toggling_item
        if item_tag:
            self._toggle_directory_node_labels(item_tag)
            self._toggling_item = None

    def _init_toggle_directory_node_labels(self, sender, app_data, handler_user_data):
        item_tag = dpg.get_item_user_data(app_data[1])
        self._toggling_item = item_tag

    def _toggle_directory_node_labels(self, item_tag):  # Currently simply makes sure the icon matches the target state.
        label = dpg.get_item_label(item_tag)
        is_open = dpg.get_value(item_tag)
        if is_open:
            label = u'\u00a4' + label[1:len(label)]
            dpg.configure_item(f"after_{item_tag}", height=0)
        else:
            label = u'\u00a3' + label[1:len(label)]
            dpg.configure_item(f"after_{item_tag}", height=self.item_padding)  # extra spacing after closed dir
        dpg.set_item_label(item_tag, label)
        self._directory_nodes[item_tag] = is_open
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
        if directory.tag not in self._directory_nodes.keys():
            dpg.add_spacer(height=self.item_padding, parent=parent)
            is_open = self.viewmodel.get_dir_state(directory.tag)
            print(f"Open? {directory.name, is_open}")
            icon = u"\u00a4  " if is_open else u"\u00a3  "
            with dpg.tree_node(label=icon + directory.name, parent=parent, tag=directory.tag, default_open=is_open, user_data=directory.tag):
                dpg.bind_item_handler_registry(directory.tag, self.node_handlers)
                dpg.add_spacer(height=self.item_padding)
                for dir_tag in directory.content_dirs.keys():
                    d = directory.content_dirs[dir_tag]
                    self._display_directory(d, parent=directory.tag)
                self._display_files(directory.content_files, parent=directory.tag)
            dpg.add_spacer(height=0 if is_open else self.item_padding, parent=parent, tag=f"after_{directory.tag}", show=not is_open)
            self._directory_nodes[directory.tag] = is_open

    def _display_files(self, files: dict, parent: str):
        tag = f"{parent}-files table"
        if tag not in self._file_tables:
            self._file_tables.append(tag)
            with dpg.group(horizontal=True, parent=parent):
                if parent == "file explorer group":  # Extra indent for top-level files
                    dpg.add_spacer(width=32)
                else:
                    dpg.add_spacer(width=22)
                with dpg.table(width=-1, tag=tag, header_row=False, policy=dpg.mvTable_SizingFixedFit):
                    for column in self._table_columns:
                        dpg.add_table_column(label=column[0])
        for file_tag in files.keys():
            self.update_file(files[file_tag], table=f"{parent}-files table")

    def update_file(self, file: File, table=None):  # TODO: Could also make table rows horizontal groups starting with a selectable. Possible issues: Clicks (for combo boxes?),drag container feasability.
        if file.tag not in [f.tag for f in self._file_rows]:  # construct dpg items for this row
            with dpg.table_row(tag=file.tag, parent=table):
                for i, column in enumerate(self._table_columns):
                    width = self._table_columns[i][1]
                    if i == 1:  # file name, adjust indent of following columns
                        width -= 52 + file.depth * 20
                        dpg.add_selectable(label=file.name, width=width, span_columns=True, tag=f"{file.tag}-c1")
                    else:
                        dpg.add_button(width=width, tag=f"{file.tag}-c{i}", show=self._table_columns[i][3])
            self._file_rows.append(file)

        # Gather file info # TODO: Decide on file icon: Chk, input, log-freq-ground/excited, log-FC-up/down
        file_icon = Icons.file
        if file.type == FileType.GAUSSIAN_INPUT:
            file_icon = Icons.file_code

        status_icon = ""
        color = None
        status_tooltip = None
        if file.extension == ".log":  # TODO: These decisions should be made in the viewmodel.
            status = file.properties.get(GaussianLog.STATUS)
            if status:
                if file.properties[GaussianLog.STATUS] == GaussianLog.FINISHED:
                    status_icon = Icons.check
                    color = [0, 200, 0]
                    status_tooltip = "Calculation finished successfully."
                elif file.properties[GaussianLog.STATUS] == GaussianLog.NEGATIVE_FREQUENCY:
                    status_icon = Icons.exclamation_triangle
                    color = [200, 0, 0]
                    status_tooltip = "Negative frequencies detected!"
                elif file.properties[GaussianLog.STATUS] == GaussianLog.ERROR:
                    status_icon = Icons.x
                    color = [200, 0, 0]
                    status_tooltip = "Calculation terminated with an error!"
                else:
                    status_icon = Icons.hourglass_start
                    status_tooltip = "Calculation running..."

        # Insert file info
        self.icons.insert(f"{file.tag}-c0", file_icon, 16, solid=False)
        self.icons.insert(f"{file.tag}-c2", icon=status_icon, size=16, color=color, tooltip=status_tooltip)

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
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, 0)
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, [200, 200, 255, 80])
                dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, [200, 200, 255, 50])

        dpg.bind_item_theme("action bar", action_bar_theme)

        # "collapse all"

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
