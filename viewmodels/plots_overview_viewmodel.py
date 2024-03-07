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

        self.xydatas = []

    def update(self, event, *args):
        print(f"Plots overview viewmodel received event: {event}")
        if event == ExperimentalSpectrum.spectrum_analyzed_notification:
            self._extract_exp_x_y_data()
            self._callbacks.get("update plot")()

    def _extract_exp_x_y_data(self):
        self.xydatas = []
        for exp in ExperimentalSpectrum.spectra_list:
            if exp.is_emission == self.is_emission and exp.ok:
                self.xydatas.append((exp.get_x_data(), exp.get_y_data()))

    def set_callback(self, key, callback):
        self._callbacks[key] = callback

