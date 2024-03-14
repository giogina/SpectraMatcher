import dearpygui.dearpygui as dpg


class ItemThemes:

    @staticmethod
    def invisible_button_theme():
        with dpg.theme() as invisible_button_theme:
            with dpg.theme_component(dpg.mvImageButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, [11, 11, 36, 0])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [11, 11, 36, 0])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [11, 11, 36, 0])
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, [11, 11, 36, 0])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [11, 11, 36, 0])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [11, 11, 36, 0])
        return invisible_button_theme

    @staticmethod
    def action_bar_theme():
        with dpg.theme() as action_bar_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Button, [0, 0, 0, 0])
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 0, 0)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, 0)
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, [200, 200, 255, 80])
                dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, [200, 200, 255, 50])
        return action_bar_theme