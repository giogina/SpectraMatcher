import sys

from viewmodels.main_viewmodel import MainViewModel
from viewmodels.menu_viewmodel import MenuViewModel
from views.main_menu import MainMenu
import dearpygui.dearpygui as dpg
import DearPyGui_Markdown as markdown
from screeninfo import get_monitors
import threading
import logging


class MainWindow():
    def __init__(self, path):
        self.result = 0
        self.logger = logging.getLogger(__name__)
        self.viewModel = MainViewModel(path)

        dpg.create_context()
        dpg.configure_app(auto_device=True)

        font_size = 18
        default_font_path = './fonts/Sansation_Regular.ttf'
        bold_font_path = './fonts/Sansation_Bold.ttf'
        italic_font_path = './fonts/Sansation_Italic.ttf'
        italic_bold_font_path = './fonts/Sansation_Bold_Italic.ttf'

        markdown.set_font_registry(dpg.add_font_registry())
        # You can also put your own fonts load function, this is needed
        # to add specific characters from the font file (e.g. Cyrillic)
        # An example of the use can be found in the example folder (example/font.py)
        # dpg_markdown.set_add_font_function({CUSTOM_ADD_FONT_FUNCTION})

        # Function to set fonts, the first time you call it,
        # you must specify the default font (default argument)
        # Return the default DPG font
        dpg_font = markdown.set_font(
            font_size=font_size,
            default=default_font_path,
            bold=bold_font_path,
            italic=italic_font_path,
            italic_bold=italic_bold_font_path
        )

        # Apply the created DPG font
        dpg.bind_font(dpg_font)

        # self.fonts = {}
        # self.normal_font = 16
        # with dpg.font_registry():
        #     self.fonts[self.normal_font] = dpg.add_font("./fonts/Sansation_Regular.ttf", self.normal_font)
        # self._load_fonts_async()
        # dpg.bind_font(self.fonts[self.normal_font])
        #
        # # Minimal example of working with the library
        # with dpg.window(label="Example", width=240, height=210):
        #     markdown.add_text("This is text\n"
        #                       "*This is italic text*\n"
        #                       "__This is bold text__\n"
        #                       "***This is bold italic text***\n"
        #                       "This is underline <u>text</u>")

        for icon_file in ["folder_outline"]:
            width, height, channels, icon = dpg.load_image(f"./resources/{icon_file}.png")
            with dpg.texture_registry(show=False):
                dpg.add_static_texture(width=width, height=height, default_value=icon, tag=icon_file)

        monitor = get_monitors()[0]
        dpg.create_viewport(title='SpectraMatcher',
                            width=monitor.width, height=monitor.height, x_pos=0, y_pos=0)

        with dpg.window(tag="main window", label="SpectraMatcher", no_resize=True):
            pass

        self.configure_theme()
        dpg.set_primary_window("main window", True)
        self.menu = MainMenu(self.viewModel)

        # need to initialize view model here to be able to show messages about the project
        self.viewModel.set_title_callback(callback=self.update_title)
        self.viewModel.set_message_callback(callback=self.menu.show_dialog)

    def configure_theme(self):
        palette = [[11, 11, 36],  # 0
                   [22, 22, 72],  # 1
                   [50, 50, 120],  # 2
                   [60, 60, 154],  # 3
                   [70, 70, 255],  # 4
                   [100, 100, 255],  # 5
                   [131, 131, 255],  # 6
                   [180, 180, 255],  # 7
                   ]  # todo: some kind of centralized color management, using settings to store palette
        with dpg.theme() as global_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 3, 6)
                dpg.add_theme_style(dpg.mvStyleVar_CellPadding, 0, 3)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 12, 5)
                dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0)
                dpg.add_theme_style(dpg.mvStyleVar_PopupBorderSize, 0)
                dpg.add_theme_color(dpg.mvThemeCol_MenuBarBg, palette[1])
                dpg.add_theme_color(dpg.mvThemeCol_PopupBg, palette[1])
                dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, palette[3]+[200])
                dpg.add_theme_color(dpg.mvThemeCol_Header, palette[3]+[100])
                dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, palette[3]+[200])
                dpg.add_theme_color(dpg.mvThemeCol_TableHeaderBg, palette[0]+[200])
                dpg.add_theme_color(dpg.mvThemeCol_WindowBg, palette[0])
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, palette[0])
                dpg.add_theme_color(dpg.mvThemeCol_TitleBg, palette[2])
                dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, palette[2])
                dpg.add_theme_color(dpg.mvThemeCol_TitleBgCollapsed, palette[2])
                dpg.add_theme_color(dpg.mvThemeCol_Button, palette[3])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, palette[6])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, palette[4])
                dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg, palette[1])
                dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab, palette[3])
                dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabActive, palette[3])
                dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabHovered, palette[3])
                dpg.add_theme_color(dpg.mvThemeCol_Separator, palette[7]+[100])
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, [60, 60, 154, 100])

        dpg.bind_theme(global_theme)

    def startup_callback(self):
        self.viewModel.load_project()

    def show(self):
        dpg.setup_dearpygui()
        dpg.set_frame_callback(1, self.startup_callback)
        dpg.set_exit_callback(self._on_viewport_close)
        dpg.show_viewport()
        dpg.start_dearpygui()
        dpg.destroy_context()
        return self.result

    def _load_fonts_async(self):
        fonts_thread = threading.Thread(target=self._load_fonts)
        fonts_thread.daemon = True
        fonts_thread.start()

    def _load_fonts(self):
        with dpg.font_registry():
            for i in range(5, 33):
                if not i in self.fonts.keys():
                    self.fonts[i] = dpg.add_font("./fonts/Sansation_Regular.ttf", i)

    def update_title(self, title):
        dpg.set_viewport_title(title)

    def _on_viewport_close(self):  # TODO: "save project?" dialog
        print("Viewport is closing. Exiting application.")
        self.viewModel.on_close()  # project lock cleanup
        dpg.stop_dearpygui()
        sys.exit()




