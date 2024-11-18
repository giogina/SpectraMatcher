# Import Data files

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

<figure><img src=".gitbook/assets/select data columns.gif" alt=""><figcaption></figcaption></figure>

Experimental files are interpreted as excitation or emission spectra based on their file names: Any file containing one of the sub-strings "DF_", "fluor" or "emmi" is interpreted as an emission spectrum; all other data table files are interpreted as excitation spectra.

<!-- TODO: right-click to choose emmission / excitation -->

<!--<img src="../resources/laser-2-16.png" alt="Alt text for icon" width="16" height="16" style="display: inline;">-->

### Computed Spectra Files

SpectraMatcher parses Gaussian 16 output files, and detect the following types necessary for the rendering and analysis of vibronic spectra:


* <img src="../resources/FC-down-2-16-red.png" alt="Emission file icon" width="16" height="16" style="display: inline;">: Emission Franck-Condon / Herzberg-Teller computations
* <img src="../resources/FC-up-2-16-green.png" alt="Excitation file icon" width="16" height="16" style="display: inline;">: Excitation Franck-Condon / Herzberg-Teller computations
* <img src="../resources/file-freq-16-blue.png" alt="Frequency file icon" width="16" height="16" style="display: inline;">: Frequency & vibrational mode computations

<!-- TODO: Section about preparing these Gaussian files -->
