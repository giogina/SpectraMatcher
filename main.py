import sys
from launcher import Launcher


# Windows: -m nuitka --assume-yes-for-downloads --standalone --follow-imports --include-data-dir=C:/Users/Giogina/SpectraMatcher/fonts=fonts  --include-data-dir=C:/Users/Giogina/SpectraMatcher/resources=resources --windows-icon-from-ico=C:/Users/Giogina/SpectraMatcher/resources/SpectraMatcher.ico --enable-plugin=tk-inter --windows-disable-console --output-filename=SpectraMatcher.exe $FilePath$
#         Installation wizard:
#         To make dearpygui work on win7: Make sure # https://learn.microsoft.com/en-GB/cpp/windows/latest-supported-vc-redist?view=msvc-170
#         is installed, and include IEShims.dll and d3dcompiler_47.dll (currently present in C:\Users\Giogina\SpectraMatcher\venv_win\Lib\site-packages\dearpygui).
#         (The VC .dlls are automatically included in Nuitka; the other two dlls are added by inno setup.)
#         Then, simply run wizard_creator.iss in Inno setup.

# Linux: -m nuitka --standalone --follow-imports --enable-plugin=tk-inter --include-data-dir=./fonts=fonts --include-data-dir=./resources=resources --assume-yes-for-downloads --output-filename=SpectraMatcher $FilePath$
#         mv main.dist/ (obtained form Nuitka) -> Linux_installer/bin/;
#         cd Linux_installer/
#         cp spectramatcher.sh bin/ (launcher to take care of the --open flag);
#         zip -9 -r SpectraMatcher_Linux_Installer.zip bin/ install_spectramatcher.sh README.txt LICENSE


def main():

    if len(sys.argv) > 3 and sys.argv[1] == "-dialog":   # DO NOT print anything (except the result) here - that would mess with subprocess results.
        from utility.system_file_browser import run_directly
        print(run_directly(sys.argv[2], sys.argv[3]))
        return

    log_file = None
    try:
        input_path = str(sys.argv[2]) if len(sys.argv) > 2 else "SpectraMatcher"
        log_file_path = Launcher.get_logfile_path(input_path)

        log_file = open(log_file_path, "w", buffering=1, encoding="utf-8")  # Line-buffered, safer

        sys.stdout = log_file  # Redirect stdout and stderr
        sys.stderr = log_file
    except Exception as e:
        print(f"Could not open log file {log_file_path}: {e}")
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

    Launcher.cleanup_old_logs()
    print(f"Program started with flags: {sys.argv}")

    flags = None
    if len(sys.argv) > 1:
        if sys.argv[1] == "-open" and len(sys.argv) > 2:
            from views.main_window import MainWindow
            MainWindow(sys.argv[2]).show()
        elif sys.argv[1] == "-new":
            from views.create_project import CreateProjectWindow
            if len(sys.argv) > 2:
                flags = CreateProjectWindow(sys.argv[2:len(sys.argv)]).show()
            else:
                flags = CreateProjectWindow().show()
        else:
            return
    else:
        from views.startup_dashboard import Dashboard
        flags = Dashboard().show()

    if flags:  # Restart this program with proper flags.
        Launcher.launch(*flags)

    if log_file:
        try:
            log_file.close()
        except Exception as e:
            print("Closing exception: ", e)
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__


if __name__ == "__main__":
    main()
