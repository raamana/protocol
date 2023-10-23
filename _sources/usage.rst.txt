The protocol library provides a simple API for creating sequences and acquisition protocols. You can check if
acquisition parameters for two imaging sequences are same. Sequences can also be checked for
compliance against a reference protocol (XML) generated from Siemens scanners.


.. code:: python

    from protocol import ImagingSequence
    from pydicom import dcmread
    from protocol import SiemensMRImagingProtocol

    dcm_seq1 = dcmread('path/to/dicom')
    dcm_seq2 = dcmread('path/to/dicom')
    seq1 = ImagingSequence(dicom=my_dicom)
    seq2 = ImagingSequence(dicom=sub2_dicom)
    is_compliant = seq1.compliant(seq2)

    reference_protocol = SiemensMRImagingProtocol(filepath='path/to/xml')
    # Get sequence from the protocol with the same name, e.g. t1w
    reference_sequence = reference_protocol[seq1.name]
    compliant_flag, non_compliant_parameters = reference_sequence.compliant(seq1)

The ``non_compliant_parameters`` is a list of tuples containing the parameters that are not same as in
the ``reference_sequence``. The first element of the tuple is the parameter in the ``reference_sequence`` and
the second element is the parameter in the ``seq1``.

..
    Apart from dicom, ImagingSequence can also be created using a dictionary of parameters. However, the parameter names must match with respective parameters available in the protocol library. For a full list of parameters available, please refer to the documentation here_.

    .. code:: python

        from protocol import ImagingSequence
        params = {}
        params['RepetitionTime'] = 2000
        params['EchoTime'] = 30
        params['FlipAngle'] = 90

        seq = ImagingSequence()
        seq.from_dict(params)

    This would be helpful in cases where the parameters are not available in the dicom header. It will also be
    helpful in cases when we are not working with dicom files. For example, when we are working with json sidecar
    files. BIDS datasets are a good example of this.



    .. code:: python

        from protocol import ImagingSequence
        from pydicom import dcmread

        # Create a new sequence
        sub1_dicom = dcmread('path/to/dicom')
        sub2_dicom = dcmread('path/to/dicom')

        seq1 = ImagingSequence(
            dicom=sub1_dicom,
            path='path/to/dicom',
        )

        seq2 = ImagingSequence(
            dicom=sub2_dicom,
            path='path/to/dicom',
        )

        # Check compliance
        seq1.compliant(seq2)


    The library supports xml files generated from Siemens scanners.


    .. code:: python




    If an xml file is not available, it is also possible to create a protocol from a list of sequences.


    .. code:: python

        from protocol import MRImagingProtocol
        reference_protocol = MRImagingProtocol(name='My Protocol')
        sequence_name = 'My Sequence'
        params = {}
        reference_protocol.add_sequence_from_dict(sequence_name, params)

    A MRImagingProtocol object can be used to check if a sequence is compliant with the protocol.

    .. code:: python

        sequence_name = 't1w'
        test_sequence = ImagingSequence(
            dicom=sub1_dicom,
            path='path/to/dicom',
        )

        try:
            reference_sequence = reference_protocol[sequence_name]
        except KeyError:
            print('Sequence name not found in protocol')

        compliant_flag, non_compliant_parameters = reference_sequence.compliant(test_sequence)



    Finally, The protocol can be saved to a file using pickle.

    .. code:: python

        import pickle
        pickle.dump(reference_protocol, open('path/to/protocol.pkl', 'wb'))


.. _here: config.html
