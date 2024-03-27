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
            first_chars = {str(i): chr(0x20a0+i) for i in range(0, 10)}
            other_chars = {str(i): chr(0x2080+i) for i in range(0, 10)}
        else:
            first_chars = {str(i): chr(0x2090+i) for i in range(0, 10)}
            other_chars = {str(i): chr(0x2070+i) for i in range(0, 10)}

        for peak in peaks:
            if len(peak.transition[0]) == 1:
                label = f"0{first_chars['0']}"
                gaussian_label = f"0{first_chars['0']}"
            else:
                label = ""
                gaussian_label = ""
                last_name = -1
                peak.transition.sort(key=lambda tr: tr[0])
                for t in peak.transition:
                    scr = str(t[1])
                    label_sub_super_scripts = first_chars.get(scr[0]) + ''.join([other_chars.get(c, '') for c in scr[1:]])
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
    def label2html(cls, label):
        html_label = ""
        for char in label:
            if ord(char) in range(0x20a0, 0x20b0):  # emission first char
                html_label += f"<sup>0</sup><sub>{ord(char)-0x20a0}</sub>"
            elif ord(char) in range(0x2080, 0x2090):  # emission other char
                html_label += f"<sub>{ord(char)-0x2080}</sub>"
            elif ord(char) in range(0x2090, 0x20a0):  # excitation first char
                html_label += f"<sub>0</sub><sup>{ord(char)-0x2090}</sup>"
            elif ord(char) in range(0x2070, 0x2080):  # excitation other char
                html_label += f"<sup>{ord(char)-0x2070}</sup>"
            else:
                html_label += char

        html_label = html_label.replace("</sub><sub>", "")
        html_label = html_label.replace("</sup><sup>", "")
        return html_label

    @classmethod
    def label2tex(cls, label):
        tex_label = ""
        for char in label:
            if ord(char) in range(0x20a0, 0x20b0):  # emission first char
                tex_label += "^0_{"+str(ord(char)-0x20a0)+"}"
            elif ord(char) in range(0x2080, 0x2090):  # emission other char
                tex_label += "_{"+str(ord(char)-0x2080)+"}"
            elif ord(char) in range(0x2090, 0x20a0):  # excitation first char
                tex_label += "_0^{"+str(ord(char)-0x2090)+"}"
            elif ord(char) in range(0x2070, 0x2080):  # excitation other char
                tex_label += "^{"+str(ord(char)-0x2070)+"}"
            else:
                tex_label += char

        tex_label = tex_label.replace("}_{", "")
        tex_label = tex_label.replace("}^{", "")
        return '$'+tex_label+'$'

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


