import sys

from launcher import Launcher
from viewmodels.main_viewmodel import MainViewModel
from views.main_menu import MainMenu
from views.file_explorer import FileExplorer
from views.project_setup import ProjectSetup
from views.plots_overview import PlotsOverview
from utility.icons import Icons
from utility.font_manager import FontManager
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

        FontManager.load_fonts()
        monitor = get_monitors()[0]
        dpg.create_viewport(title='SpectraMatcher',
                            width=monitor.width, height=monitor.height-30, x_pos=0, y_pos=0)

        with dpg.window(tag="main window", label="SpectraMatcher", no_scrollbar=True):
            self.menu = MainMenu(self.viewModel)
            with dpg.tab_bar(tag="main tab bar"):
                with dpg.tab(label=" Import Data ", tag="import tab"):
                    with dpg.table(header_row=False, borders_innerV=True, resizable=True, width=-1):
                        dpg.add_table_column(label="file explorer")
                        dpg.add_table_column(label="project setup")
                        with dpg.table_row():
                            with dpg.table_cell():
                                self.file_manager_panel = FileExplorer(self.viewModel.get_file_manager_viewmodel())
                            with dpg.table_cell():
                                self.project_setup_panel = ProjectSetup(self.viewModel.get_project_setup_viewmodel())

                with dpg.tab(label=" Emission Spectra ", tag="emission tab"):  # todo: "OK" button switches to better-populated of these two
                    with dpg.table(header_row=False, borders_innerV=True, resizable=True, width=-1):
                        dpg.add_table_column(label="project settings", init_width_or_weight=1)  # TODO> List like project setup: Name, color buttons, show/hide buttons
                        dpg.add_table_column(label="plots", init_width_or_weight=3)  # todo - compute arrays in background, update with all currently requested, done spectra
                        with dpg.table_row():
                            with dpg.table_cell():
                                self.project_settings_panel = None  # TODO
                            with dpg.table_cell():
                                self.emission_plots_overview_panel = PlotsOverview(self.viewModel.get_plots_overview_viewmodel(is_emission=True))

                with dpg.tab(label=" Excitation Spectra ", tag="excitation tab"):
                    with dpg.table(header_row=False, borders_innerV=True, resizable=True, width=-1):
                        dpg.add_table_column(label="project settings", init_width_or_weight=1)  # TODO> List like project setup: Name, color buttons, show/hide buttons
                        dpg.add_table_column(label="plots", init_width_or_weight=3)
                        with dpg.table_row():
                            with dpg.table_cell():
                                self.project_settings_panel = None  # TODO
                            with dpg.table_cell():
                                self.emission_plots_overview_panel = PlotsOverview(self.viewModel.get_plots_overview_viewmodel(is_emission=False))

        self.configure_theme()
        dpg.set_primary_window("main window", True)

        # need to initialize view model here to be able to show messages about the project
        self.viewModel.set_title_callback(callback=self.update_title)
        self.viewModel.set_message_callback(callback=self.menu.show_dialog)
        self.viewModel.set_switch_tab_callback(callback=self.switch_tab)

    def switch_tab(self, progress):
        print("Switch tab", dpg.get_item_configuration("main tab bar"))
        print(dpg.get_value("main tab bar"))
        if progress == "start":
            dpg.set_value("main tab bar", "import tab")
        elif progress == "import done":
            dpg.set_value("main tab bar", "emission tab")



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
            with dpg.theme_component(dpg.mvTab):
                dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 0, 0)
                dpg.add_theme_style(dpg.mvStyleVar_CellPadding, 0, 0)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 0, 0)
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 3, 6)
                dpg.add_theme_style(dpg.mvStyleVar_CellPadding, 0, 0)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 12, 5)
                dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0)
                dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 0)
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
                # dpg.add_theme_color(dpg.mvThemeCol_Tab, [144, 0, 255, 100])  # Nice highlight color
                dpg.add_theme_color(dpg.mvThemeCol_TabActive, [144, 0, 255, 160])
                dpg.add_theme_color(dpg.mvThemeCol_TabHovered, [144, 0, 255, 255])
                dpg.add_theme_color(dpg.mvThemeCol_Tab, palette[3] + [160])
                # dpg.add_theme_color(dpg.mvThemeCol_TabActive, palette[3] + [200])
                # dpg.add_theme_color(dpg.mvThemeCol_TabHovered, palette[3] + [255])
                dpg.add_theme_color(dpg.mvThemeCol_TableBorderLight, palette[2] + [100])

        dpg.bind_theme(global_theme)

    def startup_callback(self):
        Launcher.maximize_window(dpg.get_viewport_title())
        self.viewModel.load_project()

    def show(self):
        dpg.setup_dearpygui()
        dpg.set_frame_callback(1, self.startup_callback)
        dpg.set_exit_callback(self._on_viewport_close)
        dpg.show_viewport()
        dpg.start_dearpygui()
        dpg.destroy_context()
        return self.result

    def update_title(self, title):
        dpg.set_viewport_title(title)

    def _on_viewport_close(self):
        print("Viewport is closing. Exiting application.")
        self.viewModel.on_close()  # project lock cleanup
        dpg.stop_dearpygui()
        sys.exit()




