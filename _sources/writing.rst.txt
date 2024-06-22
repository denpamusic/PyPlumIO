Writing
=======

Setters
-------

.. autofunction:: pyplumio.devices.Device.set

When using blocking setter, you will get the result
represented by the boolean value. `True` if write was successful,
`False` otherwise.

.. code-block:: python

    result = await ecomax.set("heating_target_temp", 65)
    if result:
        print("Heating target temperature was successfully set.")
    else:
        print("Error while trying to set heating target temperature.")

.. autofunction:: pyplumio.devices.Device.set_nowait

You can't access result, when using non-blocking setter as task is done
in the background. You will, however, still get error message in the log
in case of failure.

.. code-block:: python

    ecomax.set_nowait("heating_target_temp", 65)

Parameters
----------

It's possible to get the ``Parameter`` object and then modify it using
it's own setter methods. When using the parameter object, you don't
need to pass the parameter name.

.. code-block:: python

    from pyplumio.helpers.parameter import Parameter


    ecomax = await conn.get("ecomax")
    heating_target: Parameter = ecomax.get("heating_target_temp")
    result = heating_target.set(65)

Each parameter has a range of allowed values.
PyPlumIO will raise ``ValueError`` if value is not within the
acceptable range.

You can check allowed range by reading ``min_value`` and ``max_value``
properties of the parameter object. Both values are **inclusive**.

.. code-block:: python

    ecomax = await connection.get("ecomax")
    target_temp = await ecomax.get("heating_target_temp")
    print(target_temp.min_value)  # Minimum allowed target temperature.
    print(target_temp.max_value)  # Maximum allowed target temperature.

Binary Parameters
-----------------

For binary parameters, you can also use boolean `True` or `False`,
string literals "on" or "off" or special ``turn_on()`` and
``turn_off()`` methods.

.. autofunction:: pyplumio.helpers.parameter.BinaryParameter.turn_on
.. autofunction:: pyplumio.helpers.parameter.BinaryParameter.turn_on_nowait
.. autofunction:: pyplumio.helpers.parameter.BinaryParameter.turn_off
.. autofunction:: pyplumio.helpers.parameter.BinaryParameter.turn_off_nowait

One such parameter is "ecomax_control" that allows you to switch
the ecoMAX on or off.

.. code-block:: python

    # Set an ecomax_control parameter value to "on".
    result = await ecomax.set("ecomax_control", "on")

If you want to use **turn_on()** method, you must first get a parameter
object.

.. code-block:: python

    # Get an ecomax_control parameter and turn it on.
    ecomax_control = await ecomax.get("ecomax_control")
    result = await ecomax_control.turn_on()

If you simply want to turn on or off the ecoMAX controller there's,
handy shortcut built-in the controller object itself.

.. code-block:: python
    
    # Turn on the controller.
    await ecomax.turn_on()

    # Turn off the controller.
    await ecomax.turn_off()

Writing Examples
----------------

The following example opens the connection, enables the controller
without waiting for result and tries to set a target temperature,
outputting result to the terminal.

.. code-block:: python

    import asyncio

    import pyplumio

    async def main():
        """Turn on the controller and set target temperature."""
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
