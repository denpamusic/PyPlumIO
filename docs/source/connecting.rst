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

.. autoclass:: pyplumio.protocol.Protocol

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
    from pyplumio.protocol import DummyProtocol
    from pyplumio.frames import requests, responses

    async def main():
        """Open a connection and request alerts."""
        async with pyplumio.open_tcp_connection(
            host="localhost",
            port=8899,
            protocol=DummyProtocol
        ) as connection:
            await connection.write(request.AlertsRequest(recipient=DeviceType.ECOMAX))

            while connection.connected:
                if isinstance((frame := await connection.read()), responses.AlertsResponse):
                    print(frame.data)
                    break

    asyncio.run(main())

All built-in protocols are listed below.

.. autoclass:: pyplumio.protocol.DummyProtocol
.. autoclass:: pyplumio.protocol.AsyncProtocol

Network Information
-------------------
When opening the connection, you can send ethernet and wireless
network information to the ecoMAX controller using one or both
of data classes below.

.. autoclass:: pyplumio.structures.network_info.EthernetParameters
    :members:

.. autoclass:: pyplumio.structures.network_info.WirelessParameters
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
        ) as connection:
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
                ecomax = await conn.get("ecomax", timeout=10)
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
            ecomax = await connection.get("ecomax", timeout=10)
        except asyncio.TimeoutError:
            # If device times out, log the error.
            _LOGGER.error("Failed to get the device within 10 seconds")
        
        # Close the connection.
        await connection.close()
        

    # Run the coroutine in asyncio event loop.
    asyncio.run(main())
