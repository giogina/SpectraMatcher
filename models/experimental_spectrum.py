from models.data_file_manager import File, FileType
from scipy import signal
from utility.spectrum_plots import SpecPlotter


class ExperimentalSpectrum:
    spectra_list = []
    _observers = []
    new_spectrum_notification = "New experimental spectrum"
    spectrum_analyzed_notification = "Experimental spectrum analyzed"

    def __init__(self, file: File, settings=None):
        # settings = {"path": str,
        # "used columns": {"relative wavenumber": int, "absolute wavenumber": int, "intensity": int}}
        # "relative wavenumber column": int,
        # "absolute wavenumber column": int,
        # "intensity column": int,
        # "chosen peaks": [peak indices]
        # "removed peaks": [peak indices]
        # }}
        if settings is None:
            settings = {"path": file.path}
        self.settings = settings  # coupled to project._data
        self.spectra_list.append(self)

        self.is_emission = False
        self.columns = None
        self.name = None

        self.peak_width = None
        self.zero_zero_transition = None
        self.peaks = []
        self.x_min = None
        self.x_max = None

        self.xdata = []
        self.ydata = []
        self.smooth_ydata = []

        self.ok = False
        self.errors = []

        file.experiment = self
        if file.progress == "parsing done":
            self.assimilate_file_data(file)  # if not, the file will call that function upon completion.

    @classmethod
    def add_observer(cls, observer):
        cls._observers.append(observer)

    @classmethod
    def remove_observer(cls, observer):
        cls._observers.remove(observer)

    def _notify_observers(self, message):
        for o in self._observers:
            # print(f"Updating state observers: {message}")
            o.update(message, self)

    def check(self):
        """Confirm integrity of own data"""
        if not self.peaks:
            self.determine_peaks()  # errors detected during peak determination
        return self.ok

    def assimilate_file_data(self, file: File):
        if file.progress != "parsing done":
            print(f"Warning in molecular_data assimilate_file_data: File wasn't done parsing yet: {file.path}")
            return
        if file.type not in (FileType.EXPERIMENT_EXCITATION, FileType.EXPERIMENT_EMISSION):
            print(f"Tried to import non-experiment file {file.path} as experiment. Skipping.")
            return

        self.is_emission = file.type == FileType.EXPERIMENT_EMISSION
        self.columns = file.columns

        # Try to figure out which column is which
        column_keys = list(self.columns)
        available_column_indices = [i for i, _ in enumerate(column_keys)]
        int_found = False
        rel_found = False
        abs_found = False
        if self.settings.get("intensity column") in available_column_indices:           # 1.) Check settings.
            available_column_indices.remove(self.settings.get("intensity column"))
            int_found = True
        if self.settings.get("relative wavenumber column") in available_column_indices:
            available_column_indices.remove(self.settings.get("relative wavenumber column"))
            rel_found = True
        if self.settings.get("absolute wavenumber column") in available_column_indices:
            available_column_indices.remove(self.settings.get("absolute wavenumber column"))
            abs_found = True
        if not int_found:                                                               # 2.) Check heading
            for i in available_column_indices:
                if column_keys[i].find("int") > -1:
                    self.settings["intensity column"] = i
                    int_found = True
                    available_column_indices.remove(i)
                    break
        if not rel_found:
            for i in available_column_indices:
                if column_keys[i].find("rel") > -1:
                    self.settings["relative wavenumber column"] = i
                    rel_found = True
                    available_column_indices.remove(i)
                    break
        if not abs_found:
            for i in available_column_indices:
                if column_keys[i].find("abs") > -1:
                    self.settings["absolute wavenumber column"] = i
                    abs_found = True
                    available_column_indices.remove(i)
                    break
        if not int_found:                                                               # 3.) Check values
            for i in available_column_indices:
                if abs(self.columns[column_keys[i]][0]) <= 1:
                    self.settings["intensity column"] = i
                    int_found = True
                    available_column_indices.remove(i)
                    break
        if (not rel_found) and (not abs_found):
            for i in available_column_indices:
                for j in available_column_indices:  # same step size
                    if (i != j) and \
                            abs(abs(self.columns[column_keys[i]][1] - self.columns[column_keys[i]][0])
                                - abs(self.columns[column_keys[j]][1] - self.columns[column_keys[j]][0])) < 0.01:
                        if abs(self.columns[column_keys[i]][0]) > abs(self.columns[column_keys[j]][0]):
                            self.settings["absolute wavenumber column"] = i
                            self.settings["relative wavenumber column"] = j
                        else:
                            self.settings["relative wavenumber column"] = i
                            self.settings["absolute wavenumber column"] = j
                        rel_found = True
                        abs_found = True
                        available_column_indices.remove(i)
                        available_column_indices.remove(j)
                        break
        if not int_found:                                                               # 4.) Blind guess
            self.settings["intensity column"] = available_column_indices[-1]
        if not rel_found:
            self.settings["relative wavenumber column"] = available_column_indices[0]
        if not abs_found:
            self.settings["absolute wavenumber column"] = available_column_indices[1]

        file.experiment = None
        rel_col = self.columns[column_keys[self.settings['relative wavenumber column']]]
        self.name = ("Emission " if self.is_emission else "Excitation ") + f"{rel_col[0]} .. {rel_col[-1]} cm⁻¹"
        self._notify_observers(self.new_spectrum_notification)
        self.determine_peaks()

    def get_x_data(self):
        column_keys = list(self.columns)
        key = column_keys[self.settings["relative wavenumber column"]]
        return self.columns.get(key)

    def get_y_data(self):
        column_keys = list(self.columns)
        key = column_keys[self.settings["intensity column"]]
        return self.columns.get(key)

    def set_column_usage(self, key, usage):
        column_keys = list(self.columns)
        if key in column_keys:
            index = column_keys.index(key)
            if usage == "abs":
                self.settings["absolute wavenumber column"] = index
            elif usage == "rel":
                self.settings["relative wavenumber column"] = index
            elif usage == "int":
                self.settings["intensity column"] = index
        self._notify_observers(self.new_spectrum_notification)
        self.determine_peaks()

    def determine_peaks(self):
        self.errors = []
        if self.columns is None:
            self.errors.append("No data columns found")
            return
        int_index = self.settings.get("intensity column")
        if int_index not in range(0, len(list(self.columns))):
            self.errors.append(f"Intensity column not known")
            return
        rel_index = self.settings.get("relative wavenumber column")
        if rel_index not in range(0, len(list(self.columns))):
            self.errors.append(f"Relative wavenumber column not known")
            return
        abs_index = self.settings.get("absolute wavenumber column")
        if abs_index not in range(0, len(list(self.columns))):
            self.errors.append(f"Absolute wavenumber column not known")
            return

        xdata = self.columns.get(list(self.columns)[rel_index])
        wndata = self.columns.get(list(self.columns)[abs_index])
        ydata = self.columns.get(list(self.columns)[int_index])

        self.x_min = min(xdata)
        self.x_max = max(xdata)
        self.xdata = xdata
        self.ydata = ydata

        smooth_ydata = []
        for iy, y in enumerate(ydata):  # Take running average to make peak detection easier
            interval = ydata[max(0, iy - 3):min(len(ydata), iy + 4)]
            smooth_ydata.append(sum(interval) / len(interval))

        if int(xdata[0] - wndata[0]) == int(xdata[-1] - wndata[-1]):
            self.zero_zero_transition = int(xdata[0] - wndata[0])
        elif int(xdata[0] + wndata[0]) == int(xdata[-1] + wndata[-1]):
            self.zero_zero_transition = int(xdata[0] + wndata[0])
        else:
            self.errors.append(f"Absolute and relative wavenumber columns don't match")
        self.smooth_ydata = smooth_ydata

        # determine width from high / most prominent peaks
        high_peaks = []
        pr = 1
        while not len(high_peaks):
            high_peaks, _ = signal.find_peaks(smooth_ydata, prominence=pr)
            pr = pr / 2
        pws = signal.peak_widths(smooth_ydata, high_peaks)

        widths = [xdata[round(w[0])] - xdata[round(w[1])] for w in zip(pws[2], pws[3])]
        width = int(abs(sum(widths) / len(widths)) * 5) / 10
        self.peak_width = width / ((max(xdata) - min(xdata)) / len(xdata))

        # TODO: allow for adjustment of prominence / width here? Or allow more / filter later?
        self.detect_peaks(prominence=0.05, width=10 / (abs(xdata[-1] - xdata[0]) / len(xdata)))

        self.ok = len(self.errors) == 0
        self._notify_observers(self.spectrum_analyzed_notification)

        ExperimentalSpectrum.adjust_spec_plotter_range(self.is_emission)
        # for peak in self.peaks:
        #     print(peak.wavenumber, peak.intensity, peak.prominence)
# todo> prominence and width limits are settings; changing them triggers re-evaluation of peaks
    def detect_peaks(self, prominence, width):
        peaks, _ = signal.find_peaks(self.smooth_ydata, prominence=prominence, width=width)
        peaks = list(peaks) + self.settings.get("chosen peaks", [])
        self.peaks = []
        for p in peaks:
            if p not in self.settings.get("removed peaks", []):
                self.peaks.append(ExpPeak(index=p, wavenumber=self.xdata[p], intensity=self.ydata[p]))
        # prominences = signal.peak_prominences(self.smooth_ydata, [p.index for p in self.peaks])
        # widths = signal.peak_widths(self.smooth_ydata, [p.index for p in self.peaks])
        #
        # for p, peak in enumerate(self.peaks):
        #     peak.prominence = prominences[0][p]
        #     peak.width = widths[0][p]

    @classmethod
    def remove(cls, exp):
        if exp in cls.spectra_list:
            cls.spectra_list.remove(exp)
        ExperimentalSpectrum.adjust_spec_plotter_range(exp.is_emission)
        exp._notify_observers(cls.spectrum_analyzed_notification)

    @classmethod
    def adjust_spec_plotter_range(cls, is_emission):
        """Set up SpecPlotter with sufficient range to fit all experimental spectra & matching half-width"""
        exp_list = [exp for exp in cls.spectra_list if exp.is_emission == is_emission]
        if not len(exp_list):
            return None
        x_min = min([exp.x_min for exp in exp_list])
        x_max = max([exp.x_max for exp in exp_list])
        half_width = SpecPlotter.get_half_width(is_emission)  # Prevent overwriting of half-width
        if half_width is None:
            half_width = [exp.peak_width for exp in exp_list if exp.x_min == x_min][0]
        SpecPlotter.set_active_plotter(is_emission, half_width, x_min-1000, 2*x_max+1000)


class ExpPeak:
    def __init__(self, wavenumber, intensity, index, prominence=0):
        self.wavenumber = wavenumber
        self.intensity = intensity
        self.index = index
        self.prominence = prominence


