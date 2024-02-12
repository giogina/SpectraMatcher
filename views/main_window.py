import sys
from viewmodels.main_viewmodel import MainViewModel
from views.main_menu import MainMenu
from views.file_explorer import FileExplorer
from utility.icons import Icons
import dearpygui.dearpygui as dpg
from screeninfo import get_monitors
import threading
import logging


class MainWindow:
    def __init__(self, path):
        self.result = 0
        self.logger = logging.getLogger(__name__)
        self.viewModel = MainViewModel(path)

        dpg.create_context()
        dpg.configure_app(auto_device=True)

        self.fonts = {}
        self.normal_font = 18
        with dpg.font_registry() as font_reg:
            # ! Open/Closed folder icons have been added to this font !
            # Don't change it, or you will get currency signs instead. (Or add folder icons as \u00a3 and \u00a4)
            self.fonts[self.normal_font] = dpg.add_font("./fonts/SansationRegular.ttf", self.normal_font)
            icons = Icons().set_font_registry(font_reg)
        # self._load_fonts_async()  # todo: Still needed or throw out? Or dynamically load fonts using font_reg?
        dpg.bind_font(self.fonts[self.normal_font])

        # with dpg.window(label="Test", width=240, height=210) as testwindow:
        #     with dpg.tree_node(label=u"\u00a4  Open folder!"):
        #         with dpg.tree_node(label=u"\u00a3  Closed folder!"):
        #             dpg.add_text("HAH!")
        #     icons.insert(dpg.add_button(), icons.open_folder, 24)
        #     icons.insert(dpg.add_button(), icons.star, 24)

        monitor = get_monitors()[0]
        dpg.create_viewport(title='SpectraMatcher',
                            width=monitor.width, height=monitor.height, x_pos=0, y_pos=0)
        self.menu = MainMenu(self.viewModel)

        with dpg.window(tag="main window", label="SpectraMatcher", no_resize=True):
            dpg.add_spacer(height=20)
            with dpg.tab_bar():
                with dpg.tab(label=" Import Data "):
                    self.file_manager_panel = FileExplorer(self.viewModel.get_file_manager_viewmodel())

        self.configure_theme()
        dpg.set_primary_window("main window", True)

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




