from typing import List


def notif_dispatch(message: str,
                   notif_type: str,
                   url: str,
                   users: List['User']):
    from .users import Notification
    for user in users:
        notif = Notification(message=message, notif_type=notif_type, url=url)
        notif.save()
        user.pending_notifications.append(notif)
        user.save()
