import sys

from launcher import Launcher
from viewmodels.main_viewmodel import MainViewModel
from views.main_menu import MainMenu
from views.file_explorer import FileExplorer
from views.project_setup import ProjectSetup
from views.plots_overview import PlotsOverview
from views.spectra_overview import SpectraOverview
from utility.icons import Icons
from utility.font_manager import FontManager
import dearpygui.dearpygui as dpg
from screeninfo import get_monitors
# import logging


class MainWindow:

    def __init__(self, path):
        # with open("C:/Users/Giogina/SpectraMatcher/launch.log", 'a') as launch_log:
        #     launch_log.write(f"Init called\n")
        self.result = 0
        # self.logger = logging.getLogger(__name__)
        self.viewModel = MainViewModel(path)
        self.icons = Icons()

        dpg.create_context()

        dpg.configure_app(auto_device=True)

        FontManager.load_fonts()
        monitor = get_monitors()[0]
        dpg.create_viewport(title='SpectraMatcher',
                            width=monitor.width-600, height=monitor.height-30, x_pos=600, y_pos=0)
        self.viewport_resize_callbacks = []  # list of functions to be called when viewport resizes
        dpg.set_viewport_resize_callback(self.on_viewport_resize)
        self.viewport_size = [0, 0]

        with dpg.window(tag="main window", label="SpectraMatcher", no_scrollbar=True):
            self.menu = MainMenu(self.viewModel)
            with dpg.tab_bar(tag="main tab bar"):
                with dpg.tab(label=" Import Data ", tag="import tab"):
                    with dpg.table(header_row=False, borders_innerV=True, resizable=True, width=-1):
                        dpg.add_table_column(label="file explorer")
                        dpg.add_table_column(label="project setup")
                        with dpg.table_row():
                            with dpg.table_cell():
                                vm = self.viewModel.get_file_manager_viewmodel()
                                self.file_manager_panel = FileExplorer(vm)
                            with dpg.table_cell():
                                self.project_setup_panel = ProjectSetup(self.viewModel.get_project_setup_viewmodel())
                emission_viewmodel = self.viewModel.get_plots_overview_viewmodel(is_emission=True)
                with dpg.tab(label=" Emission Spectra ", tag="emission tab"):
                    with dpg.table(header_row=False, borders_innerV=True, resizable=True, width=-1, tag="Emission layout table"):
                        dpg.add_table_column(label="spectra settings", init_width_or_weight=1, tag="Emission spectra column")
                        dpg.add_table_column(label="plots", init_width_or_weight=5, tag="Emission plots column")
                        with dpg.table_row():
                            with dpg.table_cell():
                                self.project_settings_panel = SpectraOverview(emission_viewmodel)
                            with dpg.table_cell():
                                self.emission_plots_overview_panel = PlotsOverview(emission_viewmodel, self.append_viewport_resize_callback)
                excitation_viewmodel = self.viewModel.get_plots_overview_viewmodel(is_emission=False)
                with dpg.tab(label=" Excitation Spectra ", tag="excitation tab"):
                    with dpg.table(header_row=False, borders_innerV=True, resizable=True, width=-1, tag="Excitation layout table"):
                        dpg.add_table_column(label="spectra settings", init_width_or_weight=1, tag="Excitation spectra column")  #
                        dpg.add_table_column(label="plots", init_width_or_weight=5, tag="Excitation plots column")
                        with dpg.table_row():
                            with dpg.table_cell():
                                self.project_settings_panel = SpectraOverview(excitation_viewmodel)
                            with dpg.table_cell():
                                self.excitation_plots_overview_panel = PlotsOverview(excitation_viewmodel, self.append_viewport_resize_callback)
        self.configure_theme()
        dpg.set_primary_window("main window", True)
        # need to initialize view model here to be able to show messages about the project
        self.viewModel.set_title_callback(callback=self.update_title)
        self.viewModel.set_message_callback(callback=self.menu.show_dialog)
        self.viewModel.set_switch_tab_callback(callback=self.switch_tab)
        self.viewModel.set_exit_callback(callback=dpg.stop_dearpygui)

    def append_viewport_resize_callback(self, func):  # hand this to any view that needs to react to viewport resize
        self.viewport_resize_callbacks.append(func)

    def on_viewport_resize(self, *args):
        if self.viewport_size != [dpg.get_viewport_width(), dpg.get_viewport_height()]:
            for func in self.viewport_resize_callbacks:
                func()
        self.viewport_size = [dpg.get_viewport_width(), dpg.get_viewport_height()]

    def switch_tab(self, progress, *args):
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
                   [33, 33, 36*3],  # 8
                   ]
        with dpg.theme() as global_theme:
            with dpg.theme_component(dpg.mvTab):
                dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 0, 0)
                dpg.add_theme_style(dpg.mvStyleVar_CellPadding, 0, 0)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 0, 0)
            with dpg.theme_component(dpg.mvPlot):
                dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 12, 6)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 6, 3)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 12, 3)
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, palette[8])
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, palette[1])
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, palette[4])
                dpg.add_theme_color(dpg.mvThemeCol_TextSelectedBg, palette[4])
                dpg.add_theme_color(dpg.mvThemeCol_CheckMark, palette[4])
                dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, palette[4]+[100])
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 3, 6)
                dpg.add_theme_style(dpg.mvStyleVar_CellPadding, 0, 0)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 12, 5)
                dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0)
                dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 0)
                dpg.add_theme_style(dpg.mvStyleVar_PopupBorderSize, 0)
                # dpg.add_theme_color(dpg.mvThemeCol_Border, palette[6])
                dpg.add_theme_color(dpg.mvThemeCol_MenuBarBg, palette[1])
                dpg.add_theme_color(dpg.mvThemeCol_PopupBg, palette[2])
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

    def startup_callback(self, *args):
        Launcher.maximize_window(dpg.get_viewport_title())
        self.viewModel.load_project()

    def show(self):
        dpg.setup_dearpygui()
        dpg.set_frame_callback(5, self.startup_callback)
        if sys.platform.startswith("win"):
            dpg.set_viewport_small_icon("resources/SpectraMatcher.ico")
            dpg.set_viewport_large_icon("resources/SpectraMatcher.ico")
        else:
            dpg.set_viewport_small_icon("resources/SpectraMatcher_16.png")
            dpg.set_viewport_large_icon("resources/SpectraMatcher_64.png")
        dpg.show_viewport()
        dpg.start_dearpygui()
        print("Viewport is closing. Exiting application.")
        try:
            self.viewModel.on_close()  # project lock cleanup
        except Exception as e:
            print(f"Error closing: {e}")
        dpg.destroy_context()
        return self.result

    def update_title(self, title, *args):
        dpg.set_viewport_title(title)


