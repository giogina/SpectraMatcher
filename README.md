# SpectraMatcher

SpectraMatcher is a tool for analyzing and matching vibronic spectra. A quick start guide and full manual are available here: https://spectramatcher.gitbook.io/spectramatcher

The tool is available as compiled binaries for Windows and Linux, or can be run using Python. The respective setup steps are described below.


Installation wizards:

/installer/Spectramatcher-setup-ver#.exe

Requirements: Windows 7+


<details><summary><strong>Windows installer</strong></summary>
</details>


<details><summary><strong>Linux installer</strong></summary>
To install the Linux binary, download the [installer](Linux_installer/) follow these steps:


1. Unzip the archive:

```bash
   unzip SpectraMatcher_Linux.zip
   cd SpectraMatcher_Linux
```
2. Make the installer executable:
```bash
   chmod +x install_spectramatcher.sh
```
3. Run the installer with root permissions:
```bash
   sudo ./install_spectramatcher.sh
```
   This will:
   - Copy the application to /opt/SpectraMatcher
   - Install launcher and icon
   - Register the `.smp` file extension
   - Create a menu entry and optional desktop shortcut

You can then simply start SpectraMatcher through the start menu / desktop icon, through the console using ```/opt/SpectraMatcher/SpectraMatcher```, or directly open ```.smp``` SpectraMatcher project files.
</details>
