import dearpygui.dearpygui as dpg
from viewmodels.plots_overview_viewmodel import PlotsOverviewViewmodel
from utility.spectrum_plots import hsv_to_rgb


class PlotsOverview:
    def __init__(self, viewmodel: PlotsOverviewViewmodel):
        self.viewmodel = viewmodel
        self.viewmodel.set_callback("update plot", self.update_plot)

        with dpg.table(header_row=False):
            dpg.add_table_column(init_width_or_weight=4)
            dpg.add_table_column(init_width_or_weight=1)

            with dpg.table_row():
                with dpg.table_cell():
                    with dpg.plot(label="Experimental spectra", height=-200, width=-1, anti_aliased=True):
                        # optionally create legend
                        dpg.add_plot_legend()

                        # REQUIRED: create x and y axes
                        dpg.add_plot_axis(dpg.mvXAxis, label="x", tag=f"x_axis_{self.viewmodel.is_emission}")
                        dpg.set_axis_limits(dpg.last_item(), -300, 3000)
                        dpg.add_plot_axis(dpg.mvYAxis, label="y", tag=f"y_axis_{self.viewmodel.is_emission}")
                        dpg.set_axis_limits(dpg.last_item(), 0, 1)  # TODO: only on spectrum add/remove, zoom accordingly

                with dpg.table_cell():
                    with dpg.group():
                        dpg.add_checkbox(label="auto-zoom", tag=f"auto_zoom_check_{self.viewmodel.is_emission}", default_value=True, callback=lambda s, a, u: self.viewmodel.on_toggle_autozoom(a))
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

    def update_plot(self):
        print("Update plot...")
        dpg.delete_item(f"y_axis_{self.viewmodel.is_emission}", children_only=True)  # todo: change value rather than delete

        if len(self.viewmodel.xydatas):
            for x_data, y_data in self.viewmodel.xydatas:
                print(x_data[:6], y_data[:6])
                dpg.add_line_series(x_data, y_data, parent=f"y_axis_{self.viewmodel.is_emission}")
            dpg.set_axis_limits_auto(f"x_axis_{self.viewmodel.is_emission}")
            dpg.set_axis_limits_auto(f"y_axis_{self.viewmodel.is_emission}")

        for s in self.viewmodel.state_plots:
            print("State plot:", s.xdata[:6], s.ydata[:6])
            dpg.add_line_series(s.xdata, s.ydata, parent=f"y_axis_{self.viewmodel.is_emission}")
