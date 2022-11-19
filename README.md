# PyPlumIO is a native ecoNET library for Plum ecoMAX controllers.
[![PyPI version](https://badge.fury.io/py/PyPlumIO.svg)](https://badge.fury.io/py/PyPlumIO)
[![PyPI Supported Python Versions](https://img.shields.io/pypi/pyversions/pyplumio.svg)](https://pypi.python.org/pypi/pyplumio/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PyPlumIO CI](https://github.com/denpamusic/PyPlumIO/actions/workflows/ci.yml/badge.svg)](https://github.com/denpamusic/PyPlumIO/actions/workflows/ci.yml)
[![Maintainability](https://api.codeclimate.com/v1/badges/9f275fbc50fe9082a909/maintainability)](https://codeclimate.com/github/denpamusic/PyPlumIO/maintainability)
[![Test Coverage](https://api.codeclimate.com/v1/badges/9f275fbc50fe9082a909/test_coverage)](https://codeclimate.com/github/denpamusic/PyPlumIO/test_coverage)
[![stability-beta](https://img.shields.io/badge/stability-beta-33bbff.svg)](https://github.com/mkenney/software-guides/blob/master/STABILITY-BADGES.md#beta)

## Overview
This package aims to provide complete and easy to use solution for communicating with climate devices by [Plum Sp. z o.o.](https://www.plum.pl/)

![ecoMAX controllers](https://raw.githubusercontent.com/denpamusic/PyPlumIO/main/images/ecomax.png)

Currently it supports reading and writing parameters of ecoMAX automatic pellet boiler controllers, getting service password and sending network information to show on controller's display.

Devices can be connected directly via RS-485 to USB adapter or through network by using RS-485 to Ethernet/WiFi converter.

![RS-485 converters](https://raw.githubusercontent.com/denpamusic/PyPlumIO/main/images/rs485.png)

## Table of contents
- [Usage](#usage)
  - [TCP](#tcp)
  - [Serial](#serial)
  - [Values and Parameters](#values-and-parameters)
  - [Reading](#reading)
  - [Writing](#writing)
  - [Callbacks](#callbacks)
  - [Filters](#filters)
  - [Working with Mixers](#working-with-mixers)
  - [Working with Schedules](#working-with-schedules)
  - [Network Information](#network-information)
- [Protocol](#protocol)
  - [Frame Structure](#frame-structure)
  - [Requests and Responses](#requests-and-responses)
  - [Communication](#communication)
  - [Frame Versioning](#frame-versioning)
- [Home Assistant Integration](#home-assistant-integration)
- [Attribution](#attribution)
- [License](#license)

## Usage
To interact with devices, you must first initialize connection by utilizing `pyplumio.open_tcp_connection()` or `pyplumio.open_serial_connection()` methods.

You can find examples for each supported connection type below.

### TCP
This is intended to be used with RS-485 to Ethernet/WiFi converters, which are readily
available online or can be custom built using RS-485 to USB converter and ser2net software.

```python
import asyncio
import pyplumio

async def main():
  async with pyplumio.open_tcp_connection("localhost", 8899) as connection:
    ecomax = await connection.get_device("ecomax")
    # Do something.
	
asyncio.run(main())
```

### Serial
This is intended to be used with RS-485 to USB adapters, that are connected directly to the device running PyPlumIO.

```python
import asyncio
import pyplumio
import logging

_LOGGER = logging.getLogger(__name__)

async def main():
  async with pyplumio.open_serial_connection("/dev/ttyUSB0", baudrate=115200) as connection:
    # You can also use optional timeout parameter of get_device method.
    try:
      ecomax = await connection.get_device("ecomax", timeout=10)
      # Do something.
    except asyncio.TimeoutError:
      _LOGGER.error("Failed to get device within 10 seconds")
	
asyncio.run(main())
```

> NB: Although use of the `async with` statement is preferred, you can open the connection without it:

```python
import asyncio
import pyplumio

async def main():
  connection = pyplumio.open_tcp_connection("localhost", 8899)
  await connection.connect()
  ecomax = await connection.get_device("ecomax")
  # Do something.
  await connection.close()
	
asyncio.run(main())
```

### Values and Parameters
Data can be immutable (Values) or mutable (Parameters). They can be accessed via 
`AsyncDevice.get_value(name: str, timeout: float | None = None)` and `AsyncDevice.get_parameter(name: str, timeout: float | None = None)` methods.

Each device supports different attributes and parameters, you can check all available values and parameters by looking at `AsyncDevice.data` attribute.

### Reading
Interaction with the device is mainly done through async getter methods.
For example you can read current feed water temperature by awaiting for `AsyncDevice.get_value("heating_temp")`.

The following example will print out current feed water temperature and close the connection.
```python
import asyncio
import pyplumio

async def main():
  async with pyplumio.open_tcp_connection("localhost", 8899) as connection:
    ecomax = await connection.get_device("ecomax")
    print(await ecomax.get_value("heating_temp"))
    
asyncio.run(main())
```

### Writing
You can change controller parameters by awaiting `AsyncDevice.set_value(name: str, value: int, timeout: float | None = None)` or
by getting parameter via `AsyncDevice.get_parameter(name: str, timeout: float | None = None)` method and calling `set(name, value)`.
In examples below, we'll set target temperature to 65 degrees Celsius (~ 150 degrees Fahrenheit) using both methods.
```python
import pyplumio

async def main():
  async with pyplumio.open_tcp_connection("localhost", 8899) as connection:
    ecomax = await connection.get_device("ecomax")
    result = await ecomax.set_value("heating_target_temp", 65)
```

```python
import pyplumio

async def main():
  async with pyplumio.open_tcp_connection("localhost", 8899) as connection:
    ecomax = await connection.get_device("ecomax")
    target_temp = await ecomax.get_parameter("heating_target_temp")
    result = await target_temp.set(65)
    if result:
      print("Parameter value was successfully set.")
    else:
      print("Error while trying to set parameter value.")
```

For a binary parameters, that can only have "0" or "1" value, you can also use string
literals "on", "off" or use `turn_on()`, `turn_off()` methods of the parameter instance.
```python
import pyplumio

async def main():
  async with pyplumio.open_tcp_connection("localhost", 8899) as connection:
    ecomax = await connection.get_device("ecomax")
    result = await ecomax.set_value("boiler_control", "on")
```

```python
import pyplumio

async def main():
  async with pyplumio.open_tcp_connection("localhost", 8899) as connection:
    ecomax = await connection.get_device("ecomax")
    boiler = await ecomax.get_parameter("boiler_control")
    result = await boiler.turn_on()  # or await boiler.turn_off()
```

Each parameter has a range of acceptable values. PyPlumIO will raise `ValueError` if value is not within the acceptable range.
You can check allowed range by reading `min_value` and `max_value` attributes of parameter object. Both `min_value` and `max_value` are inclusive.
```python
import pyplumio

async def main():
  async with pyplumio.open_tcp_connection("localhost", 8899) as connection:
    ecomax = await connection.get_device("ecomax")
    target_temp = await ecomax.get_parameter("heating_target_temp")
    print(target_temp.min_value)  # Prints minimum allowed target temperature.
    print(target_temp.max_value)  # Prints maximum allowed target temperature.
```

### Callbacks
It's possible to register a callback, that will be called every time a data with
the certain name is received (e. g. heating_temp), using `AsyncDevice.subscribe(name, callback)` function, register callback that will be called only once using `AsyncDevice.subscribe_once(name, callback)` function or remove existing callback by calling `AsyncDevice.unsubscribe(name, callback).`
```python
import asyncio
import pyplumio

async def my_callback(value) -> None:
  print(f"Heating Temperature: {value}")

async def main():
  async with pyplumio.open_tcp_connection("localhost", 8899) as connection:
    ecomax = await connection.get_device("ecomax")
    ecomax.subscribe("heating_temp", my_callback)
    # Wait until disconnected (forever)
    connection.wait_until_done()

asyncio.run(main())
```

### Filters
Callbacks can be improved by using built-in filters `aggregate(callback, seconds)`, `on_change(callback)`,
`debounce(callback, min_calls)` `delta(callback)`, and `throttle(callback, seconds)`.

You can find examples on how to use them below:
```python
import pyplumio
from pyplumio.helpers.filters import aggregate, debounce, delta, on_change, throttle

async def main():
  async with pyplumio.open_tcp_connection("localhost", 8899) as connection:
    ecomax = await connection.get_device("ecomax")
    
    # Callback "first_callback" will be awaited on every received frame
    # that contains "heating_temp" regardless of whether value is
    # changed or not.
    ecomax.subscribe("heating_temp", first_callback)
    
    # Callback "second_callback" will be awaited only if the
    # "heating_temp" value is changed since last call.
    ecomax.subscribe("heating_temp", on_change(second_callback))
    
    # Callback "third_callback" will be awaited once the "heating_temp"
    # value is stabilized across three received frames.
    ecomax.subscribe("heating_temp", debounce(third_callback, min_calls=3))

    # Callback "fourth_callback" will be awaited once in 5 seconds.
    ecomax.subscribe("heating_temp", throttle(fourth_callback, seconds=5))

    # Callback "fifth_callback" will be awaited with the sum of values
    # accumulated over the span of 5 seconds. Works with numeric values only.
    ecomax.subscribe("fuel_burned", aggregate(fifth_callback, seconds=5))

    # Callback "sixth_callback" will be awaited with difference between
    # values in the last and current calls.
    ecomax.subscribe("heating_temp", delta(sixth_callback))

    # Throttle callback can be chained with others.
    # Callback "seventh_callback" will be awaited on value change but no
    # sooner that 5 seconds.
    ecomax.subscribe("heating_temp", throttle(on_change(seventh_callback), seconds=5))

```

### Working with Mixers
If your ecoMAX controller support mixers, you can access them via `mixers` property
through `AsyncDevice.get_value("mixers")` call.

Result of this call will be a list of `Mixer` instances.
`Mixer` class inherits `AsyncDevice` and provides access to getter/setter functions and
callback support.

Each device supports different attributes and parameters for mixers, you can check all
available values and parameters by looking at `Mixer.data` attribute.

```python
import asyncio
import pyplumio

from pyplumio.helpers.filters import on_change

async def my_callback(mixer_pump_status: bool) -> None:
  print(f"Mixer Pump Working: {mixer_pump_status}")

async def main():
  async with pyplumio.open_tcp_connection("localhost", 8899) as connection:
    ecomax = await connection.get_device("ecomax")
    mixers = await ecomax.get_value("mixers", timeout=10)
    # If this fails with timeout, check that you have temperature probe
    # connected for at least one mixer.

    # Get single mixer from the list.
    mixer = mixers[0]
    mixer_temp = await mixer.get_value("temp")
    await mixer.set_value("mix_target_temp", 50)
    mixer.subscribe("mixer_pump", on_change(my_callback))

    # Print all available mixer data.
    print(mixer.data)

    # Wait until disconnected (forever)
    connection.wait_until_done()

asyncio.run(main())
```

### Working with Schedules
You can set device schedule, enable/disable it and change associated parameter.

To disable the schedule, turn off "schedule_{schedule_name}_switch" parameter, by using
`AsyncDevice.set_value` method, to enable it turn in on.

```python
  await ecomax.set_value("schedule_heating_switch", "off")
  await ecomax.set_value("schedule_heating_switch", "on")
```

To change associated parameter value, use `AsyncDevice.set_value`
function with "schedule_{schedule_name}_parameter".

```python
  await ecomax.set_value("schedule_heating_parameter", 10)
```

To set the schedule, you can use `set_state`, `set_on` or `set_off` functions and call
`commit` to send changes to device.

This example sets nighttime mode for Monday from 00:00 to 07:00 and switches back to daytime
mode from 07:00 to 00:00.

```python
heating_schedule = (await ecomax.get_value("schedules"))["heating"]
heating_schedule.monday.set_off(start="00:00", end="07:00")
heating_schedule.monday.set_on(start="07:00", end="00:00")
heating_schedule.commit()
```

For clarity sake, you might want to use `STATE_NIGHT` and `STATE_DAY`
constants from `pyplumio.helpers.schedule` with set state.
```python
heating_schedule.monday.set_state(STATE_NIGHT, "00:00", "07:00")
```

You may also omit one of the boundaries.
The other boundary is then set to the end or start of the day.
`heating_schedule.monday.set_on(start="07:00")` is equivalent to
`heating_schedule.monday.set_on(start="07:00", end="00:00")` and `heating_schedule.monday.set_off(end="07:00")` is
equivalent to `heating_schedule.monday.set_off(start="00:00", end="07:00")`.

This can be used to set state for a whole day: `heating_schedule.monday.set_on()`

To set schedule for all days you can iterate through Schedule object:
```python
heating_schedule = (await ecomax.get_value("schedules"))["heating"]

for weekday in heating_schedule:
  weekday.set_on("00:00", "07:00")
  weekday.set_off("07:00", "00:00")

heating_schedule.commit()
```

Following example showcases most of the methods described above:
```python
import pyplumio

from pyplumio.helpers.schedule import STATE_DAY, STATE_NIGHT

async def main():
  async with pyplumio.open_tcp_connection("localhost", 8899) as connection:
    ecomax = await connection.get_device("ecomax")
    heating_schedule = (await ecomax.get_value("schedules"))["heating"]

    # Turn heating schedule on.
    await ecomax.set_value("schedule_heating_switch", "on")

    # Drop heating temperature by 10 degrees during nighttime.
    await ecomax.set_value("schedule_heating_parameter", 10)

    for weekday in heating_schedule:
      weekday.set_state(STATE_DAY, "00:00", "00:30")
      weekday.set_state(STATE_NIGHT, "00:30", "09:00")
      weekday.set_state(STATE_DAY, "09:00", "00:00")

    # There will be no nighttime on sunday.
    heating_schedule.sunday.set_state(STATE_DAY)
    
    heating_schedule.commit()

asyncio.run(main())
```

### Network Information
You can send ethernet and wireless network information to the ecoMAX controller to show on it's
LCD. It serves information purposes only and can be omitted.
```python
import pyplumio

async def main():
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
    encryption=pyplumio.WLAN_ENCRYPTION_WPA2,
    signal_quality=100,
  )
  async with pyplumio.open_tcp_connection(
    host="localhost",
    port=8899,
    ethernet_parameters=ethernet,
    wireless_parameters=wireless,
  ) as connection:
    # Do something.
```

## Protocol
Plum devices use RS-485 standard for communication. Each frame consists of header (7 bytes),
message type (1 byte), message data (optional), CRC (1 byte) and frame end delimiter (1 byte).
The minimum frame size therefore is 10 bytes.

Protocol supports unicast and broadcast frames. Broadcast frames will always have their
recipient address set to `0x00`, while unicast messages will have specific device address.
ecoMAX controller address is `0x45`, ecoSTER panel address is `0x51`.

### Frame Structure
- Header:
  - [Byte] Frame start delimiter. Always `0x68`.
  - [Unsigned Short] Byte size of the frame. Includes CRC and frame end delimiter. 
  - [Byte] Recipient address.
  - [Byte] Sender address.
  - [Byte] Sender type. PyPlumIO uses EcoNET type `48`.
  - [Byte] ecoNET version. PyPlumIO uses version `5`.
- Body:
  - [Byte] Frame type.
  - [Byte*] Message data (optional).
  - [Byte] Frame CRC.
  - [Byte] Frame end delimiter. Always `0x16`.

### Requests and Responses
PyPlumIO splits frames into requests, responses and messages.
See [requests.py](https://github.com/denpamusic/PyPlumIO/blob/main/pyplumio/frames/requests.py),
[responses.py](https://github.com/denpamusic/PyPlumIO/blob/main/pyplumio/frames/responses.py) and
[messages.py](https://github.com/denpamusic/PyPlumIO/blob/main/pyplumio/frames/messages.py)
for a list of supported frame types.

For example, we can request list of editable parameters from the ecoMAX controller by sending
frame with frame type `49` and receive response with frame type `177` that contains requested parameters.

### Communication
The controller constantly sends `ProgramVersionRequest[type=64]` and `CheckDeviceRequest[type=48]`
requests to every known device on the network and broadcasts `RegulatorDataMessage[type=8]` message, that contains basic controller data.

Initial exchange between ecoMAX controller and PyPlumIO library can be illustrated with following diagram:

> NB: device network address is listed in square brackets.

```
ecoMAX[0x45] -> Broadcast[0x00]: RegulatorDataMessage[type=8] Contains basic ecoMAX data.
ecoMAX[0x45] -> PyPlumIO[0x56]:  ProgramVersionRequest[type=64] Program version request.
ecoMAX[0x45] <- PyPlumIO[0x56]:  ProgramVersionResponse[type=192] Contains program version.
ecoMAX[0x45] -> PyPlumIO[0x56]:  CheckDeviceRequest[type=48] Check device request.
ecoMAX[0x45] <- PyPlumIO[0x56]:  DeviceAvailableResponse[type=176] Contains network information.
ecoMAX[0x45] -> PyPlumIO[0x56]:  SensorDataMessage[type=53] Contains ecoMAX sensor data.
```

### Versioning
Protocol has built-in way to track frame versions. This is used to synchronize changes between devices.
Both broadcast `RegulatorDataMessage[type=8]` and unicast `SensorDataMessage[type=53]` frames sent by ecoMAX controller contain versioning data.

This data can be represented with following dictionary:
```python
frame_versions: Dict[int, int] = {
  49: 37,
  50: 37,
  54: 1,
  56: 5,
  57: 1,
  61: 40767,
  80: 1,
  81: 1,
  82: 1,
  83: 1,
}
```
In this dictionary, keys are frame types and values are version numbers. In example above,
frame `ParametersRequest[type=49]` has version 37. If we change any parameters either remotely or
on the controller itself, version number will increase, so PyPlumIO will be able to tell that it's
need to request list of parameters again to obtain changes.
```python
frame_versions: Dict[int, int] = {
  49: 38,  # Note the version number change.
  50: 37,
  54: 1,
  56: 5,
  57: 1,
  61: 40767,
  80: 1,
  81: 1,
  82: 1,
  83: 1,
}
```

## Home Assistant Integration
There is companion Home Assistant integration that is being co-developed with this package and depends on it. Click button below to check it out.

[![hass integration](https://img.shields.io/badge/hass%20integration-v0.2.22-41bdf5)](https://github.com/denpamusic/homeassistant-plum-ecomax)

## Attribution
Special thanks to [econetanalyze](https://github.com/twkrol/econetanalyze) project by twkrol for initial information about protocol.

## License
This product is distributed under MIT license.
