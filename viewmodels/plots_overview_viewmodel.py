import time
from models.experimental_spectrum import ExperimentalSpectrum
from models.state import State
from models.state_plot import StatePlot
from utility.async_manager import AsyncManager
from utility.spectrum_plots import SpecPlotter
from utility.wavenumber_corrector import WavenumberCorrector
from utility.noop import noop


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


