from enum import Enum


class FileCreator(str, Enum):
    user = "user"
    system = "system"


class UserRole(str, Enum):
    admin = "admin"
    user = "user"


class FieldType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    CATEGORY = "category"
    DATE = "date"
    ARRAY = "array"
    OBJECT = "object"


class ComparisonMethod(str, Enum):
    EXACT = "exact"
    FUZZY = "fuzzy"
    NUMERIC = "numeric"
    BOOLEAN = "boolean"
    CATEGORY = "category"
    DATE = "date"
