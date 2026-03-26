from rest_framework.throttling import ScopedRateThrottle


class BurstScopedRateThrottle(ScopedRateThrottle):
    """
    Оставляем стандартный ScopedRateThrottle,
    но выносим класс отдельно для явности и будущего расширения.
    """
    pass