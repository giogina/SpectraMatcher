import time
import threading
from models.experimental_spectrum import ExperimentalSpectrum
from models.state import State
from models.state_plot import StatePlot
from utility.labels import Labels
from utility.matcher import Matcher
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
        Labels.add_observer(self)
        Matcher.add_observer(self)
        self._callbacks = {
            "post load update": noop,
            "update plot": noop,
            "add spectrum": noop,
            "redraw plot": noop,
            "delete sticks": noop,
            "redraw sticks": noop,
            "update labels": noop,
            "redraw peaks": noop,
            "add list spectrum": noop,
            "update list spec": noop,
            "update spectrum color": noop,
            "hide spectrum": noop,
        }

        self.xydatas = []  # experimental x, y
        self.state_plots = {}  # whole State instances, for x, y, color, etc.
        self._auto_zoom = True
        self.last_correction_factor_change_time = 0
        self.last_action_x = noop
        self.last_action_y = noop

    def update(self, event, *args):
        # print(f"Plots overview viewmodel received event: {event}")
        if event == "project loaded":
            self._callbacks.get("post load update")()
        elif event == ExperimentalSpectrum.spectrum_analyzed_notification:
            self._extract_exp_x_y_data()
            self._callbacks.get("redraw plot")()
        elif event == State.state_ok_notification:
            state = args[0]
            new_spec_tag = self._extract_state(state)
            if new_spec_tag is not None:
                self._callbacks.get("add spectrum")(new_spec_tag)
                self._callbacks.get("add list spectrum")(self.state_plots[new_spec_tag])
                for tag, s in self.state_plots.items():
                    self._callbacks.get("update labels")(tag)
            # todo> react to already-plotted state deletion (see if it's still in State.state_list?)
        elif event == Labels.label_settings_updated_notification:
            for tag, s in self.state_plots.items():
                self._callbacks.get("update labels")(tag)
        elif event == ExperimentalSpectrum.peaks_changed_notification:
            self._callbacks.get("redraw peaks")()

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
                self.state_plots[tag] = StatePlot(state, self.is_emission, state_index=state_index)
                self.state_plots[tag].index = state_index
                self.state_plots[tag].set_spectrum_update_callback(self.update_plot_and_drag_lines)
                self.state_plots[tag].set_sticks_update_callback(self.update_sticks)
                return tag
        return None

    def update_plot_and_drag_lines(self, state_plot):
        if state_plot != self.state_plots[state_plot.tag]:
            print(f"Different plot instance detected! {state_plot.tag}")
        self._callbacks.get("update plot")(state_plot, update_drag_lines=True)

    def update_sticks(self, state_plot):
        thread = threading.Thread(target=self.schedule_stick_spectrum_redraw, args=(state_plot,))
        thread.start()

    def schedule_stick_spectrum_redraw(self, state_plot):
        debounce_period = 0.2
        while True:
            time_since_last_update = time.time() - self.last_correction_factor_change_time
            if time_since_last_update >= debounce_period:
                self._callbacks.get("redraw sticks")(state_plot)
                break
            time.sleep(debounce_period)

    def on_x_drag(self, value, state_plot, slider=False):
        if slider:
            value = value + self.state_plots[state_plot.tag].handle_x
        self.state_plots[state_plot.tag].set_x_shift(value)
        self._callbacks.get("delete sticks")(state_plot.tag)
        if slider:
            self._callbacks.get("update plot")(self.state_plots[state_plot.tag], update_drag_lines=True)
        else:
            self._callbacks.get("update plot")(self.state_plots[state_plot.tag], mark_dragged_plot=state_plot.tag)
        self._callbacks.get("update list spec")(self.state_plots[state_plot.tag])
        self.last_action_x = lambda direction: self.on_x_drag(self.state_plots[state_plot.tag].xshift + 10*direction, state_plot, slider=True)

    def on_y_drag(self, value, state_plot):
        self.state_plots[state_plot.tag].set_y_shift(value)
        self._callbacks.get("delete sticks")(state_plot.tag)
        self._callbacks.get("update plot")(self.state_plots[state_plot.tag], mark_dragged_plot=state_plot.tag)
        self._callbacks.get("update list spec")(state_plot)
        self.last_action_y = lambda direction: self.on_y_drag(value+0.01*direction, state_plot)

        # for s in self.state_plots.values():
        #     if abs(value - s.yshift) < 0.01:

    def resize_spectrum(self, spec_tag, direction):
        if spec_tag is not None and spec_tag in self.state_plots.keys():
            spec = self.state_plots[spec_tag]
            spec.resize_y_scale(direction)
            self._callbacks.get("update plot")(spec, redraw_sticks=True)
            self._callbacks.get("update list spec")(spec)
            self.last_action_y = lambda d: self.resize_spectrum(spec_tag, d)

    def set_y_scale(self, value, state_plot):
        state_plot.set_y_scale(value)
        self._callbacks.get("update plot")(state_plot, redraw_sticks=True)
        self._callbacks.get("update list spec")(state_plot)
        self.last_action_y = lambda d: self.resize_spectrum(state_plot.tag, d)

    def set_y_shifts(self, value):
        Labels.set(self.is_emission, 'global y shifts', value)
        for tag, state_plot in self.state_plots.items():
            state_plot.set_y_shift(state_plot.index*value)
            self._callbacks.get("delete sticks")(state_plot.tag)
            self._callbacks.get("update plot")(state_plot, fit_y_axis=True)
            self._callbacks.get("update list spec")(state_plot)
        self.last_action_y = lambda d: self.set_y_shifts(value+0.1*d)

    def resize_half_width(self, direction, relative=True):
        print("Resize: ", direction)
        self._callbacks.get("post load update")(half_width=True)
        self.last_action_x = self.resize_half_width
        return SpecPlotter.change_half_width(self.is_emission, direction, relative)

    def change_correction_factor(self, key, value):
        self.last_correction_factor_change_time = time.time()
        self._callbacks.get("delete sticks")()
        WavenumberCorrector.set_correction_factor(self.is_emission, key, value)
        self.last_action_x = lambda d: self.change_correction_factor(key, value+0.01*d)
        self._callbacks.get("post load update")(x_scale=True)

    def set_color(self, color, state_plot):
        state_plot.set_color(color)
        self._callbacks.get("update spectrum color")(state_plot)

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

    def hide_spectrum(self, tag, hide=True):
        self.state_plots[tag].hide(hide)
        shown_specs_counter = 0
        global_y_shift = Labels.settings[self.is_emission].get('global y shifts', 1.25)
        for spec in self.state_plots.values():
            if not spec.is_hidden():
                shown_specs_counter += 1
                spec.set_y_shift(shown_specs_counter * global_y_shift)
            self._callbacks.get("update plot")(spec, redraw_sticks=True, update_drag_lines=True)
            self._callbacks.get("update list spec")(spec)
        self._callbacks.get("hide spectrum")(tag, hide)

    def match_peaks(self, match_on):
        pass # todo



