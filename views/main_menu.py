from tkinter import simpledialog

from launcher import Launcher
from viewmodels.main_viewmodel import MainViewModel, noop
import dearpygui.dearpygui as dpg
from utility.icons import Icons
from utility.system_file_browser import *
import logging
from screeninfo import get_monitors
from contextlib import contextmanager
# TODO: Implement more shortcuts & menu actions (visible panels? Switch to spectrum tab?)

class MainMenu:
    """Takes care of the viewport menu as well as keyboard shortcuts (combinations including Ctrl or Alt only)"""
    def __init__(self, viewmodel: MainViewModel):
        self.viewmodel = viewmodel
        self.logger = logging.getLogger(__name__)
        self.icons = Icons()

        # Helper variables for various stuff below; handle with care
        self.currently_pressed = []     # Keeps track of presently pressed keys
        self.alter_shortcut_of = None   # Marks shortcut to be modified by configure shortcuts window
        monitor = get_monitors()[0]     # For modal window placement (relative to viewport not working...)
        self.actions = {}               # Dict of all available (shortcuttable & menu-listable) actions
        # self.menu_tables = {}           # Collects the tables shown in menus (mostly for theme application)
        sep = 0                         # Placeholder representing a separator in the menu
        self.button_callbacks = [noop, noop, noop]  # functions to be executed on button clicks

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

            self._register_action("Shortcuts", label="Configure shortcuts...", callback=self._show_configure_shortcuts,
                                  icon=Icons.keyboard)

        # Each menu is a dict with "name": [list of items]; items can be actions, menus, or a separator line (sep).
        self.menu_items = {"Projects": ["New", "Open",
                                        {"Open Recent": [(r, self._open_recent) for r in self.viewmodel.get_recents()]},
                                        sep, "Save", "Save as", sep, "Exit"],
                           "Tools": ["Shortcuts"]}

        # Construct main menu bar from self.menu_items
        # with dpg.viewport_menu_bar() as self.menu_bar:
        with dpg.menu_bar() as self.menu_bar:
            self._add_menu(self.menu_items)

        # Looks like I can have only one modal window, so I'll toggle the contents instead.
        self.modal_child_window_tags = []
        with dpg.window(label="modal", show=False, modal=True, no_collapse=True, no_scrollbar=True, no_resize=True, tag="the one modal window", width=600, height=400, pos=(int(monitor.width/2-600/2), int(monitor.height/2-400/2))):
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
                self.modal_child_window_tags.append("message and buttons")  # TODO: "warning" icon (button above the message with self.icon.(dpg.add_button(), icon=Icon.exclamation_triangle, size=32)
                dpg.add_button(label="Message", height=300, width=-1, tag="button dialog message")  # TODO: Same with Icons.x_circle for errors! (Could even write a specialized "show error" function)
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

    def show_dialog(self, title, message, buttons=None):  # buttons: list of ("label", callback)
        if buttons is None:
            buttons = [("Ok", noop)]
        dpg.show_item("the one modal window")
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

    def _on_modal_button_press(self, s, a, u):
        dpg.hide_item("the one modal window")
        if u in [0, 1, 2]:
            self.button_callbacks[u]()

    def _show_modal_child(self, tag):
        if tag not in self.modal_child_window_tags:
            return
        for t in self.modal_child_window_tags:
            dpg.hide_item(t)
        dpg.show_item(tag)

    def _show_configure_shortcuts(self):
        dpg.show_item("the one modal window")
        self._show_modal_child("configure shortcuts window")
        dpg.configure_item("the one modal window", no_title_bar=False, label="Configure keyboard shortcuts")

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
                                        dpg.add_selectable(label=action["label"], span_columns=True,
                                                           callback=action["callback"], user_data=items[i])
                                        shortcut_label = action.get("shortcut_string", "")
                                        # if len(shortcut_label):
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
        # Before yielding, you could also modify self.actions if needed
        yield self.actions
        self._assign_shortcuts_to_actions()

    def _register_action(self, action, label="", callback=noop, icon=""):
        if not label:
            label = action
        self.actions[action] = {"label": label, "callback": callback, "icon": icon}

    def _on_save_as(self):
        self.logger.info(f"Save as requested")
        file = save_as_file_dialog(self.viewmodel.get_setting("projectsPath", "/"))
        if len(file):
            self.viewmodel.on_save_as(file)

    def _on_save(self):
        self.viewmodel.on_save()

    def _on_new(self):
        self.logger.info(f"New project")
        self.viewmodel.on_new()

    def _on_exit(self):
        dpg.stop_dearpygui()

    def _on_open(self):
        self.logger.info(f"Open project")
        file = open_project_file_dialog(self.viewmodel.get_setting("projectsPath", "/"))
        if file:
            self.viewmodel.on_open(file)

    def _open_recent(self, s, a, u):
        self.viewmodel.on_open(u)

    def _on_select_new_shortcut(self, s, a, u):
        self._show_modal_child("input shortcut window")
        dpg.configure_item("the one modal window", no_title_bar=True)
        dpg.set_item_label("press shortcut", label=f"Press desired shortcut to {u}...")
        self.alter_shortcut_of = u

    def _close_modal_window(self):
        dpg.hide_item("the one modal window")

    def _restore_default_shortcuts(self):
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

    def _on_key_down(self, s, a):
        if a not in self.currently_pressed:
            self.currently_pressed.append(a)
            shortcuts = self.viewmodel.get_shortcuts()
            action = shortcuts.get(tuple(sorted(self.currently_pressed)))
            if action:
                action_dict = self.actions.get(action)
                if action_dict:
                    callback = action_dict.get("callback")
                    if callback:
                        callback()

    def _on_key_released(self, s, a):
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
        key_dict = {
            dpg.mvKey_0: "0",
            dpg.mvKey_1: "1",
            dpg.mvKey_2: "2",
            dpg.mvKey_3: "3",
            dpg.mvKey_4: "4",
            dpg.mvKey_5: "5",
            dpg.mvKey_6: "6",
            dpg.mvKey_7: "7",
            dpg.mvKey_8: "8",
            dpg.mvKey_9: "9",
            dpg.mvKey_A: "A",
            dpg.mvKey_B: "B",
            dpg.mvKey_C: "C",
            dpg.mvKey_D: "D",
            dpg.mvKey_E: "E",
            dpg.mvKey_F: "F",
            dpg.mvKey_G: "G",
            dpg.mvKey_H: "H",
            dpg.mvKey_I: "I",
            dpg.mvKey_J: "J",
            dpg.mvKey_K: "K",
            dpg.mvKey_L: "L",
            dpg.mvKey_M: "M",
            dpg.mvKey_N: "N",
            dpg.mvKey_O: "O",
            dpg.mvKey_P: "P",
            dpg.mvKey_Q: "Q",
            dpg.mvKey_R: "R",
            dpg.mvKey_S: "S",
            dpg.mvKey_T: "T",
            dpg.mvKey_U: "U",
            dpg.mvKey_V: "V",
            dpg.mvKey_W: "W",
            dpg.mvKey_X: "X",
            dpg.mvKey_Y: "Y",
            dpg.mvKey_Z: "Z",
            dpg.mvKey_Control: "Ctrl",
            dpg.mvKey_Alt: "Alt",
            dpg.mvKey_Shift: "Shift",
            dpg.mvKey_Back: "Back",
            dpg.mvKey_Tab: "Tab",
            dpg.mvKey_Clear: "Clear",
            dpg.mvKey_Return: "Return",
            dpg.mvKey_Pause: "Pause",
            dpg.mvKey_Capital: "Capital",
            dpg.mvKey_Escape: "Escape",
            dpg.mvKey_Spacebar: "Spacebar",
            dpg.mvKey_Prior: "Prior",
            dpg.mvKey_Next: "Next",
            dpg.mvKey_End: "End",
            dpg.mvKey_Home: "Home",
            dpg.mvKey_Left: "Left",
            dpg.mvKey_Up: "Up",
            dpg.mvKey_Right: "Right",
            dpg.mvKey_Down: "Down",
            dpg.mvKey_PrintScreen: "PrintScreen",
            dpg.mvKey_Insert: "Insert",
            dpg.mvKey_Delete: "Delete",
            dpg.mvKey_Help: "Help",
            dpg.mvKey_F1: "F1",
            dpg.mvKey_F2: "F2",
            dpg.mvKey_F3: "F3",
            dpg.mvKey_F4: "F4",
            dpg.mvKey_F5: "F5",
            dpg.mvKey_F6: "F6",
            dpg.mvKey_F7: "F7",
            dpg.mvKey_F8: "F8",
            dpg.mvKey_F9: "F9",
            dpg.mvKey_F10: "F10",
            dpg.mvKey_F11: "F11",
            dpg.mvKey_F12: "F12",
            dpg.mvKey_F13: "F13",
            dpg.mvKey_F14: "F14",
            dpg.mvKey_F15: "F15",
            dpg.mvKey_F16: "F16",
            dpg.mvKey_F17: "F17",
            dpg.mvKey_F18: "F18",
            dpg.mvKey_F19: "F19",
            dpg.mvKey_F20: "F20",
            dpg.mvKey_F21: "F21",
            dpg.mvKey_F22: "F22",
            dpg.mvKey_F23: "F23",
            dpg.mvKey_F24: "F24",
            dpg.mvKey_F25: "F25",
            dpg.mvKey_Colon: ":",
            dpg.mvKey_Plus: "+",
            dpg.mvKey_Comma: ",",
            dpg.mvKey_Minus: "-",
            dpg.mvKey_Period: ".",
            dpg.mvKey_Slash: "/",
            dpg.mvKey_Tilde: "~",
            dpg.mvKey_Open_Brace: "(",
            dpg.mvKey_Backslash: "\\",
            dpg.mvKey_Close_Brace: ")",
        }
        if key_dict.get(key):
            return key_dict.get(key)  # key, get it?
        else:
            return ""



