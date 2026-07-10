from abc import ABC, abstractmethod

from fastapi import Request

from .models import CurrentUser, Login, Token


class BaseAuth(ABC):
    @abstractmethod
    def login(self, data: Login) -> Token:
        """Login a user."""
        pass

    @abstractmethod
    def authenticate(self, request: Request, token: str) -> CurrentUser:
        """Authenticate a user."""
        pass

    @abstractmethod
    def authenticate_optional(self, request: Request) -> CurrentUser | None:
        """Authenticate a user if credentials are present."""
        pass
