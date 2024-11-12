import os
import re
import subprocess
import dearpygui.dearpygui as dpg
import pyperclip

from models.state import State
from utility.font_manager import FontManager
from viewmodels.data_files_viewmodel import DataFileViewModel
from models.data_file_manager import GaussianLog, FileType, File, Directory
from utility.icons import Icons
from utility.drop_receiver_window import DropReceiverWindow, initialize_dnd
from utility.custom_dpg_items import CustomDpgItems
from utility.item_themes import ItemThemes

_file_icons = {
    FileType.GAUSSIAN_INPUT: Icons.file_code,
    FileType.OTHER: Icons.file
}


_file_icon_textures = {
    FileType.GAUSSIAN_CHECKPOINT: "resources/chk-file-16.png",
    FileType.EXPERIMENT_EMISSION: "resources/laser-2-16.png",
    FileType.EXPERIMENT_EXCITATION: "resources/laser-2-16.png",
    FileType.FC_EMISSION: "resources/FC-down-2-16.png",
    FileType.FC_EXCITATION: "resources/FC-up-2-16.png",
    FileType.FREQ_GROUND: "resources/file-freq-16.png",
    FileType.FREQ_EXCITED: "resources/file-freq-16.png",
    FileType.FREQ_GROUND_ANHARM: "resources/file-freq-16.png",
    FileType.FREQ_EXCITED_ANHARM: "resources/file-freq-16.png",
}

_file_icon_colors = {
    FileType.GAUSSIAN_CHECKPOINT: [255, 255, 255, 180],
    FileType.EXPERIMENT_EMISSION: [255, 180, 180, 255],
    FileType.EXPERIMENT_EXCITATION: [180, 255, 180, 255],
    FileType.FC_EMISSION: [255, 180, 180, 255],
    FileType.FC_EXCITATION: [180, 255, 180, 255],
    FileType.FREQ_GROUND: [180, 180, 255, 255],
    FileType.FREQ_EXCITED: [180, 180, 255, 255],
    FileType.FREQ_GROUND_ANHARM: [200, 160, 255, 255],
    FileType.FREQ_EXCITED_ANHARM: [200, 160, 255, 255]
}


def _get_icon_texture(tag):
    if tag in _file_icon_textures.keys():
        color = [c/255. for c in _file_icon_colors.get(tag, [255, 255, 255, 180])]
        file_name = _file_icon_textures.get(tag)
        base_path = os.path.dirname(FontManager.find_fonts_path())
        texture_path = os.path.join(base_path, file_name).replace('\\', '/')
        width, height, channels, data = dpg.load_image(texture_path)
        tex = []
        for i in range(len(data)):
            tex.append(data[i] * color[i % 4])
        return width, height, tex
    else:
        return 1, 1, [0, 0, 0, 0]


_status_icons = {
    GaussianLog.FINISHED: {"icon": Icons.check, "color": [0, 200, 0], "tooltip": "Calculation finished successfully."},
    GaussianLog.ERROR: {"icon": Icons.x, "color": [200, 0, 0], "tooltip": "Calculation terminated with an error!"},
    GaussianLog.NEGATIVE_FREQUENCY: {"icon": Icons.exclamation_triangle, "color": [200, 0, 0], "tooltip": "Negative frequencies detected!"},
    GaussianLog.RUNNING: {"icon": Icons.hourglass_start, "color": None, "tooltip": "Calculation running..."},
    "None": {"icon": "", "color": None, "tooltip": None},
}


class FileExplorer:
    file_type_color_theme = {}  # Themes for the texts coming after the icons; filetype: theme.

    def __init__(self, viewmodel: DataFileViewModel):
        self.viewmodel = viewmodel
        self.viewmodel.set_callback("populate file explorer", self.update_file_explorer)
        self.viewmodel.set_callback("reset file explorer", self.reset_file_explorer)
        self.viewmodel.set_callback("update file", self.update_file)
        self.viewmodel.set_callback("update directory ignore status", self.update_dir_ignored_status)
        self.icons = Icons()
        self.cdi = CustomDpgItems()
        self.item_padding = 3
        self._resizing_column = None  # column number currently being resized
        self._dragging_button = None  # tag of resizer button being dragged
        # New columns: Just add in settings manager, then fill in display_file.
        self._table_columns = self.viewmodel.table_columns
        self._file_rows = []
        self._file_tables = []
        self._directory_nodes = {}
        self._last_delta = 0
        self.filterable_extensions = [".log", ".gjf", ".com", ".chk", ".txt", ".*"]
        initialize_dnd()
        with dpg.texture_registry(show=False):
            for tag in _file_icon_textures.keys():
                width, height, data = _get_icon_texture(tag)
                dpg.add_static_texture(width=width, height=height, default_value=data, tag=f"{tag}-{width}")

        with dpg.theme() as hover_drag_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Border, (150, 150, 255), category=dpg.mvThemeCat_Core)
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (25, 50, 75, 100), category=dpg.mvThemeCat_Core)

        with dpg.theme() as non_hover_drag_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (25, 50, 75, 0), category=dpg.mvThemeCat_Core)

        with dpg.theme() as self.ignored_directory_theme:
            with dpg.theme_component(dpg.mvTreeNode):
                dpg.add_theme_color(dpg.mvThemeCol_Text, [255, 255, 255, 100])

        with dpg.theme() as self.un_ignored_directory_theme:
            with dpg.theme_component(dpg.mvTreeNode):
                dpg.add_theme_color(dpg.mvThemeCol_Text, [255, 255, 255, 200])

        with dpg.theme() as self.ignored_file_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Text, [255, 255, 255, 100])
            with dpg.theme_component(dpg.mvSelectable):
                dpg.add_theme_color(dpg.mvThemeCol_Text, [255, 255, 255, 100])

        with dpg.theme() as self.un_ignored_file_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Text, [255, 255, 255, 200])
            with dpg.theme_component(dpg.mvSelectable):
                dpg.add_theme_color(dpg.mvThemeCol_Text, [255, 255, 255, 200])

        self.file_explorer_theme = None

        with dpg.item_handler_registry() as self.table_handlers:
            dpg.add_item_clicked_handler(callback=self._start_table_mouse_drag)
        with dpg.handler_registry() as self.mouse_handlers:
            dpg.add_mouse_release_handler(dpg.mvMouseButton_Left, callback=self._on_mouse_left_release)

        with dpg.child_window(tag="action bar", width=-1, height=32):
            with dpg.table(header_row=False):
                dpg.add_table_column(width_stretch=True)
                dpg.add_table_column(width_fixed=True, init_width_or_weight=220)
                with dpg.table_row():
                    dpg.add_spacer()
                    with dpg.group(horizontal=True):
                        self.icons.insert(dpg.add_button(height=32, width=32, callback=self._add_data_folder), Icons.folder_plus, size=16, tooltip="Import data folder")
                        self.icons.insert(dpg.add_button(height=32, width=32, callback=self._add_data_files), Icons.file_plus, size=16, tooltip="Import data files")
                        self.cdi.insert_separator_button(height=32)
                        self.icons.insert(dpg.add_button(height=32, width=32, tag="collapse all", callback=self._collapse_all, user_data=False), Icons.angle_double_up, size=16, tooltip="Collapse all folders")
                        self.icons.insert(dpg.add_button(height=32, width=32, tag="expand all", callback=self._collapse_all, user_data=True), Icons.angle_double_down, size=16, tooltip="Expand all folders")
                        self.cdi.insert_separator_button(height=32)
                        b = dpg.add_button(height=32, width=32)
                        self.icons.insert(b, Icons.filter, size=16, tooltip="Filter file types")
                        self._setup_filter_popup(b)
                        self.icons.insert(dpg.add_button(height=32, width=32, tag="file filter button"), Icons.eye, size=16, tooltip="Select visible columns")
                        with dpg.popup("file filter button", tag="column selector popup", mousebutton=dpg.mvMouseButton_Left):
                            for i, column in enumerate(self._table_columns):
                                if i > 1:
                                    dpg.add_checkbox(label=column[0], default_value=column[3], tag=f"file column {i}", callback=self._select_columns, user_data=i)

        with dpg.group(horizontal=True, tag="file table header"):
            nr_prev_invisible = 0
            for i in range(1, len(self._table_columns)):
                column = self._table_columns[i]
                dpg.add_button(label=column[0], width=column[1]+nr_prev_invisible*2, height=24, tag=f"table header {i}", show=self._table_columns[i][3])
                dpg.bind_item_handler_registry(dpg.add_image_button("pixel", width=1, height=24, user_data=i, tag=f"sep-button-{i}", show=self._table_columns[i][3]), self.table_handlers)
                if column[3]:
                    nr_prev_invisible = 0
                else:
                    nr_prev_invisible += 1
            dpg.add_button(label="", width=-1, height=24)

        with dpg.child_window(tag="file explorer panel", horizontal_scrollbar=True):
            DropReceiverWindow(self.on_drop_files, hover_drag_theme, non_hover_drag_theme).create(tag="drop window")
            dpg.add_spacer(height=16, parent="drop window")
            with dpg.group(horizontal=True, parent="drop window"):
                dpg.add_spacer(width=1)
                dpg.add_group(horizontal=False, tag="file explorer group")

        self.configure_theme()

    def on_drop_files(self, data, *args):
        if type(data) == list:
            self.viewmodel.add_directory_or_file(data)

    def _setup_filter_popup(self, filter_button, *args):
        with dpg.popup(filter_button, tag="file filter popup", mousebutton=dpg.mvMouseButton_Left, no_move=False):
            dpg.add_button(label="Filter file types", width=200)
            dpg.bind_item_theme(dpg.last_item(), ItemThemes.invisible_button_theme())
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

    def _collapse_folder(self, directory, expand, *args):
        dpg.set_value(directory.tag, expand)
        self._toggle_directory_node_labels(directory.tag)
        for subdir in directory.content_dirs.values():
            self._collapse_folder(subdir, expand)

    def _remove_file(self, s, a, u, *args):
        self.viewmodel.remove_file(u)
        dpg.delete_item(u)
        for file in self._file_rows:
            if file.tag == u:
                self._file_rows.remove(file)

    def _setup_folder_right_click_menu(self, directory):
        tag = directory.tag
        if dpg.does_item_exist(f"{tag}-rightclick-menu"):
            dpg.delete_item(f"{tag}-rightclick-menu")
        with dpg.popup(tag, tag=f"{tag}-rightclick-menu"):
            dpg.add_selectable(label="Collapse", user_data=(directory, False), callback=lambda s, a, u: self._collapse_folder(*u))
            dpg.add_selectable(label="Expand", user_data=(directory, True), callback=lambda s, a, u: self._collapse_folder(*u))
            dpg.add_spacer(height=2)
            dpg.add_separator()
            dpg.add_spacer(height=2)

            if directory.parent_directory is None:
                dpg.add_selectable(label="Remove", user_data=directory, callback=lambda s, a, u: self.viewmodel.remove_directory(u))

            dpg.add_selectable(label="Un-ignore", tag=f"include-{tag}", user_data=directory, callback=lambda s, a, u: self.viewmodel.ignore_directory(u, False))
            dpg.add_selectable(label="Ignore", tag=f"exclude-{tag}", user_data=directory, callback=lambda s, a, u: self.viewmodel.ignore_directory(u, True))
            if self.viewmodel.is_ignored(tag):
                dpg.hide_item(f"exclude-{tag}")
            else:
                dpg.hide_item(f"include-{tag}")
            dpg.add_spacer(height=2)
            dpg.add_separator()
            dpg.add_spacer(height=2)
            dpg.add_selectable(label="Open in Explorer ", user_data=directory.path.replace("/", "\\"),
                               callback=lambda s, a, u: subprocess.Popen(f'explorer "{u}"'))

    def _setup_file_right_click_menu(self, file: File):
        if file.tag not in [f.tag for f in self._file_rows]:
            dpg.delete_item(f"{file.tag}-c1")
        with dpg.popup(f"{file.tag}-c1", min_size=(300, 40)):

            if file.type not in (FileType.OTHER, FileType.GAUSSIAN_CHECKPOINT, FileType.GAUSSIAN_INPUT):
                if self.viewmodel.is_ignored(file.tag):
                    dpg.add_selectable(label="Un-ignore", user_data=file.tag, callback=lambda s, a, u: self.viewmodel.ignore_tag(u, False))
                else:
                    dpg.add_selectable(label="Ignore", user_data=file.tag, callback=lambda s, a, u: self.viewmodel.ignore_tag(u, True))
            if file.type == FileType.EXPERIMENT_EMISSION:
                dpg.add_selectable(label="Mark as Excitation spectrum", user_data=file.tag, callback=lambda s, a, u: self.viewmodel.mark_file_as_excitation(u, True))
                dpg.add_spacer(height=2)
                dpg.add_separator()
                dpg.add_spacer(height=2)
            if file.type == FileType.EXPERIMENT_EXCITATION:
                dpg.add_selectable(label="Mark as Emission spectrum", user_data=file.tag, callback=lambda s, a, u: self.viewmodel.mark_file_as_excitation(u, False))
                dpg.add_spacer(height=2)
                dpg.add_separator()
                dpg.add_spacer(height=2)
            if file.type in (FileType.FREQ_GROUND, FileType.EXPERIMENT_EXCITATION, FileType.EXPERIMENT_EMISSION) or file.type in FileType.LOG_TYPES:
                add_sep = True
                with dpg.menu(label="Add to project..."):
                    if file.type == FileType.FREQ_GROUND:
                        dpg.add_menu_item(label="   ground state", user_data=State.state_list[0], callback=lambda: self.viewmodel.import_state_file(file, State.state_list[0]))
                    elif file.type in FileType.LOG_TYPES:
                        for state in State.state_list[1:]:
                            dpg.add_menu_item(label=f"   {state.name}", user_data=state, callback=lambda: self.viewmodel.import_state_file(file, state))
                    elif file.type in (FileType.EXPERIMENT_EXCITATION, FileType.EXPERIMENT_EMISSION):
                        dpg.add_menu_item(label="   experimental spectra", callback=lambda: self.viewmodel.import_experimental_file(file))
            else:
                add_sep = False
            if file.parent_directory is None:
                if add_sep:
                    dpg.add_spacer(height=2)
                    dpg.add_separator()
                    dpg.add_spacer(height=2)
                add_sep = True
                dpg.add_selectable(label="Remove", user_data=file.tag, callback=self._remove_file)
            if file.type in FileType.LOG_TYPES and (file.geometry is not None) or (file.initial_geom is not None) or (file.final_geom is not None):
                if add_sep:
                    dpg.add_spacer(height=2)
                    dpg.add_separator()
                    dpg.add_spacer(height=2)
                add_sep = True
                if file.type in (FileType.FC_EMISSION, FileType.FC_EXCITATION):
                    if file.initial_geom is not None:
                        dpg.add_selectable(label="Copy initial geometry to clipboard ", user_data=file.initial_geom, callback=lambda s, a, u: pyperclip.copy(u.get_gaussian_geometry()))
                    if file.final_geom is not None:
                        dpg.add_selectable(label="Copy final geometry to clipboard ", user_data=file.final_geom, callback=lambda s, a, u: pyperclip.copy(u.get_gaussian_geometry()))
                else:
                    if file.geometry is not None:
                        dpg.add_selectable(label="Copy last geometry to clipboard ", user_data=file.geometry, callback=lambda s, a, u: pyperclip.copy(u.get_gaussian_geometry()))
                if not file.is_human_readable:
                    dpg.add_selectable(label="Make readable", user_data=file.tag, callback=lambda s, a, u: self.viewmodel.make_file_readable(u))
            if file.type == FileType.GAUSSIAN_INPUT and file.geometry is not None:
                dpg.add_selectable(label="Copy geometry to clipboard ", user_data=file.geometry, callback=lambda s, a, u: pyperclip.copy(u.get_gaussian_geometry()))
            # if file.properties.get(GaussianLog.STATUS, "") == GaussianLog.NEGATIVE_FREQUENCY:
            #     dpg.add_selectable(label="Copy adjusted geometry for re-optimization", user_data=file.path)
            if add_sep:
                dpg.add_spacer(height=2)
                dpg.add_separator()
                dpg.add_spacer(height=2)
            dpg.add_selectable(label="Show in Explorer ", user_data=file.path.replace("/", "\\"),
                               callback=lambda s, a, u: subprocess.Popen(f'explorer /select,"{u}"'))

    def _collapse_all(self, s, a, expand=False, *args):
        for directory in self._directory_nodes:
            dpg.set_value(directory, expand)
            self._toggle_directory_node_labels(directory)

    def _select_columns(self, s, show, i, *args):
        self._table_columns[i][3] = show
        self.viewmodel.update_column_settings()
        dpg.configure_item(f"table header {i}", show=show)  # header
        dpg.configure_item(f"sep-button-{i}", show=show)
        if not i == len(self._table_columns) - 1:
            self._resizing_column = i+1
        self._tables_resize()
        for file in self._file_rows:                        # file rows
            dpg.configure_item(f"{file.tag}-c{i}", show=show)

    def _update_filter(self, *args):
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
                elif file.type in [FileType.FREQ_GROUND, FileType.FREQ_EXCITED, FileType.FREQ_GROUND_ANHARM, FileType.FREQ_EXCITED_ANHARM] and not dpg.get_value("check-freq") \
                    or (file.type in [FileType.FC_EXCITATION, FileType.FC_EMISSION] and not dpg.get_value("check-fc")) \
                    or (file.type == FileType.GAUSSIAN_LOG and not dpg.get_value("check-other-log")):
                    dpg.configure_item(file.tag, show=False)
                elif file.type in [FileType.FREQ_EXCITED, FileType.FC_EXCITATION, FileType.FREQ_EXCITED_ANHARM] and not dpg.get_value("check-excitation") \
                    or (file.type in [FileType.FREQ_GROUND, FileType.FC_EMISSION, FileType.FREQ_GROUND_ANHARM] and not dpg.get_value("check-emission")):
                    dpg.configure_item(file.tag, show=False)
                else:
                    dpg.configure_item(file.tag, show=True)
            elif file.extension in self.filterable_extensions:
                dpg.configure_item(file.tag, show=dpg.get_value(f'check {file.extension}'))
            else:
                dpg.configure_item(file.tag, show=dpg.get_value(f'check .*'))

    def _tables_resize(self, *args):
        column = self._resizing_column
        if column:
            delta = dpg.get_mouse_drag_delta()[0]
            if delta != self._last_delta:  # Necessary to avoid bug where delta is last drag's delta when it should be 0
                item = f"table header {column}"
                header_width = max(self._table_columns[column][2], self._table_columns[column][1] + delta)
                nr_prev_invisible = 0
                for c in range(column-1, 2, -1):
                    if self._table_columns[c][3]:
                        break
                    else:
                        nr_prev_invisible += 1
                dpg.set_item_width(item, header_width + 2*nr_prev_invisible)
                for file in self._file_rows:
                    item = f"{file.tag}-c{column}"
                    if column == 1:
                        width = header_width - 52 - file.depth * 20
                        if file.parent_directory is None:
                            width -= 10  # Make up for extra spacing in front
                    else:
                        width = header_width
                    dpg.set_item_width(item, width+6)  # table button extra width adjustment
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

    def _on_mouse_left_release(self, *args):
        column = self._resizing_column
        if column:
            # arrow_cursor = ctypes.windll.user32.LoadCursorW(0, 32512)
            # ctypes.windll.user32.SetCursor(arrow_cursor)
            self._table_columns[column][1] = dpg.get_item_width(f"table header {column}")
            self._resizing_column = None  # Reset
            self.viewmodel.update_column_settings()

        for node, is_open in self._directory_nodes.items():
            if is_open != dpg.get_value(node):
                self._toggle_directory_node_labels(node)

    def _toggle_directory_node_labels(self, item_tag, *args):  # Currently simply makes sure the icon matches the target state.
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

    def _add_data_folder(self, *args):
        self.viewmodel.inquire_open_data_directory()

    def _add_data_files(self, *args):
        self.viewmodel.inquire_open_data_files()

    def reset_file_explorer(self, directories, files):
        self._file_rows = []
        self._file_tables = []
        self._directory_nodes = {}
        dpg.delete_item("file explorer group", children_only=True)
        self.update_file_explorer(directories, files)

    def update_file_explorer(self, directories, files):
        for directory_tag, directory in directories.items():
            self._display_directory(directory, parent="file explorer group")
        self._display_files(files, parent="file explorer group")

    def _display_directory(self, directory: Directory, parent: str):
        if directory.tag not in self._directory_nodes.keys():
            dpg.add_spacer(height=self.item_padding, parent=parent)
            is_open = self.viewmodel.get_dir_state(directory.tag)
            icon = u"\u00a4  " if is_open else u"\u00a3  "
            with dpg.tree_node(label=icon + directory.name, parent=parent, tag=directory.tag, default_open=is_open, user_data=directory.tag):
                dpg.add_spacer(height=self.item_padding)
                for dir_tag in directory.content_dirs.keys():
                    d = directory.content_dirs[dir_tag]
                    self._display_directory(d, parent=directory.tag)
                self._display_files(directory.content_files, parent=directory.tag)
                self._setup_folder_right_click_menu(directory)
            dpg.add_spacer(height=0 if is_open else self.item_padding, parent=parent, tag=f"after_{directory.tag}", show=not is_open)
            self._directory_nodes[directory.tag] = is_open
        self.update_dir_ignored_status(directory.tag)

    def _display_files(self, files: dict, parent: str):
        tag = f"{parent}-files table"
        if tag not in self._file_tables:
            self._file_tables.append(tag)
            with dpg.group(horizontal=True, parent=parent):
                if parent == "file explorer group":  # Extra indent for top-level files
                    dpg.add_spacer(width=32)
                else:
                    dpg.add_spacer(width=22)
                with dpg.table(width=-1, tag=tag, header_row=False, policy=dpg.mvTable_SizingFixedFit, no_pad_innerX=True, no_pad_outerX=True):
                    for column in self._table_columns:
                        dpg.add_table_column(label=column[0])
        for file_tag in files.keys():
            self.update_file(files[file_tag], table=f"{parent}-files table")

    def update_dir_ignored_status(self, directory_tag):
        if directory_tag in self._directory_nodes.keys():
            if self.viewmodel.is_ignored(directory_tag):
                dpg.show_item(f"include-{directory_tag}")
                dpg.hide_item(f"exclude-{directory_tag}")
                dpg.bind_item_theme(directory_tag, theme=self.ignored_directory_theme)
            else:
                dpg.hide_item(f"include-{directory_tag}")
                dpg.show_item(f"exclude-{directory_tag}")
                dpg.bind_item_theme(directory_tag, theme=self.un_ignored_directory_theme)

    def update_file(self, file: File, table=None):
        # print(f"update file: {file.path}, {file.routing_info}")
        if file.tag not in [f.tag for f in self._file_rows]:  # construct dpg items for this row
            if table is None:
                # print(f"Delay displaying file: {file.path}")
                return  # Too early, the item to be updated hasn't been made yet.
            # print(f"Constructing table row for {file.tag}")
            with dpg.table_row(tag=file.tag, parent=table):
                for i, column in enumerate(self._table_columns):
                    width = self._table_columns[i][1] + 6   # table button extra width adjustment
                    if i == 0:  # Icon, can be icon or image button
                        with dpg.group(horizontal=True):
                            dpg.add_button(width=width, tag=f"{file.tag}-c{i}")
                            dpg.add_image_button("FC excitation-16", width=width, tag=f"{file.tag}-c{i}-img", show=False)
                            dpg.add_spacer(width=6)
                    elif i == 1:  # file name, adjust indent of following columns
                        width -= 52 + file.depth * 20
                        if file.parent_directory is None:
                            width -= 10  # Make up for extra spacing in front
                        dpg.add_selectable(label=file.name, width=width, span_columns=True, tag=f"{file.tag}-c1")
                    else:
                        dpg.add_button(width=width, tag=f"{file.tag}-c{i}", show=self._table_columns[i][3])
            self._file_rows.append(file)

        # Gather & insert file info
        if self.viewmodel.is_ignored(file.tag):
            dpg.bind_item_theme(f"{file.tag}-c{0}", self.ignored_file_theme)
            dpg.bind_item_theme(f"{file.tag}-c{1}", self.ignored_file_theme)
        else:
            dpg.bind_item_theme(f"{file.tag}-c{0}", self.un_ignored_file_theme)
            dpg.bind_item_theme(f"{file.tag}-c{1}", self.un_ignored_file_theme)
        if file.type in _file_icon_textures.keys() and not self.viewmodel.is_ignored(file.tag):
            dpg.configure_item(f"{file.tag}-c0", width=0, show=False)
            dpg.configure_item(f"{file.tag}-c0-img", width=self._table_columns[0][1], show=True)
            file_icon_texture_tag = f"{file.type}-{16}"
            dpg.configure_item(f"{file.tag}-c0-img", texture_tag=file_icon_texture_tag)
            dpg.bind_item_theme(f"{file.tag}-c1", self.file_type_color_theme[file.type])
            if type(file.properties) == dict and file.properties.get(GaussianLog.STATUS) == GaussianLog.FINISHED:
                with dpg.drag_payload(parent=f"{file.tag}-c{1}", drag_data=file, payload_type="Ground file" if file.type==FileType.FREQ_GROUND else "Excited file"):
                    dpg.add_text(file.path)
            if file.type in (FileType.EXPERIMENT_EMISSION, FileType.EXPERIMENT_EXCITATION):
                with dpg.drag_payload(parent=f"{file.tag}-c{1}", drag_data=file, payload_type="Experiment file"):
                    dpg.add_text(file.path)
        else:
            dpg.configure_item(f"{file.tag}-c0-img", width=0, show=False)
            dpg.configure_item(f"{file.tag}-c0", width=self._table_columns[0][1], show=True)
            file_icon = Icons.file
            if file.type == FileType.GAUSSIAN_INPUT:
                file_icon = Icons.file_code
            self.icons.insert(f"{file.tag}-c0", file_icon, 16, solid=False)

        status = file.properties.get(GaussianLog.STATUS, "None")
        status_icon = _status_icons.get(status)
        tooltip = status_icon["tooltip"]
        if status == GaussianLog.ERROR and file.error is not None:
            tooltip += file.error
        self.icons.insert(f"{file.tag}-c2", icon=status_icon["icon"], size=16,
                          color=status_icon["color"], tooltip=tooltip)

        if file.routing_info is not None:
            self._setup_file_right_click_menu(file)
            td = file.routing_info.get('td')
            if td is not None:
                dpg.set_item_label(f"{file.tag}-c3", f"{td[0]}/{td[1]}")
            elif file.type == FileType.FREQ_GROUND:
                dpg.set_item_label(f"{file.tag}-c3", "ground")

            jobs = ' '.join(file.routing_info.get('jobs', ''))
            job_label = ' '.join([job.split('=')[0] for job in file.routing_info.get('jobs', [])])
            if file.type in (FileType.FC_EXCITATION, FileType.FC_EMISSION, FileType.GAUSSIAN_INPUT):
                if re.search(r"(?<![a-zA-Z])(fc)", jobs):
                    if re.search(r"(?<![a-zA-Z])(fcht)", jobs):
                        job_label = "FCHT"
                    else:
                        job_label = "FC"
                elif re.search(r"(?<![a-zA-Z])(ht)", jobs):
                    job_label = "HT"
            dpg.set_item_label(f"{file.tag}-c4", job_label)
            if dpg.does_item_exist(f"{file.tag}-c4 tooltip"):
                dpg.delete_item(f"{file.tag}-c4 tooltip")
            with dpg.tooltip(f"{file.tag}-c4", tag=f"{file.tag}-c4 tooltip", delay=0.3):
                dpg.add_text(f" {jobs} ")

            if file.routing_info.get('loth') is not None:
                dpg.set_item_label(f"{file.tag}-c5", f"{file.routing_info.get('loth', '')}")

                dpg.set_item_label(f"{file.tag}-c6", f"{' '.join(file.routing_info.get('keywords', ''))}")

            dpg.set_item_label(f"{file.tag}-c7", file.molecular_formula)

            if file.multiplicity is not None:
                dpg.set_item_label(f"{file.tag}-c8", f"{file.multiplicity}")

        if file.modes is not None:
            dpg.set_item_label(f"{file.tag}-c10", f"{str([int(wn) for wn in file.modes.get_wavenumbers(5)]).strip('[]').replace(' ', '  ')}, ...")

        if file.spectrum is not None:
            dpg.set_item_label(f"{file.tag}-c9", f"{int(file.spectrum.zero_zero_transition_energy)}")
            dpg.set_item_label(f"{file.tag}-c10", f"{str([int(wn) for wn in file.spectrum.get_wavenumbers(5)]).strip('[]').replace(' ', '  ')}, ...")

    def configure_theme(self):
        with dpg.theme() as file_explorer_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 8, 0)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 0, 0)
                dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 0)
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, [200, 200, 255, 30])
                dpg.add_theme_color(dpg.mvThemeCol_Text, [255, 255, 255, 200])
                dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, [0, 0, 0, 0])
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, [0, 0, 0, 0])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [0, 0, 0, 0])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [0, 0, 0, 0])
                dpg.add_theme_style(dpg.mvStyleVar_ButtonTextAlign, 0.5, 0.5)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, 0)
            with dpg.theme_component(dpg.mvImageButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, [0, 0, 0, 0])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [0, 0, 0, 0])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [0, 0, 0, 0])
                dpg.add_theme_style(dpg.mvStyleVar_ButtonTextAlign, 0.5, 0.5)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, 0)
            with dpg.theme_component(dpg.mvTable):
                dpg.add_theme_style(dpg.mvStyleVar_CellPadding, 0, self.item_padding)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, self.item_padding)
                dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, [0, 0, 0, 0])

        dpg.bind_item_theme("file explorer panel", file_explorer_theme)
        self.file_explorer_theme = file_explorer_theme

        dpg.bind_item_theme("action bar", ItemThemes.action_bar_theme())

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

        for tag, color in _file_icon_colors.items():
            with dpg.theme() as self.file_type_color_theme[tag]:
                with dpg.theme_component(dpg.mvAll):
                    dpg.add_theme_color(dpg.mvThemeCol_Text, color)
                    dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, [60, 60, 154, 200])
