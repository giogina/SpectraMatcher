import dearpygui.dearpygui as dpg
from viewmodels.project_setup_viewmodel import ProjectSetupViewModel
from models.data_file_manager import FileType
from utility.icons import Icons
from utility.custom_dpg_items import CustomDpgItems
from views.file_explorer import _file_icon_colors, FileExplorer
from utility.item_themes import ItemThemes


class ProjectSetup:
    def __init__(self, viewmodel: ProjectSetupViewModel):
        self.viewmodel = viewmodel
        self.viewmodel.set_callback("update state data", self.update_state_data)
        self.viewmodel.set_callback("update states data", self.update_states_data)
        self.viewmodel.set_callback("update experimental data", self.update_experimental_data)
        self.icons = Icons()
        self.cdi = CustomDpgItems()
        self.empty_field_theme = None
        self.full_field_theme = None

        self.nr_states_displayed = 2

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
            dpg.add_text(tag="setup panel project name")
            dpg.add_spacer(height=16)

            with dpg.collapsing_header(label="Experimental emission spectra", tag="emission spectra node"):
                with dpg.table(header_row=False):
                    dpg.add_table_column(label="File")
                    dpg.add_table_column(label="wavenumber")
                    dpg.add_table_column(label="intensity")
                    dpg.add_table_column(label="xmin")
                    dpg.add_table_column(label="xmax")
                with dpg.group(horizontal=True, drop_callback=viewmodel.set_experimental_file):  # TODO> Make this the drop target for spectrum files
                    self.icons.insert(dpg.add_button(height=32, width=32), Icons.plus, size=16, tooltip="Add file")
            dpg.add_spacer(height=24)
# todo: make this a single list with an up/down button for emission/excitation; sorted by that.
            with dpg.collapsing_header(label="Experimental excitation spectra", tag="excitation spectra node"):
                with dpg.table(header_row=False):
                    dpg.add_table_column(label="File")
                    dpg.add_table_column(label="wavenumber")
                    dpg.add_table_column(label="intensity")
                    dpg.add_table_column(label="xmin")
                    dpg.add_table_column(label="xmax")
                with dpg.group(horizontal=True):  # TODO> Make this the drop target for spectrum files
                    self.icons.insert(dpg.add_button(height=32, width=32), Icons.plus, size=16, tooltip="Add file")
            dpg.add_spacer(height=24)

            with dpg.group(horizontal=True, tag="state buttons"):
                dpg.add_spacer(width=-42)
                self.icons.insert(dpg.add_button(height=42, width=42, tag="add state button", callback=self.add_state), Icons.plus, size=16)
                self.icons.insert(dpg.add_button(height=42, width=42, tag="remove state button", callback=self.remove_state), Icons.minus, size=16)


            # TODO> put large auto-import button on panel that disappears on manual action (or moves up to the action bar)
            #  Here, for every state, make a tree node showing them; with drop receiver fields for the strings.
            #  On top, show main info of this project - just name for now (with edit button?)
            #  Plus button below files to add states
            #  color choice buttons for each state
            #  At the bottom: "Okay" button greyed out until all necessary files are filled in

            # TODO: Allow for excitation/emission only. (Action bar buttons). Grey out unnecessary files, change okay button activity conditions.

        self.configure_theme()

    def add_state_tree_node(self, state):
        with dpg.collapsing_header(label=state.name, parent="project setup panel", before="state buttons", tag=f"state-node-{state.state}", default_open=True, drop_callback=lambda s, file: self.set_file(state.state, file), payload_type="Ground file" if state.state == 0 else "Excited file"):
            with dpg.table(header_row=False):
                dpg.add_table_column(label="text", width_fixed=True, init_width_or_weight=200)
                dpg.add_table_column(label="file")
                if state.state == 0:
                    with dpg.table_row():
                        with dpg.group(horizontal=True):
                            dpg.add_spacer(width=16)
                            dpg.add_image_button("Frequency ground state-16", width=16)
                            dpg.add_button(label="Frequency file:")
                        dpg.bind_item_theme(dpg.last_item(), FileExplorer.file_type_color_theme.get(FileType.FREQ_GROUND))
                        dpg.add_input_text(tag=f"frequency file for state {state.state}", hint="Drag & drop file here, or click 'auto import'")
                        dpg.bind_item_theme(dpg.last_item(), self.empty_field_theme)
                if state.state > 0:
                    with dpg.table_row():
                        with dpg.group(horizontal=True):
                            dpg.add_spacer(width=16)
                            dpg.add_image_button("Frequency excited state-16", width=16)
                            dpg.add_button(label="Frequency file:")
                        dpg.bind_item_theme(dpg.last_item(), FileExplorer.file_type_color_theme.get(FileType.FREQ_EXCITED))
                        dpg.add_input_text(tag=f"frequency file for state {state.state}", hint="Drag & drop file here, or click 'auto import'")  # ,  drop_callback=lambda s, a: dpg.set_value(s, a), payload_type=FileType.FREQ_EXCITED,
                        dpg.bind_item_theme(dpg.last_item(), self.empty_field_theme)
                    with dpg.table_row():
                        with dpg.group(horizontal=True):
                            dpg.add_spacer(width=16)
                            dpg.add_image_button("FC excitation-16", width=16)
                            dpg.add_button(label="Excitation FC file:")
                            dpg.bind_item_theme(dpg.last_item(),FileExplorer.file_type_color_theme.get(FileType.FC_EXCITATION))
                        dpg.add_input_text(tag=f"Excitation FC file for state {state.state}", hint="Drag & drop file here, or click 'auto import'")
                        dpg.bind_item_theme(dpg.last_item(), self.empty_field_theme)  # TODO> Allow drag&drop for folders to fill in all three
                    with dpg.table_row():
                        with dpg.group(horizontal=True):
                            dpg.add_spacer(width=16)
                            dpg.add_image_button("FC emission-16", width=16)
                            dpg.add_button(label="Emission FC file:")
                            dpg.bind_item_theme(dpg.last_item(), FileExplorer.file_type_color_theme.get(FileType.FC_EMISSION))
                        dpg.add_input_text(tag=f"Emission FC file for state {state.state}",  hint="Drag & drop file here, or click 'auto import'")
                        dpg.bind_item_theme(dpg.last_item(), self.empty_field_theme)
        dpg.add_spacer(height=24, parent="project setup panel", before="state buttons")

    def set_file(self, state, file):
        path = file.path
        print(f"{state}, type: {file.type} at path {path}")
        if file.type == FileType.FREQ_GROUND and state == 0:
            dpg.set_value(f"frequency file for state {state}", path)
            dpg.bind_item_theme(f"frequency file for state {state}", self.full_field_theme)
            self.viewmodel.set
        elif file.type == FileType.FREQ_EXCITED and state > 0:
            dpg.set_value(f"frequency file for state {state}", path)
            dpg.bind_item_theme(f"frequency file for state {state}", self.full_field_theme)
        elif file.type == FileType.FC_EMISSION and state > 0:
            dpg.set_value(f"Emission FC file for state {state}", path)
            dpg.bind_item_theme(f"Emission FC file for state {state}", self.full_field_theme)
        elif file.type == FileType.FC_EXCITATION and state > 0:
            dpg.set_value(f"Excitation FC file for state {state}", path)
            dpg.bind_item_theme(f"Excitation FC file for state {state}", self.full_field_theme)

    def add_state(self):
        self.viewmodel.add_state()

    def remove_state(self):
        self.viewmodel.delete_state()  # todo - this should all be more flexible, what if the user wants to delete the second state?

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
        palette = [[11, 11, 36],  # 0
                   [22, 22, 72],  # 1
                   [50, 50, 120],  # 2
                   [60, 60, 154],  # 3
                   [70, 70, 255],  # 4
                   [100, 100, 255],  # 5
                   [131, 131, 255],  # 6
                   [180, 180, 255],  # 7
                   ]

        with dpg.theme() as project_setup_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 6, 4)
                dpg.add_theme_style(dpg.mvStyleVar_CellPadding, 8, 4)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 12, 12)
                dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 1)
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, [200, 200, 255, 30])
                dpg.add_theme_color(dpg.mvThemeCol_Text, [255, 255, 255, 200])
                dpg.add_theme_color(dpg.mvThemeCol_Header, [50, 50, 120])
            with dpg.theme_component(dpg.mvChildWindow):
                dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 62, 42)
            with dpg.theme_component(dpg.mvCollapsingHeader):
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 10, 10)
            with dpg.theme_component(dpg.mvInputText):
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 10, 6)
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, 6)
                dpg.add_theme_color(dpg.mvThemeCol_Button, [11, 11, 36, 0])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [11, 11, 36, 0])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [11, 11, 36, 0])
            with dpg.theme_component(dpg.mvImageButton):
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 10, 7)
                dpg.add_theme_color(dpg.mvThemeCol_Button, [11, 11, 36, 0])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [11, 11, 36, 0])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [11, 11, 36, 0])

        dpg.bind_item_theme("project setup panel", project_setup_theme)

        with dpg.theme() as action_bar_theme:  # TODO> Set up some kind of centralized theme supply? All action bars should probably look the same...
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Button, [0, 0, 0, 0])
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 0, 0)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, 0)
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, [200, 200, 255, 80])
                dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, [200, 200, 255, 50])

        dpg.bind_item_theme("project setup action bar", action_bar_theme)

        with dpg.theme() as self.empty_field_theme:
            with dpg.theme_component(dpg.mvInputText):
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, [160, 0, 0, 30])
                dpg.add_theme_color(dpg.mvThemeCol_Border, [120, 0, 0, 255])
                dpg.add_theme_color(dpg.mvThemeCol_BorderShadow, [160, 0, 0, 0])
                dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)

        with dpg.theme() as self.full_field_theme:
            with dpg.theme_component(dpg.mvInputText):
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, [0, 40, 0, 100])
                dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0)

        with dpg.theme() as actual_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, palette[3])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, palette[6])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, palette[4])

        dpg.bind_item_theme("add state button", actual_button_theme)
        dpg.bind_item_theme("remove state button", actual_button_theme)




