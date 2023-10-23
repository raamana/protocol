API Reference
=============

This is the API reference for the protocol which might be helpful fo users who want to add
their own parameters and acquisition protocol for MR data acquisition. The API is divided into
two categories: the high-level API and the low-level API.

High-level API
--------------
The high-level API is the most convenient way to add new parameters and acquisition protocols.
It is based on the core API and provides a simple interface to add new parameters and protocols.

.. automodule:: protocol.imaging
   :members: ImagingSequence, SiemensMRImagingProtocol, MRImagingProtocol, RepetitionTime, EchoTime, PhaseEncodingDirection
   :show-inheritance:


Core API
--------
The core API is the low-level API which is used by the high-level API. It provides the
basic functionality to add new parameters and acquisition protocols.

.. automodule:: protocol.base
   :members:
   :undoc-members:
   :show-inheritance:
