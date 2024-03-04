import logging
import sys
from utility.gui_log_handler import GuiLogHandler
from launcher import Launcher
from views.main_window import MainWindow
from views.startup_dashboard import Dashboard
from views.create_project import CreateProjectWindow


def main():
    logging.basicConfig(level=logging.INFO, filename='spectraMatcher.log',
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    gui_handler = GuiLogHandler()  # TODO: Pass GUI element to display logs.
    logging.getLogger().addHandler(gui_handler)
    logging.info(f"Started with flags: {sys.argv}")

    flags = None
    if len(sys.argv) > 1:
        if sys.argv[1] == "-open" and len(sys.argv) > 2:
            MainWindow(sys.argv[2]).show()
        elif sys.argv[1] == "-new":
            if len(sys.argv) > 2:
                flags = CreateProjectWindow(sys.argv[2:len(sys.argv)]).show()
            else:
                flags = CreateProjectWindow().show()
        else:
            return
    else:
        flags = Dashboard().show()

    logging.info(f"Flags received:{flags}")

    if flags:  # Restart this program with proper flags.
        Launcher.launch(*flags)

if __name__ == "__main__":
    main()

    # TODO: Installation wizard: Set path for spectraMatcher projects folder; save that to .config/settings.json .
    #   To make dearpygui work on win7: Make sure # https://learn.microsoft.com/en-GB/cpp/windows/latest-supported-vc-redist?view=msvc-170
    #   is installed, and include IEShims.dll and d3dcompiler_47.dll (currently present in C:\Users\Giogina\SpectraMatcher\venv_win\Lib\site-packages\dearpygui).
    #   pyinstaller --add-binary='path/to/dll;.' main.py
    #   For taskbar / shortcut icon: M made out of peaks
    #   Adapt os.system(f'python {sys.argv[0]} {flags}') to only os.system(f'{sys.argv[0]} {flags}'), make sure it works with the right executable.
