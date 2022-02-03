import logging
import os
import re

from galaxy.datatypes import metadata
from galaxy.datatypes.binary import Binary
from galaxy.datatypes.data import (
    get_file_peek,
    Text,
)
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes.sniff import (
    build_sniff_from_prefix,
    FilePrefix,
    get_headers,
    iter_headers
)
from galaxy.datatypes.tabular import Tabular
from galaxy.datatypes.util.generic_util import count_special_lines
from galaxy.datatypes.xml import GenericXml
from galaxy.util import (
    commands,
    unicodify
)

# optional import to enhance metadata
try:
    from ase import io as ase_io
except ImportError:
    ase_io = None

log = logging.getLogger(__name__)


def count_lines(filename, non_empty=False):
    """
    counting the number of lines from the 'filename' file
    """
    if non_empty:
        cmd = ['grep', '-cve', r'^\s*$', filename]
    else:
        cmd = ['wc', '-l', filename]
    try:
        out = commands.execute(cmd)
    except commands.CommandLineException as e:
        log.error(unicodify(e))
        return 0
    return int(out.split()[0])


class GenericMolFile(Text):
    """
    Abstract class for most of the molecule files.
    """
    MetadataElement(name="number_of_molecules", default=0, desc="Number of molecules", readonly=True, visible=True, optional=True, no_value=0)

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            if (dataset.metadata.number_of_molecules == 1):
                dataset.blurb = "1 molecule"
            else:
                dataset.blurb = f"{dataset.metadata.number_of_molecules} molecules"
            dataset.peek = get_file_peek(dataset.file_name)
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def get_mime(self):
        return 'text/plain'


class MOL(GenericMolFile):
    file_ext = "mol"

    def set_meta(self, dataset, **kwd):
        """
        Set the number molecules, in the case of MOL its always one.
        """
        dataset.metadata.number_of_molecules = 1


@build_sniff_from_prefix
class SDF(GenericMolFile):
    file_ext = "sdf"

    def sniff_prefix(self, file_prefix: FilePrefix):
        """
        Try to guess if the file is a SDF2 file.

        An SDfile (structure-data file) can contain multiple compounds.

        Each compound starts with a block in V2000 or V3000 molfile format,
        which ends with a line equal to 'M  END'.
        This is followed by a non-structural data block, which ends with a line
        equal to '$$$$'.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('drugbank_drugs.sdf')
        >>> SDF().sniff(fname)
        True
        >>> fname = get_test_fname('github88.v3k.sdf')
        >>> SDF().sniff(fname)
        True
        >>> fname = get_test_fname('chebi_57262.v3k.mol')
        >>> SDF().sniff(fname)
        False
        """
        m_end_found = False
        limit = 10000
        idx = 0
        for line in file_prefix.line_iterator():
            idx += 1
            line = line.rstrip('\n\r')
            if idx < 4:
                continue
            elif idx == 4:
                if len(line) != 39 or not(line.endswith(' V2000')
                        or line.endswith(' V3000')):
                    return False
            elif not m_end_found:
                if line == 'M  END':
                    m_end_found = True
            elif line == '$$$$':
                return True
            if idx == limit:
                break
        return False

    def set_meta(self, dataset, **kwd):
        """
        Set the number of molecules in dataset.
        """
        dataset.metadata.number_of_molecules = count_special_lines(r"^\$\$\$\$$", dataset.file_name)

    @classmethod
    def split(cls, input_datasets, subdir_generator_function, split_params):
        """
        Split the input files by molecule records.
        """
        if split_params is None:
            return None

        if len(input_datasets) > 1:
            raise Exception("SD-file splitting does not support multiple files")
        input_files = [ds.file_name for ds in input_datasets]

        chunk_size = None
        if split_params['split_mode'] == 'number_of_parts':
            raise Exception(f"Split mode \"{split_params['split_mode']}\" is currently not implemented for SD-files.")
        elif split_params['split_mode'] == 'to_size':
            chunk_size = int(split_params['split_size'])
        else:
            raise Exception(f"Unsupported split mode {split_params['split_mode']}")

        def _read_sdf_records(filename):
            lines = []
            with open(filename) as handle:
                for line in handle:
                    lines.append(line)
                    if line.startswith("$$$$"):
                        yield lines
                        lines = []

        def _write_part_sdf_file(accumulated_lines):
            part_dir = subdir_generator_function()
            part_path = os.path.join(part_dir, os.path.basename(input_files[0]))
            with open(part_path, 'w') as part_file:
                part_file.writelines(accumulated_lines)

        try:
            sdf_records = _read_sdf_records(input_files[0])
            sdf_lines_accumulated = []
            for counter, sdf_record in enumerate(sdf_records, start=1):
                sdf_lines_accumulated.extend(sdf_record)
                if counter % chunk_size == 0:
                    _write_part_sdf_file(sdf_lines_accumulated)
                    sdf_lines_accumulated = []
            if sdf_lines_accumulated:
                _write_part_sdf_file(sdf_lines_accumulated)
        except Exception as e:
            log.error('Unable to split files: %s', unicodify(e))
            raise


@build_sniff_from_prefix
class MOL2(GenericMolFile):
    file_ext = "mol2"

    def sniff_prefix(self, file_prefix: FilePrefix):
        """
        Try to guess if the file is a MOL2 file.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('drugbank_drugs.mol2')
        >>> MOL2().sniff(fname)
        True
        >>> fname = get_test_fname('drugbank_drugs.cml')
        >>> MOL2().sniff(fname)
        False
        """
        limit = 60
        idx = 0
        for line in file_prefix.line_iterator():
            line = line.rstrip('\n\r')
            if line == '@<TRIPOS>MOLECULE':
                return True
            idx += 1
            if idx == limit:
                break
        return False

    def set_meta(self, dataset, **kwd):
        """
        Set the number of lines of data in dataset.
        """
        dataset.metadata.number_of_molecules = count_special_lines("@<TRIPOS>MOLECULE", dataset.file_name)

    @classmethod
    def split(cls, input_datasets, subdir_generator_function, split_params):
        """
        Split the input files by molecule records.
        """
        if split_params is None:
            return None

        if len(input_datasets) > 1:
            raise Exception("MOL2-file splitting does not support multiple files")
        input_files = [ds.file_name for ds in input_datasets]

        chunk_size = None
        if split_params['split_mode'] == 'number_of_parts':
            raise Exception(f"Split mode \"{split_params['split_mode']}\" is currently not implemented for MOL2-files.")
        elif split_params['split_mode'] == 'to_size':
            chunk_size = int(split_params['split_size'])
        else:
            raise Exception(f"Unsupported split mode {split_params['split_mode']}")

        def _read_mol2_records(filename):
            lines = []
            start = True
            with open(filename) as handle:
                for line in handle:
                    if line.startswith("@<TRIPOS>MOLECULE"):
                        if start:
                            start = False
                        else:
                            yield lines
                            lines = []
                    lines.append(line)

        def _write_part_mol2_file(accumulated_lines):
            part_dir = subdir_generator_function()
            part_path = os.path.join(part_dir, os.path.basename(input_files[0]))
            with open(part_path, 'w') as part_file:
                part_file.writelines(accumulated_lines)

        try:
            mol2_records = _read_mol2_records(input_files[0])
            mol2_lines_accumulated = []
            for counter, mol2_record in enumerate(mol2_records, start=1):
                mol2_lines_accumulated.extend(mol2_record)
                if counter % chunk_size == 0:
                    _write_part_mol2_file(mol2_lines_accumulated)
                    mol2_lines_accumulated = []
            if mol2_lines_accumulated:
                _write_part_mol2_file(mol2_lines_accumulated)
        except Exception as e:
            log.error('Unable to split files: %s', unicodify(e))
            raise


@build_sniff_from_prefix
class FPS(GenericMolFile):
    """
    chemfp fingerprint file: http://code.google.com/p/chem-fingerprints/wiki/FPS
    """
    file_ext = "fps"

    def sniff_prefix(self, file_prefix: FilePrefix):
        """
        Try to guess if the file is a FPS file.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('q.fps')
        >>> FPS().sniff(fname)
        True
        >>> fname = get_test_fname('drugbank_drugs.cml')
        >>> FPS().sniff(fname)
        False
        """
        header = get_headers(file_prefix, sep='\t', count=1)
        if header[0][0].strip() == '#FPS1':
            return True
        else:
            return False

    def set_meta(self, dataset, **kwd):
        """
        Set the number of lines of data in dataset.
        """
        dataset.metadata.number_of_molecules = count_special_lines('^#', dataset.file_name, invert=True)

    @classmethod
    def split(cls, input_datasets, subdir_generator_function, split_params):
        """
        Split the input files by fingerprint records.
        """
        if split_params is None:
            return None

        if len(input_datasets) > 1:
            raise Exception("FPS-file splitting does not support multiple files")
        input_files = [ds.file_name for ds in input_datasets]

        chunk_size = None
        if split_params['split_mode'] == 'number_of_parts':
            raise Exception(f"Split mode \"{split_params['split_mode']}\" is currently not implemented for MOL2-files.")
        elif split_params['split_mode'] == 'to_size':
            chunk_size = int(split_params['split_size'])
        else:
            raise Exception(f"Unsupported split mode {split_params['split_mode']}")

        def _write_part_fingerprint_file(accumulated_lines):
            part_dir = subdir_generator_function()
            part_path = os.path.join(part_dir, os.path.basename(input_files[0]))
            with open(part_path, 'w') as part_file:
                part_file.writelines(accumulated_lines)

        try:
            header_lines = []
            lines_accumulated = []
            fingerprint_counter = 0
            for line in open(input_files[0]):
                if not line.strip():
                    continue
                if line.startswith('#'):
                    header_lines.append(line)
                else:
                    fingerprint_counter += 1
                    lines_accumulated.append(line)
                if fingerprint_counter != 0 and fingerprint_counter % chunk_size == 0:
                    _write_part_fingerprint_file(header_lines + lines_accumulated)
                    lines_accumulated = []
            if lines_accumulated:
                _write_part_fingerprint_file(header_lines + lines_accumulated)
        except Exception as e:
            log.error('Unable to split files: %s', unicodify(e))
            raise

    @staticmethod
    def merge(split_files, output_file):
        """
        Merging fps files requires merging the header manually.
        We take the header from the first file.
        """
        if len(split_files) == 1:
            # For one file only, use base class method (move/copy)
            return Text.merge(split_files, output_file)
        if not split_files:
            raise ValueError("No fps files given, %r, to merge into %s"
                             % (split_files, output_file))
        with open(output_file, "w") as out:
            first = True
            for filename in split_files:
                with open(filename) as handle:
                    for line in handle:
                        if line.startswith('#'):
                            if first:
                                out.write(line)
                        else:
                            # line is no header and not a comment, we assume the first header is written to out and we set 'first' to False
                            first = False
                            out.write(line)


class OBFS(Binary):
    """OpenBabel Fastsearch format (fs)."""
    file_ext = 'obfs'
    composite_type = 'basic'

    MetadataElement(name="base_name", default='OpenBabel Fastsearch Index',
                    readonly=True, visible=True, optional=True,)

    def __init__(self, **kwd):
        """
            A Fastsearch Index consists of a binary file with the fingerprints
            and a pointer the actual molecule file.
        """
        super().__init__(**kwd)
        self.add_composite_file('molecule.fs', is_binary=True,
                                description='OpenBabel Fastsearch Index')
        self.add_composite_file('molecule.sdf', optional=True,
                                is_binary=False, description='Molecule File')
        self.add_composite_file('molecule.smi', optional=True,
                                is_binary=False, description='Molecule File')
        self.add_composite_file('molecule.inchi', optional=True,
                                is_binary=False, description='Molecule File')
        self.add_composite_file('molecule.mol2', optional=True,
                                is_binary=False, description='Molecule File')
        self.add_composite_file('molecule.cml', optional=True,
                                is_binary=False, description='Molecule File')

    def set_peek(self, dataset):
        """Set the peek and blurb text."""
        if not dataset.dataset.purged:
            dataset.peek = "OpenBabel Fastsearch Index"
            dataset.blurb = "OpenBabel Fastsearch Index"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        """Create HTML content, used for displaying peek."""
        try:
            return dataset.peek
        except Exception:
            return "OpenBabel Fastsearch Index"

    def get_mime(self):
        """Returns the mime type of the datatype (pretend it is text for peek)"""
        return 'text/plain'

    def merge(split_files, output_file, extra_merge_args):
        """Merging Fastsearch indices is not supported."""
        raise NotImplementedError("Merging Fastsearch indices is not supported.")

    def split(cls, input_datasets, subdir_generator_function, split_params):
        """Splitting Fastsearch indices is not supported."""
        if split_params is None:
            return None
        raise NotImplementedError("Splitting Fastsearch indices is not possible.")


class DRF(GenericMolFile):
    file_ext = "drf"

    def set_meta(self, dataset, **kwd):
        """
        Set the number of lines of data in dataset.
        """
        dataset.metadata.number_of_molecules = count_special_lines('\"ligand id\"', dataset.file_name, invert=True)


class PHAR(GenericMolFile):
    """
    Pharmacophore database format from silicos-it.
    """
    file_ext = "phar"

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name)
            dataset.blurb = "pharmacophore"
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'


@build_sniff_from_prefix
class PDB(GenericMolFile):
    """
    Protein Databank format.
    http://www.wwpdb.org/documentation/format33/v3.3.html
    """
    file_ext = "pdb"
    MetadataElement(name="chain_ids", default=[], desc="Chain IDs", readonly=False, visible=True)

    def sniff_prefix(self, file_prefix: FilePrefix):
        """
        Try to guess if the file is a PDB file.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('5e5z.pdb')
        >>> PDB().sniff(fname)
        True
        >>> fname = get_test_fname('drugbank_drugs.cml')
        >>> PDB().sniff(fname)
        False
        """
        headers = iter_headers(file_prefix, sep=' ', count=300)
        h = t = c = s = k = e = False
        for line in headers:
            section_name = line[0].strip()
            if section_name == 'HEADER':
                h = True
            elif section_name == 'TITLE':
                t = True
            elif section_name == 'COMPND':
                c = True
            elif section_name == 'SOURCE':
                s = True
            elif section_name == 'KEYWDS':
                k = True
            elif section_name == 'EXPDTA':
                e = True

        if h * t * c * s * k * e:
            return True
        else:
            return False

    def set_meta(self, dataset, **kwd):
        """
        Find Chain_IDs for metadata.
        """
        try:
            chain_ids = set()
            with open(dataset.file_name) as fh:
                for line in fh:
                    if line.startswith('ATOM  ') or line.startswith('HETATM'):
                        if line[21] != ' ':
                            chain_ids.add(line[21])
            dataset.metadata.chain_ids = list(chain_ids)
        except Exception as e:
            log.error('Error finding chain_ids: %s', unicodify(e))
            raise

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            atom_numbers = count_special_lines("^ATOM", dataset.file_name)
            hetatm_numbers = count_special_lines("^HETATM", dataset.file_name)
            chain_ids = ','.join(dataset.metadata.chain_ids) if len(dataset.metadata.chain_ids) > 0 else 'None'
            dataset.peek = get_file_peek(dataset.file_name)
            dataset.blurb = f"{atom_numbers} atoms and {hetatm_numbers} HET-atoms\nchain_ids: {chain_ids}"
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'


@build_sniff_from_prefix
class PDBQT(GenericMolFile):
    """
    PDBQT Autodock and Autodock Vina format
    http://autodock.scripps.edu/faqs-help/faq/what-is-the-format-of-a-pdbqt-file
    """
    file_ext = "pdbqt"

    def sniff_prefix(self, file_prefix: FilePrefix):
        """
        Try to guess if the file is a PDBQT file.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('NuBBE_1_obabel_3D.pdbqt')
        >>> PDBQT().sniff(fname)
        True
        >>> fname = get_test_fname('drugbank_drugs.cml')
        >>> PDBQT().sniff(fname)
        False
        """
        headers = iter_headers(file_prefix, sep=' ', count=300)
        h = t = c = s = k = False
        for line in headers:
            section_name = line[0].strip()
            if section_name == 'REMARK':
                h = True
            elif section_name == 'ROOT':
                t = True
            elif section_name == 'ENDROOT':
                c = True
            elif section_name == 'BRANCH':
                s = True
            elif section_name == 'TORSDOF':
                k = True

        if h * t * c * s * k:
            return True
        else:
            return False

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            root_numbers = count_special_lines("^ROOT", dataset.file_name)
            branch_numbers = count_special_lines("^BRANCH", dataset.file_name)
            dataset.peek = get_file_peek(dataset.file_name)
            dataset.blurb = f"{root_numbers} roots and {branch_numbers} branches"
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'


@build_sniff_from_prefix
class PQR(GenericMolFile):
    """
    Protein Databank format.
    https://apbs-pdb2pqr.readthedocs.io/en/latest/formats/pqr.html
    """
    file_ext = "pqr"
    MetadataElement(name="chain_ids", default=[], desc="Chain IDs", readonly=False, visible=True)

    def get_matcher(self):
        """
        Atom and HETATM line fields are space separated, match group:
          0: Field_name
              A string which specifies the type of PQR entry: ATOM or HETATM.
          1: Atom_number
              An integer which provides the atom index.
          2: Atom_name
              A string which provides the atom name.
          3: Residue_name
              A string which provides the residue name.
          5: Chain_ID   (Optional, group 4 is whole field)
              An optional string which provides the chain ID of the atom.
              Note that chain ID support is a new feature of APBS 0.5.0 and later versions.
          6: Residue_number
              An integer which provides the residue index.
          7: X 8: Y 9: Z
              3 floats which provide the atomic coordinates (in angstroms)
          10: Charge
              A float which provides the atomic charge (in electrons).
          11: Radius
              A float which provides the atomic radius (in angstroms).
        """
        pat = r'(ATOM|HETATM)\s+' +\
              r'(\d+)\s+' +\
              r'([A-Z0-9]+)\s+' +\
              r'([A-Z0-9]+)\s+' +\
              r'(([A-Z]?)\s+)?' +\
              r'([-+]?\d*\.\d+|\d+)\s+' +\
              r'([-+]?\d*\.\d+|\d+)\s+' +\
              r'([-+]?\d*\.\d+|\d+)\s+' +\
              r'([-+]?\d*\.\d+|\d+)\s+' +\
              r'([-+]?\d*\.\d+|\d+)\s+'
        return re.compile(pat)

    def sniff_prefix(self, file_prefix: FilePrefix):
        """
        Try to guess if the file is a PQR file.
        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('5e5z.pqr')
        >>> PQR().sniff(fname)
        True
        >>> fname = get_test_fname('drugbank_drugs.cml')
        >>> PQR().sniff(fname)
        False
        """
        prog = self.get_matcher()
        headers = iter_headers(file_prefix, sep=None, comment_designator='REMARK   5', count=3000)
        h = a = False
        for line in headers:
            section_name = line[0].strip()
            if section_name == 'REMARK':
                h = True
            elif section_name == 'ATOM' or section_name == 'HETATM':
                if prog.match(' '.join(line)):
                    a = True
                    break
        if h * a:
            return True
        else:
            return False

    def set_meta(self, dataset, **kwd):
        """
        Find Optional Chain_IDs for metadata.
        """
        try:
            prog = self.get_matcher()
            chain_ids = set()
            with open(dataset.file_name) as fh:
                for line in fh:
                    if line.startswith('REMARK'):
                        continue
                    match = prog.match(line.rstrip())
                    if match and match.groups()[5]:
                        chain_ids.add(match.groups()[5])
            dataset.metadata.chain_ids = list(chain_ids)
        except Exception as e:
            log.error('Error finding chain_ids: %s', unicodify(e))
            raise

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            atom_numbers = count_special_lines("^ATOM", dataset.file_name)
            hetatm_numbers = count_special_lines("^HETATM", dataset.file_name)
            chain_ids = ','.join(dataset.metadata.chain_ids) if len(dataset.metadata.chain_ids) > 0 else 'None'
            dataset.peek = get_file_peek(dataset.file_name)
            dataset.blurb = f"{atom_numbers} atoms and {hetatm_numbers} HET-atoms\nchain_ids: {str(chain_ids)}"
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'


class Cell(GenericMolFile):
    """
    CASTEP CELL format.
    """

    file_ext = "cell"
    MetadataElement(
        name="atom_data",
        default=[],
        desc="Atom symbols and positions",
        readonly=True,
        visible=False,
    )
    MetadataElement(
        name="number_atoms",
        desc="Number of atoms",
        readonly=True,
        visible=True,
    )
    MetadataElement(
        name="chemical_formula",
        desc="Chemical formula",
        readonly=True,
        visible=True,
    )
    MetadataElement(
        name="is_periodic",
        desc="Periodic boundary conditions",
        readonly=True,
        visible=True,
    )
    MetadataElement(
        name="lattice_parameters",
        desc="Lattice parameters",
        readonly=True,
        visible=True,
    )

    def sniff(self, filename):
        """
        Try to guess if the file is a CELL file.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('Si.cell')
        >>> Cell().sniff(fname)
        True
        >>> fname = get_test_fname('Si_cell.txt')
        >>> Cell().sniff(fname)
        True
        >>> fname = get_test_fname('Si.cif')
        >>> Cell().sniff(fname)
        False
        """
        with open(filename) as f:
            cell = f.read(1000)
        if '\n%BLOCK ' in cell:
            if '\n%ENDBLOCK ' in cell:
                return True
        else:
            return False

        # if BLOCK was found but not ENDBLOCK, check the rest of the file
        with open(filename) as f:
            cell = f.read()
        if '\n%ENDBLOCK ' in cell:
            return True
        else:
            return False

    def set_meta(self, dataset, **kwd):
        """
        Find Atom IDs for metadata.
        """
        # CELL file can only have one molecule
        dataset.metadata.number_of_molecules = 1

        if ase_io:
            # enhanced metadata
            try:
                ase_data = ase_io.read(dataset.file_name, format="castep-cell")
            except ValueError:
                log.error("Could not read cell structure data: %s", unicodify(e))
                raise

            try:
                dataset.metadata.atom_data = [
                    str(sym) + str(pos)
                    for sym, pos in zip(
                        ase_data.get_chemical_symbols(), ase_data.get_positions()
                    )
                ]
                log.warning(len(dataset.metadata.atom_data))
                dataset.metadata.number_atoms=len(dataset.metadata.atom_data)
                dataset.metadata.chemical_formula=ase_data.get_chemical_formula()
                pbc = ase_data.get_pbc()
                try:
                    dataset.metadata.is_periodic=1 if pbc else 0
                except ValueError: # pbc is an array
                    dataset.metadata.is_periodic=1 if pbc.any() else 0
                cell_data = ase_data.get_cell()
                dataset.metadata.lattice_parameters=list(cell_data.cellpar())
                log.warning("metadata is: %s", dataset.metadata)
            except Exception as e:
                log.error("Error finding metadata: %s", unicodify(e))
                raise

        else:
            # simple metadata
            with open(dataset.file_name) as f:
                cell = f.read()
            try:
                block = cell.split('%BLOCK POSITIONS')[1].split('%ENDBLOCK POSITIONS')[0].split('\n')[1:-1]
                dataset.metadata.atom_data = [atom.strip() for atom in block]
                dataset.metadata.number_atoms = len(dataset.metadata.atom_data)
            except Exception as e:
                log.error("Error finding atom_data: %s", unicodify(e))
                raise

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name)
            if ase_io:
                # enhanced blurb
                dataset.blurb = f"Structure of {dataset.metadata.chemical_formula}."
                if dataset.metadata.is_periodic:
                    dataset.blurb += f"\nPeriodic.\nLattice parameters in axis-angle format:\n{[round(x,2) for x in dataset.metadata.lattice_parameters]}."
                else:
                    dataset.blurb += "Not periodic."
                dataset.blurb += f"\nFile contains {len(dataset.metadata.atom_data)} atoms."
            else:
                # simple blurb
                dataset.blurb = f"CASTEP cell file containing {len(dataset.metadata.atom_data)} atoms"
            dataset.info = dataset.blurb
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"


class CIF(GenericMolFile):
    """
    CIF format.
    """

    file_ext = "cif"
    MetadataElement(
        name="atom_data",
        default=[],
        desc="Atom Positions",
        readonly=False,
        visible=True,
    )

    def sniff(self, filename):
        """
        Try to guess if the file is a CIF file.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('Si.cif')
        >>> CIF().sniff(fname)
        True
        >>> fname = get_test_fname('Si_cif.txt')
        >>> CIF().sniff(fname)
        True
        >>> fname = get_test_fname('Si.cell')
        >>> CIF().sniff(fname)
        False
        """
        with open(filename) as f:
            cif = f.read(1000)

        for line in cif.split('\n'):
            if not line:
                continue
            elif line[0] == '#':  # comment so skip
                continue
            if line.startswith('data_'):
                if '_atom_site_fract_' in cif:
                    return True
                break
            else:
                return False

        # if '_atom_site_fract_' not found check the rest of the file
        with open(filename) as f:
            cif = f.read()
        if '_atom_site_fract_' in cif:
            return True
        else:
            return False

    # def set_meta(self, dataset, **kwd):
    #     """
    #     Find Atom IDs for metadata.
    #     """

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name)
            dataset.blurb = (
                "CIF file"
            )
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"


class XYZ(GenericMolFile):
    """
    XYZ format.
    """

    file_ext = "xyz"
    MetadataElement(
        name="atom_data",
        default=[],
        desc="Atom Positions",
        readonly=False,
        visible=True,
    )

    def sniff(self, filename):
        """
        Try to guess if the file is a XYZ file.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('Si.xyz')
        >>> XYZ().sniff(fname)
        True
        >>> fname = get_test_fname('Si_xyz.txt')
        >>> XYZ().sniff(fname)
        True
        >>> fname = get_test_fname('Si.cell')
        >>> XYZ().sniff(fname)
        False
        """
        try:
            ase_data = ase_read(
                filename, format="extxyz"
            )  # use extxyz ("extended XYZ") as basic xyz format won't throw errors
            return True if ase_data else False
        except (TypeError, XYZError):
            return False

    def set_meta(self, dataset, **kwd):
        """
        Find Atom IDs for metadata.
        """
        try:
            ase_data = ase_read(dataset.file_name, format="xyz")
            atom_data = [
                str(sym) + str(pos)
                for sym, pos in zip(
                    ase_data.get_chemical_symbols(), ase_data.get_positions()
                )
            ]
            dataset.metadata.atom_data = atom_data
        except Exception as e:
            log.error("Error finding atom_data: %s", unicodify(e))
            raise

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name)
            dataset.blurb = (
                f"XYZ file containing {len(dataset.metadata.atom_data)} atoms"
            )
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"


class grd(Text):
    file_ext = "grd"

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name)
            dataset.blurb = "grids for docking"
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'


class grdtgz(Binary):
    file_ext = "grd.tgz"

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = 'binary data'
            dataset.blurb = "compressed grids for docking"
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'


@build_sniff_from_prefix
class InChI(Tabular):
    file_ext = "inchi"
    column_names = ['InChI']
    MetadataElement(name="columns", default=2, desc="Number of columns", readonly=True, visible=False)
    MetadataElement(name="column_types", default=['str'], param=metadata.ColumnTypesParameter, desc="Column types", readonly=True, visible=False)
    MetadataElement(name="number_of_molecules", default=0, desc="Number of molecules", readonly=True, visible=True, optional=True, no_value=0)

    def set_meta(self, dataset, **kwd):
        """
        Set the number of lines of data in dataset.
        """
        dataset.metadata.number_of_molecules = self.count_data_lines(dataset)

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            if (dataset.metadata.number_of_molecules == 1):
                dataset.blurb = "1 molecule"
            else:
                dataset.blurb = f"{dataset.metadata.number_of_molecules} molecules"
            dataset.peek = get_file_peek(dataset.file_name)
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def sniff_prefix(self, file_prefix: FilePrefix):
        """
        Try to guess if the file is a InChI file.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('drugbank_drugs.inchi')
        >>> InChI().sniff(fname)
        True
        >>> fname = get_test_fname('drugbank_drugs.cml')
        >>> InChI().sniff(fname)
        False
        """
        inchi_lines = iter_headers(file_prefix, sep=' ', count=10)
        found_lines = False
        for inchi in inchi_lines:
            if not inchi[0].startswith('InChI='):
                return False
            found_lines = True
        return found_lines


class SMILES(Tabular):
    # It is hard or impossible to sniff a SMILES File. We can try to import the
    # first SMILES and check if it is a molecule, but currently it is not
    # possible to use external libraries in datatype definition files.
    # Moreover it seems impossible to include OpenBabel as Python library
    # because OpenBabel is GPL licensed.
    file_ext = "smi"
    column_names = ['SMILES', 'TITLE']
    MetadataElement(name="columns", default=2, desc="Number of columns", readonly=True, visible=False)
    MetadataElement(name="column_types", default=['str', 'str'], param=metadata.ColumnTypesParameter, desc="Column types", readonly=True, visible=False)
    MetadataElement(name="number_of_molecules", default=0, desc="Number of molecules", readonly=True, visible=True, optional=True, no_value=0)

    def set_meta(self, dataset, **kwd):
        """
        Set the number of lines of data in dataset.
        """
        dataset.metadata.number_of_molecules = self.count_data_lines(dataset)

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            if dataset.metadata.number_of_molecules == 1:
                dataset.blurb = "1 molecule"
            else:
                dataset.blurb = f"{dataset.metadata.number_of_molecules} molecules"
            dataset.peek = get_file_peek(dataset.file_name)
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'


@build_sniff_from_prefix
class CML(GenericXml):
    """
    Chemical Markup Language
    http://cml.sourceforge.net/
    """
    file_ext = "cml"
    MetadataElement(name="number_of_molecules", default=0, desc="Number of molecules", readonly=True, visible=True, optional=True, no_value=0)

    def set_meta(self, dataset, **kwd):
        """
        Set the number of lines of data in dataset.
        """
        dataset.metadata.number_of_molecules = count_special_lines(r'^\s*<molecule', dataset.file_name)

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            if (dataset.metadata.number_of_molecules == 1):
                dataset.blurb = "1 molecule"
            else:
                dataset.blurb = f"{dataset.metadata.number_of_molecules} molecules"
            dataset.peek = get_file_peek(dataset.file_name)
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def sniff_prefix(self, file_prefix: FilePrefix):
        """
        Try to guess if the file is a CML file.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('interval.interval')
        >>> CML().sniff(fname)
        False
        >>> fname = get_test_fname('drugbank_drugs.cml')
        >>> CML().sniff(fname)
        True
        """
        for expected_string in ['<?xml version="1.0"?>', 'http://www.xml-cml.org/schema']:
            if expected_string not in file_prefix.contents_header:
                return False

        return True

    @classmethod
    def split(cls, input_datasets, subdir_generator_function, split_params):
        """
        Split the input files by molecule records.
        """
        if split_params is None:
            return None

        if len(input_datasets) > 1:
            raise Exception("CML-file splitting does not support multiple files")
        input_files = [ds.file_name for ds in input_datasets]

        chunk_size = None
        if split_params['split_mode'] == 'number_of_parts':
            raise Exception(f"Split mode \"{split_params['split_mode']}\" is currently not implemented for CML-files.")
        elif split_params['split_mode'] == 'to_size':
            chunk_size = int(split_params['split_size'])
        else:
            raise Exception(f"Unsupported split mode {split_params['split_mode']}")

        def _read_cml_records(filename):
            lines = []
            with open(filename) as handle:
                for line in handle:
                    if line.lstrip().startswith('<?xml version="1.0"?>') or \
                       line.lstrip().startswith('<cml xmlns="http://www.xml-cml.org/schema') or \
                       line.lstrip().startswith('</cml>'):
                        continue
                    lines.append(line)
                    if line.lstrip().startswith('</molecule>'):
                        yield lines
                        lines = []

        header_lines = ['<?xml version="1.0"?>\n', '<cml xmlns="http://www.xml-cml.org/schema">\n']
        footer_line = ['</cml>\n']

        def _write_part_cml_file(accumulated_lines):
            part_dir = subdir_generator_function()
            part_path = os.path.join(part_dir, os.path.basename(input_files[0]))
            with open(part_path, 'w') as part_file:
                part_file.writelines(header_lines)
                part_file.writelines(accumulated_lines)
                part_file.writelines(footer_line)

        try:
            cml_records = _read_cml_records(input_files[0])
            cml_lines_accumulated = []
            for counter, cml_record in enumerate(cml_records, start=1):
                cml_lines_accumulated.extend(cml_record)
                if counter % chunk_size == 0:
                    _write_part_cml_file(cml_lines_accumulated)
                    cml_lines_accumulated = []
            if cml_lines_accumulated:
                _write_part_cml_file(cml_lines_accumulated)
        except Exception as e:
            log.error('Unable to split files: %s', unicodify(e))
            raise

    @staticmethod
    def merge(split_files, output_file):
        """
        Merging CML files.
        """
        if len(split_files) == 1:
            # For one file only, use base class method (move/copy)
            return Text.merge(split_files, output_file)
        if not split_files:
            raise ValueError("Given no CML files, %r, to merge into %s"
                             % (split_files, output_file))
        with open(output_file, "w") as out:
            for filename in split_files:
                with open(filename) as handle:
                    header = handle.readline()
                    if not header:
                        raise ValueError(f"CML file {filename} was empty")
                    if not header.lstrip().startswith('<?xml version="1.0"?>'):
                        out.write(header)
                        raise ValueError(f"{filename} is not a valid XML file!")
                    line = handle.readline()
                    header += line
                    if not line.lstrip().startswith('<cml xmlns="http://www.xml-cml.org/schema'):
                        out.write(header)
                        raise ValueError(f"{filename} is not a CML file!")
                    molecule_found = False
                    for line in handle.readlines():
                        # We found two required header lines, the next line should start with <molecule >
                        if line.lstrip().startswith('</cml>'):
                            continue
                        if line.lstrip().startswith('<molecule'):
                            molecule_found = True
                        if molecule_found:
                            out.write(line)
            out.write("</cml>\n")


class GRO(GenericMolFile):
    """
    GROMACS structure format.
    https://manual.gromacs.org/current/reference-manual/file-formats.html#gro
    """
    file_ext = "gro"

    def sniff_prefix(self, file_prefix: FilePrefix):
        """
        Try to guess if the file is a GRO file.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('5e5z.gro')
        >>> GRO().sniff_prefix(fname)
        True
        >>> fname = get_test_fname('5e5z.pdb')
        >>> GRO().sniff_prefix(fname)
        False
        """
        headers = get_headers(file_prefix, sep='\n', count=300)
        try:
            int(headers[1][0])  # the second line should just be the number of atoms
        except ValueError:
            return False
        for line in headers[2:-1]:  # skip the first, second and last lines
            if not re.search(r'^[0-9 ]{5}[a-zA-Z0-9 ]{10}[0-9 ]{5}[0-9 -]{4}\.[0-9]{3}[0-9 -]{4}\.[0-9]{3}[0-9 -]{4}\.[0-9]{3}', line[0]):
                return False
        return True

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name)
            atom_number = int(dataset.peek.split('\n')[1])
            dataset.blurb = f"{atom_number} atoms"
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'
