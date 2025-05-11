class ProxyError(Exception):
    """
    Erreur de base pour les problèmes liés au proxy
    """
    pass


class ServiceUnavailableError(ProxyError):
    """
    Erreur levée lorsqu'un service n'est pas disponible
    """
    pass


class RouteNotFoundError(ProxyError):
    """
    Erreur levée lorsqu'aucune route n'est configurée pour un chemin
    """
    pass


class AuthenticationError(ProxyError):
    """
    Erreur levée lors de problèmes d'authentification
    """
    pass


class RateLimitExceededError(ProxyError):
    """
    Erreur levée lorsque la limite de taux est dépassée
    """
    pass