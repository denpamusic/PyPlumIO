Statistics
==========

About Statistics
----------------

Since PyPlumIO v0.5.56, you can access statistics via following property.

.. autoattribute:: pyplumio.protocol.AsyncProtocol.statistics

Statistics contain transfer data consisting of number of received/sent frames and bytes
as well as datetime of when connection was established, when connection was lost and
number of connection loss event.

.. autoclass:: pyplumio.protocol.Statistics

The `devices` property of statistics class of also contains a list of
device statistics objects.

.. autoclass:: pyplumio.protocol.DeviceStatistics

Statistics Examples
-------------------

You can easily access statistic object via proxy call through Connection object
as in example below.

.. code-block:: python

    import asyncio

    import pyplumio

    async def main():
        """Read the current heating temperature."""
        async with pyplumio.open_tcp_connection("localhost", 8899) as conn:
            print(conn.statistic)


    asyncio.run(main())