from redis import Redis
from omnisdk.omnitron.client import OmnitronApiClient as BaseOmnitronApiClient


class RedisClient(Redis):
    def __init__(self):
        from channel_app.core import settings
        self.broker_database_index = int(settings.CACHE_DATABASE_INDEX)
        self.broker_port = settings.CACHE_PORT
        self.broker_host = settings.CACHE_HOST
        super(RedisClient, self).__init__(host=self.broker_host,
                                          port=self.broker_port,
                                          db=self.broker_database_index)


class OmnitronApiClient(BaseOmnitronApiClient):
    """
    OmnitronApiClient class for Omnitron API requests.
    """
    client_route = "api/v1/"
    redis_prefix = "omnitron_auth_token_prefix"

    def __init__(self, base_url, username, password):
        self.redis_client = RedisClient()
        super().__init__(base_url, username, password)

    @property
    def token(self):
        token = self.redis_client.get(self.redis_prefix)
        if token:
            token = token.decode("utf-8")
        else:
            # Check redis key for retry count with max 3 attempts in 6 min.
            retry_count = int(self.redis_client.get("retry_count") or 0)
            if retry_count < 3:
                token = self.refresh_key()
                self.redis_client.set("retry_count", retry_count + 1, 360)
            else:
                raise Exception("Login attempts exceeded 3 times in 6 min.")
        return token

    def set_token(self, token):
        self.redis_client.set(self.redis_prefix, token)
