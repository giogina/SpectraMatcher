import os
import time

from utility.icons import Icons
import dearpygui.dearpygui as dpg


class FontManager:

    fonts = {}
    normal_font = 18
    big_font = 22
    font_registry = None

    @classmethod
    def find_fonts_path(cls):
        base_path = os.path.dirname(os.path.abspath(__file__))
        while True:
            fonts_path = os.path.join(base_path, "fonts")
            if os.path.isdir(fonts_path):  # Check if 'fonts' directory exists
                return fonts_path
            new_base = os.path.dirname(base_path)  # Move up one directory
            if new_base == base_path:  # If we reach the root directory, stop
                print("Error: The 'fonts' directory was not found in any parent directories.")
            base_path = new_base

    @classmethod
    def load_fonts(cls):
        fonts_path = cls.find_fonts_path()
        with open("C:/Users/Giogina/SpectraMatcher/launch.log", 'a') as launch_log:  # TODO: temp
            launch_log.write(f"fonts_path: {fonts_path}\n")
        with dpg.font_registry() as cls.font_registry:
            # ! Open/Closed folder icons have been added to this font !
            # Don't change it, or you will get currency signs instead. (Or add folder icons as \u00a3 and \u00a4)
            # self.fonts[self.normal_font] = dpg.add_font("./fonts/SansationRegular.ttf", self.normal_font)
            with dpg.font(os.path.join(fonts_path, "SansationRegular.ttf"), cls.normal_font) as cls.fonts[cls.normal_font]:
                dpg.add_font_range(0x2070, 0x20b0, parent=cls.fonts[cls.normal_font])
                dpg.add_font_chars([0x0394, 0x2264, 0x2265])
            with dpg.font(os.path.join(fonts_path, "SansationRegular.ttf"), cls.big_font) as cls.fonts[cls.big_font]:
                dpg.add_font_range(0x2070, 0x20b0, parent=cls.fonts[cls.big_font])
                dpg.add_font_chars([0x0394, 0x2264, 0x2265])
            for i in range(12, 25):
                cls.get(i)
            Icons().set_font_registry(cls.font_registry, fonts_path)

        dpg.bind_font(cls.fonts[cls.normal_font])

    @classmethod
    def get(cls, size):
        if cls.font_registry is None:
            return
        if size not in cls.fonts.keys():
            with dpg.font(os.path.join(cls.find_fonts_path(), "SansationRegular.ttf"), size, parent=cls.font_registry) as cls.fonts[size]:
                dpg.add_font_range(0x2070, 0x20b0)
                dpg.add_font_chars([0x0394, 0x2264, 0x2265])
        return cls.fonts[size]

    # self._load_fonts_async()  # Still needed or throw out? Or dynamically load fonts using font_reg?
    # def _load_fonts_async(self):
    #     fonts_thread = threading.Thread(target=self._load_fonts)
    #     fonts_thread.daemon = True
    #     fonts_thread.start()
    #
    # def _load_fonts(self):
    #     with dpg.font_registry():
    #         for i in range(5, 33):
    #             if not i in self.fonts.keys():
    #                 self.fonts[i] = dpg.add_font("./fonts/Sansation_Regular.ttf", i)
