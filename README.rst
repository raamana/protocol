========
protocol
========

``protocol`` is a class-driven library for representing acquisition protocols
as structured objects instead of loose config files or one-off scripts.

The central idea is simple and still unusually strong: a protocol is made of
sequences, and sequences are made of typed parameters with their own compliance
logic. That gives you a clean object model for comparing observed data against
reference expectations, inferring protocols from datasets, and parsing vendor
protocol exports into reusable reference objects.

This design was built against many open neuroimaging datasets and it shows in
the API: the abstractions are opinionated, layered, and practical.


Why The Design Is Strong
------------------------

``protocol`` does not treat a protocol as just a dictionary. It models the
domain explicitly:

- ``BaseParameter`` represents one acquisition property with its own type,
  units, validity, and compliance behavior.
- ``BaseSequence`` acts like a mutable mapping of parameters, but keeps the
  parameter objects intact rather than flattening everything to raw values.
- ``BaseProtocol`` and ``MRImagingProtocol`` represent reference collections of
  sequences that can be compared against observed datasets.
- ``DicomImagingSequence`` and ``BidsImagingSequence`` let the same conceptual
  sequence be populated from different real-world sources.
- ``SiemensMRImagingProtocol`` turns Siemens XML exports into structured
  protocol objects instead of forcing users to hand-parse vendor files.

That layered class design is the real strength of the library. It gives you:

- composable protocol objects instead of ad hoc parsing code
- compliance checks at the parameter, sequence, and protocol levels
- a bridge from vendor-specific metadata to canonical sequence objects
- a path to protocol inference when no formal reference file exists
- a foundation for QA tooling such as ``mrQA`` without hardwiring all logic
  into one monolith


Examples Of The Class Design
----------------------------

1. Parameters are first-class objects

Every parameter is a real object with comparison semantics, not just a scalar.
That means numeric parameters can respect tolerances while categorical
parameters can keep their own domain-specific validation behavior.

Examples in the codebase:

- ``BaseParameter`` in ``protocol/base.py``
- ``NumericParameter`` and related subclasses in ``protocol/base.py``
- domain-specific parameter classes such as ``MagneticFieldStrength`` and
  ``ReceiveCoilActiveElements`` in ``protocol/imaging.py``

2. Sequences are mutable containers of parameter objects

``BaseSequence`` subclasses ``MutableMapping``, so a sequence behaves like a
mapping while still preserving typed parameter instances. That is a subtle but
powerful choice: the public surface is ergonomic, but the internal model still
knows about units, tolerances, acronyms, and compliance behavior.

Examples in the codebase:

- ``BaseSequence`` in ``protocol/base.py``
- ``ImagingSequence.from_dict(...)`` in ``protocol/imaging.py`` to build a
  sequence from parameter dictionaries
- ``BaseSequence.compliant(...)`` in ``protocol/base.py`` to compare sequences
  parameter by parameter

3. Protocols are reference objects, not just files

``MRImagingProtocol`` stores a set of named sequences and lets you compare full
protocols or retrieve the reference sequence that corresponds to an observed
sequence.

Examples in the codebase:

- ``MRImagingProtocol.add(...)`` in ``protocol/imaging.py``
- ``MRImagingProtocol.add_sequence_from_dict(...)`` in ``protocol/imaging.py``
- ``MRImagingProtocol.compliant(...)`` in ``protocol/imaging.py``

4. Vendor-specific exports become reusable protocol objects

``SiemensMRImagingProtocol`` is one of the most distinctive parts of the
library. It parses Siemens XML protocol exports into structured sequences and
maps vendor-facing cards and labels into canonical parameters such as
``RepetitionTime``, ``EchoTime``, ``FlipAngle``, and
``PhaseEncodingDirection``.

Examples in the codebase:

- ``SiemensMRImagingProtocol.from_xml(...)``
- ``SiemensMRImagingProtocol._collect_sequences_by_program(...)``
- ``SiemensMRImagingProtocol._get_parameter(...)``

5. The same protocol concepts can be populated from DICOM or BIDS

The library already recognizes that the conceptual sequence matters more than
the raw storage format. ``DicomImagingSequence`` and ``BidsImagingSequence``
both populate imaging sequences from different sources while preserving the same
higher-level protocol model.

Examples in the codebase:

- ``BidsImagingSequence.parse(...)`` in ``protocol/imaging.py``
- ``DicomImagingSequence.parse(...)`` in ``protocol/imaging.py``
- alias handling through analogue-name lookup in ``protocol/config.py`` and
  ``ImagingSequence.import_string(...)``


What This Lets You Do
---------------------

Check whether two observed sequences are compatible:

.. code:: python

    from pydicom import dcmread
    from protocol import DicomImagingSequence

    seq1 = DicomImagingSequence(dicom=dcmread("sub-01_T1w.dcm"))
    seq2 = DicomImagingSequence(dicom=dcmread("sub-02_T1w.dcm"))

    compliant, differences = seq1.compliant(seq2, rtol=0.0, decimals=3)


Build a reference protocol from dictionaries:

.. code:: python

    from protocol import MRImagingProtocol

    reference = MRImagingProtocol(name="Example Protocol")
    reference.add_sequence_from_dict(
        "T1w",
        {
            "RepetitionTime": 2300,
            "EchoTime": 2.98,
            "FlipAngle": 9,
        },
    )


Parse a Siemens XML export into a reusable protocol object:

.. code:: python

    from protocol import SiemensMRImagingProtocol

    siemens_protocol = SiemensMRImagingProtocol(filepath="scanner_export.xml")
    program_names = list(siemens_protocol.get_program_names())
    reference_t1w = siemens_protocol["T1w"]


Compare an observed sequence against a reference sequence:

.. code:: python

    from pydicom import dcmread
    from protocol import DicomImagingSequence, SiemensMRImagingProtocol

    observed = DicomImagingSequence(dicom=dcmread("subject_T1w.dcm"))
    reference = SiemensMRImagingProtocol(filepath="scanner_export.xml")

    compliant, non_compliant_parameters = reference[observed.name].compliant(
        observed,
        rtol=0.0,
        decimals=3,
    )


Current Scope
-------------

The current release focuses on MRI acquisition protocols and related medical
imaging use cases, especially neuroimaging QA and protocol compliance. The
architecture is broader than the current release surface, which is part of what
makes the library interesting: it already contains the seeds of a more general
protocol modeling system.


Documentation
-------------

* Docs with examples: https://raamana.github.io/protocol
* License: Apache-2.0
