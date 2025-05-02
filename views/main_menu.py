import os.path

from models.settings_manager import Settings
from utility.item_themes import ItemThemes
from viewmodels.main_viewmodel import MainViewModel, noop
import dearpygui.dearpygui as dpg
from utility.icons import Icons
from utility.system_file_browser import *
from screeninfo import get_monitors
from contextlib import contextmanager
import webbrowser
from launcher import Launcher


class MainMenu:
    """Takes care of the viewport menu as well as keyboard shortcuts (combinations including Ctrl or Alt only)"""
    def __init__(self, viewmodel: MainViewModel):
        self.viewmodel = viewmodel
        self.icons = Icons()

        # Helper variables for various stuff below; handle with care
        self.currently_pressed = []     # Keeps track of presently pressed keys
        self.alter_shortcut_of = None   # Marks shortcut to be modified by configure shortcuts window
        monitor = get_monitors()[0]     # For modal window placement (relative to viewport not working...)
        self.actions = {}               # Dict of all available (shortcuttable & menu-listable) actions
        # self.menu_tables = {}           # Collects the tables shown in menus (mostly for theme application)
        sep = 0                         # Placeholder representing a separator in the menu
        self.button_callbacks = [noop, noop, noop]  # functions to be executed on button clicks
        self.selectables = {}

        # Registries
        with dpg.handler_registry():
            dpg.add_key_press_handler(callback=self._on_key_down)
            dpg.add_key_release_handler(callback=self._on_key_released)

        # Register every (shortcuttable, menu-listable) action here; then add it to the menu_items to show in menu.
        with self._actions_registry():  # First argument is the "action" identifactor (basically my tag)
            self._register_action("New", label="New Project...", callback=self._on_new)
            self._register_action("Open", label="Open Project...", callback=self._on_open, icon=Icons.folder_open)
            self._register_action("Save", callback=self._on_save, icon=Icons.floppy)
            self._register_action("Save as", label="Save As...", callback=self._on_save_as)
            self._register_action("Exit", callback=self._on_exit, icon=Icons.power_off)
            self._register_action("Sanity checks", label="Turn off sanity checks" if self.viewmodel.get_setting(Settings.CHECKS) else "Turn on sanity checks", callback=self._on_toggle_sanity_checks, icon=Icons.check_circle_o)
            self._register_action("Show log file", label="Show project log file", callback=self._on_show_project_log, icon=Icons.file_text)
            self._register_action("Shortcuts", label="Configure shortcuts...", callback=self._show_configure_shortcuts,
                                  icon=Icons.keyboard)
            self._register_action("User Guide", label="User Guide...", callback=self._user_guide, icon=Icons.book)
            self._register_action("Report bug", label="Report a Bug...", callback=self._report_bug, icon=Icons.bug)

        # Each menu is a dict with "name": [list of items]; items can be actions, menus, or a separator line (sep).
        self.menu_items = {"Projects": ["New", "Open",
                                        {"Open Recent": [(r, self._open_recent) for r in self.viewmodel.get_recents()]},
                                        sep, "Save", "Save as", sep, "Exit"],
                           "Settings": ["Sanity checks"],
                           "Tools": ["Shortcuts"],
                           "Help": ["User Guide", "Report bug", "Show log file"]}

        # Construct main menu bar from self.menu_items
        # with dpg.viewport_menu_bar() as self.menu_bar:
        with dpg.menu_bar() as self.menu_bar:
            self._add_menu(self.menu_items)

        # Looks like I can have only one modal window, so I'll toggle the contents instead.
        self.modal_child_window_tags = []
        with dpg.window(label="modal", show=False, modal=True, no_collapse=True, no_scrollbar=True, no_resize=True, tag="the one modal window", width=600, height=400, pos=(int(monitor.x + monitor.width/2-600/2), int(monitor.y + monitor.height/2-400/2))):
            with dpg.child_window(show=False, no_scrollbar=True, tag="configure shortcuts window"):
                self.modal_child_window_tags.append("configure shortcuts window")
                with dpg.table(height=300, tag="shortcuts table", indent=42, header_row=False):
                    # dpg.add_table_column(label="")
                    dpg.add_table_column(label="    action", indent_enable=True)
                    dpg.add_table_column(label="shortcut")
                    for key, action in self.actions.items():
                        with dpg.table_row():
                            dpg.add_button(label=action.get("label", key).replace("...", ""), width=-1)
                            shortcut_label = action.get("shortcut_string", "")
                            dpg.add_selectable(label=shortcut_label, span_columns=True, disable_popup_close=True, callback=self._on_select_new_shortcut, user_data=key, tag=f"shortcut of {key}")
                with dpg.table(header_row=False, width=-1):
                    dpg.add_table_column()
                    dpg.add_table_column()
                    with dpg.table_row():
                        dpg.add_button(label="Restore Defaults", width=-1, callback=self._restore_default_shortcuts)
                        dpg.add_button(label="OK", width=-1, callback=self._close_modal_window)

            with dpg.child_window(show=False, tag="input shortcut window"):
                self.modal_child_window_tags.append("input shortcut window")
                dpg.add_button(label="Press desired shortcut...", width=-1, height=-1, tag="press shortcut")

            # Some standard modal window fillings
            with dpg.child_window(show=False, tag="message and buttons"):
                self.modal_child_window_tags.append("message and buttons")
                dpg.add_spacer(height=80)
                self.icons.insert(dpg.add_button(tag="modal icon button", height=60, width=-1), icon=Icons.exclamation_triangle, size=50)
                dpg.bind_item_theme("modal icon button", ItemThemes.get_invisible_button_theme())
                dpg.add_button(label="Message", height=100, width=-1, tag="button dialog message")
                dpg.add_spacer(height=40)
                with dpg.table(header_row=False, show=False, width=-1, tag="three buttons table"):
                    dpg.add_table_column()
                    dpg.add_table_column()
                    dpg.add_table_column()
                    with dpg.table_row():
                        dpg.add_button(label="Button 3", width=-1, tag="Button 3/3", callback=self._on_modal_button_press, user_data=2)
                        dpg.add_button(label="Button 2", width=-1, tag="Button 2/3", callback=self._on_modal_button_press, user_data=1)
                        dpg.add_button(label="Button 1", width=-1, tag="Button 1/3", callback=self._on_modal_button_press, user_data=0)
                with dpg.table(header_row=False, show=False, width=-1, tag="two buttons table"):
                    dpg.add_table_column()
                    dpg.add_table_column()
                    with dpg.table_row():
                        dpg.add_button(label="Button 2", width=-1, tag="Button 2/2", callback=self._on_modal_button_press, user_data=1)
                        dpg.add_button(label="Button 1", width=-1, tag="Button 1/2", callback=self._on_modal_button_press, user_data=0)
                with dpg.table(header_row=False, show=False, width=-1, tag="one button table"):
                    dpg.add_table_column(width_stretch=True, init_width_or_weight=2)
                    dpg.add_table_column(width_stretch=True, init_width_or_weight=1)
                    with dpg.table_row():
                        dpg.add_spacer(width=10)
                        dpg.add_button(label="Button 1", width=-1, tag="Button 1/1", callback=self._on_modal_button_press, user_data=0)
        self.setup_menu_theme()

    def show_dialog(self, title, message, icon=Icons.exclamation_triangle, buttons=None):  # buttons: list of ("label", callback)
        if buttons is None:
            buttons = [("Ok", noop)]
        dpg.show_item("the one modal window")
        self.icons.insert("modal icon button", icon=icon, size=50)
        self._show_modal_child("message and buttons")
        if len(buttons) == 1:
            dpg.show_item("one button table")
            dpg.hide_item("two buttons table")
            dpg.hide_item("three buttons table")
            dpg.set_item_label("Button 1/1", buttons[0][0])
        elif len(buttons) == 2:
            dpg.hide_item("one button table")
            dpg.show_item("two buttons table")
            dpg.hide_item("three buttons table")
            dpg.set_item_label("Button 1/2", buttons[0][0])
            dpg.set_item_label("Button 2/2", buttons[1][0])
        elif len(buttons) == 3:
            dpg.hide_item("one button table")
            dpg.hide_item("two buttons table")
            dpg.show_item("three buttons table")
            dpg.set_item_label("Button 1/3", buttons[0][0])
            dpg.set_item_label("Button 2/3", buttons[1][0])
            dpg.set_item_label("Button 3/3", buttons[2][0])
        for i in range(len(buttons)):
            self.button_callbacks[i] = buttons[i][1]
        dpg.set_item_label("button dialog message", message)

        dpg.configure_item("the one modal window", no_title_bar=False, label=title)

    def _on_modal_button_press(self, s, a, u, *args):
        dpg.hide_item("the one modal window")
        if u in [0, 1, 2]:
            self.button_callbacks[u]()

    def _show_modal_child(self, tag, *args):
        if tag not in self.modal_child_window_tags:
            return
        for t in self.modal_child_window_tags:
            dpg.hide_item(t)
        dpg.show_item(tag)

    def _show_configure_shortcuts(self, *args):
        dpg.show_item("the one modal window")
        self._show_modal_child("configure shortcuts window")
        dpg.configure_item("the one modal window", no_title_bar=False, label="Configure keyboard shortcuts")

    def _user_guide(self, *args):
        issues_url = 'https://spectramatcher.gitbook.io/spectramatcher'
        webbrowser.open(issues_url, new=2)

    def _report_bug(self, *args):
        issues_url = 'https://github.com/giogina/SpectraMatcher/issues'
        webbrowser.open(issues_url, new=2)

    def _add_menu(self, menu: dict, indent=0):
        icon_column_width = 24  # Space to the left of each menu item (placeholder for icons)
        for key, items in menu.items():
            with dpg.menu(label=key, tag=f"menu_{key}", indent=indent):
                i = 0
                while i < len(items):
                    if type(items[i]) == str:  # Start table of actions
                        with dpg.table(header_row=False, policy=dpg.mvTable_SizingFixedFit, no_pad_innerX=True,
                                       borders_outerH=False, borders_outerV=False, no_keep_columns_visible=True):
                            dpg.add_table_column(label="icon", width_fixed=True, init_width_or_weight=icon_column_width)
                            dpg.add_table_column(label="action", width_stretch=True, init_width_or_weight=1)
                            dpg.add_table_column(label="shortcut", width_stretch=True, init_width_or_weight=1)

                            while i < len(items) and type(items[i]) == str:
                                action = self.actions.get(items[i])
                                if action:
                                    with dpg.table_row():
                                        if action.get("icon"):
                                            self.icons.insert(dpg.add_button(width=16, height=16), action["icon"], 14)
                                        else:
                                            dpg.add_spacer(width=icon_column_width)
                                        self.selectables[items[i]] = dpg.add_selectable(label=action["label"], span_columns=True, callback=action["callback"], user_data=items[i])
                                        shortcut_label = action.get("shortcut_string", "")
                                        dpg.add_button(label=shortcut_label, width=-1)
                                i += 1
                            i -= 1  # Undo last raise (which will be re-done at end of outer while loop)
                    elif type(items[i]) == dict:  # nested menu item!
                        self._add_menu(items[i], indent=icon_column_width)
                    elif type(items[i]) == tuple:  # Pair of label and callback for dynamic, unregistered actions
                        dpg.add_menu_item(label=items[i][0], indent=icon_column_width, callback=items[i][1], user_data=items[i][0])
                    elif type(items[i]) == int:
                        dpg.add_spacer(height=1)
                        dpg.add_separator()
                        dpg.add_spacer(height=1)
                    i += 1

    def setup_menu_theme(self):
        # menu_font = markdown.set_font(font_size=16)
        with dpg.theme() as menu_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Header, [0, 0, 0, 0])
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Text, [255, 255, 255, 150])
                dpg.add_theme_color(dpg.mvThemeCol_Button, [0, 0, 0, 0])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [0, 0, 0, 0])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [0, 0, 0, 0])
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, 0)
                dpg.add_theme_style(dpg.mvStyleVar_ButtonTextAlign, 1, 0.5)
        for key in self.menu_items.keys():
            # dpg.bind_item_font(f"menu_{key}", menu_font)
            dpg.bind_item_theme(f"menu_{key}", menu_theme)

        with dpg.theme() as modal_child_theme:
            with dpg.theme_component(dpg.mvChildWindow):
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, [0, 0, 0, 0])
                dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 0)
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 3)
                dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 16, 16)
                dpg.add_theme_style(dpg.mvStyleVar_CellPadding, 8, 0)
                dpg.add_theme_color(dpg.mvThemeCol_Border, [50, 50, 120])
                dpg.add_theme_color(dpg.mvThemeCol_PopupBg, [22, 22, 72])
                # dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, [11, 11, 36, 100])
        dpg.bind_item_theme("the one modal window", modal_child_theme)

        with dpg.theme() as invisible_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, [0, 0, 0, 0])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [0, 0, 0, 0])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [0, 0, 0, 0])

        with dpg.theme() as table_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, [0, 0, 0, 0])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [0, 0, 0, 0])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [0, 0, 0, 0])
                dpg.add_theme_style(dpg.mvStyleVar_CellPadding, 32, 6)
                dpg.add_theme_style(dpg.mvStyleVar_ButtonTextAlign, 0, 0.5)
        dpg.bind_item_theme("shortcuts table", table_theme)
        dpg.bind_item_theme("press shortcut", invisible_button_theme)
        dpg.bind_item_theme("button dialog message", invisible_button_theme)

    @contextmanager
    def _actions_registry(self):
        yield self.actions
        self._assign_shortcuts_to_actions()

    def _register_action(self, action, label="", callback=noop, icon=""):
        if not label:
            label = action
        self.actions[action] = {"label": label, "callback": callback, "icon": icon}

    def _on_save_as(self, *args):
        print(f"Save as requested")
        file = save_as_file_dialog(self.viewmodel.get_setting("projectsPath", os.path.expanduser("~")))
        if len(file) > 4:
            self.viewmodel.on_save_as(file)

    def _on_save(self, *args):
        self.viewmodel.on_save()

    def _on_new(self, *args):
        print(f"New project")
        self.viewmodel.on_new()

    def _on_exit(self, *args):
        dpg.stop_dearpygui()

    def _on_open(self, *args):
        print(f"Open project")
        file = open_project_file_dialog(self.viewmodel.get_setting("projectsPath", os.path.expanduser("~")))
        if file and len(file) > 4 and os.path.exists(file):
            self.viewmodel.on_open(file)

    def _open_recent(self, s, a, u, *args):
        self.viewmodel.on_open(u)

    def _on_toggle_sanity_checks(self, s, a, u, *args):
        checks = self.viewmodel.toggle_sanity_checks()
        if checks:
            dpg.set_item_label(self.selectables["Sanity checks"], "Turn off sanity checks")  # todo: Put text according to settings initially
        else:
            dpg.set_item_label(self.selectables["Sanity checks"], "Turn on sanity checks")
        pass

    def _on_show_project_log(self, s, a, u, *args):
        Launcher.show_log_file()

    def _on_select_new_shortcut(self, s, a, u, *args):
        self._show_modal_child("input shortcut window")
        dpg.configure_item("the one modal window", no_title_bar=True)
        dpg.set_item_label("press shortcut", label=f"Press desired shortcut to {u}...")
        self.alter_shortcut_of = u

    def _close_modal_window(self, *args):
        dpg.hide_item("the one modal window")

    def _restore_default_shortcuts(self, *args):
        self.viewmodel.restore_default_shortcuts()
        self._repopulate_shortcuts_table()

    def _assign_shortcuts_to_actions(self):
        shortcuts = self.viewmodel.get_shortcuts()
        for shortcut, action in shortcuts.items():
            if self.actions[action]:
                self.actions[action]["shortcut"] = shortcut
                self.actions[action]["shortcut_string"] = self._get_shortcut_string(shortcut)
            else:
                self.actions[action]["shortcut"] = None
                self.actions[action]["shortcut_string"] = ""

    def _repopulate_shortcuts_table(self):
        """Delete all shortcuts and replace them by current value from settings."""
        for key in self.actions.keys():
            self.actions[key]["shortcut"] = None
            self.actions[key]["shortcut_string"] = ""
        self._assign_shortcuts_to_actions()
        for key in self.actions.keys():
            dpg.configure_item(f"shortcut of {key}", label=self.actions[key]["shortcut_string"])

    def _update_shortcut(self, action, shortcut):
        # Delete previous action of this shortcut (if it exists):
        for key in self.actions.keys():
            if shortcut == self.actions[key].get("shortcut"):
                self.actions[key]["shortcut"] = None
                self.actions[key]["shortcut_string"] = ""
                break

        shortcut_string = self._get_shortcut_string(shortcut)
        self.actions[action]["shortcut"] = shortcut
        self.actions[action]["shortcut_string"] = shortcut_string
        dpg.configure_item(f"shortcut of {action}", label=shortcut_string)
        self.viewmodel.set_shortcut(action, shortcut)

    def _get_shortcut_string(self, shortcut: tuple):
        return '+'.join([self._dpg_key_to_name(key) for key in shortcut]).replace("Shift+Ctrl", "Ctrl+Shift")

    def _on_key_down(self, s, a, *args):
        # print(self._dpg_key_to_name(a))
        if a not in self.currently_pressed:
            if len(self._dpg_key_to_name(a)):
                self.currently_pressed.append(a)
            shortcuts = self.viewmodel.get_shortcuts()
            action = shortcuts.get(tuple(sorted(self.currently_pressed)))
            if action:
                action_dict = self.actions.get(action)
                if action_dict:
                    callback = action_dict.get("callback")
                    if callback:
                        callback()

    def _on_key_released(self, s, a, *args):
        # If "configure shortcuts" window is open, update shortcut upon release.
        if self.alter_shortcut_of:
            pressed = []
            for key in self.currently_pressed:
                if len(self._dpg_key_to_name(key)):  # only register shortcuts for keys I know the names of.
                    pressed.append(key)
            self._update_shortcut(self.alter_shortcut_of, tuple(sorted(pressed)))
            self.alter_shortcut_of = False
            dpg.configure_item("the one modal window", no_title_bar=False, label="Configure keyboard shortcuts")
            self._show_modal_child("configure shortcuts window")

        if a in self.currently_pressed:
            self.currently_pressed.remove(a)

    def _dpg_key_to_name(self, key):
        raw_dict = {
            "mvKey_0": "0",
            "mvKey_1": "1",
            "mvKey_2": "2",
            "mvKey_3": "3",
            "mvKey_4": "4",
            "mvKey_5": "5",
            "mvKey_6": "6",
            "mvKey_7": "7",
            "mvKey_8": "8",
            "mvKey_9": "9",
            "mvKey_A": "A",
            "mvKey_B": "B",
            "mvKey_C": "C",
            "mvKey_D": "D",
            "mvKey_E": "E",
            "mvKey_F": "F",
            "mvKey_G": "G",
            "mvKey_H": "H",
            "mvKey_I": "I",
            "mvKey_J": "J",
            "mvKey_K": "K",
            "mvKey_L": "L",
            "mvKey_M": "M",
            "mvKey_N": "N",
            "mvKey_O": "O",
            "mvKey_P": "P",
            "mvKey_Q": "Q",
            "mvKey_R": "R",
            "mvKey_S": "S",
            "mvKey_T": "T",
            "mvKey_U": "U",
            "mvKey_V": "V",
            "mvKey_W": "W",
            "mvKey_X": "X",
            "mvKey_Y": "Y",
            "mvKey_Z": "Z",
            "mvKey_Control": "Ctrl",
            "mvKey_LControl": "Ctrl",
            "mvKey_RControl": "Ctrl",
            "mvKey_Alt": "Alt",
            "mvKey_LAlt": "Alt",
            "mvKey_RAlt": "Alt",
            "mvKey_Shift": "Shift",
            "mvKey_LShift": "Shift",
            "mvKey_RShift": "Shift",
            "mvKey_Back": "Back",
            "mvKey_Tab": "Tab",
            "mvKey_Clear": "Clear",
            "mvKey_Return": "Return",
            "mvKey_Pause": "Pause",
            "mvKey_Capital": "Capital",
            "mvKey_Escape": "Escape",
            "mvKey_Spacebar": "Spacebar",
            "mvKey_Prior": "Prior",
            "mvKey_Next": "Next",
            "mvKey_End": "End",
            "mvKey_Home": "Home",
            "mvKey_Left": "Left",
            "mvKey_Up": "Up",
            "mvKey_Right": "Right",
            "mvKey_Down": "Down",
            "mvKey_PrintScreen": "PrintScreen",
            "mvKey_Insert": "Insert",
            "mvKey_Delete": "Delete",
            "mvKey_Help": "Help",
            "mvKey_F1": "F1",
            "mvKey_F2": "F2",
            "mvKey_F3": "F3",
            "mvKey_F4": "F4",
            "mvKey_F5": "F5",
            "mvKey_F6": "F6",
            "mvKey_F7": "F7",
            "mvKey_F8": "F8",
            "mvKey_F9": "F9",
            "mvKey_F10": "F10",
            "mvKey_F11": "F11",
            "mvKey_F12": "F12",
            "mvKey_F13": "F13",
            "mvKey_F14": "F14",
            "mvKey_F15": "F15",
            "mvKey_F16": "F16",
            "mvKey_F17": "F17",
            "mvKey_F18": "F18",
            "mvKey_F19": "F19",
            "mvKey_F20": "F20",
            "mvKey_F21": "F21",
            "mvKey_F22": "F22",
            "mvKey_F23": "F23",
            "mvKey_F24": "F24",
            "mvKey_F25": "F25",
            "mvKey_Colon": ":",
            "mvKey_Plus": "+",
            "mvKey_Comma": ",",
            "mvKey_Minus": "-",
            "mvKey_Period": ".",
            "mvKey_Slash": "/",
            "mvKey_Tilde": "~",
            "mvKey_Open_Brace": "(",
            "mvKey_Backslash": "\\",
            "mvKey_Close_Brace": ")",
        }
        key_dict = {
            getattr(dpg, attr, None): name for attr, name in raw_dict.items() if hasattr(dpg, attr)
        }
        if key_dict.get(key):
            return key_dict.get(key)  # key, get it?
        else:
            return ""



