import functools
import json
import re
import unicodedata
import warnings
from importlib import import_module
from pathlib import Path
from typing import Optional

import pydicom
from protocol import config
from protocol import logger
from protocol.config import (BASE_IMAGING_PARAMS_DICOM_TAGS as DICOM_TAGS,
                             Unspecified)

with warnings.catch_warnings():
    warnings.filterwarnings('ignore')
    from nibabel.nicom import csareader


def get_dicom_param_value(dicom: pydicom.FileDataset,
                          name: str,
                          not_found_value=None):
    """
    Extracts value from dicom metadata looking up the corresponding HEX tag
    in DICOM_TAGS

    Parameters
    ----------
    dicom : pydicom.FileDataset
        dicom object read from pydicom.read_file

    name : str
        parameter name such as MagneticFieldStrength or Manufacturer

    not_found_value : object
        value to be returned if name is not found

    Returns
    -------
    This method return a value for the given key. If key is not available,
    then returns default value None.
    """
    # TODO: consider name.lower()
    try:
        data = dicom.get(DICOM_TAGS[name], not_found_value)
    except KeyError:
        return not_found_value

    if data:
        return data.value
    else:
        return not_found_value


def safe_get(dictionary: dict, keys: str, default=None):
    """
    Used to get value from nested dictionaries without getting KeyError

    Parameters
    ----------
    dictionary : nested dict from which the value should be fetched
    keys : string of keys delimited by '.'
    default : if KeyError, return default

    Returns
    -------
    Value stored in that key

    Examples:
    To get value, dictionary[tag1][tag2][tag3],
    if KeyError: return default
    >>>     items = safe_get(dictionary, 'tags1.tag2.tag3')

    """
    return functools.reduce(
        lambda d, key: d.get(key, default) if isinstance(d, dict) else default,
        keys.split('.'),
        dictionary
        )


def parse_csa_params(dicom: pydicom.FileDataset,
                     not_found_value=None
                     ):
    """
    Returns params parsed from private CSA header from Siemens scanner exported DICOM

    Parameters
    ----------
    dicom : pydicom.FileDataset
        dicom object read from pydicom.read_file

    not_found_value : object
        value to be returned if a parameter is not found

    Returns
    -------
    dict
        Contains PED, multi-slice mode, iPAT and shim_mode

    """
    # series_header
    csa_header = csareader.read(get_header(dicom, 'series_header_info'))
    items = safe_get(csa_header, 'tags.MrPhoenixProtocol.items')
    if items:
        text = items[0]
    else:
        raise AttributeError('CSA Header exists, but xProtocol is missing')

    slice_code = get_csa_props("sKSpace.ucMultiSliceMode", text)
    slice_mode = config.SLICE_MODE.get(slice_code, slice_code)

    ipat_code = get_csa_props("sPat.ucPATMode", text)
    ipat = config.PAT.get(ipat_code, ipat_code)

    shim_code = get_csa_props("sAdjData.uiAdjShimMode", text)
    shim = config.SHIM.get(shim_code, shim_code)

    shim_first_order = []
    for i in ['X', 'Y', 'Z']:
        value = get_csa_props(f"sGRADSPEC.asGPAData[0].lOffset{i}", text)
        shim_first_order.append(float(value))

    shim_second_order = []
    for i in range(5):
        value = get_csa_props(f"sGRADSPEC.alShimCurrent[{i}]", text)
        shim_second_order.append(float(value))

    shim_setting = shim_first_order + shim_second_order

    # image_header
    image_header = csareader.read(get_header(dicom, 'image_header_info'))
    phase_value = safe_get(image_header,
                           'tags.PhaseEncodingDirectionPositive.items')
    phpl = None
    if phase_value:
        phpl = phase_value[0]

    values = {'MultiSliceMode'              : slice_mode,
              'ParallelAcquisitionTechnique': ipat,
              'ShimSetting'                 : shim_setting,
              'ShimMode'                    : shim,
              'PhasePolarity'               : phpl}

    return csa_header, values


def get_header(dicom: pydicom.FileDataset, name: str):
    """
    Extracts value from dicom headers looking up the corresponding HEX tag
    in config.HEADER_TAGS

    Parameters
    ----------
    dicom : pydicom.FileDataset
        dicom object read from pydicom.read_file

    name : str
        parameter name such as ImageHeader or SeriesHeader

    Returns
    -------
    This method return a value for the given key. If key is not available,
    then returns default value None.
    """
    data = dicom.get(config.HEADER_TAGS[name], None)
    if data:
        return data.value
    return None


def get_csa_props(parameter, corpus):
    """Extract parameter code from CSA header text

    we want 0x1 from e.g.
    sAdjData.uiAdjShimMode                = 0x1
    """
    index = corpus.find(parameter)
    if index == -1:
        return -1

    # checks for atleast one character after equal sign
    shift = len(parameter) + 6
    if index + shift > len(corpus):
        print(f"#WARNING: {parameter} in CSA too short: '{corpus[index:]}'")
        return -1

    # 1st value -  parameter name, 2nd value - equals sign, 3rd value - parameter
    # value
    param_val = corpus[index:]
    code_parts = re.split('[\t\n]', param_val)
    if len(code_parts) >= 3:
        return code_parts[2]

    # if not above, might look like:
    # sAdjData.uiAdjShimMode                = 0x1

    # this runs multiple times on every dicom
    # regexp is expesive? dont use unless we need to
    match = re.search(r'=\s*([^\n]+)', corpus[index:])
    if match:
        match = match.groups()[0]
        # above is also a string. dont worry about conversion?
        # match = int(match, 0)  # 0x1 -> 1
        return match

    # couldn't figure out
    return -1


# TODO : rename csa
def header_exists(dicom: pydicom.FileDataset) -> bool:
    """
    Check if the private SIEMENS header exists in the file or not. Some
    parameters like effective_echo_spacing and shim method need the dicom
    header to be present.

    Parameters
    ----------
    dicom : pydicom.FileDataset
        dicom object read from pydicom.read_file

    Returns
    -------
    bool
    """
    try:
        series = get_header(dicom, 'series_header_info')
        image = get_header(dicom, 'image_header_info')
        series_header = csareader.read(series)

        # just try reading these values, to bypass any errors,
        # don't need these values now
        # image_header = \
        csareader.read(image)
        # items = \
        series_header['tags']['MrPhoenixProtocol']['items'][0].split('\n')
        return True
    except Exception as e:
        logger.warn(f'Expects dicom files from Siemens to be able to'
                    f' read the private header. For other vendors,'
                    f'private header is skipped. '
                    f'{e} in {dicom.filename}')
        # "Use --skip_private_header to create report".format(e))
        # raise e
        return False


def get_effective_echo_spacing(dicom: pydicom.FileDataset,
                               not_found_value=Unspecified
                               ) -> Optional[float]:
    """
    Calculates effective echo spacing in sec.
    * For Siemens
    Effective Echo Spacing (s) =
    (BandwidthPerPixelPhaseEncode * MatrixSizePhase)^-1

    * For Philips
    echo spacing (msec) =
     1000*water-fat shift (per pixel)/(water-fat shift(in Hz)*echo_train_length)

    Parameters
    ----------
    dicom : pydicom.FileDataset

    Returns
    -------
    float value for effective echo spacing
    """

    bwp_phase_encode = get_dicom_param_value(dicom, 'PixelBandwidth')
    phase_encoding = get_dicom_param_value(dicom, 'PhaseEncodingSteps')

    if (bwp_phase_encode is None) or (phase_encoding is None):
        return not_found_value
    denominator = (bwp_phase_encode * phase_encoding)
    if denominator:
        value = 1000 / denominator
        # Match value to output of dcm2niix
        return value / 1000
    else:
        return not_found_value


def import_string(dotted_path):
    """
    Import a dotted module path and return the attribute/class designated by the
    last name in the path. Raise ImportError if the import failed.
    """
    try:
        module_path, class_name = dotted_path.rsplit(".", 1)
    except ValueError as err:
        raise ImportError(
            "%s doesn't look like a module path" % dotted_path) from err

    module = import_module(module_path)

    try:
        return getattr(module, class_name)
    except AttributeError as err:
        raise ImportError(
            'Module "%s" does not define a "%s" attribute/class'
            % (module_path, class_name)
            ) from err


def convert2ascii(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize(
            'NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value)
    return re.sub(r'[-\s]+', '-', value).strip('-_')


def get_sequence_name(dicom: pydicom.FileDataset) -> str:
    """
    Infer modality through dicom tags. In most cases series_description
    should explain the modality of the volume, otherwise either use sequence
    name or protocol name from DICOM metadata

    Parameters
    ----------
    dicom : pydicom.FileDataset
        dicom object read from pydicom.read_file

    Returns
    -------
    str
    """

    value = dicom.get('SeriesDescription', None)
    if value is None:
        value = dicom.get('SequenceName', None)
    if value is None:
        value = dicom.get('ProtocolName', None)

    if value is None:
        raise ValueError('Could not query either '
                         'SequenceName or SeriesDescription or ProtocolName')

    value = str(value.replace(" ", "_"))

    return convert2ascii(value)


def boolify(s):
    if s == 'True':
        return True
    if s == 'False':
        return False
    raise ValueError("huh?")


def auto_convert(s):
    """convert pydicom values to python data types for ease of use"""

    for fn in (boolify, int, float):
        try:
            return fn(s)
        except ValueError:
            continue
    if isinstance(s, str):
        return s.strip()
    return s


def read_json(filepath: Path):
    if isinstance(filepath, str):
        filepath = Path(filepath)
    elif not isinstance(filepath, Path):
        raise FileNotFoundError(f'Expected str or pathlib.Path, '
                                f'Got {type(filepath)}')

    if not filepath.is_file():
        raise FileNotFoundError(f'File not found: {filepath}')

    with open(filepath, 'r') as fp:
        try:
            dict_ = json.load(fp)
        except json.decoder.JSONDecodeError as e:
            raise ValueError(f'Error while reading {filepath}: {e}')
    return dict_
