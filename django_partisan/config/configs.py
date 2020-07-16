from datetime import timedelta, datetime
from typing import List, Type

from pydantic import BaseModel, validator, ValidationError
from django.utils import timezone

from django_partisan.config import const


class ErrorsHandleConfig(BaseModel):
    retry_on_errors: List[Type[Exception]]
    retries_count: int
    retry_pause: int
    retry_pause_strategy: str = const.DELAY_STRATEGY_CONSTANT

    def shoud_be_retried(self, try_num: int) -> bool:
        return try_num - 1 < self.retries_count

    def get_new_datetime_for_delay(self, try_num: int) -> datetime:
        if not self.shoud_be_retried(try_num):
            raise RuntimeError('Task should not be delayed, tries ended')
        now = timezone.now()
        if self.retry_pause_strategy == const.DELAY_STRATEGY_CONSTANT:
            return now + timedelta(seconds=self.retry_pause)
        return now + timedelta(seconds=(self.retry_pause * try_num))

    @validator('retry_on_errors')
    def must_be_not_empty(cls, v: List) -> List:
        if len(v) == 0:
            raise ValueError('"retry_on_errors" should be defined and not empty')
        return v

    @validator('retry_pause_strategy')
    def strategy_must_be_one_of_defined(cls, v: str) -> str:
        if v not in const.DELAY_STRATEGIES:
            raise ValueError(
                '"retry_pause_strategy" should be set to '
                'DELAY_STRATEGY_INCREMENTAL or DELAY_STRATEGY_CONSTANT'
            )
        return v

    @validator('retries_count')
    def value_should_be_bigger_than_zero(cls, v: int) -> int:
        if v < 1:
            raise ValueError('"retries_count" should be equal or bigger then 1')
        return v

    @validator('retry_pause')
    def value_should_be_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError('"retry_pause" should be bigger then 0')
        return v
