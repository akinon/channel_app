import asyncio
from typing import Any

from omnisdk.omnitron.endpoints import CatalogEndpoint, ChannelEndpoint
from omnisdk.omnitron.models import Catalog, Channel


class BaseIntegration(object):
    """
    To integrate with any system you must create a class which inherits from BaseIntegration.
    This class was designed to work with `command design pattern` which basically defines
    a task procedure interface. All defined commands override some of the default base
    methods according to their requirements.
    """
    actions = {}

    def get_action(self, key: str):
        return self.actions[key]

    def do_action(self, key: str, **kwargs) -> Any:
        """
        Runs the command given with the key and supplies the additional parameters to the command.

        :param key: Command key
        :param kwargs: Any additional parameters can be specified, for example `objects` must be
            supplied if you want to provide input to the action.

        :return: Result of the command

        """
        action_class = self.get_action(key)
        action_object = action_class(integration=self, **kwargs)
        return action_object.run()

    def do_action_async_run(self, key: str, **kwargs) -> Any:
        """
        Runs the command given with the key asynchronously and supplies the additional parameters
        to the command.

        :param key: Command key
        :param kwargs: Any additional parameters can be specified, for example `objects` must be
            supplied if you want to provide input to the action.

        :return: Result of the command

        """

        action_class = self.get_action(key)
        action_object = action_class(integration=self, **kwargs)
        return asyncio.run(action_object.run_async())

    @property
    def catalog(self) -> Catalog:
        """
        Retrieves the catalog object using the `catalog_id` stored in the `self`.

        Side effect: It stores the result in the `self.catalog_object`, if catalog is updated
        on the currently running task you must delete self.catalog_object and re-call this method
        """
        if not getattr(self, 'catalog_object', None):
            self.catalog_object = CatalogEndpoint().retrieve(id=self.catalog_id)
        return self.catalog_object

    @property
    def channel(self) -> Channel:
        """
        Retrieves the channel object using the `channel_id` stored in the `self`.

        Side effect: It stores the result in the `self.channel_object`, if channel is updated
        on the currently running task you must delete self.channel_object and re-call this method
        """
        if not getattr(self, 'channel_object', None):
            self.channel_object = ChannelEndpoint().retrieve(id=self.channel_id)
        return self.channel_object
