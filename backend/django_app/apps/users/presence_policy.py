from .models import User


def can_view_presence(request_user: User, target_user: User) -> bool:
    if request_user.is_staff:
        return True
    if not request_user.show_online_status:
        return False
    return target_user.show_online_status
