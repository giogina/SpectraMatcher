from utility.noop import noop
from models.molecular_data import FCSpectrum
import numpy as np


class StatePlot:
    def __init__(self, state, is_emission: bool, xshift=0, yshift=1):
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

    def set_y_scale(self, value):
        self.yscale = value
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
