from enum import Enum


class LogStepStatus(str, Enum):
    in_progress = "IN_PROGRESS"
    success = "SUCCESS"
    failure = "FAILURE"


class LogFlowAuthor(str, Enum):
    user = "User"
    system = "System"
    