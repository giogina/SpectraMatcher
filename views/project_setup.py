import dearpygui.dearpygui as dpg
from viewmodels.project_setup_viewmodel import ProjectSetupViewModel
from utility.icons import Icons
from utility.custom_dpg_items import CustomDpgItems


class ProjectSetup:
    def __init__(self, viewmodel: ProjectSetupViewModel):
        self.viewmodel = viewmodel
        self.viewmodel.set_callback("update state data", self.update_state_data)
        self.viewmodel.set_callback("update states data", self.update_states_data)
        self.viewmodel.set_callback("update experimental data", self.update_experimental_data)
        self.icons = Icons()
        self.cdi = CustomDpgItems()

        self.nr_states_displayed = 0

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
            with dpg.tree_node(label="Experimental emission spectra", tag="emission spectra node"):
                with dpg.table(header_row=False):
                    dpg.add_table_column(label="File")
                    dpg.add_table_column(label="wavenumber")
                    dpg.add_table_column(label="intensity")
                    dpg.add_table_column(label="xmin")
                    dpg.add_table_column(label="xmax")
                with dpg.group(horizontal=True, drop_callback=viewmodel.set_experimental_file):  # TODO> Make this the drop target for spectrum files
                    self.icons.insert(dpg.add_button(height=32, width=32), Icons.plus, size=16, tooltip="Add file")
# todo: make this a single list with an up/down button for emission/excitation; sorted by that.
            with dpg.tree_node(label="Experimental excitation spectra", tag="excitation spectra node"):
                with dpg.table(header_row=False):
                    dpg.add_table_column(label="File")
                    dpg.add_table_column(label="wavenumber")
                    dpg.add_table_column(label="intensity")
                    dpg.add_table_column(label="xmin")
                    dpg.add_table_column(label="xmax")
                with dpg.group(horizontal=True):  # TODO> Make this the drop target for spectrum files
                    self.icons.insert(dpg.add_button(height=32, width=32), Icons.plus, size=16, tooltip="Add file")

            # TODO> put large auto-import button on panel that disappears on manual action (or moves up to the action bar)
            #  Here, for every state, make a tree node showing them; with drop receiver fields for the strings.
            #  On top, show main info of this project - just name for now (with edit button?)
            #  Plus button below files to add states
            #  color choice buttons for each state
            #  At the bottom: "Okay" button greyed out until all necessary files are filled in

            # TODO: Allow for excitation/emission only. (Action bar buttons). Grey out unnecessary files, change okay button activity conditions.

            # self.icons.insert(dpg.add_button(height=32, width=100), Icons.angle_double_right, size=16, tooltip="Auto-import all")

        self.configure_theme()

    def add_state_tree_node(self, state):
        with dpg.tree_node(label=state.name, tag=f"state-node-{state.state}", parent="project setup panel"):
            pass  # TODO

    def update_state_data(self, state):
        """Update a single state in-place"""
        print(f"Updating state data: {state}")
        if self.nr_states_displayed < state.state:  # already got this one, proceed
            pass  # TODO> Display this stuff
        elif self.nr_states_displayed == state.state:  # add one
            self.add_state_tree_node(state)

    def update_states_data(self, states):
        """Re-populate all the states from scratch. Except Ground state I guess?"""
        print(f"Updating states data: {states}")  # TODO> Display this stuff
        self.nr_states_displayed = len(states)
        for nr, state in states.items():
            self.add_state_tree_node(state)

    def update_experimental_data(self, experimental_spectra):
        """Display all the experimental data (from scratch, in table)"""
        print(f"Updating exp data: {experimental_spectra}")  # TODO> Display this stuff

    def configure_theme(self):
        with dpg.theme() as file_explorer_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 8, 0)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 0, 12)
                dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 0)
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, [200, 200, 255, 30])
                dpg.add_theme_color(dpg.mvThemeCol_Text, [255, 255, 255, 200])
                dpg.add_theme_color(dpg.mvThemeCol_Header, [50, 50, 120])
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


