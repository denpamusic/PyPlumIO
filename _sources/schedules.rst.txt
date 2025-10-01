
Schedules
=========

About Schedules
---------------

You can set different device schedules, enable or disable them and
change their associated parameters.

Enabling/Disabling Schedule
---------------------------

To disable the schedule, set **schedule_{schedule_name}_switch** parameter
parameter to `off`, to enable it set the parameter to `on`.

The following example illustrates how you can turn heating schedule
on or off.

.. code-block:: python

    # Turn on the heating schedule.
    await ecomax.set("schedule_heating_switch", "on")

    # Turn off the heating schedule.
    await ecomax.set("schedule_heating_switch", "off")

Changing Schedule Parameter
---------------------------

To change associated parameter value, change
**schedule_{schedule_name}_parameter** property.

Use following example to lower night time heating
temperature by 10 degrees Celsius.

.. code-block:: python

    # Lower heating temperature by 10 C at night time.
    await ecomax.set("schedule_heating_parameter", 10)

Setting Schedule
----------------

To set the schedule, you can either directly set the state via key or
by using ``set_state(state)``, ``set_on()`` or ``set_off()``.

After updating the state you must call ``commit()`` method to save
changes on the device.

This example sets nighttime mode for Monday from 00:00 to 07:00 and
switches back to daytime mode from 07:00 to 00:00.

.. code-block:: python

    schedules = await ecomax.get("schedules")
    heating_schedule = schedules["heating"]
    heating_schedule.monday.set_off(start="00:00", end="07:00")
    heating_schedule.monday.set_on(start="07:00", end="00:00")
    await heating_schedule.commit()

For clarity sake, you might want to use ``STATE_OFF`` and
``STATE_ON`` constants from ``pyplumio.const`` module.

.. code-block:: python

    from pyplumio.const import STATE_OFF

    heating_schedule.monday["18:00"] = STATE_OFF
    heating_schedule.monday.set_state(STATE_OFF, "00:00", "07:00")

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
    await heating_schedule.commit()

Schedule Examples
-----------------

.. code-block:: python

    import pyplumio
    from pyplumio.const import STATE_ON, STATE_OFF


    async def main():
        """Set a device schedule."""
        async with pyplumio.open_tcp_connection("localhost", 8899) as conn:
            async with conn.device("ecomax") as ecomax:
                schedules = await ecomax.get("schedules")
                heating_schedule = schedules["heating"]

                # Turn the heating schedule on.
                await ecomax.set("schedule_heating_switch", "on")

                # Drop the heating temperature by 10 degrees in the nighttime mode.
                await ecomax.set("schedule_heating_parameter", 10)

                for weekday in heating_schedule:
                    weekday.set_state(STATE_ON, "00:00", "00:30")
                    weekday.set_state(STATE_OFF, "00:30", "09:00")
                    weekday.set_state(STATE_ON, "09:00", "00:00")
                    weekday["19:00"] = STATE_OFF

                # There will be no nighttime mode on sunday.
                heating_schedule.sunday.set_state(STATE_ON)
                
                await heating_schedule.commit()


    asyncio.run(main())
