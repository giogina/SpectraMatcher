import dearpygui.dearpygui as dpg
from viewmodels.plots_overview_viewmodel import PlotsOverviewViewmodel
from utility.spectrum_plots import hsv_to_rgb


class PlotsOverview:
    def __init__(self, viewmodel: PlotsOverviewViewmodel):
        self.viewmodel = viewmodel
        self.viewmodel.set_callback("redraw plot", self.redraw_plot)
        self.viewmodel.set_callback("update plot", self.update_plot)
        self.custom_series = None
        self.spec_theme = {}
        self.hovered_spectrum = None

        with dpg.handler_registry() as self.mouse_handlers:
            dpg.add_mouse_wheel_handler(callback=lambda s, a, u: self.on_scroll(a))


        with dpg.table(header_row=False):
            dpg.add_table_column(init_width_or_weight=4)
            dpg.add_table_column(init_width_or_weight=1)

            with dpg.table_row():
                with dpg.table_cell():
                    with dpg.plot(label="Experimental spectra", height=-200, width=-1, anti_aliased=True, tag=f"plot_{self.viewmodel.is_emission}"):
                        # optionally create legend
                        dpg.add_plot_legend()

                        # REQUIRED: create x and y axes
                        dpg.add_plot_axis(dpg.mvXAxis, label="x", tag=f"x_axis_{self.viewmodel.is_emission}")
                        dpg.add_plot_axis(dpg.mvYAxis, label="y", tag=f"y_axis_{self.viewmodel.is_emission}")

                        dpg.set_axis_limits_auto(f"x_axis_{self.viewmodel.is_emission}")
                        dpg.set_axis_limits_auto(f"y_axis_{self.viewmodel.is_emission}")

                with dpg.table_cell():
                    # with dpg.group():
                        # dpg.add_checkbox(label="auto-zoom", tag=f"auto_zoom_check_{self.viewmodel.is_emission}", default_value=True, callback=lambda s, a, u: self.viewmodel.on_toggle_autozoom(a))
                    with dpg.group(horizontal=True):

                        for i in range(7):  # todo: react to state creation/deletion
                            with dpg.theme(tag=f"slider_theme_{self.viewmodel.is_emission} {i}"):  # TODO> state colors (start with these tho)
                                with dpg.theme_component(0):
                                    dpg.add_theme_color(dpg.mvThemeCol_FrameBg, hsv_to_rgb(i / 7.0, 0.5, 0.5))
                                    dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, hsv_to_rgb(i / 7.0, 0.9, 0.9))
                                    dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, hsv_to_rgb(i / 7.0, 0.7, 0.5))
                                    dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, hsv_to_rgb(i / 7.0, 0.6, 0.5))

                            dpg.add_slider_float(label=" ", default_value=1, vertical=True, max_value=1.0, height=160, format="")
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
            for s_tag, s in self.viewmodel.state_plots.items():
                # print(sender, mouse_y_plot_space, s.yshift, s.yshift+s.yscale)
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

    def redraw_plot(self):
        print("Redraw plot...")
        dpg.delete_item(f"y_axis_{self.viewmodel.is_emission}", children_only=True)

        with dpg.custom_series([0.0, 1.0, 2.0, 4.0, 5.0], [0.0, 1.0, 2.0, 4.0, 5.0], 2,
                               parent=f"y_axis_{self.viewmodel.is_emission}",
                               label="Custom Series", callback=self._custom_series_callback) as self.custom_series:
            self.tooltiptext = dpg.add_text("Current Point: ")

        xmin, xmax, ymin, ymax = self.viewmodel.get_zoom_range()

        dpg.add_scatter_series([xmin, xmax], [ymin, ymax], parent=f"y_axis_{self.viewmodel.is_emission}")
        dpg.bind_item_theme(dpg.last_item(), f"plot_theme_{self.viewmodel.is_emission}")
        if len(self.viewmodel.xydatas):
            for x_data, y_data in self.viewmodel.xydatas:
                print(x_data[:6], y_data[:6])
                dpg.add_line_series(x_data, y_data, parent=f"y_axis_{self.viewmodel.is_emission}")
        if self.viewmodel.state_plots == {}:
            dpg.fit_axis_data(f"x_axis_{self.viewmodel.is_emission}")

        dpg.add_line_series([], [], parent=f"y_axis_{self.viewmodel.is_emission}", tag=f"exp_overlay_{self.viewmodel.is_emission}")

        for s in self.viewmodel.state_plots.values():
            with dpg.theme() as self.spec_theme[s.tag]:
                with dpg.theme_component(dpg.mvLineSeries):
                    dpg.add_theme_color(dpg.mvPlotCol_Line, s.color, category=dpg.mvThemeCat_Plots)
            print("State plot:", s.xdata[:6], s.ydata[:6])
            xdata, ydata, max_x = s.get_xydata(xmin, xmax)  # truncated versions
            dpg.add_line_series(xdata, ydata, parent=f"y_axis_{self.viewmodel.is_emission}", tag=s.tag)  #, user_data=s, callback=lambda sender, a, u: self.viewmodel.on_spectrum_click(sender, a, u)
            dpg.bind_item_theme(s.tag, self.spec_theme[s.tag])
            if not dpg.does_item_exist(f"drag-{s.tag}"):
                dpg.add_drag_line(tag=f"drag-{s.tag}", vertical=False, default_value=s.yshift, user_data=s, callback=lambda sender, a, u: self.viewmodel.on_y_drag(dpg.get_value(sender), u), parent=f"plot_{self.viewmodel.is_emission}", show=False, color=s.color)
                print(f"line at max x: {max_x}")
                dpg.add_drag_line(tag=f"drag-x-{s.tag}", vertical=True, default_value=max_x, user_data=s, callback=lambda sender, a, u: self.viewmodel.on_x_drag(dpg.get_value(sender), u), parent=f"plot_{self.viewmodel.is_emission}", show=False, color=s.color)
            else:
                dpg.set_value(f"drag-{s.tag}", s.yshift)

        dpg.fit_axis_data(f"y_axis_{self.viewmodel.is_emission}")

                # TODO: Attach scroll event handler to drag lines: y line to scroll y scale; x line maybe for width?

    def update_plot(self, state_plot):
        dpg.set_value(state_plot.tag, [state_plot.xdata, state_plot.ydata])


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
        self.viewmodel.resize_spectrum(self.hovered_spectrum, direction)