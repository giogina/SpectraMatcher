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