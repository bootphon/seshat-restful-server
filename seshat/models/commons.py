from typing import List, Optional


def notif_dispatch(message: str,
                   notif_type: str,
                   object_type: str,
                   object_id: Optional[str],
                   users: List['User']):
    from .users import Notification
    for user in users:
        notif = Notification(message=message,
                             notif_type=notif_type,
                             object_type=object_type,
                             object_id=object_id)
        notif.save()
        user.pending_notifications.append(notif)
        user.save()
