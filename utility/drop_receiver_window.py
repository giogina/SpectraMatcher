import dearpygui.dearpygui as dpg
import DearPyGui_DragAndDrop as dpg_dnd


def initialize_dnd():
    dpg_dnd.initialize()


def drag_over(keys):
    dpg_dnd.set_drop_effect()


class DropReceiverWindow(dpg_dnd.DragAndDrop):
    window: int = None
    dpg_text: int

    def __init__(self, drop_callback, hover_drag_theme, normal_theme):
        super().__init__()
        self.drop_callback = drop_callback
        self.hover_drag_theme = hover_drag_theme
        self.normal_theme = normal_theme

    def create(self, **kwargs):
        self.window = dpg.add_child_window(**kwargs)
        dpg.bind_item_theme(self.window, self.normal_theme)
        dpg_dnd.set_drag_over(drag_over)

    def DragOver(self, keyState: list):
        if self.window is None:
            return
        if dpg.is_item_hovered(self.window):
            dpg.bind_item_theme(self.window, self.hover_drag_theme)
            dpg_dnd.set_drop_effect(dpg_dnd.DROPEFFECT.MOVE)
        else:
            dpg.bind_item_theme(self.window, self.normal_theme)

    def Drop(self, dataObject: dpg_dnd.DragAndDropDataObject, keyState: list):
        if self.window is None:
            return
        dpg.bind_item_theme(self.window, self.normal_theme)
        if dpg.is_item_hovered(self.window):
            self.drop_callback(dataObject)


