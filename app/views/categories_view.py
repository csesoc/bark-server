from flask_admin.contrib.sqla import ModelView
from flask_login import current_user

from app.db import Category


class CategoriesView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated()

    def __init__(self, session, **kwargs):
        super(CategoriesView, self).__init__(Category, session, **kwargs)
