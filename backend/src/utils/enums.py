from enum import Enum


class UserRole(str, Enum):
    admin = "admin"
    user = "user"
