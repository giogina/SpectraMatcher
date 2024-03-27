import math
import random

import dearpygui.dearpygui as dpg
import pyperclip

from models.experimental_spectrum import ExperimentalSpectrum
from utility.async_manager import AsyncManager
from utility.font_manager import FontManager
from utility.icons import Icons
from utility.item_themes import ItemThemes
from utility.labels import Labels
from utility.matcher import Matcher
from viewmodels.plots_overview_viewmodel import PlotsOverviewViewmodel, WavenumberCorrector
from utility.spectrum_plots import adjust_color_for_dark_theme, SpecPlotter


class PlotsOverview:
    def __init__(self, viewmodel: PlotsOverviewViewmodel, append_viewport_resize_update_callback):
        self.viewmodel = viewmodel
        self.viewmodel.set_callback("redraw plot", self.redraw_plot)
        self.viewmodel.set_callback("update plot", self.update_plot)
        self.viewmodel.set_callback("add spectrum", self.add_spectrum)
        self.viewmodel.set_callback("update spectrum color", self.update_spectrum_color)
        self.viewmodel.set_callback("delete sticks", self.delete_sticks)
        self.viewmodel.set_callback("redraw sticks", self.draw_sticks)
        self.viewmodel.set_callback("post load update", self.set_ui_values_from_settings)
        self.viewmodel.set_callback("update labels", self.draw_labels)
        self.viewmodel.set_callback("redraw peaks", self.redraw_peak_drag_points)
        self.viewmodel.set_callback("hide spectrum", self.hide_spectrum)
        self.viewmodel.set_callback("update match plot", self.update_match_plot)
        self.custom_series = None
        self.spec_theme = {}
        self.hovered_spectrum_y_drag_line = None
        self.hovered_spectrum = None
        self.hovered_x_drag_line = None
        self.show_all_drag_lines = False  # show all drag lines
        self.line_series = []
        self.show_sticks = None
        self.dragged_plot = None
        self.gaussian_labels = False
        self.labels = False
        self.annotations = {}  # state_plot tag: annotation object
        self.annotation_lines = {}  # state_plot tag: annotation object
        self.label_drag_points = {}
        self.label_controls = {}
        self.peak_controls = {}
        self.match_controls = {}
        self.icons = Icons()
        self.pixels_per_plot_x = 1
        self.pixels_per_plot_y = 1
        self.peak_edit_mode_enabled = False
        self.peak_indicator_points = []
        self.hovered_peak_indicator_point = None
        self.exp_hovered = False
        self.mouse_plot_pos = (0, 0)
        self.dragged_peak = None
        self.vertical_slider_active = False
        self.adjustment_factor = 1
        self.disable_ui_update = False  # True while slider scrolls are being processed
        self.ctrl_pressed = False
        self.shade_plots = []
        self.shade_line_plots = []
        self.component_plots = []
        self.match_lines = []
        self.matched_spectra_checks = {}
        self.sticks_layer = {}
        self.redraw_sticks_on_release = False

        with dpg.handler_registry() as self.mouse_handlers:
            dpg.add_mouse_wheel_handler(callback=lambda s, a, u: self.on_scroll(a))
            dpg.add_mouse_release_handler(dpg.mvMouseButton_Left, callback=self.on_drag_release)
            dpg.add_mouse_release_handler(dpg.mvMouseButton_Right, callback=self.on_right_click_release)
            dpg.add_key_down_handler(dpg.mvKey_Alt, callback=lambda s, a, u: self.show_drag_lines(u), user_data=True)
            dpg.add_key_release_handler(dpg.mvKey_Alt, callback=lambda s, a, u: self.show_drag_lines(u), user_data=False)
            dpg.add_key_down_handler(dpg.mvKey_Shift, callback=lambda s, a, u: self.toggle_fine_adjustments(u), user_data=True)
            dpg.add_key_release_handler(dpg.mvKey_Shift, callback=lambda s, a, u: self.toggle_fine_adjustments(u), user_data=False)
            dpg.add_key_down_handler(dpg.mvKey_Control, callback=lambda s, a, u: self.toggle_ctrl_flag(u), user_data=True)
            dpg.add_key_release_handler(dpg.mvKey_Control, callback=lambda s, a, u: self.toggle_ctrl_flag(u), user_data=False)
            dpg.add_key_press_handler(dpg.mvKey_Down, callback=lambda s, a, u: self.on_arrow_press("y", -1))
            dpg.add_key_press_handler(dpg.mvKey_Up, callback=lambda s, a, u: self.on_arrow_press("y", 1))
            dpg.add_key_press_handler(dpg.mvKey_Left, callback=lambda s, a, u: self.on_arrow_press("x", -1))
            dpg.add_key_press_handler(dpg.mvKey_Right, callback=lambda s, a, u: self.on_arrow_press("x", 1))

        with dpg.theme() as self.white_line_series_theme:
            with dpg.theme_component(dpg.mvLineSeries):
                dpg.add_theme_color(dpg.mvPlotCol_Line, [255, 255, 255], category=dpg.mvThemeCat_Plots)

        with dpg.table(header_row=False, borders_innerV=True, resizable=True) as self.layout_table:
            self.plot_column = dpg.add_table_column(init_width_or_weight=4)
            self.plot_settings_column = dpg.add_table_column(init_width_or_weight=1)

            with dpg.table_row():
                with dpg.table_cell():
                    with dpg.group(horizontal=True):
                        dpg.add_spacer(width=0, tag=f"{'Emission' if self.viewmodel.is_emission else 'Excitation'} plot left spacer")
                        with dpg.table(height=-1, header_row=False, borders_innerH=True, resizable=True, policy=dpg.mvTable_SizingStretchProp) as self.plot_and_matches_table:
                            dpg.add_table_column()
                            with dpg.table_row() as self.plot_row:
                                with dpg.table_cell():
                                    with dpg.plot(height=-1, width=-1, anti_aliased=True, tag=f"plot_{self.viewmodel.is_emission}") as self.plot:

                                        dpg.add_plot_axis(dpg.mvXAxis, label="wavenumber / cm⁻¹", tag=f"x_axis_{self.viewmodel.is_emission}", no_gridlines=True)
                                        dpg.add_plot_axis(dpg.mvYAxis, label="relative intensity", tag=f"y_axis_{self.viewmodel.is_emission}", no_gridlines=True)

                                        # dpg.set_axis_limits_auto(f"x_axis_{self.viewmodel.is_emission}")
                                        # dpg.set_axis_limits_auto(f"y_axis_{self.viewmodel.is_emission}")

                                        with dpg.custom_series([0.0, 1000.0], [1.0, 0.0], 2,
                                                               parent=f"y_axis_{self.viewmodel.is_emission}",
                                                               callback=self._custom_series_callback) as self.custom_series:
                                            # self.tooltiptext = dpg.add_text("Current Point: ")
                                            pass

                                        dpg.add_line_series([], [], parent=f"y_axis_{self.viewmodel.is_emission}", tag=f"exp_overlay_{self.viewmodel.is_emission}")
                with dpg.table_cell():
                    with dpg.child_window(width=-1, height=32) as self.plot_settings_action_bar:
                        with dpg.table(header_row=False):
                            dpg.add_table_column(width_fixed=True, init_width_or_weight=40)
                            dpg.add_table_column(width_stretch=True)
                            dpg.add_table_column(width_fixed=True, init_width_or_weight=220)
                            with dpg.table_row():
                                with dpg.group(horizontal=True):
                                    self.collapse_plot_settings_button = self.icons.insert(dpg.add_button(height=32, width=32, callback=lambda s, a, u: self.collapse_plot_settings(False), show=True), Icons.caret_right, size=16)
                                # dpg.add_spacer()
                                dpg.add_button(height=32, label="Plot settings")
                                dpg.bind_item_theme(dpg.last_item(), ItemThemes.invisible_button_theme())
                                dpg.add_spacer(width=32)
                    dpg.bind_item_theme(self.plot_settings_action_bar, ItemThemes.action_bar_theme())

                    with dpg.child_window() as self.plot_settings_group:
                        with dpg.theme(tag=f"slider_theme_{self.viewmodel.is_emission} Red"):
                            with dpg.theme_component(0):
                                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, [160, 0, 0, 180])
                                dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, [160, 0, 0, 200])
                                dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, [160, 0, 0])
                                dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, [180, 0, 0])
                                dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, [220, 0, 0])
                        with dpg.theme(tag=f"slider_theme_{self.viewmodel.is_emission} Green"):
                            with dpg.theme_component(0):
                                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, [0, 160, 0, 180])
                                dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, [0, 160, 0, 200])
                                dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, [0, 160, 0])
                                dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, [0, 180, 0])
                                dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, [0, 220, 0])
                        with dpg.theme(tag=f"slider_theme_{self.viewmodel.is_emission} Blue"):
                            with dpg.theme_component(0):
                                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, [0, 0, 120, 180])
                                dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, [0, 0, 150, 200])
                                dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, [0, 0, 150])
                                dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, [0, 0, 220])
                                dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, [0, 0, 250])
                        dpg.add_spacer(height=24)
                        with dpg.group(horizontal=True):
                            dpg.add_spacer(width=6)
                            with dpg.group(horizontal=False):
                                self.half_width_slider = dpg.add_slider_float(label="Half-width", min_value=0.1, max_value=60, format="%.1f", callback=lambda s, a, u: self.viewmodel.resize_half_width(a, relative=False))
                                self.vertical_spacing_slider = dpg.add_slider_float(label="Vertical spacing", min_value=-2, max_value=2, default_value=1.25, callback=lambda s, a, u: self.viewmodel.set_y_shifts(a))
                        dpg.add_spacer(height=16)
                        with dpg.collapsing_header(label="Anharmonic corrections", default_open=True):
                            dpg.add_spacer(height=6)
                            with dpg.group(horizontal=True):
                                dpg.add_spacer(width=6)
                                with dpg.group(horizontal=False):
                                    for i, x_scale_key in enumerate(['H stretches', 'bends', 'others']):
                                        dpg.add_slider_float(label=[' H-* stretches', ' Bends', ' Others'][i], tag=f"{x_scale_key} {self.viewmodel.is_emission} slider", vertical=False, max_value=1.0, min_value=0.8, callback=lambda s, a, u: self.viewmodel.change_correction_factor(u, a), user_data=x_scale_key)  #, format=""
                                        dpg.bind_item_theme(dpg.last_item(), f"slider_theme_{self.viewmodel.is_emission} {['Red', 'Blue', 'Green'][i]}")
                                    self.show_sticks = dpg.add_checkbox(label=" Show stick spectra", callback=self.toggle_sticks)
                            dpg.add_spacer(height=6)
                        dpg.add_spacer(height=6)
                        with dpg.collapsing_header(label="Label settings", default_open=True):
                            # dpg.add_spacer(height=6)
                            with dpg.group(horizontal=True):
                                dpg.add_spacer(width=6)
                                with dpg.group(horizontal=False):
                                    self.label_controls['show labels'] = dpg.add_checkbox(label=" Show labels", callback=lambda s, a, u: self.toggle_labels(u), user_data=False, default_value=Labels.settings[self.viewmodel.is_emission].get('show labels', False))
                                    self.label_controls['show gaussian labels'] = dpg.add_checkbox(label=" Show Gaussian labels", callback=lambda s, a, u: self.toggle_labels(u), user_data=True, default_value=Labels.settings[self.viewmodel.is_emission].get('show gaussian labels', False))
                                    self.label_controls['peak intensity label threshold'] = dpg.add_slider_float(label=" Min. Intensity", min_value=0, max_value=0.2, default_value=Labels.settings[self.viewmodel.is_emission].get('peak intensity label threshold', 0.03), callback=lambda s, a, u: Labels.set(self.viewmodel.is_emission, 'peak intensity label threshold', a))
                                    # self.label_controls['peak separation threshold'] = dpg.add_slider_float(label=" Min. Separation", min_value=0, max_value=100, default_value=Labels.settings[self.viewmodel.is_emission].get('peak separation threshold', 1), callback=lambda s, a, u: Labels.set(self.viewmodel.is_emission, 'peak separation threshold', a))  # In original, caused re-draw with higher half-width to smooth out peaks. Probably not necessary.
                                    self.label_controls['stick label relative threshold'] = dpg.add_slider_float(label=" Min rel. stick", min_value=0, max_value=0.5, default_value=Labels.settings[self.viewmodel.is_emission].get('stick label relative threshold', 0.1), callback=lambda s, a, u: Labels.set(self.viewmodel.is_emission, 'stick label relative threshold', a))
                                    self.label_controls['stick label absolute threshold'] = dpg.add_slider_float(label=" Min abs. stick", min_value=0, max_value=0.1, default_value=Labels.settings[self.viewmodel.is_emission].get('stick label absolute threshold', 0.001), callback=lambda s, a, u: Labels.set(self.viewmodel.is_emission, 'stick label absolute threshold', a))
                                    self.label_controls['label font size'] = dpg.add_slider_int(label=" Font size", min_value=12, max_value=24, default_value=Labels.settings[self.viewmodel.is_emission].get('label font size', 18), callback=lambda s, a, u: Labels.set(self.viewmodel.is_emission, 'label font size', a))
                                    # self.label_controls['axis font size'] = dpg.add_slider_int(label=" Axis font size", min_value=12, max_value=24, default_value=Labels.settings[self.viewmodel.is_emission].get('axis font size', 18), callback=lambda s, a, u: Labels.set(self.viewmodel.is_emission, 'axis font size', a))
                                    dpg.add_button(label="Defaults", width=-6, callback=self.restore_label_defaults)
                            dpg.add_spacer(height=6)
                        dpg.add_spacer(height=6)
                        with dpg.collapsing_header(label="Peak detection", default_open=True):
                            with dpg.group(horizontal=True):
                                dpg.add_spacer(width=6)
                                with dpg.group(horizontal=False):
                                    dpg.add_checkbox(label=" Edit peaks", default_value=False, callback=lambda s, a, u: self.enable_edit_peaks(a))
                                    self.peak_controls['peak prominence threshold'] = dpg.add_slider_float(label=" Min. prominence", min_value=0, max_value=0.1, default_value=ExperimentalSpectrum.get(self.viewmodel.is_emission, 'peak prominence threshold', 0.005), callback=lambda s, a, u: ExperimentalSpectrum.set(self.viewmodel.is_emission, 'peak prominence threshold', a))
                                    self.peak_controls['peak width threshold'] = dpg.add_slider_int(label=" Min. width", min_value=0, max_value=100, default_value=ExperimentalSpectrum.get(self.viewmodel.is_emission, 'peak width threshold', 2), callback=lambda s, a, u: ExperimentalSpectrum.set(self.viewmodel.is_emission, 'peak width threshold', a))
                                    dpg.add_button(label="Defaults", width=-6, callback=lambda s, a, u: ExperimentalSpectrum.reset_defaults(self.viewmodel.is_emission))
                                    dpg.add_button(label="Reset manual selection", width=-6, callback=lambda s, a, u: ExperimentalSpectrum.reset_manual_peaks(self.viewmodel.is_emission))
                        dpg.add_spacer(height=6)
                        with dpg.collapsing_header(label="Match settings", default_open=True):
                            # dpg.add_spacer(height=6)
                            with dpg.group(horizontal=True):
                                dpg.add_spacer(width=6)
                                with dpg.group():
                                    self.match_controls['match active'] = dpg.add_checkbox(label=" Match peaks", default_value=False, callback=lambda s, a, u: self.viewmodel.match_peaks(a))
                                    with dpg.tree_node(label="Match thresholds"):
                                        self.match_controls['peak intensity match threshold'] = dpg.add_slider_float(min_value=0, max_value=0.2, format=f"Rel. intensity ≥ %0.2f", default_value=Matcher.settings[self.viewmodel.is_emission].get('peak intensity match threshold', 0.03), callback=lambda s, a, u: Matcher.set(self.viewmodel.is_emission, 'peak intensity match threshold', a), width=-32)
                                        self.match_controls['distance match threshold'] = dpg.add_slider_float(min_value=0, max_value=100, format=f"Distance ≤ %0.2f  cm⁻¹", default_value=Matcher.settings[self.viewmodel.is_emission].get('distance match threshold', 30), callback=lambda s, a, u: Matcher.set(self.viewmodel.is_emission, 'distance match threshold', a), width=-32)
                                        dpg.add_button(label="Defaults", width=-32, callback=self.restore_matcher_defaults)
                                        dpg.add_spacer(height=6)
                                    with dpg.tree_node(label="Component spectra") as self.matched_spectra_node:
                                        self.matched_spectra_checks_spacer = dpg.add_spacer(height=6)
                                    with dpg.tree_node(label="Composite spectrum display options"):
                                        self.match_controls['show composite spectrum'] = dpg.add_checkbox(label="Composite spectrum", callback=lambda s, a, u: Matcher.set(self.viewmodel.is_emission, 'show composite spectrum', a), default_value=Matcher.get(self.viewmodel.is_emission, 'show composite spectrum', False))
                                        self.match_controls['show component spectra'] = dpg.add_checkbox(label="Component spectra", callback=lambda s, a, u: Matcher.set(self.viewmodel.is_emission, 'show component spectra', a), default_value=Matcher.get(self.viewmodel.is_emission, 'show component spectra', False))
                                        self.match_controls['show shade spectra'] = dpg.add_checkbox(label="Shaded contributions", callback=lambda s, a, u: Matcher.set(self.viewmodel.is_emission, 'show shade spectra', a), default_value=Matcher.get(self.viewmodel.is_emission, 'show shade spectra', False))
                                        # self.match_controls['show stick spectra'] = dpg.add_checkbox(label="Stick spectra", callback=lambda s, a, u: Matcher.set(self.viewmodel.is_emission, 'show stick spectra', a), default_value=Matcher.get(self.viewmodel.is_emission, 'show stick spectra', False))
                                    self.show_match_table_button = dpg.add_button(label="Show assignment table", callback=self.show_match_table, width=-6)
        self.expand_plot_settings_button = self.icons.insert(dpg.add_button(height=20, width=20, show=False, parent="emission tab" if self.viewmodel.is_emission else "excitation tab", callback=lambda s, a, u: self.collapse_plot_settings(True)), Icons.caret_left, size=16)
        self.dummy_series = dpg.add_scatter_series([0, 2000], [-0.1, 1.1], parent=f"y_axis_{self.viewmodel.is_emission}")
        self.match_plot = dpg.add_line_series([], [], show=False, parent=f"y_axis_{self.viewmodel.is_emission}")
        self.match_plot_y_drag = dpg.add_drag_line(vertical=False, show_label=False, default_value=0, callback=lambda sender, a, u: self.viewmodel.set_y_shifts(dpg.get_value(sender), dragging=True), parent=f"plot_{self.viewmodel.is_emission}", show=False, color=[200, 200, 200])
        append_viewport_resize_update_callback(self.viewport_resize_update)
        self.match_table = None
        self.match_table_row = None
        self.match_table_shown = False
        self.match_table_theme = None
        self.match_entry = {}
        self.match_rows = {}
        self.table = []
        self.configure_theme()

    def viewport_resize_update(self):
        if dpg.get_item_configuration(self.expand_plot_settings_button).get('show'):
            dpg.hide_item(self.expand_plot_settings_button)
            dpg.configure_item(self.expand_plot_settings_button, show=True, pos=(dpg.get_viewport_width() - 40, 45))
        for tag in self.viewmodel.state_plots.keys():
            self.draw_labels(tag)
        if self.match_table_shown:
            dpg.configure_item(self.plot, height=dpg.get_viewport_height()/2)
            dpg.configure_item(self.plot_row, height=dpg.get_viewport_height()/2)

    def toggle_fine_adjustments(self, fine):
        if fine:
            self.adjustment_factor = 0.1
        else:
            self.adjustment_factor = 1

    def toggle_ctrl_flag(self, down):
        self.ctrl_pressed = down

    def on_arrow_press(self, dimension, direction):
        if dimension == "x":
            self.viewmodel.last_action_x(direction * self.adjustment_factor)
        else:
            self.viewmodel.last_action_y(direction * self.adjustment_factor)

    def on_right_click_release(self):
        point = self.hovered_peak_indicator_point
        if point is not None:
            exp, peak = dpg.get_item_user_data(point)
            exp.delete_peak(peak)
            dpg.delete_item(point)
            self.peak_indicator_points.remove(point)
            self.viewmodel.match_plot.assign_peaks()
        for tag, check in self.matched_spectra_checks.items():
            if dpg.is_item_hovered(check):
                for tag2, check2 in self.matched_spectra_checks.items():
                    if tag2 != tag:
                        self.viewmodel.toggle_match_spec_contribution(self.viewmodel.state_plots[tag2], False)
                self.viewmodel.toggle_match_spec_contribution(self.viewmodel.state_plots[tag], True)
                break

    def show_match_table(self):
        if self.match_table_shown:
            dpg.delete_item(self.match_table_row)
            dpg.configure_item(self.plot, height=-1)
            dpg.configure_item(self.plot_row, height=0)
            self.match_table_shown = False
            dpg.configure_item(self.show_match_table_button, label="Show assignment table")
        else:
            dpg.configure_item(self.plot, height=dpg.get_viewport_height()/2)
            dpg.configure_item(self.plot_row, height=dpg.get_viewport_height()/2)
            self.match_table_shown = True
            dpg.configure_item(self.show_match_table_button, label="Hide assignment table")
            self.match_entry = {}
            with dpg.table_row(parent=self.plot_and_matches_table) as self.match_table_row:
                with dpg.table_cell():
                    with dpg.table(resizable=True, hideable=True, context_menu_in_body=True, borders_innerV=True, scrollX=True, scrollY=True, no_pad_innerX=False, no_pad_outerX=False) as self.match_table:
                        for header in self.viewmodel.match_plot.get_match_table(header_only=True)[0]:
                            dpg.add_table_column(label=header)
                        self.update_match_table()
            dpg.bind_item_theme(self.match_table, self.match_table_theme)

    def update_match_table(self):
        if self.match_table_shown:
            table = self.viewmodel.match_plot.get_match_table()
            if len(table) > 1 and sum([len(line) for line in table]) >= len(list(self.match_rows.keys())):  # sum([len(line) for line in self.table]):
                for i, line in enumerate(table[1:]):
                    if i not in self.match_rows.keys():
                        self.match_rows[i] = dpg.add_table_row(parent=self.match_table)
                    for j, entry in enumerate(line):
                        if dpg.does_item_exist(self.match_entry.get((i, j))):
                            dpg.set_value(self.match_entry[(i, j)], entry)
                        else:
                            self.match_entry[(i, j)] = dpg.add_text(entry, parent=self.match_rows[i])
            else:
                # AsyncManager.submit_task("re-draw match table", self.reconstruct_match_table, table, buffer=0.01)
                self.reconstruct_match_table(table)
            self.table = table

    def reconstruct_match_table(self, table):
        for row in self.match_rows.values():
            dpg.delete_item(row)
        self.match_rows = {}
        for i, line in enumerate(table[1:]):
            with dpg.table_row(parent=self.match_table) as self.match_rows[i]:
                for j, entry in enumerate(line):
                    self.match_entry[(i, j)] = dpg.add_text(entry)

    def enable_edit_peaks(self, enable):
        self.peak_edit_mode_enabled = enable
        self.redraw_peak_drag_points()

    def redraw_peak_drag_points(self):
        self.delete_peak_indicator_points()
        if self.peak_edit_mode_enabled:
            for exp in ExperimentalSpectrum.spectra_list:
                if exp.is_emission == self.viewmodel.is_emission:
                    for peak in exp.peaks:
                        self.add_peak_drag_point(exp, peak)

    def add_peak_drag_point(self, exp, peak):
        self.peak_indicator_points.append(dpg.add_drag_point(default_value=(peak.wavenumber, peak.intensity), callback=lambda s, a, u: self.mark_peak_dragged(s), user_data=(exp, peak), parent=self.plot))

    def delete_peak_indicator_points(self):
        for point in self.peak_indicator_points:
            if dpg.does_item_exist(point):
                dpg.delete_item(point)
        self.peak_indicator_points = []

    def mark_peak_dragged(self, peak_point):
        self.dragged_peak = peak_point
        exp, peak = dpg.get_item_user_data(peak_point)
        index = exp.get_x_index(dpg.get_value(peak_point)[0])
        dpg.set_value(self.dragged_peak, (exp.xdata[index], exp.ydata[index]))

    def collapse_plot_settings(self, show=False):
        dpg.configure_item(self.plot_settings_group, show=show)
        dpg.configure_item(self.plot_settings_action_bar, show=show)
        dpg.configure_item(self.collapse_plot_settings_button, show=show)
        dpg.configure_item(self.expand_plot_settings_button, show=not show, pos=(dpg.get_viewport_width()-40, 45))
        if show:
            dpg.configure_item(self.layout_table, resizable=True, policy=dpg.mvTable_SizingStretchProp)
        else:
            dpg.configure_item(self.layout_table, resizable=False, policy=dpg.mvTable_SizingFixedFit)
            dpg.configure_item(self.plot_column, width_stretch=True)
        for tag in self.viewmodel.state_plots.keys():
            self.draw_labels(tag)  # redistribute those

    def restore_label_defaults(self):
        Labels.restore_defaults(self.viewmodel.is_emission)
        self.set_ui_values_from_settings(labels=True)

    def restore_matcher_defaults(self):
        Matcher.restore_defaults(self.viewmodel.is_emission)
        self.set_ui_values_from_settings(matcher=True)

    def print_table(self):
       pyperclip.copy(self.viewmodel.match_plot.get_match_table(self.gaussian_labels))

    def set_ui_values_from_settings(self, x_scale=False, half_width=False, x_shifts=False, y_shifts=False, labels=False, peak_detection=False, matcher=False):
        if self.disable_ui_update:
            self.disable_ui_update = False
            return
        load_all = True not in (x_scale, half_width, x_shifts, y_shifts, labels, matcher)

        if load_all or x_scale:
            for i, x_scale_key in enumerate(['bends', 'H stretches', 'others']):
                dpg.set_value(f"{x_scale_key} {self.viewmodel.is_emission} slider", value=WavenumberCorrector.correction_factors[self.viewmodel.is_emission].get(x_scale_key, 0))
        if load_all or half_width:
            dpg.set_value(self.half_width_slider, SpecPlotter.get_half_width(self.viewmodel.is_emission))
        if load_all or y_shifts:
            if self.viewmodel.match_plot.matching_active:
                dpg.set_value(self.vertical_spacing_slider, Matcher.get(self.viewmodel.is_emission, 'combo spectrum y shift', self.viewmodel.match_plot.yshift))
            else:
                dpg.set_value(self.vertical_spacing_slider, Labels.settings[self.viewmodel.is_emission].get('global y shifts', 1.25))
        if load_all or labels:
            for key, item in self.label_controls.items():
                value = Labels.settings[self.viewmodel.is_emission].get(key)
                dpg.set_value(item, value)
                if not (key in ('show labels', 'show gaussian labels') and value is False and (Labels.settings[self.viewmodel.is_emission].get('show labels') or Labels.settings[self.viewmodel.is_emission].get('show gaussian labels'))):
                    if dpg.get_item_callback(item) is not None:
                        dpg.get_item_callback(item)(item, value, dpg.get_item_user_data(item))
        if load_all or peak_detection:
            for key, item in self.peak_controls.items():
                value = ExperimentalSpectrum.get(self.viewmodel.is_emission, key)
                dpg.set_value(item, value)
                if dpg.get_item_callback(item) is not None:
                    dpg.get_item_callback(item)(item, value, dpg.get_item_user_data(item))
        if load_all or matcher:
            for key, item in self.match_controls.items():
                value = Matcher.settings[self.viewmodel.is_emission].get(key, False)
                dpg.set_value(item, value)
                if dpg.get_item_callback(item) is not None:
                    dpg.get_item_callback(item)(item, value, dpg.get_item_user_data(item))

    def _custom_series_callback(self, sender, app_data):
        try:
            _helper_data = app_data[0]
            mouse_x_plot_space = _helper_data["MouseX_PlotSpace"]
            mouse_y_plot_space = _helper_data["MouseY_PlotSpace"]
            transformed_x = app_data[1]
            transformed_y = app_data[2]
            self.pixels_per_plot_x = (transformed_x[1]-transformed_x[0])/1000
            self.pixels_per_plot_y = transformed_y[1]-transformed_y[0]
            if dpg.is_item_hovered(f"plot_{self.viewmodel.is_emission}"):
                dpg.show_item(f"exp_overlay_{self.viewmodel.is_emission}")
            else:
                dpg.hide_item(f"exp_overlay_{self.viewmodel.is_emission}")
                return
            # mouse_x_pixel_space = _helper_data["MouseX_PixelSpace"]
            # mouse_y_pixel_space = _helper_data["MouseY_PixelSpace"]
            self.mouse_plot_pos = (mouse_x_plot_space, mouse_y_plot_space)
            dpg.delete_item(sender, children_only=True, slot=2)
            dpg.push_container_stack(sender)
            dpg.configure_item(sender, tooltip=False)
            dpg.set_value(f"exp_overlay_{self.viewmodel.is_emission}", [[], []])
            self.hovered_spectrum_y_drag_line = None
            hovered_spectrum = None
            min_hovered_drag_line_distance = 10*self.pixels_per_plot_y  # (measured in pixel space)
            self.hovered_x_drag_line = None
            for s_tag, s in self.viewmodel.state_plots.items():
                if not dpg.does_item_exist(f"drag-x-{s_tag}"):
                    return  # drawing is currently underway
                if dpg.is_item_shown(s.tag):  # non-hidden spectrum
                    if not self.show_all_drag_lines:
                        if not self.viewmodel.match_plot.matching_active:
                            if abs(dpg.get_value(f"drag-{s_tag}") - mouse_y_plot_space) < 0.02:
                                dpg.show_item(f"drag-{s_tag}")
                                self.hovered_spectrum_y_drag_line = s_tag
                            elif abs(dpg.get_value(f"drag-{s_tag}") - mouse_y_plot_space) > 0.1:
                                dpg.hide_item(f"drag-{s_tag}")
                        if abs(dpg.get_value(f"drag-x-{s_tag}") - mouse_x_plot_space) > 50:
                            dpg.hide_item(f"drag-x-{s_tag}")

                    if s.yshift - 0.02 <= mouse_y_plot_space <= s.yshift+s.yscale:
                        if abs(dpg.get_value(f"drag-x-{s_tag}") - mouse_x_plot_space) < 10:
                            dpg.show_item(f"drag-x-{s_tag}")
                            self.hovered_x_drag_line = s_tag
                        drag_line_distance = min(abs(dpg.get_value(f'drag-x-{s_tag}') - mouse_x_plot_space)*self.pixels_per_plot_x, abs(dpg.get_value(f'drag-{s_tag}') - mouse_y_plot_space)*self.pixels_per_plot_y)

                        if drag_line_distance < min_hovered_drag_line_distance:
                            hovered_spectrum = s
                            min_hovered_drag_line_distance = drag_line_distance
                            if not -0.2 < s.yshift <= 0.9 and not self.viewmodel.match_plot.matching_active:
                                dpg.set_value(f"exp_overlay_{self.viewmodel.is_emission}", [s.xdata, s.ydata - s.yshift])
                                dpg.bind_item_theme(f"exp_overlay_{self.viewmodel.is_emission}", self.spec_theme[s.tag])

                    if self.labels:
                        for label in self.annotations[s_tag].values():
                            pos = dpg.get_value(label)
                            dist = self.pixel_distance([mouse_x_plot_space, mouse_y_plot_space], pos)
                            if max(dist) < 10:
                                dpg.show_item(self.label_drag_points[s_tag][label])
                            else:
                                dpg.hide_item(self.label_drag_points[s_tag][label])
                        # dpg.configure_item(sender, tooltip=True)
                        # dpg.set_value(self.tooltiptext, f"Diff: {abs(dpg.get_value(f'drag-x-{s_tag}') - mouse_x_plot_space)}")
            self.hovered_spectrum = hovered_spectrum

            if self.viewmodel.match_plot.matching_active:
                for s in self.viewmodel.match_plot.contributing_state_plots:
                    if not self.show_all_drag_lines:
                        if abs(dpg.get_value(f"drag-x-{s.tag}") - mouse_x_plot_space) > 50:
                            dpg.hide_item(f"drag-x-{s.tag}")

                    if self.viewmodel.match_plot.yshift - 0.02 <= mouse_y_plot_space <= self.viewmodel.match_plot.yshift + 1:
                        if abs(dpg.get_value(f"drag-x-{s.tag}") - mouse_x_plot_space) < 10:
                            dpg.show_item(f"drag-x-{s.tag}")
                if abs(dpg.get_value(self.match_plot_y_drag) - mouse_y_plot_space) < 0.02:
                    dpg.show_item(self.match_plot_y_drag)
                elif (not self.show_all_drag_lines) and abs(dpg.get_value(self.match_plot_y_drag) - mouse_y_plot_space) > 0.1:
                    dpg.hide_item(self.match_plot_y_drag)
            else:
                dpg.hide_item(self.match_plot_y_drag)

            if self.peak_edit_mode_enabled:
                self.hovered_peak_indicator_point = None
                for point in self.peak_indicator_points:
                    if max(self.pixel_distance(dpg.get_value(point), [mouse_x_plot_space, mouse_y_plot_space])) < 6:
                        self.hovered_peak_indicator_point = point
                        break
                self.exp_hovered = 0 <= mouse_y_plot_space <= 1
            dpg.pop_container_stack()
        except Exception as e:
            print(f"Exception in custom series callback: {e}")

    def pixel_distance(self, plot_pos_1, plot_pos_2):
        return abs((plot_pos_1[0] - plot_pos_2[0])*self.pixels_per_plot_x), abs((plot_pos_1[1] - plot_pos_2[1])*self.pixels_per_plot_y)

    def sticks_callback(self, sender, app_data):
        return

    def redraw_plot(self):
        for tag in self.line_series:
            dpg.delete_item(tag)
        self.line_series = []

        xmin, xmax, ymin, ymax = self.viewmodel.get_zoom_range()
        dpg.set_value(self.dummy_series, [[xmin, xmax], [ymin, ymax]])

        for x_data, y_data in self.viewmodel.xydatas:
            self.add_experimental_spectrum(x_data, y_data)
        for s in self.viewmodel.state_plots.keys():
            self.add_spectrum(s)

    def add_experimental_spectrum(self, x_data, y_data):
        dpg.add_line_series(x_data, y_data, parent=f"y_axis_{self.viewmodel.is_emission}")
        self.line_series.append(dpg.last_item())
        if self.viewmodel.state_plots == {}:
            dpg.fit_axis_data(f"x_axis_{self.viewmodel.is_emission}")
            dpg.bind_item_theme(dpg.last_item(), f"exp_spec_theme_{self.viewmodel.is_emission}")

    def add_spectrum(self, tag):
        xmin, xmax, ymin, ymax = self.viewmodel.get_zoom_range()
        s = self.viewmodel.state_plots[tag]
        if not dpg.does_item_exist(tag):
            xdata, ydata = s.get_xydata(xmin, xmax)  # truncated versions
            dpg.add_line_series(xdata, ydata, label=s.name, show=not s.is_hidden(), parent=f"y_axis_{self.viewmodel.is_emission}", tag=s.tag, before=self.match_plot)
            self.line_series.append(s.tag)
        else:
            self.update_plot(s)
        if not dpg.does_item_exist(f"drag-{s.tag}"):
            dpg.add_drag_line(tag=f"drag-{s.tag}", vertical=False, show_label=False, default_value=s.yshift,
                              callback=lambda sender, a, u: self.viewmodel.on_y_drag(dpg.get_value(sender), s),
                              parent=f"plot_{self.viewmodel.is_emission}", show=False, color=s.state.get_color())
            dpg.add_drag_line(tag=f"drag-x-{s.tag}", vertical=True, show_label=False, default_value=s.handle_x+s.xshift,
                              callback=lambda sender, a, u: self.viewmodel.on_x_drag(dpg.get_value(sender), s.tag),
                              parent=f"plot_{self.viewmodel.is_emission}", show=False, color=s.state.get_color())
        else:
            dpg.set_value(f"drag-{s.tag}", s.yshift)
        self.draw_sticks(s)
        self.draw_labels(s.tag)
        dpg.set_value(self.half_width_slider, SpecPlotter.get_half_width(self.viewmodel.is_emission))
        if tag not in self.matched_spectra_checks.keys() or not dpg.does_item_exist(self.matched_spectra_checks[tag]):
            self.matched_spectra_checks[tag] = dpg.add_checkbox(label=" "+s.name, default_value=s.is_matched(), parent=self.matched_spectra_node, before=self.matched_spectra_checks_spacer, callback=lambda sender, a, u: self.viewmodel.toggle_match_spec_contribution(s, a))
        else:
            dpg.set_value(self.matched_spectra_checks[tag], s.is_matched())
        dpg.get_item_callback(self.matched_spectra_checks[tag])(self.matched_spectra_checks[tag], dpg.get_value(self.matched_spectra_checks[tag]), None)

        for spec in self.viewmodel.state_plots.values():
            self.update_spectrum_color(spec)
        self.fit_y()

    def hide_spectrum(self, tag, hide):
        dpg.configure_item(tag, show=not hide)  # line series
        if hide:
            self.delete_sticks(tag)
            self.delete_labels(tag)
            dpg.configure_item(f"drag-{tag}", show=False)  # y drag line
            dpg.configure_item(f"drag-x-{tag}", show=False)  # x drag line
        else:
            self.draw_sticks(self.viewmodel.state_plots[tag])
            self.draw_labels(tag)
        # if not self.viewmodel.match_plot.matching_active:
        self.fit_y()

    def update_spectrum_color(self, spec):
        with dpg.theme() as self.spec_theme[spec.tag]:
            with dpg.theme_component(dpg.mvLineSeries):
                dpg.add_theme_color(dpg.mvPlotCol_Line, spec.state.get_color(), category=dpg.mvThemeCat_Plots)
            with dpg.theme_component(dpg.mvShadeSeries):
                dpg.add_theme_color(dpg.mvPlotCol_Fill, list(spec.state.get_color())[:3]+[120], category=dpg.mvThemeCat_Plots)
            with dpg.theme_component(dpg.mvCheckbox):
                dpg.add_theme_color(dpg.mvThemeCol_CheckMark, spec.state.get_color())
        dpg.bind_item_theme(spec.tag, self.spec_theme[spec.tag])
        dpg.configure_item(f"drag-{spec.tag}", color=spec.state.get_color())
        dpg.configure_item(f"drag-x-{spec.tag}", color=spec.state.get_color())
        for shade in [shade for shade in self.shade_plots if dpg.get_item_user_data(shade) == spec.tag]:
            dpg.bind_item_theme(shade, self.spec_theme[spec.tag])
        for shade in [shade for shade in self.shade_line_plots if dpg.get_item_user_data(shade) == spec.tag]:
            dpg.bind_item_theme(shade, self.spec_theme[spec.tag])
        for component in [c for c in self.component_plots if dpg.get_item_user_data(c) == spec.tag]:
            dpg.bind_item_theme(component, self.spec_theme[spec.tag])
        if self.matched_spectra_checks.get(spec.tag) is not None:
            dpg.bind_item_theme(self.matched_spectra_checks.get(spec.tag), self.spec_theme[spec.tag])

    def update_plot(self, state_plot, mark_dragged_plot=None, update_all=False, redraw_sticks=False, update_drag_lines=False, fit_y_axis=False):
        self.dragged_plot = mark_dragged_plot
        if dpg.does_item_exist(state_plot.tag):
            dpg.set_value(state_plot.tag, [state_plot.xdata, state_plot.ydata])
            if update_drag_lines or update_all:
                dpg.set_value(f"drag-{state_plot.tag}", state_plot.yshift)
                dpg.set_value(f"drag-x-{state_plot.tag}", state_plot.handle_x + state_plot.xshift)
                self.draw_labels(state_plot.tag)
            if redraw_sticks or update_all:
                self.draw_sticks(state_plot)
            self.update_labels(state_plot.tag)
            if fit_y_axis or update_all:
                self.vertical_slider_active = True
                self.fit_y()
            else:
                self.fit_y(dummy_series_update_only=True)

    def update_match_plot(self, match_plot):
        if Matcher.get(self.viewmodel.is_emission, 'show shade spectra', False):
            for shade in self.shade_plots:
                if dpg.get_item_user_data(shade) not in [s.tag for s in match_plot.contributing_state_plots]:
                    dpg.delete_item(shade)
                    self.shade_plots.remove(shade)
            for line in self.shade_line_plots:
                if dpg.get_item_user_data(line) not in [s.tag for s in match_plot.contributing_state_plots]:
                    dpg.delete_item(line)
                    self.shade_line_plots.remove(line)

            if len(match_plot.partial_y_datas) > 1:
                prev_y, _ = match_plot.partial_y_datas[0]
                for partial_y, tag in match_plot.partial_y_datas[1:]:
                    if dpg.does_item_exist(f"shade {tag}"):
                        dpg.set_value(f"shade {tag}", [match_plot.xdata, partial_y, prev_y, [], []])
                    else:
                        shade = dpg.add_shade_series(match_plot.xdata, partial_y, y2=prev_y, tag=f"shade {tag}", user_data=tag, parent=f"y_axis_{self.viewmodel.is_emission}", before=self.match_plot)
                        if tag in self.spec_theme.keys():
                            dpg.bind_item_theme(shade, self.spec_theme[tag])
                        if shade not in self.shade_plots:
                            self.shade_plots.append(shade)
                    if dpg.does_item_exist(f"shade line {tag}"):
                        dpg.set_value(f"shade line {tag}", [match_plot.xdata, partial_y])
                    else:
                        shade_line = dpg.add_line_series(match_plot.xdata, partial_y, tag=f"shade line {tag}", user_data=tag, parent=f"y_axis_{self.viewmodel.is_emission}", before=self.match_plot)
                        if tag in self.spec_theme.keys():
                            dpg.bind_item_theme(shade_line, self.spec_theme[tag])
                        if shade_line not in self.shade_line_plots:
                            self.shade_line_plots.append(shade_line)
                    prev_y = partial_y
        else:
            for shade in self.shade_plots:
                if dpg.does_item_exist(shade):
                    dpg.delete_item(shade)
            for shade in self.shade_line_plots:
                if dpg.does_item_exist(shade):
                    dpg.delete_item(shade)
            self.shade_plots = []
            self.shade_line_plots = []

        if Matcher.get(self.viewmodel.is_emission, 'show composite spectrum', False):
            dpg.show_item(self.match_plot)
            dpg.set_value(self.match_plot, [match_plot.xdata, match_plot.ydata])
            dpg.bind_item_theme(self.match_plot, self.white_line_series_theme)
        else:
            dpg.set_value(self.match_plot, [[], []])

        if not match_plot.dragging:
            dpg.set_value(self.match_plot_y_drag, match_plot.yshift)
        #     self.fit_y()

        for tag, check in self.matched_spectra_checks.items():
            dpg.set_value(check, self.viewmodel.match_plot.is_spectrum_matched(tag))

        for tag in self.viewmodel.state_plots.keys():
            if dpg.does_item_exist(tag) and dpg.is_item_shown(tag):
                if dpg.does_item_exist(f"drag-{tag}"):
                    dpg.configure_item(f"drag-{tag}", show=False)

        old_lines = self.match_lines
        self.match_lines = []
        if not match_plot.hidden and match_plot.matching_active:
            for peak in match_plot.exp_peaks:
                if peak.match is not None:
                    line_start = (peak.wavenumber, peak.intensity + 10/self.pixels_per_plot_y)
                    line_end = (peak.match[0], match_plot.yshift - 10/self.pixels_per_plot_y)
                    y_offset = abs(line_end[0] - line_start[0])*self.pixels_per_plot_x/self.pixels_per_plot_y
                    elbow = (line_start[0], line_end[1] - y_offset)

                    vl = dpg.draw_line(line_start, elbow, thickness=0, parent=self.plot, color=[120, 120, 200, 255])
                    dl = dpg.draw_line(elbow, line_end, thickness=0, parent=self.plot, color=[120, 120, 200, 255])
                    self.match_lines.append(vl)
                    self.match_lines.append(dl)
        for line in old_lines:
            dpg.delete_item(line)

        self.update_match_table()
# todo: stick spectra ui check not saved
    def delete_sticks(self, spec_tag=None):  # None: all of them.
        if spec_tag is not None:
            self.dragged_plot = spec_tag
            if dpg.does_item_exist(self.sticks_layer.get(spec_tag)):
                dpg.delete_item(self.sticks_layer[spec_tag])
        else:
            for s in self.viewmodel.state_plots:
                if dpg.does_item_exist(self.sticks_layer.get(s)):
                    dpg.delete_item(self.sticks_layer[s])
            self.redraw_sticks_on_release = True

    def on_drag_release(self):
        if self.dragged_plot is not None:
            spec = self.viewmodel.state_plots.get(self.dragged_plot)
            if spec is not None:
                dpg.set_value(f"drag-x-{spec.tag}", spec.handle_x + spec.xshift)
                self.draw_sticks(spec)
        elif self.exp_hovered and self.peak_edit_mode_enabled:
            if self.dragged_peak is not None:
                exp, peak = dpg.get_item_user_data(self.dragged_peak)
                exp.delete_peak(peak)
            for exp in ExperimentalSpectrum.spectra_list:
                if exp.is_emission == self.viewmodel.is_emission:
                    if exp.x_min <= self.mouse_plot_pos[0] <= exp.x_max:
                        if self.dragged_peak is None:
                            self.add_peak_drag_point(exp, exp.add_peak(self.mouse_plot_pos[0]))
                        else:
                            exp.add_peak(dpg.get_value(self.dragged_peak)[0])
                        break
            self.viewmodel.match_plot.assign_peaks()
        elif self.ctrl_pressed and self.hovered_spectrum is not None:
            self.viewmodel.toggle_match_spec_contribution(self.hovered_spectrum)

        for spec in self.viewmodel.state_plots.values():
            dpg.set_value(f"drag-{spec.tag}", spec.yshift)
            self.draw_sticks(spec)

        self.viewmodel.match_plot.dragging = False

        self.dragged_plot = None
        self.dragged_peak = None
        self.exp_hovered = False
        self.vertical_slider_active = False

    def toggle_labels(self, use_Gaussian_labels):
        if use_Gaussian_labels:
            if dpg.get_value(self.label_controls['show gaussian labels']):
                self.gaussian_labels = True
                self.labels = True
                for s in self.viewmodel.state_plots:
                    self.draw_labels(s)
                dpg.set_value(self.label_controls['show labels'], False)
            else:
                self.labels = False
                self.delete_labels()
        else:
            if dpg.get_value(self.label_controls['show labels']):
                self.gaussian_labels = False
                self.labels = True
                for s in self.viewmodel.state_plots:
                    self.draw_labels(s)
                dpg.set_value(self.label_controls['show gaussian labels'], False)
            else:
                self.labels = False
                self.delete_labels()
        Labels.set(self.viewmodel.is_emission, 'show labels', dpg.get_value(self.label_controls['show labels']))
        Labels.set(self.viewmodel.is_emission, 'show gaussian labels', dpg.get_value(self.label_controls['show gaussian labels']))

    def draw_labels(self, tag):
        if self.labels and dpg.does_item_exist(tag) and dpg.is_item_shown(tag):
            plot = f"plot_{self.viewmodel.is_emission}"
            for annotation in self.annotations.get(tag, {}).values():
                if dpg.does_item_exist(annotation):
                    dpg.delete_item(annotation)
                self.delete_label_line(tag, annotation)
            for drag_point in self.label_drag_points.get(tag, {}).values():
                if dpg.does_item_exist(drag_point):
                    dpg.delete_item(drag_point)
            self.annotations[tag] = {}
            self.label_drag_points[tag] = {}
            self.annotation_lines[tag] = {}

            font_size = Labels.settings[self.viewmodel.is_emission]['label font size']
            label_font = FontManager.get(font_size)
            dpg.bind_item_font(plot, label_font)

            state_plot = self.viewmodel.state_plots[tag]
            clusters = state_plot.spectrum.get_clusters()

            for cluster in clusters:
                cluster.construct_label(self.gaussian_labels, state_plot.yscale)
                text_size = dpg.get_text_size(cluster.label, font=label_font)
                cluster.set_label_size([text_size[0]/self.pixels_per_plot_x, text_size[1]/self.pixels_per_plot_y])
            state_plot.spectrum.decide_label_positions(gap_width=font_size/self.pixels_per_plot_x, gap_height=font_size/self.pixels_per_plot_y)

            clusters = state_plot.spectrum.get_clusters(in_placement_order=True)
            for cluster in clusters:
                if len(cluster.label):
                    peak_pos, label_pos = cluster.get_plot_pos(state_plot, gap_height=Labels.settings[self.viewmodel.is_emission]['label font size']/self.pixels_per_plot_y)
                    annotation = dpg.add_plot_annotation(label=cluster.label, default_value=label_pos, clamped=False, offset=(0, -cluster.height/2/self.pixels_per_plot_y), color=[0, 0, 0, 0], parent=plot, user_data=(cluster, state_plot.tag))  #[200, 200, 200, 0]
                    self.annotations[tag][peak_pos] = annotation
                    self.label_drag_points[tag][annotation] = dpg.add_drag_point(default_value=label_pos, color=[255, 255, 0], show_label=False, show=False, user_data=annotation, callback=lambda s, a, u: self.move_label(dpg.get_value(s)[:2], u, update_drag_point=False), parent=plot)
                    self.annotation_lines[tag][annotation] = self.draw_label_line(cluster, peak_pos)

    def move_label(self, pos, label, state_plot=None, update_drag_point=True):
        dpg.set_value(label, pos) # Optional: Save manual relative positions (& zoom state?)
        cluster, tag = dpg.get_item_user_data(label)
        if dpg.is_item_shown(tag):
            if state_plot is None:
                state_plot = self.viewmodel.state_plots.get(tag)
            self.delete_label_line(tag, label)
            peak_pos, label_pos = cluster.set_plot_pos(pos, state_plot)
            self.annotation_lines[tag][label] = self.draw_label_line(cluster, peak_pos)
            if update_drag_point:
                dpg.set_value(self.label_drag_points[tag][label], pos)

    def delete_label_line(self, tag, label):
        line_v, line_d = self.annotation_lines[tag].get(label, (None, None))
        if line_v is not None:
            if dpg.does_item_exist(line_v):
                dpg.delete_item(line_v)
        if line_d is not None:
            if dpg.does_item_exist(line_d):
                dpg.delete_item(line_d)
            if line_v is not None:
                del self.annotation_lines[tag][label]

    def draw_label_line(self, cluster, peak_pos):
        if abs(cluster.rel_x) > cluster.width / 2:
            if cluster.rel_x < 0:
                anchor_offset_x = cluster.rel_x + cluster.width / 2
            else:
                anchor_offset_x = cluster.rel_x - cluster.width / 2
        else:
            anchor_offset_x = 0
        anchor_offset_y = abs(anchor_offset_x*self.pixels_per_plot_x/self.pixels_per_plot_y)
        if anchor_offset_y * self.pixels_per_plot_y < 4:
            anchor_offset_x = 0
            anchor_offset_y = 0
        if peak_pos[1] + 5/self.pixels_per_plot_y > cluster.plot_y - anchor_offset_y:  # avoid downwards vertical lines
            x_spacing = (-5 if anchor_offset_x > 0 else 5)/self.pixels_per_plot_x
            start_pos = (peak_pos[0], peak_pos[1] + 5/self.pixels_per_plot_y)
            elbow_pos = (peak_pos[0], peak_pos[1] + 5/self.pixels_per_plot_y)
            label_pos = (peak_pos[0] + anchor_offset_x + x_spacing, peak_pos[1] + anchor_offset_y)
            if anchor_offset_x + x_spacing < 0:
                label_pos = elbow_pos
        else:
            start_pos = (peak_pos[0], peak_pos[1] + 5/self.pixels_per_plot_y)  # spacing
            elbow_pos = (peak_pos[0], cluster.plot_y - anchor_offset_y)
            label_pos = (peak_pos[0] + anchor_offset_x, cluster.plot_y)
        line_v = dpg.draw_line(start_pos, elbow_pos, parent=f"plot_{self.viewmodel.is_emission}", thickness=0., color=[200, 200, 255, 200])
        line_d = dpg.draw_line(elbow_pos, label_pos, parent=f"plot_{self.viewmodel.is_emission}", thickness=0., color=[200, 200, 255, 200])
        return line_v, line_d

    def update_labels(self, tag):
        if self.labels and dpg.is_item_shown(tag):
            state_plot = self.viewmodel.state_plots.get(tag)
            for label in self.annotations.get(tag, {}).values():
                self.delete_label_line(tag, label)
                cluster, _ = dpg.get_item_user_data(label)
                if cluster.y * state_plot.yscale < Labels.settings[self.viewmodel.is_emission]['peak intensity label threshold']:
                    dpg.hide_item(label)
                else:
                    dpg.show_item(label)
                    peak_pos, label_pos = cluster.get_plot_pos(state_plot, gap_height=Labels.settings[self.viewmodel.is_emission]['label font size']/self.pixels_per_plot_y)
                    dpg.set_value(label, label_pos)
                    dpg.set_value(self.label_drag_points[tag][label], label_pos)
                    self.annotation_lines[tag][label] = self.draw_label_line(cluster, peak_pos)

    def delete_labels(self, spec_tag=None):
        if spec_tag is None:
            for tag in self.viewmodel.state_plots.keys():
                for annotation in self.annotations.get(tag, {}).values():
                    if dpg.does_item_exist(annotation):
                        dpg.delete_item(annotation)
                    self.delete_label_line(tag, annotation)
                self.annotations[tag] = {}
                for drag_point in self.label_drag_points.get(tag, {}).values():
                    if dpg.does_item_exist(drag_point):
                        dpg.delete_item(drag_point)
                self.label_drag_points[tag] = {}
        else:
            for annotation in self.annotations.get(spec_tag, {}).values():
                if dpg.does_item_exist(annotation):
                    dpg.delete_item(annotation)
                self.delete_label_line(spec_tag, annotation)
            self.annotations[spec_tag] = {}
            for drag_point in self.label_drag_points.get(spec_tag, {}).values():
                if dpg.does_item_exist(drag_point):
                    dpg.delete_item(drag_point)
            self.label_drag_points[spec_tag] = {}

    def toggle_sticks(self, *args):
        if dpg.get_value(self.show_sticks):
            for s in self.viewmodel.state_plots.values():
                self.draw_sticks(s)
        else:
            self.delete_sticks()

    def draw_sticks(self, s):
        if dpg.is_item_shown(s.tag) and dpg.get_value(self.show_sticks):
            AsyncManager.submit_task(f"draw sticks {s.tag}", self.draw_sticks_inner, s)

    def draw_sticks_inner(self, s):
        if dpg.is_item_shown(s.tag):
            if dpg.get_value(self.show_sticks):
                if s.tag in self.sticks_layer and dpg.does_item_exist(self.sticks_layer[s.tag]):
                    dpg.delete_item(self.sticks_layer[s.tag])
                with dpg.draw_layer(parent=self.plot) as self.sticks_layer[s.tag]:
                    for stick_stack in s.sticks:
                        if len(stick_stack):
                            x = stick_stack[0] + s.xshift
                            y = s.yshift
                            for sub_stick in stick_stack[1]:
                                top = y+sub_stick[0]*s.yscale
                                if self.viewmodel.match_plot.matching_active:
                                    color = s.state.settings["color"]
                                else:
                                    color = adjust_color_for_dark_theme(sub_stick[1])+[160]
                                dpg.draw_line((x, y), (x, top), color=color, thickness=0.001)
                                y = top

    def configure_theme(self):
        with dpg.theme(tag=f"plot_theme_{self.viewmodel.is_emission}"):
            with dpg.theme_component(dpg.mvScatterSeries):
                dpg.add_theme_color(dpg.mvPlotCol_Line, (60, 150, 200, 0), category=dpg.mvThemeCat_Plots)
                dpg.add_theme_color(dpg.mvPlotCol_MarkerFill, (60, 150, 200, 0), category=dpg.mvThemeCat_Plots)
                dpg.add_theme_style(dpg.mvPlotStyleVar_Marker, dpg.mvPlotMarker_Square, category=dpg.mvThemeCat_Plots)
                dpg.add_theme_style(dpg.mvPlotStyleVar_MarkerSize, 1, category=dpg.mvThemeCat_Plots)
            with dpg.theme_component(dpg.mvDragLine):
                dpg.add_theme_color(dpg.mvPlotCol_Line, (60, 150, 200, 0), category=dpg.mvThemeCat_Plots)
            # with dpg.theme_component(dpg.mvLineSeries):
            #     dpg.add_theme_color(dpg.mvPlotCol_InlayText, (200, 0, 0))
        dpg.bind_item_theme(self.dummy_series, f"plot_theme_{self.viewmodel.is_emission}")

        with dpg.theme(tag=f"exp_spec_theme_{self.viewmodel.is_emission}"):
            with dpg.theme_component(dpg.mvLineSeries):
                dpg.add_theme_color(dpg.mvPlotCol_Line, (200, 200, 255, 255), category=dpg.mvThemeCat_Plots)

        with dpg.theme() as plot_settings_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 4, 4)
                dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 4, 4)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 6, 6)
            with dpg.theme_component(dpg.mvCollapsingHeader):
                dpg.add_theme_color(dpg.mvThemeCol_Header, [200, 200, 255, 80])
            # with dpg.theme_component(dpg.mvTreeNode):
            #     dpg.add_theme_color(dpg.mvThemeCol_Header, [200, 200, 255, 40])
            #     dpg.add_theme_color(dpg.mvThemeCol_ChildBg, [200, 200, 255, 40])
            #     dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 8, 8)
        dpg.bind_item_theme(self.plot_settings_group, plot_settings_theme)

        with dpg.theme() as expand_button_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Button, [200, 200, 255, 200])
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 2, 2)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 0, 0)
        dpg.bind_item_theme(self.expand_plot_settings_button, expand_button_theme)

        with dpg.theme() as self.match_table_theme:
            with dpg.theme_component(dpg.mvTable):
                dpg.add_theme_style(dpg.mvStyleVar_CellPadding, 6, 2)

    def on_scroll(self, direction):
        if self.hovered_spectrum_y_drag_line is not None:
            self.viewmodel.resize_spectrum(self.hovered_spectrum_y_drag_line, direction * self.adjustment_factor)
        elif self.hovered_x_drag_line is not None:
            half_width = self.viewmodel.resize_half_width(direction * self.adjustment_factor)
        elif dpg.is_item_hovered(self.plot):
            for tag in self.viewmodel.state_plots.keys():
                if dpg.is_item_shown(tag):
                    self.draw_labels(tag)
        else:
            for slider in [self.half_width_slider, self.vertical_spacing_slider, f"H stretches {self.viewmodel.is_emission} slider",
                            f"bends {self.viewmodel.is_emission} slider", f"others {self.viewmodel.is_emission} slider",
                            self.label_controls['peak intensity label threshold'], self.label_controls['stick label relative threshold'],
                            self.label_controls['stick label absolute threshold'], self.label_controls['label font size'],
                            self.peak_controls['peak prominence threshold'], self.peak_controls['peak width threshold'],
                            self.match_controls['peak intensity match threshold'], self.match_controls['distance match threshold']]:
                if dpg.is_item_hovered(slider):
                    step = (dpg.get_item_configuration(slider)['max_value'] - dpg.get_item_configuration(slider)['min_value'])/20
                    step = 10**round(math.log10(step))
                    value = max(0, dpg.get_value(slider) + step*direction*self.adjustment_factor)
                    dpg.set_value(slider, value)
                    dpg.get_item_callback(slider)(slider, value, dpg.get_item_user_data(slider))
                    self.disable_ui_update = True

    def show_drag_lines(self, show):
        self.show_all_drag_lines = show
        for tag in self.viewmodel.state_plots.keys():
            if dpg.is_item_shown(tag):
                if dpg.does_item_exist(f"drag-{tag}"):
                    dpg.configure_item(f"drag-{tag}", show=show)
                if dpg.does_item_exist(f"drag-x-{tag}"):
                    dpg.configure_item(f"drag-x-{tag}", show=show)
        if self.viewmodel.match_plot.matching_active:
            for s in self.viewmodel.match_plot.contributing_state_plots:
                if dpg.does_item_exist(f"drag-x-{s.tag}"):
                    dpg.configure_item(f"drag-x-{s.tag}", show=show)
            dpg.configure_item(self.match_plot_y_drag, show=show)

    def fit_y(self, dummy_series_update_only=False):
        ymin = -0.1
        ymax = 1.25
        if self.viewmodel.match_plot.matching_active:
            ymax = dpg.get_value(self.vertical_spacing_slider) + 1.5
        else:
            for tag, spec in self.viewmodel.state_plots.items():
                if dpg.is_item_shown(tag):
                    ymin = min(ymin, spec.yshift - 0.25)
                    ymax = max(ymax, spec.yshift + 1.25)
        y_axis = f"y_axis_{self.viewmodel.is_emission}"
        dpg.set_value(self.dummy_series, value=[[0, 0], [ymin, ymax]])
        if not dummy_series_update_only:
            dpg.fit_axis_data(y_axis)
