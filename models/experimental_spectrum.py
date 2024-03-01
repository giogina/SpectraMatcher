from models.data_file_manager import File, FileType
import os


class ExperimentalSpectrum:
    spectra_list = []
    _observers = []
    new_spectrum_notification = "New experimental spectrum"

    def __init__(self, file: File, settings=None):
        # settings = {"path": str,
        # "used columns": {"relative wavenumber": int, "absolute wavenumber": int, "intensity": int}}
        # "relative wavenumber column": int,
        # "absolute wavenumber column": int,
        # "intensity column": int}}
        if settings is None:
            settings = {"path": file.path}
        self.settings = settings  # coupled to project._data
        self.spectra_list.append(self)

        self.is_emission = False
        self.columns = None

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
            print(f"Updating state observers: {message}")
            o.update(message, self)

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
        self._notify_observers(self.new_spectrum_notification)

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

