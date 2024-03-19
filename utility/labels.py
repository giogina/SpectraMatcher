from utility.noop import noop


class Labels:
    _DEFAULTS = {'show labels': False,
                 'show gaussian labels': False,
                 'peak intensity label threshold': 0.1,
                 'stick label relative threshold': 0.1,
                 'stick label absolute threshold': 0.1,
                 'peak separation threshold': 0.8,
                 'label font size': 18,
                 'axis font size': 18,
                 'peak intensity match threshold': 0.03,
                 'distance match threshold': 30,
                 'global y shifts': 1.25
                 }
    settings = {True: {}, False: {}}  # Coupled to project._data
    notify_changed_callback = noop
    _observers = []
    label_settings_updated_notification = "Label settings updated"

    @classmethod
    def construct_labels(cls, peaks, modes, is_emission):
        if is_emission:
            from_index = '⁰'
            to_indices = {'0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄', '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉'}
        else:
            from_index = '₀'
            to_indices = {'0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹'}
        for peak in peaks:

            if len(peak.transition[0]) == 1:
                label = "0₀⁰"  # todo: extra character for 0-0 above each other? Or use negative space?
                gaussian_label = "0₀⁰"
            else:
                label = ""
                gaussian_label = ""
                last_name = -1
                peak.transition.sort(key=lambda tr: tr[0])
                for t in peak.transition:
                    label_sub_super_scripts = from_index + ''.join([to_indices.get(c, '') for c in str(t[1])])
                    gaussian_label += " " + str(modes.get_mode(t[0]).gaussian_name) + label_sub_super_scripts
                    current_name = int(modes.get_mode(t[0]).name)
                    new_label = str(current_name).strip() + label_sub_super_scripts
                    if current_name > last_name:
                        label += " " + new_label
                    else:
                        label = new_label + " " + label
                    last_name = current_name
            peak.label = label.strip().replace("  ", " ")
            peak.gaussian_label = gaussian_label.strip().replace("  ", " ")
        return peaks

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
            cls._notify_observers(cls.label_settings_updated_notification, is_emission)

    @classmethod
    def restore_defaults(cls, is_emission):
        defaults = cls.defaults()
        for key, value in defaults.items():
            if key not in ('show labels', 'show gaussian labels'):
                cls.settings[is_emission][key] = value
        cls.notify_changed_callback()  # notify project
        cls._notify_observers(cls.label_settings_updated_notification, is_emission)

    @classmethod
    def defaults(cls):
        return cls._DEFAULTS.copy()


