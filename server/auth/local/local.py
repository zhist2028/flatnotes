import json
import os
import secrets
from base64 import b32encode
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError
from pyotp import TOTP
from pyotp.utils import build_uri
from qrcode import QRCode

from global_config import AuthType
from helpers import get_env, is_valid_filename, strip_whitespace
from logger import logger

from ..base import BaseAuth
from ..models import CurrentUser, FileUser, Login, Token, UsersFile

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/token", auto_error=False)


class LocalAuth(BaseAuth):
    JWT_ALGORITHM = "HS256"

    def __init__(self, global_config) -> None:
        self.global_config = global_config
        self.username = get_env("FLATNOTES_USERNAME", mandatory=True).lower()
        self.password = get_env("FLATNOTES_PASSWORD", mandatory=True)
        self.secret_key = get_env("FLATNOTES_SECRET_KEY", mandatory=True)
        self.session_expiry_days = get_env(
            "FLATNOTES_SESSION_EXPIRY_DAYS", default=30, cast_int=True
        )

        # TOTP
        self.is_totp_enabled = False
        if self.global_config.auth_type == AuthType.TOTP:
            self.is_totp_enabled = True
            self.totp_key = get_env("FLATNOTES_TOTP_KEY", mandatory=True)
            self.totp_key = b32encode(self.totp_key.encode("utf-8"))
            self.totp = TOTP(self.totp_key)
            self.last_used_totp = None
            self._display_totp_enrolment()

    def login(self, data: Login) -> Token:
        if self._is_admin_login(data):
            access_token = self._create_access_token(
                data={"sub": self.username, "role": "admin"}
            )
            return Token(access_token=access_token)

        file_user = self._get_matching_file_user(data)
        if file_user:
            access_token = self._create_access_token(
                data={"sub": file_user.username, "role": "user"}
            )
            return Token(access_token=access_token)

        raise ValueError("Incorrect login credentials.")

    def authenticate(
        self, request: Request, token: str = Depends(oauth2_scheme)
    ) -> CurrentUser:
        # If no token is found in the header, check the cookies
        if token is None:
            token = request.cookies.get("token")
        try:
            return self._validate_token(token)
        except (JWTError, ValueError):
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def authenticate_optional(self, request: Request) -> CurrentUser | None:
        token = self._token_from_request(request)
        try:
            return self._validate_token(token)
        except (JWTError, ValueError):
            return None

    def _is_admin_login(self, data: Login) -> bool:
        # Check Username
        username_correct = secrets.compare_digest(
            self.username.lower(), data.username.lower()
        )

        # Check Password & TOTP
        expected_password = self.password
        if self.is_totp_enabled:
            current_totp = self.totp.now()
            expected_password += current_totp
        password_correct = secrets.compare_digest(
            expected_password, data.password
        )

        if not (
            username_correct
            and password_correct
            # Prevent TOTP from being reused
            and (
                self.is_totp_enabled is False
                or current_totp != self.last_used_totp
            )
        ):
            return False
        if self.is_totp_enabled:
            self.last_used_totp = current_totp
        return True

    def _get_matching_file_user(self, data: Login) -> FileUser | None:
        for user in self._load_file_users():
            username_correct = secrets.compare_digest(
                user.username.lower(), data.username.lower()
            )
            password_correct = secrets.compare_digest(
                user.password, data.password
            )
            if username_correct and password_correct:
                return user
        return None

    def _validate_token(self, token: str) -> CurrentUser:
        if token is None:
            raise ValueError
        payload = jwt.decode(
            token, self.secret_key, algorithms=[self.JWT_ALGORITHM]
        )
        username = payload.get("sub")
        role = payload.get("role")
        if username is None:
            raise ValueError
        if role == "user":
            file_user = self._get_file_user(username)
            if file_user is None:
                raise ValueError
            return self._current_user_for_file_user(file_user)

        # Tokens created before multi-user support did not include a role.
        if username.lower() == self.username:
            return self._admin_user()

        raise ValueError

    def _token_from_request(self, request: Request) -> str | None:
        authorization = request.headers.get("Authorization")
        if authorization and authorization.lower().startswith("bearer "):
            return authorization[7:]
        return request.cookies.get("token")

    def _create_access_token(self, data: dict):
        to_encode = data.copy()
        expiry_datetime = datetime.utcnow() + timedelta(
            days=self.session_expiry_days
        )
        to_encode.update({"exp": expiry_datetime})
        encoded_jwt = jwt.encode(
            to_encode, self.secret_key, algorithm=self.JWT_ALGORITHM
        )
        return encoded_jwt

    def _admin_user(self) -> CurrentUser:
        os.makedirs(self.global_config.admin_workspace, exist_ok=True)
        return CurrentUser(
            username=self.username,
            workspace_path=self.global_config.admin_workspace,
            is_admin=True,
            read_only=False,
        )

    def _current_user_for_file_user(self, user: FileUser) -> CurrentUser:
        workspace_name = self._workspace_name_for_user(user)
        workspace_path = os.path.join(
            self.global_config.workspaces_path, workspace_name
        )
        os.makedirs(workspace_path, exist_ok=True)
        return CurrentUser(
            username=user.username,
            workspace_path=workspace_path,
            is_admin=False,
            read_only=user.read_only,
        )

    def _workspace_name_for_user(self, user: FileUser) -> str:
        workspace = user.workspace or user.username
        workspace = strip_whitespace(workspace)
        is_valid_filename(workspace)
        if (
            not workspace
            or workspace in [".", ".."]
            or os.path.isabs(workspace)
            or os.path.normpath(workspace) != workspace
        ):
            raise ValueError(f"Invalid workspace '{workspace}'.")
        return workspace

    def _get_file_user(self, username: str) -> FileUser | None:
        for user in self._load_file_users():
            if user.username.lower() == username.lower():
                return user
        return None

    def _load_file_users(self) -> list[FileUser]:
        users_file = self.global_config.users_file
        if users_file is None:
            return []
        if not os.path.exists(users_file):
            logger.warning(f"Users file '{users_file}' does not exist.")
            return []
        try:
            with open(users_file, "r", encoding="utf-8") as f:
                users_file_data = UsersFile.model_validate(json.load(f))
            return self._validated_file_users(users_file_data.users)
        except (json.JSONDecodeError, OSError, ValidationError, ValueError) as e:
            logger.error(f"Failed to load users file '{users_file}': {e}")
            raise ValueError("Invalid users file.")

    def _validated_file_users(self, users: list[FileUser]) -> list[FileUser]:
        validated_users = []
        usernames = set()
        workspaces = set()
        for user in users:
            user = self._validated_file_user(user)
            username = user.username.lower()
            workspace = self._workspace_name_for_user(user).lower()
            if username == self.username:
                raise ValueError("File user cannot use the admin username.")
            if username in usernames:
                raise ValueError(f"Duplicate username '{user.username}'.")
            if workspace in workspaces:
                workspace_name = self._workspace_name_for_user(user)
                raise ValueError(
                    f"Duplicate workspace '{workspace_name}'."
                )
            usernames.add(username)
            workspaces.add(workspace)
            validated_users.append(user)
        return validated_users

    def _validated_file_user(self, user: FileUser) -> FileUser:
        user.username = strip_whitespace(user.username)
        if not user.username:
            raise ValueError("Username cannot be empty.")
        if not user.password:
            raise ValueError(f"Password cannot be empty for '{user.username}'.")
        is_valid_filename(user.username)
        self._workspace_name_for_user(user)
        return user

    def _display_totp_enrolment(self):
        # Fix for #237. Remove padding as per spec:
        # https://github.com/google/google-authenticator/wiki/Key-Uri-Format#secret
        unpadded_secret = self.totp_key.rstrip(b"=")
        uri = build_uri(unpadded_secret, self.username, issuer="flatnotes")
        qr = QRCode()
        qr.add_data(uri)
        print(
            "\nScan this QR code with your TOTP app of choice",
            "e.g. Authy or Google Authenticator:",
        )
        qr.print_ascii()
        print(
            f"Or manually enter this key: {self.totp.secret.decode('utf-8')}\n"
        )
