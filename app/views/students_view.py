from flask_admin.contrib.sqla import ModelView
from flask_login import current_user

from app.db import Student


class StudentsView(ModelView):
    column_labels = {
        'zid': 'zID',
        'is_arc': 'Is ARC?',
        'override_cse': 'Override CSE?'
    }

    column_list = [
        'surname',
        'given_names',
        'zid',
        'is_arc',
        'override_cse'
    ]

    column_filters = [
        'surname',
        'given_names',
        'zid',
        'is_arc',
        'override_cse'
    ]

    def is_accessible(self):
        return current_user.is_authenticated()

    def __init__(self, session, **kwargs):
        super(StudentsView, self).__init__(Student, session, **kwargs)
