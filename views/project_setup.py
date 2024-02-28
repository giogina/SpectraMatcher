import dearpygui.dearpygui as dpg

from models.state import State
from utility.font_manager import FontManager
from viewmodels.project_setup_viewmodel import ProjectSetupViewModel
from models.data_file_manager import FileType
from utility.icons import Icons
from utility.custom_dpg_items import CustomDpgItems
from views.file_explorer import FileExplorer
from utility.item_themes import ItemThemes


class ProjectSetup:
    def __init__(self, viewmodel: ProjectSetupViewModel):
        self.viewmodel = viewmodel
        self.icons = Icons()
        self.cdi = CustomDpgItems()
        self.empty_field_theme = None
        self.full_field_theme = None
        self.displayed_state_tags = []

        with dpg.child_window(tag="project setup action bar", width=-1, height=32):
            with dpg.table(header_row=False):
                dpg.add_table_column(width_stretch=True)
                dpg.add_table_column(width_fixed=True, init_width_or_weight=220)
                with dpg.table_row():
                    with dpg.group(horizontal=True):
                        self.icons.insert(dpg_item=dpg.add_button(height=32, width=32), icon=Icons.caret_right, size=16, tooltip="Auto-Import")
                    with dpg.group(horizontal=True):
                        self.icons.insert(dpg_item=dpg.add_button(height=32, width=32),
                                          icon=Icons.diamond, size=16, tooltip="placeholder")
                        self.cdi.insert_separator_button(height=32)

        with dpg.child_window(tag="project setup panel"):
            dpg.add_spacer(height=16)
            with dpg.child_window(tag="project overview", height=140):
                dpg.add_spacer(height=16)
                dpg.add_button(label="Project name", tag="setup panel project name", width=-1)

                with dpg.group(horizontal=True, tag="mlo group"):
                    dpg.add_spacer(width=24)
                    dpg.add_combo(tag="mlo combo", show=False, callback=lambda s, a, u: self.viewmodel.select_ground_state_file(a), width=-48)
                    dpg.add_button(tag="mlo button", label="No ground state frequency calculation found!", width=-48)
            dpg.add_spacer(height=16)
            dpg.bind_item_font("setup panel project name", FontManager.fonts[FontManager.big_font])
# todo: file exlporer: chek if file energy matches ground state selected for project!
#  also, persist selected mlo.
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

        self.viewmodel.set_callback("update project", self.update_project_data)
        self.viewmodel.set_callback("update state data", self.update_state)
        self.viewmodel.set_callback("update states data", self.update_states)
        self.viewmodel.set_callback("update experimental data", self.update_experimental_data)

        self.configure_theme()
        self.update_states()

            # TODO> put large auto-import button on panel that disappears on manual action (or moves up to the action bar)
            #  Plus button below files to add states
            #  color choice buttons for each state
            #  At the bottom: "Okay" button greyed out until all necessary files are filled in

            # TODO: Allow for excitation/emission only. (Action bar buttons). Grey out unnecessary files, change okay button activity conditions.

    def update_project_data(self):  # User can choose name, molecule & ground state energy (which in turn depends on method)
        if self.viewmodel.get_project_name() is not None:
            dpg.set_item_label("setup panel project name", self.viewmodel.get_project_name())
        molecule_and_loth_options = self.viewmodel.get_mlo_list()
        selected_mlo = self.viewmodel.get_selected_mlo_path()
        if molecule_and_loth_options is not None and len(molecule_and_loth_options) > 0:
            if len(molecule_and_loth_options) == 1:
                dpg.set_item_label("mlo button", label=molecule_and_loth_options[0].split('     ---     ')[0])
                dpg.show_item("mlo button")
                dpg.hide_item("mlo combo")
            else:
                dpg.configure_item("mlo combo", items=molecule_and_loth_options)
                if selected_mlo is None:
                    dpg.set_value("mlo combo", "Multiple ground state files found! Select one to enable consistency checks.")
                    dpg.bind_item_theme("mlo combo", self.empty_field_theme)  # todo> selecting a file here == selecting ground state file
                else:    # todo: upon selection, filter files in explorer
                    for i in molecule_and_loth_options:
                        if i.endswith(selected_mlo):
                            dpg.set_value("mlo combo", i)
                            dpg.bind_item_theme("mlo combo", None)
                dpg.show_item("mlo combo")
                dpg.hide_item("mlo button")

    def add_state_tree_node(self, state: State):
        print(f"Tree node for: {state.tag}, {self.displayed_state_tags}")
        self.displayed_state_tags.append(f"state-node-{state.tag}")
        with dpg.collapsing_header(label=state.name, parent="project setup panel", before="state buttons", tag=f"state-node-{state.tag}", default_open=True, drop_callback=lambda s, file: self.viewmodel.import_state_file(file, state), payload_type="Ground file" if state.is_ground else "Excited file"):
            with dpg.table(header_row=False):
                dpg.add_table_column(label="text", width_fixed=True, init_width_or_weight=200)
                dpg.add_table_column(label="file")
                if state.is_ground:
                    with dpg.table_row():
                        with dpg.group(horizontal=True):
                            dpg.add_spacer(width=16)
                            dpg.add_image_button("Frequency ground state-16", width=16)
                            dpg.add_button(label="Frequency file:")
                        dpg.bind_item_theme(dpg.last_item(), FileExplorer.file_type_color_theme.get(FileType.FREQ_GROUND))
                        dpg.add_input_text(tag=f"frequency file for {state.tag}")
                else:
                    with dpg.table_row():
                        with dpg.group(horizontal=True):
                            dpg.add_spacer(width=16)
                            dpg.add_image_button("Frequency excited state-16", width=16)
                            dpg.add_button(label="Frequency file:")
                        dpg.bind_item_theme(dpg.last_item(), FileExplorer.file_type_color_theme.get(FileType.FREQ_EXCITED))
                        dpg.add_input_text(tag=f"frequency file for {state.tag}")  # ,  drop_callback=lambda s, a: dpg.set_value(s, a), payload_type=FileType.FREQ_EXCITED,
                    with dpg.table_row():
                        with dpg.group(horizontal=True):
                            dpg.add_spacer(width=16)
                            dpg.add_image_button("FC excitation-16", width=16)
                            dpg.add_button(label="Excitation FC file:")
                            dpg.bind_item_theme(dpg.last_item(),FileExplorer.file_type_color_theme.get(FileType.FC_EXCITATION))
                        dpg.add_input_text(tag=f"Excitation FC file for state {state.tag}")
                    with dpg.table_row():
                        with dpg.group(horizontal=True):
                            dpg.add_spacer(width=16)
                            dpg.add_image_button("FC emission-16", width=16)
                            dpg.add_button(label="Emission FC file:")
                            dpg.bind_item_theme(dpg.last_item(), FileExplorer.file_type_color_theme.get(FileType.FC_EMISSION))
                        dpg.add_input_text(tag=f"Emission FC file for state {state.tag}")
        dpg.add_spacer(height=24, parent="project setup panel", before="state buttons")
        self.update_state(state)

    def update_state(self, state):
        # print("Project setup update_state: ", state.name, state.freq_file, state.excitation_file, state.emission_file)
        if dpg.does_item_exist(f"frequency file for {state.tag}"):
            if state.freq_file is not None:
                dpg.set_value(f"frequency file for {state.tag}", state.freq_file)
                dpg.bind_item_theme(f"frequency file for {state.tag}", self.full_field_theme)
            else:
                dpg.set_value(f"frequency file for {state.tag}", "")
                dpg.configure_item(f"frequency file for {state.tag}", hint=state.freq_hint)
                dpg.bind_item_theme(f"frequency file for {state.tag}", self.empty_field_theme)
        if dpg.does_item_exist(f"Excitation FC file for state {state.tag}"):
            if state.excitation_file is not None:
                dpg.set_value(f"Excitation FC file for state {state.tag}", state.excitation_file)
                dpg.bind_item_theme(f"Excitation FC file for state {state.tag}", self.full_field_theme)
            else:
                dpg.set_value(f"Excitation FC file for state {state.tag}", "")
                dpg.configure_item(f"Excitation FC file for state {state.tag}", hint=state.excitation_hint)
                dpg.bind_item_theme(f"Excitation FC file for state {state.tag}", self.empty_field_theme)
        if dpg.does_item_exist(f"Emission FC file for state {state.tag}"):
            if state.emission_file is not None:
                dpg.set_value(f"Emission FC file for state {state.tag}", state.emission_file)
                dpg.bind_item_theme(f"Emission FC file for state {state.tag}", self.full_field_theme)
            else:
                dpg.set_value(f"Emission FC file for state {state.tag}", "")
                dpg.configure_item(f"Emission FC file for state {state.tag}", hint=state.emission_hint)
                dpg.bind_item_theme(f"Emission FC file for state {state.tag}", self.empty_field_theme)

    def add_state(self):
        self.viewmodel.add_state()

    def remove_state(self):
        self.viewmodel.delete_state()  # todo - this should all be more flexible, what if the user wants to delete the second state?

    def update_states(self):
        """Re-populate all the states from scratch"""
        for i in self.displayed_state_tags:
            dpg.delete_item(i)
        self.displayed_state_tags = []

        for state in State.state_list:
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
                dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 48, 24)
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
            with dpg.theme_component(dpg.mvAll):
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

        with dpg.theme() as project_overview_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, palette[0]+[160])
                dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 1)
                dpg.add_theme_color(dpg.mvThemeCol_Border, palette[4])
                dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 12, 6)
        dpg.bind_item_theme("project overview", project_overview_theme)

        with dpg.theme() as project_mlo_theme:
            with dpg.theme_component(dpg.mvAll):
                # dpg.add_theme_style(dpg.mvStyleVar_ButtonTextAlign, 0, 0.5)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 24, 6)
                dpg.add_theme_color(dpg.mvThemeCol_Button, palette[3])
        dpg.bind_item_theme("mlo group", project_mlo_theme)






