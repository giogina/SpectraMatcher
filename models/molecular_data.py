import math
from collections import Counter

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
            self._detect_ortho_dim()
        else:
            return self._ortho_dim

    # Return index of dimension orthogonal to the PAH plane.
    def _detect_ortho_dim(self):
        ortho_dim = -1
        for i, dim_coords in enumerate((self.x, self.y, self.z)):
            if max(dim_coords) < 1:
                ortho_dim = i
        if not ortho_dim:
            print("Molecule isn't in a plane! Not detecting bends and wobbles.")

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

# TODO>
#  add_mode: adds mode (vs negfreq), returns copy of changed geometry


class VibrationalMode:
    def __init__(self, index):
        self.name = None
        self.wavenumber = None
        self.IR = None
        self.vector_x = []
        self.vector_y = []
        self.vector_z = []
        self.vibration_properties = None
        self.vibration_type = None
        self.index = index
        self.gaussian_name = index+1

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


class FCPeak:
    def __init__(self, wavenumber, transition, intensity):
        self.wavenumber = wavenumber
        self.transition = transition
        self.intensity = intensity


class FCSpectrum:
    def __init__(self, is_emission, peaks, zero_zero_transition_energy, multiplicator):
        self.is_emission = is_emission
        self.peaks = peaks
        self.zero_zero_transition_energy = zero_zero_transition_energy
        self.multiplicator = multiplicator


