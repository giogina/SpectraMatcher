import dearpygui.dearpygui as dpg


class CustomDpgItems:
    _instance = None
    _is_initialized = False

    def __new__(cls):  # Make SettingsManager a Singleton.
        if cls._instance is None:
            cls._instance = super(CustomDpgItems, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._is_initialized:
            with dpg.theme() as self.invisible_button_theme:
                with dpg.theme_component(dpg.mvImageButton):
                    dpg.add_theme_color(dpg.mvThemeCol_Button, [11, 11, 36, 0])
                    dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [11, 11, 36, 0])
                    dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [11, 11, 36, 0])
                with dpg.theme_component(dpg.mvButton):
                    dpg.add_theme_color(dpg.mvThemeCol_Button, [11, 11, 36, 0])
                    dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [11, 11, 36, 0])
                    dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [11, 11, 36, 0])

                sep = []
                for i in range(24):
                    sep.extend([0.8, 0.8, 1, 0.4])

                with dpg.texture_registry(show=False):
                    dpg.add_static_texture(width=1, height=24, default_value=sep, tag="pixel")
            self._is_initialized = True

    def insert_separator_button(self, height=32):
        dpg.add_spacer(width=3)
        dpg.bind_item_theme(dpg.add_image_button("pixel", width=1, height=height), self.invisible_button_theme)
        dpg.add_spacer(width=3)


