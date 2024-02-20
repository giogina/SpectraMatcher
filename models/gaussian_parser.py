import re
from models.molecular_data import Geometry, VibrationalMode, FCPeak, FCSpectrum


class GaussianParser:
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

    def __init__(self):
        pass

    @staticmethod
    def get_last_geometry(log_file):
        """Parses log file, returns Geometry object (from last "standard orientation") or None"""
        last_geom_start = None
        with open(log_file, 'r') as f:
            lines = f.readlines()
        for i in range(-1, -len(lines) - 1, -1):
            if lines[i].strip() == "Standard orientation:":
                last_geom_start = i
                break
        if not isinstance(last_geom_start, int):
            return None

        geometry = Geometry()

        for i in range(last_geom_start, len(lines)):
            line = lines[i]
            coord_match = re.findall(r'\s+([-\d.]+)', line)
            if len(coord_match) == 6:
                geometry.atoms.append(GaussianParser._ELEMENT_NAMES.get(str(coord_match[1]), ""))
                geometry.x.append(float(coord_match[3]))
                geometry.y.append(float(coord_match[4]))
                geometry.z.append(float(coord_match[5]))
            elif line.startswith(" Number") or line.startswith(" Center") or line.startswith(" ---"):
                continue
            else:
                break
        return geometry

    @staticmethod
    def get_vibrational_modes(log_file):
        """Parses log file, returns list of VibrationalMode objects or None"""
        frequencies = []
        normal_mode_vectors = []
        new_normal_mode_vectors = []
        read_atoms = False
        syms = []
        hpmodes_start = None
        lpmodes_start = None

        geometry = GaussianParser.get_last_geometry(log_file)

        with open(log_file, 'r') as f:
            lines = f.readlines()

        for l, line in enumerate(lines):
            if line.strip().startswith('Frequencies --'):
                if line.strip().startswith('Frequencies ---'):
                    if hpmodes_start == None:
                        hpmodes_start = l
                        break
                else:
                    if lpmodes_start == None:
                        lpmodes_start = l
                        break
        if hpmodes_start is not None:   # Read high-precision modes
            for l in range(hpmodes_start, len(lines)):
                line = lines[l]
                if line.strip().startswith('Frequencies ---'):  # Next set of modes starts!
                    syms.extend(re.findall(r'([a-zA-Z0-9]+)', lines[l - 1]))
                    new_freqs = [float(n) for n in re.findall(r'\s+([-\d.]+)', line.split("---")[1])]
                    frequencies.extend(new_freqs)
                    if new_normal_mode_vectors:
                        normal_mode_vectors.extend(new_normal_mode_vectors)
                    new_normal_mode_vectors = [[] for n in new_freqs]
                    continue
                if line.strip() == "Coord Atom Element:":
                    read_atoms = True
                    continue
                if read_atoms:
                    atom_match = re.findall(r'\s+([-\d.]+)', line)
                    if len(atom_match) == len(new_normal_mode_vectors) + 3:
                        for i in range(0, len(new_normal_mode_vectors)):
                            new_normal_mode_vectors[i].append(atom_match[i + 3])
                    else:
                        read_atoms = False
                if l == lpmodes_start:
                    break
            normal_mode_vectors.extend(new_normal_mode_vectors)

        elif lpmodes_start is not None:  # Read low-precision modes
            for l in range(hpmodes_start, len(lines)):
                line = lines[l]
                if line.strip().startswith('Frequencies --'):  # Next set of modes starts!
                    syms.extend(re.findall(r'([a-zA-Z0-9]+)', lines[l - 1]))
                    new_freqs = [float(n) for n in re.findall(r'\s+([-\d.]+)', line.split("--")[1])]
                    frequencies.extend(new_freqs)
                    if new_normal_mode_vectors:
                        normal_mode_vectors.extend(new_normal_mode_vectors)
                    new_normal_mode_vectors = [[] for n in new_freqs]
                    continue
                if line.strip().startswith("Atom  AN"):
                    read_atoms = True
                    continue
                if read_atoms:
                    atom_match = re.findall(r'\s+([-\d.]+)', line)
                    if len(atom_match) == len(new_normal_mode_vectors) * 3 + 2:
                        for i in range(0, len(new_normal_mode_vectors)):
                            new_normal_mode_vectors[i].append(atom_match[3*i + 2])
                            new_normal_mode_vectors[i].append(atom_match[3*i + 3])
                            new_normal_mode_vectors[i].append(atom_match[3*i + 4])
                    else:
                        read_atoms = False
                if line.strip().startswith("------------"):
                    break

            mode_list = []
            for i, vector in enumerate(normal_mode_vectors):
                new_mode = VibrationalMode(len(mode_list))
                new_mode.wavenumber = frequencies[i]
                new_mode.IR = syms[i]
                for n, c in enumerate(vector):
                    if n % 3 == 0:
                        new_mode.vector_x.append(c)
                    elif n % 3 == 1:
                        new_mode.vector_y.append(c)
                    elif n % 3 == 2:
                        new_mode.vector_z.append(c)
                new_mode.classify(geometry)
                mode_list.append(new_mode)

            return GaussianParser._name_modes_by_IR(mode_list)
        else:
            print(f"No frequencies found in {log_file}!")
            return None

    @staticmethod
    def _name_modes_by_IR(mode_list):
        """Figure out mode names according to IR sorting"""  # TODO> Compare that email, clearly document

        IRs = {'AG': [],
               'B1G': [],
               'B2G': [],
               'B3G': [],
               'AU': [],
               'B1U': [],
               'B2U': [],
               'B3U': []
               }
        for mode in mode_list:
            if mode.IR in IRs.keys():
                IRs[mode.IR].append(mode.index)  # TODO> allow re-ordering afterwards for all IRs within the project
            else:
                IRs[mode.IR] = [mode.index]
                print(f"Added extra IR: {mode.IR}")

        names_inv = []  # modes in order of name
        for ir in IRs.keys():
            IRs[ir].reverse()
            names_inv.extend(IRs[ir])
        for n, m in enumerate(names_inv):
            mode_list[m].name = n + 1

        return mode_list

    @staticmethod
    def get_anharmonic_levels(log_file):
        read = ''
        anharmonic_levels = []
        with open(log_file, 'r') as f:
            lines = f.readlines()
            for l, line in enumerate(lines):
                if re.search(r'Fundamental Bands', line):
                    read = 'fundamental'
                    continue
                match = re.search(r'Overtones', line)
                if match:
                    read = 'overtone'
                    continue
                if re.search(r'Combination Bands', line):
                    read = 'combination'
                    continue
                if read and re.search(r'=======', line):
                    return anharmonic_levels
                if read:
                    match = re.findall(r'\s+([-\d.(\d)]+)', line)
                    if len(match) > 2:
                        modes = [[int(s) for s in m[0:-1].split("(")] for m in match if m.endswith(")")]
                        modes.reverse()
                        anharmonic_levels.append({
                            'modes': modes,
                            'type': read,
                            'harmonic': float(list(match)[len(modes)]),
                            'anharmonic': float(list(match)[len(modes) + 1])
                        })

    @staticmethod
    def get_FC_spectrum(log_file, is_emission: bool):
        wavenumbers = []
        transitions = []
        intensities = []
        read_transs = False
        peaks = []
        zero = 0
        with open(log_file, 'r') as f:
            lines = f.readlines()
        for l, line in enumerate(lines):
            if re.search(r'\sInformation on Transitions\s', line):
                read_transs = True
                continue
            if re.search(r'Energy of the 0-0 transition', line):
                zero = float(line.split(":")[1].split("c")[0])
            if re.search(r'\sFinal Spectrum\s', line):
                break
            if read_transs:
                if re.search(r'Energy =', line):
                    wavenumber, transition = line.split(": ")
                    wavenumber = float(re.search(r'([\d.])+\s', wavenumber).group(0))
                    wavenumbers.append(wavenumber)
                    transitions.append(transition)
                elif re.search(r'Intensity', line):
                    intensity, dipstr = line.split("(")
                    intensity = float(intensity.split("=")[1])
                    intensities.append(intensity)
        max_intensity = max(intensities)
        for i, wavenumber in enumerate(wavenumbers):
            peak = FCPeak()
            peak.intensity = intensities[i] / max_intensity
            peak.wavenumber = wavenumber
            peak.transition = [[int(n) for n in t.split('^')] for t in
                               transitions[i].split('|')[2].strip('>\n').split(';')]
            peaks.append(peak)
        peaks.sort(key=lambda p: p.wavenumber)
        spectrum = FCSpectrum()
        spectrum.is_emission = is_emission
        spectrum.peaks = peaks
        spectrum.zero_zero_transition_energy = zero
        spectrum.multiplicator = max_intensity

        return spectrum

