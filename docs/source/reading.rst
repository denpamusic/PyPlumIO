Reading
=======

Dataset
-------

.. autoattribute:: pyplumio.devices.Device.data

You can use this property get a full device dataset.

.. code-block:: python

    ecomax = await conn.get("ecomax")
    print(ecomax.data)

In a pinch, you can also use this attribute to directly access the data,
but this is not recommended, please use getters instead.

Getters
-------

.. autofunction:: pyplumio.devices.Device.get

This method can be used to get a single item from the device dataset.

The following example will print out current feed water temperature
and close the connection.

.. code-block:: python

    import asyncio

    import pyplumio

    async def main():
        """Read the current heating temperature."""
        async with pyplumio.open_tcp_connection("localhost", 8899) as conn:
            # Get the ecoMAX device.
            ecomax = await conn.get("ecomax")

            # Get the heating temperature.
            heating_temp = await ecomax.get("heating_temp")
            print(heating_temp)
            ...
            

    asyncio.run(main())

.. autofunction:: pyplumio.devices.Device.get_nowait

This method can be used to get single item from device dataset without
waiting until it becomes available.

The following example will print out current feed water temperature if
it is available, otherwise it'll print ``60``.

.. code-block:: python

    # Print the heating temperature or 60, if property is not available.
    heating_temp = ecomax.get_nowait("heating_temp", default=60)
    print(heating_temp)

.. autofunction:: pyplumio.devices.Device.wait_for

You can use this method to wait until the value is available and
then directly access the attribute under the device object.

The following example will wait until current feed water temperature is
available and print it out.

.. code-block:: python

    # Wait until the 'heating_temp' property becomes available.
    await ecomax.wait_for("heating_temp")

    # Output the 'heating_temp' property.
    print(ecomax.heating_temp)

Regulator Data
--------------
Regulator Data messages are broadcasted by the ecoMAX controller
once per second and allow access to some device-specific
information that isn't available elsewhere.

.. note::

    RegData is device-specific. Each ecoMAX controller has different
    keys and their associated meanings.

It's represented by a dictionary mapped with numerical keys.

RegData can be accessed via the **regdata** property.

.. code-block:: python

    from pyplumio.structures.regulator_data import RegulatorData

    ecomax = await conn.get("ecomax")
    regdata: RegulatorData = await ecomax.get("regdata")

The ``RegulatorData`` object supports all aforementioned methods of
getting the data.

.. code-block:: python

    # Get regulator data with the 1280 key.
    heating_target = regdata.get_nowait(1280)

To see every value stored in the RegulatorData object, you can check
``RegulatorData.data`` property.

Reading Examples
----------------

The following example make uses of all available methods to get
heating current and target temperatures and device state and outputs it
to the terminal.

.. code-block:: python

    import asyncio

    import pyplumio


    async def main():
        """Read current temp, target temp and device state from
        the regdata.
        """
        async with pyplumio.open_tcp_connection("localhost", 8899) as conn:
            # Get the ecoMAX device.
            ecomax = await conn.get("ecomax")

            # Get the heating temperature if it is available, or return
            # default value (65).
            heating_temp = ecomax.get_nowait("heating_temp", default=65)

            # Wait for the heating temperature and get it's value.
            heating_target_temp = await ecomax.get("heating_target_temp")

            # Wait until regulator data is available, and grab key 1792.
            await ecomax.wait_for("regdata")
            status = ecomax.regdata.get(1792)

            print(
                f"Current temp: {heating_temp}, "
                f"target temp: {heating_target_temp}, "
                f"status: {status}."
            )


    asyncio.run(main())
