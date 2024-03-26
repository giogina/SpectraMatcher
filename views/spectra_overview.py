import math

import dearpygui.dearpygui as dpg

from models.experimental_spectrum import ExperimentalSpectrum
from models.state_plot import StatePlot
from utility.icons import Icons
from utility.item_themes import ItemThemes
from viewmodels.plots_overview_viewmodel import PlotsOverviewViewmodel


class SpectraOverview:
    def __init__(self, viewmodel: PlotsOverviewViewmodel):
        self.viewmodel = viewmodel
        self.icons = Icons()
        self.layout_table = "Emission layout table" if self.viewmodel.is_emission else "Excitation layout table"
        self.spectra_column = "Emission spectra column" if self.viewmodel.is_emission else "Excitation spectra column"
        self.plots_column = "Emission plots column" if self.viewmodel.is_emission else "Excitation plots column"
        self.expand_panel_button = None
        self.spectrum_controls = {}  # spec.tag: {property: spec property controls}
        self.spectrum_headers = {}  # spec.tag: collapsing_header item
        self.color_edits = {}  # spec.tag: color_edit item

        self.viewmodel.set_callback("add list spectrum", self.add_spectrum)
        self.viewmodel.set_callback("update list spec", self.update_spectrum)

        self.expand_panel_button = self.icons.insert(dpg.add_button(height=20, width=20, pos=(10, 65), show=False, parent="emission tab" if self.viewmodel.is_emission else "excitation tab", callback=lambda s, a, u: self.collapse_spectrum_list(True)), Icons.caret_right, size=16)

        self.disable_ui_update = True
        self.adjustment_factor = 1

        with dpg.handler_registry() as self.mouse_handlers:
            dpg.add_mouse_release_handler(dpg.mvMouseButton_Right, callback=self.on_right_click_release)
            dpg.add_mouse_wheel_handler(callback=lambda s, a, u: self.on_scroll(a))
            dpg.add_key_down_handler(dpg.mvKey_Shift, callback=lambda s, a, u: self.toggle_fine_adjustments(u), user_data=True)
            dpg.add_key_release_handler(dpg.mvKey_Shift, callback=lambda s, a, u: self.toggle_fine_adjustments(u), user_data=False)

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
            self.last_inserted_spec_tag = dpg.add_spacer(height=0)  # new specs inserted before this tag

        self.configure_theme()

    # TODO: Entries for experimental spectra
    #  enable selecting experimental spectra; only match visible exp spectra
    #  Allow adjustment of minx, maxx of exp spectra
    #  Same min, max x adjustment via vertical drag lines visible on hover
    #  Allow color choices
    #  Collapse / expand all sections

    def on_right_click_release(self):
        for tag in self.viewmodel.state_plots.keys():
            if dpg.is_item_hovered(self.spectrum_controls[tag]['hide']) or dpg.is_item_hovered(self.spectrum_controls[tag]['show']):
                for tag2 in self.viewmodel.state_plots.keys():
                    if tag2 != tag:
                        self.hide_spectrum(tag2)
                self.hide_spectrum(tag, False)

    def reset_spectrum_controls(self, tag):
        defaults = {'xshift': 0., 'yscale': 1.}
        state_plot = self.viewmodel.state_plots[tag]
        self.viewmodel.on_x_drag(defaults['xshift'], state_plot.tag, slider=True)
        self.viewmodel.set_y_scale(defaults['yscale'], state_plot)

    def add_spectrum(self, state_plot: StatePlot):
        self.spectrum_controls[state_plot.tag] = {}
        with dpg.collapsing_header(label=state_plot.name, parent=self.spectra_list_group, before=self.last_inserted_spec_tag, default_open=True) as self.spectrum_headers[state_plot.tag]:
            dpg.add_spacer(height=6)
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=6)
                with dpg.group(horizontal=False):
                    self.spectrum_controls[state_plot.tag]['xshift'] = dpg.add_slider_float(format=f"shift = %.0f - {int(state_plot.spectrum.zero_zero_transition_energy)} cm⁻¹", min_value=-1000, max_value=5000, default_value=state_plot.xshift, callback=lambda s, a, u: self.viewmodel.on_x_drag(a, state_plot.tag, slider=True), width=-66)
                    self.spectrum_controls[state_plot.tag]['yscale'] = dpg.add_slider_float(format=f"scale = %.2f / {int(state_plot.spectrum.multiplicator * state_plot.spectrum.mul2)}", min_value=0, max_value=1.2, default_value=state_plot.yscale, callback=lambda s, a, u: self.viewmodel.set_y_scale(a, u), user_data=state_plot, width=-66)
                    self.spectrum_controls[state_plot.tag]['yshift'] = dpg.add_slider_float(format="y position = %.2f", min_value=0, max_value=len(self.viewmodel.state_plots)*1.2, default_value=state_plot.yshift, callback=lambda s, a, u: self.viewmodel.on_y_drag(a, state_plot), user_data=state_plot, width=-66)
                    for tag in self.viewmodel.state_plots:
                        dpg.configure_item(self.spectrum_controls[tag]['yshift'], max_value=len(self.viewmodel.state_plots)*1.2)
                dpg.add_spacer(width=6)
                with dpg.group(horizontal=False):
                    self.spectrum_controls[state_plot.tag]['show'] = self.icons.insert(dpg.add_button(width=30, height=30, callback=lambda s, a, u: self.hide_spectrum(u, False), user_data=state_plot.tag, show=state_plot.is_hidden()), Icons.eye, size=15)
                    self.spectrum_controls[state_plot.tag]['hide'] = self.icons.insert(dpg.add_button(width=30, height=30, callback=lambda s, a, u: self.hide_spectrum(u, True), user_data=state_plot.tag, show=not state_plot.is_hidden()), Icons.eye_slash, size=15)
                    self.color_edits[state_plot.tag] = dpg.add_color_edit(state_plot.state.get_color(), width=30, height=30, no_inputs=True, callback=lambda s, a, u: self.viewmodel.set_color([c*255 for c in a], u), user_data=state_plot)
                    self.spectrum_controls[state_plot.tag]['reset'] = self.icons.insert(dpg.add_button(width=30, height=30, callback=lambda s, a, u: self.reset_spectrum_controls(u), user_data=state_plot.tag), Icons.rotate_left, size=15)
            dpg.add_spacer(height=6)
        self.last_inserted_spec_tag = self.spectrum_headers[state_plot.tag]
        for tag, color_edit in self.color_edits.items():
            dpg.set_value(color_edit, self.viewmodel.state_plots[tag].state.get_color())

    # def add_exp_spectrum(self, exp: ExperimentalSpectrum):
    #     with dpg.collapsing_header(label=exp.name, parent=self.spectra_list_group, default_open=True):  # as self.spectrum_headers[exp.name]:

    def update_spectrum(self, state_plot: StatePlot):
        if self.disable_ui_update:
            self.disable_ui_update = False
            return
        if state_plot.tag in self.spectrum_controls.keys() and dpg.does_item_exist(self.spectrum_controls[state_plot.tag].get('hide')):
            dpg.set_value(self.spectrum_controls[state_plot.tag]['xshift'], state_plot.xshift)
            dpg.set_value(self.spectrum_controls[state_plot.tag]['yshift'], state_plot.state.settings.get(f"y shift {state_plot.e_key}", state_plot.yshift))
            dpg.set_value(self.spectrum_controls[state_plot.tag]['yscale'], state_plot.yscale)
            dpg.configure_item(self.spectrum_controls[state_plot.tag]['show'], show=state_plot.is_hidden())
            dpg.configure_item(self.spectrum_controls[state_plot.tag]['hide'], show=not state_plot.is_hidden())

    def hide_spectrum(self, tag, hide=True):
        self.viewmodel.hide_spectrum(tag, hide)

    def collapse_spectrum_list(self, show):
        dpg.configure_item(self.spectra_list_group, show=show)
        dpg.configure_item(self.spectra_list_action_bar, show=show)
        dpg.configure_item(self.collapse_plot_settings_button, show=show)
        dpg.configure_item(self.expand_panel_button, show=not show)
        if show:
            dpg.configure_item(self.layout_table, resizable=True, policy=dpg.mvTable_SizingStretchProp)
            dpg.configure_item(f"{'Emission' if self.viewmodel.is_emission else 'Excitation'} plot left spacer", width=0)
        else:
            # dpg.configure_item(f"{'Emission' if self.viewmodel.is_emission else 'Excitation'} plot left spacer", width=20)
            dpg.configure_item(self.layout_table, resizable=False, policy=dpg.mvTable_SizingFixedFit)
            dpg.configure_item(self.spectra_column, width_stretch=False, width=10)
            dpg.configure_item(self.plots_column, width_stretch=True)
            dpg.bind_item_theme(self.expand_panel_button, self.expand_button_theme)

    def configure_theme(self):
        with dpg.theme() as spec_list_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 6, 6)
                # dpg.add_theme_style(dpg.mvStyleVar_CellPadding, 6, 6)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 6, 6)

        dpg.bind_item_theme(self.spectra_list_group, spec_list_theme)

    def on_scroll(self, direction):
        for tag in self.viewmodel.state_plots.keys():
            for key in ['xshift', 'yscale', 'yshift']:
                slider = self.spectrum_controls[tag][key]
                if dpg.does_item_exist(slider) and dpg.is_item_hovered(slider):
                    step = {'xshift': 10, 'yscale': 0.1, 'yshift': 0.1}[key]
                    value = dpg.get_value(slider) + step*direction*self.adjustment_factor
                    dpg.set_value(slider, value)
                    dpg.get_item_callback(slider)(slider, value, dpg.get_item_user_data(slider))
                    self.disable_ui_update = True

    def toggle_fine_adjustments(self, fine):
        if fine:
            self.adjustment_factor = 0.1
        else:
            self.adjustment_factor = 1

