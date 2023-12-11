import unittest
from unittest.mock import MagicMock
from channel_app.core.commands import OmnitronCommandInterface


class BaseTestCaseMixin(unittest.TestCase):
    mock_integration = MagicMock()
    omnitron_command_interface = OmnitronCommandInterface(
        integration=mock_integration
    )
    
    def setUp(self) -> None:
        return super().setUp()
    
    def tearDown(self) -> None:
        return super().tearDown()
