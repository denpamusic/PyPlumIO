"""Test lambda sensor structure decoder."""

import pytest

from pyplumio.const import BYTE_UNDEFINED, LambdaState
from pyplumio.frames.messages import SensorDataMessage
from pyplumio.structures.lambda_sensor import (
    ATTR_LAMBDA_LEVEL,
    ATTR_LAMBDA_STATE,
    ATTR_LAMBDA_TARGET,
    LambdaSensorStructure,
)


@pytest.fixture(name="lambda_sensor_structure")
def fixture_lambda_sensor_structure() -> LambdaSensorStructure:
    """Fixture for LambdaSensorStructure."""
    return LambdaSensorStructure(frame=SensorDataMessage())


class TestLambdaSensorStructure:
    """Test the LambdaSensor structure decoder."""

    def test_decode(self, lambda_sensor_structure: LambdaSensorStructure) -> None:
        """Test decoding of lambda sensor structure."""
        message = bytearray([0x00, 0x01, 0x4B, 0x00])
        data, offset = lambda_sensor_structure.decode(message)
        assert data == {
            ATTR_LAMBDA_STATE: LambdaState.STOP,
            ATTR_LAMBDA_TARGET: 1,
            ATTR_LAMBDA_LEVEL: 7.5,
        }
        assert offset == 4

    def test_decode_without_lambda_sensor(
        self, lambda_sensor_structure: LambdaSensorStructure
    ) -> None:
        """Test decoding of lambda sensor structure without lambda sensor."""
        message = bytearray([BYTE_UNDEFINED])
        data, offset = lambda_sensor_structure.decode(message)
        assert data == {}
        assert offset == 1
