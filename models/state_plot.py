from utility.labels import Labels
from utility.noop import noop
from models.molecular_data import FCSpectrum
import numpy as np

from utility.spectrum_plots import SpecPlotter


class StatePlot:
    def __init__(self, state, is_emission: bool, state_index=0):
        print(f"Making StatePlot for {state.name}")
        self.tag = StatePlot.construct_tag(state, is_emission)
        self.state = state
        self.spectrum = state.get_spectrum(is_emission)
        self.spectrum.add_observer(self)
        self.name = state.name
        self.index = state_index
        self.e_key = 'emission' if is_emission else 'excitation'
        self.xshift = self.state.settings.get(f"x shift {self.e_key}", 0)
        self.yshift = self.state.settings.get(f"y shift {self.e_key}", state_index*Labels.settings[is_emission].get('global y shifts', 1.25))
        self.yscale = self.state.settings.get(f"y scale {self.e_key}", 1)
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

    def _compute_x_data(self):
        return self._base_xdata + self.xshift

    def _compute_y_data(self):
        return (self._base_ydata * self.yscale) + self.yshift

    def set_x_shift(self, xshift):
        self.xshift = xshift - self.handle_x
        self.state.settings[f"x shift {self.e_key}"] = self.xshift
        self.xdata = self._compute_x_data()

    def set_y_shift(self, yshift):
        self.yshift = yshift
        self.state.settings[f"y shift {self.e_key}"] = yshift
        self.ydata = self._compute_y_data()

    def resize_y_scale(self, direction):
        self.yscale += direction * 0.1
        self.yscale = max(0, self.yscale)
        self.state.settings[f"y scale {self.e_key}"] = self.yscale
        self.ydata = self._compute_y_data()

    def set_y_scale(self, value):
        self.yscale = value
        self.state.settings[f"y scale {self.e_key}"] = value
        self.ydata = self._compute_y_data()

    def set_color(self, color, selection_type="manual"):
        self.state.settings["color"] = color
        self.state.settings["color selection type"] = selection_type

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

    def is_hidden(self):
        return self.state.settings.get(f"hidden {self.e_key}", False)

    def hide(self, hide=True):
        self.state.settings[f"hidden {self.e_key}"] = hide


class MatchPlot:
    def __init__(self, is_emission: bool):
        self.contributing_state_plots = []  # StatePlot instances
        self.xdata = []
        self.ydata = []
        self.is_emission = is_emission
        self.hidden = True

    def add_state_plot(self, spec: StatePlot):
        if spec not in self.contributing_state_plots:
            self.contributing_state_plots.append(spec)
        self.compute_composite_xy_data()

    def remove_state_plot(self, spec: StatePlot):
        if spec in self.contributing_state_plots:
            self.contributing_state_plots.remove(spec)
        self.compute_composite_xy_data()

    def compute_composite_xy_data(self):
        _, _, _, x_step = SpecPlotter.get_plotter_key(self.is_emission)  # step size used in all xdata arrays
        x_min = min([s.xdata[0] for s in self.contributing_state_plots])
        x_max = min([s.xdata[-1] for s in self.contributing_state_plots])
        self.xdata = np.array(np.arange(start=x_min, stop=x_max, step=x_step))  # mirrors SpecPlotter x_data construction
        self.ydata = np.zeros(self.xdata)
        for s in self.contributing_state_plots:
            start_index = min(max(0, int((s.xdata[0] - x_min)/x_step)), len(self.xdata)-1)
            stop_index = min(start_index + len(s.ydata), len(self.ydata))
            self.ydata[start_index:stop_index] += s.ydata[0:stop_index-start_index]

