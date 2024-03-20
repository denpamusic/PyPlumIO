.. PyPlumIO documentation master file, created by
   sphinx-quickstart on Mon Feb 13 10:56:31 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to PyPlumIO's documentation!
====================================

This project aims to provide complete and easy to use solution for communicating with
climate devices by `Plum Sp. z o.o. <https://www.plum.pl/>`_

Currently it supports reading and writing parameters of ecoMAX controllers by
Plum Sp. z o.o., getting service password and sending network information to
show on controller's display.

Devices can be connected directly via RS-485 to USB adapter or through network by using
RS-485 to Ethernet/WiFi converter.

Quickstart
==========
1. To use PyPlumIO, first install it using pip:

.. code-block:: console

    (.venv) $ pip install pyplumio

2. Connect to the ecoMAX controller:

>>> connection = pyplumio.open_serial_connection("/dev/ttyUSB0")
>>> await connection.connect()
>>> ecomax = await connection.get("ecomax")

3. Print some values:

>>> print(await ecomax.get("heating_temp"))

4. Don't forget to close the connection:

>>> await connection.close()

Documentation
=============
.. toctree::
   :maxdepth: 2
   :caption: Contents:
   
   connecting
   reading
   writing
   callbacks
   mixers_thermostats
   schedules
   protocol

.. autosummary::
   :toctree: _autosummary
