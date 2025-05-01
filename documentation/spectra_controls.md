---
icon: wave-pulse
---

# Visualization & Spectra Controls

The emission and excitation spectra corresponding to the experiment and all computed excited states are shown in the "Emission Spectra" and "Excitation Spectra" tabs.

<figure><img src=".gitbook/assets/emission_tab.png" alt="SpectraMatcher Emission Spectra overview"><figcaption></figcaption></figure>

The white, lower-most spectrum is the experimental spectrum, or a combination of the experimental spectra if multiple are supplied.\
The computed spectra are displayed above, and listed in the left side-panel.
The right panel provides controls for various plot, spectrum, and matching properties.\
This section explains the various ways in which the plot and spectra can be manipulated, including:
* [Moving and scaling](#moving-and-scaling-computed-spectra) of computed spectra
* Setting the **half-width** of computed spectra
* Applying **anharmonic correction factors** to different vibration types
* Showing customizable **transition labels**
* Animating vibrational modes
* Adjusting the (auto-detected) experimental peak positions
* Overlaying composite computed spectra onto the experimental one


## Plot controls: Zoom & Pan

The plot can be zoomed with constant aspect ratio by scrolling while the mouse is hovered over a by scrolling while hovering the mouse over an empty area of the plot (i.e., not over a spectrum).\
To zoom only in x or y direction, hover the mouse over the corresponding axis and scroll.

Equivalently, the plot can be dragged freely by clicking into the free plot area, or along one axis only by dragging the axis.

Zoom into an interesting region by right-click-dragging over it. Double click the plot to zoom out to show all contents.

Alternatively, to set exact axis limits, right-click the axis (or the plot area and select X/Y axis), Ctrl+click the relevant min/max number, and enter the desired number.

Further axis and plot options are available in the plot context menu under "X/Y axis" and "Settings":

<figure><img src=".gitbook/assets/Axis_right_click_menu.png" alt=""><figcaption></figcaption></figure>

[//]: # (<figure><img src=".gitbook/assets/settings_right_click_menu.png" alt=""><figcaption></figcaption></figure>)

## Slider controls

All sliders can be changed by dragging the handle or by scrolling the mouse wheel while hovering the mouse over the slider.

Alternatively, an exact numerical value can be entered after holding Control and left-clicking the slider.

The arrow keys adjust the last altered slider in the corresponding direction:\
The vertical arrow keys ↑ ↓ alter the most recently changed vertical spectrum shift, spectrum scale, or global vertical spacing.\
The horizontal arrow keys ← → adjust the most recently changed spectrum wavenumber shift, half width, or anharmonic correction factor.

Holding down Shift while scrolling or using arrow buttons allows for finer adjustments.

## Moving and scaling computed spectra

The computed spectra can be moved horizontally and vertically, as well as scaled vertically, in three ways:

### Spectra control panel

Each spectrum can be individually moved using its corresponding sliders in the left control panel:

<figure><img src=".gitbook/assets/state_sliders.png" alt="Spectrum slider controls"><figcaption></figcaption></figure>

Additionally, using the buttons on the right-hand side of this section, one can hide the spectrum from the plot, choose its color, and reset the shift & scale parameters.

### Plot drag lines

Spectra can be manipulated directly in the plot, using certain drag lines which appear when the mouse pointer is close enough. All available drag lines can be shown by holding down the Alt button.\
Hovering the mouse near the base of the spectrum reveals a drag line which can be used to vertically drag the spectrum. While this line is being hovered, scrolling the mouse wheel scales the corresponding spectrum:

<figure><img src=".gitbook/assets/scroll_and_y_shift_using_drag_lines.gif" alt="Scrolling and y shifting using drag lines"><figcaption></figcaption></figure>

Similarly, hovering the mouse at the position of the highest peak reveals a line which can be used to horizontally drag the spectrum. Scrolling while this drag line is hovered adjusts the half-width of the computed spectra.\
Note that the half-width is a global variable applied to all computed spectra, as it should not depend on the choice of excited state.

<figure><img src=".gitbook/assets/scroll_and_wavenumber_shift_using_drag_lines.gif" alt="Scrolling and x shifting using drag lines"><figcaption></figcaption></figure>

As with sliders, holding down the Shift button causes a finer adjustment while scrolling.

### Global vertical spacing

The global "vertical spacing" slider on the top right places all visible spectra equidistantly.


## Vibrational mode animations

## Composite Spectrum

The composite spectrum is a sum of selected computed excited-state spectra.
While the matching mode is not active, the composite spectrum is shown as an overlay over the experimental spectrum:

<figure><img src=".gitbook/assets/overlay_composite.png" alt="Composite spectrum computed overlayed over experiment"></figure>

This can be quite useful while aligning the computed spectra with the experimental data. To add or remove spectra from the composite, you can:
- Hold `Ctrl` and click on a computed spectrum in the plot to quickly add or remove it.
- Use the checkboxes in the **Composite Spectrum** panel to include or exclude specific excited states:

<figure><img src=".gitbook/assets/composite.png" alt="Composite spectrum selection"></figure>

In the bottom of this panel, you can choose how the composite spectrum and its components are displayed:
- **Composite spectrum**: The sum of all individual component spectra, as a line (white/black).
- **Component spectra**: The component spectra, stacked on top of each other, as colored lines.
- **Shaded contributions**: The area under each component spectrum is colored.

This is quite fun to play with:
<figure><img src=".gitbook/assets/composite.gif" alt="Composite spectra"></figure>

> 📝 Note: Peak labels are a property of the component spectra. Thus, if you turn off the **component spectra** option, the labels will disappear.
