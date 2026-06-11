from celery import shared_task


@shared_task
def send_new_message_push_notifications(message_id: int) -> dict:
    from apps.users.push_services import send_message_push_by_id

    return send_message_push_by_id(message_id).as_dict()
