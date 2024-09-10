import math
from collections import Counter

import numpy as np
from scipy import signal

from utility.async_manager import AsyncManager
from utility.spectrum_plots import SpecPlotter
from utility.wavenumber_corrector import WavenumberCorrector
from utility.labels import Labels


_ELEMENT_NAMES = {'1': "H", '2': "He", '3': "Li", '4': "Be", '5': "B", '6': "C", '7': "N", '8': "O", '9': "F",
                      '10': "Ne", '11': "Na", '12': "Mg", '13': "Al", '14': "Si", '15': "P", '16': "S", '17': "Cl", '18': "Ar",
                      '19': "K", '20': "Ca", '21': "Sc", '22': "Ti", '23': "V", '24': "Cr", '25': "Mn", '26': "Fe", '27': "Ni", '28': "Co",
                      '29': "Cu", '30': "Zn", '31': "Ga", '32': "Ge", '33': "As", '34': "Se", '35': "Br", '36': "Kr", '37': "Rb", '38': "Sr",
                      '39': "Y", '40': "Zr", '41': "Nb", '42': "Mo", '43': "Tc", '44': "Ru", '45': "Rh", '46': "Pd", '47': "Ag", '48': "Cd",
                      '49': "In", '50': "Sn", '51': "Sb", '52': "Te", '53': "I", '54': "Xe", '55': "Cs", '56': "Ba", '57': "La", '58': "Ce",
                      '59': "Pr", '60': "Nd", '61': "Pm", '62': "Sm", '63': "Eu", '64': "Gd", '65': "Tb", '66': "Dy", '67': "Ho", '68': "Er",
                      '69': "Tm", '70': "Yb", '71': "Lu", '72': "Hf", '73': "Ta", '74': "W", '75': "Re", '76': "Os", '77': "Ir", '78': "Pt",
                      '79': "Au", '80': "Hg", '81': "Tl", '82': "Pb", '83': "Bi", '84': "Po", '85': "At", '86': "Rn", '87': "Fr", '88': "Ra",
                      '89': "Ac", '90': "Th", '91': "Pa", '92': "U", '93': "Np", '94': "Pu", '95': "Am", '96': "Cm", '97': "Bk", '98': "Cf",
                      '99': "Es", '100': "Fm"}


def format_float(f: float, target_len=10):
    res = f"{f: .6f}"
    return ' '*(target_len-len(res)) + res


class Geometry:
    def __init__(self):

        self.atoms = []
        self.x = []
        self.y = []
        self.z = []

        self._H_bonds = None
        self._other_bonds = None
        self._H_bond_matrix = None
        self.Bx = None
        self.By = None
        self.Bz = None

        self._ortho_dim = None

    def atom_distance(self, a, b, mode=None):
        """Compute distance between atoms #a and #b in this geometry"""
        if mode:
            res = (self.x[a] + mode[3 * a] - self.x[b] - mode[3 * b]) ** 2
            res += (self.y[a] + mode[3 * a + 1] - self.y[b] - mode[3 * b + 1]) ** 2
            res += (self.z[a] + mode[3 * a + 2] - self.z[b] - mode[3 * b + 2]) ** 2
        else:
            res = (self.x[a] - self.x[b]) ** 2
            res += (self.y[a] - self.y[b]) ** 2
            res += (self.z[a] - self.z[b]) ** 2
        return math.sqrt(res)

    def get_gaussian_geometry(self):
        res = ""
        for i, atom in enumerate(self.atoms):
            res += f" {_ELEMENT_NAMES.get(atom, str(atom))}        {format_float(self.x[i])}    {format_float(self.y[i])}    {format_float(self.z[i])}\r\n"
        return res

    def detect_bonds(self):
        self._H_bonds = []
        self._other_bonds = []
        self._H_bond_matrix = np.zeros((len([h for h in self.atoms if h == 'H']), len(self.atoms)), dtype=int)
        row_counter = 0
        for a, atom in enumerate(self.atoms):
            for b in range(a + 1, len(self.atoms)):
                btom = self.atoms[b]
                dist = self.atom_distance(a, b)
                if dist < 2:
                    if dist < 1.4 and atom == 'H' and btom != 'H':
                        self._H_bonds.append([b, a, dist])
                        self._H_bond_matrix[row_counter, a] = -1
                        self._H_bond_matrix[row_counter, b] = 1
                        row_counter += 1
                    elif dist < 1.4 and atom != 'H' and btom == 'H':
                        self._H_bonds.append([a, b, dist])
                        self._H_bond_matrix[row_counter, a] = 1
                        self._H_bond_matrix[row_counter, b] = -1
                        row_counter += 1
                    else:
                        self._other_bonds.append([a, b, dist])
        self.Bx = np.matmul(self._H_bond_matrix, self.x)
        self.By = np.matmul(self._H_bond_matrix, self.y)
        self.Bz = np.matmul(self._H_bond_matrix, self.z)
        lenBxyz = math.sqrt(np.dot(self.Bx, self.Bx) + np.dot(self.By, self.By) + np.dot(self.Bz, self.Bz))
        self.Bx /= lenBxyz
        self.By /= lenBxyz
        self.Bz /= lenBxyz

    def get_bonds(self):
        if self._H_bonds is None:
            self.detect_bonds()
        return self._H_bonds, self._other_bonds, self._H_bond_matrix

    def get_ortho_dim(self):
        if self._ortho_dim is None:
            return self._detect_ortho_dim()
        else:
            return self._ortho_dim

    # Return index of dimension orthogonal to the PAH plane.
    def _detect_ortho_dim(self):
        ortho_dim = -1
        for i, dim_coords in enumerate((self.x, self.y, self.z)):
            if max([abs(c) for c in dim_coords]) < 2:
                ortho_dim = i
        if ortho_dim == -1:
            print("Molecule isn't in a plane! Not detecting bends and wobbles.")
        self._ortho_dim = ortho_dim
        return ortho_dim

    def get_molecular_formula(self, charge=0):
        element_counts = Counter(self.atoms)
        formula_parts = []
        h_part = ""
        for element, count in sorted(element_counts.items()):
            if element == 'H':
                h_part = f"{element}{count if count > 1 else ''}"
            else:
                formula_parts.append(f"{element}{count if count > 1 else ''}")
        formula = ''.join(formula_parts) + h_part
        formula = formula.replace('0', '₀').replace('1', '₁').replace('2', '₂').replace('3', '₃').replace('4', '₄')\
            .replace('5', '₅').replace('6', '₆').replace('7', '₇').replace('8', '₈').replace('9', '₉')
        if type(charge) == int and charge != 0:
            if abs(charge) != 1:
                formula += str(abs(charge)).replace('0', '⁰').replace('1', '¹').replace('2', '²').replace('3', '³').replace('4', '⁴')\
                    .replace('5', '⁵').replace('6', '⁶').replace('7', '⁷').replace('8', '⁸').replace('9', '⁹')
            if charge > 0:
                formula += '⁺'
            else:
                formula += '⁻'
        return formula

    def get_fitted_vectors(self, mode_vectors=None, inp_scale=-1):
        """Return vectors scaled, shifted & permuted to fit into the vibration animation
        :returns x, y, z, scale"""
        sizes = [max(v) - min(v) for v in [self.x, self.y, self.z]]
        if inp_scale == -1:
            scale = 0.9/max(sizes)  # Maybe include vibration scale, to fit maximally vibrated molecule?
        else:
            scale = inp_scale
        vs = []
        middle = (max(self.x) + min(self.x))/2
        vs.append([0, [(c-middle)*scale for c in self.x]])
        middle = (max(self.y) + min(self.y))/2
        vs.append([1, [(c-middle)*scale for c in self.y]])
        middle = (max(self.z) + min(self.z))/2
        vs.append([2, [(c-middle)*scale for c in self.z]])
        vs.sort(key=lambda v: max(v[1])-min(v[1]), reverse=True)
        x, y, z = [v[1] for v in vs]
        mode_x, mode_y, mode_z = None, None, None
        if mode_vectors is not None:
            mult, mode = mode_vectors[0]
            mode_x, mode_y, mode_z = [[c*scale for c in [mode.vector_x, mode.vector_y, mode.vector_z][v[0]]] for v in vs]  #e.g. [2,0,1]
        return np.array(x), np.array(y), np.array(z), scale, np.array(mode_x), np.array(mode_y), np.array(mode_z)


class VibrationalMode:

    def __init__(self, index, wavenumber, IR, x, y, z, geometry):
        self.name = None
        self.wavenumber = wavenumber
        self.IR = IR
        self.vector_x = x
        self.vector_y = y
        self.vector_z = z
        self.vibration_properties = None
        self.vibration_type = None
        self.index = index
        self.gaussian_name = index+1
        self.classify(geometry)
        self.geometry = geometry  # only needed for the animation (dimensions are switched in main geom) - maybe just save some marker for the dimensions?

    def classify(self, geometry: Geometry):
        if self.wavenumber is None:
            print(f"VibrationalMode classify was called before its data was assigned!")
            return None

        h_stretches = []
        h_bends = []
        other_stretches = []
        h_bonds, other_bonds, H_matrix = geometry.get_bonds()
        
        bend = self.molecular_bend(geometry)
        for ch in h_bonds:
            h_stretches.append(math.fabs(self.bond_stretch(geometry, ch[0], ch[1])))  # todo: Could this be done as a 3N vector operation (dot product with h bonds displacement somehow)?
            h_bends.append(math.fabs(self.H_oop_bend(geometry, ch[0], ch[1])))  # Looks like you won't be a H oop bend if you're not a molecular bend (although there are mol bends that aren't very H bend heavy)
        for cc in other_bonds:
            other_stretches.append(math.fabs(self.bond_stretch(geometry, cc[0], cc[1])))

        self.vibration_properties = [p if p <= 1 else 1.0 for p in
                                     [
                                      # max([int(c * 100) for c in h_stretches]) / 100,  # *-H stretches (max bond length change)
                                      int(self.h_stretches(geometry, H_matrix)*100)/100,  # *-H stretches
                                      int(math.sqrt(sum(other_stretches) / len(other_stretches)) * 10000) / 10000,  # Other stretches
                                      # int((sum(other_stretches) / len(other_stretches)) * 10000) / 10000,  # Other stretches
                                      int(bend * 100) / 100]]  # Molecular Bends
                                      # max([int(c * 100) for c in h_bends]) / 100]  # H oop bends

        # print(self.vibration_properties[0], int(self.h_stretches(geometry, H_matrix)*100)/100,
        #       (self.vibration_properties[0] > 0.2) == (int(self.h_stretches(geometry, H_matrix)*100)/100 > 0.7))
        # print(self.vibration_properties)

        if self.vibration_properties[2] > 0.9:      # out-of-plane bends
            self.vibration_type = 'bends'  # key of WavenumberCorrector.correction_factors
        elif self.vibration_properties[0] > 0.7:    # *-H stretches (0.2 for old algo)
            self.vibration_type = 'H stretches'
        else:                                       # Other stretches and deformations
            self.vibration_type = 'others'

    def bond_stretch(self, geometry, a, b):
        bond_eq = [geometry.x[a] - geometry.x[b],
                   geometry.y[a] - geometry.y[b],
                   geometry.z[a] - geometry.z[b]]
        bond_st = [float(self.vector_x[a] - self.vector_x[b]),
                   float(self.vector_y[a] - self.vector_y[b]),
                   float(self.vector_z[a] - self.vector_z[b])]
        return bond_eq[0] * bond_st[0] + bond_eq[1] * bond_st[1] + bond_eq[2] * bond_st[2]

    def h_stretches(self, geometry, H_matrix):
        # print(np.absolute(geometry.By), np.dot(geometry.By, geometry.By))
        # print(np.matmul(H_matrix, self.vector_y), np.dot(np.matmul(H_matrix, self.vector_y), np.matmul(H_matrix, self.vector_y)))
        return np.dot(np.absolute(geometry.Bx), np.absolute(np.matmul(H_matrix, self.vector_x)))\
         + np.dot(np.absolute(geometry.By), np.absolute(np.matmul(H_matrix, self.vector_y)))\
         + np.dot(np.absolute(geometry.Bz), np.absolute(np.matmul(H_matrix, self.vector_z)))

    def molecular_bend(self, geometry: Geometry):
        b = 0

        dim_index = geometry.get_ortho_dim()
        if dim_index < 0:  # Not in a plane, assume no bend.
            return 0
        ortho_vector = (self.vector_x, self.vector_y, self.vector_z)[dim_index]
        # ortho_geom_coord = (geometry.x, geometry.y, geometry.z)[dim_index]

        for a, g in enumerate(geometry.atoms):
            b += float(ortho_vector[a]) ** 2  # amount to which the mode is leaving the plane.
        return b

    def H_oop_bend(self, geometry, a, b):
        dim_index = geometry.get_ortho_dim()
        if dim_index < 0:
            return 0
        bond_st = [float(self.vector_x[a] - self.vector_x[b]),
                   float(self.vector_y[a] - self.vector_y[b]),
                   float(self.vector_z[a] - self.vector_z[b])]
        return math.fabs(bond_st[dim_index])

    def H_wobble(self, geometry, a, b):
        dim_index = geometry.get_ortho_dim()
        if dim_index < 0:
            return 0

        bond_eq = [geometry.x[a] - geometry.x[b],
                   geometry.y[a] - geometry.y[b],
                   geometry.z[a] - geometry.z[b]]
        ortho_vec = [0, 0, 0]
        ortho_vec[dim_index] = 1
        wobble_vec = [bond_eq[1] * ortho_vec[2] - bond_eq[2] * ortho_vec[1],
                      bond_eq[2] * ortho_vec[0] - bond_eq[0] * ortho_vec[2],
                      bond_eq[0] * ortho_vec[1] - bond_eq[1] * ortho_vec[0]]
        bond_st = [float(self.vector_x[a] - self.vector_x[b]),
                   float(self.vector_y[a] - self.vector_y[b]),
                   float(self.vector_z[a] - self.vector_z[b])]

        return wobble_vec[0] * bond_st[0] + wobble_vec[1] * bond_st[1] + wobble_vec[2] * bond_st[2]


class ModeList:
    IR_order = ['AG', 'B1G', 'B2G', 'B3G', 'AU', 'B1U', 'B2U', 'B3U']
    instances = []
    _observers = []

    def __init__(self):
        self.IRs = {ir: [] for ir in self.IR_order}  # record of all vibrational modes by IR
        self.modes = {}
        ModeList.instances.append(self)

    def add_mode(self, wavenumber, sym, x, y, z, geometry):
        mode = VibrationalMode(len(list(self.modes.keys())), wavenumber, sym, x, y, z, geometry)
        self.modes[mode.gaussian_name] = mode
        if sym in self.IRs.keys():
            self.IRs[sym] = [mode] + self.IRs[sym]
        else:
            self.IRs[sym] = [mode]
            self.IR_order.append(sym)
            print(f"Added extra IR: {sym}")

    def determine_mode_names(self):
        for ml in self.IRs.values():
            ml.sort(key=lambda x: x.wavenumber, reverse=True)
        name = 1
        for key in self.IR_order:
            if key in self.IRs.keys():
                for mode in self.IRs[key]:
                    # if not mode.name == name:
                    #     print(key, mode.name, name)
                    mode.name = name
                    name += 1

    def update_IR_order(self, order):
        self.IR_order = order
        self.determine_mode_names()

    def get_wavenumbers(self, nr=-1):
        mode_name_list = list(self.modes.keys())
        end = len(mode_name_list) if nr == -1 else nr + 1
        return [self.modes[name].wavenumber for name in mode_name_list[:end]]

    def get_mode(self, gaussian_name: int):
        return self.modes.get(gaussian_name)

    @classmethod
    def add_observer(cls, observer):
        cls._observers.append(observer)

    @classmethod
    def get_symmetry_order(cls):
        return cls.IR_order.copy()

    @classmethod
    def reorder_symmemtry(cls, sym: str, up: bool):
        if sym not in cls.IR_order:
            return
        index = cls.IR_order.index(sym)
        if (up and index == 0) or (not up and index == len(cls.IR_order)-1):
            return
        if up:
            cls.IR_order[index], cls.IR_order[index - 1] = (cls.IR_order[index - 1], cls.IR_order[index])
        else:
            cls.IR_order[index], cls.IR_order[index + 1] = (cls.IR_order[index + 1], cls.IR_order[index])
        for mode_list in cls.instances:
            mode_list.determine_mode_names()


class FCPeak:
    def __init__(self, wavenumber, transition, intensity):
        self.wavenumber = wavenumber
        self.corrected_wavenumber = wavenumber
        self.transition = transition
        self.intensity = intensity
        self.types = []
        self.label = ""
        self.gaussian_label = ""
        self.symmetries = []

    def get_label(self, gaussian: bool):
        if gaussian:
            return self.gaussian_label
        else:
            return self.label


class Cluster:
    """Cluster of peaks forming a local maximum of a spectrum"""
    def __init__(self, x, y, y_max, peaks, is_emission):
        self.x = x
        self.y = y
        self.floor = y
        self.y_max = y_max
        self.is_emission = is_emission
        self.peaks = peaks
        self.peaks.sort(key=lambda p: float(p.intensity), reverse=True)
        self.label = ""
        self.width = 0
        self.height = 0
        self.to_be_positioned = False
        self.left_neighbour = None
        self.right_neighbour = None
        self.space = [0, 0] # space in wavenumbers to left and right to-be-positioned neighbours
        self.rel_x = 0  # shift in wavenumbers of label position w.r.t. peak position
        self.rel_y = 0
        self.on_top_of = []
        self.plot_x = 0  # own label position in the plot, dynamically updated as labels are moved
        self.plot_y = 0

    def filtered_peaks(self, yscale):
        if self.y * yscale < Labels.settings[self.is_emission]['peak intensity label threshold']:
            return []
        threshold = Labels.settings[self.is_emission]['stick label relative threshold'] * float(self.peaks[0].intensity) + \
                    Labels.settings[self.is_emission]['stick label absolute threshold']  # Threshold for counting as contributing to the peak
        return [p for p in self.peaks if p.intensity > threshold]

    def construct_label(self, gaussian: bool, yscale):
        if self.y * yscale < Labels.settings[self.is_emission]['peak intensity label threshold']:
            self.label = ""
            return ""
        threshold = Labels.settings[self.is_emission]['stick label relative threshold'] * float(self.peaks[0].intensity) + \
                    Labels.settings[self.is_emission]['stick label absolute threshold']  # Threshold for counting as contributing to the peak
        filtered_peak_labels = [p.get_label(gaussian) for p in self.peaks if p.intensity > threshold]
        self.label = "\n".join(filtered_peak_labels)
        return self.label

    def set_label_size(self, size):
        self.width = size[0]
        self.height = size[1]

    def get_plot_pos(self, state_plot, gap_height=0.001):
        x = self.x + state_plot.xshift
        y = state_plot.yshift + self.y * state_plot.yscale
        self.plot_x = x + self.rel_x
        self.plot_y = max(y + 0.05 + self.rel_y * state_plot.yscale, gap_height+max([0]+[c.get_roof() for c in self.on_top_of]))
        return (x, y), (self.plot_x, self.plot_y)  # should self.rel_y be adapted here?

    def set_plot_pos(self, pos, state_plot):
        (self.plot_x, self.plot_y) = pos
        x = self.x + state_plot.xshift  # peak position
        y = state_plot.yshift + self.y * state_plot.yscale
        self.rel_x = self.plot_x - x
        self.rel_y = (self.plot_y - y - 0.05) / state_plot.yscale
        return (x, y), (self.plot_x, self.plot_y)

    def get_roof(self):
        return self.plot_y + self.height


class FCSpectrum:
    xy_data_changed_notification = "Spectrum xy data changed"
    peaks_changed_notification = "Spectrum peaks changed"

    def __init__(self, is_emission, peaks, zero_zero_transition_energy, multiplicator):
        self.is_emission = is_emission
        self._observers = []
        self.peaks = peaks
        self.multiplicator = multiplicator
        self.x_min = 0
        self.x_max = 0
        self.zero_zero_transition_energy = zero_zero_transition_energy
        self.minima = None
        self.maxima = None
        key, self.x_data, self.y_data, self.mul2 = SpecPlotter.get_spectrum_array(self.peaks, self.is_emission)
        if len(self.x_data):
            self.x_min = min(self.x_data)
            self.x_max = max(self.x_data)
        for peak in self.peaks:
            peak.intensity /= self.mul2  # scale to match self.y_data scaling
        self.determine_label_clusters()
        SpecPlotter.add_observer(self)
        WavenumberCorrector.add_observer(self)
        ModeList.add_observer(self)
        self.x_data_arrays = {key: self.x_data}  # SpecPlotter key: array (save previously computed spectra)
        self.y_data_arrays = {key: self.y_data}  # SpecPlotter key: array (save previously computed spectra)
        self.vibrational_modes = None
        self.clusters = []
        self.clusters_in_placement_order = []

    def add_observer(self, observer):
        self._observers.append(observer)

    def remove_observer(self, observer):
        self._observers.remove(observer)

    def _notify_observers(self, message):
        for o in self._observers:
            o.update(message, self)

    def set_vibrational_modes(self, modes: ModeList):  # todo> subscribe to symmetry order updates; re-compute labels.
        self.vibrational_modes = modes
        self.peaks = WavenumberCorrector.compute_corrected_wavenumbers(self.is_emission, self.peaks, self.vibrational_modes)
        self.peaks = Labels.construct_labels(self.peaks, self.vibrational_modes, self.is_emission)
        key, self.x_data, self.y_data, self.mul2 = SpecPlotter.get_spectrum_array(self.peaks, self.is_emission)
        if len(self.x_data):
            self.x_min = min(self.x_data)
            self.x_max = max(self.x_data)
        for peak in self.peaks:
            peak.intensity /= self.mul2
        self.determine_label_clusters()
        self.get_symmetries_and_types_from_modes()
        self.x_data_arrays = {key: self.x_data}
        self.y_data_arrays = {key: self.y_data}
        self._notify_observers(FCSpectrum.xy_data_changed_notification)
        self._notify_observers(FCSpectrum.peaks_changed_notification)

    def get_symmetries_and_types_from_modes(self):
        if self.vibrational_modes is not None:
            for peak in self.peaks:
                peak.symmetries = []
                for t in peak.transition:
                    mode = self.vibrational_modes.get_mode(t[0])
                    if mode is not None:
                        peak.symmetries.append(mode.IR)
                        type = {'bends': "Bend", 'H stretches': "*-H stretch", "others": "Other"}[mode.vibration_type]
                        # type = ["*-H stretch", "Other", "Bend"][mode.vibration_properties.index(max(mode.vibration_properties))]
                        peak.types.append(type)

    def space_between_lines(self, to_be_placed, i):
        """bounds in wavenumbers (original xdata)"""
        if len(to_be_placed) == 1:
            bounds = [self.x_min, self.x_max]
        elif i == to_be_placed[0]:
            bounds = [self.x_min, self.clusters[to_be_placed[1]].x]
        elif i == to_be_placed[-1]:
            bounds = [self.clusters[to_be_placed[-2]].x, self.x_max]
        else:
            j = to_be_placed.index(i)
            bounds = [self.clusters[to_be_placed[j - 1]].x, self.clusters[to_be_placed[j + 1]].x]
        return [self.clusters[i].x - bounds[0] - self.clusters[i].width / 2, bounds[1] - self.clusters[i].x  - self.clusters[i].width / 2]

    def compute_space_between_unpositioned_neighbours(self):
        unpositioned_cluster = None
        for cluster in self.clusters:
            if cluster.to_be_positioned:
                unpositioned_cluster = cluster
                break
        if unpositioned_cluster is not None:
            unpositioned_cluster.space[0] = unpositioned_cluster.x - self.x_min
            while unpositioned_cluster.right_neighbour is not None:
                distance = unpositioned_cluster.right_neighbour.x - unpositioned_cluster.x
                unpositioned_cluster.right_neighbour.space[0] = distance - unpositioned_cluster.right_neighbour.width / 2
                unpositioned_cluster.space[1] = distance - unpositioned_cluster.width / 2
                unpositioned_cluster = unpositioned_cluster.right_neighbour
            unpositioned_cluster.space[1] = self.x_max - unpositioned_cluster.x

    def decide_label_positions(self, gap_width, gap_height):
        self.clusters_in_placement_order = []
        prev_unpositioned_cluster = None
        for cluster in self.clusters:
            cluster.rel_y = gap_height
            cluster.floor = cluster.y + cluster.rel_y
            cluster.to_be_positioned = len(cluster.label) > 0
            cluster.on_top_of = []
            if cluster.to_be_positioned:
                cluster.left_neighbour = prev_unpositioned_cluster
                if prev_unpositioned_cluster is not None:
                    prev_unpositioned_cluster.right_neighbour = cluster
                prev_unpositioned_cluster = cluster
        if prev_unpositioned_cluster is not None:
            prev_unpositioned_cluster.right_neighbour = None  # use neighbours to keep track of spacings

        to_be_positioned = [c for c in self.clusters if c.to_be_positioned]
        while to_be_positioned:
            self.compute_space_between_unpositioned_neighbours()
            placeables = [cluster for cluster in to_be_positioned if sum(cluster.space) >= 0
                          and (cluster.left_neighbour is None or cluster.left_neighbour.floor >= cluster.floor or sum(cluster.left_neighbour.space) < 0)
                          and (cluster.right_neighbour is None or cluster.right_neighbour.floor >= cluster.floor or sum(cluster.right_neighbour.space) < 0)]
            if not placeables:
                print("No label position found: ", [(c.label, sum(c.space),
                                                     None if c.left_neighbour is None else (c.left_neighbour.label, sum(c.left_neighbour.space), c.floor - c.left_neighbour.floor),
                                                     None if c.right_neighbour is None else (c.right_neighbour.label, sum(c.right_neighbour.space), c.floor - c.right_neighbour.floor)) for c in to_be_positioned if c not in placeables])
                break

            for cluster in placeables:

                # adjust horizontal spacing
                if sum(cluster.space) <= gap_width:
                    cluster.rel_x = cluster.space[1]/2 - cluster.space[0]/2  # kinda cramped; center it.
                elif cluster.space[0] < gap_width/2:
                    cluster.rel_x = gap_width/2 - cluster.space[0]  # nudge it away from left line
                elif cluster.space[1] < gap_width/2:
                    cluster.rel_x = cluster.space[1] - gap_width/2  # nudge it away from right line
                else:
                    cluster.rel_x = 0  # all good, keep it there.

                # adjust lift of neighbours
                if cluster.left_neighbour is not None:
                    cluster.left_neighbour.right_neighbour = cluster.right_neighbour
                    if cluster.space[0] - abs(cluster.rel_x) < cluster.left_neighbour.width + gap_width:
                        cluster.left_neighbour.floor = max(cluster.left_neighbour.floor, cluster.floor + cluster.height + gap_height)
                        cluster.left_neighbour.on_top_of.append(cluster)
                        cluster.left_neighbour.rel_y = cluster.left_neighbour.floor - cluster.left_neighbour.y
                if cluster.right_neighbour is not None:
                    cluster.right_neighbour.left_neighbour = cluster.left_neighbour
                    if cluster.space[1] - abs(cluster.rel_x) < cluster.right_neighbour.width + gap_width:
                        cluster.right_neighbour.floor = max(cluster.right_neighbour.floor, cluster.floor + cluster.height + gap_height)
                        cluster.right_neighbour.on_top_of.append(cluster)
                        cluster.right_neighbour.rel_y = cluster.right_neighbour.floor - cluster.right_neighbour.y

                cluster.to_be_positioned = False
                self.clusters_in_placement_order.append(cluster)

            to_be_positioned = [c for c in self.clusters if c.to_be_positioned]

    def get_wavenumbers(self, nr=-1):
        end = len(self.peaks) if nr == -1 else nr + 1
        return [peak.wavenumber for peak in self.peaks[:end]]

    def compute_min_max(self):
        """Return indices of local minima and maxima of self.ydata"""
        maxima, _ = list(signal.find_peaks(self.y_data))
        if len(maxima) == 0:
            return None, None
        mins, _ = list(signal.find_peaks([-y for y in self.y_data]))
        minima = [0]
        minima.extend(mins)
        minima.append(len(self.y_data) - 1)
        self.minima = minima
        self.maxima = maxima

    def get_clusters(self, in_placement_order=False):
        if in_placement_order:
            return self.clusters_in_placement_order
        else:
            return self.clusters

    def determine_label_clusters(self):
        self.compute_min_max()
        if self.minima is None or self.maxima is None:
            return
        peaks = self.peaks.copy()
        self.clusters = []
        peaks.sort(key=lambda pk: pk.corrected_wavenumber)

        j = 0  # maxima index
        p = 0  # peaks index

        for i in range(0, len(self.minima) - 1):
            cluster = []
            while self.maxima[j] < self.minima[i]:
                j += 1
                if j >= len(self.maxima):
                    break
            if j >= len(self.maxima):
                break

            while p < len(peaks) and peaks[p].corrected_wavenumber < self.x_data[self.minima[i]]:
                p += 1
            while p < len(peaks) and peaks[p].corrected_wavenumber < self.x_data[self.minima[i + 1]] and not peaks[p].get_label(False) == '':
                cluster.append(peaks[p])
                p += 1
            if cluster:
                self.clusters.append(Cluster(x=self.x_data[self.maxima[j]], y_max=max(self.y_data[max(0, self.maxima[j] - 8):min(self.maxima[j] + 8, len(self.y_data))]), y=self.y_data[self.maxima[j]], peaks=cluster, is_emission=self.is_emission))

        for i, cluster in enumerate(self.clusters):
            if i > 0:
                prev_cluster = self.clusters[i-1]
                prev_cluster.right_neighbour = cluster
                cluster.left_neighbour = prev_cluster

    def update(self, event, *args):
        """Automatically re-calculate y_data when active SpecPlotter instance changes."""
        if event == SpecPlotter.active_plotter_changed_notification:
            key = args[0]
            is_emission = args[1]
            if is_emission == self.is_emission:
                if key in self.y_data_arrays:
                    self.x_data = self.x_data_arrays[key]
                    self.y_data = self.y_data_arrays[key]
                else:
                    _, self.x_data, self.y_data, _ = SpecPlotter.get_spectrum_array(self.peaks, self.is_emission)
                    if len(self.x_data):
                        self.x_min = min(self.x_data)
                        self.x_max = max(self.x_data)
                    self.x_data_arrays[key] = self.x_data
                    self.y_data_arrays[key] = self.y_data
                self.determine_label_clusters()
                self._notify_observers(FCSpectrum.xy_data_changed_notification)
        elif event == WavenumberCorrector.correction_factors_changed_notification:
            if self.vibrational_modes is not None:
                self.peaks = WavenumberCorrector.compute_corrected_wavenumbers(self.is_emission, self.peaks, self.vibrational_modes)
                AsyncManager.submit_task(f"Recompute spectrum {self.zero_zero_transition_energy} {self.is_emission}",
                                         SpecPlotter.get_spectrum_array, self.peaks, self.is_emission,
                                         notification="xy data ready", observers=[self])
                if len(self.x_data):
                    self.x_min = min(self.x_data)
                    self.x_max = max(self.x_data)
        elif event == "xy data ready":
            (key, self.x_data, self.y_data, self.mul2) = args[0]
            for peak in self.peaks:
                peak.intensity /= self.mul2
            self.determine_label_clusters()
            self.x_data_arrays = {key: self.x_data}
            self.y_data_arrays = {key: self.y_data}
            self._notify_observers(FCSpectrum.peaks_changed_notification)
            self._notify_observers(FCSpectrum.xy_data_changed_notification)


