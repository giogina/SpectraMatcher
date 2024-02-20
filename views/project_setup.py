import dearpygui.dearpygui as dpg
from viewmodels.project_setup_viewmodel import ProjectSetupViewModel
from utility.icons import Icons
from utility.custom_dpg_items import CustomDpgItems


class ProjectSetup:
    def __init__(self, viewmodel: ProjectSetupViewModel):
        self.viewmodel = viewmodel
        self.viewmodel.set_callback("update project data", self.update_project_data)
        self.icons = Icons()
        self.cdi = CustomDpgItems()

        with dpg.child_window(tag="project setup action bar", width=-1, height=32):
            with dpg.table(header_row=False):
                dpg.add_table_column(width_stretch=True)
                dpg.add_table_column(width_fixed=True, init_width_or_weight=220)
                with dpg.table_row():
                    dpg.add_spacer()
                    with dpg.group(horizontal=True):
                        self.icons.insert(dpg_item=dpg.add_button(height=32, width=32),
                                          icon=Icons.diamond, size=16, tooltip="placeholder")
                        self.cdi.insert_separator_button(height=32)

        with dpg.child_window(tag="project setup panel"):
            dpg.add_spacer(height=16)
            # TODO> put large auto-import button on panel that disappears on manual action (or moves up to the action bar)
            #  Implement in project: (maybe through extra classes) ground & excited states & experiment, with corresponding files for Freq, FC
            #  Here, for every state, make a tree node showing them; with drop receiver fields for the strings.
            #  On top, show main info of this project - just name for now (with edit button?)
            #  Plus button below files to add states
            self.icons.insert(dpg.add_button(height=32, width=100), Icons.angle_double_right, size=16, tooltip="Auto-import all")

        self.configure_theme()

    def update_project_data(self, *args):
        print(f"Updating project data: {self.viewmodel._project.get('name')}")

    def configure_theme(self):
        with dpg.theme() as file_explorer_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 8, 0)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 0, 0)
                dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 0)
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, [200, 200, 255, 30])
                dpg.add_theme_color(dpg.mvThemeCol_Text, [255, 255, 255, 200])
            # with dpg.theme_component(dpg.mvButton):
            #     dpg.add_theme_color(dpg.mvThemeCol_Button, [0, 0, 0, 0])
            #     dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [0, 0, 0, 0])
            #     dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [0, 0, 0, 0])
            #     dpg.add_theme_style(dpg.mvStyleVar_ButtonTextAlign, 0.5, 0.5)
            #     dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, 0)
            # with dpg.theme_component(dpg.mvImageButton):
            #     dpg.add_theme_color(dpg.mvThemeCol_Button, [0, 0, 0, 0])
            #     dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [0, 0, 0, 0])
            #     dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [0, 0, 0, 0])
            #     dpg.add_theme_style(dpg.mvStyleVar_ButtonTextAlign, 0.5, 0.5)
            #     dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, 0)

        dpg.bind_item_theme("project setup panel", file_explorer_theme)

        with dpg.theme() as action_bar_theme:  # TODO> Set up some kind of centralized theme supply? All action bars should probably look the same...
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Button, [0, 0, 0, 0])
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 0, 0)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, 0)
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, [200, 200, 255, 80])
                dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, [200, 200, 255, 50])

        dpg.bind_item_theme("project setup action bar", action_bar_theme)


