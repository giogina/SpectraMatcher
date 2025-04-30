# SpectraMatcher

SpectraMatcher is a tool for analyzing and matching vibronic spectra. A quick start guide and full manual can be found here: https://spectramatcher.gitbook.io/spectramatcher

The tool is available as compiled binaries for Windows and Linux, or can be run using Python. The respective setup steps are described below.


<details><summary><strong>Windows installer</strong></summary>

SpectraMatcher is compatible with **Windows 7 and above**.

To install:

1. Download the latest installer from the [`windows_installer/`](windows_installer/) folder of this repository.
2. Run the `.exe` file and follow the prompts.

That's it — no Python or dependencies required.  
Once installed, you can launch SpectraMatcher from the Start Menu or by double-clicking `.smp` project files.

> 💡 If you encounter a warning from Windows SmartScreen, choose “More info” → “Run anyway”.

---


</details>


<details><summary><strong>Linux installer</strong></summary>

The provided SpectraMatcher binary requries **glibc version 2.31 or newer** (typically available on Ubuntu 20.04+, Debian 11+, Fedora 32+, and most other Linux distributions released since 2020).


Download the installer [linux_installer/SpectraMatcher_Linux_Installer_1.1.0.zip](linux_installer/SpectraMatcher_Linux_Installer_1.1.0.zip) and follow these steps:

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

---
</details>

<details><summary><strong>Run from source (Python)</strong></summary>

SpectraMatcher can also be run directly from source using Python 3.7+  
This is useful if you want to contribute to development or run on platforms not supported by the precompiled installer.

#### 1. Clone the repository
```bash
git clone https://github.com/giogina/SpectraMatcher.git
cd SpectraMatcher
```

#### 2. Install dependencies
<details><summary>Windows setup</summary>
On recent Windows verions, install the required libaries with

```bash
pip install -r requirements/win-latest.txt
```

On Windows 7, only Python 3.7 can be run, which requires specific versions of the dependencies. These libraries can be installed with

```bash
pip install -r requirements/win7.txt
```
Should a library download no longer be available, use the [backup wheels](./backup_wheels_python37/).
Be careful to keep the provided `.dll` files in the main directory, as some might be missing from Windows 7. 

You can then run SpectraMatcher as
```bash
python main.py
```
or open a project file with
```bash
python main.py -open file.smp
```

---
</details>

<details><summary>Linux setup</summary>

Make sure you have the following system dependencies installed first:
```bash
# On Debian/Ubuntu:
sudo apt install python3-tk wmctrl xclip
```
Then install the Python packages:
```bash
pip install -r requirements/unix.txt
```
And run:

```bash
python3 main.py
```

or open a file with
```bash
python3 main.py -open file.smp
```
---
</details>

</details>

---

![](./documentation/.gitbook/assets/screenshot.png)