"""Tests for entity descriptions."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock

from custom_components.homeconnect_ws import entity_descriptions
from custom_components.homeconnect_ws.entity_descriptions import (
    HCBinarySensorEntityDescription,
    HCSelectEntityDescription,
    HCSensorEntityDescription,
    HCSwitchEntityDescription,
)
from custom_components.homeconnect_ws.entity_descriptions.common import (
    generate_power_switch,
    generate_program,
)
from custom_components.homeconnect_ws.helpers import merge_dicts
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.switch import SwitchDeviceClass
from homeconnect_websocket.entities import Access, DeviceDescription, EntityDescription

if TYPE_CHECKING:
    import pytest
    from homeconnect_websocket.testutils import MockAppliance, MockApplianceType


def test_merge_dicts() -> None:
    """Test merge dicts."""
    dict1 = {"a": [1, 2], "b": [3, 4]}
    dict2 = {"b": [5, 6], "c": [7, 8]}
    out_dict = merge_dicts(dict1, dict2)
    assert out_dict == {"a": [1, 2], "b": [3, 4, 5, 6], "c": [7, 8]}


MOCK_ENTITY_DESCRIPTIONS = {
    "binary_sensor": [
        HCBinarySensorEntityDescription(key="binary_sensor_available", entity="Test.BinarySensor"),
        HCBinarySensorEntityDescription(
            key="binary_sensor_not_available", entity="Test.BinarySensor2"
        ),
    ],
    "event_sensor": [
        HCSensorEntityDescription(
            key="sensor_event_available",
            entities=[
                "Test.Event1",
                "Test.Event2",
            ],
        ),
        HCSensorEntityDescription(
            key="sensor_event_not_available",
            entities=[
                "Test.Event1",
                "Test.Event3",
            ],
        ),
    ],
}


def test_get_available_entities(
    mock_appliance: MockAppliance, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test get_available_entities."""
    monkeypatch.setattr(
        entity_descriptions,
        "get_all_entity_description",
        Mock(return_value=MOCK_ENTITY_DESCRIPTIONS),
    )
    entities = entity_descriptions.get_available_entities(mock_appliance)
    assert entities["binary_sensor"] == [
        HCBinarySensorEntityDescription(key="binary_sensor_available", entity="Test.BinarySensor")
    ]
    assert entities["event_sensor"] == [
        HCSensorEntityDescription(
            key="sensor_event_available",
            entities=[
                "Test.Event1",
                "Test.Event2",
            ],
        )
    ]


POWER_SWITCH = {
    "setting": [
        {
            "access": "readwrite",
            "available": True,
            "enumeration": {"0": "MainsOff", "1": "Off", "2": "On", "3": "Standby"},
            "min": 0,
            "max": 2,
            "uid": 539,
            "name": "BSH.Common.Setting.PowerState",
        },
    ]
}


async def test_power_switch(mock_homeconnect_appliance: MockApplianceType) -> None:
    """Test dynamic Power switch."""
    device_description = POWER_SWITCH.copy()

    # On/Off Switch
    device_description["setting"][0]["min"] = 1
    device_description["setting"][0]["max"] = 2
    appliance = await mock_homeconnect_appliance(description=device_description)
    switch_description = generate_power_switch(appliance)

    assert switch_description["switch"][0] == HCSwitchEntityDescription(
        key="switch_power_state",
        entity="BSH.Common.Setting.PowerState",
        device_class=SwitchDeviceClass.SWITCH,
        value_mapping=("On", "Off"),
    )

    # No Switch
    device_description["setting"][0]["min"] = 0
    device_description["setting"][0]["max"] = 4
    appliance = await mock_homeconnect_appliance(description=device_description)
    switch_description = generate_power_switch(appliance)

    assert "switch" not in switch_description

    # On/MainsOff Switch
    device_description["setting"][0]["enumeration"] = {"0": "MainsOff", "2": "On"}
    appliance = await mock_homeconnect_appliance(description=device_description)
    switch_description = generate_power_switch(appliance)

    assert switch_description["switch"][0] == HCSwitchEntityDescription(
        key="switch_power_state",
        entity="BSH.Common.Setting.PowerState",
        device_class=SwitchDeviceClass.SWITCH,
        value_mapping=("On", "MainsOff"),
    )

    # Standby/Off Switch
    device_description["setting"][0]["enumeration"] = {"1": "Off", "3": "Standby"}
    appliance = await mock_homeconnect_appliance(description=device_description)
    switch_description = generate_power_switch(appliance)

    assert switch_description["switch"][0] == HCSwitchEntityDescription(
        key="switch_power_state",
        entity="BSH.Common.Setting.PowerState",
        device_class=SwitchDeviceClass.SWITCH,
        value_mapping=("Standby", "Off"),
    )


PROGRAM = DeviceDescription(
    setting=[
        EntityDescription(
            uid=101,
            name="BSH.Common.Setting.Favorite.001.Name",
            access=Access.READ_WRITE,
            available=True,
            max=30,
            min=0,
            default="Named Favorite",
        ),
        EntityDescription(
            uid=102,
            name="BSH.Common.Setting.Favorite.002.Name",
            access=Access.READ_WRITE,
            available=True,
            max=30,
            min=0,
            default="",
        ),
    ],
    program=[
        EntityDescription(
            uid=201,
            name="BSH.Common.Program.Favorite.001",
            available=True,
        ),
        EntityDescription(
            uid=202,
            name="BSH.Common.Program.Favorite.002",
            available=True,
        ),
        EntityDescription(
            uid=500,
            name="BSH.Common.Program.Program1",
        ),
    ],
)


async def test_program(mock_homeconnect_appliance: MockApplianceType) -> None:
    """Test dynamic Program."""
    appliance = await mock_homeconnect_appliance(description=PROGRAM)
    program_description = generate_program(appliance)
    assert program_description["program"][0] == HCSelectEntityDescription(
        key="select_program",
        entity="BSH.Common.Root.SelectedProgram",
        has_state_translation=False,
        mapping={
            "BSH.Common.Program.Favorite.001": "Named Favorite",
            "BSH.Common.Program.Favorite.002": "favorite_002",
            "BSH.Common.Program.Program1": "BSH.Common.Program.Program1",
        },
    )
    assert program_description["active_program"][0] == HCSensorEntityDescription(
        key="sensor_active_program",
        entity="BSH.Common.Root.ActiveProgram",
        has_state_translation=False,
        device_class=SensorDeviceClass.ENUM,
        mapping={
            "BSH.Common.Program.Favorite.001": "Named Favorite",
            "BSH.Common.Program.Favorite.002": "favorite_002",
            "BSH.Common.Program.Program1": "BSH.Common.Program.Program1",
        },
    )

    appliance = await mock_homeconnect_appliance(description={})
