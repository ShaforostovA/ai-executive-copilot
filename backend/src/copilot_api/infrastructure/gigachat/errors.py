class GigaChatError(Exception):
    pass


class GigaChatConfigurationError(GigaChatError):
    pass


class GigaChatAuthenticationError(GigaChatError):
    pass


class GigaChatRateLimitError(GigaChatError):
    pass


class GigaChatServiceUnavailableError(GigaChatError):
    pass


class GigaChatTimeoutError(GigaChatError):
    pass


class GigaChatNetworkError(GigaChatError):
    pass


class GigaChatResponseError(GigaChatError):
    pass


class GigaChatRequestError(GigaChatError):
    pass
