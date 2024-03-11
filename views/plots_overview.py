import dearpygui.dearpygui as dpg

from utility.async_manager import AsyncManager
from viewmodels.plots_overview_viewmodel import PlotsOverviewViewmodel
from utility.spectrum_plots import hsv_to_rgb
from utility.wavenumber_corrector import WavenumberCorrector


class PlotsOverview:
    def __init__(self, viewmodel: PlotsOverviewViewmodel):
        self.viewmodel = viewmodel
        self.viewmodel.set_callback("redraw plot", self.redraw_plot)
        self.viewmodel.set_callback("update plot", self.update_plot)
        self.viewmodel.set_callback("add spectrum", self.add_spectrum)
        self.viewmodel.set_callback("delete sticks", self.delete_sticks)
        self.custom_series = None
        self.spec_theme = {}
        self.hovered_spectrum = None
        self.hovered_x_drag_line = None
        self.show__all_drag_lines = False  # show all drag lines
        self.line_series = []
        self.show_sticks = True  # todo: checkbox
        self.dragged_plot = None

        with dpg.handler_registry() as self.mouse_handlers:
            dpg.add_mouse_wheel_handler(callback=lambda s, a, u: self.on_scroll(a))
            dpg.add_mouse_release_handler(dpg.mvMouseButton_Left, callback=self.on_drag_release)
            dpg.add_key_down_handler(dpg.mvKey_Alt, callback=lambda s, a, u: self.show_drag_lines(u), user_data=True)
            dpg.add_key_release_handler(dpg.mvKey_Alt, callback=lambda s, a, u: self.show_drag_lines(u), user_data=False)

        with dpg.table(header_row=False):
            dpg.add_table_column(init_width_or_weight=4)
            dpg.add_table_column(init_width_or_weight=1)

            with dpg.table_row():
                with dpg.table_cell():
                    with dpg.plot(label="Experimental spectra", height=-100, width=-1, anti_aliased=True, tag=f"plot_{self.viewmodel.is_emission}"):
                        # optionally create legend
                        dpg.add_plot_legend()

                        # REQUIRED: create x and y axes
                        dpg.add_plot_axis(dpg.mvXAxis, label="wavenumber / cm⁻¹", tag=f"x_axis_{self.viewmodel.is_emission}")
                        dpg.add_plot_axis(dpg.mvYAxis, label="relative intensity", tag=f"y_axis_{self.viewmodel.is_emission}")

                        dpg.set_axis_limits_auto(f"x_axis_{self.viewmodel.is_emission}")
                        dpg.set_axis_limits_auto(f"y_axis_{self.viewmodel.is_emission}")

                        with dpg.custom_series([0.0, 1.0, 2.0, 4.0, 5.0], [0.0, 1.0, 2.0, 4.0, 5.0], 2,
                                               parent=f"y_axis_{self.viewmodel.is_emission}",
                                               callback=self._custom_series_callback) as self.custom_series:
                            self.tooltiptext = dpg.add_text("Current Point: ")

                        dpg.add_line_series([], [], parent=f"y_axis_{self.viewmodel.is_emission}", tag=f"exp_overlay_{self.viewmodel.is_emission}")

                with dpg.table_cell():
                    # with dpg.group():
                        # dpg.add_checkbox(label="auto-zoom", tag=f"auto_zoom_check_{self.viewmodel.is_emission}", default_value=True, callback=lambda s, a, u: self.viewmodel.on_toggle_autozoom(a))
                    with dpg.group(horizontal=False):

                        for i in range(7):  # todo: react to state creation/deletion
                            with dpg.theme(tag=f"slider_theme_{self.viewmodel.is_emission} {i}"):  # TODO> state colors (start with these tho)
                                with dpg.theme_component(0):
                                    dpg.add_theme_color(dpg.mvThemeCol_FrameBg, hsv_to_rgb(i / 7.0, 0.5, 0.5))
                                    dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, hsv_to_rgb(i / 7.0, 0.9, 0.9))
                                    dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, hsv_to_rgb(i / 7.0, 0.7, 0.5))
                                    dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, hsv_to_rgb(i / 7.0, 0.6, 0.5))
                        for i, x_scale_key in enumerate(['bends', 'H stretches', 'others']):
                            dpg.add_slider_float(label=x_scale_key, default_value=WavenumberCorrector.correction_factors.get(x_scale_key, 0), vertical=False, max_value=1.0, min_value=0.8, callback=lambda s, a, u: WavenumberCorrector.set_correction_factor(u, a), user_data=x_scale_key)  #, format=""
                            dpg.bind_item_theme(dpg.last_item(), f"slider_theme_{self.viewmodel.is_emission} {i}")
                self.configure_theme()

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
                if not self.show__all_drag_lines:
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

    def redraw_plot(self):
        print("Redraw plot...")
        # dpg.delete_item(f"y_axis_{self.viewmodel.is_emission}", children_only=True)
        for tag in self.line_series:
            dpg.delete_item(tag)
        self.line_series = []

        xmin, xmax, ymin, ymax = self.viewmodel.get_zoom_range()
        dpg.add_scatter_series([xmin, xmax], [ymin, ymax], parent=f"y_axis_{self.viewmodel.is_emission}")
        self.line_series.append(dpg.last_item())
        dpg.bind_item_theme(dpg.last_item(), f"plot_theme_{self.viewmodel.is_emission}")

        if len(self.viewmodel.xydatas):
            for x_data, y_data in self.viewmodel.xydatas:
                dpg.add_line_series(x_data, y_data, parent=f"y_axis_{self.viewmodel.is_emission}")
                self.line_series.append(dpg.last_item())
        if self.viewmodel.state_plots == {}:
            dpg.fit_axis_data(f"x_axis_{self.viewmodel.is_emission}")

        for s in self.viewmodel.state_plots.keys():
            self.add_spectrum(s)
        dpg.fit_axis_data(f"y_axis_{self.viewmodel.is_emission}")

    def add_spectrum(self, tag):
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

    def update_plot(self, state_plot, mark_dragged_plot=None, redraw_sticks=False):
        self.dragged_plot = mark_dragged_plot
        dpg.set_value(state_plot.tag, [state_plot.xdata, state_plot.ydata])
        if redraw_sticks:
            AsyncManager.submit_task(f"draw sticks {state_plot.tag}", self.draw_sticks, state_plot)

    def delete_sticks(self, spec_tag):
        self.dragged_plot = spec_tag
        if dpg.does_item_exist(f"sticks-{spec_tag}"):
            dpg.delete_item(f"sticks-{spec_tag}")

    def on_drag_release(self):
        if self.dragged_plot is not None:
            spec = self.viewmodel.state_plots.get(self.dragged_plot)
            if spec is not None:
                dpg.set_value(f"drag-x-{spec.tag}", spec.handle_x + spec.xshift)
                AsyncManager.submit_task(f"draw sticks {self.dragged_plot}", self.draw_sticks, spec)
        self.dragged_plot = None

    def draw_sticks(self, s):
        if self.show_sticks:
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
                            dpg.draw_line((x, y), (x, top), color=[255-c for c in sub_stick[1]], thickness=0.001)
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

    def on_scroll(self, direction):
        if self.hovered_spectrum is not None:
            self.viewmodel.resize_spectrum(self.hovered_spectrum, direction)
        elif self.hovered_x_drag_line is not None:
            self.viewmodel.resize_half_width(direction)

    def show_drag_lines(self, show):
        self.show__all_drag_lines = show
        for tag in self.viewmodel.state_plots.keys():
            if dpg.does_item_exist(f"drag-{tag}"):
                dpg.configure_item(f"drag-{tag}", show=show)
            if dpg.does_item_exist(f"drag-x-{tag}"):
                dpg.configure_item(f"drag-x-{tag}", show=show)