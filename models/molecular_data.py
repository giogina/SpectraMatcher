import math


class Geometry:
    atoms = []
    x = []
    y = []
    z = []

    _H_bonds = None
    _other_bonds = None

    _ortho_dim = None

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
# TODO> def print_geometry: Returns .gjf-usable string of geometry.
#  add_mode: adds mode (vs negfreq), returns copy of changed geometry
#  Provide access to all those in right-click menu of file explorer


class VibrationalMode:
    index = None
    name = None
    gaussian_name = None
    wavenumber = None
    IR = None
    vector_x = []
    vector_y = []
    vector_z = []

    vibration_properties = None
    vibration_type = None

    def __init__(self, index):
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
    wavenumber = None
    transition = None
    intensity = None


class FCSpectrum:
    is_emission = True
    peaks = []
    zero_zero_transition_energy = 0
    multiplicator = 1


