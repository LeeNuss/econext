"""Test configuration for econext integration tests."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from aiohttp import ClientSession

# Add project root to path so econext package can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def fixture_path() -> Path:
    """Return the path to test fixtures."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def all_params_response(fixture_path: Path) -> dict:
    """Load the parameters.json fixture in index-keyed format.

    This represents the format AFTER the API client transforms the gateway response.
    Used by coordinator and entity tests.
    """
    with open(fixture_path / "parameters.json") as f:
        return json.load(f)


@pytest.fixture
def all_params_parsed(all_params_response: dict) -> dict:
    """Return the parsed params dict (index-keyed format)."""
    return all_params_response


@pytest.fixture
def gateway_api_response(all_params_response: dict) -> dict:
    """Create a gateway-format API response from the fixture.

    Gateway returns index-keyed: {"timestamp": "...", "parameters": {"0": {"index": 0, "name": "PS", ...}}}
    """
    parameters = {}
    for index_str, param_data in all_params_response.items():
        parameters[index_str] = {
            "index": int(index_str),
            "name": param_data.get("name", f"param_{index_str}"),
            "value": param_data.get("value"),
            "type": param_data.get("type", 2),
            "unit": param_data.get("unit", 0),
            "writable": param_data.get("writable", False),
            "min": param_data.get("minv"),
            "max": param_data.get("maxv"),
        }
    return {"timestamp": "2026-02-06T12:00:00", "parameters": parameters}


@pytest.fixture
def mock_session() -> MagicMock:
    """Create a mock aiohttp ClientSession."""
    session = MagicMock(spec=ClientSession)
    return session


@pytest.fixture
def mock_response() -> MagicMock:
    """Create a mock aiohttp response."""
    response = MagicMock()
    response.status = 200
    return response
