import unittest
from unittest.mock import patch, Mock
from redis import Redis
from channel_app.core.clients import OmnitronApiClient
from omnisdk.exceptions import ValidationError

class TestOmnitronApiClient(unittest.TestCase):
    """
    Test the OmnitronApiClient class.
    
    run: python -m unittest channel_app.core.tests.test_clients.TestOmnitronApiClient
    """
    redis_con = Redis()
    omnitron_auth_url = "https://example.com/api/v1/auth/login/"
    test_token = "Token test_key"

    @patch("channel_app.core.clients.RedisClient")
    @patch('requests.Session')
    def setUp(self, mock_session, mock_redis_client):
        self.redis_con.flushall()
        mock_redis_client.return_value = self.redis_con
        # Create a mock session and set it as the return value of
        # requests.Session()
        self.mock_session = mock_session.return_value
        self.mock_session.post.return_value = Mock(
            status_code=200,
            json=Mock(return_value={"key": "test_key"})
        )
        self.base_url = "https://example.com/"
        self.username = "testuser"
        self.password = "testpassword"
        self.client = OmnitronApiClient(
            self.base_url,
            self.username,
            self.password
        )

    def test_token_property(self):
        # Assert that the session.post() method was called once
        self.mock_session.post.assert_called_once_with(
            self.omnitron_auth_url,
            json={"username": "testuser", "password": "testpassword"}
        )
        # Assert that the self.client.redis_prefix key is set to the token
        self.assertEqual(
            self.redis_con.get(self.client.redis_prefix).decode("utf-8"),
            self.test_token
        )
        # Call token property and assert that the token is returned
        for _ in range(2):
            token = self.client.token
            self.assertEqual(
                token,
                self.test_token
            )

        # Assert that the session.post() method was called only once
        self.mock_session.post.assert_called_once_with(
            self.omnitron_auth_url,
            json={"username": "testuser", "password": "testpassword"}
        )

    def test_refresh_key(self):
        self.redis_con.flushall()
        self.mock_session.reset_mock()
        self.mock_session.post.return_value = Mock(
            status_code=200,
            json=Mock(return_value={"key": "updated_key"})
        )
        self.client.refresh_key()
        # Assert that the session.post() method was called once
        self.mock_session.post.assert_called_once_with(
            self.omnitron_auth_url,
            json={"username": "testuser", "password": "testpassword"}
        )
        # Assert that the self.client.redis_prefix key is set to the token
        self.assertEqual(
            self.redis_con.get(self.client.redis_prefix).decode("utf-8"),
            "Token updated_key"
        )

    def test_refresh_key_with_authentication_error(self):
        self.redis_con.flushall()
        self.mock_session.reset_mock()
        self.mock_session.post.return_value = Mock(
            status_code=400,
            json=Mock(return_value={"error_message": "Authentication failed"})
        )

        with self.assertRaises(ValidationError) as context:
            self.client.refresh_key()

        self.assertIn("Authentication failed", str(context.exception))
        self.mock_session.post.assert_called_once_with(
            self.omnitron_auth_url,
            json={"username": "testuser", "password": "testpassword"}
        )
        # Assert that the self.client.redis_prefix key is not set
        self.assertIsNone(
            self.redis_con.get(self.client.redis_prefix)
        )

    def test_set_token(self):
        # Get token from redis which is set at initialization of the client
        token = self.client.token
        self.assertEqual(
            token,
            self.test_token
        )
        new_token = "Token test_new_key"
        self.client.set_token(new_token)
        self.assertEqual(
            self.client.token,
            new_token
        )
        # Assert that the self.client.redis_prefix key is set to the token
        self.assertEqual(
            self.redis_con.get(self.client.redis_prefix).decode("utf-8"),
            new_token
        )


    def test_retry_count_with(self):
        # Get token from redis which is set at initialization of the client
        token = self.client.token
        self.assertEqual(
            token,
            self.test_token
        )
        new_token = "Token test_new_key"
        self.client.set_token(new_token)
        self.assertEqual(
            self.client.token,
            new_token
        )
        # Assert that the self.client.redis_prefix key is set to the token
        self.assertEqual(
            self.redis_con.get(self.client.redis_prefix).decode("utf-8"),
            new_token
        )
        self.assertEqual(
            int(self.redis_con.get("retry_count").decode("utf-8")),
            1
        )

    def test_retry_count(self):
        self.redis_con.flushall()
        for i in range(3):
            token = self.client.token
            self.assertEqual(
                token,
                self.test_token
            )
            self.redis_con.delete(self.client.redis_prefix)
        with self.assertRaises(Exception) as context:
            self.client.token
        self.assertIn(
            "Login attempts exceeded 3 times in 6 min.",
            str(context.exception)
        )
        self.assertEqual(
            int(self.redis_con.get("retry_count").decode("utf-8")),
            i + 1
        )
