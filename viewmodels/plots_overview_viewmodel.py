from models.experimental_spectrum import ExperimentalSpectrum
from models.state import State


def noop(*args, **kwargs):
    pass


class StatePlot:
    def __init__(self, state: State, is_emission: bool, xshift=0, yshift=1):
        print(f"Making StatePlot for {state.name}")
        self.tag = f"{state.name} - {is_emission} plot"
        self._base_xdata = state.x_data(is_emission)
        self._base_ydata = state.y_data(is_emission)
        self.xshift = xshift
        self.yshift = yshift
        self.yscale = 1
        self.color = state.color
        self.xdata = self._compute_x_data()
        self.ydata = self._compute_y_data()

    def _compute_x_data(self):
        return self._base_xdata + self.xshift

    def _compute_y_data(self):
        return (self._base_ydata * self.yscale) + self.yshift

    def set_y_shift(self, yshift):
        self.yshift = yshift
        print("new yshift: ", yshift)
        self.ydata = self._compute_y_data()


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
        self.state_plots = []  # whole State instances, for x, y, color, etc.
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
        self.state_plots = []
        for state in State.state_list:
            if state.ok and (self.is_emission and state.emission_spectrum is not None) or ((not self.is_emission) and state.excitation_spectrum is not None):
                self.state_plots.append(StatePlot(state, self.is_emission, yshift=len(self.state_plots)+1))

    def on_y_drag(self, value, state_plot):
        print(value, state_plot.tag)
        state_plot.set_y_shift(value)
        self._callbacks.get("update plot")(state_plot)

    def set_callback(self, key, callback):
        self._callbacks[key] = callback

    def on_toggle_autozoom(self, auto_zoom):
        self._auto_zoom = auto_zoom
        self.adjust_zoom()

    def adjust_zoom(self):
        xmin = -1000
        xmax = 3000
        ymin = -0.1  # todo: probably enough to trigger an auto-zoom of the plot itself...
        ymax = 1.1  # todo: adjust according to states and their distances
        if len(self.xydatas):
            exp_x_ranges = [(xy[0][0], xy[0][-1]) for xy in self.xydatas]
            xmin = min([min(xm) for xm in exp_x_ranges])
            xmax = max([max(xm) for xm in exp_x_ranges])

