from flask_admin.contrib.sqla import ModelView
from flask_login import current_user

from app.db import Degree


class DegreesView(ModelView):
    column_labels = {
        'is_cse': 'Is CSE?'
    }

    column_list = [
        'code',
        'name',
        'is_cse'
    ]

    column_filters = [
        'code',
        'name',
        'is_cse'
    ]

    def is_accessible(self):
        return current_user.is_authenticated()

    def __init__(self, session, **kwargs):
        super(DegreesView, self).__init__(Degree, session, **kwargs)
