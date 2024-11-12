import logging
import sys
from utility.gui_log_handler import GuiLogHandler
from launcher import Launcher
from views.main_window import MainWindow
from views.startup_dashboard import Dashboard
from views.create_project import CreateProjectWindow
# -m nuitka --assume-yes-for-downloads --standalone --follow-imports --include-data-dir=C:/Users/Giogina/SpectraMatcher/fonts=fonts  --include-data-dir=C:/Users/Giogina/SpectraMatcher/resources=resources --windows-icon-from-ico=C:/Users/Giogina/SpectraMatcher/resources/SpectraMatcher.ico --enable-plugin=tk-inter --windows-disable-console --output-filename=SpectraMatcher.exe $FilePath$


def main():
    # # regularly remove the logger; or just turn it all off?
    # logging.basicConfig(level=logging.INFO, filename='spectraMatcher.log',
    #                     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # gui_handler = GuiLogHandler()  # to do: Pass GUI element to display logs?
    # logging.getLogger().addHandler(gui_handler)
    # logging.info(f"Started with flags: {sys.argv}")

    flags = None
    if len(sys.argv) > 1:
        if sys.argv[1] == "-open" and len(sys.argv) > 2:
            MainWindow(sys.argv[2].replace("\\", "/")).show()
        elif sys.argv[1] == "-new":
            if len(sys.argv) > 2:
                flags = CreateProjectWindow(sys.argv[2:len(sys.argv)]).show()
            else:
                flags = CreateProjectWindow().show()
        else:
            return
    else:
        flags = Dashboard().show()

    if flags:  # Restart this program with proper flags.
        Launcher.launch(*flags)


if __name__ == "__main__":
    main()

    # Installation wizard:
    #   To make dearpygui work on win7: Make sure # https://learn.microsoft.com/en-GB/cpp/windows/latest-supported-vc-redist?view=msvc-170
    #   is installed, and include IEShims.dll and d3dcompiler_47.dll (currently present in C:\Users\Giogina\SpectraMatcher\venv_win\Lib\site-packages\dearpygui).
    #   (The VC .dlls are automatically included in Nuitka; the other two dlls are added by inno setup.)
