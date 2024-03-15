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
        self.spectrum_controls = {}  # spec.tag: {property: spec property controls}

        self.viewmodel.set_callback("add list spectrum", self.add_spectrum)
        self.viewmodel.set_callback("update list spec", self.update_spectrum)

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
        self.spectrum_controls[state_plot.tag] = {}
        with dpg.collapsing_header(label=state_plot.name, parent=self.spectra_list_group, default_open=True):
            dpg.add_spacer(height=6)
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=6)
                with dpg.group(horizontal=False):
                    with dpg.group(horizontal=True):
                        self.icons.insert(dpg.add_button(width=32, height=32), Icons.eye_slash, size=16)
                        # todo: color button
                        # todo: sort specs bottom-up?
                    self.spectrum_controls[state_plot.tag]['xshift'] = dpg.add_slider_float(label="wavenumber shift", min_value=-1000, max_value=5000, default_value=state_plot.xshift, callback=lambda s, a, u: self.viewmodel.on_x_drag(a, u), user_data=state_plot)
                    self.spectrum_controls[state_plot.tag]['yshift'] = dpg.add_slider_float(label="y shift", min_value=0, max_value=len(self.viewmodel.state_plots)*1.2, default_value=state_plot.yshift, callback=lambda s, a, u: self.viewmodel.on_y_drag(a, u), user_data=state_plot)
                    self.spectrum_controls[state_plot.tag]['yscale'] = dpg.add_slider_float(label="intensity scale", min_value=0, max_value=1.2, default_value=state_plot.yscale, callback=lambda s, a, u: self.viewmodel.set_y_scale(a, u), user_data=state_plot)
                    for tag in self.viewmodel.state_plots:
                        dpg.configure_item(self.spectrum_controls[tag]['yshift'], max_value=len(self.viewmodel.state_plots)*1.2)
            dpg.add_spacer(height=6)

    def update_spectrum(self, state_plot: StatePlot):
        dpg.set_value(self.spectrum_controls[state_plot.tag]['xshift'], state_plot.xshift)
        dpg.set_value(self.spectrum_controls[state_plot.tag]['yshift'], state_plot.yshift)
        dpg.set_value(self.spectrum_controls[state_plot.tag]['yscale'], state_plot.yscale)

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

    def configure_theme(self):
        with dpg.theme() as spec_list_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(dpg.mvStyleVar_CellPadding, 6, 6)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 6, 6)

        dpg.configure_item(self.spectra_list_group, spec_list_theme)

