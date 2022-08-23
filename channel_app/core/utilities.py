import json
import logging

from celery import current_app as app
from requests import Response, Request

from channel_app.core.clients import RedisClient

logger = logging.getLogger(__name__)


class LockTask(app.Task):
    """this abstract class ensures the same tasks run only once at a time"""
    abstract = True

    def __init__(self, *args, **kwargs):
        from channel_app.core import settings
        self.TTL = getattr(settings, 'DEFAULT_TASK_LOCK_TTL', 60 * 15)
        self.redis = RedisClient()
        super(LockTask, self).__init__(*args, **kwargs)

    def generate_lock_cache_key(self, *args, **kwargs):
        args_key = [str(arg) for arg in args]
        kwargs_key = ['{}_{}'.format(k, str(v)) for k, v in
                      sorted(kwargs.items())]
        return '_'.join([self.name] + args_key + kwargs_key)

    def __call__(self, *args, **kwargs):
        """check task"""
        lock_cache_key = (self.request.headers or {}).pop('cache_key', None)
        if not lock_cache_key:
            lock_cache_key = self.generate_lock_cache_key(*args, **kwargs)

        if self.lock_acquired(lock_cache_key):
            try:
                return self.run(*args, **kwargs)
            finally:
                pass
        else:
            return f'Task {self.name} is already running..'

    def lock_acquired(self, lock_cache_key):
        lock_acquired = True
        app_inspect = self.app.control.inspect()
        active_task = app_inspect.active(safe=True)
        if not active_task:
            return lock_acquired
        for worker_name, task_list in active_task.items():
            for task in task_list:
                if (task.get("name", None) == lock_cache_key) and (
                        self.request.id != task['id']):
                    lock_acquired = False
                    break
        return lock_acquired


def split_list(lst, n):
    """
    Split a list to chunks of n
    :param lst:
    :param n:
    :return iterator to get chunks
    """
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def request_log():
    import logging
    try:
        import http.client as http_client
    except ImportError:
        import httplib as http_client

    http_client.HTTPConnection.debuglevel = 1
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True


def is_updated(current, new):
    no_default = "NO_DEFAULT"
    for key, new_value in new.items():
        old_value = getattr(current, key, no_default)
        if old_value != no_default and old_value != new_value:
            return True
    return False


def lowercase_keys(obj):
    if isinstance(obj, dict):
        obj = {key.lower(): value for key, value in obj.items()}
        for key, value in obj.items():
            if isinstance(value, list):
                for idx, item in enumerate(value):
                    value[idx] = lowercase_keys(value[idx])
            obj[key] = value
    return obj


class MockResponse(Response):
    def __init__(self,
                 url='http://example.com',
                 headers={"Content-Type": "application/json",
                          "charset": "UTF-8"},
                 status_code=200,
                 reason='Success',
                 _content='Some html goes here',
                 json_=None,
                 encoding='UTF-8',
                 request_body={}
                 ):
        request = Request()
        request.body = request_body
        request.url = url
        self.request = request
        self.url = url
        self.headers = headers
        if json_ and headers['Content-Type'] == 'application/json':
            self._content = json.dumps(json_).encode(encoding)
        else:
            self._content = _content.encode(encoding)

        self.status_code = status_code
        self.reason = reason
        self.encoding = encoding


def mock_response_decorator(func):
    def wrapper(*args, **kwargs):
        return MockResponse(json_=func(*args, **kwargs))

    return wrapper
