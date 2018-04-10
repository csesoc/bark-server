from flask_admin.contrib.sqla import ModelView
from flask_login import current_user

from app.db import Enrolment


class EnrolmentsView(ModelView):
    column_list = [
        'check_in',
        'course'
    ]

    column_filters = [
        'course.code',
        'check_in.event.name',
        'check_in.student.zid',
        'check_in.student.given_names',
        'check_in.student.surname'
    ]

    def is_accessible(self):
        return current_user.is_authenticated()

    def __init__(self, session, **kwargs):
        super(EnrolmentsView, self).__init__(Enrolment, session, **kwargs)

