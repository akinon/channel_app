from redis import Redis
from omnisdk.omnitron.client import OmnitronApiClient as BaseOmnitronApiClient
v

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
        return self.redis_client.get(self.redis_prefix)

    def set_token(self, token):
        self.redis_client.set(self.redis_prefix, token)