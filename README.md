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
  - [Data and Parameters](#data-and-parameters)
  - [Reading](#reading)
  - [Writing](#writing)
  - [Callbacks](#callbacks)
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
This is intended to be used with RS-485 to Ethernet/WiFi converters, which are readily available online or can be custom built using RS-485 to USB converter and ser2net software.

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

async def main():
  async with pyplumio.open_serial_connection("/dev/ttyUSB0", baudrate=115200) as connection:
    ecomax = await connection.get_device("ecomax")
    # Do something.
	
asyncio.run(main())
```

_NB: Although use of `async with` statement is preferred, you can open the connection without it:_
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

### Data and Parameters
Data can be mutable (Parameters) or immutable (Values). They can be accessed via `await ecomax.get_value(name: str)` and `await ecomax.get_parameter(name: str)` methods.

Each Plum device supports different attributes and parameters.

### Reading
Interaction with the device is mainly done through async getter methods.
For example you can read current feed water temperature by awaiting for `Device.get_value("heating_temp")`.

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
You can easily change controller parameters by awaiting `Device.set_value(name: str, value: int)` or by getting parameter via `Device.get_parameter(name: str)` method and calling `set(name, value)`. In examples below, we will set target temperature to 65 degrees Celsius (~ 150 degrees Fahrenheit) using both methods.
```python
import pyplumio

async def main():
  async with pyplumio.open_tcp_connection("localhost", 8899) as connection:
    ecomax = await connection.get_device("ecomax")
    await ecomax.set_value("heating_target_temp", 65)
```

```python
import pyplumio

async def main():
  async with pyplumio.open_tcp_connection("localhost", 8899) as connection:
    ecomax = await connection.get_device("ecomax")
    target_temp = await ecomax.get_parameter("heating_target_temp")
    target_temp.set(65)
```

For binary parameters, that can only have 0 or 1 value, you can use string literals "on", "off" as value or use `turn_on()`, `turn_off()` methods.
```python
import pyplumio

async def main():
  async with pyplumio.open_tcp_connection("localhost", 8899) as connection:
    ecomax = await connection.get_device("ecomax")
    await ecomax.set_value("boiler_control", "on")
```

```python
import pyplumio

async def main():
  async with pyplumio.open_tcp_connection("localhost", 8899) as connection:
    ecomax = await connection.get_device("ecomax")
    boiler = await ecomax.get_parameter("boiler_control")
    boiler.turn_on()  # or boiler.turn_off()
```

Please note that each parameter has a range of acceptable values that you must check by yourself. The PyPlumIO will raise `ValueError` if value is not within acceptable range. You can check allowed values by reading `min_value` and `max_value` attributes of parameter object.
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
It's possible to register a callback function that will be called every time a data is received.
```python
import asyncio
import pyplumio

async def my_callback(value) -> None:
  print(f"Heating Temperature: {value}")

async def main():
  async with pyplumio.open_tcp_connection("localhost", 8899) as connection:
    ecomax = await connection.get_device("ecomax")
    ecomax.register_callback("heating_temp", my_callback)
    # Wait until disconnected.
    connection.wait_until_done()

asyncio.run(main())
````

Callbacks can be further improved using built-in filters `aggregate(callback, seconds)`, `on_change(callback)`, `debounce(callback, min_calls)` `delta(callback)`, and `throttle(callback, seconds)`. Below are some examples on how to use them.

```python
import pyplumio
from pyplumio.helpers.filters import aggregate, debounce, delta, on_change, throttle

async def main():
  async with pyplumio.open_tcp_connection("localhost", 8899) as connection:
    ecomax = await connection.get_device("ecomax")
    
    # Callback "first_callback" will be awaited on every received frame
    # that contains "heating_temp" regardless of whether value is
    # changed or not.
    ecomax.register_callback("heating_temp", first_callback)
    
    # Callback "second_callback" will be awaited only if the
    # "heating_temp" value is changed since last call.
    ecomax.register_callback("heating_temp", on_change(second_callback))
    
    # Callback "third_callback" will be awaited once the "heating_temp"
    # value is stabilized across three received frames.
    ecomax.register_callback("heating_temp", debounce(third_callback, min_calls=3))

    # Callback "fourth_callback" will be awaited once in 5 seconds.
    ecomax.register_callback("heating_temp", throttle(fourth_callback, seconds=5))

    # Callback "fifth_callback" will be awaited with the sum of values
    # accumulated over the span of 5 seconds. Works with numeric values only.
    ecomax.register_callback("fuel_burned", aggregate(fifth_callback, seconds=5))

    # Callback "sixth_callback" will be awaited with difference between
    # values in the last and current calls.
    ecomax.register_callback("heating_temp", delta(sixth_callback))

    # Throttle callback can be chained with others.
    # Callback "seventh_callback" will be awaited on value change but no
    # sooner that 5 seconds.
    ecomax.register_callback("heating_temp", throttle(on_change(seventh_callback), seconds=5))

```

### Network Information
You can send ethernet and wireless network information to the controller to show on it's
screen. It serves information purposes only and can be omitted.
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
ecoNET communication uses RS-485 standard. Each frame consists of header (7 bytes), message type (1 byte), message data (optional), CRC (1 byte) and frame end delimiter (1 byte). The minimum frame size therefore is 10 bytes.

Protocol supports unicast and broadcast frames. Broadcast frames will always have their recipient address set to `0x00`, while unicast messages will have specific device address. ecoMAX controller address is `0x45`, ecoSTER panel address is `0x51`.

### Frame Structure
- Header:
  - [Byte] Frame start delimiter. Always `0x68`.
  - [Unsigned Short] Byte size of the frame. Includes CRC and frame end delimiter. 
  - [Byte] Recipient address.
  - [Byte] Sender address.
  - [Byte] Sender type. PyPlumIO uses EcoNET type `0x30`.
  - [Byte] ecoNET version. PyPlumIO uses version `0x05`.
- Body:
  - [Byte] Frame type.
  - [Byte*] Message data (optional).
  - [Byte] Frame CRC.
  - [Byte] Frame end delimiter. Always `0x16`.

### Requests and Responses
Frames can be split into requests, responses and messages. See [requests.py](https://github.com/denpamusic/PyPlumIO/blob/main/pyplumio/frames/requests.py), [responses.py](https://github.com/denpamusic/PyPlumIO/blob/main/pyplumio/frames/responses.py) and [messages.py](https://github.com/denpamusic/PyPlumIO/blob/main/pyplumio/frames/messages.py) for a list of supported frames.

For example we can request list of editable parameters from the controller by sending frame with frame type `0x31` and receive response with frame type `0xB1` that contains requested parameters.

### Communication
ecoMAX controller constantly sends `ProgramVersion[type=0x40]` and `CheckDevice[type=0x30]` requests to every known device on the network and broadcasts `RegData[type=0x08]` message, that contains basic controller data.

Initial exchange between ecoMAX controller and PyPlumIO library can be illustrated with following diagram:

_NOTE: device network address is listed in square brackets._

```
ecoMAX[0x45] -> Broadcast[0x00]: RegData[type=0x08] Contains basic ecoMAX data.
ecoMAX[0x45] -> PyPlumIO[0x56]:  ProgramVersion[type=0x40] Program version request.
ecoMAX[0x45] <- PyPlumIO[0x56]:  ProgramVersion[type=0xC0] Contains program version.
ecoMAX[0x45] -> PyPlumIO[0x56]:  CheckDevice[type=0x30] Check device request.
ecoMAX[0x45] <- PyPlumIO[0x56]:  DeviceAvailable[type=0xB0] Contains network information.
ecoMAX[0x45] -> PyPlumIO[0x56]:  CurrentData[type=0x35] Contains current ecoMAX data.
```

### Versioning
Protocol has built-in way to track frame versions. This is used to synchronize changes between devices.
Both broadcast `RegData[type=0x08]` and unicast `CurrentData[type=0x35]` frames sent by ecoMAX controller contain versioning data.

This data can be represented with following dictionary:
```python
frame_versions: Dict[int, int] = {
  0x31: 37,
  0x32: 37,
  0x36: 1,
  0x38: 5,
  0x39: 1,
  0x3D: 40767,
  0x50: 1,
  0x51: 1,
  0x52: 1,
  0x53: 1,
}
```
In this dictionary keys are frame types and values are version numbers. In example above, frame `Parameters[type=0x31]` has version 37.
If we change any parameters either remotely or on ecoMAX itself, version number will increase, so PyPlumIO will be able to tell that it's need to request list of parameters again to obtain changes.
```python
frame_versions: Dict[int, int] = {
  0x31: 38,  # Note version number change.
  0x32: 37,
  0x36: 1,
  0x38: 5,
  0x39: 1,
  0x3D: 40767,
  0x50: 1,
  0x51: 1,
  0x52: 1,
  0x53: 1,
}
```

## Home Assistant Integration
There is companion Home Assistant integration that is being co-developed with this package and depends on it. Click button below to check it out.

[![hass integration](https://img.shields.io/badge/hass%20integration-v0.2.5-41bdf5)](https://github.com/denpamusic/homeassistant-plum-ecomax)

## Attribution
Special thanks to [econetanalyze](https://github.com/twkrol/econetanalyze) project by twkrol for initial information about protocol.

## License
This product is distributed under MIT license.
