Writing
=======

Setters
-------

.. autofunction:: pyplumio.devices.Device.set

When using blocking setter, you'll get the result represented by a
boolean value. `True` if write was successful, `False` otherwise.

.. code-block:: python

    result = await ecomax.set("heating_target_temp", 65)
    if result:
        print("Heating target temperature was successfully set.")
    else:
        print("Error while trying to set heating target temperature.")

.. autofunction:: pyplumio.devices.Device.set_nowait

When using non-blocking setter, you can't access the result as task is
done in background. However, you'll still get error log message in case
of a failure.

.. code-block:: python

    ecomax.set_nowait("heating_target_temp", 65)

Parameters
----------

For the parameters, it's possible to retrieve the ``Parameter`` object
and then modify it via it's own setter method.

.. autoclass:: pyplumio.parameters.Parameter

When using the parameter object directly, you don't need to pass the
parameter name to the setter method.

Numbers
^^^^^^^

Numbers are parameters that have numerical value associated with them.

.. code-block:: python

    from pyplumio.parameters import Number

    async with conn.device("ecomax") as ecomax:
        heating_target: Number = ecomax.get("heating_target_temp")
        result = heating_target.set(65)

Each number has an unique range of allowed values.
PyPlumIO will raise ``ValueError`` if value isn't within acceptable
range.

You can check allowed range boundaries by reading ``min_value`` and
``max_value`` properties of the parameter object.
Please note, that both values are **inclusive**.

.. code-block:: python

    from pyplumio.parameters import Number

    async with conn.device("ecomax") as ecomax:
        target_temp: Number = await ecomax.get("heating_target_temp")
        print(target_temp.min_value)  # Minimum allowed target temperature.
        print(target_temp.max_value)  # Maximum allowed target temperature.

Switches
^^^^^^^^

Switches are parameters that could only have two possible states: on or off.

Thus, for switches, you can use Python's boolean keywords `True` or `False`,
string literals "on" or "off" or special ``turn_on()`` and
``turn_off()`` methods.

.. autofunction:: pyplumio.parameters.Switch.turn_on
.. autofunction:: pyplumio.parameters.Switch.turn_on_nowait
.. autofunction:: pyplumio.parameters.Switch.turn_off
.. autofunction:: pyplumio.parameters.Switch.turn_off_nowait

Good example of a switch is "ecomax_control" that allows you to switch
the ecoMAX controller on or off.

.. code-block:: python

    # Set an ecomax_control parameter value to "on".
    result = await ecomax.set("ecomax_control", "on")

If you want to use **turn_on()** method, you must first get the parameter
object.

.. code-block:: python

    from pyplumio.parameters import Switch

    # Get an ecomax_control parameter and turn it on.
    ecomax_control: Switch = await ecomax.get("ecomax_control")
    result = await ecomax_control.turn_on()

If you simply want to switch the ecoMAX controller on or off,
there's a handy built-in way to do that.

.. code-block:: python
    
    # Turn on the controller.
    await ecomax.turn_on()

    # Turn off the controller.
    await ecomax.turn_off()

Writing Examples
----------------

The following example opens a connection, enables the controller
without waiting for the result and tries to set a target temperature,
outputting the result to the terminal.

.. code-block:: python

    import asyncio

    import pyplumio

    async def main():
        """Turn on the controller and set target temperature."""
        async with pyplumio.open_tcp_connection("localhost", 8899) as conn:
            # Get the ecoMAX device.
            async with conn.device("ecomax") as ecomax:
                # Turn on controller without waiting for the result.
                ecomax.turn_on_nowait()

                # Set heating temperature to 65 degrees.
                result = await ecomax.set("heating_target_temp", 65)
                if result:
                    print("Heating temperature is set to 65.")
                else:
                    print("Couldn't set heating temperature.")
            

    asyncio.run(main())
