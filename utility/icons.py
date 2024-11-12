import os

import dearpygui.dearpygui as dpg


class Icons:
    _instance = None
    _is_initialized = False
    _font_reg = None

    # https://fontawesome.com/v4/cheatsheet/
    open_folder = 0xf07c
    star = 0xf005
    check = 0xf00c
    x = 0xf00d
    folder_plus = 0xf65e
    folder_minus = 0xf65d
    file_arrow_up = 0xf574
    file_arrow_down = 0xf56d
    file_plus = 0xf477
    adjust = 0xf042
    align_center = 0xf037
    align_justify = 0xf039
    angle_double_down = 0xf103
    angle_double_left = 0xf100
    angle_double_right = 0xf101
    angle_double_up = 0xf102
    angle_down = 0xf107
    angle_left = 0xf104
    angle_right = 0xf105
    angle_up = 0xf106
    archive = 0xf187
    area_chart = 0xf1fe
    arrow_circle_down = 0xf0ab
    arrow_circle_left = 0xf0a8
    arrow_circle_o_down = 0xf01a
    arrow_circle_o_left = 0xf190
    arrow_circle_o_right = 0xf18e
    arrow_circle_o_up = 0xf01b
    arrow_circle_right = 0xf0a9
    arrow_circle_up = 0xf0aa
    arrow_down = 0xf063
    arrow_left = 0xf060
    arrow_right = 0xf061
    arrow_up = 0xf062
    arrows = 0xf047
    arrows_alt = 0xf0b2
    arrows_h = 0xf07e
    arrows_v = 0xf07d
    asterisk = 0xf069
    backward = 0xf04a
    balance_scale = 0xf24e
    ban = 0xf05e
    bar_chart = 0xf080
    bars = 0xf0c9
    battery_empty = 0xf244
    battery_full = 0xf240
    battery_half = 0xf242
    battery_quarter = 0xf243
    battery_three_quarters = 0xf241
    bell = 0xf0f3
    bell_o = 0xf0a2
    bell_slash = 0xf1f6
    bell_slash_o = 0xf1f7
    binoculars = 0xf1e5
    bold = 0xf032
    bolt = 0xf0e7
    bomb = 0xf1e2
    book = 0xf02d
    bookmark = 0xf02e
    bookmark_o = 0xf097
    briefcase = 0xf0b1
    bug = 0xf188
    bullhorn = 0xf0a1
    bullseye = 0xf140
    calculator = 0xf1ec
    camera = 0xf030
    caret_down = 0xf0d7
    caret_left = 0xf0d9
    caret_right = 0xf0da
    caret_square_o_down = 0xf150
    caret_square_o_left = 0xf191
    caret_square_o_right = 0xf152
    caret_square_o_up = 0xf151
    caret_up = 0xf0d8
    chain = 0xf0c1
    chain_broken = 0xf127
    check_circle = 0xf058
    check_circle_o = 0xf05d
    check_square = 0xf14a
    check_square_o = 0xf046
    chevron_circle_down = 0xf13a
    chevron_circle_left = 0xf137
    chevron_circle_right = 0xf138
    chevron_circle_up = 0xf139
    chevron_down = 0xf078
    chevron_left = 0xf053
    chevron_right = 0xf054
    chevron_up = 0xf077
    circle = 0xf111
    circle_o = 0xf10c
    circle_o_notch = 0xf1ce
    circle_thin = 0xf1db
    clipboard = 0xf0ea
    clock_o = 0xf017
    clone = 0xf24d
    close = 0xf00d
    code = 0xf121
    columns = 0xf0db
    compress = 0xf066
    copy = 0xf0c5
    crop = 0xf125
    crosshairs = 0xf05b
    cube = 0xf1b2
    cubes = 0xf1b3
    cut = 0xf0c4
    dashboard = 0xf0e4
    database = 0xf1c0
    unindent = 0xf03b
    checker_board = 0xf1a5
    monitor = 0xf108
    diamond = 0xf219
    dot_circle_o = 0xf192
    download = 0xf019
    edit = 0xf044
    eject = 0xf052
    ellipsis_h = 0xf141
    ellipsis_v = 0xf142
    envelope = 0xf0e0
    envelope_o = 0xf003
    envelope_open = 0xf2b6
    envelope_open_o = 0xf2b7
    eraser = 0xf12d
    exchange = 0xf0ec
    exclamation = 0xf12a
    exclamation_circle = 0xf06a
    exclamation_triangle = 0xf071
    expand = 0xf065
    external_link = 0xf08e
    external_link_square = 0xf14c
    eye = 0xf06e
    eye_slash = 0xf070
    eyedropper = 0xf1fb
    fast_backward = 0xf049
    fast_forward = 0xf050
    file = 0xf15b
    file_archive = 0xf1c6
    file_audio = 0xf1c7
    file_code = 0xf1c9
    file_image = 0xf1c5
    file_movie = 0xf1c8
    file = 0xf016
    file_text = 0xf15c
    file_text = 0xf0f6
    file_video = 0xf1c8
    file_zip = 0xf1c6
    copy2 = 0xf0c5
    film = 0xf008
    filter = 0xf0b0
    fire = 0xf06d
    flag = 0xf024
    flag_checkered = 0xf11e
    flag_o = 0xf11d
    flash = 0xf0e7
    flask = 0xf0c3
    floppy = 0xf0c7
    folder = 0xf07b
    folder_open = 0xf07c
    font = 0xf031
    forward = 0xf04e
    gear = 0xf013
    gears = 0xf085
    get_pocket = 0xf265
    glass = 0xf000
    globe = 0xf0ac
    graduation_cap = 0xf19d
    hashtag = 0xf292
    hdd = 0xf0a0
    header = 0xf1dc
    history = 0xf1da
    home = 0xf015
    hourglass = 0xf254
    hourglass_end = 0xf253
    hourglass_half = 0xf252
    hourglass_start = 0xf251
    i_cursor = 0xf246
    image = 0xf03e
    inbox = 0xf01c
    indent = 0xf03c
    info = 0xf129
    info_circle = 0xf05a
    italic = 0xf033
    key = 0xf084
    keyboard = 0xf11c
    laptop = 0xf109
    leaf = 0xf06c
    level_down = 0xf149
    level_up = 0xf148
    support = 0xf1cd
    lightbulb_o = 0xf0eb
    line_chart = 0xf201
    link = 0xf0c1
    list = 0xf03a
    list_alt = 0xf022
    list_ol = 0xf0cb
    list_ul = 0xf0ca
    location_arrow = 0xf124
    lock = 0xf023
    long_arrow_down = 0xf175
    long_arrow_left = 0xf177
    long_arrow_right = 0xf178
    long_arrow_up = 0xf176
    magic = 0xf0d0
    magnet = 0xf076
    map_pin = 0xf276
    microphone = 0xf130
    microphone_slash = 0xf131
    minus = 0xf068
    minus_circle = 0xf056
    minus_square = 0xf146
    moon = 0xf186
    mouse_pointer = 0xf245
    music = 0xf001
    navicon = 0xf0c9
    newspaper_o = 0xf1ea
    object_group = 0xf247
    object_ungroup = 0xf248
    paint_brush = 0xf1fc
    paper_plane = 0xf1d8
    paperclip = 0xf0c6
    paragraph = 0xf1dd
    pause = 0xf04c
    pause_circle = 0xf28b
    pencil = 0xf040
    pencil_square = 0xf044
    percent = 0xf295
    pie_chart = 0xf200
    play = 0xf04b
    play_circle = 0xf144
    play_circle_o = 0xf01d
    plug = 0xf1e6
    plus = 0xf067
    plus_circle = 0xf055
    plus_square = 0xf0fe
    plus_square_o = 0xf196
    podcast = 0xf2ce
    power_off = 0xf011
    print = 0xf02f
    puzzle_piece = 0xf12e
    question = 0xf128
    question_circle = 0xf059
    quote_left = 0xf10d
    quote_right = 0xf10e
    random = 0xf074
    recycle = 0xf1b82
    refresh = 0xf021
    repeat = 0xf01e
    road = 0xf018
    rocket = 0xf135
    rotate_left = 0xf0e2
    rotate_right = 0xf01e
    waves = 0xf09e
    save = 0xf0c7
    search = 0xf002
    search_minus = 0xf010
    search_plus = 0xf00e
    shield = 0xf132
    signal_bars = 0xf012
    sliders = 0xf1de
    snowflake = 0xf2dc
    sort = 0xf0dc
    spinner = 0xf110
    square = 0xf0c8
    step_backward = 0xf048
    step_forward = 0xf051
    sticky_note = 0xf249
    stop = 0xf04d
    stop_circle = 0xf28d
    table = 0xf0ce
    tag = 0xf02b
    tags = 0xf02c
    grid = 0xf00a
    grid_large = 0xf009
    grid_list = 0xf00b
    thermometer_three_quarters = 0xf2c8
    thumb_tack = 0xf08d
    x_circle = 0xf057
    tint = 0xf043
    toggle_off = 0xf204
    toggle_on = 0xf205
    trash = 0xf1f8
    tree = 0xf1bb
    trophy = 0xf091
    umbrella = 0xf0e9
    underline = 0xf0cd
    undo = 0xf0e2
    university = 0xf19c
    unlink = 0xf127
    unlock = 0xf09c
    unlock_alt = 0xf13e
    video_camera = 0xf03d
    volume_down = 0xf027
    volume_off = 0xf026
    volume_up = 0xf028
    window_close = 0xf2d3
    window_maximize = 0xf2d0
    window_minimize = 0xf2d1
    window_restore = 0xf2d2
    wrench = 0xf0ad
    person_running = 0xf70c

    _fonts_path = ""

    def __new__(cls, font_reg=None):  # Make class a Singleton.
        if cls._instance is None:
            cls._instance = super(Icons, cls).__new__(cls)
        return cls._instance

    def __init__(self, font_reg=None):
        if not self._is_initialized:
            self._fa = {}
            self._fs = {}
            self._color_themes = {}
            if font_reg:
                self.set_font_registry(font_reg)
            self._is_initialized = True

    def set_font_registry(self, font_reg, fonts_path):
        self._font_reg = font_reg
        self._fonts_path = fonts_path
        return self

    def get_icon(self, icon, size, solid=True):  # icon: unicode hex code (e.g. 0xf07c)
        """add icon hex to loaded special characters if necessary; then return string."""

        if type(icon) == int:
            if self._font_reg is None:
                print("Icons: Could not register font, I don't have the registry yet!")
                return ""
            if (not solid) and (size not in self._fa.keys()):
                with dpg.font(os.path.join(self._fonts_path, "Font Awesome 6 Free-Regular-400.otf"), size, parent=self._font_reg) as self._fa[size]:
                    dpg.add_font_range(0xf000, 0xf999)
                # self._registered_fa[size] = []
            elif solid and (size not in self._fs.keys()):
                with dpg.font(os.path.join(self._fonts_path, "Font Awesome 6 Free-Solid-900.otf"), size, parent=self._font_reg) as self._fs[size]:
                    dpg.add_font_range(0xf000, 0xf999)
            return chr(icon)
        else:
            return ""

    def insert(self, dpg_item, icon, size, solid=True, color=None, tooltip=None):
        """Inserts icon character as label of dpg_item."""
        if color is not None:
            if not tuple(color) in self._color_themes.keys():
                with dpg.theme() as self._color_themes[tuple(color)]:
                    with dpg.theme_component(dpg.mvButton):
                        dpg.add_theme_color(dpg.mvThemeCol_Text, color)
            dpg.bind_item_theme(dpg_item, self._color_themes[tuple(color)])

        if type(icon) == list:  # multiple icons above each other
            label_list = []
            for i in icon:
                label_list.append(self.get_icon(i, size, solid))
            label = '\n'.join(label_list)
        else:
            label = self.get_icon(icon, size, solid)
        dpg.configure_item(dpg_item, label=label)  # automatically ensures that font is registered

        if solid:
            dpg.bind_item_font(dpg_item, self._fs[size])
        else:
            dpg.bind_item_font(dpg_item, self._fa[size])
        if tooltip:
            if dpg.does_item_exist(f"{dpg_item} tooltip"):
                dpg.delete_item(f"{dpg_item} tooltip")
            with dpg.tooltip(parent=dpg_item, tag=f"{dpg_item} tooltip", delay=0.3):
                dpg.add_text(f" {tooltip} ")
        return dpg_item


