Mixers/Thermostats
==================

About Mixers/Thermostats
------------------------

If your ecoMAX controller have connected devices such as mixers
and thermostats, you can access them through their
respective properties.

.. code-block:: python

    ecomax = await conn.get("ecomax")
    thermostats = await ecomax.get("thermostats")
    mixers = await ecomax.get("mixers")

Result of this call will be a dictionary of ``Mixer`` or ``Thermostat``
object keyed by the device indexes.

Both classes inherit the ``Device`` class and provide access to
getter/setter functions, callback support and access to the
``Device.data`` property.

Both mixers and thermostats can also have editable parameters.

Mixer Examples
--------------

In the following example, we'll get single mixer by it's index,
get it's current_temp property and set it's target temperature to
50 degrees Celsius.

.. code-block:: python

    from pyplumio.devices import Mixer

    # Get the ecoMAX device.
    ecomax = await conn.get("ecomax")

    # Get connected mixers.
    mixers = await ecomax.get("mixers")

    # Get single mixer.
    mixer: Mixer = mixers[1]

    # Get current mixer temperature.
    mixer_current_temp = await mixer.get("current_temp")

    # Set mixer target temperature to 50 degrees Celsius.
    await mixer.set("mixer_target_temp", 50)

Thermosat Examples
------------------

In the following example, we'll get single thermostat by it's index,
get current room temperature and set daytime target temperature to 20
degrees Celsius.

.. code-block:: python

    from pyplumio.device import Thermostat

    # Get the ecoMAX device.
    ecomax = await conn.get("ecomax")

    # Get connected thermostats.
    thermostats = await ecomax.get("thermostats")

    # Get single thermostat.
    thermostat: Thermostat = thermostats[1]

    # Get current room temperature.
    thermostat_current_temp = await thermostat.get("current_temp")

    # Set day target temperature to 20 degrees Celsius.
    await thermostat.set("day_target_temp", 20)
