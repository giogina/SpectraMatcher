from models.data_file_manager import File, FileType
from utility import signal as signal
import numpy as np
from utility.spectrum_plots import SpecPlotter
from utility.noop import noop


class ExpPeak:
    def __init__(self, wavenumber, intensity, index):
        self.wavenumber = wavenumber
        self.intensity = intensity
        self.match = None  # used in MatchPlot.assign_peaks; key of MatchPlot.super_clusters


class ExperimentalSpectrum:
    spectra_list = []
    _settings = {True: {}, False: {}}
    _observers = []
    new_spectrum_notification = "New experimental spectrum"
    spectrum_analyzed_notification = "Experimental spectrum analyzed"
    peaks_changed_notification = "Experimental spectrum peaks changed"
    notify_changed_callback = noop  # to inform project

    @classmethod
    def defaults(cls):
        return {'peak prominence threshold': 0.05,
                'peak width threshold': 10,
                }

    def __init__(self, file: File, settings=None):
        # settings = {"path": str,
        # "used columns": {"relative wavenumber": int, "absolute wavenumber": int, "intensity": int}}
        # "relative wavenumber column": int,
        # "absolute wavenumber column": int,
        # "intensity column": int,
        # "chosen peaks": [int(peak wavenumber)s]
        # "removed peaks": [int(peak wavenumber)s]
        # }}

        if settings is None:
            settings = {"path": file.path,
                        "chosen peaks": [],
                        "removed peaks": [],
                        }
        self.settings = settings  # coupled to project._data
        print("self.settings = ", self.settings)
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

        self.hidden = False

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

    @classmethod
    def set(cls, is_emission, keyword, value):
        cls._settings[is_emission][keyword] = value
        cls.notify_changed_callback()
        for spec in cls.spectra_list:
            if spec.is_emission == is_emission:
                spec.detect_peaks()

    @classmethod
    def get(cls, is_emission, keyword, default=None):
        return cls._settings[is_emission].get(keyword, default)

    @classmethod
    def reset_defaults(cls, is_emission):
        for key, value in ExperimentalSpectrum.defaults().items():
            cls._settings[is_emission][key] = value
        cls.notify_changed_callback()
        for spec in cls.spectra_list:
            if spec.is_emission == is_emission:
                spec.detect_peaks()

    @classmethod
    def reset_manual_peaks(cls, is_emission):
        for spec in cls.spectra_list:
            if spec.is_emission == is_emission:
                spec.settings["chosen peaks"] = []
                spec.settings["removed peaks"] = []
                spec.detect_peaks()
        ExperimentalSpectrum.notify_changed_callback()

    def add_peak(self, x):
        print("Add peak called")
        index = self.get_x_index(x)
        new_peak = ExpPeak(wavenumber=self.xdata[index], intensity=self.ydata[index], index=index)
        self.peaks.append(new_peak)
        if self.settings.get("chosen peaks") is None:
            self.settings["chosen peaks"] = [int(new_peak.wavenumber)]
            print("New chosen peaks list", self.settings)
        else:
            if int(new_peak.wavenumber) not in self.settings["chosen peaks"]:
                self.settings["chosen peaks"].append(int(new_peak.wavenumber))
            if int(new_peak.wavenumber) in self.settings.get("removed peaks", []):
                self.settings["removed peaks"].remove(int(new_peak.wavenumber))
            print("Appended new peak", x, self.settings)
        ExperimentalSpectrum.notify_changed_callback()
        return new_peak

    def get_x_index(self, x):
        if self.xdata is None:
            return -1
        if self.xdata[0] < self.xdata[1]:  # ascending
            index = np.searchsorted(self.xdata, x)
        else:
            index = np.searchsorted(-self.xdata, -x)

        index = int(index)
        if index == 0:
            closest_index = 0
        elif index == len(self.xdata):
            closest_index = index - 1
        else:
            if abs(x - self.xdata[index - 1]) <= abs(x - self.xdata[index]):
                closest_index = index - 1
            else:
                closest_index = index
        return closest_index

    def delete_peak(self, peak: ExpPeak):
        if peak in self.peaks:
            print("delete peak: ", peak)
            self.peaks.remove(peak)
            if self.settings.get("removed peaks") is None:
                self.settings["removed peaks"] = [int(peak.wavenumber)]
            else:
                if int(peak.wavenumber) not in self.settings["removed peaks"]:
                    self.settings["removed peaks"].append(int(peak.wavenumber))
                if int(peak.wavenumber) in self.settings.get("chosen peaks", []):
                    self.settings["chosen peaks"].remove(int(peak.wavenumber))
        ExperimentalSpectrum.notify_changed_callback()

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

        self.detect_peaks()  #prominence=0.05, width=10 / (abs(xdata[-1] - xdata[0]) / len(xdata))

        self.ok = len(self.errors) == 0
        self._notify_observers(self.spectrum_analyzed_notification)

        ExperimentalSpectrum.adjust_spec_plotter_range(self.is_emission)

    def detect_peaks(self):
        if self.x_min is None or self.x_max is None or len(self.xdata) < 2:
            return
        xstep = (self.x_max - self.x_min)/(len(self.xdata) - 1)
        if xstep is None:
            return
        peaks, pm = signal.find_peaks(self.smooth_ydata, prominence=ExperimentalSpectrum.get(self.is_emission, 'peak prominence threshold'), width=ExperimentalSpectrum.get(self.is_emission, 'peak width threshold', 10)/xstep)

        peaks = list(peaks)
        for chosen_peak in self.settings.get("chosen peaks", []):
            if self.x_min <= chosen_peak <= self.x_max:
                index = self.get_x_index(chosen_peak)
                if index not in peaks:
                    peaks.append(index)
        self.peaks = []
        for p in peaks:
            if int(self.xdata[p]) not in self.settings.get("removed peaks", []):
                self.peaks.append(ExpPeak(index=p, wavenumber=self.xdata[p], intensity=self.ydata[p]))

        self._notify_observers(self.peaks_changed_notification)

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
        min_list = [exp.x_min for exp in exp_list if exp.x_min is not None]
        max_list = [exp.x_max for exp in exp_list if exp.x_max is not None]
        if not len(min_list) or not len(max_list):
            return None
        x_min = min(min_list)
        x_max = max(max_list)
        half_width = SpecPlotter.get_half_width(is_emission)  # Prevent overwriting of set half-width
        # if half_width == 10 or half_width is None:
        #     half_width = [exp.peak_width for exp in exp_list if exp.x_min == x_min][0]
        SpecPlotter.set_active_plotter(is_emission, half_width, x_min-1000, 2*x_max+1000)



