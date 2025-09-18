Connecting
==========

Opening the connection
----------------------

.. autofunction:: pyplumio.open_tcp_connection

With this you can connect to the controller remotely via RS-485 to
Ethernet/WiFi converters, which are readily available online or
can be custom built using wired connection and ser2net software.

.. code-block:: python
    
    import pyplumio

    async with pyplumio.open_tcp_connection("localhost", port=8899) as conn:
        ...


.. note::

    Although **async with** syntax is preferred, you can initiate connection without it.
    See following :ref:`examples<Connection Examples>` for more information.

.. autofunction:: pyplumio.open_serial_connection

You can connect to the ecoMAX controller via wired connection through
RS-485 to USB or RS-485 to TTL adapters, that are connected directly
to the device running PyPlumIO.

You MUST not connect RS-485 lines directly to the UART outputs of your
PC or you'll risk damaging your PC/controller or the ecoMAX controller itself.

.. code-block:: python
    
    import pyplumio

    async with pyplumio.open_serial_connection("/dev/ttyUSB0", baudrate=115200) as conn:
        ...

Protocols
---------

Connection helpers and classes allow to specify custom protocol to handle data, once
connection is established.

All protocols should inherit following abstract base class:

.. autoclass:: pyplumio.Protocol

Most of documentation assumes that protocol is left as is, which
is by default AsyncProtocol. However, setting different protocol
allows for more fine-grained control over data processing.

In following example we'll set protocol to DummyProtocol, request and
output alerts and close the connection without an additional overhead of
working with device classes and queues.

.. code-block:: python

    import asyncio

    import pyplumio
    from pyplumio.const import DeviceType
    from pyplumio.frames import requests, responses


    async def main():
        """Open a connection and request alerts."""
        async with pyplumio.open_tcp_connection(
            host="localhost", port=8899, protocol=pyplumio.DummyProtocol()
        ) as conn:
            await conn.writer.write(
                requests.AlertsRequest(recipient=DeviceType.ECOMAX, start=0, count=5)
            )

            while conn.connected:
                try:
                    if isinstance(
                        (frame := await conn.reader.read()), responses.AlertsResponse
                    ):
                        print(frame.data)
                        break
                except pyplumio.ProtocolError:
                    # Skip protocol errors and read the next frame.
                    pass


    asyncio.run(main())

All built-in protocols are listed below.

.. autoclass:: pyplumio.DummyProtocol
.. autoclass:: pyplumio.AsyncProtocol

Network Information
-------------------
When opening the connection, you can send ethernet and wireless
network information to the ecoMAX controller by passing one or both
of data classes below to the Protocol of your choice.

.. autoclass:: pyplumio.EthernetParameters
    :members:

.. autoclass:: pyplumio.WirelessParameters
    :members:

    .. autoattribute:: status

Once set, network information will be shown in information section
on the ecoMAX panel.

In the example below, we'll set both ethernet and wireless parameters.

.. code-block:: python

    import pyplumio
    from pyplumio.const import EncryptionType


    async def main():
        """Initialize a connection with network parameters."""
        async with pyplumio.open_tcp_connection(
            host="localhost",
            port=8899,
            protocol=pyplumio.AsyncProtocol(
                ethernet_parameters=pyplumio.EthernetParameters(
                    ip="10.10.1.100",
                    netmask="255.255.255.0",
                    gateway="10.10.1.1",
                ),
                wireless_parameters=pyplumio.WirelessParameters(
                    ip="10.10.2.100",
                    netmask="255.255.255.0",
                    gateway="10.10.2.1",
                    ssid="My SSID",
                    encryption=EncryptionType.WPA2,
                    signal_quality=100,
                ),
            ),
        ) as conn:
            ...

Statistics
----------

Since PyPlumIO v0.5.56, you can access statistics via following property.

.. autoattribute:: pyplumio.protocol.AsyncProtocol.statistics

Statistics contain transfer data consisting of number of received/sent frames and bytes
as well as datetime of when connection was established, when connection was lost and
number of connection loss event.

.. autoclass:: pyplumio.protocol.Statistics
    :members:
    :exclude-members: update_transfer_statistics, track_connection_loss, reset_transfer_statistics

The `devices` property of statistics class of also contains a list of
device statistics objects. Those statistics include time the device was initially
connected as well as time, when device was last seen (sent an :ref:`RegulatorData`
message).

.. autoclass:: pyplumio.protocol.DeviceStatistics
    :members:
    :exclude-members: update_last_seen

In the following example we'll print connection statistics after establishing a
connection.

.. code-block:: python

    import pyplumio


    async def main():
        """Print connection statistics."""
        async with pyplumio.open_tcp_connection("localhost", 8899) as conn:
            print(conn.statistics)
            ...

Connection Examples
-------------------

The following example illustrates opening a TCP connection using Python's
context manager.

.. code-block:: python

    import asyncio
    import logging

    import pyplumio


    _LOGGER = logging.getLogger(__name__)


    async def main():
        """Opens the connection and gets the ecoMAX device."""
        async with pyplumio.open_tcp_connection("localhost", port=8899) as conn:
            try:
                # Get the ecoMAX device within 10 seconds or timeout.
                async with conn.device("ecomax", timeout=10) as ecomax:
                    ...
            except asyncio.TimeoutError:
                # If device times out, log the error.
                _LOGGER.error("Failed to get the device within 10 seconds")
        

    # Run the coroutine in asyncio event loop.
    asyncio.run(main())

The following example illustrates opening a TCP connection without
using Python's context manager.

.. code-block:: python

    import asyncio
    import logging

    import pyplumio


    _LOGGER = logging.getLogger(__name__)


    async def main():
        """Opens the connection and gets the ecoMAX device."""
        connection = pyplumio.open_tcp_connection("localhost", port=8899)

        # Connect to the device.
        await connection.connect()
        
        try:
            # Get the ecoMAX device within 10 seconds or timeout.
            async with conn.device("ecomax", timeout=10) as ecomax:
                ...
        except asyncio.TimeoutError:
            # If device times out, log the error.
            _LOGGER.error("Failed to get the device within 10 seconds")

        # Close the connection.
        await connection.close()
        

    # Run the coroutine in asyncio event loop.
    asyncio.run(main())
