from models.experimental_spectrum import ExperimentalSpectrum
from models.molecular_data import FCSpectrum
from models.state import State
import numpy as np
import time

from utility.async_manager import AsyncManager
from utility.spectrum_plots import SpecPlotter
from utility.wavenumber_corrector import WavenumberCorrector


def noop(*args, **kwargs):
    pass


class StatePlot:
    def __init__(self, state: State, is_emission: bool, xshift=0, yshift=1):
        print(f"Making StatePlot for {state.name}")
        self.tag = StatePlot.construct_tag(state, is_emission)
        self.state = state
        self.spectrum = state.get_spectrum(is_emission)
        self.spectrum.add_observer(self)
        self.name = state.name
        self.xshift = xshift
        self.yshift = yshift
        self.yscale = 1
        self.color = state.color
        self._base_xdata = self.spectrum.x_data
        self._base_ydata = self.spectrum.y_data
        self.xdata = self._compute_x_data()
        self.ydata = self._compute_y_data()
        self.handle_x = self._base_xdata[np.where(self._base_ydata == max(self._base_ydata))[0][0]]
        self.sticks = []  # stick: position, [[height, color]]
        for peak in self.spectrum.peaks:
            if peak.transition[0] != [0]:
                sub_stick_scale = peak.intensity/sum([t[1] for t in peak.transition])
                self.sticks.append([peak.corrected_wavenumber, [[vib[1]*sub_stick_scale, [c*255 for c in vib[0].vibration_properties]] for vib in [(self.spectrum.vibrational_modes.get_mode(t[0]), t[1]) for t in peak.transition if len(t) == 2] if vib is not None]])
        self.spectrum_update_callback = noop
        self.sticks_update_callback = noop

    @staticmethod
    def construct_tag(state, is_emission):
        return f"{state.name} - {is_emission} plot"

    def update(self, event, *args):
        if event == FCSpectrum.xy_data_changed_notification:
            self._base_xdata = self.spectrum.x_data
            self._base_ydata = self.spectrum.y_data
            self.xdata = self._compute_x_data()
            self.ydata = self._compute_y_data()
            self.handle_x = self._base_xdata[np.where(self._base_ydata == max(self._base_ydata))[0][0]]
            self.spectrum_update_callback(self)
        if event == FCSpectrum.peaks_changed_notification:
            self.sticks = []  # stick: position, [[height, color]]
            for peak in self.spectrum.peaks:
                if peak.transition[0] != [0]:
                    sub_stick_scale = peak.intensity / sum([t[1] for t in peak.transition])
                    self.sticks.append([peak.corrected_wavenumber,
                                        [[vib[1] * sub_stick_scale, [c * 255 for c in vib[0].vibration_properties]] for
                                         vib in [(self.spectrum.vibrational_modes.get_mode(t[0]), t[1]) for t in
                                                 peak.transition if len(t) == 2] if vib is not None]])
            self.sticks_update_callback(self)

    def set_spectrum_update_callback(self, callback):
        self.spectrum_update_callback = callback

    def set_sticks_update_callback(self, callback):
        self.sticks_update_callback = callback

    def get_clusters(self):
        return self.spectrum.get_clusters()

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

        return self.xdata[start:stop], self.ydata[start:stop]


class PlotsOverviewViewmodel:
    def __init__(self, project, is_emission: bool):
        self._project = project
        self.is_emission = is_emission
        self._project.add_observer(self, "project loaded")
        ExperimentalSpectrum.add_observer(self)
        State.add_observer(self)
        self._callbacks = {
            "update plot": noop,
            "add spectrum": noop,
            "redraw plot": noop,
            "delete sticks": noop,
            "redraw sticks": noop,
            "set correction factor values": noop,
        }

        self.xydatas = []  # experimental x, y
        self.state_plots = {}  # whole State instances, for x, y, color, etc.
        self._auto_zoom = True
        self.last_correction_factor_change_time = 0

    def update(self, event, *args):
        print(f"Plots overview viewmodel received event: {event}")
        if event == "project loaded":
            self._callbacks.get("set correction factor values")(WavenumberCorrector.correction_factors)
        elif event == ExperimentalSpectrum.spectrum_analyzed_notification:
            self._extract_exp_x_y_data()
            self._callbacks.get("redraw plot")()
        elif event == State.state_ok_notification:
            state = args[0]
            new_spec_tag = self._extract_state(state)
            if new_spec_tag is not None:
                self._callbacks.get("add spectrum")(new_spec_tag)
            # self._callbacks.get("redraw plot")()  # todo> react to already-plotted state deletion (see if it's still in State.state_list?)

    def _extract_exp_x_y_data(self):
        xydatas = []
        for exp in ExperimentalSpectrum.spectra_list:
            if exp.is_emission == self.is_emission and exp.ok:
                xydatas.append((exp.get_x_data(), exp.get_y_data()))
        self.xydatas = xydatas

    def _extract_state(self, state):
        if state in State.state_list and state.ok and (self.is_emission and state.emission_spectrum is not None) or ((not self.is_emission) and state.excitation_spectrum is not None):
            tag = StatePlot.construct_tag(state, self.is_emission)
            if tag not in self.state_plots.keys() or self.state_plots[tag].state != state:
                state_index = State.state_list.index(state)
                self.state_plots[tag] = StatePlot(state, self.is_emission, yshift=state_index)
                self.state_plots[tag].set_spectrum_update_callback(self.update_plot)
                self.state_plots[tag].set_sticks_update_callback(self.update_sticks)
                return tag
        return None

    def update_plot(self, state_plot):
        self._callbacks.get("update plot")(state_plot)

    def update_sticks(self, state_plot):
        AsyncManager.submit_task(f"schedule stick redraw for {state_plot.tag}", self.schedule_stick_spectrum_redraw, state_plot)

    def schedule_stick_spectrum_redraw(self, state_plot):
        debounce_period = 0.2
        while True:
            time_since_last_update = time.time() - self.last_correction_factor_change_time
            if time_since_last_update >= debounce_period:
                self._callbacks.get("redraw sticks")(state_plot)
                break
            time.sleep(debounce_period)

    def on_x_drag(self, value, state_plot):
        self.state_plots[state_plot.tag].set_x_shift(value)
        self._callbacks.get("delete sticks")(state_plot.tag)
        self._callbacks.get("update plot")(self.state_plots[state_plot.tag], mark_dragged_plot=state_plot.tag)

    def on_y_drag(self, value, state_plot):
        self.state_plots[state_plot.tag].set_y_shift(value)
        self._callbacks.get("delete sticks")(state_plot.tag)
        self._callbacks.get("update plot")(self.state_plots[state_plot.tag], mark_dragged_plot=state_plot.tag)

    def resize_spectrum(self, spec_tag, direction):
        if spec_tag is not None and spec_tag in self.state_plots.keys():
            spec = self.state_plots[spec_tag]
            spec.resize_y_scale(direction)
            self._callbacks.get("update plot")(spec, redraw_sticks=True)

    def resize_half_width(self, direction):
        SpecPlotter.change_half_width(self.is_emission, direction)

    def change_correction_factor(self, key, value):
        self.last_correction_factor_change_time = time.time()
        self._callbacks.get("delete sticks")()
        WavenumberCorrector.set_correction_factor(key, value)

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

