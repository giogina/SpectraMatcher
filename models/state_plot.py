from scipy import signal
from models.experimental_spectrum import ExperimentalSpectrum
from utility.labels import Labels
from utility.matcher import Matcher
from utility.noop import noop
from models.molecular_data import FCSpectrum
import numpy as np

from utility.spectrum_plots import SpecPlotter


class StatePlot:
    def __init__(self, state, is_emission: bool, state_index=0, match_plot=None):
        self.tag = StatePlot.construct_tag(state, is_emission)
        self.state = state
        self.spectrum = state.get_spectrum(is_emission)
        self.spectrum.add_observer(self)
        self.name = state.name
        self.index = state_index
        self.e_key = 'emission' if is_emission else 'excitation'
        self.xshift = self.state.settings.get(f"x shift {self.e_key}", 0)
        self.yshift = self.state.settings.get(f"y shift {self.e_key}", state_index*Labels.settings[is_emission].get('global y shifts', 1.25))
        self.state.settings[f"y shift {self.e_key}"] = self.yshift
        self.yscale = self.state.settings.get(f"y scale {self.e_key}", 1)
        self._base_xdata = self.spectrum.x_data
        self._base_ydata = self.spectrum.y_data
        self.xdata = self._compute_x_data()
        self.ydata = self._compute_y_data()
        self.handle_x = self._base_xdata[np.where(self._base_ydata == max(self._base_ydata))[0][0]]
        self.sticks = []  # stick: position, [[height, color]]
        if self.spectrum.vibrational_modes is not None:
            for peak in self.spectrum.peaks:
                if peak.transition[0] != [0]:
                    sub_stick_scale = peak.intensity/sum([t[1] for t in peak.transition])
                    self.sticks.append([peak.corrected_wavenumber, [[vib[1]*sub_stick_scale, [c*255 for c in vib[0].vibration_properties]] for vib in [(self.spectrum.vibrational_modes.get_mode(t[0]), t[1]) for t in peak.transition if len(t) == 2] if vib is not None]])
        self.spectrum_update_callback = noop
        self.sticks_update_callback = noop
        self.match_plot = match_plot

    @staticmethod
    def construct_tag(state, is_emission):
        return f"{state.name} - {is_emission} plot"

    def update(self, event, *args):
        if event == FCSpectrum.xy_data_changed_notification:
            self._base_xdata = self.spectrum.x_data
            self._base_ydata = self.spectrum.y_data
            self.xdata = self._compute_x_data()
            self.ydata = self._compute_y_data()
            self.handle_x = self._base_xdata[np.where(self._base_ydata == max(self._base_ydata))[0][0]]
            self.spectrum_update_callback(self)
            self.update_match_plot()
        if event == FCSpectrum.peaks_changed_notification:
            self.sticks = []  # stick: position, [[height, color]]
            for peak in self.spectrum.peaks:
                if peak.transition[0] != [0]:
                    sub_stick_scale = peak.intensity / sum([t[1] for t in peak.transition])
                    self.sticks.append([peak.corrected_wavenumber,
                                        [[vib[1] * sub_stick_scale, [c * 255 for c in vib[0].vibration_properties]] for
                                         vib in [(self.spectrum.vibrational_modes.get_mode(t[0]), t[1]) for t in
                                                 peak.transition if len(t) == 2] if vib is not None]])
            self.sticks_update_callback(self)

    def set_spectrum_update_callback(self, callback):
        self.spectrum_update_callback = callback

    def set_sticks_update_callback(self, callback):
        self.sticks_update_callback = callback

    def _compute_x_data(self):
        return self._base_xdata + self.xshift

    def _compute_y_data(self):
        return (self._base_ydata * self.yscale) + self.yshift

    def set_x_shift(self, xshift):
        self.xshift = xshift - self.handle_x
        self.state.settings[f"x shift {self.e_key}"] = self.xshift
        self.xdata = self._compute_x_data()
        self.update_match_plot()

    def set_y_shift(self, yshift, temporary=False):
        if temporary or self.match_plot is None or not self.match_plot.matching_active:
            self.yshift = yshift
            self.ydata = self._compute_y_data()
        if not temporary:
            self.state.settings[f"y shift {self.e_key}"] = yshift

    def restore_y_shift(self):
        self.yshift = self.state.settings.get(f"y shift {self.e_key}", 1.25)
        self.ydata = self._compute_y_data()

    def resize_y_scale(self, direction):
        self.yscale += direction * 0.1
        self.yscale = max(0, self.yscale)
        self.state.settings[f"y scale {self.e_key}"] = self.yscale
        self.ydata = self._compute_y_data()
        self.update_match_plot()

    def set_y_scale(self, value):
        self.yscale = value
        self.state.settings[f"y scale {self.e_key}"] = value
        self.ydata = self._compute_y_data()
        self.update_match_plot()

    def set_color(self, color, selection_type="manual"):
        self.state.settings["color"] = color
        self.state.settings["color selection type"] = selection_type

    def get_xydata(self, xmin, xmax):
        if self.xdata[0] < xmin:
            step = float(self.xdata[1] - self.xdata[0])
            start = min(int((xmin - self.xdata[0]) / step), len(self.xdata)-1)
        else:
            start = 0
        if self.xdata[-1] > xmax:
            step = float(self.xdata[1] - self.xdata[0])
            stop = max(int((xmax - self.xdata[-1]) / step), -len(self.xdata)+1)
        else:
            stop = len(self.xdata)
        return self.xdata[start:stop], self.ydata[start:stop]

    def is_hidden(self, during_match=None):
        if during_match is None:
            during_match = self.match_plot is not None and self.match_plot.matching_active
        if during_match:
            return self.state.settings.get(f"hidden during match {self.e_key}", self.is_matched())
        else:
            return self.state.settings.get(f"hidden {self.e_key}", False)

    def hide(self, hide=True):
        if self.match_plot is not None and self.match_plot.matching_active:
            self.state.settings[f"hidden during match {self.e_key}"] = hide
        else:
            self.state.settings[f"hidden {self.e_key}"] = hide
        # self.update_match_plot()

    def add_to_match_spec(self, add=True):
        self.state.settings[f"matched {self.e_key}"] = add

    def is_matched(self):
        return self.state.settings.get(f"matched {self.e_key}", False)

    def update_match_plot(self):
        if self.match_plot is not None:
            self.match_plot.compute_composite_xy_data()


class MatchPlot:
    match_plot_changed_notification = "Match plot changed"

    def __init__(self, is_emission: bool):
        self.contributing_state_plots = []  # StatePlot instances
        self.xdata = []
        self.ydata = []
        self.yshift = 0
        self.is_emission = is_emission
        self.hidden = True
        self._observers = []
        self.partial_y_datas = []
        self.maxima = []
        self.super_clusters = {}
        self.matching_active = False
        Matcher.add_observer(self)
        self.exp_peaks = []
        self.dragging = False  # True if match plot drag line is currently being moved

    def add_observer(self, obs):
        self._observers.append(obs)

    def _notify_observers(self):
        for obs in self._observers:
            obs.update(MatchPlot.match_plot_changed_notification, self)

    def update(self, event, *args):
        if event == Matcher.match_settings_updated_notification:
            self.assign_peaks()

    def add_state_plot(self, spec: StatePlot):
        if spec not in self.contributing_state_plots:
            self.contributing_state_plots.append(spec)
        spec.add_to_match_spec(add=True)
        self.hidden = len(self.contributing_state_plots) == 0
        self.compute_composite_xy_data()

    def remove_state_plot(self, spec: StatePlot):
        if spec in self.contributing_state_plots:
            self.contributing_state_plots.remove(spec)
        spec.add_to_match_spec(add=False)
        self.hidden = len(self.contributing_state_plots) == 0
        self.compute_composite_xy_data()

    def reset(self):
        self.hidden = True
        self.yshift = 0
        self.contributing_state_plots = []
        self._notify_observers()

    def compute_composite_xy_data(self):
        plotter_key = SpecPlotter.get_plotter_key(self.is_emission)
        if plotter_key is None:
            return
        x_step = plotter_key[-1]  # step size used in all xdata arrays
        x_min = min([s.xdata[0] for s in self.contributing_state_plots], default=0)
        x_max = max([s.xdata[-1] for s in self.contributing_state_plots], default=1)
        self.xdata = np.array(np.arange(start=x_min, stop=x_max, step=x_step))  # mirrors SpecPlotter x_data construction
        self.ydata = np.zeros(len(self.xdata)) + self.yshift
        self.partial_y_datas = [(self.ydata.copy(), None)]
        for s in self.contributing_state_plots:
            start_index = min(max(0, int((s.xdata[0] - x_min)/x_step)), len(self.xdata)-1)
            stop_index = min(start_index + len(s.ydata), len(self.ydata))
            spec_y_data = (s._base_ydata * s.yscale)[0:stop_index-start_index]
            self.ydata[start_index:stop_index] += spec_y_data
            self.partial_y_datas.append((self.ydata.copy(), s.tag))
            component_ydata = np.zeros(len(self.xdata)) + self.yshift
            component_ydata[start_index:stop_index] += spec_y_data
        self.compute_min_max()
        self.find_contributing_clusters()
        self.assign_peaks()
        self._notify_observers()

    def compute_min_max(self):
        """Find indices of local minima and maxima of self.ydata"""
        if len(self.ydata) == 0:
            return
        maxima, _ = list(signal.find_peaks(self.ydata))
        if len(maxima) == 0:
            return
        mins, _ = list(signal.find_peaks([-y for y in self.ydata]))
        minima = [0]
        minima.extend(mins)
        minima.append(len(self.ydata) - 1)

        self.maxima = []  # list of (min_x, max_x, min_x)

        jj = 0
        for ii, i in enumerate(minima[:-1]):
            while maxima[jj] < i:
                jj += 1
                if jj >= len(maxima):
                    break
            self.maxima.append(((self.xdata[i], self.ydata[i]-self.yshift), (self.xdata[maxima[jj]], self.ydata[maxima[jj]]-self.yshift), (self.xdata[minima[ii+1]], self.ydata[minima[ii+1]]-self.yshift)))

    def find_contributing_clusters(self):
        super_clusters = {}
        for maximum in self.maxima:
            xmin = maximum[0][0]
            xmax = maximum[2][0]
            super_clusters[maximum[1]] = {s.tag: [] for s in self.contributing_state_plots}
            for s in self.contributing_state_plots:
                for cluster in s.spectrum.clusters:
                    if xmin <= cluster.x + s.xshift < xmax:
                        super_clusters[maximum[1]][s.tag].append(cluster)
        self.super_clusters = super_clusters

    def assign_peaks(self):
        if not self.matching_active:
            return
        exp_peaks = []
        for exp in ExperimentalSpectrum.spectra_list:
            if exp.is_emission == self.is_emission and not exp.hidden:
                exp_peaks.extend(exp.peaks)
        for peak in exp_peaks:
            peak.match = None

        if not Matcher.get(self.is_emission, "assign only labeled"):
            super_cluster_peaks = list(self.super_clusters.keys())
        else:
            super_cluster_peaks = []
            for mm, tag_clusters in self.super_clusters.items():
                include = False
                for tag, cluster_list in tag_clusters.items():
                    if sum([len(cluster.label.strip()) for cluster in cluster_list]) > 0:
                        include = True
                        break
                if include:
                    super_cluster_peaks.append(mm)

        super_cluster_peaks.sort(key=lambda p: p[1], reverse=True)  # Assign in order of decreasing intensity
        match_failed = []

        for i, pp in enumerate(super_cluster_peaks):
            (search_wn, y) = pp
            match = None
            best_intensity_by_distance = 0
            for p1 in exp_peaks:
                if p1.match is not None:
                    continue  # p1 has already been assigned
                dist = search_wn - p1.wavenumber
                if abs(dist) > Matcher.get(self.is_emission, 'distance match threshold'):
                    continue
                int_by_dist = abs(p1.intensity / dist ** 2)
                if int_by_dist > best_intensity_by_distance:
                    match = p1
                    best_intensity_by_distance = int_by_dist
            if match is not None and min(match.intensity / y, y / match.intensity) > Matcher.get(self.is_emission, 'peak intensity match threshold'):
                match.match = pp
            else:
                match_failed.append(pp)
        self.exp_peaks = exp_peaks
        self._notify_observers()

    def activate_matching(self, on=True):
        self.matching_active = on
        Matcher.set(self.is_emission, 'match active', on)
        if on:
            self.set_yshift(Matcher.get(self.is_emission, 'combo spectrum y shift', 1.25))
            self.assign_peaks()
        else:
            self.set_yshift(0)

    def only_labeled_peaks(self, on):
        Matcher.set(self.is_emission, 'assign only labeled', on)

    def list_only_labeled_transitions(self, on):
        Matcher.set(self.is_emission, 'list only labeled transitions', on)

    def set_yshift(self, value):
        if self.matching_active:
            Matcher.set(self.is_emission, 'combo spectrum y shift', value)
        delta_y_shift = value - self.yshift
        self.yshift = value
        if len(self.ydata) == 0:
            self.compute_composite_xy_data()
        else:
            self.ydata += delta_y_shift
            self.partial_y_datas = [(t[0]+delta_y_shift, t[1]) for t in self.partial_y_datas]
            self._notify_observers()

    def is_spectrum_matched(self, spec):
        if isinstance(spec, StatePlot):
            return spec in self.contributing_state_plots
        else:
            return spec in [s.tag for s in self.contributing_state_plots]

    def get_match_table_html(self, use_gaussian_labels):
        table = self.get_match_table(use_gaussian_labels=use_gaussian_labels)
        clipboard_html = """
        Version:0.9
        StartHTML:00000097
        EndHTML:{end_html}
        StartFragment:00000133
        EndFragment:{end_fragment}
        <html>
        <body>
        <!--StartFragment-->
        <table>""".replace("\n", "\r\n")

        for line in table:
            line[-3] = Labels.label2html(line[-3])
            clipboard_html += "<tr><td>" + "</td><td>".join([str(entry) for entry in line]) + "</td></tr>\r\n"

        clipboard_html += "</table>\r\n<!--EndFragment-->\r\n</body>\r\n</html>"
        clipboard_html = clipboard_html.format(end_html=len(clipboard_html) + 1, end_fragment=len(clipboard_html) - 26)
        return clipboard_html

    def get_match_table_tex(self, use_gaussian_labels):
        table = self.get_match_table(use_gaussian_labels=use_gaussian_labels)

        column_alignment = "|".join(["c" for _ in range(len(table[0]))])
        latex_table = "\\begin{tabular}{" + "|" + column_alignment + "|}\n\\hline\n"

        for line in table:
            line[-3] = Labels.label2tex(line[-3])
            latex_table += " & ".join([str(entry) for entry in line]) + " \\\\\n\\hline\n"

        latex_table += "\\end{tabular}"
        return latex_table

    def get_match_table(self, use_gaussian_labels=False, header_only=False):
        table = [["experimental peak position",
                                  "experimental peak intensity",
                                  "computed peak position",  # comp spectrum (composite) peak wavenumber (maximum[0])
                                  "computed peak intensity",  # comp spectrum (composite) peak intensity (maximum[1]) (?)

                                  "state",
                                  "mode wavenumber",
                                  "corrected wavenumber",
                                  'intensity',
                                  'transition',
                                  'symmetry',
                                  'vibration type']]
        if header_only:
            return table

        for peak in self.exp_peaks:
            peak_data_list = [format(peak.wavenumber, ".1f"), format(peak.intensity, ".3f")]
            line_added = False
            if peak.match is None:
                peak_data_list += ["", ""]
            else:
                peak_data_list += [format(peak.match[0], ".1f"), format(peak.match[1], ".3f")]
                for tag in self.super_clusters[peak.match].keys():
                    spec = ([s for s in self.contributing_state_plots if s.tag == tag]+[None])[0]
                    peak_data_list += [spec.name]
                    if spec is not None:
                        for cluster in self.super_clusters[peak.match][tag]:
                            peak_list = cluster.filtered_peaks(spec.yscale) if Matcher.get(self.is_emission, "list only labeled transitions") else cluster.peaks
                            for p, peak in enumerate(peak_list):
                                mode_data_list = [format(peak.wavenumber+spec.xshift, ".1f"),
                                                  format(peak.corrected_wavenumber+spec.xshift, ".1f"),
                                                  format(peak.intensity*spec.yscale, ".3f"),
                                                  # (Labels.label2html(peak.get_label(use_gaussian_labels)) if html else Labels.label2tex(peak.get_label(use_gaussian_labels))),
                                                  peak.get_label(use_gaussian_labels),
                                                  peak.symmetries[0] if len(set(peak.symmetries)) == 1 else '',
                                                  peak.types[0] if len(set(peak.types)) == 1 else '']
                                peak_data_list += mode_data_list
                                table.append(peak_data_list)
                                line_added = True
                                peak_data_list = ["", "", "", "", ""]
                    peak_data_list = ["", "", "", ""]
            if not line_added:
                table.append(peak_data_list)

        for line in table:
            line += ["" for _ in range(len(line), len(table[0]))]
        return table


        # for maximum, max_clusters in self.super_clusters.items():  # super_clusters[maximum[1]][s.tag]
        #     for tag, cluster_list in max_clusters.items():
        #         spec = ([s for s in self.contributing_state_plots if s.tag == tag]+[None])[0]
        #         if spec is not None:
        #             for cluster in cluster_list:
        #                 for p, peak in enumerate(cluster.peaks):
        #                     print(tag, peak.__dict__)
        #                     if p == 0:
        #                         clusterinfolist = [format(int(maximum[0]), ">4"), format(cluster['y'], ".3f"),
        #                                            "", ""  # needs to be the exp
        #                                            ]
        #                         print(clusterinfolist)
                            #     if 'exp_peak_index' in cluster.keys():
                            #         clusterinfolist[2] = format(int(exp_spectrum[cluster['exp_peak_index']]['wavenumber']), ">4")
                            #         clusterinfolist[3] = format(exp_spectrum[cluster['exp_peak_index']]['intensity'], ".3f")
                            # else:
                            #     clusterinfolist = ["    " for c in clusterinfolist]
                            #
                            # clusterstring = "\t".join([str(n) for n in clusterinfolist]) + "\t"
                            # peakstring = "\t".join([format(n, ">4") for n in [int((peak['wavenumber'] + xshift)),
                            #                                                   # int((peak[wn_key]+xshift) * 10) / 10,
                            #                                                   int((peak['corrected_wavenumber'] + xshift))] +
                            #                         ([int((peak['anharmonic_wavenumber'] + xshift))] if anharm else [])] +
                            #                        [format(peak['intensity'], ".3f")] +
                            #                        [format(peak[label_key], ">24"),
                            #                         format(peak['symmetries'][0] if len(set(peak['symmetries'])) == 1 else "   ",
                            #                                "<5"),
                            #                         peak['types'][0] if len(set(peak['types'])) == 1 else (
                            #                             'Ring deformation' if set(peak['types']) == {'Ring deformation',
                            #                                                                          'C-C stretch'} else "")
                            #                         ])

                            # table_file.write(" " + clusterstring + peakstring + '\n')


