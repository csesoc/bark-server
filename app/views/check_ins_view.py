from flask_admin.contrib.sqla import ModelView
from flask_login import current_user

from app.db import CheckIn
from .formatters import DEFAULT_FORMATTERS


class CheckInsView(ModelView):
    column_list = [
        'student',
        'event',
        'timestamp',
        'number_of_scans',
        'is_cse',
        'degree'
    ]

    column_labels = {
        'is_cse': 'Is CSE?',
        'number_of_scans': 'Number of scans'
    }

    column_filters = [
        'event.name',
        'timestamp',
        'student.zid',
        'student.given_names',
        'student.surname',
        'degree',
        'enrolments.course',
        'is_cse',
        'number_of_scans'
    ]

    column_type_formatters = DEFAULT_FORMATTERS

    column_default_sort = ('timestamp', True)

    def is_accessible(self):
        return current_user.is_authenticated()

    def __init__(self, session, **kwargs):
        super(CheckInsView, self).__init__(CheckIn, session, **kwargs)
