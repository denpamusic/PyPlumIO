# PyPlumIO is a native ecoNET library for Plum ecoMAX controllers.
[![PyPI version](https://badge.fury.io/py/PyPlumIO.svg)](https://badge.fury.io/py/PyPlumIO)
[![PyPI Supported Python Versions](https://img.shields.io/pypi/pyversions/pyplumio.svg)](https://pypi.python.org/pypi/pyplumio/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PyPlumIO CI](https://github.com/denpamusic/PyPlumIO/actions/workflows/ci.yml/badge.svg)](https://github.com/denpamusic/PyPlumIO/actions/workflows/ci.yml)
[![Maintainability](https://api.codeclimate.com/v1/badges/9f275fbc50fe9082a909/maintainability)](https://codeclimate.com/github/denpamusic/PyPlumIO/maintainability)
[![Test Coverage](https://api.codeclimate.com/v1/badges/9f275fbc50fe9082a909/test_coverage)](https://codeclimate.com/github/denpamusic/PyPlumIO/test_coverage)
[![stability-release-candidate](https://img.shields.io/badge/stability-pre--release-48c9b0.svg)](https://guidelines.denpa.pro/stability#release-candidate)

## Overview
This package aims to provide complete and easy to use solution for communicating with climate devices by [Plum Sp. z o.o.](https://www.plum.pl/)

![ecoMAX controllers](https://raw.githubusercontent.com/denpamusic/PyPlumIO/main/images/ecomax.png)

Currently it supports reading and writing parameters of ecoMAX controllers by Plum Sp. z o.o., getting service password and sending network information to show on controller's display.

Devices can be connected directly via RS-485 to USB adapter or through network by using RS-485 to Ethernet/WiFi converter.

![RS-485 converters](https://raw.githubusercontent.com/denpamusic/PyPlumIO/main/images/rs485.png)

## Table of contents
- [Connecting](https://pyplumio.denpa.pro/connecting.html)
- [Reading](https://pyplumio.denpa.pro/reading.html)
- [Writing](https://pyplumio.denpa.pro/writing.html)
- [Callbacks](https://pyplumio.denpa.pro/callbacks.html)
- [Mixers/Thermostats](https://pyplumio.denpa.pro/mixers_thermostats.html)
- [Schedules](https://pyplumio.denpa.pro/schedules.html)
- [Protocol](https://pyplumio.denpa.pro/protocol.html)
  - [Frame Structure](https://pyplumio.denpa.pro/protocol.html#frame-structure)
  - [Requests and Responses](https://pyplumio.denpa.pro/protocol.html#requests-and-responses)
  - [Communication](https://pyplumio.denpa.pro/protocol.html#communication)
  - [Versioning](https://pyplumio.denpa.pro/protocol.html#versioning)


## Quickstart

1. To use PyPlumIO, first install it using pip:

```bash
$ pip install pyplumio
```

2. Connect to the ecoMAX controller:

```python
>>> connection = pyplumio.open_serial_connection("/dev/ttyUSB0")
>>> await connection.connect()
>>> ecomax = await connection.get("ecomax")
```

3. Print some values:
```python
>>> print(await ecomax.get("heating_temp"))
```

4. Don’t forget to close the connection:
```python
>>> await connection.close()
```

## Home Assistant Integration
There is companion Home Assistant integration that is being co-developed with this package and depends on it. Click button below to check it out.

[![Plum ecoMAX for Home Assistant](https://img.shields.io/badge/Plum%20ecoMAX%20for%20Home%20Assistant-41bdf5)](https://github.com/denpamusic/homeassistant-plum-ecomax)

## Attribution
Special thanks to [econetanalyze](https://github.com/twkrol/econetanalyze) project by twkrol for initial information about protocol.

## License
This product is distributed under MIT license.
