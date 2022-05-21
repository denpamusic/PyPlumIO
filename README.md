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

Currently it supports reading and writing parameters of ecoMAX automatic pellet boiler controllers, getting service password and sending network information to display on regulator panel.

Devices can be connected directly via RS485 to USB converter or through network by using serial port server (for example [Elfin EW11](https://aliexpress.ru/item/4001104348624.html))

## Table of contents
- [Usage](#usage)
  - [TCP](#tcp)
  - [Serial](#serial)
  - [Shortcuts](#serial)
  - [Data and Parameters](#data-and-parameters)
  - [Reading](#reading)
  - [Writing](#writing)
  - [Network and WIFI](#network-and-wifi)
- [Home Assistant Integration](#home-assistant-integration)
- [Protocol](#protocol)
  - [Frame Structure](#frame-structure)
  - [Requests and Responses](#requests-and-responses)
  - [Communication](#communication)
  - [Versioning](#versioning)
- [Attribution](#attribution)
- [License](#license)

## Usage
To interact with devices, you must pass async callback to `EcoNET.run(callback: Callable, interval: int)` method. Callback will receive `pyplumio.DeviceCollection` instance `devices` that will contain all found supported devices and `pyplumio.EcoNET` class instance `econet` that represents current connection.

Second optional parameter for `EcoNET.run(callback: Callable, interval: int)` method - `interval` defines how often the callback will be called in seconds. If unspecified, callback will be called every second.

You can find examples for each supported connection type below.

### TCP
This is intended to be used with serial to network converters like ser2net server or dedicated devices such as Elfin EW11 mentioned in the [Overview](#overview).

```python
import pyplumio

async def my_callback(devices, connection):
	# do something
	...

connection = pyplumio.TcpConnection(host="localhost", port=8899)
connection.run(my_callback, interval=1)
```

### Serial
This is intended to be used with RS485 to USB adapters, that are connected directly to the device running PyPlumIO.

```python
import pyplumio

async def my_callback(devices, connection):
	# do something
	...

connection = pyplumio.SerialConnection(device="/dev/ttyUSB0", baudrate=115200)
connection.run(my_callback, interval=1)
```

### Shortcuts
It's also possible to use following shortcuts to create connection instance and instantly run it.
```python
import pyplumio

async def my_callback(devices, connection):
	# do something
	...

pyplumio.tcp(my_callback, host="localhost", port=8899, interval=1)
# or
pyplumio.serial(my_callback, device="/dev/ttyUSB0", baudrate=115200, interval=1)
```

### Data and Parameters
Data is separated into immutable `data` that you can't change and `parameters` that you can. Both can be accessed via instance attributes `devices.ecomax.data['heating_temp']`, `devices.ecomax.parameters['heating_set_temp']` or as shortcut `devices.ecomax.heating_temp`, `devices.ecomax.heating_set_temp`.

Each regulator supports different data attributes and parameters. You can check what your regulator supports by calling `print()` on regulator instance.
```python
async def my_callback(devices, connection):
    if devices.has("ecomax"):
        print(devices.ecomax)
```

### Reading
Interaction with device is mainly done through device class instances inside your callback.
For example you can read current feedwater temperature by reading `heating_temp` attribute.

Passing my_callback to `EcoNET.run(callback: Callable, interval: int)` as demonstrated above, will print current feedwater temperature every second.
```python
async def my_callback(devices, connection):
    if devices.has("ecomax"):
        print(devices.ecomax.heating_temp)  # 61.923828125
```

### Writing
You can easily set regulator parameter by changing respective class attribute. Example below will set target temperature to 65 degrees Celsius and close the connection.
```python
async def my_callback(devices, connection):
    if devices.has("ecomax") and devices.ecomax.has("heating_set_temp"):
        """This will set target heating temperature to 65 degrees Celsius.
        and close the connection.
        """
    	devices.ecomax.heating_set_temp = 65
        connection.close()
```
Please note that each parameter has range of acceptable values that you must check and honor by yourself. This package currently silently ignores out of range values. You can check allowed values by reading `min_` and `max_` attributes.
```python
async def my_callback(devices, connection):
    if devices.has("ecomax") and devices.ecomax.has("heating_set_temp"):
        print(devices.ecomax.heating_set_temp.min_)  # Prints minimum allowed target temperature.
        print(devices.ecomax.heating_set_temp.max_)  # Prints maximum allowed target temperature.
```

### Network and WIFI
You can send network information to the regulator to be displayed on ecoMAX'es LCD.

Currently it's used for informational purposes only and can be safely ignored.
```python
import pyplumio
from pyplumio.constants import WLAN_ENCRYPTION_WPA2

async def my_callback(devices, connection):
	# do something
	...

with pyplumio.TcpConnection(host="localhost", port=8899) as c:
    c.set_eth(ip="10.10.1.100", netmask="255.255.255.0", gateway="10.10.1.1")
    c.set_wifi(
    	ip="10.10.2.100",
        netmask="255.255.255.0",
        gateway="10.10.2.1",
        ssid="My WIFI",
        encryption=WLAN_ENCRYPTION_WPA2,
        quality=100
    )
    c.run(my_callback)
```

## Home Assistant Integration
There is companion Home Assistant integration that is being co-developed with this package and depends on it.
You can find it [here](https://github.com/denpamusic/hassio-plum-ecomax).

## Protocol
ecoNET communication is based on RS485 standard. Each frame consists of header, message type, message data (optional), CRC and end delimiter.

Protocol supports unicast and broadcast frames. Broadcast frames always have recipient address set to `0x00`, unicast messages have specific device address. ecoMAX controller address is `0x45`, ecoSTER panel address is `0x51`.

### Frame Structure
- Header (header size - 7 bytes):
  - [Byte] Frame start mark `0x68`.
  - [Unsigned Short] Byte size of the frame including CRC and frame end mark.
  - [Byte] Recipient address.
  - [Byte] Sender address.
  - [Byte] Sender type. PyPlumIO uses EcoNET type `0x30`.
  - [Byte] ecoNET version. PyPlumIO uses version `0x05`.
- Body:
  - [Byte] Message type.
  - [Byte*] Message data (optional).
  - [Byte] Frame CRC.
  - [Byte] Frame end mark `0x16`.

### Requests and Responses
Frames can be split into requests and responses. See [requests.py](https://github.com/denpamusic/PyPlumIO/blob/main/pyplumio/requests.py) and [responses.py](https://github.com/denpamusic/PyPlumIO/blob/main/pyplumio/responses.py) for a list of supported frames.

For example we can request list of editable parameters from ecoMAX by sending frame with frame type `0x31` and receive response with frame type `0xB1` that contains requested parameters.

### Communication
ecoMAX constantly sends `ProgramVersion[type=0x40]` and `CheckDevice[type=0x30]` requests to every known device addresses and broadcasts `RegData[type=0x08]` message, that contains basic regulator data.

Initial exchange between ecoMAX and PyPlumIO can be illustrated with following diagram:

```
NOTE: device address is listed in square brackets.

ecoMAX[0x45] -> Broadcast[0x00]: RegData[type=0x08] Contains basic ecoMAX data.
ecoMAX[0x45] -> PyPlumIO[0x56]:  ProgramVersion[type=0x40] Program version request.
ecoMAX[0x45] <- PyPlumIO[0x56]:  ProgramVersion[type=0xC0] Contains program version.
ecoMAX[0x45] -> PyPlumIO[0x56]:  CheckDevice[type=0x30] Check device request.
ecoMAX[0x45] <- PyPlumIO[0x56]:  DeviceAvailable[type=0xB0] Contains network information.
ecoMAX[0x45] -> PyPlumIO[0x56]:  CurrentData[type=0x35] Contains current ecoMAX data.
```

PyPlumIO will then request all frames listed in frame version information from `RegData` and `CurrentData` responses. This includes at least `UID[type=0x39]`, `Parameters[type=0x31]` and `MixerParameters[type=0x32]` requests.

### Versioning
Protocol has built-in way to track frame versions. This is used to synchronize changes between devices.
Both broadcast `RegData[type=0x08]` and unicast `CurrentData[type=0x35]` frames send by ecoMAX controller contain versioning information.

This information can be represented with following dictionary:
```python
{
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
{
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

## Attribution
Special thanks to [econetanalyze](https://github.com/twkrol/econetanalyze) project by twkrol for initial information about protocol.

## License
This product is distributed under MIT license.
