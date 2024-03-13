import dearpygui.dearpygui as dpg

from utility.async_manager import AsyncManager
from utility.font_manager import FontManager
from utility.labels import Labels
from utility.matcher import Matcher
from viewmodels.plots_overview_viewmodel import PlotsOverviewViewmodel, WavenumberCorrector
from utility.spectrum_plots import hsv_to_rgb, adjust_color_for_dark_theme, SpecPlotter


class PlotsOverview:
    def __init__(self, viewmodel: PlotsOverviewViewmodel):
        self.viewmodel = viewmodel
        self.viewmodel.set_callback("redraw plot", self.redraw_plot)
        self.viewmodel.set_callback("update plot", self.update_plot)
        self.viewmodel.set_callback("add spectrum", self.add_spectrum)
        self.viewmodel.set_callback("delete sticks", self.delete_sticks)
        self.viewmodel.set_callback("redraw sticks", self.draw_sticks)
        self.viewmodel.set_callback("post load update", self.set_ui_values_from_settings)
        self.viewmodel.set_callback("update labels", self.draw_labels)
        self.custom_series = None
        self.spec_theme = {}
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
        self.label_controls = {}
        self.match_controls = {}

        with dpg.handler_registry() as self.mouse_handlers:
            dpg.add_mouse_wheel_handler(callback=lambda s, a, u: self.on_scroll(a))
            dpg.add_mouse_release_handler(dpg.mvMouseButton_Left, callback=self.on_drag_release)
            dpg.add_key_down_handler(dpg.mvKey_Alt, callback=lambda s, a, u: self.show_drag_lines(u), user_data=True)
            dpg.add_key_release_handler(dpg.mvKey_Alt, callback=lambda s, a, u: self.show_drag_lines(u), user_data=False)

        with dpg.table(header_row=False, borders_innerV=True, resizable=True):
            dpg.add_table_column(init_width_or_weight=4)
            dpg.add_table_column(init_width_or_weight=1)

            with dpg.table_row():
                with dpg.table_cell():
                    with dpg.plot(label="Experimental spectra", height=-1, width=-1, anti_aliased=True, tag=f"plot_{self.viewmodel.is_emission}"):
                        # optionally create legend
                        dpg.add_plot_legend()

                        # REQUIRED: create x and y axes
                        dpg.add_plot_axis(dpg.mvXAxis, label="wavenumber / cm⁻¹", tag=f"x_axis_{self.viewmodel.is_emission}", no_gridlines=True)
                        dpg.add_plot_axis(dpg.mvYAxis, label="relative intensity", tag=f"y_axis_{self.viewmodel.is_emission}", no_gridlines=True)

                        dpg.set_axis_limits_auto(f"x_axis_{self.viewmodel.is_emission}")
                        dpg.set_axis_limits_auto(f"y_axis_{self.viewmodel.is_emission}")

                        with dpg.custom_series([0.0, 1.0, 2.0, 4.0, 5.0], [0.0, 1.0, 2.0, 4.0, 5.0], 2,
                                               parent=f"y_axis_{self.viewmodel.is_emission}",
                                               callback=self._custom_series_callback) as self.custom_series:
                            self.tooltiptext = dpg.add_text("Current Point: ")

                        dpg.add_line_series([], [], parent=f"y_axis_{self.viewmodel.is_emission}", tag=f"exp_overlay_{self.viewmodel.is_emission}")

                with dpg.table_cell():
                    with dpg.group(horizontal=False) as self.plot_settings_group:
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

                        self.half_width_slider = dpg.add_slider_float(label="Half-width", min_value=0.1, max_value=60, callback=lambda s, a, u: self.viewmodel.resize_half_width(a, relative=False))
                        dpg.add_spacer(height=16)
                        with dpg.collapsing_header(label="Anharmonic corrections", default_open=True):
                            dpg.add_spacer(height=6)
                            with dpg.group(horizontal=True):
                                dpg.add_spacer(width=6)
                                with dpg.group(horizontal=False):
                                    for i, x_scale_key in enumerate(['H stretches', 'bends', 'others']):
                                        dpg.add_slider_float(label=[' H-* stretches', ' Bends', ' Others'][i], tag=f"{x_scale_key} {self.viewmodel.is_emission} slider", vertical=False, max_value=1.0, min_value=0.8, callback=lambda s, a, u: self.viewmodel.change_correction_factor(u, a), user_data=x_scale_key)  #, format=""
                                        dpg.bind_item_theme(dpg.last_item(), f"slider_theme_{self.viewmodel.is_emission} {['Red', 'Blue', 'Green'][i]}")
                                    self.show_sticks = dpg.add_checkbox(label="Show stick spectra", callback=self.toggle_sticks)
                        dpg.add_spacer(height=16)
                        with dpg.collapsing_header(label="Label settings", default_open=True):
                            # dpg.add_spacer(height=6)
                            with dpg.group(horizontal=True):
                                dpg.add_spacer(width=6)
                                with dpg.group(horizontal=False):
                                    self.label_controls['show labels'] = dpg.add_checkbox(label=" Show labels", callback=lambda s, a, u: self.toggle_labels(u), user_data=False, default_value=Labels.settings[self.viewmodel.is_emission].get('show labels', False))
                                    self.label_controls['show gaussian labels'] = dpg.add_checkbox(label=" Show Gaussian labels", callback=lambda s, a, u: self.toggle_labels(u), user_data=True, default_value=Labels.settings[self.viewmodel.is_emission].get('show gaussian labels', False))
                                    self.label_controls['peak intensity label threshold'] = dpg.add_slider_float(label=" Intensity threshold", min_value=0, max_value=0.2, default_value=Labels.settings[self.viewmodel.is_emission].get('peak intensity label threshold', 0.03), callback=lambda s, a, u: Labels.set(self.viewmodel.is_emission, 'peak intensity label threshold', a))
                                    self.label_controls['peak separation threshold'] = dpg.add_slider_float(label=" Separation thr.", min_value=0, max_value=1, default_value=Labels.settings[self.viewmodel.is_emission].get('peak separation threshold', 0.8), callback=lambda s, a, u: Labels.set(self.viewmodel.is_emission, 'peak separation threshold', a))
                                    self.label_controls['stick label relative threshold'] = dpg.add_slider_float(label=" Stick rel. thr.", min_value=0, max_value=0.1, default_value=Labels.settings[self.viewmodel.is_emission].get('stick label relative threshold', 0.1), callback=lambda s, a, u: Labels.set(self.viewmodel.is_emission, 'stick label relative threshold', a))
                                    self.label_controls['stick label absolute threshold'] = dpg.add_slider_float(label=" Stick abs. thr.", min_value=0, max_value=0.1, default_value=Labels.settings[self.viewmodel.is_emission].get('stick label absolute threshold', 0.001), callback=lambda s, a, u: Labels.set(self.viewmodel.is_emission, 'stick label absolute threshold', a))
                                    self.label_controls['label font size'] = dpg.add_slider_int(label=" Font size", min_value=12, max_value=24, default_value=Labels.settings[self.viewmodel.is_emission].get('label font size', 18), callback=lambda s, a, u: Labels.set(self.viewmodel.is_emission, 'label font size', a))
                                    # self.label_controls['axis font size'] = dpg.add_slider_int(label=" Axis font size", min_value=12, max_value=24, default_value=Labels.settings[self.viewmodel.is_emission].get('axis font size', 18), callback=lambda s, a, u: Labels.set(self.viewmodel.is_emission, 'axis font size', a))
                                    dpg.add_button(label="Defaults", width=-1, callback=self.restore_label_defaults)

                        dpg.add_spacer(height=16)
                        with dpg.collapsing_header(label="Match settings", default_open=True):
                            # dpg.add_spacer(height=6)
                            with dpg.group(horizontal=True):
                                dpg.add_spacer(width=6)
                                with dpg.group(horizontal=False):
                                    self.match_controls['peak intensity match threshold'] = dpg.add_slider_float(label=" Min. Intensity", min_value=0, max_value=0.2, default_value=Matcher.settings[self.viewmodel.is_emission].get('peak intensity match threshold', 0.03), callback=lambda s, a, u: Matcher.set(self.viewmodel.is_emission, 'peak intensity match threshold', a))
                                    self.match_controls['distance match threshold'] = dpg.add_slider_float(label=" Max. Distance", min_value=0, max_value=100, default_value=Matcher.settings[self.viewmodel.is_emission].get('distance match threshold', 30), callback=lambda s, a, u: Matcher.set(self.viewmodel.is_emission, 'distance match threshold', a))
                                    dpg.add_button(label="Defaults", width=-1, callback=self.restore_matcher_defaults)
                                    dpg.add_button(label="Save as table", callback=self.print_table, width=-1)
                self.configure_theme()

    def restore_label_defaults(self):
        Labels.restore_defaults(self.viewmodel.is_emission)
        self.set_ui_values_from_settings(labels=True)

    def restore_matcher_defaults(self):
        Matcher.restore_defaults(self.viewmodel.is_emission)
        self.set_ui_values_from_settings(matcher=True)

    def print_table(self):
        pass
        # todo

    def set_ui_values_from_settings(self, x_scale=False, half_width=False, labels=False, matcher=False):
        load_all = True not in (x_scale, half_width, labels, matcher)

        if load_all or x_scale:
            for i, x_scale_key in enumerate(['bends', 'H stretches', 'others']):
                dpg.set_value(f"{x_scale_key} {self.viewmodel.is_emission} slider", value=WavenumberCorrector.correction_factors[self.viewmodel.is_emission].get(x_scale_key, 0))
        if load_all or half_width:
            dpg.set_value(self.half_width_slider, SpecPlotter.get_half_width(self.viewmodel.is_emission))
        if load_all or labels:
            for key, item in self.label_controls.items():
                value = Labels.settings[self.viewmodel.is_emission].get(key)
                dpg.set_value(item, value)
                if not (key in ('show labels', 'show gaussian labels') and value is False and (Labels.settings[self.viewmodel.is_emission].get('show labels') or Labels.settings[self.viewmodel.is_emission].get('show gaussian labels'))):
                    print("Callback ", key, value, dpg.get_item_callback(item))
                    if dpg.get_item_callback(item) is not None:
                        dpg.get_item_callback(item)(item, value, dpg.get_item_user_data(item))
        if load_all or matcher:
            for key, item in self.match_controls.items():
                value = Matcher.settings[self.viewmodel.is_emission].get(key)
                dpg.set_value(item, value)
                if dpg.get_item_callback(item) is not None:
                    dpg.get_item_callback(item)(item, value, dpg.get_item_user_data(item))

    def _custom_series_callback(self, sender, app_data):
        try:
            _helper_data = app_data[0]
            transformed_x = app_data[1]
            transformed_y = app_data[2]
            mouse_x_plot_space = _helper_data["MouseX_PlotSpace"]
            mouse_y_plot_space = _helper_data["MouseY_PlotSpace"]
            mouse_x_pixel_space = _helper_data["MouseX_PixelSpace"]
            mouse_y_pixel_space = _helper_data["MouseY_PixelSpace"]
            dpg.delete_item(sender, children_only=True, slot=2)
            dpg.push_container_stack(sender)
            # dpg.configure_item(sender, tooltip=False)
            dpg.set_value(f"exp_overlay_{self.viewmodel.is_emission}", [[], []])
            self.hovered_spectrum = None
            self.hovered_x_drag_line = None
            for s_tag, s in self.viewmodel.state_plots.items():
                if not dpg.does_item_exist(f"drag-x-{s_tag}"):
                    return  # drawing is currently underway
                if not self.show_all_drag_lines:
                    if abs(dpg.get_value(f"drag-{s_tag}") - mouse_y_plot_space) < 0.02:
                        dpg.show_item(f"drag-{s_tag}")
                        self.hovered_spectrum = s_tag
                    elif abs(dpg.get_value(f"drag-{s_tag}") - mouse_y_plot_space) > 0.1:
                        dpg.hide_item(f"drag-{s_tag}")
                    if abs(dpg.get_value(f"drag-x-{s_tag}") - mouse_x_plot_space) > 50:
                        dpg.hide_item(f"drag-x-{s_tag}")

                if s.yshift - 0.02 <= mouse_y_plot_space <= s.yshift+s.yscale:
                    if abs(dpg.get_value(f"drag-x-{s_tag}") - mouse_x_plot_space) < 10:
                        dpg.show_item(f"drag-x-{s_tag}")
                        self.hovered_x_drag_line = s_tag
                    if not -0.2 < s.yshift <= 0.9:
                        dpg.set_value(f"exp_overlay_{self.viewmodel.is_emission}", [s.xdata, s.ydata - s.yshift])
                        dpg.bind_item_theme(f"exp_overlay_{self.viewmodel.is_emission}", self.spec_theme[s.tag])

                    # dpg.draw_circle((mouse_x_pixel_space, mouse_y_pixel_space), 30)
                    dpg.configure_item(sender, tooltip=False)
                    dpg.configure_item(sender, tooltip=True)
                    dpg.set_value(self.tooltiptext, f"Diff: {abs(dpg.get_value(f'drag-x-{s_tag}') - mouse_x_plot_space)}")
            # for i in range(0, len(transformed_x)):
            #     dpg.draw_text((transformed_x[i] + 15, transformed_y[i] - 15), str(i), size=20)
            #     dpg.draw_circle((transformed_x[i], transformed_y[i]), 15, fill=(50+i*5, 50+i*50, 0, 255))
            #     if mouse_x_pixel_space < transformed_x[i] + 15 and mouse_x_pixel_space > transformed_x[
            #         i] - 15 and mouse_y_pixel_space > transformed_y[i] - 15 and mouse_y_pixel_space < transformed_y[i] + 15:
            #         dpg.draw_circle((transformed_x[i], transformed_y[i]), 30)
            #         dpg.configure_item(sender, tooltip=True)
            #         dpg.set_value(self.tooltiptext, "Current Point: " + str(i))
            dpg.pop_container_stack()
        except Exception as e:
            print(f"Exception in custom series callback: {e}")

    def sticks_callback(self, sender, app_data):
        return
# TODO: Preview plot fixable (ctrl+click or button on plot overview panel), in addition to hover plot
    # TODO: Hover plot only when mouse is in plot area
    def redraw_plot(self):  # todo: what if auto_fit was false to begin with, maybe truncating spectra wouldn't be necessary?
        print("Redraw plot...")
        # dpg.delete_item(f"y_axis_{self.viewmodel.is_emission}", children_only=True)
        for tag in self.line_series:
            dpg.delete_item(tag)
        self.line_series = []

        xmin, xmax, ymin, ymax = self.viewmodel.get_zoom_range()
        dpg.add_scatter_series([xmin, xmax], [ymin, ymax], parent=f"y_axis_{self.viewmodel.is_emission}")
        self.line_series.append(dpg.last_item())
        dpg.bind_item_theme(dpg.last_item(), f"plot_theme_{self.viewmodel.is_emission}")

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

    def add_spectrum(self, tag):  # TODO: erase pop-up menu when this spectrum comes into view
        xmin, xmax, ymin, ymax = self.viewmodel.get_zoom_range()
        s = self.viewmodel.state_plots[tag]
        if not dpg.does_item_exist(tag):
            with dpg.theme() as self.spec_theme[s.tag]:
                with dpg.theme_component(dpg.mvLineSeries):
                    dpg.add_theme_color(dpg.mvPlotCol_Line, s.color, category=dpg.mvThemeCat_Plots)
            xdata, ydata = s.get_xydata(xmin, xmax)  # truncated versions
            dpg.add_line_series(xdata, ydata, label=s.name, parent=f"y_axis_{self.viewmodel.is_emission}", tag=s.tag)  # , user_data=s, callback=lambda sender, a, u: self.viewmodel.on_spectrum_click(sender, a, u)
            self.line_series.append(s.tag)
            dpg.bind_item_theme(s.tag, self.spec_theme[s.tag])
        else:
            self.update_plot(s)
        if not dpg.does_item_exist(f"drag-{s.tag}"):
            dpg.add_drag_line(tag=f"drag-{s.tag}", vertical=False, show_label=False, default_value=s.yshift,
                              user_data=s,
                              callback=lambda sender, a, u: self.viewmodel.on_y_drag(dpg.get_value(sender), u),
                              parent=f"plot_{self.viewmodel.is_emission}", show=False, color=s.color)
            dpg.add_drag_line(tag=f"drag-x-{s.tag}", vertical=True, show_label=False, default_value=s.handle_x, user_data=s,
                              callback=lambda sender, a, u: self.viewmodel.on_x_drag(dpg.get_value(sender), u),
                              parent=f"plot_{self.viewmodel.is_emission}", show=False, color=s.color)
        else:
            dpg.set_value(f"drag-{s.tag}", s.yshift)
        self.draw_sticks(s)
        self.draw_labels(s.tag)
        print(self.labels)
        dpg.fit_axis_data(f"y_axis_{self.viewmodel.is_emission}")
        dpg.set_value(self.half_width_slider, SpecPlotter.get_half_width(self.viewmodel.is_emission))

    def update_plot(self, state_plot, mark_dragged_plot=None, redraw_sticks=False, update_drag_lines=False):
        self.dragged_plot = mark_dragged_plot
        dpg.set_value(state_plot.tag, [state_plot.xdata, state_plot.ydata])
        if update_drag_lines:
            dpg.set_value(f"drag-x-{state_plot.tag}", state_plot.handle_x + state_plot.xshift)
        if redraw_sticks:
            AsyncManager.submit_task(f"draw sticks {state_plot.tag}", self.draw_sticks, state_plot)

    def delete_sticks(self, spec_tag=None):  # None: all of them.
        if spec_tag is not None:
            self.dragged_plot = spec_tag
            if dpg.does_item_exist(f"sticks-{spec_tag}"):
                dpg.delete_item(f"sticks-{spec_tag}")
        else:
            for s in self.viewmodel.state_plots:
                if dpg.does_item_exist(f"sticks-{s}"):
                    dpg.delete_item(f"sticks-{s}")
            self.redraw_sticks_on_release = True

    def on_drag_release(self):
        if self.dragged_plot is not None:
            spec = self.viewmodel.state_plots.get(self.dragged_plot)
            if spec is not None:
                dpg.set_value(f"drag-x-{spec.tag}", spec.handle_x + spec.xshift)
                # AsyncManager.submit_task(f"draw sticks {self.dragged_plot}", self.draw_sticks, spec)
                self.draw_sticks(spec)
        self.dragged_plot = None

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
        if self.labels:
            plot = f"plot_{self.viewmodel.is_emission}"
            for annotation in self.annotations.get(tag, []):
                if dpg.does_item_exist(annotation):
                    dpg.delete_item(annotation)
            for line in self.annotation_lines.get(tag, []):
                if dpg.does_item_exist(line):
                    dpg.delete_item(line)
            self.annotations[tag] = []
            self.annotation_lines[tag] = []
            state_plot = self.viewmodel.state_plots[tag]
            clusters = state_plot.get_clusters()
            label_font = FontManager.get(Labels.settings[self.viewmodel.is_emission]['label font size'])
            dpg.bind_item_font(plot, label_font)
            for cluster in clusters:
                if cluster.y > Labels.settings[self.viewmodel.is_emission]['peak intensity label threshold']:
                    label = cluster.get_label(self.gaussian_labels)
                    if len(label):
                        self.annotations[tag].append(dpg.add_plot_annotation(label=label, default_value=(cluster.x, state_plot.yshift + cluster.y_max+0.05), clamped=False, offset=(0, -3), color=[200, 200, 200, 0], parent=plot))
                        self.annotation_lines[tag].append(dpg.draw_line((cluster.x, state_plot.yshift+cluster.y+0.03), (cluster.x, state_plot.yshift+cluster.y_max+0.05), parent=plot))
                        # TODO: Hover over annotation to see extra info about that vibration
                        #  Ctrl-drag (or direct drag?) to change its position (value)
                        #  Equal distribution of labels in available y space
                        #  Nicer o/digit chars and double-chars

            # dpg.bind_item_font(f"x_axis_{self.viewmodel.is_emission}", FontManager.get(Labels.settings[self.viewmodel.is_emission]['axis font size']))


    def delete_labels(self):
        for tag in self.viewmodel.state_plots.keys():
            for annotation in self.annotations.get(tag, []):
                if dpg.does_item_exist(annotation):
                    dpg.delete_item(annotation)
            self.annotations[tag] = []  # todo: do this on scroll/drag operations

    def toggle_sticks(self, *args):
        if dpg.get_value(self.show_sticks):
            for s in self.viewmodel.state_plots.values():
                self.draw_sticks(s)
        else:
            self.delete_sticks()

    def draw_sticks(self, s):
        if dpg.get_value(self.show_sticks):
            plot = f"plot_{self.viewmodel.is_emission}"
            if dpg.does_item_exist(f"sticks-{s.tag}"):
                dpg.delete_item(f"sticks-{s.tag}")
            with dpg.draw_layer(tag=f"sticks-{s.tag}", parent=plot):
                for stick_stack in s.sticks:
                    if len(stick_stack):
                        x = stick_stack[0] + s.xshift
                        y = s.yshift
                        for sub_stick in stick_stack[1]:
                            top = y+sub_stick[0]*s.yscale
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

        dpg.bind_item_theme(self.plot_settings_group, plot_settings_theme)

    def on_scroll(self, direction):
        if self.hovered_spectrum is not None:
            self.viewmodel.resize_spectrum(self.hovered_spectrum, direction)
        elif self.hovered_x_drag_line is not None:
            half_width = self.viewmodel.resize_half_width(direction)
            dpg.set_value(self.half_width_slider, half_width)

    def show_drag_lines(self, show):
        self.show_all_drag_lines = show
        for tag in self.viewmodel.state_plots.keys():
            if dpg.does_item_exist(f"drag-{tag}"):
                dpg.configure_item(f"drag-{tag}", show=show)
            if dpg.does_item_exist(f"drag-x-{tag}"):
                dpg.configure_item(f"drag-x-{tag}", show=show)