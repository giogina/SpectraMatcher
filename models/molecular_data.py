import math
from collections import Counter
from scipy import signal
from utility.spectrum_plots import SpecPlotter
from utility.wavenumber_corrector import WavenumberCorrector


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
        print(f"Geom: {self.atoms}, {self.x}")
        res = ""
        for i, atom in enumerate(self.atoms):
            res += f" {_ELEMENT_NAMES.get(atom, str(atom))}        {format_float(self.x[i])}    {format_float(self.y[i])}    {format_float(self.z[i])}\r\n"
        return res

    def detect_bonds(self):
        self._H_bonds = []
        self._other_bonds = []
        for a, atom in enumerate(self.atoms):
            for b in range(a + 1, len(self.atoms)):
                btom = self.atoms[b]
                dist = self.atom_distance(a, b)
                if dist < 2:
                    if dist < 1.4 and atom == 'H' and btom != 'H':
                        self._H_bonds.append([b, a, dist])
                    elif dist < 1.4 and atom != 'H' and btom == 'H':
                        self._H_bonds.append([a, b, dist])
                    else:
                        self._other_bonds.append([a, b, dist])

    def get_bonds(self):
        if self._H_bonds is None:
            self.detect_bonds()
        return self._H_bonds, self._other_bonds

    def get_ortho_dim(self):
        if self._ortho_dim is None:
            return self._detect_ortho_dim()
        else:
            return self._ortho_dim

    # Return index of dimension orthogonal to the PAH plane.
    def _detect_ortho_dim(self):
        ortho_dim = -1
        for i, dim_coords in enumerate((self.x, self.y, self.z)):
            if max([abs(c) for c in dim_coords]) < 1:
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

    def classify(self, geometry: Geometry):
        if self.wavenumber is None:
            print(f"VibrationalMode classify was called before its data was assigned!")
            return None

        h_stretches = []
        other_stretches = []
        h_bonds, other_bonds = geometry.get_bonds()
        
        bend = self.molecular_bend(geometry)
        for ch in h_bonds:
            h_stretches.append(math.fabs(self.bond_stretch(geometry, ch[0], ch[1])))
        for cc in other_bonds:
            other_stretches.append(math.fabs(self.bond_stretch(geometry, cc[0], cc[1])))

        self.vibration_properties = [p if p <= 1 else 1.0 for p in
                                     [max([int(c * 100) for c in h_stretches]) / 100,  # *-H stretches
                                      int(math.sqrt(sum(other_stretches) / len(other_stretches)) * 10000) / 10000,  # Other stretches
                                      int(bend * 100) / 100]]  # Bends

        if self.vibration_properties[2] > 0.9:      # out-of-plane bends
            self.vibration_type = "Bend"
        elif self.vibration_properties[0] > 0.2:    # *-H stretches
            self.vibration_type = "H stretch"
        else:                                       # Other stretches and deformations
            self.vibration_type = "Other"

    def bond_stretch(self,geometry, a, b):
        bond_eq = [geometry.x[a] - geometry.x[b],
                   geometry.y[a] - geometry.y[b],
                   geometry.z[a] - geometry.z[b]]
        bond_st = [float(self.vector_x[a] - self.vector_x[b]),
                   float(self.vector_y[a] - self.vector_y[b]),
                   float(self.vector_z[a] - self.vector_z[b])]
        return bond_eq[0] * bond_st[0] + bond_eq[1] * bond_st[1] + bond_eq[2] * bond_st[2]

    def molecular_bend(self, geometry: Geometry):
        b = 0

        dim_index = geometry.get_ortho_dim()
        if dim_index < 0:  # Not in a plane, assume no bend.
            return 0
        ortho_vector = (self.vector_x, self.vector_y, self.vector_z)[dim_index]
        ortho_geom_coord = (geometry.x, geometry.y, geometry.z)[dim_index]

        for a, g in enumerate(geometry.atoms):
            b += float(ortho_vector[a]-ortho_geom_coord[a]) ** 2  # amount to which the mode is leaving the plane.
        return b

    def H_wobble(self, a, b, geometry: Geometry):

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
    IR_order = ['AG', 'B1G', 'B2G', 'B3G', 'AU', 'B1U', 'B2U', 'B3U']  # TODO> Persist this order in settings

    def __init__(self):
        self.IRs = {ir: [] for ir in self.IR_order}  # record of all vibrational modes by IR
        self.modes = {}

    def add_mode(self, wavenumber, sym, x, y, z, geometry):
        mode = VibrationalMode(len(list(self.modes.keys())), wavenumber, sym, x, y, z, geometry)
        self.modes[mode.gaussian_name] = mode
        if sym in self.IRs.keys():
            self.IRs[sym] = [mode] + self.IRs[sym]  # TODO> allow re-ordering afterwards for all IRs within the project
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


class FCPeak:
    def __init__(self, wavenumber, transition, intensity):
        self.wavenumber = wavenumber
        self.corrected_wavenumber = wavenumber
        self.transition = transition
        self.intensity = intensity


class FCSpectrum:
    xy_data_changed_notification = "Spectrum xy data changed"
    def __init__(self, is_emission, peaks, zero_zero_transition_energy, multiplicator):
        self.is_emission = is_emission
        self._observers = []
        self.peaks = peaks
        self.multiplicator = multiplicator
        self.zero_zero_transition_energy = zero_zero_transition_energy
        key, self.x_data, self.y_data, self.mul2 = SpecPlotter.get_spectrum_array(self.peaks, self.is_emission)
        for peak in self.peaks:
            peak.intensity /= self.mul2  # scale to match self.y_data scaling
        self.minima, self.maxima = self.compute_min_max()
        SpecPlotter.add_observer(self)
        WavenumberCorrector.add_observer(self)
        self.x_data_arrays = {key: self.x_data}  # SpecPlotter key: array (save previously computed spectra)
        self.y_data_arrays = {key: self.y_data}  # SpecPlotter key: array (save previously computed spectra)
        self.mode_list = None

    def add_observer(self, observer):
        self._observers.append(observer)

    def remove_observer(self, observer):
        self._observers.remove(observer)

    def _notify_observers(self, message):
        for o in self._observers:
            o.update(message, self)

    def set_vibrational_modes(self, modes: ModeList):
        print(f"Vibrational modes set: {'emission' if self.is_emission else 'excitation'}")
        self.mode_list = modes

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
        print(minima, maxima)
        return minima, maxima

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
                    self.x_data_arrays[key] = self.x_data
                    self.y_data_arrays[key] = self.y_data
                self.minima, self.maxima = self.compute_min_max()
                self._notify_observers(FCSpectrum.xy_data_changed_notification)
        elif event == WavenumberCorrector.correction_factors_changed_notification:
            self.peaks = WavenumberCorrector.compute_corrected_wavenumbers(self.peaks)
            key, self.x_data, self.y_data, self.mul2 = SpecPlotter.get_spectrum_array(self.peaks, self.is_emission)
            for peak in self.peaks:
                peak.intensity /= self.mul2
            self.minima, self.maxima = self.compute_min_max()
            self.x_data_arrays = {key: self.x_data}
            self.y_data_arrays = {key: self.y_data}
            self._notify_observers(FCSpectrum.xy_data_changed_notification)




