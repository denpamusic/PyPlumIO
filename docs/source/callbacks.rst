Callbacks
=========

Description
-----------

PyPlumIO has an extensive event driven system where each device
property is an event that you can subscribe to.

When you subscribe callback to the event, your callback will be
awaited with the property value each time the property is received
from the device by PyPlumIO.

.. note::

    Callbacks must be coroutines defined with **async def**.

Subscribing to events
---------------------

.. autofunction:: pyplumio.devices.Device.subscribe

.. autofunction:: pyplumio.devices.Device.subscribe_once

To remove the previously registered callback, use the
``unsubcribe()`` method.

.. autofunction:: pyplumio.devices.Device.unsubscribe

Filters
-------

PyPlumIO's callback system can be further improved upon by
using built-in filters. Filters allow you to specify when you want your
callback to be awaited.

All built-in filters are described below.

.. autofunction:: pyplumio.filters.aggregate

This filter aggregates value for specified amount of seconds and 
then calls the callback with the sum of values collected.

.. code-block:: python

    from pyplumio.filters import aggregate

    # Await the callback with the fuel burned during 30 seconds.
    ecomax.subscribe("fuel_burned", aggregate(my_callback, seconds=30))


.. autofunction:: pyplumio.filters.on_change

Normally callbacks are awaited each time the PyPlumIO receives data
from the device, regardless of whether value is changed or not.

With this filter it's possible to only await the callback when
value is changed.

.. code-block:: python

    from pyplumio.filter import on_change

    # Await the callback once heating_temp value is changed since
    # last call.
    ecomax.subscribe("heating_temp", on_change(my_callback))

.. autofunction:: pyplumio.filters.debounce

This filter will only await the callback once value is settled across
multiple calls, specified in ``min_calls`` argument.

.. code-block:: python

    from pyplumio.filter import debounce

    # Await the callback once outside_temp stays the same for three
    # consecutive times it's received by PyPlumIO.
    ecomax.subscribe("outside_temp", debounce(my_callback, min_calls=3))

.. autofunction:: pyplumio.filters.throttle

This filter limits how often your callback will be awaited.

.. code-block:: python

    from pyplumio.filter import throttle

    # Await the callback once per 5 seconds, regardless of 
    # how often outside_temp value is being processed by PyPlumIO.
    ecomax.subscribe("outside_temp", throttle(my_callback, seconds=5))

.. autofunction:: pyplumio.filters.delta

Instead of raw value, this filter awaits callback with value change.

It can be used with numeric values, dictionaries, tuples or lists.

.. code-block:: python

    from pyplumio.filter import delta

    # Await the callback with difference between values in current
    # and last await.
    ecomax.subscribe("outside_temp", delta(my_callback))

.. autofunction:: pyplumio.filters.custom

This filter allows to specify filter function that will be called
every time the value is received from the controller.

A callback is awaited once the filter function returns true.

.. code-block:: python

    from pyplumio.filter import custom

    # Await the callback when temperature is higher that 10 degrees
    # Celsius.
    ecomax.subscribe("outside_temp", custom(my_callback, lambda x: x > 10))

Callbacks Examples
------------------

In this example we'll use filter chaining to achieve more complex event
processing.

.. code-block:: python

    from pyplumio.filter import throttle, on_change


    async def my_callback(value) -> None:
        """Prints current heating temperature."""
        print(f"Heating Temperature: {value}")


    async def main():
        """Subscribes callback to the current heating temperature."""
        async with pyplumio.open_tcp_connection("localhost", 8899) as conn:

            # Get the ecoMAX device.
            ecomax = await conn.get("ecomax")

            # Await the callback on value change but no faster than
            # once per 5 seconds.
            ecomax.subscribe("heating_temp", throttle(on_change(my_callback), seconds=5))

            # Wait until disconnected (forever)
            await conn.wait_until_done()


    asyncio.run(main())


In the example below, ``my_callback`` with be called with
current heating temperature on every SensorDataMessage.

.. code-block:: python

    import asyncio

    import pyplumio


    async def my_callback(value) -> None:
        """Prints current heating temperature."""
        print(f"Heating Temperature: {value}")


    async def main():
        """Subscribes callback to the current heating temperature."""
        async with pyplumio.open_tcp_connection("localhost", 8899) as conn:

            # Get the ecoMAX device.
            ecomax = await conn.get("ecomax")

            # Subscribe my_callback to heating_temp event.
            ecomax.subscribe("heating_temp", my_callback)

            # Wait until disconnected (forever)
            await conn.wait_until_done()


    asyncio.run(main())

In the example below, ``my_callback`` with be called with
current target temperature once and ``my_callback2`` will be called
when heating temperature will change more the 0.1 degrees Celsius.

.. code-block:: python

    import asyncio

    import pyplumio
    from pyplumio.filters import on_change


    async def my_callback(value) -> None:
        """Prints heating target temperature."""
        print(f"Target Temperature: {value}")

    async def my_callback2(value) -> None:
        """Prints current heating temperature."""
        print(f"Current Temperature: {value}")

    async def main():
        """Subscribes callback to the current heating temperature."""
        async with pyplumio.open_tcp_connection("localhost", 8899) as conn:
            # Get the ecoMAX device.
            ecomax = await conn.get("ecomax")

            # Subscribe my_callback to heating_target_temp event.
            ecomax.subscribe_once("heating_target_temp", my_callback)

            # Subscribe my_callback2 to heating_temp changes.
            ecomax.subscribe("heating_temp", on_change(my_callback2))

            # Wait until disconnected (forever)
            await conn.wait_until_done()


    asyncio.run(main())