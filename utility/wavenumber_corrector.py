

class WavenumberCorrector:
    correction_factors = {'bends': 0.986, 'H stretches': 0.975, 'others': 0.996}  # coupled to project._data["wavenumber correction factors"]
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
    def compute_corrected_wavenumbers(cls, peaks):
        print(peaks)
        cls._notify_observers(cls.correction_factors_changed_notification)