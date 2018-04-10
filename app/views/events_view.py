from flask_admin.contrib.sqla import ModelView
from flask_login import current_user

from app.db import Event
from .formatters import DEFAULT_FORMATTERS
from .fields.qr_code_field import QRCodeField


class EventsView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated()

    column_type_formatters = DEFAULT_FORMATTERS

    column_list = [
        'name',
        'location',
        'start',
        'end',
        'category',
        'check_cse',
        'check_arc',
        'timestamp',
        # 'token',
    ]

    column_labels = {
        'start': 'Start Time',
        'end': 'End Time',
        'check_cse': 'Check CSE',
        'check_arc': 'Check ARC',
        'timestamp': 'Created At'
    }

    column_default_sort = ('start', True)

    form_overrides = {
        'token': QRCodeField
    }

    form_widget_args = {
        'token': {
            'disabled': True
        }
    }

    form_excluded_columns = [
        'timestamp',
        'sessions'
    ]

    def __init__(self, session, **kwargs):
        super(EventsView, self).__init__(Event, session, **kwargs)
