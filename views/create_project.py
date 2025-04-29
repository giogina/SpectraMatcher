import dearpygui.dearpygui as dpg
import os
from screeninfo import get_monitors
from models.settings_manager import SettingsManager
from models.project import Project
from utility.font_manager import FontManager
from utility.system_file_browser import *
from utility.icons import Icons
from utility.drop_receiver_window import DropReceiverWindow, initialize_dnd


class CreateProjectWindow:
    """Gather fundamental data for new project, create project file, and set its path."""
    def __init__(self, args=[]):
        self.result = None
        self.import_from = args
        self.projectPath = ""
        self.settings = SettingsManager()

        monitor = get_monitors()[0]
        dpg.create_context()
        dpg.configure_app(auto_device=True)

        fonts_path = FontManager.find_fonts_path()
        self.fonts = {}
        with dpg.font_registry() as font_reg:
            for i in [18, 24]:
                self.fonts[i] = dpg.add_font(os.path.join(fonts_path, "Sansation_Regular.ttf"), i)
            icons = Icons(font_reg, fonts_path)
        dpg.bind_font(self.fonts[18])
        close_button_theme, selectables_theme = self.adjust_theme()  # selectables_theme_2

        with dpg.handler_registry() as self.keyReg:
            dpg.add_key_press_handler(dpg.mvKey_Escape, callback=self.on_escape)

        self.path_changed = False
        self.path_from_file_dialog = False  # If true, doesn't re-confirm whether to overwrite a file.

        dash_width = 800
        dash_height = 550

        if len(self.import_from):
            name = os.path.basename(os.path.normpath(self.import_from[0]))
        else:
            name = ""

        with dpg.theme() as hover_drag_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Border, (150, 150, 255), category=dpg.mvThemeCat_Core)
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (25, 50, 75, 100), category=dpg.mvThemeCat_Core)

        dpg.create_viewport(title='Create new project - SpectraMatcher', width=dash_width, height=dash_height,
                            x_pos=int(monitor.width/2-dash_width/2), y_pos=int(monitor.height/2-dash_height/2))
        initialize_dnd()
        dpg.set_viewport_decorated(False)
        with dpg.window(label="Create New Project", width=dash_width, height=dash_height, tag="new project window"):
            icons.insert(dpg.add_button(pos=[dash_width - 36, 6], width=30, height=30, tag="close-button",
                                        callback=self.on_close), Icons.x, 16)
            dpg.bind_item_theme("close-button", close_button_theme)
            with dpg.child_window(label="inner", pos=[100, 60], width=dash_width-200, height=-1):
                dpg.add_text("Project name:", color=[131, 131, 255])
                dpg.add_input_text(width=-1, hint="New Project", default_value=name, callback=self.project_name_entered, tag="name input")
                dpg.bind_item_font("name input", self.fonts[24])
                dpg.add_spacer(height=16)
                dpg.add_text("Save as:", color=[131, 131, 255])
                with dpg.group(horizontal=True):
                    dpg.add_input_text(default_value=self.construct_savefile_name(), width=-53, tag="path input", callback=self.path_entered)
                    dpg.add_spacer(width=10)
                    with dpg.group(horizontal=False):
                        # dpg.add_spacer(height=1)
                        icons.insert(dpg.add_button(width=42, height=42, callback=self.on_save_as), Icons.open_folder, 16, solid=False)

                dpg.add_spacer(height=6)
                with dpg.group(horizontal=True):
                    dpg.add_text("Import data:", color=[131, 131, 255])

                with dpg.group(horizontal=True):
                    DropReceiverWindow(self.on_drop_callback, hover_drag_theme, selectables_theme).create(tag="selectables", height=94, width=-53)
                    self.selectables = []
                    for path in self.import_from:
                        s = dpg.add_selectable(label=path, parent="selectables")
                        self.selectables.append((path, s))
                    dpg.bind_item_theme("selectables", selectables_theme)

                    dpg.add_spacer(width=10)
                    with dpg.group(horizontal=False):
                        icons.insert(dpg.add_button(width=42, height=42, callback=self.on_add_data), Icons.folder_plus, 16)
                        dpg.add_spacer(height=10)
                        icons.insert(dpg.add_button(width=42, height=42, callback=self.delete_items), Icons.trash, 16)

                dpg.add_spacer(height=52)
                with dpg.group(horizontal=True):
                    dpg.add_spacer(width=dash_width-200-200)
                    dpg.add_button(label="OK", width=200, height=42, callback=self.on_ok)

            with dpg.window(label="Overwrite", modal=True, show=False, tag="modal_id", no_title_bar=True, no_resize=True,
                            width=300, height=200, pos=(int(dash_width/2-150), int(dash_height/2-100))):

                dpg.add_spacer(height=24)
                with dpg.group(horizontal=True):
                    dpg.add_spacer(width=60)
                    dpg.add_text("Project file already exists.")
                dpg.add_spacer(height=-10)
                with dpg.group(horizontal=True):
                    dpg.add_spacer(width=110)
                    dpg.add_text("Overwrite?")
                dpg.add_spacer(height=26)
                with dpg.group(horizontal=True):
                    dpg.add_spacer(width=22)
                    dpg.add_button(label="OK", width=100, callback=self.save_new_project)
                    dpg.add_spacer(width=50)
                    dpg.add_button(label="Cancel", width=100, callback=lambda: dpg.configure_item("modal_id", show=False))
        # dpg.show_style_editor()
        dpg.set_primary_window("new project window", True)

    def on_drop_callback(self, data, *args):
        if type(data) == list:
            for path in data:
                if os.path.exists(path):
                    self.import_from.append(path)
                    s = dpg.add_selectable(label=path, parent="selectables")
                    self.selectables.append((path, s))

    def adjust_theme(self, *args):
        with dpg.theme() as global_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4)
                dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 4)
                dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 0)
                dpg.add_theme_style(dpg.mvStyleVar_PopupBorderSize, 2)
                dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0)
                dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 0)
                dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 3, 3)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 12, 12)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 0, 0)
                dpg.add_theme_color(dpg.mvThemeCol_WindowBg, [11, 11, 36])
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, [11, 11, 36])
                dpg.add_theme_color(dpg.mvThemeCol_TitleBg, [11, 11, 36])
                dpg.add_theme_color(dpg.mvThemeCol_PopupBg, [11, 11, 36])
                dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, [11, 11, 36])
                dpg.add_theme_color(dpg.mvThemeCol_TitleBgCollapsed, [11, 11, 36])
                dpg.add_theme_color(dpg.mvThemeCol_Button, [60, 60, 154, 255])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [131, 131, 255])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [70, 70, 255])
                dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg, [22, 22, 72])
                dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab, [60, 60, 154])
                dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabActive, [60, 60, 154])
                dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabHovered, [60, 60, 154])
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, [60, 60, 154, 100])
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, 0)

        dpg.bind_theme(global_theme)

        with dpg.theme() as close_button_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Button, [60, 60, 154, 0])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [60, 60, 154])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [60, 60, 154])
                dpg.add_theme_color(dpg.mvThemeCol_Text, [131, 131, 255])
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 3, 0)

        with dpg.theme() as selectables_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 12, 12)
                dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 1)  # necessary to make window padding work
                dpg.add_theme_color(dpg.mvThemeCol_Border, [60, 60, 154, 20])
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, [60, 60, 154, 60])
                dpg.add_theme_color(dpg.mvThemeCol_Header, [60, 60, 154])
                dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, [60, 60, 154, 200])
                dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, [60, 60, 154, 160])
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 10, 4)
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, [60, 60, 154, 100])
                dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 4)

        return close_button_theme, selectables_theme

    def construct_savefile_name(self, *args):
        if dpg.get_value('name input'):
            name = dpg.get_value('name input')+".smp"
        else:
            name = "untitled.smp"
        directory = self.settings.get("projectsPath", os.getcwd())
        path = os.path.join(directory, name)
        return self.uniquify_path(path)

    def uniquify_path(self, path):
        unique_path = path
        i = 1
        while os.path.exists(unique_path):
            base, ext = os.path.splitext(path)
            unique_path = f"{base}({i}){ext}"
            i += 1
        return unique_path

    def delete_items(self, *args):
        remove = []
        for i, selectable in enumerate(self.selectables):
            if dpg.get_value(selectable[1]):
                self.import_from.remove(selectable[0])
                remove.append(selectable)
        for r in remove:
            self.selectables.remove(r)
            dpg.delete_item(r[1])

    def on_add_data(self, *args):
        file = data_dir_file_dialog(self.settings.get("dataPath", os.path.expanduser("~")))
        if file and len(file) and os.path.exists(file):
            self.import_from.append(file)
            s = dpg.add_selectable(label=file, parent="selectables")
            self.selectables.append((file, s))

    def on_save_as(self, *args):
        file = save_as_file_dialog(self.settings.get("projectsPath", "/"))
        if file and len(file):
            dpg.set_value("path input", file)
            self.path_changed = True
            self.path_from_file_dialog = True

    def project_name_entered(self, *args):
        if not self.path_changed:
            dpg.set_value("path input", self.construct_savefile_name())

    def path_entered(self, *args):
        self.path_changed = True
        self.path_from_file_dialog = False

    def on_ok(self, *args):
        path = os.path.abspath(dpg.get_value('path input'))
        if os.path.exists(path) and not self.path_from_file_dialog:
            dpg.configure_item("modal_id", show=True)
        else:
            self.save_new_project()

    def save_new_project(self, *args):
        dpg.configure_item("modal_id", show=False)
        path = dpg.get_value('path input')
        name = dpg.get_value("name input")
        if not len(name):
            name = "Untitled"
        new_dirs = []
        new_files = []
        for data in self.import_from:
            if type(data) == str:
                if os.path.exists(data):
                    if os.path.isdir(data):
                        new_dirs.append(data)
                    elif os.path.isfile(data):
                        new_files.append(data)
        Project(path).new(name=name, import_data_dirs=new_dirs, import_data_files=new_files)
        self.result = ('-open', path)
        dpg.stop_dearpygui()

    def on_escape(self, *args):
        self.result = None
        self.on_close()
        # if dpg.is_item_visible("modal_id"):
        #     dpg.configure_item("modal_id", show=False)

    def show(self):
        dpg.setup_dearpygui()
        dpg.set_viewport_small_icon("resources/SpectraMatcher.ico")
        dpg.set_viewport_large_icon("resources/SpectraMatcher.ico")
        dpg.show_viewport()
        dpg.start_dearpygui()
        dpg.destroy_context()
        return self.result

    def on_close(self, *args):
        dpg.stop_dearpygui()
