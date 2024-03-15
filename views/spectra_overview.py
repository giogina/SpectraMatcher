import dearpygui.dearpygui as dpg
from models.state_plot import StatePlot
from utility.icons import Icons
from utility.item_themes import ItemThemes
from viewmodels.plots_overview_viewmodel import PlotsOverviewViewmodel
from utility.noop import noop


class SpectraOverview:  # TODO> List like project setup: Name, color buttons, show/hide buttons
    def __init__(self, viewmodel: PlotsOverviewViewmodel):
        self.viewmodel = viewmodel
        self.icons = Icons()
        self.layout_table = "Emission layout table" if self.viewmodel.is_emission else "Excitation layout table"
        self.spectra_column = "Emission spectra column" if self.viewmodel.is_emission else "Excitation spectra column"
        self.plots_column = "Emission plots column" if self.viewmodel.is_emission else "Excitation plots column"
        self.expand_panel_button = None

        self.expand_panel_button = self.icons.insert(dpg.add_button(height=20, width=20, pos=(10, 65), show=False, parent="emission tab" if self.viewmodel.is_emission else "excitation tab", callback=lambda s, a, u: self.collapse_spectrum_list(True)), Icons.caret_right, size=16)

        with dpg.child_window(width=-1, height=32) as self.spectra_list_action_bar:

            with dpg.theme() as self.expand_button_theme:
                with dpg.theme_component(dpg.mvAll):
                    dpg.add_theme_color(dpg.mvThemeCol_Button, [200, 200, 255, 200])
                    dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 2, 2)
                    dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 0, 0)

            with dpg.table(header_row=False):
                dpg.add_table_column(width_fixed=True, init_width_or_weight=40)
                dpg.add_table_column(width_stretch=True)
                dpg.add_table_column(width_fixed=True, init_width_or_weight=40)
                with dpg.table_row():
                    dpg.add_spacer()
                    dpg.add_button(height=32, label="Spectra")
                    dpg.bind_item_theme(dpg.last_item(), ItemThemes.invisible_button_theme())
                    self.collapse_plot_settings_button = self.icons.insert(
                        dpg.add_button(height=32, width=32, callback=lambda s, a, u: self.collapse_spectrum_list(False),
                                       show=True), Icons.caret_left, size=16)
        dpg.bind_item_theme(self.spectra_list_action_bar, ItemThemes.action_bar_theme())

        with dpg.group() as self.spectra_list_group:
            pass

    def add_spectrum(self, state_plot: StatePlot):
        with dpg.collapsing_header(label=state_plot.name):
            pass

    def collapse_spectrum_list(self, show):
        dpg.configure_item(self.spectra_list_group, show=show)
        dpg.configure_item(self.spectra_list_action_bar, show=show)
        dpg.configure_item(self.collapse_plot_settings_button, show=show)
        dpg.configure_item(self.expand_panel_button, show=not show)
        if show:
            dpg.configure_item(self.layout_table, resizable=True, policy=dpg.mvTable_SizingStretchProp)
            dpg.configure_item(f"{'Emission' if self.viewmodel.is_emission else 'Excitation'} plot left spacer", width=0)
        else:
            dpg.configure_item(f"{'Emission' if self.viewmodel.is_emission else 'Excitation'} plot left spacer", width=20)
            dpg.configure_item(self.layout_table, resizable=False, policy=dpg.mvTable_SizingFixedFit)
            dpg.configure_item(self.spectra_column, width_stretch=False, width=30)
            dpg.configure_item(self.plots_column, width_stretch=True)
            dpg.bind_item_theme(self.expand_panel_button, self.expand_button_theme)
