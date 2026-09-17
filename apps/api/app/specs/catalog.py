"""The frozen block catalog.

This is the complete menu the AI planner may choose from. Nothing outside this
file can appear in a spec, and the validator enforces that. Adding a member
here means committing to rendering or executing it — so adding is a decision,
not a convenience.
"""

from enum import StrEnum


class FieldType(StrEnum):
    TEXT = "text"
    LONG_TEXT = "long_text"
    NUMBER = "number"
    DATE = "date"
    CHOICE = "choice"
    BOOLEAN = "boolean"
    REFERENCE = "reference"  # points at another entity's record
    USER = "user"  # points at an app_user


class ScreenType(StrEnum):
    FORM = "form"  # create a record
    TABLE = "table"  # rows with search/filter/sort
    DETAIL = "detail"  # one record, read-only + actions
    APPROVALS = "approvals"  # queue of items waiting on this role


class RecordScope(StrEnum):
    OWN = "own"  # only records this user created
    ALL = "all"  # every record in the app


class StepType(StrEnum):
    CREATE_RECORD = "create_record"
    UPDATE_RECORD = "update_record"
    CONDITION = "condition"
    APPROVAL = "approval"
    NOTIFY_IN_APP = "notify_in_app"
    NOTIFY_EMAIL = "notify_email"
    AI_CLASSIFY = "ai_classify"


class TriggerType(StrEnum):
    FORM_SUBMISSION = "form_submission"


class Operator(StrEnum):
    EQ = "eq"
    NEQ = "neq"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    CONTAINS = "contains"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"


#: Operators that compare against a right-hand value. The rest are unary.
BINARY_OPERATORS = frozenset(
    {
        Operator.EQ,
        Operator.NEQ,
        Operator.GT,
        Operator.GTE,
        Operator.LT,
        Operator.LTE,
        Operator.CONTAINS,
    }
)

#: Operators that require both sides to be numeric.
NUMERIC_OPERATORS = frozenset(
    {Operator.GT, Operator.GTE, Operator.LT, Operator.LTE}
)

#: Field types whose stored value is a reference to another row.
REFERENCE_FIELD_TYPES = frozenset({FieldType.REFERENCE, FieldType.USER})

#: Every entity gets these automatically. Specs must not redeclare them.
RESERVED_FIELD_NAMES = frozenset(
    {"id", "created_at", "updated_at", "created_by", "app_id", "entity_name"}
)

#: Slugs we serve ourselves, so no published project may claim one.
RESERVED_SLUGS = frozenset(
    {
        "api",
        "app",
        "apps",
        "admin",
        "login",
        "logout",
        "signup",
        "dashboard",
        "settings",
        "account",
        "billing",
        "pricing",
        "docs",
        "help",
        "support",
        "about",
        "blog",
        "static",
        "assets",
        "public",
        "health",
        "www",
        "mail",
        "s",
        "a",
        "new",
        "edit",
        "terms",
        "privacy",
    }
)

#: Cap on how many steps one workflow may contain — a guard against a planner
#: that loops, and a ceiling on how long one run can take.
MAX_WORKFLOW_STEPS = 40
