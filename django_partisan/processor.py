import abc
from datetime import datetime
from typing import Type, Any

from django.db import transaction

from django_partisan.exceptions import ProcessorClassNotFound
from django_partisan.models import Task
from django_partisan.registry import registry


class BaseTaskProcessor(abc.ABC):
    PRIORITY: int = 10
    UNIQUE_FOR_PARAMS: bool = False

    def __init__(self, *args: Any, **kwargs: Any):
        self.args = args
        self.kwargs = kwargs

    @classmethod
    def get_processor_class(cls, processor_name: str) -> Type['BaseTaskProcessor']:
        if registry.is_processor_registered(processor_name):
            return registry.get_processor_class_by_name(processor_name)
        for subclass in cls.__subclasses__():
            if subclass.__name__ == processor_name:
                return subclass
        raise ProcessorClassNotFound(processor_name)

    @abc.abstractmethod
    def run(self) -> Any:
        raise NotImplementedError()  # pragma: no cover

    @transaction.atomic
    def delay(self, *, priority: int = 0, execute_after: datetime = None) -> Task:
        if self.UNIQUE_FOR_PARAMS:
            task_config = {
                'arguments__args': self.args,
                'arguments__kwargs': self.kwargs,
                'status': Task.STATUS_NEW,
                'processor_class': self.processor_name,
            }
            if Task.objects.select_for_update().filter(**task_config).exists():
                return Task.objects.get(**task_config)

        task_data = {
            'processor_class': self.processor_name,
            'arguments': {'args': self.args, 'kwargs': self.kwargs},
            'priority': priority or self.PRIORITY,
        }
        if execute_after is not None:
            task_data.update(
                {'execute_after': execute_after,}
            )
        return Task.objects.create(**task_data)

    @property
    def processor_name(self) -> str:
        return self.__class__.__name__
