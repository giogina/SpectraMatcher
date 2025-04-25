================================================
SpectraMatcher — Vibronic Spectrum Matching Tool
================================================

This package contains:
- bin/                          ← Main application folder (precompiled binary)
- install_spectramatcher.sh     ← Installation script
- LICENSE                       ← MIT License
- README.txt                    ← This file. You're looking at it.


Installation Instructions (Linux)
---------------------------------

1. Unzip the archive:
   unzip SpectraMatcher_Linux.zip
   cd SpectraMatcher_Linux

2. Make the installer executable:
   chmod +x install_spectramatcher.sh

3. Run the installer with root permissions:
   sudo ./install_spectramatcher.sh

   This will:
   - Copy the application to /opt/SpectraMatcher
   - Install launcher and icon
   - Register the `.smp` file extension
   - Create a menu entry and optional desktop shortcut


How to launch SpectraMatcher
----------------------------

After installation, you can:

- Launch it from the system menu (under "Education" or "Science")
- Double-click `.smp` project files to open them directly


Resources & Help
----------------

Documentation:
https://giogina.gitbook.io/spectramatcher

GitHub source code & issues:
https://github.com/giogina/SpectraMatcher


Uninstallation
--------------

To uninstall, simply delete:

- /opt/SpectraMatcher
- /usr/share/applications/spectramatcher.desktop
- /usr/share/mime/packages/spectramatcher.xml
- Icon files from /usr/share/icons/.../mimetypes/application-x-spectramatcher*



Thank you for using SpectraMatcher!
