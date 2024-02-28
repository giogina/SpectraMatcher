from utility.icons import Icons
import dearpygui.dearpygui as dpg

class FontManager:

    fonts = {}
    normal_font = 18
    big_font = 22
    font_registry = None

    @classmethod
    def load_fonts(cls):
        with dpg.font_registry() as cls.font_registry:
            # ! Open/Closed folder icons have been added to this font !
            # Don't change it, or you will get currency signs instead. (Or add folder icons as \u00a3 and \u00a4)
            # self.fonts[self.normal_font] = dpg.add_font("./fonts/SansationRegular.ttf", self.normal_font)
            with dpg.font("./fonts/SansationRegular.ttf", cls.normal_font) as cls.fonts[cls.normal_font]:
                dpg.add_font_range(0x2070, 0x2090, parent=cls.fonts[cls.normal_font])
                dpg.add_font_chars([0x0394])
            with dpg.font("./fonts/SansationRegular.ttf", cls.big_font) as cls.fonts[cls.big_font]:
                dpg.add_font_range(0x2070, 0x2090, parent=cls.fonts[cls.big_font])  # todo: Find larger symbols for these
                dpg.add_font_chars([0x0394])
            Icons().set_font_registry(cls.font_registry)

        dpg.bind_font(cls.fonts[cls.normal_font])

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
