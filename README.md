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
  - [Shortcuts](#serial)
  - [Data and Parameters](#data-and-parameters)
  - [Reading](#reading)
  - [Writing](#writing)
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
To interact with devices, you must pass async callback to `Connection.run(callback: Callable[[DeviceCollection, Connection], Awaitable[Any]], interval: int)` method. Callback will receive two arguments: `devices: DeviceCollection` that will contain all found supported devices and `connection: Connection` that represents current connection.

Second optional parameter `interval`, defines how often the callback will be called in seconds. If left unspecified, callback will be called every second.

You can find examples for each supported connection type below.

### TCP
This is intended to be used with RS-485 to Ethernet/WiFi converters, which are readily available online or can be custom built using RS-485 to USB converter and ser2net software.

```python
from pyplumio import TcpConnection
from pyplumio.devices import DeviceCollection

async def my_callback(devices: DeviceCollection, connection):
	# do something
	...

connection = TcpConnection(host="localhost", port=8899)
connection.run(my_callback, interval=1)
```

### Serial
This is intended to be used with RS-485 to USB adapters, that are connected directly to the device running PyPlumIO.

```python
from pyplumio import SerialConnection
from pyplumio.devices import DeviceCollection

async def my_callback(devices: DeviceCollection, connection):
	# do something
	...

connection = SerialConnection(device="/dev/ttyUSB0", baudrate=115200)
connection.run(my_callback, interval=1)
```

### Shortcuts
It's also possible to use following shortcuts to create connection instance and instantly run it.
```python
from pyplumio import tcp as pyplumio_tcp, serial as pyplumio_serial
from pyplumio.devices import DeviceCollection

async def my_callback(devices: DeviceCollection, connection):
	# do something
	...

pyplumio_tcp(my_callback, host="localhost", port=8899, interval=1)
# or
pyplumio_serial(my_callback, device="/dev/ttyUSB0", baudrate=115200, interval=1)
```

### Data and Parameters
Data is separated into immutable `data` that can't be changed and `parameters` that can. Both can be accessed via instance attributes. (e. g. `devices.ecomax.heating_temp`, `devices.ecomax.heating_target_temp`)

Each ecoMAX controller supports different data attributes and parameters. You can check what your controller supports by calling `print()` on controller instance in device collection.
```python
async def my_callback(devices: DeviceCollection, connection):
    if devices.has("ecomax"):
        print(devices.ecomax)
```

### Reading
Interaction with the device is mainly done through device class instances inside your callback.
For example you can read current feed water temperature by reading `heating_temp` attribute.

Passing my_callback function to `Connection.run(callback: Callable[[DeviceCollection, Connection], Awaitable[Any]], interval: int)` as demonstrated above, will print current feed water temperature every second.
```python
async def my_callback(devices: DeviceCollection, connection):
    if devices.has("ecomax"):
        print(devices.ecomax.heating_temp)  # e. g. 61.923828125
```

### Writing
You can easily change controller parameters by modifying their respective class attribute. In example below, we will set target temperature to 65 degrees Celsius (~ 150 degrees Fahrenheit) and close the connection.
```python
async def my_callback(devices: DeviceCollection, connection):
    if devices.has("ecomax") and devices.ecomax.has("heating_target_temp"):
        """This will set target heating temperature to 65 degrees Celsius.
        and close the connection.
        """
    	devices.ecomax.heating_target_temp = 65
        connection.close()
```
Please note that each parameter has a range of acceptable values that you must check by yourself. The PyPlumIO library currently silently ignores out of range values. You can check allowed values by reading `min_value` and `max_value` attributes of parameter instance.
```python
async def my_callback(devices: DeviceCollection, connection):
    if devices.has("ecomax") and devices.ecomax.has("heating_target_temp"):
        print(devices.ecomax.heating_target_temp.min_value)  # Prints minimum allowed target temperature.
        print(devices.ecomax.heating_target_temp.max_value)  # Prints maximum allowed target temperature.
```

### Network Information
You can send network information to the controller that will be shown on it's display.

It's used for informational purposes only and can be skipped.
```python
from pyplumio import TcpConnection
from pyplumio.devices import DeviceCollection
from pyplumio.helpers.network_info import WLAN_ENCRYPTION_WPA2

async def my_callback(devices: DeviceCollection, connection):
	# do something
	...

with TcpConnection(host="localhost", port=8899) as c:
    c.set_eth(ip="10.10.1.100", netmask="255.255.255.0", gateway="10.10.1.1")
    c.set_wlan(
        ip="10.10.2.100",
        netmask="255.255.255.0",
        gateway="10.10.2.1",
        ssid="My WIFI",
        encryption=WLAN_ENCRYPTION_WPA2,
        quality=100
    )
    c.run(my_callback)
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
  0x31: 38,  # note version number change
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

[![hass integration](https://img.shields.io/badge/hass%20integration-v0.1.2-41bdf5)](https://github.com/denpamusic/homeassistant-plum-ecomax)

## Attribution
Special thanks to [econetanalyze](https://github.com/twkrol/econetanalyze) project by twkrol for initial information about protocol.

## License
This product is distributed under MIT license.
