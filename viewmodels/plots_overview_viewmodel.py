from models.experimental_spectrum import ExperimentalSpectrum
from models.state import State
import numpy as np


def noop(*args, **kwargs):
    pass


class StatePlot:
    def __init__(self, state: State, is_emission: bool, xshift=0, yshift=1):
        print(f"Making StatePlot for {state.name}")
        self.tag = f"{state.name} - {is_emission} plot"
        self.spectrum = state.get_spectrum(is_emission)
        self.name = state.name
        self._base_xdata = self.spectrum.x_data
        self._base_ydata = self.spectrum.y_data
        self.xshift = xshift
        self.yshift = yshift
        self.yscale = 1
        self.color = state.color
        self.xdata = self._compute_x_data()
        self.ydata = self._compute_y_data()
        self.handle_x = 0

    def _compute_x_data(self):
        return self._base_xdata + self.xshift

    def _compute_y_data(self):
        return (self._base_ydata * self.yscale) + self.yshift

    def set_x_shift(self, xshift):
        self.xshift = xshift - self.handle_x
        self.xdata = self._compute_x_data()

    def set_y_shift(self, yshift):
        self.yshift = yshift
        self.ydata = self._compute_y_data()

    def resize_y_scale(self, direction):
        self.yscale += direction * 0.1
        self.yscale = max(0, self.yscale)
        self.ydata = self._compute_y_data()

    def get_xydata(self, xmin, xmax):
        if self.xdata[0] < xmin:
            step = float(self.xdata[1] - self.xdata[0])
            start = min(int((xmin - self.xdata[0]) / step), len(self.xdata)-1)
        else:
            start = 0
        if self.xdata[-1] > xmax:
            step = float(self.xdata[1] - self.xdata[0])
            stop = max(int((xmax - self.xdata[-1]) / step), -len(self.xdata)+1)
        else:
            stop = len(self.xdata)
        max_index = np.where(self.ydata[start:stop]==max(self.ydata[start:stop]))[0][0]
        max_x = self.xdata[start:stop][max_index]
        self.handle_x = max_x
        return self.xdata[start:stop], self.ydata[start:stop], max_x


class PlotsOverviewViewmodel:
    def __init__(self, project, is_emission: bool):
        self._project = project
        self.is_emission = is_emission
        print("Plots overview viewmodel created: ", is_emission)
        # self._project.add_observer(self, "state data changed")
        ExperimentalSpectrum.add_observer(self)
        State.add_observer(self)
        self._callbacks = {
            "update plot": noop,
            "redraw plot": noop
        }

        self.xydatas = []  # experimental x, y
        self.state_plots = {}  # whole State instances, for x, y, color, etc.
        self._auto_zoom = True

    def update(self, event, *args):
        print(f"Plots overview viewmodel received event: {event}")
        if event == ExperimentalSpectrum.spectrum_analyzed_notification:
            self._extract_exp_x_y_data()
            self._callbacks.get("redraw plot")()
        elif event == State.state_ok_notification:
            self._extract_states()
            self._callbacks.get("redraw plot")()

    def _extract_exp_x_y_data(self):
        xydatas = []
        for exp in ExperimentalSpectrum.spectra_list:
            if exp.is_emission == self.is_emission and exp.ok:
                xydatas.append((exp.get_x_data(), exp.get_y_data()))
        self.xydatas = xydatas

    def _extract_states(self):
        print("Extract states called")
        self.state_plots = {}
        for state in State.state_list:
            if state.ok and (self.is_emission and state.emission_spectrum is not None) or ((not self.is_emission) and state.excitation_spectrum is not None):
                s = StatePlot(state, self.is_emission, yshift=len(list(self.state_plots.keys())) + 1)
                self.state_plots[s.tag] = s

    def on_x_drag(self, value, state_plot):
        self.state_plots[state_plot.tag].set_x_shift(value)
        self._callbacks.get("update plot")(self.state_plots[state_plot.tag])

    def on_y_drag(self, value, state_plot):
        self.state_plots[state_plot.tag].set_y_shift(value)
        self._callbacks.get("update plot")(self.state_plots[state_plot.tag])

    def resize_spectrum(self, spec_tag, direction):
        if spec_tag is not None and spec_tag in self.state_plots.keys():
            spec = self.state_plots[spec_tag]
            spec.resize_y_scale(direction)
            self._callbacks.get("update plot")(spec)

    def on_spectrum_click(self, *args):
        print(args)

    def set_callback(self, key, callback):
        self._callbacks[key] = callback

    def get_zoom_range(self):
        xmin = -1000
        xmax = 3000
        ymin = -0.1
        ymax = 1.1
        if len(self.xydatas):
            exp_x_ranges = [(xy[0][0], xy[0][-1]) for xy in self.xydatas]
            xmin = min([min(xm) for xm in exp_x_ranges])
            xmax = max([max(xm) for xm in exp_x_ranges])
        for p in self.state_plots.values():
            if p.yshift < ymin + 0.1:
                ymin = p.yshift - 0.1
            if p.yshift + 1 > ymax + 0.1:
                ymax = p.yshift + 1.1
        return xmin, xmax, ymin, ymax

