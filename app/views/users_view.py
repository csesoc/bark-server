from flask_admin.contrib.sqla import ModelView
from flask_login import current_user

from app.db import User


class UsersView(ModelView):
    column_labels = {
        'zid': 'zID'
    }

    def is_accessible(self):
        return current_user.is_authenticated()

    def __init__(self, session, **kwargs):
        super(UsersView, self).__init__(User, session, **kwargs)

