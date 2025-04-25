from utility import noop


class Matcher:
    _DEFAULTS = {'peak intensity match threshold': 0.03,
                 'distance match threshold': 30,
                 'match active': False,
                 'combo spectrum y shift': 1.25,
                 'show composite spectrum': True,
                 'show component spectra': True,
                 'show shade spectra': False,
                 'show stick spectra': False,
                 "list only labeled transitions": False
                 }
    settings = {True: {}, False: {}}
    notify_changed_callback = noop
    _observers = []
    match_settings_updated_notification = "Matcher settings updated"
    match_display_settings_updated_notification = "Matcher display settings updated"

    @classmethod
    def add_observer(cls, observer):
        cls._observers.append(observer)

    @classmethod
    def remove_observer(cls, observer):
        cls._observers.remove(observer)

    @classmethod
    def _notify_observers(cls, message, is_emission):
        for o in cls._observers:
            o.update(message, is_emission)

    @classmethod
    def set(cls, is_emission, key, value):
        if key in cls.settings[is_emission].keys():
            cls.settings[is_emission][key] = value
        cls.notify_changed_callback()  # notify project
        if key in ('show composite spectrum', 'show component spectra', 'show shade spectra', 'show stick spectra'):
            cls._notify_observers(cls.match_display_settings_updated_notification, is_emission)
        else:
            cls._notify_observers(cls.match_settings_updated_notification, is_emission)

    @classmethod
    def get(cls, is_emission, key, default=None):
        return cls.settings[is_emission].get(key, default)

    @classmethod
    def restore_defaults(cls, is_emission):
        defaults = cls.defaults()
        for key, value in defaults.items():
            cls.settings[is_emission][key] = value
        cls.notify_changed_callback()  # notify project

    @classmethod
    def defaults(cls):
        return cls._DEFAULTS.copy()