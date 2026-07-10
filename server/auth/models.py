from typing import List, Optional

from pydantic import BaseModel, Field

from helpers import CustomBaseModel


class Login(CustomBaseModel):
    username: str
    password: str


class Token(BaseModel):
    # Note: OAuth requires keys to be snake_case so we use the standard
    # BaseModel here
    access_token: str
    token_type: str = Field("bearer")


class FileUser(CustomBaseModel):
    username: str
    password: str
    workspace: Optional[str] = Field(None)
    read_only: bool = Field(False)


class UsersFile(CustomBaseModel):
    users: List[FileUser] = Field(default_factory=list)


class CurrentUser(CustomBaseModel):
    username: str
    workspace_path: str
    is_admin: bool = Field(False)
    read_only: bool = Field(False)
