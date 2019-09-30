from typing import List


class DBError(Exception):
    """Exception raised when there is something wrong with the db,
    that should be displayed on the client"""
    def __init__(self, msg: str, *args):
        super().__init__(*args)
        self.msg = msg


def notif_dispatch(message : str,
                   notif_type : str,
                   url : str,
                   users : List['User']):
    from .users import Notification
    for user in users:
        notif = Notification(message=message, notif_type=notif_type, url=url)
        notif.save()
        user.pending_notifications.append(notif)
        user.save()
