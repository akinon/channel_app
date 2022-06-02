from redis import Redis


class RedisClient(Redis):
    def __init__(self):
        from channel_app.core import settings
        self.broker_database_index = int(settings.CACHE_DATABASE_INDEX)
        self.broker_port = settings.CACHE_PORT
        self.broker_host = settings.CACHE_HOST
        super(RedisClient, self).__init__(host=self.broker_host,
                                          port=self.broker_port,
                                          db=self.broker_database_index)
