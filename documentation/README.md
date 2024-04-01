# Quick start guide

SpectraMatcher is a tool for displaying and analyzing experimental and computed vibronic spectra.

## Installation

A Windows installation file is available [here](../installer/SpectraMatcher-setup.exe). Simply download this .exe and click through the installation wizard. No special permissions are necessary.

It is recommended to keep the default installation directory.

## Startup

The startup dashboard allows to create or open a SpectraMatcher project file. These files, which have the extension .spm, are by default saved in the C:\Users\UserName\SpectraMatcher\ directory.

You may use up or down arrow keys to select a recent project, and hit enter to open it. Pressing Escape closes the dashbaord.

<figure><img src=".gitbook/assets/Dashboard.png" alt=""><figcaption></figcaption></figure>

## Create a new project

Upon choosing to create a new project, you are queried to choose the project name and file location. Optionally, you can already supply data files; either by clicking the "Add folder" icon, or by dragging & dropping files or folders into the "import data" field.

<figure><img src=".gitbook/assets/Create_Project.png" alt=""><figcaption></figcaption></figure>

## Import Data

After completing the initial project creation, you are presented by the "Import Data" tab, which gives an overview of all files available for analysis.project

If you added data files or folders in the previous step, the file overview panel on the left will already be populated. The "Add file" or "Add folder" icons in the top right corner of the left panel open file explorer windows to include additional data. Alternatively, files and directories can be added by dragging and dropping them into the left panel.

<figure><img src=".gitbook/assets/Import_Data.png" alt=""><figcaption></figcaption></figure>

The available data files are immediately scanned to detect experimental spectra, in the form of tables, and computed spectra, in the form of Gaussian 16 output files.
See the [Import Data](documentation/File%20explorer.md) section for supported data formats and options.



