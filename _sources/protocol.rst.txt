Protocol
========

About Protocol
--------------

Plum devices use RS-485 standard for communication.

Each frame consists of header (7 bytes), message type (1 byte),
message data (optional), CRC (1 byte) and frame end delimiter (1 byte).
The minimum frame size therefore is 10 bytes.

Protocol supports unicast and broadcast frames.
Broadcast frames will always have their recipient address set
to **0x00**, while unicast messages will have specific device address.
ecoMAX controller address is **0x45**, ecoSTER panel
address is **0x51**.

For example, we can request list of editable parameters from the ecoMAX
controller by sending frame with frame type **49** and receive response
with frame type **177** that contains requested parameters.

Frame structure
---------------

* Header:
    * [Byte] Frame start delimiter. Always **0x68**.
    * [Unsigned Short] Byte size of the frame. Includes CRC and frame end delimiter. 
    * [Byte] Recipient address.
    * [Byte] Sender address.
    * [Byte] Sender type. PyPlumIO uses EcoNET type **48**.
    * [Byte] ecoNET version. PyPlumIO uses version **5**.
* Body:
    * [Byte] Frame type.
    * [Byte*] Message data (optional).
    * [Byte] Frame CRC.
    * [Byte] Frame end delimiter. Always **0x16**.

Communication
-------------

The controller constantly sends out :ref:`ProgramVersion[frame_type=64]<ProgramVersion>` and
:ref:`CheckDevice[frame_type=48]<CheckDevice>` requests to every known device on the
network and broadcasts :ref:`RegulatorData[frame_type=8]<RegulatorData>` message,
that contains basic controller data.

Initial exchange between ecoMAX controller (EM) and
PyPlumIO library (PIO) can be illustrated with following diagram:

+----------+---+-----------+-----------------------------------------------+-------------------------------+
| Sender   |   | Receiver  | Frame                                         | Description                   |
+==========+===+===========+===============================================+===============================+
| EM[0x45] | > | ANY[0x00] | :ref:`RegulatorDataMessage<RegulatorData>`    | Contains ecoMAX data.         |
+----------+---+-----------+-----------------------------------------------+-------------------------------+
| EM[0x45] | > | PIO[0x56] | :ref:`ProgramVersionRequest<ProgramVersion>`  | Program version request.      |
+----------+---+-----------+-----------------------------------------------+-------------------------------+ 
| EM[0x45] | < | PIO[0x56] | :ref:`ProgramVersionResponse<ProgramVersion>` | Contains program version.     |
+----------+---+-----------+-----------------------------------------------+-------------------------------+
| EM[0x45] | > | PIO[0x56] | :ref:`CheckDeviceRequest<CheckDevice>`        | Check device request.         |
+----------+---+-----------+-----------------------------------------------+-------------------------------+
| EM[0x45] | < | PIO[0x56] | :ref:`DeviceAvailableResponse<CheckDevice>`   | Contains network information. |
+----------+---+-----------+-----------------------------------------------+-------------------------------+
| EM[0x45] | > | PIO[0x56] | :ref:`SensorDataMessage<SensorData>`          | Contains ecoMAX sensor data.  |
+----------+---+-----------+-----------------------------------------------+-------------------------------+

.. note::
    
    Device network address is listed in square brackets.

Versioning
----------

Protocol has built-in way to track frame versions. This is used to
synchronize changes between devices.

Both broadcast :ref:`RegulatorData[frame_type=8]<RegulatorData>` and unicast
:ref:`SensorData[frame_type=53]<SensorData>` frames sent by the ecoMAX controller
contain versioning data.

This data can be represented with following dictionary:

.. code-block:: python

    frame_versions: dict[int, int] = {
        49: 37,
        50: 37,
        54: 1,
        56: 5,
        57: 1,
        61: 40767,
        80: 1,
        81: 1,
        82: 1,
        83: 1,
    }


In this dictionary, keys are frame types and values are version numbers.

In example above, frame :ref:`ecomaxparameters` with frame type 49 has version 37.
If we change any parameters either remotely or on the controller itself,
the version number will increase, so PyPlumIO will be able
to tell that it's need to request list of parameters again
to obtain changes.

.. code-block:: python

    frame_versions: dict[int, int] = {
        49: 38,  # Note the version number change.
        50: 37,
        54: 1,
        56: 5,
        57: 1,
        61: 40767,
        80: 1,
        81: 1,
        82: 1,
        83: 1,
    }
