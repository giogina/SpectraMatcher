import math
import random

import dearpygui.dearpygui as dpg
from models.settings_manager import SettingsManager
from utility.async_manager import AsyncManager
from utility.icons import Icons
from utility.spectrum_plots import SpecPlotter
from utility.system_file_browser import *
from screeninfo import get_monitors
import numpy as np
from pathlib import Path
import threading


class Peak:
    def __init__(self, wavenumber, transition, intensity):
        self.wavenumber = wavenumber
        self.corrected_wavenumber = wavenumber
        self.transition = transition
        self.intensity = intensity


class Dashboard:
    def __init__(self):
        self.result = None
        self.settings = SettingsManager()
        self.recent = self.settings.get("recentProjects")
        self.selected_recent_item = -1

        monitor = get_monitors()[0]
        dpg.create_context()
        dpg.configure_app(auto_device=True)
        self.file_list_item_theme, self.file_list_item_hovered_theme, close_button_theme = self.adjust_theme()

        self.fonts = {}
        self.small_font = 13
        self.normal_font = 18
        self.title_font = 33
        with dpg.font_registry() as font_reg:
            for i in [self.small_font, self.normal_font, self.title_font]:
                self.fonts[i] = dpg.add_font("./fonts/Sansation_Regular.ttf", i)
        self.icons = Icons(font_reg)
        dpg.bind_font(self.fonts[self.normal_font])

        with dpg.handler_registry() as self.keyReg:
            dpg.add_key_press_handler(dpg.mvKey_Escape, callback=self.on_escape)
            dpg.add_key_press_handler(dpg.mvKey_Down, callback=self.on_down)
            dpg.add_key_press_handler(dpg.mvKey_Up, callback=self.on_up)
            dpg.add_key_press_handler(dpg.mvKey_Return, callback=self.on_enter)
            dpg.add_mouse_move_handler(callback=self.on_recent_hover)
            dpg.add_mouse_click_handler(callback=self.on_recent_click)

        AsyncManager.start()

        Phi = 1.618033
        dash_width = 800
        dash_height = int(dash_width/Phi)
        self.wavy_width = int(dash_width/2)
        self.wavy_height = int(dash_height-1)
        self.spec_plotter = SpecPlotter(20, 0, self.wavy_width)
        self.thickness = 4
        self.exp_peaks = [[0.25*self.wavy_width, 0.3], [0.4*self.wavy_width, 0.7], [0.7*self.wavy_width, 0.4]]
        self.wobbles = self.determine_wobble_parameters([
             # {"center": (0.4*self.wavy_width, 0.4), "speed": 2, "aspect_ratio": 1},
             # {"center": (0.3 * self.wavy_width, 0.45), "speed": 1, "aspect_ratio": 0.8},
             # {"center": (0.9 * self.wavy_width, 0.3), "speed": 3, "aspect_ratio": 0.6},
             # {"center": (0.5 * self.wavy_width, 0.1), "speed": 1, "aspect_ratio": 0.3},
             # {"center": (0.7 * self.wavy_width, 0.2), "speed": 1, "aspect_ratio": 0.8},
             # {"center": (0.5 * self.wavy_width, 0.5), "speed": 1, "aspect_ratio": 0.2},
             {"center": (0.4*self.wavy_width, 0.4), "speed": random.choice(range(1, 3)), "aspect_ratio": 0.2+random.random()*0.6},
             {"center": (0.3 * self.wavy_width, 0.45), "speed": random.choice(range(1, 3)), "aspect_ratio": 0.2+random.random()*0.6},
             {"center": (0.9 * self.wavy_width, 0.3), "speed": random.choice(range(1, 3)), "aspect_ratio": 0.2+random.random()*0.6},
             {"center": (0.5 * self.wavy_width, 0.1), "speed": random.choice(range(1, 3)), "aspect_ratio": 0.2+random.random()*0.6},
             {"center": (0.7 * self.wavy_width, 0.2), "speed": random.choice(range(1, 3)), "aspect_ratio": 0.5+random.random()/2},
             {"center": (0.5 * self.wavy_width, 0.15), "speed": random.choice(range(1, 3)), "aspect_ratio": 0.5+random.random()/2},
             ])
        # print([w["speed"] for w in self.wobbles])
        # print([w["aspect_ratio"] for w in self.wobbles])
        # self.exp_peaks = [[-0.3*self.wavy_width, 0.3]]
        self.phase = 90
        self.pixel_intensity_stamps = self.precompute_pixel_intensities()
        self.shadow = np.zeros((self.wavy_height, self.wavy_width, 4))
        self.last_texture = np.zeros((self.wavy_height, self.wavy_width, 4))
        self.frames_per_degree = 2
        self.texture_buffer = np.zeros((self.frames_per_degree*360, self.wavy_height, self.wavy_width, 4), dtype=np.uint8)
        self.texture_buffer_pointer = 0
        self.startup_indicator = -self.frames_per_degree*360
        self.init_textures()

        dpg.create_viewport(title='SpectraMatcher', width=dash_width, height=dash_height,
                            x_pos=int(monitor.width/2-dash_width/2), y_pos=int(monitor.height/2-dash_height/2))
        dpg.set_viewport_decorated(False)
        with dpg.window(label="Dashboard", width=dash_width, height=dash_height, tag="dash"):
            with dpg.group(horizontal=True):

                with dpg.child_window(width=self.wavy_width, height=-1, tag="wavy"):
                    with dpg.drawlist(width=self.wavy_width, height=self.wavy_height):
                        dpg.draw_image("shadow_texture", (0, 0), (self.wavy_width, self.wavy_height))
                        dpg.draw_image("comp_texture", (0, 0), (self.wavy_width, self.wavy_height))
                        dpg.draw_image("exp_texture", (0, 0), (self.wavy_width, self.wavy_height))

                with dpg.child_window(width=dash_width - self.wavy_width, height=-1):
                    # dpg.add_button(label="x", pos=[self.wavy_width-53, 3], width=30, tag="close-button", callback=self.on_escape)

                    self.icons.insert(dpg.add_button(pos=[self.wavy_width-53, 3], width=30, height=30, tag="close-button", callback=self.on_escape), icon=Icons.x, size=16)
                    dpg.bind_item_theme("close-button", close_button_theme)
                    dpg.add_spacer(height=20)
                    with dpg.group(horizontal=True):
                        dpg.add_spacer(width=56)
                        title_text = dpg.add_text("SpectraMatcher", color=[150, 150, 255])
                    dpg.bind_item_font(title_text, self.fonts[self.title_font])
                    dpg.add_spacer(height=16)
                    with dpg.group(horizontal=True):
                        dpg.add_spacer(width=10)
                        dpg.add_button(label="New Project...", width=300, callback=self.create_new_project, tag="new project button")
                    dpg.add_spacer(height=16)
                    with dpg.group(horizontal=True):
                        dpg.add_spacer(width=10)
                        dpg.add_button(label="Open Project...", width=300, callback=self.open_project, tag="open button")
                    dpg.add_spacer(height=16)

                    # List of recent projects
                    with dpg.child_window(height=-1):
                        with dpg.group(horizontal=True):
                            dpg.add_spacer(width=10)
                            dpg.add_text("Open recent project:", color=[200, 200, 255])
                        with dpg.group(horizontal=True):
                            dpg.add_spacer(width=10)
                            with dpg.child_window(label="file_list", width=300, height=4*53, no_scrollbar=True, tag="file list") as file_list_frame:
                                self.file_item = {}
                                for i, file_path in enumerate(self.recent):
                                     # os.path.basename(file_path)
                                    file_name = Path(file_path).stem
                                    with dpg.child_window(width=-1, height=50, no_scrollbar=True, tag=f"list item {i}") as self.file_item[i]:
                                        dpg.add_spacer(label="file_item_top", height=4)
                                        with dpg.group(horizontal=True):
                                            dpg.add_spacer(label="pre1", width=16)
                                            dpg.add_text(file_name, color=[220, 220, 255])
                                        with dpg.group(horizontal=True):
                                            dpg.add_spacer(label="pre2", width=16)
                                            path_line = dpg.add_text(file_path, color=[140, 140, 255])
                                            dpg.bind_item_font(path_line, self.fonts[self.small_font])
                                    dpg.bind_item_theme(f"list item {i}", self.file_list_item_theme)
                                    # dpg.bind_item_handler_registry(f"list item {i}", "list item handler")
                            # dpg.bind_item_theme(file_list_frame, file_list_theme)

        dpg.set_primary_window("dash", True)

    def init_textures(self):
        with dpg.texture_registry(show=False):
            dpg.add_static_texture(width=self.wavy_width, height=self.wavy_height,
                                   default_value=self.static_peaks_array(), tag="exp_texture")
            dpg.add_dynamic_texture(width=self.wavy_width, height=self.wavy_height,
                                    default_value=self.empty_texture(), tag="shadow_texture")
            dpg.add_dynamic_texture(width=self.wavy_width, height=self.wavy_height,
                                    default_value=self.empty_texture(), tag="comp_texture")
        self.precompute_dynamic_textures_async()

    def precompute_dynamic_textures_async(self):
        phase = 0
        while phase < 360:
            AsyncManager.submit_task(f"texture pre compute {phase}", self.precompute_dynamic_texture, phase)
            phase += 1./self.frames_per_degree

    def precompute_dynamic_texture(self, phase):
        color = [(math.cos((-phase - 120) * math.pi / 180) + 1) / 2 * 255,
                 (math.cos(-phase * math.pi / 180) + 1) / 2 * 255,
                 (math.cos((-phase + 120) * math.pi / 180) + 1) / 2 * 255,
                 200]
        color = np.array(color).astype(np.uint8)
        peaks = self.get_comp_peaks(phase)
        self.texture_buffer[self.get_texture_index(phase), :, :, :] = self.construct_spectrum_texture(color, peaks).astype(dtype=np.uint8)

        self.startup_indicator += 1
        if self.startup_indicator >= 0:
            self.startup_indicator = 90
        # print(self.startup_indicator)

    def _update_dynamic_textures(self):
        if self.startup_indicator < 0:
            return
        if self.phase > 350:
            self.shadow[:, :, :] *= 0.9
        if self.phase == 0:
            self.shadow = np.zeros((self.wavy_height, self.wavy_width, 4))
        self.shadow[:, :, :] *= 0.98
        new_texture_data = self.texture_buffer[self.get_texture_index(self.phase), :, :, :] / 255.
        if math.isclose(self.phase % 1, 0, abs_tol=1e-9):
            self.shadow = np.maximum(0.6 * new_texture_data, self.shadow)
        new_shadow = self.shadow
        if self.startup_indicator > 0:
            self.startup_indicator -= 0.5/self.frames_per_degree
            new_texture_data *= (1. - self.startup_indicator/90)**0.5
            new_shadow *= (1. - self.startup_indicator/90)**0.5
        dpg.set_value("shadow_texture", new_shadow)
        dpg.set_value("comp_texture", new_texture_data)

    def get_texture_index(self, phase):
        return int(self.frames_per_degree*(phase % 360))

    def empty_texture(self):
        return np.zeros((self.wavy_height, self.wavy_width, 4))

    def static_peaks_array(self):
        """Compute numpy array for displaying a static "experimental" spectrum"""
        color = [140, 180, 255, 255]
        return self.construct_spectrum_texture(color, self.exp_peaks) / 255.

    def determine_wobble_parameters(self, wobble_list):
        res = []
        for i, wobble in enumerate(wobble_list):
            # {"center": (0.1 * self.wavy_width, 0.4), "speed": 2, "aspect_ratio": 1}
            aspect_ratio = wobble["aspect_ratio"] / self.wavy_width

            if i < len(self.exp_peaks):
                a = self.exp_peaks[i][0] - wobble["center"][0]
                b = self.exp_peaks[i][1] - wobble["center"][1]
                wobble["phi"] = math.atan(b/a/aspect_ratio) / wobble["speed"]
                wobble["rx"] = a / math.cos(wobble["phi"] * wobble["speed"])
                wobble["ry"] = aspect_ratio*wobble["rx"]
            else:
                wobble["ry"] = wobble["center"][1]
                wobble["rx"] = wobble["ry"] / aspect_ratio
                wobble["phi"] = 3/2*math.pi / wobble["speed"]

            res.append(wobble)
            # print(wobble)
        return res

    # wobble["rx"]*math.cos((wobble["phi"] * math.pi/180)*wobble["speed"])  =! peak_x_center - wobble["center"][0]

    def get_comp_peaks(self, phase):
        res = []
        for i, wobble in enumerate(self.wobbles):
            res.append([wobble["rx"]*math.cos((wobble["phi"]+phase * math.pi/180)*wobble["speed"]) + wobble["center"][0],
                        wobble["ry"]*math.sin((wobble["phi"]+phase * math.pi/180)*wobble["speed"]) + wobble["center"][1]])
        return res

    def construct_spectrum_texture(self, color, peaks):
        texture_data = np.zeros((self.wavy_height, self.wavy_width, 4))
        fc_peaks = [Peak(peak[0], "", peak[1]) for peak in peaks]
        spec = self.spec_plotter.spectrum_array(fc_peaks)*self.wavy_height  # np array with x: index, y: value (float)
        for x in range(1, self.wavy_width-1):
            texture_data = self.draw_slice(texture_data, x, self.wavy_height - spec[x],
                                           self.wavy_height - spec[x-1], self.wavy_height - spec[x+1], color)
        return texture_data

    def draw_slice(self, texture, x, y, y0, y1, color):  # todo: anti-aliasing still wonky
        y_int = int(math.floor(y+0.5))
        y_shift = int(round((y-y_int)*10))
        y_shift_exact = y-y_int
        slope0 = y-y0  # delta x is always 1
        slope1 = y1-y

        if slope0*slope1 > 0:
            if slope0 > 0:  # going up; Bottom half from slope0, Top half from slope1
                bottom_slope = slope0
                top_slope = slope1
            else:  # going down; other way around.
                bottom_slope = slope1
                top_slope = slope0
        else:
            if slope0 > 0:  # local maximum
                top_slope = (y1-y0)/2  # average slope
                bottom_slope = max(slope0, slope1)
            else:  # local minimum
                bottom_slope = (y1-y0)/2
                top_slope = min(slope0, slope1)

        # stamp_bottom = self.lookup_stamp(bottom_slope, y_shift, bottom=True)
        # stamp_top = self.lookup_stamp(top_slope, y_shift)
        # stamp_bottom[-1] = stamp_bottom[-1] + stamp_top[0] - 1  # in case two corners are missing from middle pixel
        # stamp = np.concatenate((stamp_bottom, stamp_top[1:]))
        # start_index = -stamp_bottom.size+1
        stamp, start_index = self.assemble_stamp(top_slope, bottom_slope, y_shift_exact)

        start = y_int + start_index - 10
        stop = y_int + start_index + stamp.size - 10

        if stop < 1 or start > texture.shape[0]-1:
            return texture

        clip_start = max(-start, 0)
        clip_stop = max(stop - texture.shape[0], 0)

        texture[start + clip_start:stop-clip_stop, x, 0] = color[0]
        texture[start + clip_start:stop-clip_stop, x, 1] = color[1]
        texture[start + clip_start:stop-clip_stop, x, 2] = color[2]
        texture[start + clip_start:stop-clip_stop, x, 3] = stamp[clip_start:stamp.size-clip_stop]*color[3]
        return texture

    def assemble_stamp(self, top_slope, bottom_slope, exact_y_shift):
        y_shift = math.floor(exact_y_shift*10)
        y_shift_tail = exact_y_shift*10 - y_shift  # inflated by factor 10, so in (0,1)

        stamp_bottom_1 = self.lookup_stamp(bottom_slope, y_shift, bottom=True)
        if y_shift < 5:
            stamp_bottom_2 = self.lookup_stamp(bottom_slope, y_shift+1, bottom=True)
            stamp_bottom = np.zeros(max(stamp_bottom_1.size, stamp_bottom_2.size))
            stamp_bottom[stamp_bottom.size - stamp_bottom_1.size:stamp_bottom.size] = stamp_bottom_1*(1-y_shift_tail)
            stamp_bottom[stamp_bottom.size - stamp_bottom_2.size:stamp_bottom.size] += stamp_bottom_2*y_shift_tail
        else:
            stamp_bottom = stamp_bottom_1
        stamp_top_1 = self.lookup_stamp(top_slope, y_shift)
        if y_shift < 5:
            stamp_top_2 = self.lookup_stamp(top_slope, y_shift+1)
            stamp_top = np.zeros(max(stamp_top_1.size, stamp_top_2.size))
            stamp_top[0:stamp_top_1.size] = stamp_top_1*(1-y_shift_tail)
            stamp_top[0:stamp_top_2.size] += stamp_top_2*y_shift_tail
        else:
            stamp_top = stamp_top_1

        stamp_bottom[-1] = stamp_bottom[-1] + stamp_top[0] - 1  # in case two corners are missing from middle pixel
        stamp = np.concatenate((stamp_bottom, stamp_top[1:]))
        start_index = -stamp_bottom.size + 1
        return stamp, start_index

    def lookup_stamp(self, slope, y_shift, bottom=False):
        """Returns top or bottom half of the pixel slice of the graph."""
        alpha = min(89, int(round(180/math.pi*math.atan(math.fabs(slope)))))
        y_shift = min(max(-5, int(y_shift)), 5)

        if not bottom:
            stamp = self.pixel_intensity_stamps[alpha][y_shift]
        else:
            stamp = self.pixel_intensity_stamps[alpha][-y_shift]
            stamp = stamp[::-1]
        return stamp

    def area_above_crossing_line(self, crossings, slope):
        areas = [crossings[0] ** 2 * slope / 2]  # lowest pixel, contributing only a corner
        for i in range(1, len(crossings)):  # in between pixels, contributing a trapezoid
            areas.append((crossings[i] + crossings[i - 1]) / 2)
        areas.append(1 - (1 - crossings[-1]) ** 2 * slope / 2)  # highest partial pixel
        return areas

    def compute_pixel_intensities(self, alpha_deg, center_pos):
        # Center_pos: -5 to 5; understood as center_pos/10 above the pixel middle. Reverse array for below.
        alpha = math.fabs(alpha_deg * math.pi / 180)  # In radians; sign doesn't matter, assume positive slope.
        slope = math.tan(alpha)

        # special case of line edges falling exactly between pixels (which makes below computations a bit sketchy)
        if alpha_deg == 0 and center_pos == 0 and self.thickness % 2 == 1:
            return np.array([1. for x in range(round((self.thickness+1) / 2))])
        if alpha_deg == 0 and center_pos == 5 and self.thickness % 2 == 0:
            return np.array([1. for x in range(round(self.thickness / 2)+1)])
        if alpha_deg == 0 and center_pos == -5 and self.thickness % 2 == 0:
            return np.array([1. for x in range(round(self.thickness / 2))])

        center_y = center_pos / 10
        adjusted_thickness = self.thickness / math.cos(alpha)
        entry_y_above = center_y - slope * 0.5 + adjusted_thickness / 2
        exit_y_above = center_y + slope * 0.5 + adjusted_thickness / 2

        crossings_above = []
        intensities = []

        for i in range(0, math.floor(entry_y_above + 0.5)):  # fully filled middle pixels
            intensities.append(1)

        yy = math.ceil(entry_y_above + 0.5) - 0.5
        while yy < exit_y_above:
            crossings_above.append((yy - entry_y_above) / slope)
            yy += 1
        if crossings_above:
            intensities += [1 - a for a in self.area_above_crossing_line(crossings_above, slope)]
        else:
            top_middle_y = center_y + adjusted_thickness / 2
            intensities.append(1 - math.ceil(top_middle_y + 0.5) + (top_middle_y + 0.5))

        return np.array(intensities)

    def precompute_pixel_intensities(self):
        precomputed_intensities = {}
        for a in range(0, 90):
            alpha_ints = {}
            for shift in range(-5, 6):
                alpha_ints[shift] = self.compute_pixel_intensities(a, shift)
            precomputed_intensities[a] = alpha_ints
            # print(a, alpha_ints[0])
        return precomputed_intensities

    def adjust_theme(self, *args):
        with dpg.theme() as global_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4)
                dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 4)
                dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 0)
                dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0)
                dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 0)
                dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 0, 0)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 12, 12)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 20, 0)
                dpg.add_theme_color(dpg.mvThemeCol_WindowBg, [11, 11, 36])
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, [11, 11, 36])
                dpg.add_theme_color(dpg.mvThemeCol_TitleBg, [11, 11, 36])
                dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, [11, 11, 36])
                dpg.add_theme_color(dpg.mvThemeCol_TitleBgCollapsed, [11, 11, 36])
                dpg.add_theme_color(dpg.mvThemeCol_Button, [60, 60, 154])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [131, 131, 255])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [70, 70, 255])
                dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg, [22, 22, 72])
                dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab, [60, 60, 154])
                dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabActive, [60, 60, 154])
                dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabHovered, [60, 60, 154])

        dpg.bind_theme(global_theme)

        with dpg.theme() as file_list_item_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 4)
                dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 0)
                dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0)
                dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 0)
                dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 20, 0)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 15, 0)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 0, 3)
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, [95, 95, 188, 88])

        with dpg.theme() as file_list_item_hovered_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 4)
                dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 0)
                dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0)
                dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 0)
                dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 20, 0)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 15, 0)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 0, 3)
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, [131, 131, 255, 100])
                # dpg.add_theme_color(dpg.mvThemeCol_ChildBg, [50, 50, 150, 100])

        with dpg.theme() as close_button_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Button, [60, 60, 154, 0])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [60, 60, 154])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [60, 60, 154])
                dpg.add_theme_color(dpg.mvThemeCol_Text, [131, 131, 255, 160])
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 5, 5)

        return file_list_item_theme, file_list_item_hovered_theme, close_button_theme

    def on_escape(self, *args):
        self.result = None
        dpg.delete_item("dash")
        dpg.stop_dearpygui()

    def show(self):
        dpg.setup_dearpygui()
        dpg.set_viewport_small_icon("resources/SpectraMatcher.ico")
        dpg.set_viewport_large_icon("resources/SpectraMatcher.ico")
        dpg.show_viewport()
        # dpg.start_dearpygui()
        while dpg.is_dearpygui_running():
            if self.startup_indicator >= 0:
                self.phase = (self.phase + 1./self.frames_per_degree) % 360
                # if self.phase > 350 or self.phase < 10:
                #     self.phase = (self.phase + 0.5) % 360
                # else:
                #     self.phase = (self.phase + 1) % 360
                # print(self.phase)
                self._update_dynamic_textures()
            dpg.render_dearpygui_frame()
        AsyncManager.shutdown()
        dpg.destroy_context()
        return self.result

    def open_project(self, *args):
        # Logic to open a project
        project_path = open_project_file_dialog(self.settings.get("projectsPath", "/"))
        if project_path:
            self.result = ('-open', project_path)
            dpg.stop_dearpygui()

    def create_new_project(self, *args):
        self.result = ("-new", )
        dpg.stop_dearpygui()

    def on_recent_click(self, *args):
        for i, item in enumerate(self.file_item):
            if dpg.is_item_hovered(f"list item {i}"):
                self.result = ('-open', self.recent[i])
                dpg.stop_dearpygui()

    def on_recent_hover(self, *args):
        for i, item in enumerate(self.file_item):
            item_tag = f"list item {i}"
            if dpg.is_item_hovered(item_tag):
                dpg.bind_item_theme(item_tag, self.file_list_item_hovered_theme)
            else:
                dpg.bind_item_theme(item_tag, self.file_list_item_theme)

    def mark_selected_recent_item(self, *args):
        for i, item in enumerate(self.file_item):
            item_tag = f"list item {i}"
            if i == self.selected_recent_item:
                dpg.bind_item_theme(item_tag, self.file_list_item_hovered_theme)
                if (i+1)*53 > dpg.get_item_height("file list") + dpg.get_y_scroll("file list"):
                    dpg.set_y_scroll("file list", (i-3)*53)
                elif i*53 < dpg.get_y_scroll("file list"):
                    dpg.set_y_scroll("file list", i*53)
                print(dpg.get_y_scroll("file list"))
            else:
                dpg.bind_item_theme(item_tag, self.file_list_item_theme)

    def on_down(self, *args):
        if self.recent:
            self.selected_recent_item = (self.selected_recent_item + 1) % len(self.recent)
            self.mark_selected_recent_item()

    def on_up(self, *args):
        if self.recent:
            if self.selected_recent_item == -1:
                self.selected_recent_item = 0
            self.selected_recent_item = (self.selected_recent_item - 1) % len(self.recent)
            self.mark_selected_recent_item()

    def on_enter(self, *args):
        if self.selected_recent_item in range(len(self.recent)):
            self.result = ('-open', self.recent[self.selected_recent_item])
            dpg.stop_dearpygui()

    def __del__(self):
        # Cleanup
        dpg.destroy_context()
