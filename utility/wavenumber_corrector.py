

class WavenumberCorrector:
    correction_factors = {True: {}, False: {}}  # coupled to project._data["wavenumber correction factors"]
    _observers = []
    correction_factors_changed_notification = "Correction factors changed"

    @classmethod
    def add_observer(cls, observer):
        cls._observers.append(observer)

    @classmethod
    def remove_observer(cls, observer):
        cls._observers.remove(observer)

    @classmethod
    def _notify_observers(cls, message):
        for o in cls._observers:
            o.update(message)

    @classmethod
    def set_correction_factor(cls, is_emission, vibration_type, value):
        if vibration_type in cls.correction_factors[is_emission].keys():
            cls.correction_factors[is_emission][vibration_type] = value
        cls._notify_observers(cls.correction_factors_changed_notification)

    @classmethod
    def compute_corrected_wavenumbers(cls, is_emission, peaks, modes):
        # Weighted sum of wavenumbers * correction_factor(vibration type) for each mode in transition.
        for peak in peaks:
            if not (peak.transition == [[0]] or peak.transition == [[0, 0]]):
                peak.corrected_wavenumber = 0
                for t in peak.transition:
                    multiplicity = t[1]
                    mode = modes.get_mode(t[0])
                    correction_factor = cls.correction_factors[is_emission].get(mode.vibration_type)
                    peak.corrected_wavenumber += mode.wavenumber*correction_factor*multiplicity
        return peaks
