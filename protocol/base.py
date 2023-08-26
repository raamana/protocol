# -*- coding: utf-8 -*-

"""Main module containing the core classes."""

from abc import ABC, abstractmethod
from collections.abc import Iterable, MutableMapping
from numbers import Number
from typing import Union, List
from warnings import warn

import numpy as np
from protocol.config import (UnspecifiedType, Unspecified,
                             SUPPORTED_IMAGING_MODALITIES)
from protocol import logger


# A [imaging] Parameter is a container class for a single value, with a name
#       with methods to check for compliance and validity
# A [imaging] Sequence is defined as a set of parameters
#       implemented as a dict
# A [Sequence] Protocol is an unmutable Sequence for reference
# An Imaging Protocol is an ordered sequence of Sequences for a single session
#       although their order isn't used or checked in any way


class BaseParameter(ABC):
    """
    Container class to support various parameter data types
      including numerical continuous (time), categorical (site), or an array of them
    """

    def __init__(self,
                 name='parameter',
                 value=Unspecified,
                 dtype=float,
                 units='ms',
                 steps=1,
                 range=None,
                 required=True,
                 severity='critical',
                 dicom_tag=None,
                 acronym=None):
        """constructor"""

        self.required = required
        self.severity = severity

        self.value = value
        self.dtype = dtype
        self.units = units
        self.range = range
        self.steps = steps

        self.name = name
        self.acronym = acronym
        self.dicom_tag = dicom_tag

        self.decimals = 2  # numerical tolerance in decimal places

    def compliant(self, other):
        """Method to check if one parameter value is compatible w.r.t another,
            either in equality or within acceptable range, for that data type.

        If any of the values to be compared are UnspecifiedType, it returns False
        """

        if isinstance(self.value, UnspecifiedType) or isinstance(other.value, UnspecifiedType):
            warn('one of the values being compared is UnspecifiedType'
                 f'in {self.name}',
                 UserWarning)
            return False
        else:
            return self._check_compliance(other)

    @abstractmethod
    def _check_compliance(self, other):
        """Method to check if one parameter value is compatible w.r.t another,
            either in equality or within acceptable range, for that data type.
        """

    @abstractmethod
    def _cmp_value(self, other):
        """
        Method to compare the values of two parameters
        """

    @abstractmethod
    def _cmp_units(self, other):
        """
        Method to compare the units of two parameters
        """

    def __eq__(self, other):
        """equality is defined as compliance here"""

        return self.compliant(other)

    def __hash__(self):
        return hash(self.__repr__())

    def __repr__(self):
        """repr"""

        name = self.acronym if self.acronym else self.name
        return f'{name}({self.value})'

    def __str__(self):
        return self.__repr__()


class VariableNumericParameter(BaseParameter):
    """Parameter specific class for EchoTime"""

    def __init__(self,
                 name,
                 value,
                 dicom_tag,
                 acronym,
                 units=None,
                 range=None,
                 steps=None,
                 required=True,
                 severity='critical', ):
        """Constructor."""

        super().__init__(name=name,
                         value=value,
                         dtype=Number,
                         units=units,
                         range=range,
                         steps=steps,
                         required=required,
                         severity=severity,
                         dicom_tag=dicom_tag,
                         acronym=acronym)

        if not isinstance(value, UnspecifiedType):
            if isinstance(value, Iterable):
                if not all([isinstance(v, self.dtype) for v in value]):
                    raise TypeError(f'Input {value} is not of type {self.dtype}'
                                    f' for {self.name}')
                self.value = sorted([float(v) for v in value])

            elif isinstance(value, self.dtype):
                self.value = [float(value)]
            else:
                raise TypeError(f'Input {value} is not of type {self.dtype} for'
                                f' {self.name}')

        # overriding default from parent class
        self.decimals = 3

    def _check_compliance(self, other):
        """Method to check if one parameter value is compatible w.r.t another,
            either in equality or within acceptable range, for that data type.
        """
        return self._cmp_value(other) and self._cmp_units(other)

    def _cmp_value(self, other):
        # tolerance is 1e-N where N = self.decimals
        for v, o in zip(self.value, other.value):
            if not np.isclose(v, o, atol=1 ** -self.decimals):
                return False
        return True

    def _cmp_units(self, other):
        # TODO: implement unit conversion
        return self.units == other.units


class NumericParameter(BaseParameter):
    """Parameter specific class for RepetitionTime"""

    def __init__(self,
                 name,
                 value,
                 dicom_tag,
                 acronym,
                 units=None,
                 range=None,
                 steps=None,
                 required=True,
                 severity='critical', ):
        """Constructor."""

        super().__init__(name=name,
                         value=value,
                         dtype=Number,
                         units=units,
                         range=range,
                         steps=steps,
                         required=required,
                         severity=severity,
                         dicom_tag=dicom_tag,
                         acronym=acronym)

        if not isinstance(value, UnspecifiedType):
            if not isinstance(value, self.dtype):
                raise TypeError(f'Input {value} is not of type {self.dtype} for'
                                f' {self.name}')

            self.value = float(value)

        # overriding default from parent class
        self.decimals = 3

    def _check_compliance(self, other):
        """Method to check if one parameter value is compatible w.r.t another,
            either in equality or within acceptable range, for that data type.
        """
        return self._cmp_value(other) and self._cmp_units(other)

    def _cmp_value(self, other):
        # tolerance is 1e-N where N = self.decimals
        if np.isclose(self.value, other.value, atol=1 ** -self.decimals):
            return True
        else:
            return False

    def _cmp_units(self, other):
        # TODO: implement unit conversion
        return self.units == other.units


class CategoricalParameter(BaseParameter):
    """Parameter specific class for PhaseEncodingDirection"""

    def __init__(self,
                 name,
                 value,
                 dicom_tag,
                 acronym,
                 dtype=Iterable,
                 required=True,
                 severity='critical',
                 units=None,
                 range=None,
                 allowed_values=tuple()):

        """Constructor."""

        super().__init__(name=name,
                         value=value,
                         dtype=dtype,
                         units=units,
                         range=range,
                         required=required,
                         severity=severity,
                         dicom_tag=dicom_tag,
                         acronym=acronym)

        self.allowed_values = allowed_values
        if not isinstance(value, UnspecifiedType):
            if not isinstance(value, self.dtype):
                try:
                    value = self.dtype(value)
                except TypeError:
                    raise TypeError(f'Got input {value} of type {type(value)}. '
                                    f'Expected {self.dtype} for {self.name}')

        # if allowed_values is set, check if input value is allowed
        if self.allowed_values and (value not in self.allowed_values):
            raise ValueError(f'Invalid value for {self.name}. '
                             f'Must be one of {self.allowed_values}')

        self.value = str(value).upper()

    def _check_compliance(self, other):
        """Method to check if one parameter value is compatible w.r.t another,
            either in equality or within acceptable range, for that data type.
        """
        return self._cmp_value(other) and self._cmp_units(other)

    def _cmp_units(self, other):
        # TODO: implement unit conversion
        return self.units == other.units

    def _cmp_value(self, other):
        if isinstance(other, type(self)):
            value_to_compare = other.value
        elif isinstance(other, self.dtype):
            value_to_compare = other
        else:
            raise TypeError(f'Invalid type. Must be an instance of '
                            f'{self.dtype} or {self}')

        return self.value == value_to_compare


class BaseSequence(MutableMapping):
    """Container to capture imaging parameter values for a given sequence.

    Intended usage:

    seq = Sequence()
    seq.params['name'] = value

    if seq1.compliant(seq2):
        # they are compliant
    else:
        # not compliant

    """

    def __init__(self,
                 name: str = 'Sequence',
                 params: dict = None,
                 path: str = None,):
        """constructor"""

        super().__init__()

        self.name = name
        self.params = set()
        self.path = path
        self.subject_id = None
        self.session_id = None
        self.run_id = None
        if isinstance(params, dict):
            self.params = set(list(params.keys()))
            self.__dict__.update(params)

        # parameters and their values can be modified
        self._mutable = True

    def set_session_info(self, subject_id: str, session_id: str, run_id: str):
        """method to add metadata to the sequence"""
        self.subject_id = subject_id
        self.session_id = session_id
        self.run_id = run_id

    def get_session_info(self):
        """method to get metadata to the sequence"""
        return self.subject_id, self.session_id, self.run_id

    def add(self, param_list: Union[BaseParameter, List[BaseParameter]]):
        """method to add new parameters; overwrite previous values if exists."""

        if not isinstance(param_list, Iterable):
            param_list = [param_list, ]

        for param in param_list:
            if not isinstance(param, BaseParameter):
                raise ValueError(
                    f'Input value {param} is not of type BaseParameter')

            # retaining full Parameter instance, not just value
            self.__dict__[param.name] = param
            self.params.add(param.name)

    def __setitem__(self,
                    key: str,
                    value: BaseParameter):
        """setter"""

        if not isinstance(value, BaseParameter):
            raise ValueError('Input value is not of type BaseParameter')

        if not isinstance(key, str):
            raise ValueError('Input name is not a string!')

        self.__dict__[key] = value
        self.params.add(key)

    def get(self, name, not_found_value=None):
        self.__getitem__(name=name, not_found_value=not_found_value)

    def __getitem__(self, name,
                    not_found_value=None):
        """getter"""

        try:
            return self.__dict__[name]
        except KeyError:
            if not_found_value is not None:
                return not_found_value
            else:
                raise KeyError(f'{name} has not been set yet')

    def compliant(self, other):
        """Method to check if one sequence is compatible w.r.t another,
            either in equality or within acceptable range, for each parameter.
        """

        if not isinstance(other, BaseSequence):
            raise TypeError(f'Sequence to compare {other} is not of type '
                            f'BaseSequence')

        if self.params != other.params:
            diff = self.params.symmetric_difference(other.params)
            warn('different sets of parameters - '
                 'below params exist in one but not the other :\n\t{}'
                 ''.format(diff))
            return False, diff  # TODO varying dtype: list of names!

        non_compliant_params = list()

        for pname in self.params:
            this_param = self.__dict__[pname]
            that_param = other[pname]
            if not that_param.compliant(this_param):
                non_compliant_params.append((this_param, that_param))

        bool_flag = len(non_compliant_params) < 1

        return bool_flag, non_compliant_params  # list of BaseParameter classes

    def __eq__(self, other):
        """equivalence operator"""

        bool_flag, _ = self.compliant(other)
        return bool_flag

    def __delitem__(self, key):
        del self.__dict__[key]
        self.params.remove(key)

    def __iter__(self):
        return iter(self.params)

    def __len__(self):
        return len(self.params)

    def __str__(self):
        """human readable representation"""

        plist = list()
        for key in self.params:
            param = self.__dict__[key]
            name = param.acronym if param.acronym else param.name
            plist.append(f'{name}={param.value}')

        return '{}({})'.format(self.name, ','.join(plist))

    def __repr__(self):
        return self.__str__()


class BaseProtocol():
    """
    Base class for all protocols.

    A protocol is a sequence, except it is not mutable, to serve as a reference.
    """

    def __init__(self,
                 name="Protocol"):
        """constructor"""
        self._mutable = False


class BaseImagingProtocol(BaseProtocol):
    """Base class for all imaging protocols such as MRI / neuroimaging.
    """

    def __init__(self,
                 name='ImagingProtocol',
                 category='MR'):
        """constructor
        """

        super().__init__(name=name)

        # to distinguish between different types of imaging: MR, CT, XRAY etc.
        #   as they touch different portions of DICOM
        if category not in SUPPORTED_IMAGING_MODALITIES:
            raise TypeError(f'This modality {category} not supported.'
                            f'Choose one of {SUPPORTED_IMAGING_MODALITIES}')
        else:
            self._category = category


class BaseMRImagingProtocol(BaseImagingProtocol):
    """Base class for all MR imaging protocols, including neuroimaging datasets
    """

    def __init__(self,
                 name="MRIProtocol",
                 path=None):
        """constructor"""

        super().__init__(name=name, category='MR')

        self._seq = dict()

    def add(self, seq):
        """Adds a new sequence to the current protocol"""

        if not isinstance(seq, BaseSequence):
            raise TypeError(
                'Invalid type! Must be a valid instance of BaseSequence')

        if seq.name in self._seq:
            raise ValueError(
                'This sequence already exists! Double check or rename!')

        self._seq[seq.name] = seq

    def __bool__(self):
        """Checks if the protocol is empty"""

        if len(self._seq) < 1:
            return False
        else:
            return True

    def __getitem__(self, name):
        """getter"""

        try:
            return self._seq[name]
        except KeyError:
            raise KeyError(f'{name} has not been set yet')

# MR_protocol = BaseMRImagingProtocol('MRP')
#
# MR_protocol['param']
# MR_protocol['param'] = value
#
# MR_protocol.set_param(name, value)
# MR_protocol.get_param(name)
#
# mrds = MRdataset()
#
# mrds[subject, session, run] = list()  # list of volumes from different modalities
# mrds[modality] = list()  # list of all sessions with that modality
#
# MRdataset
