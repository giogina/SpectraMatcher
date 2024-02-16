from contextlib import contextmanager
from typing import Union, List, Tuple
import dearpygui._dearpygui as internal_dpg


@contextmanager
def custom_popup(parent: Union[int, str], mousebutton: int = internal_dpg.mvMouseButton_Right, modal: bool=False, tag:Union[int, str]=0, min_size:Union[List[int], Tuple[int, ...]]=[100,100], max_size: Union[List[int], Tuple[int, ...]] =[30000, 30000], no_move: bool=False, no_background: bool=False, handler_registry=None) -> int:
    """A window that will be displayed when a parent item is hovered and the corresponding mouse button has been clicked. By default a popup will shrink fit the items it contains.
    This is useful for context windows, and simple modal window popups.
    When popups are used a modal they have more avaliable settings (i.e. title, resize, width, height) These
    can be set by using configure item.
    This is a light wrapper over window. For more control over a modal|popup window use a normal window with the modal|popup keyword
    and set the item handler and mouse events manually.

    Args:
        parent: The UI item that will need to be hovered.
        **mousebutton: The mouse button that will trigger the window to popup.
        **modal: Will force the user to interact with the popup.
        **min_size: New in 1.4. Minimum window size.
        **max_size: New in 1.4. Maximum window size.
        **no_move: New in 1.4. Prevents the window from moving based on user input.
        **no_background: New in 1.4. Sets Background and border alpha to transparent.

    Returns:
        item's uuid
    """
    try:
        if tag == 0:
            _internal_popup_id = internal_dpg.generate_uuid()
        else:
            _internal_popup_id = tag
        if handler_registry is not None:
            _handler_reg_id = handler_registry
        else:
            _handler_reg_id = internal_dpg.add_item_handler_registry()
        internal_dpg.add_item_clicked_handler(mousebutton, parent=_handler_reg_id, callback=lambda: internal_dpg.configure_item(_internal_popup_id, show=True))
        internal_dpg.bind_item_handler_registry(parent, _handler_reg_id)
        if modal:
            internal_dpg.add_window(modal=True, show=False, tag=_internal_popup_id, autosize=True, min_size=min_size, max_size=max_size, no_move=no_move, no_background=no_background)
        else:
            internal_dpg.add_window(popup=True, show=False, tag=_internal_popup_id, autosize=True, min_size=min_size, max_size=max_size, no_move=no_move, no_background=no_background)
        internal_dpg.push_container_stack(internal_dpg.last_container())
        yield _internal_popup_id

    finally:
        internal_dpg.pop_container_stack()