import math
from collections import Counter

import numpy as np
# from scipy import signal

from utility.async_manager import AsyncManager
from utility.spectrum_plots import SpecPlotter
from utility.wavenumber_corrector import WavenumberCorrector
from utility.labels import Labels
from utility import signal


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

_ELEMENT_MASSES = {"H": 1.007, "He": 3.999, "Li": 6.934, "Be": 9.004, "B": 10.800, "C": 12.000, "N": 13.994, "O": 15.984, "F": 18.981, "Ne": 20.162, "Na": 22.969, "Mg": 24.283, "Al": 26.957, "Si": 28.059, "P": 30.946, "S": 32.031, "Cl": 35.418, "Ar": 39.913, "K": 39.062, "Ca": 40.041, "Sc": 44.915, "Ti": 47.823, "V": 50.895, "Cr": 51.948, "Mn": 54.888, "Fe": 55.794, "Co": 58.879, "Ni": 58.639, "Cu": 63.488, "Zn": 65.320, "Ga": 69.659, "Ge": 72.563, "As": 74.853, "Se": 78.899, "Br": 79.831, "Kr": 83.721, "Rb": 85.390, "Sr": 87.540, "Y": 88.825, "Zr": 91.138, "Nb": 92.821, "Mo": 95.862, "Tc": 97.910, "Ru": 100.977, "Rh": 102.816, "Pd": 106.323, "Ag": 107.771, "Cd": 112.307, "In": 114.715, "Sn": 118.601, "Sb": 121.648, "Te": 127.483, "I": 126.784, "Xe": 131.170, "Cs": 132.788, "Ba": 137.204, "La": 138.783, "Ce": 139.992, "Pr": 140.781, "Nd": 144.108, "Pm": 145.866, "Sm": 150.222, "Eu": 151.821, "Gd": 157.106, "Tb": 158.784, "Dy": 162.351, "Ho": 164.779, "Er": 167.107, "Tm": 168.775, "Yb": 172.892, "Lu": 174.810, "Hf": 178.327, "Ta": 180.784, "W": 183.672, "Re": 186.039, "Os": 190.056, "Ir": 192.044, "Pt": 194.901, "Au": 196.790, "Hg": 200.406, "Tl": 204.193, "Pb": 207.010, "Bi": 208.789}


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
        self._center_of_mass = None

    def center_of_mass(self):
        if self._center_of_mass is not None:
            return self._center_of_mass
        comx = 0
        comy = 0
        comz = 0
        full_mass = 0
        for a, x, y, z in zip(self.atoms, self.x, self.y, self.z):
            mass = _ELEMENT_MASSES.get(a, 0)
            comx += mass*x
            comy += mass*y
            comz += mass*z
            full_mass += mass
        self._center_of_mass = [comx/full_mass, comy/full_mass, comz/full_mass]
        return self._center_of_mass

    def to_numpy_coords(self):
        return np.stack([np.array(self.x), np.array(self.y), np.array(self.z)], axis=1)

    def align(self, other_geom):
        ref_coords = self.to_numpy_coords()
        mov_coords = other_geom.to_numpy_coords()
        ref_COM = self.center_of_mass()
        mov_COM = other_geom.center_of_mass()
        masses = np.array([_ELEMENT_MASSES[a] for a in self.atoms])
        ref_centered = (ref_coords - ref_COM) * np.sqrt(masses[:, np.newaxis])
        mov_centered = (mov_coords - mov_COM) * np.sqrt(masses[:, np.newaxis])

        H = mov_centered.T @ ref_centered
        U, S, Vt = np.linalg.svd(H)
        R = Vt.T @ U.T
        if np.linalg.det(R) < 0:
            Vt[-1, :] *= -1
            R = Vt.T @ U.T
        R = np.round(R / 1e-12) * 1e-12

        rotated_coords = ((mov_coords - mov_COM) @ R.T)+ref_COM
        rotated = Geometry()
        rotated.atoms = self.atoms
        rotated.x = [round(c*1e10)/1e10 for c in rotated_coords[:, 0].tolist()]
        rotated.y = [round(c*1e10)/1e10 for c in rotated_coords[:, 1].tolist()]
        rotated.z = [round(c*1e10)/1e10 for c in rotated_coords[:, 2].tolist()]
        return rotated

    def distance(self, other_geom):
        ref_coords = self.to_numpy_coords()
        other_coords = other_geom.to_numpy_coords()
        masses = np.array([_ELEMENT_MASSES[a] for a in self.atoms])
        mass_weighted_shift = (other_coords-ref_coords) * np.sqrt(masses[:, np.newaxis])
        return mass_weighted_shift.flatten()
        # return (other_coords-ref_coords).flatten()

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

    def __init__(self, index, wavenumber, IR, reduced_mass, x, y, z, geometry):
        self.name = None
        self.wavenumber = wavenumber
        self.IR = IR
        self.reduced_mass = reduced_mass
        self.q_turnaround = self.compute_potential_width()  # distance in (mass-weighted-normalized) normal coords q at which potential == E(v=0)
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
            h_stretches.append(math.fabs(self.bond_stretch(geometry, ch[0], ch[1])))
            h_bends.append(math.fabs(self.H_oop_bend(geometry, ch[0], ch[1])))  # Looks like you won't be a H oop bend if you're not a molecular bend (although there are mol bends that aren't very H bend heavy)
        for cc in other_bonds:
            other_stretches.append(math.fabs(self.bond_stretch(geometry, cc[0], cc[1])))

        self.vibration_properties = [p if p <= 1 else 1.0 for p in
                                     [
                                      max([int(c * 100) for c in h_stretches]) / 100,  # *-H stretches (max bond length change)
                                      # int(self.h_stretches(geometry, H_matrix)*100)/100,  # *-H stretches
                                      int(math.sqrt(sum(other_stretches) / len(other_stretches)) * 10000) / 10000,  # Other stretches
                                      # int((sum(other_stretches) / len(other_stretches)) * 10000) / 10000,  # Other stretches
                                      int(bend * 100) / 100]]  # Molecular Bends
                                      # max([int(c * 100) for c in h_bends]) / 100]  # H oop bends

        if self.vibration_properties[2] > 0.9:      # out-of-plane bends
            self.vibration_type = 'bends'  # key of WavenumberCorrector.correction_factors
        elif self.vibration_properties[0] > 0.2:    # *-H stretches (0.7 for second line algo)
            self.vibration_type = 'H stretches'
        else:                                       # Other stretches and deformations
            self.vibration_type = 'others'

    def compute_potential_width(self):
        """ Returns coordinate q_t of (classical) turnaround point of the v=0 vibration along the mass-weighted-*normalized* normal mode vector. """
        return 5.806484163/math.sqrt(abs(self.wavenumber))

    # Eh := 4.3597447222071e-18*(kg*m^2/s^2)/Hartree;
    # IDalton := 1.66053906660e-27*kg/amu;
    # c := 2.99792458e8*m/s;
    # IDyne := 1e-5*kg*m/s^2/Dyne;
    # IAng :=1e-10*m/Angstrom;
    #
    # wavenumber = simplify(omega/sqrt(1*amu)/sqrt(IDalton)/IAng*sqrt(Eh)/c/(100*cm/m)/2/Pi,symbolic);
    # omega = solve(%,omega);  # omega = 0.3676161564e-3*wavenumber*sqrt(Hartree)*cm/Angstrom
    #
    # nu := wavenumber*c*(100*cm/m);
    # dE := h*nu;
    # dEau := dE/Eh;
    # 1/2*omega^2*qt^2 = dEau/2;
    # qt = [solve(%,qt)][1];
    # simplify(eval(%,omega = 0.3676161564e-3*wavenumber*sqrt(Hartree)*cm/Angstrom),symbolic);  # qt = 5.806484163*Angstrom/(sqrt(wavenumber*cm))

    def mass_weighted_xyz(self):
        xyz = np.stack([np.array(self.vector_x), np.array(self.vector_y), np.array(self.vector_z)], axis=1)
        masses = np.array([_ELEMENT_MASSES[a] for a in self.geometry.atoms])
        com = np.sum(xyz * masses[:, np.newaxis], axis=0)/np.sum(masses)
        xyz -= com
        mass_weighted_xyz = xyz * np.sqrt(masses[:, np.newaxis])
        return mass_weighted_xyz

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
    IR_order = []  # coupled to project._data["IR order"]
    instances = []
    _observers = []

    def __init__(self):
        self.IRs = {ir: [] for ir in self.IR_order}  # record of all vibrational modes by IR
        self.modes = {}
        ModeList.instances.append(self)

    def add_mode(self, wavenumber, sym, reduced_mass, x, y, z, geometry):
        mode = VibrationalMode(len(list(self.modes.keys())), wavenumber, sym, reduced_mass, x, y, z, geometry)
        self.modes[mode.gaussian_name] = mode
        if sym in self.IRs.keys():
            self.IRs[sym] = [mode] + self.IRs[sym]
        elif len(sym) > 0:
            self.IRs[sym] = [mode]
            self.IR_order.append(sym)
            try:
                self.IR_order.sort(key=self.irreps_sort_key)
            except Exception as e:
                print(f"Problem sorting IRs: {e}")
            print(f"Added extra IR: {sym}")

    def irreps_sort_key(self, sym: str):
        if len(sym) == 0:
            return 2, "x"
        elif '?' in sym:
            return 1, sym  # all questionmarked ones at the end, in alphabetical order
        else:
            head = sym[0]
            try:
                number = int(sym[1])
                tail = sym[2:]
            except Exception:
                number = 0  # no number present in irrep string
                tail = sym[1:]
            return 0, tail, head, number

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
    def _notify_observers(cls, message):
        for obs in cls._observers:
            obs.update(message, cls)

    @classmethod
    def get_symmetry_order(cls):
        return cls.IR_order.copy()

    @classmethod
    def reorder_symmetry(cls, sym: str, up: bool):
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
        cls._notify_observers("IR order updated")

    def shift_vector(self, initial_geom: Geometry):  # TODO: Call this from file manager option (rather than state)
        shift_vector = []
        if self.modes == {}:
            return 0
        final_geom = self.get_mode(1).geometry
        initial_geom = final_geom.align(initial_geom)
        distance = final_geom.distance(initial_geom)  # mass weighted distance
        #sqrt_masses = np.sqrt(np.array([_ELEMENT_MASSES.get(a) for a in final_geom.atoms]))
        acc_shift = 0
        for mode in self.modes.values():

            mw_mode_vector = mode.mass_weighted_xyz()
            vec_abs = np.sqrt(np.dot(mw_mode_vector.flatten(), mw_mode_vector.flatten()))
            shift = np.dot(mw_mode_vector.flatten() / vec_abs, distance)  # in terms of mass-normalized displacement vector
            displacement_factor = abs(shift/mode.q_turnaround)
            acc_shift += shift**2

            if abs(displacement_factor) > 0.00:
                print(mode.gaussian_name, mode.IR, shift, f"{displacement_factor:.5f}", mode.vibration_type, mode.wavenumber)
            shift_vector.append(shift)
            # if False:
            # if displacement_factor > 0.1:
            # if mode.IR == "A'":
            if mode.gaussian_name == 1:
                # print(f"Mode {mode.gaussian_name} has a large displacement factor of {displacement_factor}. Creating PES determination input files.")
                # print(f"Mass-normalized displacement
                print(mode.wavenumber)
                print('atoms = '+str(mode.geometry.atoms))
                #
                print('ground_x = '+str(mode.geometry.x))
                print('ground_y = '+str(mode.geometry.y))
                print('ground_z = '+str(mode.geometry.z))
                print(f'\nif mode == {mode.gaussian_name}:')
                print('    Dx = ['+', '.join(map(str, mode.vector_x / vec_abs))+']')
                print('    Dy = ['+', '.join(map(str, mode.vector_y / vec_abs))+']')
                print('    Dz = ['+', '.join(map(str, mode.vector_z / vec_abs))+']')
                # for q in np.linspace(-1.5*shift, 1.5*shift, 30):

                # print(vec_abs, vec_abs**2, mode.reduced_mass)
                if False:
                # for q in np.linspace(-0.5, 0.5, 11):
                    x = np.array(final_geom.x) + q * dx
                    y = np.array(final_geom.y) + q * dy
                    z = np.array(final_geom.z) + q * dz
                    # print( np.sqrt(np.dot(np.array(mode.vector_x),np.array(mode.vector_x))+np.dot(np.array(mode.vector_y),np.array(mode.vector_y))+np.dot(np.array(mode.vector_z),np.array(mode.vector_z))))
                    # av=0
                    # for i, x in enumerate(mode.vector_x):
                    #     av +=mode.vector_x[i]**2* _ELEMENT_MASSES[final_geom.atoms[i]]
                    #     av +=mode.vector_y[i]**2* _ELEMENT_MASSES[final_geom.atoms[i]]
                    #     av +=mode.vector_z[i]**2* _ELEMENT_MASSES[final_geom.atoms[i]]
                    # print(np.sqrt(av))

                    disp_int = int(round(q * 1000))
                    disp_str = f"d{disp_int:+04d}"  # includes sign, e.g., +020, -120
                    gjf = f"%NProcShared=8\n%mem=26GB\n%chk=pes_mode{mode.gaussian_name}_d{disp_str}.chk\n#p b3lyp/cc-pvdz td=(root=1) nosymm int=ultrafine scf=conver=10\n\n1D PES scan mode {mode.gaussian_name}, displacement {disp_str}\n\n0 1\n"
                    # gjf = f"%NProcShared=8\n%mem=26GB\n%chk=pes_mode{mode.gaussian_name}_d{disp_str}.chk\n#p b3lyp/cc-pvdz td=(root=1) nosymm\n\n1D PES scan mode {mode.gaussian_name}, displacement {disp_str}\n\n0 1\n"
                    for i, atom in enumerate(final_geom.atoms):
                        gjf += f" {_ELEMENT_NAMES.get(atom, str(atom))}        {format_float(x[i])}    {format_float(y[i])}    {format_float(z[i])}\n"
                    gjf += "\n\n\n"
                    pes_dir = f"/home/giogina/Downloads/quinoline/PES/{mode.gaussian_name}/"
                    import os
                    os.makedirs(pes_dir, exist_ok=True)
                    print(pes_dir)
                    filename = f"mode_{mode.gaussian_name}_{disp_str}.gjf"
                    filepath = os.path.join(pes_dir, filename)
                    with open(filepath, 'w') as f:
                        f.write(gjf)
                    print("Written to ", filepath)
        print("Shift vector length: ", np.sqrt(acc_shift))

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
        self.peaks = peaks
        self.multiplicator = multiplicator
        self.x_min = 0
        self.x_max = 0
        self.zero_zero_transition_energy = zero_zero_transition_energy
        self.minima = None
        self.maxima = None
        self._observers = []
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

    def set_vibrational_modes(self, modes: ModeList):
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
                        type = {'bends': "Bend", 'H stretches': "X-H stretch", "others": "Other"}[mode.vibration_type]
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
        self.minima, self.maxima = signal.local_extrema(self.y_data)

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
        elif event == "IR order updated":
            if self.peaks is not None and self.vibrational_modes is not None:
                self.peaks = Labels.construct_labels(self.peaks, self.vibrational_modes, self.is_emission)
                self.determine_label_clusters()



