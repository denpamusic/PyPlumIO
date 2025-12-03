Frames
======

StopMaster
----------

Stop the ecoMAX controller transmission.

Request
^^^^^^^

.. autoattribute:: pyplumio.const.FrameType.REQUEST_STOP_MASTER

StartMaster
-----------

Start the ecoMAX controller transmission.

Request
^^^^^^^

.. autoattribute:: pyplumio.const.FrameType.REQUEST_START_MASTER

CheckDevice
-----------

Check if device is available. This frame is being broadcasted by the ecoMAX
controller to all connected devices.

The response to this request can contain the network parameters as
represented by the following dataclass:

.. autoclass:: pyplumio.structures.network_info.NetworkInfo

Request
^^^^^^^

.. autoattribute:: pyplumio.const.FrameType.REQUEST_CHECK_DEVICE

Response
^^^^^^^^

.. autoattribute:: pyplumio.const.FrameType.RESPONSE_DEVICE_AVAILABLE

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Name
     - Description
   * - network
     - Contains network parameters.


EcomaxParameters
----------------

Get the ecoMAX controller editable parameters.
Each parameter is represented by a tuple containing parameter index and parameter
values represented by the following dataclass:

.. autoclass:: pyplumio.parameters.ParameterValues

Request
^^^^^^^

.. autoattribute:: pyplumio.const.FrameType.REQUEST_ECOMAX_PARAMETERS

.. list-table::
   :widths: 20 65 10
   :header-rows: 1

   * - Name
     - Description
     - Default
   * - start
     - Parameter index to start on.
     - 0
   * - count
     - Number of parameters to request.
     - 255

Response
^^^^^^^^

.. autoattribute:: pyplumio.const.FrameType.RESPONSE_ECOMAX_PARAMETERS

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Name
     - Description
   * - ecomax_parameters
     - Contains a list of ecomax parameters.

Handler
^^^^^^^

.. autoclass:: pyplumio.structures.ecomax_parameters.EcomaxParametersStructure

MixerParameters
---------------

Get the editable parameters for each connected mixer.

Request
^^^^^^^

.. autoattribute:: pyplumio.const.FrameType.REQUEST_MIXER_PARAMETERS

.. list-table::
   :widths: 20 65 10
   :header-rows: 1

   * - Name
     - Description
     - Default
   * - device_index
     - Mixer index.
     -
   * - start
     - Parameter index to start on.
     - 0
   * - count
     - Number of parameters to request.
     - 255

Response
^^^^^^^^

.. autoattribute:: pyplumio.const.FrameType.RESPONSE_MIXER_PARAMETERS

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Name
     - Description
   * - mixer_parameters
     - Contains a list of parameters for each connected mixer.

Handler
^^^^^^^

.. autoclass:: pyplumio.structures.mixer_parameters.MixerParametersStructure

SetEcomaxParameter
------------------

Set the editable parameter value.

Request
^^^^^^^

.. autoattribute:: pyplumio.const.FrameType.REQUEST_SET_ECOMAX_PARAMETER

.. list-table::
   :widths: 20 65 10
   :header-rows: 1

   * - Name
     - Description
     - Default
   * - index
     - Parameter index.
     - 
   * - value
     - Value to set parameter to.
     - 

Response
^^^^^^^^

.. autoattribute:: pyplumio.const.FrameType.RESPONSE_SET_ECOMAX_PARAMETER

SetMixerParameter
-----------------

Set the editable parameter for the connected mixer.

Request
^^^^^^^

.. autoattribute:: pyplumio.const.FrameType.REQUEST_SET_MIXER_PARAMETER

.. list-table::
   :widths: 20 65 10
   :header-rows: 1

   * - Name
     - Description
     - Default
   * - device_index
     - Mixer index.
     -
   * - index
     - Parameter index.
     - 
   * - value
     - Value to set parameter to.
     - 

Response
^^^^^^^^

.. autoattribute:: pyplumio.const.FrameType.RESPONSE_SET_MIXER_PARAMETER

Schedules
---------

Get the list of schedules from the ecoMAX controller.
This doesn't include schedules from thermostat (ecoSTER) devices.

Request
^^^^^^^

.. autoattribute:: pyplumio.const.FrameType.REQUEST_SCHEDULES

Response
^^^^^^^^

.. autoattribute:: pyplumio.const.FrameType.RESPONSE_SCHEDULES

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Name
     - Description
   * - schedules
     - Contains a list of schedules.
   * - schedule_parameters
     - Contains a list of schedule parameters.

Handler
^^^^^^^

.. autoclass:: pyplumio.structures.schedules.SchedulesStructure

SetSchedule
-----------

Set the schedule on the ecoMAX controller.
All schedules must be passed with this request all at once, even
unchanged ones.

Request
^^^^^^^

.. autoattribute:: pyplumio.const.FrameType.REQUEST_SET_SCHEDULE

.. list-table::
   :widths: 20 65 10
   :header-rows: 1

   * - Name
     - Description
     - Default
   * - data
     - List of schedule data.
     -
   * - switch
     - List of values for a schedule switches (on/off).
     - 
   * - parameter
     - List of values for a schedule parameters
     - 

UID
---

Get the device identification as presented in the following dataclass:

.. autoclass:: pyplumio.structures.product_info.ProductInfo

Request
^^^^^^^

.. autoattribute:: pyplumio.const.FrameType.REQUEST_UID

Response
^^^^^^^^

.. autoattribute:: pyplumio.const.FrameType.RESPONSE_UID

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Name
     - Description
   * - product_info
     - Contains a product info.

Handler
^^^^^^^

.. autoclass:: pyplumio.structures.product_info.ProductInfoStructure

Password
--------

Get the device service password.

Request
^^^^^^^

.. autoattribute:: pyplumio.const.FrameType.REQUEST_PASSWORD

Response
^^^^^^^^

.. autoattribute:: pyplumio.const.FrameType.RESPONSE_PASSWORD

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Name
     - Description
   * - password
     - Contains a device service password.

EcomaxControl
-------------

Turns the ecoMAX controller on or off.

Request
^^^^^^^

.. autoattribute:: pyplumio.const.FrameType.REQUEST_ECOMAX_CONTROL

.. list-table::
   :widths: 20 65 10
   :header-rows: 1

   * - Name
     - Description
     - Default
   * - value
     - Value that describes wanted state. 0 - off, 1 - on
     -

Response
^^^^^^^^

.. autoattribute:: pyplumio.const.FrameType.RESPONSE_ECOMAX_CONTROL

Alerts
------

Get the list of device alerts, each is represented by the following dataclass:

.. autoclass:: pyplumio.structures.alerts.Alert

Request
^^^^^^^

.. autoattribute:: pyplumio.const.FrameType.REQUEST_ALERTS

.. list-table::
   :widths: 20 65 10
   :header-rows: 1

   * - Name
     - Description
     - Default
   * - start
     - Index to start on.
     - 0
   * - count
     - Number of alerts to request.
     - 10

Response
^^^^^^^^

.. autoattribute:: pyplumio.const.FrameType.RESPONSE_ALERTS

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Name
     - Description
   * - alerts
     - Contains a list of alerts.

Handler
^^^^^^^

.. autoclass:: pyplumio.structures.alerts.AlertsStructure


ProgramVersion
--------------

Get the software version, represented by the following dataclass:

.. autoclass:: pyplumio.structures.program_version.VersionInfo

It is broadcasted by the ecoMAX controller to all connected devices.

Request
^^^^^^^

.. autoattribute:: pyplumio.const.FrameType.REQUEST_PROGRAM_VERSION

Response
^^^^^^^^

.. autoattribute:: pyplumio.const.FrameType.RESPONSE_PROGRAM_VERSION

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Name
     - Description
   * - version_info
     - Contains software version.

Handler
^^^^^^^

.. autoclass:: pyplumio.structures.program_version.ProgramVersionStructure


RegulatorDataSchema
-------------------

Get the regulator data schema, that describes the data type of :ref:`regulatordata` message.

It's represented by dictionary, that's indexed by regulator data field id and
a member of the following DataType class, that defines the regulator data field type.

.. autoclass:: pyplumio.data_types.DataType

Request
^^^^^^^

.. autoattribute:: pyplumio.const.FrameType.REQUEST_REGULATOR_DATA_SCHEMA

Response
^^^^^^^^

.. autoattribute:: pyplumio.const.FrameType.RESPONSE_REGULATOR_DATA_SCHEMA

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Name
     - Description
   * - regdata_schema
     - Contains regulator data schema.

Handler
^^^^^^^

.. autoclass:: pyplumio.structures.regulator_data_schema.RegulatorDataSchemaStructure

ThermostatParameters
--------------------

Request
^^^^^^^

.. autoattribute:: pyplumio.const.FrameType.REQUEST_THERMOSTAT_PARAMETERS

.. list-table::
   :widths: 20 65 10
   :header-rows: 1

   * - Name
     - Description
     - Default
   * - device_index
     - Mixer index.
     -
   * - start
     - Parameter index to start on.
     - 0
   * - count
     - Number of parameters to request.
     - 255

Response
^^^^^^^^

.. autoattribute:: pyplumio.const.FrameType.RESPONSE_THERMOSTAT_PARAMETERS

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Name
     - Description
   * - thermostat_profile
     - Contains current thermostat profile or None.
   * - thermostat_parameters
     - Contains list of thermostat parameters.


Handler
^^^^^^^

.. autoclass:: pyplumio.structures.thermostat_parameters.ThermostatParametersStructure

SetThermostatParameter
----------------------

Set the editable parameter for the connected thermostat.

Request
^^^^^^^

.. autoattribute:: pyplumio.const.FrameType.REQUEST_SET_THERMOSTAT_PARAMETER

.. list-table::
   :widths: 20 65 10
   :header-rows: 1

   * - Name
     - Description
     - Default
   * - offset
     - Parameter offset. (n\ :sub:`thermostat` \ * n\ :sub:`parameters per thermostat` \)
     -
   * - index
     - Parameter index.
     - 
   * - value
     - Value to set parameter to.
     - 

Response
^^^^^^^^

.. autoattribute:: pyplumio.const.FrameType.RESPONSE_SET_THERMOSTAT_PARAMETER

RegulatorData
-------------

Special message that is broadcasted by the ecoMAX controller at regular interval.
It contains all controller's data indexed by numerical keys.

As this is broadcasted message, there's no need to send a request, but in order to be
decoded, :ref:`regulatordataschema` request must be send to obtain the schema.

Message
^^^^^^^

.. autoattribute:: pyplumio.const.FrameType.MESSAGE_REGULATOR_DATA

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Name
     - Description
   * - regdata
     - Contains regulator data indexed by numerical keys.


Handler
^^^^^^^

.. autoclass:: pyplumio.structures.frame_versions.FrameVersionsStructure

.. autoclass:: pyplumio.structures.regulator_data.RegulatorDataStructure

SensorData
----------

Special message that is being send by the ecoMAX controller as result of responding
to :ref:`checkdevice` request.

Unlike :ref:`regulatordata`, it's structure is predetermined and consistent across
all ecoMAX controllers and thus can be decoded without schema. However, it only contains
common sensors and lacks controller-specific sensors.

.. note::

    Some of the attributes listed below, might be unsupported by your ecoMAX controller.

Message
^^^^^^^

.. autoattribute:: pyplumio.const.FrameType.MESSAGE_SENSOR_DATA

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Name
     - Description
   * - fan
     - Blower fan status.
   * - feeder
     - Feeder status.
   * - heating_pump
     - Heating pump status.
   * - water_heater_pump
     - Water heater pump status.
   * - circulation_pump
     - Hot water recirculation pump status.
   * - lighter
     - Lighter status.
   * - alarm
     - Alarm status.
   * - outer_boiler
     - Outer boiler status.
   * - fan2_exhaust
     - Exhaust fan status.
   * - feeder2
     - Secondary feeder status.
   * - outer_feeder
     - Outer feeder status.
   * - solar_pump
     - Solar pump status.
   * - fireplace_pump
     - Fireplace pump status.
   * - heating_pump_flag
     - Indicates whether heating pump is connected.
   * - water_heater_pump_flag
     - Indicates whether water heater pump is connected.
   * - circulation_pump_flag
     - Indicates whether hot water recirculation pump is connected.
   * - solar_pump_flag
     - Indicates whether solar pump is connected.
   * - heating_temp
     - Heating temperature.
   * - feeder_temp
     - Feeder temperature.
   * - water_heater_temp
     - Water heater temperature.
   * - outside_temp
     - Outside temperature.
   * - return_temp
     - Return feedwater temperature.
   * - exhaust_temp
     - Exhaust fumes temperature.
   * - optical_temp
     - Flame intensity in percent.
   * - upper_buffer_temp
     - Upper buffer temperature.
   * - lower_buffer_temp
     - Lower buffer temperature.
   * - upper_solar_temp
     - Upper solar buffer temperature.
   * - lower_solar_temp
     - Lower solar buffer temperature.
   * - fireplace_temp
     - Fireplace temperature.
   * - heating_target
     - Heating target temperature.
   * - heating_status
     - Heating status.
   * - water_heater_target
     - Water heater target temperature.
   * - water_heater_status
     - Water heater status.
   * - pending_alerts
     - Number of pending alerts.
   * - fuel_level
     - Current fuel level in percent.
   * - fan_power
     - Current fan power in percent.
   * - boiler_load
     - Boiler load (power) in percent.
   * - boiler_power
     - Boiler power in kWh.
   * - fuel_consumption
     - Current fuel consumption in kg/h.
   * - modules
     - Dataclass containing versions of the connected modules.
   * - lambda_state
     - Current lambda sensor state.
   * - lambda_target
     - Lambda sensor target.
   * - lambda_level
     - Lambda sensor level.
   * - thermostat_sensor
     - Thermostat sensors.
   * - thermsotats_available
     - Number of thermostats supported by your controller.
   * - thermostats_connected
     - Number of thermostats currently connected to your controller.
   * - mixer_sensor
     - Mixer sensors.
   * - mixers_available
     - Number of mixers supported by your controller.
   * - mixers_connected
     - Number of mixers currently connected to your controller.

Handlers
^^^^^^^^

.. autoclass:: pyplumio.structures.frame_versions.FrameVersionsStructure

.. autoclass:: pyplumio.structures.sensor_data.SensorDataStructure
