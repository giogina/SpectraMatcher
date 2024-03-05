import dearpygui.dearpygui as dpg
from viewmodels.plots_overview_viewmodel import PlotsOverviewViewmodel


class PlotsOverview:
    def __init__(self, viewmodel: PlotsOverviewViewmodel):
        self.viewmodel = viewmodel
        self.viewmodel.set_callback("update plot", self.update_plot)

        with dpg.plot(label="Experimental spectra", height=800, width=-1):
            # optionally create legend
            dpg.add_plot_legend()

            # REQUIRED: create x and y axes
            dpg.add_plot_axis(dpg.mvXAxis, label="x")
            dpg.add_plot_axis(dpg.mvYAxis, label="y", tag=f"y_axis_{self.viewmodel.is_emission}")


    def update_plot(self):
        print("Update plot...", self.viewmodel.xdata)
        dpg.delete_item(f"y_axis_{self.viewmodel.is_emission}", children_only=True)  # todo: change value rather than delete

        if len(self.viewmodel.xdata):
            for y_data in self.viewmodel.ydatas:
                print(self.viewmodel.xdata[:3], y_data[:3])
                dpg.add_line_series(self.viewmodel.xdata, y_data, label="exp", parent=f"y_axis_{self.viewmodel.is_emission}")