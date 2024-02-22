import numpy as np
import logging


class SpecPlotter:
    def __init__(self, half_width, x_min, x_max, x_step=1, type="Lorentzian"):
        self._type = type  # "Lorentzian" or "Gaussian"
        self._half_width = half_width
        self._x_min = int(x_min/x_step)*x_step  # actual min and max x values, rounded to x_step
        self._x_max = int(x_max/x_step)*x_step
        self._x_step = x_step
        self._x_data = np.array([np.arange(start=self._x_min, stop=self._x_max, step=self._x_step)])
        self._base_peak = self._base_lorentzian_array()
        self._base_peak_middle_index = int((self._base_peak.size-1)/2)  # index at which _base_peak peaks
        self.log = False
        if self.log:
            logging.info(f"base peak length: {self._base_peak.size}, middle: {self._base_peak_middle_index}")
            logging.info(f"base peak: {self._base_peak}")

    def _base_lorentzian_array(self):
        """Compute 1D array of lorentzian peak values with top at (0,1) for x_data_length width scaled to 1"""
        a = np.array([1 / (1 + (x*self._x_step / self._half_width) ** 2) for x in np.arange(2*self._x_data.size)])
        return np.concatenate([a[-1::-1], a[1:a.size]])

    def spectrum_array(self, peaks):
        """peaks: array of tuples (position, height)"""
        res = np.zeros(self._x_data.size)
        for peak in peaks:
            position_index = int((peak[0]-self._x_min)/self._x_step)
            res += self._shifted_peak(position_index)*peak[1]
        return res

    def _shifted_peak(self, position_index):  #TODO: Make this work for producing a single-peak array.
        """Shifts and truncates self._base_peak to be correctly positioned in self._x_data."""
        # logging.info(f"position_index: {position_index}")
        start_index = self._base_peak_middle_index - position_index
        stop_index = start_index + self._x_data.size
        if self.log:
            logging.info(f"Start: {start_index}, Stop: {stop_index}, max: {self._base_peak.size}")
        if start_index < 0 or stop_index > self._base_peak.size:
            return np.zeros(self._x_data.size)  # peak too far out of range, return zeroes.
        else:
            return self._base_peak[start_index:stop_index]  # section of base peak vector with peak in correct position

