"""Contains tests for the device handler classes."""

from __future__ import annotations

import asyncio
from typing import Literal
from unittest.mock import Mock, patch

import pytest

from pyplumio.const import ATTR_FRAME_ERRORS, DeviceType, FrameType
from pyplumio.devices import Device, PhysicalDevice, device_handler, get_device_handler
from pyplumio.exceptions import RequestError, UnknownDeviceError
from pyplumio.filters import on_change
from pyplumio.frames import Response
from pyplumio.parameters import Parameter
from pyplumio.structures.frame_versions import ATTR_FRAME_VERSIONS
from pyplumio.structures.network_info import NetworkInfo
from tests.conftest import RAISES


@pytest.mark.parametrize(
    ("device_type", "handler"),
    [
        (DeviceType.ECOMAX, "devices.ecomax.EcoMAX"),
        (DeviceType.ECONET, "devices.econet.EcoNET"),
        (DeviceType.ECOSTER, "devices.ecoster.EcoSTER"),
        (99, RAISES),
    ],
)
def test_get_device_handler(
    device_type: DeviceType | int, handler: str | Literal["raises"]
) -> None:
    """Test getting device handler class by device address."""
    if handler == RAISES:
        with pytest.raises(UnknownDeviceError, match="Unknown device type"):
            get_device_handler(device_type)
    else:
        assert get_device_handler(device_type) == handler


class DummyDevice(Device):
    """Represents a dummy device."""


@pytest.fixture(name="device")
def fixture_device() -> Device:
    """Return a Device object."""
    return DummyDevice(asyncio.Queue())


class TestDevice:
    """Contains tests for the Device class."""

    @patch(
        "pyplumio.devices.Device.get", return_value=Mock(spec=Parameter, autospec=True)
    )
    async def test_set(self, mock_get, device: Device) -> None:
        """Test changing a device parameter."""
        await device.set("foo", "on")
        mock_get.assert_awaited_once_with("foo", None)
        parameter = mock_get.return_value
        parameter.set.assert_awaited_once_with("on", retries=0)

    @patch("pyplumio.devices.Device.get", return_value=Mock)
    async def test_set_incorrect_parameter(self, mock_get, device: Device) -> None:
        """Test changing an incorrect device parameter."""
        with pytest.raises(TypeError, match="not valid or does not exist"):
            await device.set("foo", "bar")  # type: ignore[arg-type]

    @patch("pyplumio.devices.Device.create_task")
    @patch("pyplumio.devices.Device.set", new_callable=Mock)
    def test_set_nowait(self, mock_set, mock_create_task, device: Device) -> None:
        """Test changing a device parameter without waiting."""
        device.set_nowait("foo", "off")
        mock_set.assert_called_once_with("foo", "off", 0, None)
        mock_create_task.assert_called_once_with(mock_set.return_value)

    @patch("pyplumio.devices.Device.cancel_tasks")
    @patch("pyplumio.devices.Device.wait_until_done")
    async def test_shutdown(
        self, wait_until_done, cancel_tasks, device: Device
    ) -> None:
        """Test shutting down the device tasks."""
        await device.shutdown()
        cancel_tasks.assert_called_once()
        wait_until_done.assert_awaited_once()


class DummyPhysicalDevice(PhysicalDevice):
    """Represents a dummy physical device."""

    address = 0


@pytest.fixture(name="physical_device")
def fixture_physical_device() -> PhysicalDevice:
    """Return a PhysicalDevice object."""
    return DummyPhysicalDevice(asyncio.Queue(), NetworkInfo())


class TestPhysicalDevice:
    """Contains tests for PhysicalDevice class."""

    @pytest.mark.parametrize(
        ("frame_type", "requested_frame_type"),
        [
            (FrameType.REQUEST_ALERTS, FrameType.REQUEST_ALERTS),
            (
                FrameType.REQUEST_ECOMAX_PARAMETER_CHANGES,
                FrameType.REQUEST_ECOMAX_PARAMETERS,
            ),
        ],
    )
    @patch("pyplumio.frames.Request.create", autospec=True)
    @patch("asyncio.Queue.put_nowait")
    async def test_frame_versions_event_listener(
        self,
        mock_put_nowait,
        mock_request_create,
        physical_device: PhysicalDevice,
        frame_type: FrameType,
        requested_frame_type: FrameType,
    ) -> None:
        """Test event listener for frame versions."""
        assert physical_device.has_frame_version(frame_type, 1) is False
        await physical_device.on_event_frame_versions({frame_type: 1})
        mock_request_create.assert_awaited_once_with(
            requested_frame_type, recipient=DummyPhysicalDevice.address
        )
        mock_put_nowait.assert_called_once_with(mock_request_create.return_value)
        assert physical_device.has_frame_version(frame_type, 1) is True

    def test_frame_versions_event_listener_decorator(self) -> None:
        """Test decorator for the frame version event listener."""
        event = getattr(PhysicalDevice.on_event_frame_versions, "_on_event", None)
        assert event == ATTR_FRAME_VERSIONS
        filter_func = getattr(
            PhysicalDevice.on_event_frame_versions, "_on_event_filter", None
        )
        assert filter_func is on_change

    async def test_supports_frame_type(self, physical_device: PhysicalDevice) -> None:
        """Test frame support checker."""
        assert physical_device.supports_frame_type(FrameType.REQUEST_ALERTS) is True
        await physical_device.dispatch(ATTR_FRAME_ERRORS, [FrameType.REQUEST_ALERTS])
        assert physical_device.supports_frame_type(FrameType.REQUEST_ALERTS) is False

    @patch("pyplumio.frames.Frame.assign_to")
    @patch("pyplumio.devices.PhysicalDevice.dispatch_nowait")
    async def test_handle_frame(
        self, mock_dispatch_nowait, mock_assign_to, physical_device: PhysicalDevice
    ) -> None:
        """Test frame handling."""
        frame = Response(data={"test": True})
        physical_device.handle_frame(frame)
        mock_assign_to.assert_called_once_with(physical_device)
        mock_dispatch_nowait.assert_called_once_with("test", True)

    @patch("pyplumio.devices.PhysicalDevice.get")
    @patch("pyplumio.frames.Request.create", autospec=True)
    @patch("asyncio.Queue.put_nowait")
    async def test_request(
        self,
        mock_put_nowait,
        mock_request_create,
        mock_get,
        physical_device: PhysicalDevice,
    ) -> None:
        """Test making a request."""
        await physical_device.request("alerts", frame_type=FrameType.REQUEST_ALERTS)
        mock_request_create.assert_called_once_with(
            FrameType.REQUEST_ALERTS, recipient=DummyPhysicalDevice.address
        )
        mock_put_nowait.assert_called_once_with(mock_request_create.return_value)
        mock_get.assert_awaited_once_with("alerts", timeout=3.0)

    @patch(
        "pyplumio.devices.PhysicalDevice.get",
        side_effect=(asyncio.TimeoutError, asyncio.TimeoutError),
    )
    @patch("pyplumio.frames.Request.create", autospec=True)
    @patch("asyncio.Queue.put_nowait")
    async def test_request_retry(
        self,
        mock_put_nowait,
        mock_request_create,
        mock_get,
        physical_device: PhysicalDevice,
    ) -> None:
        """Test retrying a request."""
        with pytest.raises(RequestError, match="Failed to request"):
            await physical_device.request(
                "alerts", frame_type=FrameType.REQUEST_ALERTS, retries=2
            )

        mock_request_create.assert_called_once_with(
            FrameType.REQUEST_ALERTS, recipient=DummyPhysicalDevice.address
        )
        mock_put_nowait.assert_called_with(mock_request_create.return_value)
        assert mock_put_nowait.call_count == 2
        mock_get.assert_awaited_with("alerts", timeout=3.0)
        assert mock_get.call_count == 2

    async def test_device_handler(self) -> None:
        """Test device handler decorator."""
        wrapper = device_handler(DeviceType.ECOMAX)
        device = wrapper(PhysicalDevice)(queue=asyncio.Queue(), network=NetworkInfo())
        assert device.address == DeviceType.ECOMAX
