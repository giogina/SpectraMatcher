from models.experimental_spectrum import ExperimentalSpectrum


def noop(*args, **kwargs):
    pass


class PlotsOverviewViewmodel:
    def __init__(self, project, is_emission: bool):
        self._project = project
        self.is_emission = is_emission
        print("Plots overview viewmodel created: ", is_emission)
        # self._project.add_observer(self, "state data changed")
        ExperimentalSpectrum.add_observer(self)
        self._callbacks = {
            "update plot": noop
        }

        self.xdata = []  # TODO: determine "global" x data first...
        self.ydatas = [[]]  # TODO: spec ydata to ydata fitting global xdata...

    def update(self, event, *args):
        print(f"Plots overview viewmodel received event: {event}")
        if event == ExperimentalSpectrum.spectrum_analyzed_notification:
            self._extract_exp_x_y_data()
            self._callbacks.get("update plot")()

    def _extract_exp_x_y_data(self):
        print("in get x y data: ", ExperimentalSpectrum.spectra_list)
        for exp in ExperimentalSpectrum.spectra_list:
            print(exp.name, exp.is_emission, exp.ok, exp.columns)
            if exp.is_emission == self.is_emission and exp.ok:
                self.xdata = exp.get_x_data()
                self.ydatas = [exp.get_y_data()]  # todo> temp

    def set_callback(self, key, callback):
        self._callbacks[key] = callback


