"""Contains tests for the ecoMAX device."""

import asyncio
from datetime import timedelta
import logging
from typing import Any, Final, cast
from unittest.mock import AsyncMock, Mock, call, patch

import pytest

from pyplumio.const import (
    ATTR_CONNECTED,
    ATTR_FRAME_ERRORS,
    ATTR_INDEX,
    ATTR_OFFSET,
    ATTR_PARAMETER,
    ATTR_PASSWORD,
    ATTR_SCHEDULE,
    ATTR_SENSORS,
    ATTR_SETUP,
    ATTR_SIZE,
    ATTR_SWITCH,
    ATTR_TYPE,
    ATTR_VALUE,
    STATE_OFF,
    STATE_ON,
    DeviceState,
    DeviceType,
    FrameType,
    ProductType,
    State,
    UnitOfMeasurement,
)
from pyplumio.devices.ecomax import (
    ATTR_FUEL_BURNED,
    ATTR_MIXERS,
    ATTR_THERMOSTATS,
    DataKey,
    EcoMAX,
)
from pyplumio.devices.mixer import Mixer
from pyplumio.devices.thermostat import Thermostat
from pyplumio.exceptions import RequestError
from pyplumio.frames import Request, Response
from pyplumio.frames.messages import RegulatorDataMessage, SensorDataMessage
from pyplumio.frames.requests import (
    AlertsRequest,
    EcomaxControlRequest,
    EcomaxParametersRequest,
    EcomaxServiceParametersRequest,
    SetEcomaxParameterRequest,
    SetEcomaxServiceParameterRequest,
    SetScheduleRequest,
    SetThermostatParameterRequest,
    StartMasterRequest,
)
from pyplumio.frames.responses import (
    EcomaxParametersResponse,
    EcomaxServiceParametersResponse,
    MixerParametersResponse,
    SchedulesResponse,
    ThermostatParametersResponse,
)
from pyplumio.helpers.async_cache import AsyncCache
from pyplumio.helpers.event_manager import EventCallback
from pyplumio.parameters.ecomax import (
    PARAMETER_TYPES,
    EcomaxNumber,
    EcomaxNumberDescription,
    EcomaxServiceNumber,
    EcomaxServiceSwitch,
    EcomaxSwitch,
    EcomaxSwitchDescription,
    get_service_parameter_types,
)
from pyplumio.protocol import AsyncProtocol
from pyplumio.structures.alerts import ATTR_TOTAL_ALERTS
from pyplumio.structures.ecomax_parameters import (
    ATTR_ECOMAX_CONTROL,
    ATTR_ECOMAX_PARAMETERS,
)
from pyplumio.structures.ecomax_service_parameters import ATTR_ECOMAX_SERVICE_PARAMETERS
from pyplumio.structures.frame_versions import ATTR_FRAME_VERSIONS
from pyplumio.structures.mixer_parameters import ATTR_MIXER_PARAMETERS
from pyplumio.structures.network_info import ATTR_NETWORK_INFO, NetworkInfo
from pyplumio.structures.product_info import ATTR_PRODUCT, ProductInfo
from pyplumio.structures.regulator_data_schema import ATTR_REGDATA_SCHEMA
from pyplumio.structures.schedules import (
    ATTR_SCHEDULE_PARAMETER,
    ATTR_SCHEDULE_SWITCH,
    ATTR_SCHEDULES,
    Schedule,
    ScheduleDay,
    ScheduleNumber,
    ScheduleSwitch,
)
from pyplumio.structures.sensor_data import (
    ATTR_FUEL_CONSUMPTION,
    ATTR_MIXER_SENSORS,
    ATTR_MIXERS_AVAILABLE,
    ATTR_MIXERS_CONNECTED,
    ATTR_STATE,
    ATTR_THERMOSTAT_SENSORS,
    ATTR_THERMOSTATS_AVAILABLE,
    ATTR_THERMOSTATS_CONNECTED,
)
from pyplumio.structures.thermostat_parameters import (
    ATTR_THERMOSTAT_PARAMETERS,
    ATTR_THERMOSTAT_PROFILE,
)
from tests.conftest import (
    DUMMY_MODEL,
    UNDEFINED,
    class_from_json,
    equal_parameter_value,
    json_test_data,
)


@patch("asyncio.Queue.put_nowait")
@patch("pyplumio.devices.PhysicalDevice.handle_frame")
@patch("pyplumio.frames.Request.create_response", return_value=Mock(spec=Response))
async def test_ecomax_handle_frame(
    mock_response, mock_handle_frame, mock_put_nowait, ecomax: EcoMAX
) -> None:
    """Test ecoMAX frame handling."""
    request = Request()
    ecomax.handle_frame(request)
    args = mock_response.call_args[1]
    assert isinstance(args["data"][ATTR_NETWORK_INFO], NetworkInfo)
    mock_put_nowait.assert_called_once_with(mock_response.return_value)
    mock_handle_frame.assert_called_once_with(request)


@pytest.mark.parametrize(
    ("frame_type", "frame_request"),
    [
        (FrameType.REQUEST_ALERTS, AlertsRequest(recipient=DeviceType.ECOMAX)),
        (
            FrameType.REQUEST_ECOMAX_PARAMETER_CHANGES,
            EcomaxParametersRequest(recipient=DeviceType.ECOMAX),
        ),
    ],
)
@patch("asyncio.Queue.put_nowait")
@class_from_json(SensorDataMessage, "messages/sensor_data.json", arguments=("message",))
@class_from_json(
    RegulatorDataMessage, "messages/regulator_data.json", arguments=("message",)
)
async def test_frame_versions_tracker(
    mock_put_nowait,
    ecomax: EcoMAX,
    regulator_data: RegulatorDataMessage,
    sensor_data: SensorDataMessage,
    frame_type: FrameType,
    frame_request: Request,
) -> None:
    """Test frame version tracker."""

    def _frame_version_data(frame: FrameType, version: int) -> dict[str, Any]:
        """Replace frame data with new version information."""
        return {ATTR_SENSORS: {ATTR_FRAME_VERSIONS: {frame: version}}}

    # Test with frame type that are handled during setup.
    sensor_data.data = _frame_version_data(frame_type, 1)
    ecomax.handle_frame(sensor_data)
    await ecomax.wait_until_done()
    mock_put_nowait.assert_not_called()

    # Test with same frame type after setup done.
    mock_put_nowait.reset_mock()
    sensor_data.data = _frame_version_data(frame_type, 2)
    with patch.object(EcoMAX, "data", {ATTR_SETUP: True}):
        ecomax.handle_frame(sensor_data)
        await ecomax.wait_until_done()

    mock_put_nowait.assert_called_once_with(frame_request)

    # Test with multiple source frames (sensors from before + regdata).
    frame_versions_1 = ecomax.get_nowait(ATTR_FRAME_VERSIONS)
    assert frame_versions_1 == {frame_type: 2}
    ecomax.handle_frame(regulator_data)
    await ecomax.wait_until_done()
    frame_versions_2 = ecomax.get_nowait(ATTR_FRAME_VERSIONS)
    assert frame_versions_2 == {
        frame_type: 2,
        FrameType.REQUEST_REGULATOR_DATA_SCHEMA: 0,
        84: 0,
        FrameType.REQUEST_ECOMAX_SERVICE_PARAMETERS: 359,
        FrameType.REQUEST_ALERTS: 53918,
        FrameType.REQUEST_SCHEDULES: 1,
        100: 1,
        FrameType.REQUEST_PROGRAM_VERSION: 0,
    }


@patch("asyncio.Queue.put_nowait")
async def test_frame_versions_tracker_service_parameters(
    mock_put_nowait, ecomax: EcoMAX
) -> None:
    """Test frame version tracker with ecoMAX service parameters."""
    # Regulator data from ecoMAX 860P4-NM TOUCH, that announces version 6
    # of the service parameters frame.
    regulator_data = RegulatorDataMessage(
        message=bytes.fromhex(
            "6264000109559c95547ac86106003d9dc8360100640100400f525625271a0000"
        )
    )
    ecomax.handle_frame(regulator_data)
    await ecomax.wait_until_done()
    mock_put_nowait.assert_any_call(
        EcomaxServiceParametersRequest(recipient=DeviceType.ECOMAX)
    )

    # Test that same version is not requested again.
    mock_put_nowait.reset_mock()
    ecomax.handle_frame(regulator_data)
    await ecomax.wait_until_done()
    mock_put_nowait.assert_not_called()


@pytest.mark.parametrize("state", [STATE_ON, STATE_OFF])
async def test_ecomax_control(state: State, ecomax: EcoMAX, caplog) -> None:
    """Test ecoMAX control."""
    coro = getattr(ecomax, f"turn_{state}")
    await coro()
    assert "control is not available" in caplog.text
    switch = AsyncMock(spec=EcomaxSwitch)
    await ecomax.dispatch(ATTR_ECOMAX_CONTROL, switch)
    await coro()
    switch.set.assert_awaited_once_with(state, retries=0)


@pytest.mark.parametrize("state", [STATE_ON, STATE_OFF])
@patch("pyplumio.devices.ecomax.EcoMAX.create_task")
def test_ecomax_control_nowait(mock_create_task, ecomax: EcoMAX, state: State) -> None:
    """Test ecoMAX control without waiting for result."""
    func = getattr(ecomax, f"turn_{state}_nowait")
    with patch(
        f"pyplumio.devices.ecomax.EcoMAX.turn_{state}", new_callable=Mock
    ) as mock_coro:
        func()

    mock_coro.assert_called_once()
    mock_create_task.assert_called_once_with(mock_coro.return_value)


@patch("pyplumio.devices.mixer.Mixer.shutdown")
@patch("pyplumio.devices.thermostat.Thermostat.shutdown")
@patch("pyplumio.devices.Device.cancel_tasks")
@json_test_data("messages/sensor_data.json", selector="message")
async def test_ecomax_shutdown(
    mock_cancel_tasks,
    mock_thermostat_shutdown,
    mock_mixer_shutdown,
    ecomax: EcoMAX,
    sensor_data_message,
) -> None:
    """Test shutting down the ecoMAX and children tasks."""
    ecomax.handle_frame(SensorDataMessage(message=sensor_data_message))
    await ecomax.wait_until_done()

    with patch("pyplumio.devices.Device.wait_until_done") as mock_wait_until_done:
        await ecomax.shutdown()

    mock_wait_until_done.assert_awaited_once()
    mock_cancel_tasks.assert_called_once()
    mock_thermostat_shutdown.assert_awaited_once()
    mock_mixer_shutdown.assert_awaited_once()


@patch("pyplumio.devices.ecomax.EcoMAX.request")
@patch("pyplumio.devices.ecomax.EcoMAX.wait_for")
async def test_ecomax_setup(mock_wait_for, mock_request, ecomax: EcoMAX) -> None:
    """Test setting up an ecoMAX entry."""
    in_flight = 0
    max_in_flight = 0

    async def _sequential_request(*args: Any, **kwargs: Any) -> None:
        """Yield to the event loop and track concurrent in-flight requests."""
        nonlocal in_flight, max_in_flight
        in_flight += 1
        max_in_flight = max(max_in_flight, in_flight)
        loop = asyncio.get_running_loop()
        future: asyncio.Future[None] = loop.create_future()
        loop.call_soon(future.set_result, None)
        await future
        in_flight -= 1

    mock_request.side_effect = _sequential_request
    ecomax.dispatch_nowait(ATTR_SETUP, True)
    await ecomax.wait_until_done()
    assert ecomax.get_nowait(ATTR_SETUP) is True
    assert ATTR_FRAME_ERRORS not in ecomax.data
    assert max_in_flight == 1
    assert mock_request.await_args_list == [
        call(ATTR_REGDATA_SCHEMA, FrameType.REQUEST_REGULATOR_DATA_SCHEMA),
        call(ATTR_ECOMAX_PARAMETERS, FrameType.REQUEST_ECOMAX_PARAMETERS),
        call(
            ATTR_ECOMAX_SERVICE_PARAMETERS,
            FrameType.REQUEST_ECOMAX_SERVICE_PARAMETERS,
        ),
        call(ATTR_TOTAL_ALERTS, FrameType.REQUEST_ALERTS),
        call(ATTR_SCHEDULES, FrameType.REQUEST_SCHEDULES),
        call(ATTR_PASSWORD, FrameType.REQUEST_PASSWORD),
    ]
    mock_wait_for.assert_awaited_once_with(ATTR_SENSORS, timeout=60.0)

    # Test with connected mixers and thermostats.
    mock_request.reset_mock()
    await ecomax.dispatch(ATTR_MIXERS_CONNECTED, 1)
    await ecomax.dispatch(ATTR_THERMOSTATS_CONNECTED, 1)
    ecomax.dispatch_nowait(ATTR_SETUP, True)
    await ecomax.wait_until_done()
    assert ecomax.get_nowait(ATTR_SETUP) is True
    assert max_in_flight == 1
    assert mock_request.await_args_list == [
        call(ATTR_REGDATA_SCHEMA, FrameType.REQUEST_REGULATOR_DATA_SCHEMA),
        call(ATTR_ECOMAX_PARAMETERS, FrameType.REQUEST_ECOMAX_PARAMETERS),
        call(
            ATTR_ECOMAX_SERVICE_PARAMETERS,
            FrameType.REQUEST_ECOMAX_SERVICE_PARAMETERS,
        ),
        call(ATTR_TOTAL_ALERTS, FrameType.REQUEST_ALERTS),
        call(ATTR_SCHEDULES, FrameType.REQUEST_SCHEDULES),
        call(ATTR_MIXER_PARAMETERS, FrameType.REQUEST_MIXER_PARAMETERS),
        call(ATTR_THERMOSTAT_PARAMETERS, FrameType.REQUEST_THERMOSTAT_PARAMETERS),
        call(ATTR_PASSWORD, FrameType.REQUEST_PASSWORD),
    ]

    # Test skipping mixer/thermostat parameters when already in data.
    await ecomax.dispatch(ATTR_MIXER_PARAMETERS, {0: {}})
    await ecomax.dispatch(ATTR_THERMOSTAT_PARAMETERS, {0: {}})
    assert (
        ecomax._should_request_setup_key(
            DataKey(
                ATTR_MIXER_PARAMETERS,
                FrameType.REQUEST_MIXER_PARAMETERS,
                ATTR_MIXERS_CONNECTED,
            )
        )
        is False
    )
    assert (
        ecomax._should_request_setup_key(
            DataKey(
                ATTR_THERMOSTAT_PARAMETERS,
                FrameType.REQUEST_THERMOSTAT_PARAMETERS,
                ATTR_THERMOSTATS_CONNECTED,
            )
        )
        is False
    )


@patch("pyplumio.devices.ecomax.EcoMAX.request")
@patch("pyplumio.devices.ecomax.EcoMAX.wait_for", side_effect=(TimeoutError,))
async def test_ecomax_setup_failed(
    mock_wait_for, mock_request, ecomax: EcoMAX, caplog
) -> None:
    """Test setting up an ecoMAX entry with failure due to timeout."""
    ecomax.dispatch_nowait(ATTR_SETUP, True)
    await ecomax.wait_until_done()
    assert ecomax.get_nowait(ATTR_SETUP) is False
    assert "Could not setup device entry" in caplog.text
    assert "no response from device for 60 seconds" in caplog.text


@patch("pyplumio.devices.ecomax.EcoMAX.request")
@patch("pyplumio.devices.ecomax.EcoMAX.wait_for")
async def test_ecomax_setup_errors(mock_wait_for, mock_request, ecomax: EcoMAX) -> None:
    """Test setting up an ecoMAX entry with frame errors."""

    async def _request_with_error(key: str, frame_type: FrameType) -> None:
        """Raise RequestError for alerts and succeed for other keys."""
        if frame_type == FrameType.REQUEST_ALERTS:
            raise RequestError("test", frame_type)

    mock_request.side_effect = _request_with_error
    ecomax.dispatch_nowait(ATTR_SETUP, True)
    await ecomax.wait_until_done()
    assert ecomax.get_nowait(ATTR_FRAME_ERRORS, []) == [FrameType.REQUEST_ALERTS]
    assert ecomax.get_nowait(ATTR_SETUP) is True
    assert mock_request.await_args_list == [
        call(ATTR_REGDATA_SCHEMA, FrameType.REQUEST_REGULATOR_DATA_SCHEMA),
        call(ATTR_ECOMAX_PARAMETERS, FrameType.REQUEST_ECOMAX_PARAMETERS),
        call(
            ATTR_ECOMAX_SERVICE_PARAMETERS,
            FrameType.REQUEST_ECOMAX_SERVICE_PARAMETERS,
        ),
        call(ATTR_TOTAL_ALERTS, FrameType.REQUEST_ALERTS),
        call(ATTR_SCHEDULES, FrameType.REQUEST_SCHEDULES),
        call(ATTR_PASSWORD, FrameType.REQUEST_PASSWORD),
    ]
    assert (
        ecomax._should_request_setup_key(
            DataKey(ATTR_TOTAL_ALERTS, FrameType.REQUEST_ALERTS)
        )
        is False
    )

    # Re-running setup skips frame types already present in ATTR_FRAME_ERRORS.
    mock_request.reset_mock()
    ecomax.dispatch_nowait(ATTR_SETUP, True)
    await ecomax.wait_until_done()
    assert mock_request.await_args_list == [
        call(ATTR_REGDATA_SCHEMA, FrameType.REQUEST_REGULATOR_DATA_SCHEMA),
        call(ATTR_ECOMAX_PARAMETERS, FrameType.REQUEST_ECOMAX_PARAMETERS),
        call(
            ATTR_ECOMAX_SERVICE_PARAMETERS,
            FrameType.REQUEST_ECOMAX_SERVICE_PARAMETERS,
        ),
        call(ATTR_SCHEDULES, FrameType.REQUEST_SCHEDULES),
        call(ATTR_PASSWORD, FrameType.REQUEST_PASSWORD),
    ]
    mock_wait_for.assert_awaited_with(ATTR_SENSORS, timeout=60.0)


@patch("pyplumio.devices.ecomax.EcoMAX.request")
@patch("pyplumio.devices.ecomax.EcoMAX.wait_for")
async def test_ecomax_setup_disconnected(
    mock_wait_for, mock_request, ecomax: EcoMAX
) -> None:
    """Test aborting ecoMAX setup when disconnected."""
    # Disconnected before starting requests.
    await ecomax.dispatch(ATTR_CONNECTED, False)
    ecomax.dispatch_nowait(ATTR_SETUP, True)
    await ecomax.wait_until_done()
    mock_request.assert_not_awaited()
    assert ecomax.get_nowait(ATTR_SETUP) is False
    assert ATTR_FRAME_ERRORS not in ecomax.data

    # Disconnected mid-request when RequestError is raised.
    async def _disconnect_and_fail(key: str, frame_type: FrameType) -> None:
        """Mark device disconnected and raise RequestError."""
        await ecomax.dispatch(ATTR_CONNECTED, False)
        raise RequestError("test", frame_type)

    await ecomax.dispatch(ATTR_CONNECTED, True)
    mock_request.side_effect = _disconnect_and_fail
    ecomax.dispatch_nowait(ATTR_SETUP, True)
    await ecomax.wait_until_done()
    mock_request.assert_awaited_once_with(
        ATTR_REGDATA_SCHEMA, FrameType.REQUEST_REGULATOR_DATA_SCHEMA
    )
    assert ecomax.get_nowait(ATTR_SETUP) is False
    assert ATTR_FRAME_ERRORS not in ecomax.data

    # Disconnected between successful first request and second request.
    async def _succeed_then_disconnect(key: str, frame_type: FrameType) -> None:
        """Store first key and mark device disconnected before next iteration."""
        await ecomax.dispatch(key, [])
        await ecomax.dispatch(ATTR_CONNECTED, False)

    mock_request.reset_mock()
    await ecomax.dispatch(ATTR_CONNECTED, True)
    mock_request.side_effect = _succeed_then_disconnect
    ecomax.dispatch_nowait(ATTR_SETUP, True)
    await ecomax.wait_until_done()
    mock_request.assert_awaited_once_with(
        ATTR_REGDATA_SCHEMA, FrameType.REQUEST_REGULATOR_DATA_SCHEMA
    )
    assert ATTR_REGDATA_SCHEMA in ecomax.data
    assert ecomax.get_nowait(ATTR_SETUP) is False
    assert ATTR_FRAME_ERRORS not in ecomax.data


async def test_ecomax_reconnect_resumes_setup() -> None:
    """Test reconnecting after mid-setup disconnect resumes remaining keys."""
    protocol = AsyncProtocol()
    ecomax = EcoMAX(protocol._write_queue, NetworkInfo())
    await ecomax.dispatch(ATTR_CONNECTED, True)
    await ecomax.dispatch(ATTR_SENSORS, {ATTR_STATE: DeviceState.WORKING})
    await ecomax.dispatch(
        ATTR_PRODUCT,
        ProductInfo(
            type=ProductType.ECOMAX_P,
            id=0,
            uid="TEST",
            logo=0,
            image=0,
            model=DUMMY_MODEL,
        ),
    )
    await protocol.dispatch("ecomax", ecomax)

    protocol.connected.set()
    protocol.writer = AsyncMock()
    protocol._write_queue.put_nowait(AlertsRequest(recipient=DeviceType.ECOMAX))

    calls: list[tuple[str, FrameType]] = []

    async def _request_with_disconnect(key: str, frame_type: FrameType) -> None:
        """Simulate disconnect during second request and succeed on reconnect."""
        calls.append((key, frame_type))
        if len(calls) == 2 and ecomax.get_nowait(ATTR_SETUP) is None:
            await protocol.connection_lost()
            loop = asyncio.get_running_loop()
            future: asyncio.Future[None] = loop.create_future()
            loop.call_soon(future.set_result, None)
            await future
            raise RequestError("disconnected", frame_type)

        await ecomax.dispatch(key, [])

    with (
        patch.object(EcoMAX, "request", side_effect=_request_with_disconnect),
        patch.object(AsyncProtocol, "frame_handler", new_callable=AsyncMock),
    ):
        ecomax.dispatch_nowait(ATTR_SETUP, True)
        await ecomax.wait_until_done()

        assert ecomax.get_nowait(ATTR_SETUP) is False
        assert ecomax.get_nowait(ATTR_CONNECTED) is False
        assert ATTR_FRAME_ERRORS not in ecomax.data
        assert protocol._write_queue.empty()
        assert calls == [
            (ATTR_REGDATA_SCHEMA, FrameType.REQUEST_REGULATOR_DATA_SCHEMA),
            (ATTR_ECOMAX_PARAMETERS, FrameType.REQUEST_ECOMAX_PARAMETERS),
        ]

        calls.clear()
        mock_reader = AsyncMock(spec=asyncio.StreamReader)
        mock_writer = AsyncMock(spec=asyncio.StreamWriter)
        protocol.connection_established(mock_reader, mock_writer)
        await protocol.wait_until_done()
        await ecomax.wait_until_done()

    assert isinstance(protocol._write_queue.get_nowait(), StartMasterRequest)
    assert ecomax.get_nowait(ATTR_CONNECTED) is True
    assert ecomax.get_nowait(ATTR_SETUP) is True
    assert ATTR_FRAME_ERRORS not in ecomax.data
    assert calls == [
        (ATTR_ECOMAX_PARAMETERS, FrameType.REQUEST_ECOMAX_PARAMETERS),
        (
            ATTR_ECOMAX_SERVICE_PARAMETERS,
            FrameType.REQUEST_ECOMAX_SERVICE_PARAMETERS,
        ),
        (ATTR_TOTAL_ALERTS, FrameType.REQUEST_ALERTS),
        (ATTR_SCHEDULES, FrameType.REQUEST_SCHEDULES),
        (ATTR_PASSWORD, FrameType.REQUEST_PASSWORD),
    ]


@patch("asyncio.Queue.put_nowait")
@class_from_json(
    EcomaxParametersResponse,
    "responses/ecomax_parameters.json",
    arguments=("message",),
)
async def test_ecomax_parameters_event_listener(
    mock_put_nowait, ecomax: EcoMAX, ecomax_parameters: EcomaxParametersResponse
) -> None:
    """Test event listener for ecoMAX parameters."""
    ecomax.handle_frame(ecomax_parameters)
    await ecomax.wait_until_done()
    fuzzy_logic = ecomax.get_nowait("fuzzy_logic")
    assert isinstance(fuzzy_logic, EcomaxSwitch)
    assert fuzzy_logic == STATE_ON
    assert fuzzy_logic.value == STATE_ON
    fuzzy_logic_request = await fuzzy_logic.create_request()
    assert isinstance(fuzzy_logic_request, SetEcomaxParameterRequest)
    assert fuzzy_logic_request.data == {
        ATTR_INDEX: 18,
        ATTR_VALUE: 1,
    }

    # Test that parameter instance is not recreated on subsequent calls.
    ecomax.handle_frame(ecomax_parameters)
    await ecomax.wait_until_done()
    assert ecomax.get_nowait("fuzzy_logic") is fuzzy_logic

    # Test parameter with the step (heating_heat_curve)
    fuel_calorific_value = ecomax.get_nowait("fuel_calorific_value")
    assert isinstance(fuel_calorific_value, EcomaxNumber)
    assert equal_parameter_value(fuel_calorific_value.value, 4.6)
    assert equal_parameter_value(fuel_calorific_value.min_value, 0.1)
    assert equal_parameter_value(fuel_calorific_value.max_value, 25.0)

    # Test setting parameter with the step.
    await fuel_calorific_value.set(2.5, timeout=0)
    request = mock_put_nowait.call_args[0][0]
    assert isinstance(request, SetEcomaxParameterRequest)
    assert request.data[ATTR_VALUE] == 25

    # Test parameter with the offset (heating_heat_curve_shift)
    heating_heat_curve_shift = ecomax.get_nowait("heating_curve_shift")
    assert isinstance(heating_heat_curve_shift, EcomaxNumber)
    assert equal_parameter_value(heating_heat_curve_shift.value, 0.0)
    assert equal_parameter_value(heating_heat_curve_shift.min_value, -20.0)
    assert equal_parameter_value(heating_heat_curve_shift.max_value, 20.0)
    assert heating_heat_curve_shift.unit_of_measurement == UnitOfMeasurement.CELSIUS

    # Test setting the parameter with the offset.
    await heating_heat_curve_shift.set(1, timeout=0)
    request = mock_put_nowait.call_args[0][0]
    assert isinstance(request, SetEcomaxParameterRequest)
    assert request.data[ATTR_VALUE] == 21


ECOMAX_860P4 = ProductInfo(
    type=ProductType.ECOMAX_P,
    id=41,
    uid="TEST",
    logo=0,
    image=0,
    model="ecoMAX 860P4-NM TOUCH",
)


@patch("asyncio.Queue.put_nowait")
@json_test_data("responses/ecomax_service_parameters.json", selector="message")
async def test_ecomax_service_parameters_event_listener(
    mock_put_nowait, ecomax: EcoMAX, ecomax_service_parameters_message: bytearray
) -> None:
    """Test event listener for ecoMAX service parameters."""
    await ecomax.dispatch(ATTR_PRODUCT, ECOMAX_860P4)
    ecomax.handle_frame(
        EcomaxServiceParametersResponse(
            message=bytes(ecomax_service_parameters_message)
        )
    )
    await ecomax.wait_until_done()

    # Test that raw parameters are kept.
    raw_parameters = dict(ecomax.get_nowait(ATTR_ECOMAX_SERVICE_PARAMETERS))
    assert len(raw_parameters) == 230

    # Test that only described parameters are dispatched.
    descriptions = await get_service_parameter_types(ECOMAX_860P4)
    for index, description in descriptions.items():
        parameter = ecomax.get_nowait(description.name)
        assert isinstance(parameter, (EcomaxServiceNumber, EcomaxServiceSwitch))
        assert parameter.values == raw_parameters[index]

    # Test parameter with step and offset.
    fan_speed_100 = ecomax.get_nowait("fan_speed_100")
    assert isinstance(fan_speed_100, EcomaxServiceNumber)
    assert equal_parameter_value(fan_speed_100.value, 1700)
    assert equal_parameter_value(fan_speed_100.min_value, 1360)
    assert equal_parameter_value(fan_speed_100.max_value, 2850)
    assert fan_speed_100.unit_of_measurement == UnitOfMeasurement.REVOLUTIONS_PER_MINUTE

    # Test switch parameter.
    heat_exchanger = ecomax.get_nowait("heat_exchanger")
    assert isinstance(heat_exchanger, EcomaxServiceSwitch)
    assert heat_exchanger.value == STATE_ON

    # Test that parameter instance is not recreated on subsequent calls.
    ecomax.handle_frame(
        EcomaxServiceParametersResponse(
            message=bytes(ecomax_service_parameters_message)
        )
    )
    await ecomax.wait_until_done()
    assert ecomax.get_nowait("fan_speed_100") is fan_speed_100


MOCK_SERVICE_PARAMETER_TYPES: Final = {
    40: EcomaxNumberDescription(
        name="fuel_calorific_value",
        step=0.1,
        unit_of_measurement=UnitOfMeasurement.KILO_WATT_HOUR_PER_KILOGRAM,
    ),
    100: EcomaxSwitchDescription(name="weather_control"),
}


@class_from_json(
    EcomaxParametersResponse,
    "responses/ecomax_parameters.json",
    arguments=("message",),
)
@class_from_json(
    EcomaxServiceParametersResponse,
    "responses/ecomax_service_parameters.json",
    arguments=("message",),
)
async def test_ecomax_parameters_do_not_overwrite_service_parameters(
    ecomax: EcoMAX,
    ecomax_parameters: EcomaxParametersResponse,
    ecomax_service_parameters: EcomaxServiceParametersResponse,
) -> None:
    """Test that ecoMAX parameters do not overwrite active service parameters."""
    with (
        patch("pyplumio.helpers.async_cache.async_cache", AsyncCache()),
        patch(
            "pyplumio.parameters.ecomax.get_custom_service_parameter_types",
            new=AsyncMock(return_value=MOCK_SERVICE_PARAMETER_TYPES),
        ),
    ):
        ecomax.handle_frame(ecomax_service_parameters)
        await ecomax.wait_until_done()

        service_number = ecomax.get_nowait("fuel_calorific_value")
        assert isinstance(service_number, EcomaxServiceNumber)
        assert equal_parameter_value(service_number.value, 2.0)

        service_switch = ecomax.get_nowait("weather_control")
        assert isinstance(service_switch, EcomaxServiceSwitch)
        assert service_switch.value == STATE_ON

        number_callback = AsyncMock(return_value=None)
        switch_callback = AsyncMock(return_value=None)
        ecomax.subscribe("fuel_calorific_value", number_callback)
        ecomax.subscribe("weather_control", switch_callback)

        ecomax.handle_frame(ecomax_parameters)
        await ecomax.wait_until_done()

    assert ecomax.get_nowait("fuel_calorific_value") is service_number
    assert equal_parameter_value(service_number.value, 2.0)
    assert ecomax.get_nowait("weather_control") is service_switch
    assert service_switch.value == STATE_ON
    number_callback.assert_not_awaited()
    switch_callback.assert_not_awaited()

    fuzzy_logic = ecomax.get_nowait("fuzzy_logic")
    assert isinstance(fuzzy_logic, EcomaxSwitch)
    assert not isinstance(fuzzy_logic, EcomaxServiceSwitch)


@class_from_json(
    EcomaxParametersResponse,
    "responses/ecomax_parameters.json",
    arguments=("message",),
)
@class_from_json(
    EcomaxServiceParametersResponse,
    "responses/ecomax_service_parameters.json",
    arguments=("message",),
)
async def test_ecomax_parameters_upgrade_to_service_parameters(
    ecomax: EcoMAX,
    ecomax_parameters: EcomaxParametersResponse,
    ecomax_service_parameters: EcomaxServiceParametersResponse,
) -> None:
    """Test that base ecoMAX parameters upgrade to service parameters."""
    with (
        patch("pyplumio.helpers.async_cache.async_cache", AsyncCache()),
        patch(
            "pyplumio.parameters.ecomax.get_custom_service_parameter_types",
            new=AsyncMock(return_value=MOCK_SERVICE_PARAMETER_TYPES),
        ),
    ):
        ecomax.handle_frame(ecomax_parameters)
        await ecomax.wait_until_done()

        base_number = ecomax.get_nowait("fuel_calorific_value")
        assert type(base_number) is EcomaxNumber
        assert equal_parameter_value(base_number.value, 4.6)

        base_switch = ecomax.get_nowait("weather_control")
        assert type(base_switch) is EcomaxSwitch
        assert base_switch.value == STATE_OFF

        ecomax.handle_frame(ecomax_service_parameters)
        await ecomax.wait_until_done()

        service_number = ecomax.get_nowait("fuel_calorific_value")
        assert isinstance(service_number, EcomaxServiceNumber)
        assert equal_parameter_value(service_number.value, 2.0)

        service_switch = ecomax.get_nowait("weather_control")
        assert isinstance(service_switch, EcomaxServiceSwitch)
        assert service_switch.value == STATE_ON

        ecomax.handle_frame(ecomax_parameters)
        await ecomax.wait_until_done()

    assert ecomax.get_nowait("fuel_calorific_value") is service_number
    assert equal_parameter_value(ecomax.get_nowait("fuel_calorific_value").value, 2.0)
    assert ecomax.get_nowait("weather_control") is service_switch
    assert ecomax.get_nowait("weather_control").value == STATE_ON


@pytest.mark.parametrize(
    "service_first", [True, False], ids=["service_first", "base_first"]
)
@class_from_json(
    EcomaxParametersResponse,
    "responses/ecomax_parameters.json",
    arguments=("message",),
)
@class_from_json(
    EcomaxServiceParametersResponse,
    "responses/ecomax_service_parameters.json",
    arguments=("message",),
)
async def test_ecomax_parameters_concurrent_burst_precedence(
    ecomax: EcoMAX,
    ecomax_parameters: EcomaxParametersResponse,
    ecomax_service_parameters: EcomaxServiceParametersResponse,
    service_first: bool,
) -> None:
    """Test service parameter precedence under concurrent same-burst arrivals."""
    number_events: list[Any] = []
    switch_events: list[Any] = []

    def _make_recorder(events: list[Any]) -> EventCallback:
        """Create an async subscriber that yields before recording the event."""

        async def _record(value: Any) -> None:
            """Yield to the event loop and record the dispatched value."""
            loop = asyncio.get_running_loop()
            future: asyncio.Future[None] = loop.create_future()
            loop.call_soon(future.set_result, None)
            await future
            events.append(value)

        return _record

    ecomax.subscribe("fuel_calorific_value", _make_recorder(number_events))
    ecomax.subscribe("weather_control", _make_recorder(switch_events))

    with (
        patch("pyplumio.helpers.async_cache.async_cache", AsyncCache()),
        patch(
            "pyplumio.parameters.ecomax.get_custom_service_parameter_types",
            new=AsyncMock(return_value=MOCK_SERVICE_PARAMETER_TYPES),
        ),
    ):
        if service_first:
            ecomax.handle_frame(ecomax_service_parameters)
            ecomax.handle_frame(ecomax_parameters)
        else:
            ecomax.handle_frame(ecomax_parameters)
            ecomax.handle_frame(ecomax_service_parameters)

        await ecomax.wait_until_done()

    service_number = ecomax.get_nowait("fuel_calorific_value")
    assert isinstance(service_number, EcomaxServiceNumber)
    assert equal_parameter_value(service_number.value, 2.0)

    service_switch = ecomax.get_nowait("weather_control")
    assert isinstance(service_switch, EcomaxServiceSwitch)
    assert service_switch.value == STATE_ON

    fuzzy_logic = ecomax.get_nowait("fuzzy_logic")
    assert isinstance(fuzzy_logic, EcomaxSwitch)
    assert not isinstance(fuzzy_logic, EcomaxServiceSwitch)

    if service_first:
        assert number_events == [service_number]
        assert switch_events == [service_switch]
    else:
        assert len(number_events) == 2
        assert type(number_events[0]) is EcomaxNumber
        assert number_events[1] is service_number
        assert len(switch_events) == 2
        assert type(switch_events[0]) is EcomaxSwitch
        assert switch_events[1] is service_switch


@pytest.mark.parametrize(
    "service_first", [True, False], ids=["service_first", "base_first"]
)
@class_from_json(
    EcomaxParametersResponse,
    "responses/ecomax_parameters.json",
    arguments=("message",),
)
@class_from_json(
    EcomaxServiceParametersResponse,
    "responses/ecomax_service_parameters.json",
    arguments=("message",),
)
async def test_ecomax_parameters_concurrent_burst_before_product_info(
    ecomax_parameters: EcomaxParametersResponse,
    ecomax_service_parameters: EcomaxServiceParametersResponse,
    service_first: bool,
) -> None:
    """Test burst precedence with cold cache and delayed product info."""
    fresh_ecomax = EcoMAX(asyncio.Queue(), network_info=NetworkInfo())
    product_info = ProductInfo(
        type=ProductType.ECOMAX_P,
        id=0,
        uid="*TEST*",
        logo=0,
        image=0,
        model=DUMMY_MODEL,
    )
    with (
        patch("pyplumio.helpers.async_cache.async_cache", AsyncCache()),
        patch(
            "pyplumio.parameters.ecomax.get_custom_service_parameter_types",
            new=AsyncMock(return_value=MOCK_SERVICE_PARAMETER_TYPES),
        ),
    ):
        if service_first:
            fresh_ecomax.handle_frame(ecomax_service_parameters)
            fresh_ecomax.handle_frame(ecomax_parameters)
        else:
            fresh_ecomax.handle_frame(ecomax_parameters)
            fresh_ecomax.handle_frame(ecomax_service_parameters)

        loop = asyncio.get_running_loop()
        future: asyncio.Future[None] = loop.create_future()
        loop.call_soon(future.set_result, None)
        await future

        await fresh_ecomax.dispatch(ATTR_PRODUCT, product_info)
        await fresh_ecomax.wait_until_done()

    service_number = fresh_ecomax.get_nowait("fuel_calorific_value")
    assert isinstance(service_number, EcomaxServiceNumber)
    assert equal_parameter_value(service_number.value, 2.0)

    service_switch = fresh_ecomax.get_nowait("weather_control")
    assert isinstance(service_switch, EcomaxServiceSwitch)
    assert service_switch.value == STATE_ON

    fuzzy_logic = fresh_ecomax.get_nowait("fuzzy_logic")
    assert isinstance(fuzzy_logic, EcomaxSwitch)
    assert not isinstance(fuzzy_logic, EcomaxServiceSwitch)


@patch("asyncio.Queue.put_nowait")
@json_test_data("responses/ecomax_service_parameters.json", selector="message")
async def test_set_ecomax_service_parameter(
    mock_put_nowait, ecomax: EcoMAX, ecomax_service_parameters_message: bytearray
) -> None:
    """Test that set is confirmed by the updated parameter table."""
    await ecomax.dispatch(ATTR_PRODUCT, ECOMAX_860P4)
    ecomax.handle_frame(
        EcomaxServiceParametersResponse(
            message=bytes(ecomax_service_parameters_message)
        )
    )
    await ecomax.wait_until_done()
    fuzzy_logic_a = ecomax.get_nowait("fuzzy_logic_a")
    assert fuzzy_logic_a.value == 5

    # Set the parameter, as captured from the panel.
    task = asyncio.create_task(ecomax.set("fuzzy_logic_a", 6))
    await asyncio.wait_for(fuzzy_logic_a.update_pending.wait(), timeout=1)
    request = mock_put_nowait.call_args[0][0]
    assert isinstance(request, SetEcomaxServiceParameterRequest)
    assert request.message == bytes.fromhex("010806")

    # Controller sends the updated parameter table.
    message = bytearray(ecomax_service_parameters_message)
    message[2 + 3 * 8] = 6
    ecomax.handle_frame(EcomaxServiceParametersResponse(message=bytes(message)))
    await ecomax.wait_until_done()
    assert await task is True
    assert fuzzy_logic_a.value == 6


@json_test_data("responses/ecomax_service_parameters.json", selector="message")
async def test_ecomax_service_parameters_unknown_product(
    ecomax: EcoMAX, caplog, ecomax_service_parameters_message: bytearray
) -> None:
    """Test ecoMAX service parameters for product without descriptions."""
    with caplog.at_level(logging.DEBUG):
        ecomax.handle_frame(
            EcomaxServiceParametersResponse(
                message=bytes(ecomax_service_parameters_message)
            )
        )
        await ecomax.wait_until_done()

    assert len(ecomax.get_nowait(ATTR_ECOMAX_SERVICE_PARAMETERS)) == 230
    assert "control_mode" not in ecomax.data
    assert "Encountered unknown ecoMAX service parameter table" in caplog.text


@class_from_json(
    EcomaxParametersResponse,
    "unknown/unknown_ecomax_parameter.json",
    arguments=("message",),
)
async def test_unknown_ecomax_parameter(
    ecomax: EcoMAX, caplog, unknown_ecomax_parameter: EcomaxParametersResponse
) -> None:
    """Test unknown ecoMAX parameter."""
    with caplog.at_level(logging.WARNING):
        ecomax.handle_frame(unknown_ecomax_parameter)
        await ecomax.wait_until_done()

    assert "unknown ecoMAX parameter (139)" in caplog.text
    assert "ParameterValues(value=1, min_value=1, max_value=1)" in caplog.text
    assert DUMMY_MODEL in caplog.text


@class_from_json(SensorDataMessage, "messages/sensor_data.json", arguments=("message",))
async def test_name_collisions(ecomax: EcoMAX, sensor_data: SensorDataMessage) -> None:
    """Test that the sensor names don't collide with the parameters."""
    ecomax.handle_frame(sensor_data)
    await ecomax.wait_until_done()
    for descriptions in PARAMETER_TYPES.values():
        collisions = [
            description.name
            for description in descriptions
            if description.name in ecomax.data
        ]
        assert not collisions, f"found collisions: {collisions}"

    legacy_names = {
        description.name
        for descriptions in PARAMETER_TYPES.values()
        for description in descriptions
    }
    service_descriptions = await get_service_parameter_types(ECOMAX_860P4)
    collisions = [
        description.name
        for description in service_descriptions.values()
        if description.name in ecomax.data or description.name in legacy_names
    ]
    assert not collisions, f"found collisions: {collisions}"


async def test_fuel_consumption_event_listener(
    frozen_time, caplog, ecomax: EcoMAX
) -> None:
    """Test event listener for fuel consumption."""
    # First frame establishes baseline; no fuel burned is dispatched.
    ecomax.handle_frame(Response(data={ATTR_FUEL_CONSUMPTION: 3.6}))
    await ecomax.wait_until_done()
    assert ecomax.get_nowait(ATTR_FUEL_BURNED) is None

    # Second frame calculates fuel burned with trapezoidal rule:
    # (3.6 + 3.6) / 2 * (10 / 3600) = 0.01 kg.
    frozen_time.tick(timedelta(seconds=10))
    ecomax.handle_frame(Response(data={ATTR_FUEL_CONSUMPTION: 3.6}))
    await ecomax.wait_until_done()
    fuel_burned = cast(float, ecomax.get_nowait(ATTR_FUEL_BURNED))
    assert equal_parameter_value(fuel_burned, 0.01)

    # Test with outdated data (interval >= MAX_TIME_SINCE_LAST_FUEL_UPDATE).
    message = "Skipping outdated fuel consumption"
    frozen_time.tick(timedelta(seconds=16))
    ecomax.handle_frame(Response(data={ATTR_FUEL_CONSUMPTION: 1}))
    await ecomax.wait_until_done()
    fuel_burned = cast(float, ecomax.get_nowait(ATTR_FUEL_BURNED))
    assert equal_parameter_value(fuel_burned, 0.01)
    assert message in caplog.text
    caplog.clear()

    # Resumed frame after outdated data uses the outdated rate as baseline:
    # (1.0 + 7.2) / 2 * (10 / 3600) = 0.011388... kg.
    frozen_time.tick(timedelta(seconds=10))
    ecomax.handle_frame(Response(data={ATTR_FUEL_CONSUMPTION: 7.2}))
    await ecomax.wait_until_done()
    assert message not in caplog.text
    fuel_burned = cast(float, ecomax.get_nowait(ATTR_FUEL_BURNED))
    assert equal_parameter_value(fuel_burned, (1.0 + 7.2) / 2 * (10 / 3600))

    # Test resetting the fuel meter.
    ecomax.reset_fuel_meter()
    frozen_time.tick(timedelta(seconds=10))
    ecomax.handle_frame(Response(data={ATTR_FUEL_CONSUMPTION: 3.6}))
    await ecomax.wait_until_done()
    # Baseline re-established, previous fuel burned value retained.
    assert equal_parameter_value(
        cast(float, ecomax.get_nowait(ATTR_FUEL_BURNED)), (1.0 + 7.2) / 2 * (10 / 3600)
    )

    frozen_time.tick(timedelta(seconds=10))
    ecomax.handle_frame(Response(data={ATTR_FUEL_CONSUMPTION: 3.6}))
    await ecomax.wait_until_done()
    fuel_burned = cast(float, ecomax.get_nowait(ATTR_FUEL_BURNED))
    assert equal_parameter_value(fuel_burned, 0.01)


@class_from_json(
    MixerParametersResponse,
    "responses/mixer_parameters.json",
    arguments=("message",),
)
async def test_mixer_parameters_event_listener(
    ecomax: EcoMAX, mixer_parameters: MixerParametersResponse
) -> None:
    """Test event listener for mixer parameters."""
    ecomax.handle_frame(mixer_parameters)
    await ecomax.wait_until_done()
    mixers = cast(dict[int, Mixer], ecomax.get_nowait(ATTR_MIXERS))
    assert isinstance(mixers, dict)
    assert len(mixers) == 1
    assert all(isinstance(mixer, Mixer) for mixer in mixers.values())


async def test_mixer_parameters_event_listener_without_mixers(ecomax: EcoMAX) -> None:
    """Test event listener for mixer parameters without mixers."""
    ecomax.handle_frame(MixerParametersResponse(data={ATTR_MIXER_PARAMETERS: {}}))
    await ecomax.wait_until_done()
    assert not ecomax.get_nowait(ATTR_MIXER_PARAMETERS, UNDEFINED)


@class_from_json(SensorDataMessage, "messages/sensor_data.json", arguments=("message",))
async def test_mixer_sensors_event_listener(
    ecomax: EcoMAX, sensor_data: SensorDataMessage
) -> None:
    """Test event listener for mixer sensors."""
    ecomax.handle_frame(sensor_data)
    await ecomax.wait_until_done()
    mixers = cast(dict[int, Mixer], ecomax.get_nowait(ATTR_MIXERS))
    assert isinstance(mixers, dict)
    assert len(mixers) == 1
    assert all(isinstance(mixer, Mixer) for mixer in mixers.values())
    assert ecomax.get_nowait(ATTR_MIXERS_AVAILABLE) == 5
    assert ecomax.get_nowait(ATTR_MIXERS_CONNECTED) == 1


async def test_mixer_sensors_callbacks_without_mixers(ecomax: EcoMAX) -> None:
    """Test event listener for mixer sensors without mixers."""
    ecomax.handle_frame(MixerParametersResponse(data={ATTR_MIXER_SENSORS: {}}))
    await ecomax.wait_until_done()
    assert ecomax.get_nowait(ATTR_MIXER_SENSORS, UNDEFINED) is False


@class_from_json(SensorDataMessage, "messages/sensor_data.json", arguments=("message",))
async def test_ecomax_sensors_event_listener(
    ecomax: EcoMAX, sensor_data: SensorDataMessage
) -> None:
    """Test event listener for ecoMAX sensors."""
    ecomax.handle_frame(sensor_data)
    await ecomax.wait_until_done()
    heating_target = cast(float, ecomax.get_nowait("heating_target"))
    assert equal_parameter_value(heating_target, 41.0)

    ecomax_control = ecomax.get_nowait(ATTR_ECOMAX_CONTROL)
    assert isinstance(ecomax_control, EcomaxSwitch)
    assert ecomax_control.value == STATE_OFF

    ecomax_control_request = await ecomax_control.create_request()
    assert isinstance(ecomax_control_request, EcomaxControlRequest)
    assert ecomax_control_request.data == {ATTR_VALUE: 0}

    # Check ecomax_control reference equility.
    sensor_data_message2 = SensorDataMessage(data={ATTR_STATE: DeviceState.WORKING})
    ecomax.handle_frame(sensor_data_message2)
    await ecomax.wait_until_done()
    ecomax_control2 = ecomax.get_nowait(ATTR_ECOMAX_CONTROL)
    assert isinstance(ecomax_control2, EcomaxSwitch)
    assert ecomax_control2 is ecomax_control
    assert ecomax_control2.value == STATE_ON
    ecomax_control2_request = await ecomax_control.create_request()
    assert ecomax_control2_request.data == {ATTR_VALUE: 1}


@class_from_json(
    ThermostatParametersResponse,
    "responses/thermostat_parameters.json",
    arguments=("message",),
)
async def test_thermostat_parameters_event_listener(
    ecomax: EcoMAX, thermostat_parameters: ThermostatParametersResponse
) -> None:
    """Test event listener for thermostat parameters."""
    await ecomax.dispatch(ATTR_THERMOSTATS_AVAILABLE, 3)
    ecomax.handle_frame(thermostat_parameters)
    await ecomax.wait_until_done()
    thermostats = cast(dict[int, Thermostat], ecomax.get_nowait(ATTR_THERMOSTATS))
    assert isinstance(thermostats, dict)
    assert len(thermostats) == 1
    assert all(
        isinstance(thermostat, Thermostat) for thermostat in thermostats.values()
    )


@class_from_json(
    ThermostatParametersResponse,
    "responses/thermostat_parameters.json",
    arguments=("message",),
)
async def test_thermostat_parameters_event_listener_without_thermostats(
    ecomax: EcoMAX, thermostat_parameters: ThermostatParametersResponse
) -> None:
    """Test event listener for thermostat parameters without any thermostats."""
    await ecomax.dispatch(ATTR_THERMOSTATS_AVAILABLE, 0)
    ecomax.handle_frame(thermostat_parameters)
    await ecomax.wait_until_done()
    assert ecomax.get_nowait(ATTR_THERMOSTAT_PARAMETERS, UNDEFINED) is False


@class_from_json(
    ThermostatParametersResponse,
    "responses/thermostat_parameters.json",
    arguments=("message",),
)
async def test_thermostat_profile_event_listener(
    ecomax: EcoMAX, thermostat_parameters: ThermostatParametersResponse
) -> None:
    """Test event listener for thermostat profile."""
    await ecomax.dispatch(ATTR_THERMOSTATS_AVAILABLE, 3)
    ecomax.handle_frame(thermostat_parameters)
    await ecomax.wait_until_done()
    thermostat_profile = ecomax.get_nowait(ATTR_THERMOSTAT_PROFILE)
    assert isinstance(thermostat_profile, EcomaxNumber)
    assert equal_parameter_value(thermostat_profile.value, 0.0)
    assert equal_parameter_value(thermostat_profile.min_value, 0.0)
    assert equal_parameter_value(thermostat_profile.max_value, 5.0)
    thermostat_profile_request = await thermostat_profile.create_request()
    assert isinstance(thermostat_profile_request, SetThermostatParameterRequest)
    assert thermostat_profile_request.data == {
        ATTR_INDEX: 0,
        ATTR_VALUE: 0,
        ATTR_OFFSET: 0,
        ATTR_SIZE: 1,
    }

    # Test when thermostat profile is none.
    ecomax.handle_frame(Response(data={ATTR_THERMOSTAT_PROFILE: None}))
    await ecomax.wait_until_done()
    assert ecomax.get_nowait(ATTR_THERMOSTAT_PROFILE, UNDEFINED) is None


@class_from_json(SensorDataMessage, "messages/sensor_data.json", arguments=("message",))
async def test_thermostat_sensors_event_listener(
    ecomax: EcoMAX, sensor_data: SensorDataMessage
) -> None:
    """Test event listener for thermostat sensors."""
    ecomax.handle_frame(sensor_data)
    await ecomax.wait_until_done()
    thermostats = cast(dict[int, Thermostat], ecomax.get_nowait(ATTR_THERMOSTATS))
    assert isinstance(thermostats, dict)
    assert len(thermostats) == 1
    assert all(
        isinstance(thermostat, Thermostat) for thermostat in thermostats.values()
    )
    assert ecomax.get_nowait(ATTR_THERMOSTATS_AVAILABLE) == 2
    assert ecomax.get_nowait(ATTR_THERMOSTATS_CONNECTED) == 1


async def test_thermostat_sensors_event_listener_without_thermostats(
    ecomax: EcoMAX,
) -> None:
    """Test event lister for thermostat sensors without thermostats."""
    ecomax.handle_frame(
        ThermostatParametersResponse(data={ATTR_THERMOSTAT_SENSORS: {}})
    )
    await ecomax.wait_until_done()
    assert ecomax.get_nowait(ATTR_THERMOSTAT_SENSORS, UNDEFINED) is False


@class_from_json(SchedulesResponse, "responses/schedules.json", arguments=("message",))
@json_test_data("responses/schedules.json", selector="data")
async def test_ecomax_schedules_event_listener(
    ecomax: EcoMAX, schedules: SchedulesResponse, schedules_data
) -> None:
    """Test event listener for schedules."""
    ecomax.handle_frame(schedules)
    await ecomax.wait_until_done()
    schedules_arg = cast(dict[str, Schedule], ecomax.get_nowait(ATTR_SCHEDULES))
    assert isinstance(schedules_arg, dict)
    assert len(schedules_arg) == 2
    heating_schedule = schedules_arg["heating"]
    assert isinstance(heating_schedule, Schedule)

    heating_schedule_switch = ecomax.get_nowait("heating_schedule_switch")
    assert isinstance(heating_schedule_switch, ScheduleSwitch)
    assert heating_schedule_switch.value == STATE_OFF

    water_heater_schedule_parameter = ecomax.get_nowait(
        "water_heater_schedule_parameter"
    )
    assert isinstance(water_heater_schedule_parameter, ScheduleNumber)
    assert water_heater_schedule_parameter.value == 5
    assert water_heater_schedule_parameter.min_value == 0
    assert water_heater_schedule_parameter.max_value == 30
    water_heater_schedule_parameter_request = (
        await water_heater_schedule_parameter.create_request()
    )
    assert isinstance(water_heater_schedule_parameter_request, SetScheduleRequest)
    assert water_heater_schedule_parameter_request.data == {
        ATTR_TYPE: "water_heater",
        ATTR_SWITCH: ecomax.data[f"water_heater_{ATTR_SCHEDULE_SWITCH}"],
        ATTR_PARAMETER: ecomax.data[f"water_heater_{ATTR_SCHEDULE_PARAMETER}"],
        ATTR_SCHEDULE: ecomax.data[ATTR_SCHEDULES]["water_heater"],
    }

    schedule_data = schedules_data[ATTR_SCHEDULES][0][1]
    for index, weekday in enumerate(
        (
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        )
    ):
        schedule = getattr(heating_schedule, weekday)
        assert (
            schedule.schedule
            == ScheduleDay.from_iterable(schedule_data[index]).schedule
        )

    # Test that parameter instance is not recreated on subsequent calls.
    ecomax.handle_frame(schedules)
    await ecomax.wait_until_done()
    assert ecomax.get_nowait("heating_schedule_switch") is heating_schedule_switch
