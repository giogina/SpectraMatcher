# Import Data files

After creating a project, you’ll be taken to the **Import Data** tab. This screen shows all files available for analysis.

If you added data in the setup screen, they’ll already be listed in the left-hand panel. You can add more files at any time by:
- Clicking the **“Add file”** or **“Add folder”** buttons in the top-right, or
- Dragging and dropping files or folders into the left panel.

<figure><img src=".gitbook/assets/Import_Data.png" alt="Import Data tab overview"><figcaption></figcaption></figure>

Once files are detected, click the **Auto Import** button to automatically gather and match compatible data.  
Spectra from imported files will appear in the **Emission** and **Excitation** tabs.

> 💡 **Tip:** Auto Import checks for consistency in geometry, method, and 0–0 transition energy.  
> You can also manually assign files by dragging them into the corresponding slots.

When you're ready, click **Done** to proceed to the spectrum viewer. This also causes the project to always be opened in the spectrum viewer tab in the future.

For supported file types and import options, see the [Data Import](File%20explorer.md) section.


## Accepted File Types

### Experimental Spectra Files

Experimental spectra can be supplied in the form of tables, in one of the following formats:

* as a tab- or comma- separated .txt, .csv or .tsv file,
* as an excel table in one of the formats .xls, .xlsx, .xlsm, .xltx or .xltm, or
* as an Open/Libre Office *.ods table

These tables should contain a column for the absolute and relative wavenumbers, as well as a column specifying the intensity.
Additional columns will be ignored.

The first line of the table may be column headings specifying their respective contents: Headings containing the substrings "abs", "rel" and "int" are interpreted as absolute wavenumbers, relative wavenumbers and intensitites.
If no such headings are supplied, SpectraMatcher identifies data columns according to their values.

Once an experimental spectrum data file is added to the project, the columns can be selected manually by right-clicking on the corresponding range:

<figure><img src=".gitbook/assets/select_data_columns.gif" alt=""><figcaption></figcaption></figure>

Experimental files are interpreted as excitation or emission spectra based on their file names: Any file containing one of the sub-strings "DF_", "fluor" or "emmi" is interpreted as an emission spectrum; all other data table files are interpreted as excitation spectra.

<!-- TODO: right-click to choose emmission / excitation -->

<!--<img src="../resources/laser-2-16.png" alt="Alt text for icon" width="16" height="16" style="display: inline;">-->

### Computed Spectra Files

SpectraMatcher parses Gaussian 16 output files, and detect the following types necessary for the rendering and analysis of vibronic spectra:


* <img src="../resources/FC-down-2-16-red.png" alt="Emission file icon" width="16" height="16" style="display: inline;">: Emission Franck-Condon / Herzberg-Teller computations
* <img src="../resources/FC-up-2-16-green.png" alt="Excitation file icon" width="16" height="16" style="display: inline;">: Excitation Franck-Condon / Herzberg-Teller computations
* <img src="../resources/file-freq-16-blue.png" alt="Frequency file icon" width="16" height="16" style="display: inline;">: Frequency & vibrational mode computations

<!-- TODO: Section about preparing these Gaussian files -->
