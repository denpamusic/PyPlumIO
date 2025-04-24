"""Contains tests for the ecoMAX parameter descriptors."""

from pyplumio.const import ATTR_INDEX, ATTR_OFFSET, ATTR_SIZE, ATTR_VALUE, ProductType
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.frames.requests import (
    EcomaxControlRequest,
    SetEcomaxParameterRequest,
    SetThermostatParameterRequest,
)
from pyplumio.parameters import ParameterValues
from pyplumio.parameters.ecomax import (
    PARAMETER_TYPES as ECOMAX_PARAMETER_TYPES,
    EcomaxNumber,
    EcomaxNumberDescription,
    EcomaxSwitch,
    EcomaxSwitchDescription,
    get_ecomax_parameter_types,
)
from pyplumio.structures.ecomax_parameters import ATTR_ECOMAX_CONTROL
from pyplumio.structures.product_info import ProductInfo
from pyplumio.structures.thermostat_parameters import ATTR_THERMOSTAT_PROFILE


async def test_ecomax_parameter_create_request(ecomax: EcoMAX) -> None:
    """Test create_request method for ecoMAX parameter."""
    # Test with ecoMAX control switch.
    ecomax_control = EcomaxSwitch(
        device=ecomax,
        description=EcomaxSwitchDescription(name=ATTR_ECOMAX_CONTROL),
        values=ParameterValues(value=0, min_value=0, max_value=1),
    )
    ecomax_control_request = await ecomax_control.create_request()
    assert isinstance(ecomax_control_request, EcomaxControlRequest)
    assert ecomax_control_request.data == {ATTR_VALUE: 0}

    # Test with thermostat profile number.
    thermostat_profile = EcomaxNumber(
        device=ecomax,
        description=EcomaxNumberDescription(name=ATTR_THERMOSTAT_PROFILE),
        values=ParameterValues(value=1, min_value=0, max_value=5),
    )
    thermostat_profile_request = await thermostat_profile.create_request()
    assert isinstance(thermostat_profile_request, SetThermostatParameterRequest)
    assert thermostat_profile_request.data == {
        ATTR_INDEX: 0,
        ATTR_VALUE: 1,
        ATTR_OFFSET: 0,
        ATTR_SIZE: 1,
    }

    # Test with generic number.
    ecomax_number = EcomaxNumber(
        device=ecomax,
        description=EcomaxNumberDescription(name="test_number"),
        values=ParameterValues(value=10, min_value=0, max_value=20),
    )
    ecomax_number_request = await ecomax_number.create_request()
    assert isinstance(ecomax_number_request, SetEcomaxParameterRequest)
    assert ecomax_number_request.data == {ATTR_INDEX: 0, ATTR_VALUE: 10}


def test_get_ecomax_parameter_types(ecomax: EcoMAX) -> None:
    """Test ecoMAX parameter types getter."""
    parameter_types_all = ECOMAX_PARAMETER_TYPES
    assert len(parameter_types_all) == 2
    parameter_types = get_ecomax_parameter_types(ecomax.product)
    assert len(parameter_types_all[ProductType.ECOMAX_P]) == 139
    assert len(parameter_types_all[ProductType.ECOMAX_I]) == 43
    assert parameter_types_all[ProductType.ECOMAX_P] == parameter_types

    # Test with patch.
    product_info = ProductInfo(
        type=ProductType.ECOMAX_P,
        id=48,
        uid="**REDACTED**",
        logo=48,
        image=2,
        model="ecoMAX 860D3-HB",
    )
    parameter_types_patched = get_ecomax_parameter_types(product_info)
    assert parameter_types_patched[119] == EcomaxNumberDescription(name="summer_mode")
    assert parameter_types_patched[120] == EcomaxNumberDescription(
        name="summer_mode_enable_temp"
    )
    assert parameter_types_patched[121] == EcomaxNumberDescription(
        name="summer_mode_disable_temp"
    )
