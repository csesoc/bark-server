from flask_admin import AdminIndexView as BaseAdminIndexView, expose, helpers
from flask_login import logout_user, current_user, login_user
from flask import redirect, url_for, request
from wtforms import fields, validators, Form

from app.db import db, User


class LoginForm(Form):
    zid = fields.TextField('zID', validators=[validators.required()])
    password = fields.PasswordField('Password', validators=[validators.required()])

    def __init__(self, ldap_service, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        self._ldap_service = ldap_service

    def validate_zid(self, field):
        user = self.get_user()

        if user is None:
            raise validators.ValidationError('Invalid zID/password')

        user_data = self._ldap_service.authenticate(self.zid.data, self.password.data)
        if not user_data:
            raise validators.ValidationError('Invalid zID/password')

        # set user data
        user.first_name = user_data['first_name']
        user.last_name = user_data['last_name']
        db.session.commit()

    def get_user(self):
        return db.session.query(User).filter_by(zid=self.zid.data).first()


class AdminIndexView(BaseAdminIndexView):
    def __init__(self, ldap_service, *args, **kwargs):
        super(AdminIndexView, self).__init__(*args, **kwargs)
        self._ldap_service = ldap_service

    @expose('/')
    def index(self):
        if not current_user.is_authenticated():
            return redirect(url_for('.login_view'))
        return super(AdminIndexView, self).index()

    @expose('/login/', methods=('GET', 'POST'))
    def login_view(self):
        form = LoginForm(self._ldap_service, request.form)
        if helpers.validate_form_on_submit(form):
            user = form.get_user()
            login_user(user)

        if current_user.is_authenticated():
            return redirect(url_for('.index'))
        self._template_args['form'] = form
        return super(AdminIndexView, self).index()

    @expose('/logout')
    def logout_view(self):
        logout_user()
        return redirect(url_for('.index'))
