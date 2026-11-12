"""Domain errors. The API maps each to one HTTP status in a single place."""


class NyayaError(Exception):
    code = "error"


class NotFoundError(NyayaError):
    code = "not_found"


class InvalidRequestError(NyayaError):
    code = "invalid_request"


class LlmBusyError(NyayaError):
    """Daily cap or provider rate limit reached: try again later."""

    code = "llm_busy"


class LlmUnavailableError(NyayaError):
    """Provider failed, or nothing it produced survived grounding."""

    code = "llm_unavailable"


class NoteWithdrawnError(NyayaError):
    """A shared note that was revoked or has expired."""

    code = "note_withdrawn"
