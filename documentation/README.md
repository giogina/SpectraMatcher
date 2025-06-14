---
icon: binoculars
---

# About SpectraMatcher

## SpectraMatcher: Interactive analysis of vibronic spectra

**SpectraMatcher** is a graphical cross-platform desktop tool for analyzing and matching **computed and experimental vibronic spectra**. Designed for chemists working with **Gaussian** output files, it streamlines **Franck–Condon/Herzberg–Teller** spectral analysis through intuitive visualization, real-time spectrum adjustment, and interactive **peak assignment**.

It supports automatic import of frequency and vibronic calculations for multiple excited states, overlaying and editing spectra directly on the plot, and exporting publication-ready tables and figures — no coding required.

The software is available open source under the [MIT license](https://opensource.org/licenses/MIT) and actively maintained at [github.com/giogina/SpectraMatcher](https://github.com/giogina/SpectraMatcher/), where you’ll find the latest releases, example files, and installation instructions.

Check out the features below, or jump right to the [Quick Start Guide](quickstart.md).

<figure><img src=".gitbook/assets/screenshot.png" alt="SpectraMatcher Screenshot"><figcaption></figcaption></figure>

## Features

### [Smart import & auto-detection of Gaussian files](file_explorer.md#file-explorer)

SpectraMatcher scans all added files — including entire folders — to automatically detect and classify [Gaussian 16](https://gaussian.com/) frequency and ([Franck-Condon](https://en.wikipedia.org/wiki/Franck%E2%80%93Condon_principle) / [Herzberg-Teller](https://condensedconcepts.blogspot.com/2013/03/what-is-herzberg-teller-coupling.html)) [vibronic computations](https://gaussian.com/g16vibronic-spectra/), as well as experimental spectra. Icons indicate job type and status (complete, error, negative frequencies), while additional data (molecular formula, method, $$u_{00}$$, etc.) is extracted on the fly.

<figure><img src=".gitbook/assets/file_explorer.png" alt="File explorer panel"><figcaption><p>Gaussian jobs are scanned and labeled automatically during import.</p></figcaption></figure>

All matching files can be conveniently imported with a single click on the **Auto Import** button.

### [Supports messy real-world data](file_explorer.md#experimental-spectra-files)

Experimental spectra in `.txt`, `.csv`, Excel, or OpenOffice format are recognized automatically — even without column headers. SpectraMatcher recognizes column roles based on trends and values; manual correction is a right-click away.

<figure><img src=".gitbook/assets/select_data_columns.gif" alt="Column selection for imported spectrum"><figcaption><p>Fix broken data tables with a click.</p></figcaption></figure>

It also distinguishes excitation vs. emission based on filename keywords, so you can batch-import with minimal prep.

### [Interactive spectra adjustments - right in the plot](plot_controls.md)

The experimental and computed [vibronic spectra](https://en.wikipedia.org/wiki/Vibronic_spectroscopy) are displayed in highly interactive plots; both for the fluorescence and the excitation spectra.
No need to hunt for controls — just grab and drag. Move entire spectra, shift peaks, adjust peak half-widths, or reposition labels by interacting directly with the plot.

<figure><img src=".gitbook/assets/scroll_and_wavenumber_shift_using_drag_lines.gif" alt="Spectra x shift drag line"><figcaption><p>Quickly shift wavenumbers or adjust peak broadening.</p></figcaption></figure>

<figure><img src=".gitbook/assets/label_moving.gif" alt="Label drag"><figcaption><p>Drag labels to reposition them exactly where you want.</p></figcaption></figure>

### [Fine-tuning of anharmonic corrections](spectra_controls.md#anharmonic-correction-factors)

Computed spectra often overestimate [vibrational frequencies](https://en.wikipedia.org/wiki/Molecular_vibration) due to the harmonic approximation. SpectraMatcher lets you correct this using anharmonic correction [frequency scaling factors](https://doi.org/10.1021/jp073974n) — not just globally, but per **vibrational mode type**: X–H stretches, [out-of-plane bends](https://doi.org/10.1051/0004-6361:20010242), and other modes can each have their own correction factor.

<figure><img src=".gitbook/assets/anharmonic_correction_sliders.png" alt="anharmonic correction settings"><figcaption><p>Each vibrational mode type gets its own scaling factor.</p></figcaption></figure>

Vibrational modes are auto-classified based on their displacement vectors, and sticks in the spectrum are color-coded by type (e.g. red = X–H stretch). Adjust the sliders, and watch matching peaks snap into place:

<figure><img src=".gitbook/assets/hydrogen_stretch_peak_moving.gif" alt="X-H stretch correction in action"><figcaption><p>Only X–H stretch peaks shift — the rest stay put.</p></figcaption></figure>

This lets you apply physically meaningful corrections with high precision — and without overfitting.

### [Vibrational mode animations](spectra_controls.md#vibrational-mode-animations)

Visualize what vibrational mode is responsible for a peak by clicking its label to animate the molecular motion:

<figure><img src=".gitbook/assets/anim.gif" alt="Spectrum slider controls"><figcaption></figcaption></figure>

### [Build composite spectra from excited states](spectra_controls.md#composite-spectrum)

Overlay spectra from multiple excited states into a single composite — perfect when experimental peaks arise from overlapping transitions. Click spectra or use checkboxes to include/exclude components in real time.

<figure><img src=".gitbook/assets/composite.gif" alt="Composite spectra"><figcaption><p>Interactively overlay excited-state contributions and see how well they explain experiment.</p></figcaption></figure>

Display the result as a single curve, stacked colored components, or shaded areas. A powerful tool when one state isn't enough.

### [Clean, publication-ready export](exports.md)

After matching peaks, you can copy the peak assignment table directly as tab-separated text, or nicely formatted as Word or LaTeX — ready to paste straight into your paper.

<figure><img src=".gitbook/assets/latex_table.png" alt="Rendered LaTeX table output"><figcaption><p>LaTeX export — no manual formatting required.</p></figcaption></figure>

Or take a screenshot of the annotated spectrum — perfect for slides, figures, or sharing your results.

<figure><img src=".gitbook/assets/match_plot.png" alt="Plot of matched labeled vibronic spectra"><figcaption><p>Plot of labeled, matched vibronic spectra.</p></figcaption></figure>
