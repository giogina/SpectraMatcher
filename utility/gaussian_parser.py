import re
from models.molecular_data import Geometry, VibrationalMode, FCPeak, FCSpectrum, ModeList


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

    @staticmethod
    def get_element_from_number(n):
        return GaussianParser._ELEMENT_NAMES.get(n, str(n))

    @ staticmethod
    def parse_input(lines):
        tracker = None
        routing_info = None
        charge = None
        multiplicity = None
        geometry = None
        for line in lines:
            if len(line.strip('\n').strip('\r').strip(' ')) == 0:
                if type(tracker) == str:
                    routing_info = GaussianParser.parse_gaussian_hash_line(tracker)
                    tracker = 1  # Turns into counter of blank lines after the routing line
                elif type(tracker) == int:
                    tracker -= 1  # count empty lines after routing line
                elif type(tracker) == list:
                    if len(tracker) > 0:
                        geometry = GaussianParser.extract_geometry(tracker, 0, is_input_file=True)
                    tracker = None  # Signify end of geometry
            else:
                if tracker is None and line.strip().startswith("#"):
                    tracker = ""
                if type(tracker) == str:
                    tracker += line.strip('\n').strip('\r')
                    tracker = tracker.replace('  ', ' ')
                elif tracker == 0:
                    match = re.fullmatch(r"(-?\d+)\s+(-?\d+)", line.strip())
                    charge, multiplicity = (int(match.group(1)), int(match.group(2))) if match else (None, None)
                    tracker = []  # turns into list of geom lines
                elif type(tracker) == list:
                    tracker.append(line)
        return routing_info, charge, multiplicity, geometry

    @staticmethod
    def scan_log_file(lines):
        routing_info = None
        nr_jobs = 1  # keep track of Gaussian starting new internal jobs
        nr_finished = 0
        error = None
        start_lines = {}
        tracker = None
        freqs_found = False
        hp_freqs_found = False
        charge = None
        multiplicity = None
        energy = None  # Sum of electronic and zero-point Energies= ... (FC files will have ground state energy)
        for i, line in enumerate(lines):
            if line.strip().startswith("#") and routing_info is None:
                tracker = ""
            if type(tracker) == str:
                if line.strip().startswith("---"):
                    routing_info = GaussianParser.parse_gaussian_hash_line(tracker)
                    tracker = None
                else:
                    newstr = line.strip('\n').strip('\r')
                    if newstr.startswith(' '):
                        newstr = newstr[1:]  # Remove single leading space
                    tracker += newstr
            if charge is None:
                chm_match = re.search(r"Charge\s*=\s*(\d+)\s*Multiplicity\s*=\s*(\d+)", line)
                if chm_match:
                    charge = int(chm_match.group(1))
                    multiplicity = int(chm_match.group(2))
            if not (freqs_found and hp_freqs_found) and line.strip().startswith('Frequencies --'):
                if not hp_freqs_found and line.strip().startswith('Frequencies ---'):
                    start_lines["hp freq"] = i
                    hp_freqs_found = True
                elif not freqs_found:
                    start_lines["lp freq"] = i
                    freqs_found = True
            elif energy is None and line.strip().startswith("Sum of electronic and zero-point Energies="):
                match = re.search(r"[-+]?[0-9]*\.?[0-9]+", line)
                if match:
                    energy = float(match.group()) * 219474.63  # convert to cm^(-1)
            elif line.strip() in ("Standard orientation:",  "Input orientation:"):
                start_lines["last geom"] = i+1
            elif line.strip() == "New orientation in initial state":  # Eckart orientation in FC files! Use this!
                start_lines["initial state geom"] = i+1
            elif line.strip() == "New orientation in final state":
                start_lines["final state geom"] = i+1
            elif line.strip() == "Information on Transitions":
                start_lines["FC transitions"] = i-1
            elif line.strip() == "Duschinsky matrix":
                start_lines["Duschinsky"] = i
            elif line.strip() == "Reduced system":
                start_lines["Mode mapping"] = i+3
            elif re.search('Proceeding to internal job step number', line):
                nr_jobs += 1
            elif re.search('Normal termination', line):
                nr_finished += 1
            elif re.search('Error termination', line):
                error = line

        return nr_jobs == nr_finished, error, routing_info, charge, multiplicity, start_lines, energy

    @ staticmethod
    def extract_geometry(lines, start_index, x_column=None, is_input_file=False):
        geometry = Geometry()
        for i in range(start_index, len(lines)):
            line = lines[i].strip('\n').strip('\r')
            if line.startswith(" Number") or line.startswith(" Center") or line.startswith(" ---") or len(line.strip())==0:
                continue
            coord_match = re.findall(r'\s+([-\d.]+)', line)
            if x_column is None:
                x_column = len(coord_match) - 3  # assume last 3 columns are x, y, z
            if len(coord_match) == x_column + 3 and x_column >= 0:
                if is_input_file:
                    first = line.split()[0]
                    element_symbol = ""
                    for symbol in GaussianParser._ELEMENT_NAMES.values():
                        if first.startswith(symbol) and len(symbol) > len(element_symbol):
                            element_symbol = symbol
                    geometry.atoms.append(element_symbol)
                else:
                    geometry.atoms.append(GaussianParser._ELEMENT_NAMES.get(str(coord_match[1]), ""))
                geometry.x.append(float(coord_match[x_column]))
                geometry.y.append(float(coord_match[x_column + 1]))
                geometry.z.append(float(coord_match[x_column + 2]))
            else:
                break

        return geometry

    @staticmethod
    def split_hash_line(hash_line):
        res = []
        current_piece = ""
        nr_open_parentheses = 0
        for c in hash_line:
            if c == ' ' and len(current_piece) > 0 and nr_open_parentheses == 0:
                res.append(current_piece)
                current_piece = ""
            else:
                current_piece += c
                if c == '(':
                    nr_open_parentheses += 1
                elif c == ')':
                    nr_open_parentheses -= 1
        if len(current_piece) > 0:
            res.append(current_piece)
        return res

    @staticmethod
    def parse_gaussian_hash_line(hash_line: str):
        # Known job types for Gaussian
        job_types = [
            "sp", "opt", "freq", "irc", "ircmax", "scan", "polar",
            "admp", "bomd", "eet", "force", "stable", "volume", "density=checkpoint", "guess=only"
        ]
        parts = GaussianParser.split_hash_line(hash_line.lower())  # Split string, but not between parentheses

        jobs = []
        td = None
        loth = None
        keywords = []

        for part in parts:
            if part.strip().startswith('#'):
                pass
            elif any(part.startswith(job) for job in job_types):
                jobs.append(part)
            elif part.lower().startswith('td'):
                td = part
            elif '/' in part and '=' not in part and loth is None:
                loth = part
            else:
                keywords.append(part)

        res = {"jobs": jobs, "loth": loth, "keywords": keywords}

        if td is not None:
            nstates_match = re.search(r'nstates=(\d+)', td)
            root_match = re.search(r'root=(\d+)', td)

            nstates = int(nstates_match.group(1)) if nstates_match else 3
            root = int(root_match.group(1)) if root_match else 1

            res["td"] = (root, nstates)

        return res

    @staticmethod
    def get_vibrational_modes(lines, hpmodes_start=None, lpmodes_start=None, geometry: Geometry = None):
        """Parses log file, returns list of VibrationalMode objects or None"""
        if geometry is None:
            print(f"No geometry found!")
            return

        frequencies = []
        reduced_masses = []
        normal_mode_vectors = []
        new_normal_mode_vectors = []
        read_atoms = False
        syms = []

        if hpmodes_start is not None:   # Read high-precision modes
            for l in range(hpmodes_start, len(lines)):
                line = lines[l]
                if line.strip().startswith('Frequencies ---'):  # Next set of modes starts!
                    syms.extend(re.findall(r'([a-zA-Z0-9?]+[\'"]?)', lines[l - 1]))
                    reduced_masses.extend([float(n) for n in re.findall(r'\s+([-\d.]+)', lines[l + 1].split("---")[1])])
                    new_freqs = [float(n) for n in re.findall(r'\s+([-\d.]+)', line.split("---")[1])]
                    frequencies.extend(new_freqs)
                    if new_normal_mode_vectors:
                        normal_mode_vectors.extend(new_normal_mode_vectors)
                    new_normal_mode_vectors = [[] for _ in new_freqs]
                    continue
                if line.strip() == "Coord Atom Element:":
                    read_atoms = True
                    continue
                if read_atoms:
                    atom_match = re.findall(r'\s+([-\d.]+)', line)
                    if len(atom_match) == len(new_normal_mode_vectors) + 3:
                        for i in range(0, len(new_normal_mode_vectors)):
                            new_normal_mode_vectors[i].append(float(atom_match[i + 3]))
                    else:
                        read_atoms = False
                if l == lpmodes_start:
                    break
            normal_mode_vectors.extend(new_normal_mode_vectors)

        elif lpmodes_start is not None:  # Read low-precision modes
            for l in range(lpmodes_start, len(lines)):
                line = lines[l]
                if line.strip().startswith('Frequencies --'):  # Next set of modes starts!
                    syms.extend(re.findall(r"([a-zA-Z0-9?]+['\"]?)", lines[l - 1]))
                    reduced_masses.extend([float(n) for n in re.findall(r'\s+([-\d.]+)', lines[l + 1].split("--")[1])])
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
            normal_mode_vectors.extend(new_normal_mode_vectors)
        if len(normal_mode_vectors):
            mode_list = ModeList()
            for i, vector in enumerate(normal_mode_vectors):
                x_vector = []
                y_vector = []
                z_vector = []
                for n, c in enumerate(vector):
                    if n % 3 == 0:
                        x_vector.append(float(c))
                    elif n % 3 == 1:
                        y_vector.append(float(c))
                    elif n % 3 == 2:
                        z_vector.append(float(c))
                mode_list.add_mode(frequencies[i], syms[i], reduced_masses[i], x_vector, y_vector, z_vector, geometry)
            mode_list.determine_mode_names()
            return mode_list
        else:
            print(f"No frequencies found!")
            return None

    @staticmethod
    def get_anharmonic_levels(lines, start_line=0):
        read = ''
        anharmonic_levels = []

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
    def get_FC_spectrum(lines, is_emission: bool = False, start_line=0, mode_mapping_start=None):
        wavenumbers = []
        transitions = []
        intensities = []
        read_transs = False
        peaks = []
        zero = 0
        mode_mapping_initial = {}
        mode_mapping_final = {}

        if mode_mapping_start is not None:  # fcht calculation was run in reduced-dimensionality mode
            for l in range(mode_mapping_start, len(lines)):
                line = lines[l]
                if line.strip() == "" or line.strip().startswith("Final"):
                    break
                match = re.search(r'(\d+)\s*=\s*(\d+)\s+(\d+)\s*=\s*(\d+)', line)
                if match:
                    mode_nums = [int(g) for g in match.groups()]
                    if len(mode_nums) == 4:
                        mode_mapping_initial[mode_nums[0]] = mode_nums[1]
                        mode_mapping_final[mode_nums[2]] = mode_nums[3]
            def mode_map(t): # Takes transition of type [mode, v], maps mode back to original name.
                t[0] = mode_mapping_final.get(t[0], t[0])
                return t
        else:
            def mode_map(t):
                return t

        for l in range(start_line, len(lines)):
            line = lines[l]
            if line.strip() == "Information on Transitions":
                read_transs = True
                continue
            if line.strip().startswith('Energy of the 0-0 transition'):
                zero = float(line.split(":")[1].split("c")[0])
            if line.strip() == "Final Spectrum":
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
            peak = FCPeak(intensity=intensities[i] / max_intensity,
                          wavenumber=wavenumber,
                          transition=[mode_map([int(n) for n in t.split('^')]) for t in
                                      transitions[i].split('|')[2].strip('>\n').split(';')]
                          )
            peaks.append(peak)
        peaks.sort(key=lambda p: p.wavenumber)
        spectrum = FCSpectrum(is_emission, peaks, zero, max_intensity)

        return spectrum

