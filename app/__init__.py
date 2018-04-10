from flask import Flask
from flask_admin import Admin
from flask_login import LoginManager
from app.services.udb_service import create_udb_service
from app.services.ldap_service import create_ldap_service
from app.views import (
    ReportsView, EventsView, StudentsView, CoursesView, EnrolmentsView, CheckInsView, UsersView,
    CategoriesView, DegreesView, AdminIndexView, AdminRedirectView, ApiView, AppDownloadView
)
from db import db, User


def init_login(app):
    login_manager = LoginManager(app)

    @login_manager.user_loader
    def load_user(zid):
        return db.session.query(User).get(zid)


def create_app(config):
    app = Flask(__name__)
    app.config.from_object(config)
    db.init_app(app)
    init_login(app)

    udb_service = create_udb_service(config)
    ldap_service = create_ldap_service(config)

    admin = Admin(app, name='Bark', index_view=AdminIndexView(ldap_service), base_template='master.html')
    admin.add_view(ReportsView(name='Reports'))
    admin.add_view(EventsView(db.session, name='Events'))
    admin.add_view(StudentsView(db.session, name='Students'))
    admin.add_view(DegreesView(db.session, name='Degrees'))
    admin.add_view(CoursesView(db.session, name='Courses'))
    admin.add_view(EnrolmentsView(db.session, name='Enrolments'))
    admin.add_view(CheckInsView(db.session, name='Check-ins'))
    admin.add_view(UsersView(db.session, name='Users'))
    admin.add_view(CategoriesView(db.session, name='Categories'))

    app.add_url_rule('/api', view_func=ApiView.as_view('api', udb_service, config.EVENT_LEEWAY))
    app.add_url_rule('/', view_func=AdminRedirectView.as_view('admin-redirect'))
    app.add_url_rule('/download', view_func=AppDownloadView.as_view('app-download', config.ANDROID_URL))

    return app
