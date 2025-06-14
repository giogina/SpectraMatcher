import numpy as np
import colorsys


def hsv_to_rgb(h, s, v):
    if s == 0.0: return (v, v, v)
    i = int(h*6.) # XXX assume int() truncates!
    f = (h*6.)-i; p,q,t = v*(1.-s), v*(1.-s*f), v*(1.-s*(1.-f)); i%=6
    if i == 0: return (255*v, 255*t, 255*p)
    if i == 1: return (255*q, 255*v, 255*p)
    if i == 2: return (255*p, 255*v, 255*t)
    if i == 3: return (255*p, 255*q, 255*v)
    if i == 4: return (255*t, 255*p, 255*v)
    if i == 5: return (255*v, 255*p, 255*q)


def adjust_color_for_dark_theme(color):
    r, g, b = color[0], color[1], color[2]
    # Convert RGB to HSV; RGB values are expected to be in [0, 255] range
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)

    # Define a threshold to determine if the color is "dark"
    threshold = 0.5

    # If the value is below the threshold, increase it to brighten the color
    if v < threshold:
        v = 1.0  # Set to maximum brightness

    # Convert HSV back to RGB
    r_adj, g_adj, b_adj = colorsys.hsv_to_rgb(h, s, v)

    # Return the adjusted RGB values, scaled back to [0, 255] range
    return [int(r_adj * 255), int(g_adj * 255), int(b_adj * 255)]


class SpecPlotter:
    _active_emission_plotter = None  # Key of SpecPlotter instance to be used currently
    _active_excitation_plotter = None  # Key of SpecPlotter instance to be used currently
    _plotters = {}  # coupled to project._data # dict of SpecPlotter instances (with different parameters in keys)
    _observers = []
    active_plotter_changed_notification = "Active plotter changed"

    def __new__(cls, half_width, x_min, x_max, x_step=1):  # Keep only one instance for every set of parameters
        if (half_width, x_min, x_max, x_step) not in cls._plotters:
            cls._plotters[(half_width, x_min, x_max, x_step)] = super(SpecPlotter, cls).__new__(cls)
        return cls._plotters[(half_width, x_min, x_max, x_step)]

    def __init__(self, half_width, x_min, x_max, x_step=1):
        self._half_width = half_width
        self._x_min = int(x_min/x_step)*x_step  # actual min and max x values, rounded to x_step
        self._x_max = int(x_max/x_step)*x_step
        self._x_step = x_step
        self.x_data = np.array(np.arange(start=self._x_min, stop=self._x_max, step=self._x_step))
        self._base_peak = self._base_lorentzian_array()
        self._base_peak_middle_index = int((self._base_peak.size-1)/2)  # index at which _base_peak peaks
        self.log = False
        if self.log:
            print(f"base peak length: {self._base_peak.size}, middle: {self._base_peak_middle_index}")
            print(f"base peak: {self._base_peak}")

    @classmethod
    def add_observer(cls, observer):
        cls._observers.append(observer)

    @classmethod
    def remove_observer(cls, observer):
        cls._observers.remove(observer)

    def _notify_observers(self, message):
        for o in self._observers:
            o.update(message, self)

    @classmethod
    def set_active_plotter(cls, is_emission, half_width, x_min, x_max, x_step=1):
        plotter_key = (round(half_width*10)/10, int(min(x_min, x_max)), int(max(x_min, x_max)), max(1, int(x_step)))
        if is_emission:
            cls._active_emission_plotter = plotter_key
        else:
            cls._active_excitation_plotter = plotter_key
        if plotter_key not in cls._plotters:
            SpecPlotter(*plotter_key)
        for o in cls._observers:
            o.update(cls.active_plotter_changed_notification, plotter_key, is_emission)

    @classmethod
    def change_half_width(cls, is_emission, amount, relative=True):
        plotter_key = cls.get_plotter_key(is_emission)
        if relative:
            half_width = plotter_key[0] + amount
        else:
            half_width = amount
        half_width = max(half_width, 0.1)
        cls.set_active_plotter(is_emission, half_width, plotter_key[1], plotter_key[2], plotter_key[3])
        return half_width

    @classmethod
    def get_plotter_key(cls, is_emission):
        if is_emission:
            return cls._active_emission_plotter
        else:
            return cls._active_excitation_plotter

    @classmethod
    def get_half_width(cls, is_emission):
        if is_emission:
            if cls._active_emission_plotter is None:
                return 10
            return cls._active_emission_plotter[0]
        else:
            if cls._active_excitation_plotter is None:
                return 10
            return cls._active_excitation_plotter[0]

    @classmethod
    def get_spectrum_array(cls, peaks, is_emission):
        """Get array using currently active plotter"""
        plotter_key = cls.get_plotter_key(is_emission)
        if plotter_key is not None:
            ydata = cls._plotters[plotter_key].spectrum_array(peaks)
            top = max(0.01, max(ydata))
            return plotter_key, cls._plotters[plotter_key].x_data, ydata / top, top
        else:
            return None, [], [], 1

    def _base_lorentzian_array(self):
        """Compute 1D array of lorentzian peak values with top at (0,1) for x_data_length width scaled to 1"""
        a = np.array([1 / (1 + (x*self._x_step / self._half_width) ** 2) for x in np.arange(2 * self.x_data.size)])
        return np.concatenate([a[-1::-1], a[1:a.size]])

    def spectrum_array(self, peaks):
        """peaks: array of FCPeak instances"""
        res = np.zeros(self.x_data.size)
        for peak in peaks:
            position_index = (peak.corrected_wavenumber-self._x_min)/self._x_step
            shift = position_index - int(position_index)
            a0 = self._shifted_peak(int(position_index))
            a1 = self._shifted_peak(int(position_index)+1)
            res += (a0*(1-shift) + a1*shift) * peak.intensity
        return res

    def _shifted_peak(self, position_index):
        """Shifts and truncates self._base_peak to be correctly positioned in self._x_data."""
        try:
            base_peak = self._base_peak
            middle_index = self._base_peak_middle_index

            start_index = middle_index - position_index
            start_index = int(start_index)
            stop_index = start_index + self.x_data.size
            if start_index < 0 or stop_index > base_peak.size:
                return np.zeros(self.x_data.size)  # peak too far out of range, return zeroes.
            else:
                return base_peak[start_index:stop_index]  # section of base peak vector with peak in correct position
        except Exception:
            return np.zeros(self.x_data.size)
