from flask_admin.contrib.sqla import ModelView
from flask_login import current_user

from app.db import Course


class CoursesView(ModelView):
    column_list = [
        'code',
        'name'
    ]

    column_filters = [
        'code',
        'name'
    ]

    def is_accessible(self):
        return current_user.is_authenticated()

    def __init__(self, session, **kwargs):
        super(CoursesView, self).__init__(Course, session, **kwargs)

