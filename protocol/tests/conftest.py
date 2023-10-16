from pathlib import Path

import pydicom
import pytest


@pytest.fixture()
def sample_dcm(request):
    folder_path = Path(__file__).resolve().parent / 'data'
    testdcm = get_test_dcm(folder_path / 'epi_pe_ap-00001.dcm')
    return testdcm

def get_test_dcm(filename):
    try:
        dicom = pydicom.dcmread(filename)
    except:
        raise FileNotFoundError('File not found')
    return dicom
