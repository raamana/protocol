# protocol

`protocol` is a class-driven library for representing acquisition protocols as structured objects instead of loose config files or one-off scripts.

We currently cover MRI acquisition protocols and related medical imaging QA workflows. We've tested and refined it with a diverse array of open datasets and real scanner metadata. The abstractions envision can serve broader modalities beyond medical imaging data alone and were built to model protocols as a general concept rather than as one hardcoded file format.

## What Using It Feels Like

You work with protocol objects directly.

You can read observed imaging metadata into sequence objects:

```python
from pydicom import dcmread
from protocol import DicomImagingSequence

seq1 = DicomImagingSequence(dicom=dcmread("sub-01_T1w.dcm"))
seq2 = DicomImagingSequence(dicom=dcmread("sub-02_T1w.dcm"))

compliant, differences = seq1.compliant(seq2, rtol=0.0, decimals=3)
```

You can build a reference protocol in code:

```python
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
```

You can parse a Siemens scanner export into a reusable reference object:

```python
from protocol import SiemensMRImagingProtocol

siemens_protocol = SiemensMRImagingProtocol(filepath="scanner_export.xml")
reference_t1w = siemens_protocol["T1w"]
```

And you can compare observed data against that reference:

```python
from pydicom import dcmread
from protocol import DicomImagingSequence, SiemensMRImagingProtocol

observed = DicomImagingSequence(dicom=dcmread("subject_T1w.dcm"))
reference = SiemensMRImagingProtocol(filepath="scanner_export.xml")

compliant, non_compliant_parameters = reference[observed.name].compliant(
    observed,
    rtol=0.0,
    decimals=3,
)
```

## Why This Is Powerful

That workflow is powerful because the library does not reduce protocols to raw
dictionaries too early.

It gives you:

- a direct path from real metadata sources like DICOM, BIDS, and Siemens XML
  into structured protocol objects
- a rigorous comparison model where parameters, sequences, and protocols each
  have explicit semantics
- a design that stays flexible because different parameter types can carry their
  own validation and compliance logic
- an extensible object model that can absorb new parameter families, vendors,
  or domains without collapsing into one giant parser
- a practical bridge between domain rigor and day-to-day QA workflows

The most important design choice is that the library works from the bottom up
without exposing that complexity to the user. You interact with high-level
sequence and protocol objects, but those objects are grounded in typed
parameters with domain-aware behavior.

## How The Class Design Works

### Parameters are first-class objects

Every parameter is a real object with comparison semantics, not just a scalar.
That means numeric parameters can respect tolerances while categorical
parameters can keep their own domain-specific validation behavior.

Examples in the codebase:

- `BaseParameter` in `protocol/base.py`
- `NumericParameter` and related subclasses in `protocol/base.py`
- domain-specific parameter classes such as `MagneticFieldStrength` and
  `ReceiveCoilActiveElements` in `protocol/imaging.py`

### Sequences are mutable containers of parameter objects

`BaseSequence` subclasses `MutableMapping`, so a sequence behaves like a
mapping while still preserving typed parameter instances. That is a subtle but
powerful choice: the public surface is ergonomic, but the internal model still
knows about units, tolerances, acronyms, and compliance behavior.

Examples in the codebase:

- `BaseSequence` in `protocol/base.py`
- `ImagingSequence.from_dict(...)` in `protocol/imaging.py` to build a sequence
  from parameter dictionaries
- `BaseSequence.compliant(...)` in `protocol/base.py` to compare sequences
  parameter by parameter

### Protocols are reference objects, not just files

`MRImagingProtocol` stores a set of named sequences and lets you compare full
protocols or retrieve the reference sequence that corresponds to an observed
sequence.

Examples in the codebase:

- `MRImagingProtocol.add(...)` in `protocol/imaging.py`
- `MRImagingProtocol.add_sequence_from_dict(...)` in `protocol/imaging.py`
- `MRImagingProtocol.compliant(...)` in `protocol/imaging.py`

### Vendor-specific exports become reusable protocol objects

`SiemensMRImagingProtocol` is one of the most distinctive parts of the library.
It parses Siemens XML protocol exports into structured sequences and maps
vendor-facing cards and labels into canonical parameters such as
`RepetitionTime`, `EchoTime`, `FlipAngle`, and `PhaseEncodingDirection`.

Examples in the codebase:

- `SiemensMRImagingProtocol.from_xml(...)`
- `SiemensMRImagingProtocol._collect_sequences_by_program(...)`
- `SiemensMRImagingProtocol._get_parameter(...)`

### The same protocol concepts can be populated from DICOM or BIDS

The library already recognizes that the conceptual sequence matters more than
the raw storage format. `DicomImagingSequence` and `BidsImagingSequence` both
populate imaging sequences from different sources while preserving the same
higher-level protocol model.

Examples in the codebase:

- `BidsImagingSequence.parse(...)` in `protocol/imaging.py`
- `DicomImagingSequence.parse(...)` in `protocol/imaging.py`
- alias handling through analogue-name lookup in `protocol/config.py` and
  `ImagingSequence.import_string(...)`

## Why It Holds Up

The class design is linear, disciplined, and surprisingly future-facing:

- parameter classes make the library rigorous
- sequence classes make it ergonomic
- protocol classes make it composable
- vendor/file-format adapters make it practical

That combination is why the library has been useful in the wild. It is not just
parsing metadata. It is turning metadata into a reusable, inspectable,
comparable object model.

## Documentation

- Docs with examples: https://raamana.github.io/protocol
- License: Apache-2.0
