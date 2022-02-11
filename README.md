# PyPlumIO is a native ecoNET library for Plum ecoMAX controllers.
[![PyPI version](https://badge.fury.io/py/PyPlumIO.svg)](https://badge.fury.io/py/PyPlumIO)
[![PyPI Supported Python Versions](https://img.shields.io/pypi/pyversions/pyplumio.svg)](https://pypi.python.org/pypi/pyplumio/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PyPlumIO CI](https://github.com/denpamusic/PyPlumIO/actions/workflows/ci.yml/badge.svg)](https://github.com/denpamusic/PyPlumIO/actions/workflows/ci.yml)
[![Maintainability](https://api.codeclimate.com/v1/badges/9f275fbc50fe9082a909/maintainability)](https://codeclimate.com/github/denpamusic/PyPlumIO/maintainability)
[![Test Coverage](https://api.codeclimate.com/v1/badges/9f275fbc50fe9082a909/test_coverage)](https://codeclimate.com/github/denpamusic/PyPlumIO/test_coverage)

## Overview
This package aims to provide complete and easy to use solution for communicating with climate devices by [Plum Sp. z o.o.](https://www.plum.pl/)

Currently it supports reading and writing parameters of ecoMAX automatic pellet boiler controllers, getting service password and sending network information to display on regulator panel.

Devices can be connected directly via RS485 to USB converter or through network by using serial port server (for example [Elfin EW11](https://aliexpress.ru/item/4001104348624.html))

This project is considered to be in __Pre-Alpha__ state and there __will be__ breaking changes down the road and a lot of bugs, please use with care.

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
- [Attribution](#attribution)
- [License](#license)

## Usage
To interact with devices, you must pass async callback to `EcoNET.run(callback: Callable, interval: int)` method. Callback will receive `pyplumio.DeviceCollection` instance `devices` that will contain all found supported devices and `pyplumio.EcoNET` class instance `econet` that represents current connection.

Second optional parameter for `EcoNET.run(callback: Callable, interval: int)` method - `interval` defines how often the callback will be called in seconds. If unspecified, callback will be called every second.

You can find examples for each supported connection type below.

### TCP
```python
import pyplumio

async def my_callback(devices, econet):
	# do something
	...

connection = pyplumio.TcpConnection(host="localhost", port=8899)
connection.run(my_callback, interval=1)
```

### Serial
```python
import pyplumio

async def my_callback(devices, econet):
	# do something
	...

connection = pyplumio.SerialConnection(device="/dev/ttyUSB0", baudrate=115200)
connection.run(my_callback, interval=1)
```

### Shortcuts
It's also possible to use following shortcuts to create connection instance and instantly run it.
```python
import pyplumio

pyplumio.tcp(my_callback, host="localhost", port=8899, interval=1)
# or
pyplumio.serial(my_callback, device="/dev/ttyUSB0", baudrate=115200, interval=1)
```

### Data and Parameters
Data is separated into immutable `data` that you can't change and `parameters` that you can. Both can be accessed via instance attributes `devices.ecomax.data['HEATING_TEMP']`, `devices.ecomax.parameters['HEATING_SET_TEMP']` or as shortcut `devices.ecomax.heating_temp`, `devices.ecomax.heating_set_temp`.

Each regulator supports different data attributes and parameters. You can check what your regulator supports by calling `print()` on regulator instance.
```python
async def my_callback(devices, econet):
    if devices.ecomax:
        print(devices.ecomax)
```

### Reading
Interaction with device is mainly done through device class instances inside your callback.
For example you can read current feedwater temperature by reading `heating_temp` attribute.

This example, once passed to `EcoNET.run(callback: Callable, interval: int)` as demonstrated above, will print current feedwater temperature every second.
```python
async def my_callback(devices, econet):
    if devices.ecomax:
        print(devices.ecomax.heating_temp)  # 61.923828125
```

### Writing
You can easily set regulator parameter by changing respective class attribute. Example below will set target temperature to 65 degrees celsius and close connection.
```python
async def my_callback(devices, econet):
    if devices.ecomax and devices.ecomax.heating_set_temp is not None:
    	devices.ecomax.heating_set_temp = 65  # This will set target temperature to 65 degrees Celsius.
        econet.close()
```
Please note that each parameter has range of acceptable values that you must check and honor by yourself. This package currently silently ignores out of range values. You can check allowed values by reading `min_` and `max_` attributes.
```python
async def my_callback(devices, econet):
    if devices.ecomax and devices.ecomax.heating_set_temp is not None:
    	print(devices.ecomax.heating_set_temp.min_)  # Prints minimum allowed target temperature.
        print(devices.ecomax.heating_set_temp.max_)  # Prints maximum allowed target temperature.
```

### Network and WIFI
You can send network information to the regulator to be displayed on regulator's LCD as illustrated below.

Currently it's used for informational purposes only and can be skipped altogether.
```python
import pyplumio
from pyplumio.constants import WLAN_ENCRYPTION_WPA2

async def my_callback(devices, econet):
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

## Attribution
Special thanks to [econetanalyze](https://github.com/twkrol/econetanalyze) project by twkrol for initial information about protocol.

## License
This product is distributed under MIT license.
