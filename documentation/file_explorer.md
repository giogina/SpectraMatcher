---
icon: folder-open
---

# Data Import & Project Setup

After creating a new project, you are presented with the "Import Data" tab, which is split into two parts:
* The file explorer panel on the left, which lists available input files.
* The project setup panel on the right, which shows the imported files.

## File explorer

If you added data files or folders during the project creation, this file explorer will already be populated. To include additional data, use the "Add file" or "Add folder" icons in the top right corner. Alternatively, in Windows, files and directories can be dragged and dropped directly into the left panel.

<figure><img src=".gitbook/assets/Import_Data.png" alt=""><figcaption></figcaption></figure>

The available data files are immediately read to detect experimental spectra and outputs of Gaussian 16 frequency and [vibronic computations](https://gaussian.com/g16vibronic-spectra). An overview of the contents these files is displayed alongside their names:
* The file icon indicates the type:
  * ![Emission file icon](../resources/FC-down-2-16-red.png): Emission Franck-Condon / Herzberg-Teller computations
  * ![Excitation file icon](../resources/FC-up-2-16-green.png): Excitation Franck-Condon / Herzberg-Teller computations
  * ![Frequency file icon](../resources/file-freq-16-blue.png): Frequency & vibrational mode computations
  * ![Experiment file icon](../resources/laser-2-16.png): Experimental spectrum (Green/Red for Excitation/Emission)
* The status symbol indicates the state of Gaussian jobs:
  * ✔️ Complete, successfully completed job.
  * 🏃 Still running or incomplete.
  * ⚠️ Completed job, but with negative frequencies.
  * ❌ Job encountered errors.
* Job type, method, molecular formula, 0-0 transition energy, and first frequencies.

See the [File Types](#accepted-input-file-types) section for a list of supported data formats and options.

Using the buttons on the top right of the file explorer, the entire list can be collapsed or expanded, or filtered for certain file extensions. The visible columns can be adjusted using the eye button.

Right-clicking any file in the explorer panel opens a context menu with additional options:

- **Ignore** to exclude the file or folder from auto-import.
- **Import into project** to add the file directly to the active project panel.
- **Copy last geometry** to clipboard — useful for reusing molecular structures in new calculations.
- **Open in file explorer** to locate the file on your system.
- **Make readable** to make `.log` files readable in basic editors like Notepad by converting line endings from Unix (\n) to Windows-style (\r\n).

These options make it easy to manage large datasets, troubleshoot files, and prepare follow-up calculations without leaving the interface.

## File import

Files available in the left panel can now be imported into the project. This can be done in two ways:\
By manually dragging each file into its corresponding slot, or simply by clicking **"Auto Import"** on top of the right panel.

The **Auto Import** button becomes active as soon as the scanning of files is complete. Auto import gathers all matching files by comparing ground state energies, molecular formulas and 0-0 transition energies.\
If the opened data folders contain computations for more than one molecule or method, the relevant one may be selected using the drop-down menu appearing under the project name.

If you want to import mis-matched files together - e.g., for comparing different frequency calculation methods - the consistency checks can be disabled by selecting Settings > "disable sanity checks".

Files imported into the project are immediately analyzed, and the respective spectra appear in the "Emission" and "Excitation" tabs.

Pressing the "Done" button finalizes the import, updates the project progress, and takes you to the Emission tab to begin analysis.

## Accepted Input File Types

### Experimental Spectra Files

Experimental spectra can be supplied in the form of tables, in one of the following formats:

- **Plain text**: `.txt`, `.tsv`, or `.csv` (tab- or comma-separated)
- **Excel spreadsheets**: `.xls`, `.xlsx`, `.xlsm`, `.xltx`, or `.xltm`
- **Open/LibreOffice spreadsheets**: `.ods`


Each file should contain columns for:
- **Absolute wavenumber**
- **Relative wavenumber**
- **Intensity**

Additional columns are ignored.

If the first line contains column headers, SpectraMatcher will use them to assign roles: If they contain substrings `"abs"`, `"rel"`, and `"int"`, they are interpreted as absolute wavenumber, relative wavenumber, and intensity, respectively.
If no such headings are supplied, SpectraMatcher identifies data columns by analyzing the trends and magnitudes of their values.

If this automatic column detection fails, after import the columns can be selected manually by right-clicking the corresponding range:

<figure><img src=".gitbook/assets/select_data_columns.gif" alt=""><figcaption></figcaption></figure>

#### Excitation vs. Emission

Experimental files are interpreted as excitation or emission spectra based on their file names: Any file containing one of the sub-strings "DF\_", "fluor" or "emmi" is interpreted as an emission spectrum; all other data table files are interpreted as excitation spectra.

### Computed Spectra Files

SpectraMatcher parses Gaussian 16 output files, and detects the following three types relevant for the rendering and analysis of vibronic spectra:

* ![Emission file icon](../resources/FC-down-2-16-red.png): Emission Franck-Condon / Herzberg-Teller computations
* ![Excitation file icon](../resources/FC-up-2-16-green.png): Excitation Franck-Condon / Herzberg-Teller computations
* ![Frequency file icon](../resources/file-freq-16-blue.png): Frequency & vibrational mode computations

Example Gaussian input (.gjf) and output (.log) files necessary for creating vibronic spectra of ovalene ($$C_{32}H_{14}$$, a polycyclic aromatic hydrocarbon) can be found [here](https://github.com/giogina/SpectraMatcher/tree/main/demo/ovalene.zip). All screenshots and outputs presented in this manual have been produced using this demo data - you can use it to follow along and test the features.

#### Frequency Files

Frequency jobs are used to extract:
- **Vibrational wavenumbers**, **displacement vectors** and **Molecular symmetry labels** for each normal mode
- **Zero-point energies** and total electronic energy
- **Geometry and atomic numbers**

If run with `freq=hpmodes`, SpectraMatcher will use high-precision displacement vectors (5 decimals); otherwise, the lower-precision versions are used.

These files are essential for applying **vibration-type–specific scaling factors**, as SpectraMatcher automatically classifies each vibrational mode (e.g. X–H stretch, out-of-plane bend) based on its displacement vector.

#### Vibronic (FC/HT) Files

Vibronic output files must include results of Franck–Condon / Herzberg–Teller computations, as produced by Gaussian's `fc` or `fcht` keywords. From these, SpectraMatcher extracts:
- The **wavenumber** and **intensity** of each vibronic transition
- The contributing vibrational modes and their quantum numbers
- The type of calculation (emission or excitation)
- The **zero-zero transition energy** (`ν₀₀`)

> ⚠️ Note: Files must be fully completed and contain no errors to be used in automatic import.
