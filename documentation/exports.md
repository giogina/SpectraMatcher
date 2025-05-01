---
icon: sheep
---

# Export of Results

Once your spectra are aligned and peak matching is complete, SpectraMatcher lets you export your results in formats ready for publication or further analysis.

## Exporting the Assignment Table

The table of matched peaks — including intensities, transition labels, and wavenumbers — can be exported in several formats:

- **.txt** (tab-separated plain text) for spreadsheet analysis or scripting
- **.docx** (Word) for easy insertion into reports or manuscripts
- **.tex** (LaTeX) for direct inclusion in scientific publications

Choose the format in the drop-down menu in the **Match settings** panel, then click **Copy table** to copy the data to your clipboard, ready to paste into your text editor of choice.

> 💡 The copying functionality uses the clipboard tool installed on your system. On linux, this requires e.g. xclip to be installed — this is done automatically by SpectraMatcher's installation script.

<figure><img src=".gitbook/assets/copy_table_menu.png" alt="Copy table button"></figure>

The plain-text table is kept minimally formatted, to facilitate further analysis, e.g. in spreadsheet software.
The Word and LaTeX tables feature properly aligned columns and math-mode formatting for vibrational mode labels:
<figure><img src=".gitbook/assets/latex_table.png" alt="Rendered LaTeX table output"><figcaption>Example of the exported LaTeX table as rendered in a document.</figcaption></figure>

> 💡 Ensure you use `\usepackage{booktabs}` in your preamble to enable proper formatting of the LaTeX table. Alternatively, replace the `\toprule` etc. by `\hline` commands.

## Exporting Computed Spectra as Data

To export the computed spectrum data (e.g., the current composite spectrum), open the **Composite Spectrum** dropdown in the top right and click **Copy**. This copies the spectrum as tab-separated values:

```
wavenumber[int]    intensity[rel]
1345.0             0.12
1401.2             0.31
...
```

You can paste this into a spreadsheet, plotting tool, or save it to a `.txt` file.

<figure><img src=".gitbook/assets/copy_spectrum_button.png" alt="Copy composite spectrum"><figcaption>Copying the composite spectrum as tab-separated data.</figcaption></figure>

## Saving Annotated Screenshots

To save a snapshot of the current plot — including spectrum overlays, peak matches, and annotations — use the **Save Screenshot** button in the plot panel toolbar.

This produces a high-resolution `.png` image suitable for presentations or publication figures.

<figure><img src=".gitbook/assets/save_screenshot_button.png" alt="Save screenshot button"><figcaption>Saving a screenshot of the current spectrum view.</figcaption></figure>

## Where the Files Go

- Screenshots and exported tables are saved in the same directory as your `.smp` project file.
- Composite spectra are copied to the clipboard and can be saved manually.

> 💡 Not seeing the expected output? Make sure peak matching is active and a composite spectrum is selected.
