from abc import ABC
from abc import abstractmethod


class BaseRepository(ABC):

    @abstractmethod
    def save(self, model):
        ...

    @abstractmethod
    def get(self, *args, **kwargs):
        ...

    @abstractmethod
    def delete(self, *args, **kwargs):
        ...