Usage
=====

Connecting
----------

TCP
^^^

.. autofunction:: pyplumio.open_tcp_connection

You can connect to the controller remotely via RS-485 to Ethernet/WiFi converters,
which are readily available online or can be custom built using wired connection 
and ser2net software.

.. code-block:: python
    
    import pyplumio

    async with pyplumio.open_tcp_connection("localhost", port=8899) as conn:
        ...


.. note::

    Although **async with** syntax is preferred, you can initiate connection without it.
    See following examples for more information.

RS-485
^^^^^^

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

Examples
^^^^^^^^

The following example illustrates opening the connection using Python's
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

The following example illustrates opening the connection without
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

Reading
-------
PyPlumIO stores collected data from the ecoMAX controller in the data
property of the device class.

.. autoattribute:: pyplumio.devices.Device.data

You can access this property to check what data is currently available.

.. code-block:: python

    ecomax = await conn.get("ecomax")
    print(ecomax.data)

You can also use the data attribute to access the
device properties, but preferred way is through the use of the
getter method.

.. autofunction:: pyplumio.devices.Device.get

The following example will print out current feed water temperature
and close the connection.

.. code-block:: python

    import asyncio

    import pyplumio

    async def main():
        """Opens the connection and reads heating temperature."""
        async with pyplumio.open_tcp_connection("localhost", 8899) as conn:
            # Get the ecoMAX device.
            ecomax = await conn.get("ecomax")

            # Get the heating temperature.
            heating_temp = await ecomax.get("heating_temp")
            ...
            

    asyncio.run(main())

Non-blocking getter
^^^^^^^^^^^^^^^^^^^

If you don't want to wait for a value to become available, you can
use the non-blocking getter. In case the value is not available, default
value will be returned instead.

.. autofunction:: pyplumio.devices.Device.get_nowait

The following example will print out current feed water temperature if
it is available, otherwise it'll print ``60``.

.. code-block:: python

    # Print the heating temperature or 60 it property is not available.
    heating_temp = ecomax.get_nowait("heating_temp", default=60)
    print(heating_temp)

Waiting for a value
^^^^^^^^^^^^^^^^^^^

You can also wait until value is available and then directly access
the attribute under the device object.

.. autofunction:: pyplumio.devices.Device.wait_for

The following example will wait until current feed water temperature is
available and print it out.

.. code-block:: python

    # Wait until the 'heating_temp' property becomes available.
    await ecomax.wait_for("heating_temp")

    # Output the 'heating_temp' property.
    print(ecomax.heating_temp)

Writing
-------

There's multiple ways to write data to the device.

Blocking setter
^^^^^^^^^^^^^^^

.. autofunction:: pyplumio.devices.Device.set

When using blocking setter, you will get the result
represented by the boolean value. **True** if write was successful,
**False** otherwise.

.. code-block:: python

    result = await ecomax.set("heating_target_temp", 65)
    if result:
        print("Heating target temperature was successfully set.")
    else:
        print("Error while trying to set heating target temperature.")

Non-blocking setter
^^^^^^^^^^^^^^^^^^^

You can't access result, when using non-blocking setter as task is done
in the background. You will, however, still get error message in the log
in case of failure.

.. code-block:: python

    ecomax.set_nowait("heating_target_temp", 65)

Parameters
----------

It's possible to get the Parameter object and then modify it using
it's own setter. When using the parameter object, you don't
need to pass the parameter name.

.. autofunction:: pyplumio.helpers.parameter.Parameter.set
.. autofunction:: pyplumio.helpers.parameter.Parameter.set_nowait

.. code-block:: python

    from pyplumio.helpers.parameter import Parameter


    ecomax = await conn.get("ecomax")
    heating_target: Parameter = ecomax.get("heating_target_temp")
    result = heating_target.set(65)

Parameter range
^^^^^^^^^^^^^^^

Each parameter has a range of acceptable values.
PyPlumIO will raise **ValueError** if value is not within
the acceptable range.

You can check allowed range by reading **min_value** and **max_value**
attributes of parameter object. Both values are **inclusive**.

.. code-block:: python

    ecomax = await connection.get("ecomax")
    target_temp = await ecomax.get("heating_target_temp")
    print(target_temp.min_value)  # Minimum allowed target temperature.
    print(target_temp.max_value)  # Maximum allowed target temperature.

Binary parameters
^^^^^^^^^^^^^^^^^

For binary parameters, you can also use boolean **True** or **False**,
string literals "on" or "off" or special **turn_on()** and
**turn_off()** methods.

.. autofunction:: pyplumio.helpers.parameter.BinaryParameter.turn_on
.. autofunction:: pyplumio.helpers.parameter.BinaryParameter.turn_on_nowait
.. autofunction:: pyplumio.helpers.parameter.BinaryParameter.turn_off
.. autofunction:: pyplumio.helpers.parameter.BinaryParameter.turn_off_nowait

One such parameter is "ecomax_control" that allows you to switch
the ecoMAX on or off.

.. code-block:: python

    result = await ecomax.set("ecomax_control", "on")

If you want to use **turn_on()** method, you must first get a parameter
object.

.. code-block:: python

    ecomax_control = await ecomax.get("ecomax_control")
    result = await ecomax_control.turn_on()

ecoMAX control
^^^^^^^^^^^^^^

With the **ecomax_control** parameter there's also handy shortcut that
allows turning ecoMAX controller on or off by using the controller
object itself.

.. autofunction:: pyplumio.devices.ecomax.EcoMAX.turn_on
.. autofunction:: pyplumio.devices.ecomax.EcoMAX.turn_on_nowait
.. autofunction:: pyplumio.devices.ecomax.EcoMAX.turn_off
.. autofunction:: pyplumio.devices.ecomax.EcoMAX.turn_off_nowait

Examples
^^^^^^^^
.. code-block:: python

    import asyncio

    import pyplumio

    async def main():
        """Opens the connection, enables the controller and
        tries to set target temperature.
        """
        async with pyplumio.open_tcp_connection("localhost", 8899) as conn:
            # Get the ecoMAX device.
            ecomax = await conn.get("ecomax")

            # Turn on controller without waiting for the result.
            ecomax.turn_on_nowait()

            # Set heating temperature to 65 degrees.
            result = await ecomax.set("heating_target_temp", 65)
            if result:
                print("Heating temperature is set to 65.")
            else:
                print("Couldn't set heating temperature.")
            
        

    asyncio.run(main())

Callbacks
---------

PyPlumIO has an extensive event driven system where each device
property is an event that you can subscribe to.

When you subscribe callback to the event, your callback will be
awaited with the property value each time the property is received
from the device by PyPlumIO.

.. note::

    Callbacks must be coroutines defined with **async def**.

.. autofunction:: pyplumio.devices.Device.subscribe
.. autofunction:: pyplumio.devices.Device.subscribe_once

In example below, callback ``my_callback`` with be called with
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
            ecomax = await conn.get("ecomax")
            ecomax.subscribe("heating_temp", my_callback)

            # Wait until disconnected (forever)
            await conn.wait_until_done()


    asyncio.run(main())


In order to remove the previously registered callback,
use ``unsubscribe(name: str | int, callback)`` method.

.. code-block:: python

    ecomax.unsubscribe("heating_temp", my_callback)

To have you callback only awaited once and then be automatically unsubscribed, use
``subscribe_once(name: str | int, callback)`` method.

.. code-block:: python

    ecomax.subscribe_once("heating_temp", my_callback)

Filters
-------

PyPlumIO's callback system can be further improved upon by
using built-in filters. Filters allow you to specify when you want your
callback to be awaited. Filters can also be chained.

.. code-block:: python

    from pyplumio.filter import throttle, on_change

    # Await the callback on value change but no faster than
    # once per 5 seconds.
    ecomax.subscribe("heating_temp", throttle(on_change(my_callback), seconds=5))


To use filter simply wrap your callback in filter like in example below.

.. code-block:: python

    from pyplumio.filters import on_change

    ecomax.subscribe("heating_temp", on_change(my_callback))

There's total of five built-in filters described below.

Aggregate
^^^^^^^^^

.. autofunction:: pyplumio.filters.aggregate

This filter aggregates value for specified amount of seconds and 
then calls the callback with the sum of values collected.

.. note::

    Aggregate filter can only be used with numeric values.

.. code-block:: python

    from pyplumio.filters import aggregate

    # Await the callback with the fuel burned during 30 seconds.
    ecomax.subscribe("fuel_burned", aggregate(my_callback, seconds=30))

On change
^^^^^^^^^

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

Debounce
^^^^^^^^

.. autofunction:: pyplumio.filters.debounce

This filter will only await the callback once value is settled across
multiple calls, specified in ``min_calls`` argument.

.. code-block:: python

    from pyplumio.filter import debounce

    # Await the callback once outside_temp stays the same for three
    # consecutive times it's received by PyPlumIO.
    ecomax.subscribe("outside_temp", debounce(my_callback, min_calls=3))

Throttle
^^^^^^^^

.. autofunction:: pyplumio.filters.throttle

This filter limits how often your callback will be awaited.

.. code-block:: python

    from pyplumio.filter import throttle

    # Await the callback once per 5 seconds, regardless of 
    # how often outside_temp value is being processed by PyPlumIO.
    ecomax.subscribe("outside_temp", throttle(my_callback, seconds=5))

Delta
^^^^^

.. autofunction:: pyplumio.filters.delta

Instead of raw value, this filter awaits callback with value change.

It can be used with numeric values, dictionaries, tuples or lists.

.. code-block:: python

    from pyplumio.filter import delta

    # Await the callback with difference between values in current
    # and last await.
    ecomax.subscribe("outside_temp", delta(my_callback))

Custom
^^^^^^

.. autofunction:: pyplumio.filters.custom

This filter allows to specify filter function that will be called
every time the value is received from the controller.

A callback is awaited once this filter function returns true.

.. code-block:: python

    from pyplumio.filter import delta

    # Await the callback when temperature is higher that 10 degrees
    # Celsius.
    ecomax.subscribe("outside_temp", custom(my_callback, lambda x: x > 10))

Regulator Data
--------------
Regulator Data or, as manufacturer calls it, RegData, messages are
broadcasted by the ecoMAX controller once per second and allow access to
some device-specific information that isn't available elsewhere.
It's represented by a dictionary mapped with numerical keys.

RegData can be accessed via the **regdata** property.

.. code-block:: python

    from pyplumio.structures.regulator_data import RegulatorData

    ecomax = await conn.get("ecomax")
    regdata: RegulatorData = await ecomax.get("regdata")

The **RegulatorData** object supports following getter methods, that
you can use to access the values.

.. autofunction:: pyplumio.structures.regulator_data.RegulatorData.get
.. autofunction:: pyplumio.structures.regulator_data.RegulatorData.get_nowait
.. autofunction:: pyplumio.structures.regulator_data.RegulatorData.wait_for  

.. note::

    RegData is device-specific. Each ecoMAX controller has different
    keys and their associated meanings.

.. code-block:: python

    # Get regulator data with the 1280 key.
    heating_target = regdata.get_nowait(1280)

To see every value stored in the RegulatorData object, you can check
it's **data** property.

Mixers/Thermostats
------------------

If your ecoMAX controller have connected sub-devices such as mixers
and thermostats, you can access them through their
respective properties.

.. code-block:: python

    ecomax = await conn.get("ecomax")
    thermostats = await ecomax.get("thermostats")
    mixers = await ecomax.get("mixers")

Result of this call will be a dictionary of ``Mixer`` or ``Thermostat``
object keyed by the device indexes.

Both classes inherit the ``Device`` class and provide access to
getter/setter functions, callback support and access to the ``data``
property.

Both mixers and thermostats also can have editable parameters.

Working with mixers
^^^^^^^^^^^^^^^^^^^
In the following example, we'll get single mixer by it's index,
get it's current_temp property and set it's target temperature to
50 degrees Celsius.

.. code-block:: python

    from pyplumio.devices import Mixer

    ecomax = await conn.get("ecomax")
    mixers = await ecomax.get("mixers")
    mixer: Mixer = mixers[1]
    mixer_current_temp = await mixer.get("current_temp")
    await mixer.set("mixer_target_temp", 50)

Working with thermostats
^^^^^^^^^^^^^^^^^^^^^^^^
In the following example, we'll get single thermostat by it's index,
get current room temperature and set daytime target temperature to 20
degrees Celsius.

.. code-block:: python

    from pyplumio.device import Thermostat

    ecomax = await conn.get("ecomax")
    thermostats = await ecomax.get("thermostats")
    thermostat: Thermostat = thermostats[1]
    thermostat_current_temp = await thermostat.get("current_temp")
    await thermostat.set("day_target_temp", 20)

Schedules
---------
You can set different device schedules, enable/disable them and
change their associated parameter.

Turning schedule on or off
^^^^^^^^^^^^^^^^^^^^^^^^^^
To disable the schedule, set "schedule_{schedule_name}_switch" parameter
parameter to "off", to enable it set the parameter to "on".

The following example illustrates how you can turn heating schedule
on or off.

.. code-block:: python

    await ecomax.set("schedule_heating_switch", "on")
    await ecomax.set("schedule_heating_switch", "off")

Changing schedule parameter
^^^^^^^^^^^^^^^^^^^^^^^^^^^
To change associated parameter value, change
"schedule_{schedule_name}_parameter" property.

Use following example to lower nighttime heating
temperature by 10 degrees.

.. code-block:: python

    await ecomax.set("schedule_heating_parameter", 10)

Setting the schedule
^^^^^^^^^^^^^^^^^^^^
To set the schedule, you can use ``set_state(state)``, ``set_on()`` or
``set_off()`` methods and call ``commit()`` to send changes to the
device.

This example sets nighttime mode for Monday from 00:00 to 07:00 and
switches back to daytime mode from 07:00 to 00:00.

.. code-block:: python

    schedules = await ecomax.get("schedules")
    heating_schedule = schedules["heating"]
    heating_schedule.monday.set_off(start="00:00", end="07:00")
    heating_schedule.monday.set_on(start="07:00", end="00:00")
    heating_schedule.commit()

For clarity sake, you might want to use ``STATE_NIGHT`` and
``STATE_DAY`` constants from ``pyplumio.helpers.schedule`` module.

.. code-block:: python

    from pyplumio.helpers.schedule import STATE_NIGHT

    heating_schedule.monday.set_state(STATE_NIGHT, "00:00", "07:00")

You may also omit one of the boundaries.
The other boundary is then set to the end or start of the day.

.. code-block:: python

    heating_schedule.monday.set_on(start="07:00")
    # is equivalent to
    heating_schedule.monday.set_on(start="07:00", end="00:00")

.. code-block:: python

    heating_schedule.monday.set_off(end="07:00")
    # is equivalent to
    heating_schedule.monday.set_off(start="00:00", end="07:00")

This can be used to set state for a whole day with
``heating_schedule.monday.set_on()``.

To set schedule for all days you can iterate through the
Schedule object:

.. code-block:: python

    schedules = await ecomax.get("schedules")
    heating_schedule = schedules["heating"]

    for weekday in heating_schedule:
        # Set a nighttime mode from 00:00 to 07:00
        weekday.set_on("00:00", "07:00")
        # Set a daytime mode from 07:00 to 00:00
        weekday.set_off("07:00", "00:00")

    # Commit changes to the device.
    heating_schedule.commit()

Examples
^^^^^^^^

.. code-block:: python

    import pyplumio
    from pyplumio.helpers.schedule import STATE_DAY, STATE_NIGHT


    async def main():
        """Set a device schedule."""
        async with pyplumio.open_tcp_connection("localhost", 8899) as connection:
            ecomax = await connection.get("ecomax")
            schedules = await ecomax.get("schedules")
            heating_schedule = schedules["heating"]

            # Turn the heating schedule on.
            await ecomax.set("schedule_heating_switch", "on")

            # Drop the heating temperature by 10 degrees in the nighttime mode.
            await ecomax.set("schedule_heating_parameter", 10)

            for weekday in heating_schedule:
                weekday.set_state(STATE_DAY, "00:00", "00:30")
                weekday.set_state(STATE_NIGHT, "00:30", "09:00")
                weekday.set_state(STATE_DAY, "09:00", "00:00")

            # There will be no nighttime mode on sunday.
            heating_schedule.sunday.set_state(STATE_DAY)
            
            heating_schedule.commit()


    asyncio.run(main())

Network information
-------------------
You can send ethernet and wireless network information to
the ecoMAX controller to show on it's LCD.

It serves information purposes only and can be omitted.

.. code-block:: python

    import pyplumio
    from pyplumio.const import EncryptionType

    async def main():
        """Initialize a connection with network parameters."""
        ethernet = pyplumio.ethernet_parameters(
            ip="10.10.1.100",
            netmask="255.255.255.0",
            gateway="10.10.1.1",
        )
        wireless = pyplumio.wireless_parameters(
            ip="10.10.2.100",
            netmask="255.255.255.0",
            gateway="10.10.2.1",
            ssid="My SSID",
            encryption=EncryptionType.WPA2,
            signal_quality=100,
        )
        async with pyplumio.open_tcp_connection(
            host="localhost",
            port=8899,
            ethernet_parameters=ethernet,
            wireless_parameters=wireless,
        ) as connection:
            ...
