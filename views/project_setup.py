import dearpygui.dearpygui as dpg

from models.state import State
from models.experimental_spectrum import ExperimentalSpectrum
from utility.font_manager import FontManager
from viewmodels.project_setup_viewmodel import ProjectSetupViewModel
from models.data_file_manager import FileType, File
from utility.icons import Icons
from utility.custom_dpg_items import CustomDpgItems
from views.file_explorer import FileExplorer


class ProjectSetup:
    def __init__(self, viewmodel: ProjectSetupViewModel):
        self.viewmodel = viewmodel
        self.icons = Icons()
        self.cdi = CustomDpgItems()
        self.empty_field_theme = None
        self.full_field_theme = None
        self.big_button_theme = None
        self.actual_button_theme = None
        self.icons = Icons()
        self.nr_state_nodes = 0
        self.nr_experiment_rows = 0

        with dpg.child_window(tag="project setup panel"):
            dpg.add_spacer(height=16)
            with dpg.child_window(tag="project overview", height=140):
                dpg.add_spacer(height=16)
                dpg.add_button(label="Project name", tag="setup panel project name", width=-1)
                dpg.bind_item_font("setup panel project name", FontManager.fonts[FontManager.big_font])

                with dpg.group(horizontal=True, tag="mlo group"):
                    dpg.add_spacer(width=16)
                    dpg.add_combo(tag="mlo combo", show=False, callback=lambda s, a, u: self.viewmodel.select_mlo(a), width=-48)
                    dpg.add_button(tag="mlo button", label="", width=-48)
                # dpg.add_checkbox(label="Sanity checks", default_value=True)

            dpg.add_spacer(height=6)
            with dpg.table(header_row=False):
                dpg.add_table_column()
                dpg.add_table_column()
                with dpg.table_row():
                    dpg.add_button(label="Auto Import", tag="auto import", width=-1)
                    dpg.add_button(label="Done", tag="import done", width=-1)
            dpg.add_spacer(height=16)

            with dpg.collapsing_header(label="Experimental spectra", tag="experimental spectra node", leaf=True):
                with dpg.group(width=-1, horizontal=True, drop_callback=lambda s, file: self.viewmodel.import_experimental_file(file), payload_type="Experiment file"):
                    with dpg.table(header_row=True, tag="experimental files table", resizable=True):
                        dpg.add_table_column(label="", init_width_or_weight=4)
                        dpg.add_table_column(label="abs. wavenumbers", width_fixed=True, init_width_or_weight=140)
                        dpg.add_table_column(label="rel. wavenumbers", width_fixed=True, init_width_or_weight=140)
                        dpg.add_table_column(label="max intensity", width_fixed=True, init_width_or_weight=100)
                        dpg.add_table_column(label="", width_fixed=True, init_width_or_weight=30)
                        with dpg.table_row(tag="temp table hint"):
                            dpg.add_input_text(tag=f"temp table hint input", width=-1, hint="Drag & drop files here, or click 'auto import'")
                    dpg.add_spacer(height=4)
                dpg.add_spacer(height=24)
#
            with dpg.group(horizontal=True, tag="state buttons"):
                self.icons.insert(dpg.add_button(height=42, width=42, tag="add state button", callback=self.add_state), Icons.plus, size=16)

        self.viewmodel.set_callback("update project", self.update_project_data)
        self.viewmodel.set_callback("update state data", self.update_state)
        self.viewmodel.set_callback("update states data", self.update_states)
        self.viewmodel.set_callback("update experimental data", self.update_experimental_data)

        self.configure_theme()
        self.update_states()
        self.update_experimental_data()

    # User can choose name, molecule & ground state energy (which in turn depends on method)
    def update_project_data(self):
        if self.viewmodel.get_project_name() is not None:
            dpg.set_item_label("setup panel project name", self.viewmodel.get_project_name())
        molecule_and_loth_options, chosen_item = self.viewmodel.get_mlo_list()
        if len(molecule_and_loth_options) > 0:
            if len(molecule_and_loth_options) == 1:
                dpg.set_item_label("mlo button", label=molecule_and_loth_options[0])
                dpg.show_item("mlo button")
                dpg.hide_item("mlo combo")
            else:
                dpg.configure_item("mlo combo", items=molecule_and_loth_options)
                dpg.set_value("mlo combo", chosen_item)
                dpg.show_item("mlo combo")
                dpg.hide_item("mlo button")
        if File.nr_unparsed_files == 0 and len(File.molecule_energy_votes.keys()) > 0:
            dpg.bind_item_theme("auto import", self.big_button_theme)
            dpg.configure_item("auto import", callback=self.viewmodel.auto_import)

    def add_state_tree_node(self):
        state_index = self.nr_state_nodes
        with dpg.collapsing_header(leaf=True, label=State.state_list[state_index].name, parent="project setup panel", before="state buttons", tag=f"state-node-{state_index}", default_open=True):
            self.nr_state_nodes += 1
            with dpg.group(width=-1, horizontal=True, drop_callback=lambda s, file: self.viewmodel.import_state_file(file, state_index), payload_type="Ground file" if state_index == 0 else "Excited file"):
                with dpg.table(header_row=False):
                    dpg.add_table_column()
                    dpg.add_table_column(width_fixed=True, init_width_or_weight=200)
                    dpg.add_table_column(width_fixed=True, init_width_or_weight=60)
                    with dpg.table_row():
                        with dpg.table(header_row=False):
                            dpg.add_table_column(label="text", width_fixed=True, init_width_or_weight=200)
                            dpg.add_table_column(label="file")
                            if state_index == 0:
                                with dpg.table_row():
                                    with dpg.group(horizontal=True):
                                        dpg.add_spacer(width=16)
                                        dpg.add_image_button("Frequency ground state-16", width=16)
                                        dpg.add_button(label="Frequency file:")
                                    dpg.bind_item_theme(dpg.last_item(), FileExplorer.file_type_color_theme.get(FileType.FREQ_GROUND))
                                    dpg.add_input_text(tag=f"frequency file for {state_index}", width=-42)
                            else:
                                with dpg.table_row():
                                    with dpg.group(horizontal=True):
                                        dpg.add_spacer(width=16)
                                        dpg.add_image_button("Frequency excited state-16", width=16)
                                        dpg.add_button(label="Frequency file:")
                                    dpg.bind_item_theme(dpg.last_item(), FileExplorer.file_type_color_theme.get(FileType.FREQ_EXCITED))
                                    dpg.add_input_text(tag=f"frequency file for {state_index}", width=-42)  # ,  drop_callback=lambda s, a: dpg.set_value(s, a), payload_type=FileType.FREQ_EXCITED,
                                with dpg.table_row():
                                    with dpg.group(horizontal=True):
                                        dpg.add_spacer(width=16)
                                        dpg.add_image_button("FC excitation-16", width=16)
                                        dpg.add_button(label="Excitation FC file:")
                                        dpg.bind_item_theme(dpg.last_item(), FileExplorer.file_type_color_theme.get(FileType.FC_EXCITATION))
                                    dpg.add_input_text(tag=f"Excitation FC file for state {state_index}", width=-42)
                                with dpg.table_row():
                                    with dpg.group(horizontal=True):
                                        dpg.add_spacer(width=16)
                                        dpg.add_image_button("FC emission-16", width=16)
                                        dpg.add_button(label="Emission FC file:")
                                        dpg.bind_item_theme(dpg.last_item(), FileExplorer.file_type_color_theme.get(FileType.FC_EMISSION))
                                    dpg.add_input_text(tag=f"Emission FC file for state {state_index}", width=-42)

                        with dpg.group(horizontal=True):
                            dpg.add_button(tag=f"delta E {state_index}", height=32)
                        with dpg.group():
                            if not state_index == 0:  # todo: Enable the hide/show buttons to do the same as the ones in the spectrum view (probably state -> state_plots -> .hide(hide))
                                self.icons.insert(dpg_item=dpg.add_button(width=32, height=32, user_data=state_index, tag=f"hide {state_index}", callback=lambda s, a, u: self.viewmodel.hide_state(u, False), show=False), icon=Icons.eye_slash, size=16)
                                self.icons.insert(dpg_item=dpg.add_button(width=32, height=32, user_data=state_index, tag=f"show {state_index}", callback=lambda s, a, u: self.viewmodel.hide_state(u, True), show=False), icon=Icons.eye, size=16)
                                self.icons.insert(dpg_item=dpg.add_button(width=32, height=32, user_data=state_index, tag=f"trash {state_index}", callback=lambda s, a, u: self.viewmodel.delete_state(u)), icon=Icons.trash, size=16, tooltip="Delete this state")

            dpg.add_spacer(height=24)
        self.update_state(State.state_list[state_index])

    def update_state(self, state: State):
        state_index = State.state_list.index(state)
        fc_file_encountered = False
        # print("Project setup update_state: ", state.name, state.freq_file, state.excitation_file, state.emission_file)
        if dpg.does_item_exist(f"frequency file for {state_index}"):
            if state.settings.get("freq file") is not None:
                dpg.set_value(f"frequency file for {state_index}", state.settings.get("freq file"))
                dpg.bind_item_theme(f"frequency file for {state_index}", self.full_field_theme)
            else:
                dpg.set_value(f"frequency file for {state_index}", "")
                dpg.configure_item(f"frequency file for {state_index}", hint=state.freq_hint)
                dpg.bind_item_theme(f"frequency file for {state_index}", self.empty_field_theme)
        if dpg.does_item_exist(f"Excitation FC file for state {state_index}"):
            if state.settings.get("excitation file") is not None:
                dpg.set_value(f"Excitation FC file for state {state_index}", state.settings.get("excitation file"))
                dpg.bind_item_theme(f"Excitation FC file for state {state_index}", self.full_field_theme)
                fc_file_encountered = True
            else:
                dpg.set_value(f"Excitation FC file for state {state_index}", "")
                dpg.configure_item(f"Excitation FC file for state {state_index}", hint=state.excitation_hint)
                dpg.bind_item_theme(f"Excitation FC file for state {state_index}", self.empty_field_theme)
        if dpg.does_item_exist(f"Emission FC file for state {state_index}"):
            if state.settings.get("emission file") is not None:
                dpg.set_value(f"Emission FC file for state {state_index}", state.settings.get("emission file"))
                dpg.bind_item_theme(f"Emission FC file for state {state_index}", self.full_field_theme)
                fc_file_encountered = True
            else:
                dpg.set_value(f"Emission FC file for state {state_index}", "")
                dpg.configure_item(f"Emission FC file for state {state_index}", hint=state.emission_hint)
                dpg.bind_item_theme(f"Emission FC file for state {state_index}", self.empty_field_theme)
        # if dpg.does_item_exist(f"hide {state_index}"):
        #     if state.settings.get("hidden", False):
        #         dpg.show_item(f"hide {state_index}")
        #         dpg.hide_item(f"show {state_index}")
        #     else:
        #         dpg.show_item(f"show {state_index}")
        #         dpg.hide_item(f"hide {state_index}")
        #     dpg.bind_item_theme(f"show {state_index}", self.actual_button_theme)
        #     dpg.bind_item_theme(f"hide {state_index}", self.actual_button_theme)
        if dpg.does_item_exist(f"trash {state_index}"):
            dpg.bind_item_theme(f"trash {state_index}", self.actual_button_theme)
            if state.delta_E is not None:
                dpg.set_item_label(f"delta E {state_index}", f"ΔE = {int(state.delta_E*100)/100.} cm⁻¹")

        if fc_file_encountered:
            dpg.bind_item_theme("import done", self.big_button_theme)
            dpg.configure_item("import done", callback=self.viewmodel.import_done)

    def add_state(self, *args):
        self.viewmodel.add_state()

    def update_states(self, *args):
        """Re-populate all the states"""
        nr_displayed_states = self.nr_state_nodes
        for i in range(0, min(nr_displayed_states, len(State.state_list))):
            self.update_state(State.state_list[i])
        if len(State.state_list) < nr_displayed_states:
            for i in range(len(State.state_list), nr_displayed_states):
                if dpg.does_item_exist(f"state-node-{i}"):
                    dpg.delete_item(f"state-node-{i}")
                    self.nr_state_nodes -= 1
        else:
            for i in range(nr_displayed_states, len(State.state_list)):
                self.add_state_tree_node()

    def add_experiment_row(self, *args):
        exp_index = self.nr_experiment_rows
        if dpg.does_item_exist(f"temp table hint input"):
            dpg.delete_item(f"temp table hint input")
        with dpg.table_row(tag=f"experiment row {exp_index}", parent="experimental files table"):
            self.nr_experiment_rows += 1

            with dpg.group(horizontal=True, tag=f"exp file path and icon {exp_index}"):
                dpg.add_spacer(width=16)
                dpg.add_image_button("experiment emission-16", width=16, tag=f"experiment icon {exp_index}")
                dpg.add_button(tag=f"Exp file path {exp_index}")

            dpg.add_button(label="", tag=f"Exp file abs range {exp_index}", width=-1)
            dpg.add_button(label="", tag=f"Exp file rel range {exp_index}", width=-1)
            dpg.add_button(label="", tag=f"Exp file int {exp_index}", width=-1)
            self.icons.insert(dpg.add_button(tag=f"delete exp file {exp_index}"), icon=Icons.trash, size=16)

        self.update_experiment(exp_index)

    def update_experiment(self, index):
        if index in range(0, len(ExperimentalSpectrum.spectra_list)):
            exp = ExperimentalSpectrum.spectra_list[index]
        else:
            return
        if dpg.does_item_exist(f"experiment row {index}"):
            file_type = FileType.EXPERIMENT_EMISSION if exp.is_emission else FileType.EXPERIMENT_EXCITATION
            dpg.configure_item(f"experiment icon {index}", texture_tag=f"{file_type}-{16}")
            dpg.bind_item_theme(f"exp file path and icon {index}", FileExplorer.file_type_color_theme.get(file_type))
            dpg.set_item_label(f"Exp file path {index}", exp.settings.get("path"))
            if exp.columns is not None:
                keys = list(exp.columns.keys())
                c = exp.settings.get('absolute wavenumber column')
                if c in range(0, len(keys)):
                    dpg.set_item_label(f"Exp file abs range {index}", f"{int(exp.columns[keys[c]][0])}..{int(exp.columns[keys[c]][-1])} cm⁻¹")
                c = exp.settings.get('relative wavenumber column')
                if c in range(0, len(keys)):
                    dpg.set_item_label(f"Exp file rel range {index}", f"{int(exp.columns[keys[c]][0])}..{int(exp.columns[keys[c]][-1])} cm⁻¹")
                c = exp.settings.get('intensity column')
                if c in range(0, len(keys)):
                    dpg.set_item_label(f"Exp file int {index}", f"{max(exp.columns[keys[c]])}")
                dpg.configure_item(f"delete exp file {index}", user_data=exp, callback=lambda s, a, u: self.viewmodel.delete_experimental_file(u))

                with dpg.popup(f"Exp file abs range {index}", min_size=(300, 40)):
                    with dpg.menu(label="Select file column"):
                        for key in keys:
                            dpg.add_menu_item(label=f"{key}, {exp.columns[key][0]}, {exp.columns[key][1]}, {exp.columns[key][2]}, ...", user_data=key, callback=lambda s, a, u: exp.set_column_usage(u, "abs"))

                with dpg.popup(f"Exp file rel range {index}", min_size=(300, 40)):
                    with dpg.menu(label="Select file column"):
                        for key in keys:
                            dpg.add_menu_item(label=f"{key}, {exp.columns[key][0]}, {exp.columns[key][1]}, {exp.columns[key][2]}, ...", user_data=key, callback=lambda s, a, u: exp.set_column_usage(u, "rel"))

                with dpg.popup(f"Exp file int {index}", min_size=(300, 40)):
                    with dpg.menu(label="Select file column"):
                        for key in keys:
                            dpg.add_menu_item(label=f"{key}, {exp.columns[key][0]}, {exp.columns[key][1]}, {exp.columns[key][2]}, ...", user_data=key, callback=lambda s, a, u: exp.set_column_usage(u, "int"))

    def update_experimental_data(self, *args):
        """Display all the experimental data (from scratch, in table)"""
        print(f"Updating exp data: {[e.settings for e in ExperimentalSpectrum.spectra_list]}")
        nr_displayed_experiments = self.nr_experiment_rows
        for i in range(0, min(nr_displayed_experiments, len(ExperimentalSpectrum.spectra_list))):
            self.update_experiment(i)
        if len(ExperimentalSpectrum.spectra_list) < nr_displayed_experiments:
            for i in range(len(ExperimentalSpectrum.spectra_list), nr_displayed_experiments):
                if dpg.does_item_exist(f"experiment row {i}"):
                    dpg.delete_item(f"experiment row {i}")
                    self.nr_experiment_rows -= 1
        else:
            for i in range(nr_displayed_experiments, len(ExperimentalSpectrum.spectra_list)):
                self.add_experiment_row()

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
                dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 12, 6)
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

        # with dpg.theme() as action_bar_theme:  # Set up some kind of centralized theme supply? All action bars should probably look the same...
        #     with dpg.theme_component(dpg.mvAll):
        #         dpg.add_theme_color(dpg.mvThemeCol_Button, [0, 0, 0, 0])
        #         dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 0, 0)
        #         dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, 0)
        #         dpg.add_theme_color(dpg.mvThemeCol_ChildBg, [200, 200, 255, 80])
        #         dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, [200, 200, 255, 50])
        #
        # dpg.bind_item_theme("project setup action bar", action_bar_theme)

        with dpg.theme() as self.empty_field_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, [160, 0, 0, 30])
                dpg.add_theme_color(dpg.mvThemeCol_Border, [120, 0, 0, 255])
                dpg.add_theme_color(dpg.mvThemeCol_BorderShadow, [160, 0, 0, 0])
                dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)

        if dpg.does_item_exist(f"temp table hint input"):
            dpg.bind_item_theme(f"temp table hint input", self.empty_field_theme)

        with dpg.theme() as self.full_field_theme:
            with dpg.theme_component(dpg.mvInputText):
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, [0, 40, 0, 100])
                dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0)

        with dpg.theme() as self.actual_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, palette[3])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, palette[6])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, palette[4])
        dpg.bind_item_theme("add state button", self.actual_button_theme)

        with dpg.theme() as inactive_big_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, [60, 20, 200, 50])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [60, 20, 200, 50])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [60, 20, 200, 50])
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 12, 20)
                dpg.add_theme_color(dpg.mvThemeCol_Text, [255, 255, 255, 120])
        dpg.bind_item_theme("auto import", inactive_big_button_theme)
        dpg.bind_item_theme("import done", inactive_big_button_theme)

        with dpg.theme() as self.big_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, [60, 20, 200])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [40, 20, 200])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, palette[4])
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 12, 20)
                dpg.add_theme_color(dpg.mvThemeCol_Text, [255, 255, 255, 200])

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

