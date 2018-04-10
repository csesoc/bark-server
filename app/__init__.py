from flask import Flask, url_for, redirect, request, Response
from flask_admin import Admin, BaseView, expose, helpers, AdminIndexView
from flask_admin.model import typefmt
from flask_admin.contrib.sqla import ModelView
from flask_sqlalchemy import SQLAlchemy
from flask_login import current_user, login_user, LoginManager, logout_user
from wtforms import form, fields, validators
from wtforms.widgets import HTMLString
from datetime import datetime
import time
import os
import StringIO
import json
import re
import csv
import base64
import qrcode
import requests
from app.services.udb_service import create_udb_service
from app.services.ldap_service import create_ldap_service
from config import get_config

config = get_config()
app = Flask(__name__)
app.config.from_object(config)
db = SQLAlchemy(app)

udb_service = create_udb_service(config)
ldap_service = create_ldap_service(config)


# --- Methods to do stuff
def utc_to_local(d):
    now = time.time()
    offset = datetime.fromtimestamp(now) - datetime.utcfromtimestamp(now)
    return d + offset


def generate_token():
    b = os.urandom(32)
    s = b.encode('hex')
    return s


def validate_zid(zid):
    return re.match(r'^z[0-9]{7}$', zid) is not None


# --- Web fetching stuff. Maybe move into a different module one day.

def degree_name(code):
    if code == 0:
        return 'Non-CSE degree'

    for u in ('undergraduate', 'postgraduate', 'research'):
        url = 'http://www.handbook.unsw.edu.au/%s/programs/current/%s.html' % (u, code)
        r = requests.get(url)
        content = r.content

        match = re.search(r'<meta name="DC\.Subject\.Title" CONTENT="(.*?)">', content)
        if match:
            return match.group(1).strip()


def course_name(code):
    for u in ('undergraduate', 'postgraduate'):
        url = 'http://www.handbook.unsw.edu.au/%s/courses/current/%s.html' % (u, code)
        r = requests.get(url)
        content = r.content

        match = re.search(r'<meta name="DC\.Subject\.Description\.Short" CONTENT="(.*?)">', content)
        if match:
            return match.group(1).strip()


# --- Database stuff

class User(db.Model):
    """
    Defines users that have permission to log in to the Bark web interface.
    """
    id = db.Column(db.Integer, primary_key=True)
    zid = db.Column(db.String(80), unique=True)
    first_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80))

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    def __unicode__(self):
        return self.zid


class Event(db.Model):
    """
    Defines an event.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True)
    location = db.Column(db.String(200))
    start = db.Column(db.DateTime)
    end = db.Column(db.DateTime)

    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    category = db.relationship('Category', backref=db.backref('events', lazy='dynamic'))

    check_cse = db.Column(db.Boolean)
    check_arc = db.Column(db.Boolean)

    timestamp = db.Column(db.DateTime)

    token = db.Column(db.String(64))  # hex-encoded session token

    def __init__(self):
        self.timestamp = datetime.now()

    def __unicode__(self):
        return self.name


class Category(db.Model):
    """
    Defines an event category.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))

    def __unicode__(self):
        return self.name


class Student(db.Model):
    """
    Defines a student.
    """
    id = db.Column(db.Integer, primary_key=True)
    zid = db.Column(db.String(20))
    given_names = db.Column(db.String(100))
    surname = db.Column(db.String(100))
    is_arc = db.Column(db.Boolean)  # update this infrequently, maybe every year
    # or so. probably a good idea to purge the
    # database at the start of each year.
    override_cse = db.Column(db.Boolean)

    def __unicode__(self):
        return '%s, %s (%s)' % (self.surname, self.given_names, self.zid)


class Degree(db.Model):
    """
    Defines a UNSW degree.
    """
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.Integer)
    name = db.Column(db.String(100))
    is_cse = db.Column(db.Boolean)

    def __unicode__(self):
        return self.name if self.name else 'Unknown Degree (%s)' % self.code


class Course(db.Model):
    """
    Defines a UNSW course.
    """
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(8))
    name = db.Column(db.String(100))

    def __unicode__(self):
        return self.code


class Enrolment(db.Model):
    """
    Defines a student's enrolment in a course.
    """
    id = db.Column(db.Integer, primary_key=True)

    check_in_id = db.Column(db.Integer, db.ForeignKey('check_in.id'))
    check_in = db.relationship('CheckIn', backref=db.backref('enrolments', lazy='dynamic'))

    course_id = db.Column(db.Integer, db.ForeignKey('course.id'))
    course = db.relationship('Course', backref=db.backref('enrolments', lazy='dynamic'))


class CheckIn(db.Model):
    """
    Defines an instance of an student "checking in" to an event.
    """
    id = db.Column(db.Integer, primary_key=True)

    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    student = db.relationship('Student', backref=db.backref('checkins', lazy='dynamic'))

    event_id = db.Column(db.Integer, db.ForeignKey('event.id'))
    event = db.relationship('Event', backref=db.backref('students', lazy='dynamic'))

    timestamp = db.Column(db.DateTime)

    number_of_scans = db.Column(db.Integer)

    # we also associate some information with the checkin
    # namely their degree and courses
    # this isn't tracked with the student since it can change
    is_cse = db.Column(db.Boolean)
    degree_id = db.Column(db.Integer, db.ForeignKey('degree.id'))
    degree = db.relationship('Degree', backref=db.backref('students', lazy='dynamic'))

    def __init__(self):
        self.timestamp = datetime.now()
        self.number_of_scans = 1

    def __unicode__(self):
        return '%s @ %s' % (unicode(self.student), unicode(self.event))


#
# --- Views

class LoginForm(form.Form):
    zid = fields.TextField('zID', validators=[validators.required()])
    password = fields.PasswordField('Password', validators=[validators.required()])

    def validate_zid(self, field):
        user = self.get_user()

        if user is None:
            raise validators.ValidationError('Invalid zID/password')

        user_data = ldap_service.authenticate(self.zid.data, self.password.data)
        if not user_data:
            raise validators.ValidationError('Invalid zID/password')

        # set user data
        user.first_name = user_data['first_name']
        user.last_name = user_data['last_name']
        db.session.commit()

    def get_user(self):
        return db.session.query(User).filter_by(zid=self.zid.data).first()


def init_login():
    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(zid):
        return db.session.query(User).get(zid)


class AdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if not current_user.is_authenticated():
            return redirect(url_for('.login_view'))
        return super(AdminIndexView, self).index()

    @expose('/login/', methods=('GET', 'POST'))
    def login_view(self):
        form = LoginForm(request.form)
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


class ReportsView(BaseView):
    def is_accessible(self):
        return current_user.is_authenticated()

    @expose('/')
    def index(self):
        events = Event.query.order_by(Event.start.desc())
        return self.render('admin/reports.html', events=events)

    @expose('/csv', methods=['POST'])
    def csv(self):
        event_id = request.form['event']
        event = Event.query.filter(Event.id == event_id).first()

        if event:
            # output CSV
            output = StringIO.StringIO()
            writer = csv.DictWriter(output, ['name', 'zid', 'is_arc', 'time'])
            writer.writeheader()

            results = CheckIn.query.filter(CheckIn.event == event).all()
            for check_in in results:
                if check_in.student:
                    writer.writerow({
                        'name': check_in.student.given_names + ' ' + check_in.student.surname,
                        'zid': check_in.student.zid,
                        'time': check_in.timestamp.isoformat(),
                        'is_arc': check_in.student.is_arc
                    })

            filename = re.sub(r'[^a-z0-9_]', '', event.name.replace(' ', '_').lower())
            filename = 'bark_' + filename + '.csv'

            headers = {'Content-Disposition': 'attachment; filename=' + filename}

            return Response(output.getvalue(), mimetype='text/csv', headers=headers)
        else:
            return 'u wot m8'


DEFAULT_FORMATTERS = dict(typefmt.BASE_FORMATTERS)
DEFAULT_FORMATTERS.update({
    datetime: lambda v, d: d.strftime('%I:%M%p %d/%m/%Y'),
})


class UsersView(ModelView):
    column_labels = {
        'zid': 'zID'
    }

    def is_accessible(self):
        return current_user.is_authenticated()

    def __init__(self, session, **kwargs):
        super(UsersView, self).__init__(User, session, **kwargs)


class QRCodeWidget(object):
    def __call__(self, field, **kwargs):
        if 'value' not in kwargs:
            kwargs['value'] = field._value()

        if kwargs['value']:
            img = qrcode.make(kwargs['value'])
            output = StringIO.StringIO()
            img.save(output, 'PNG')
            data = output.getvalue()
            output.close()

            uri = 'data:image/gif;base64,%s' % base64.b64encode(data)

            img_str = '<img src="%s">' % uri
            caption_str = '<br>Data: "' + kwargs['value'] + '"'

            return HTMLString(img_str + caption_str)

        return HTMLString('<i>(Will be displayed after event is created)</i>')


class QRCodeField(fields.Field):
    widget = QRCodeWidget()

    # def __init__(self):
    #    self.data = ''

    def process_formdata(self, valuelist):
        if not self.data:
            self.data = generate_token()

    def _value(self):
        return self.data


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


class CategoriesView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated()

    def __init__(self, session, **kwargs):
        super(CategoriesView, self).__init__(Category, session, **kwargs)


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


init_login()

admin = Admin(app, name='Bark', index_view=AdminIndexView(), base_template='master.html')
admin.add_view(ReportsView(name='Reports'))
# admin.add_view(MyView(name='Hello'))
# admin.add_view(ModelView(User, db.session))
admin.add_view(EventsView(db.session, name='Events'))
admin.add_view(StudentsView(db.session, name='Students'))
admin.add_view(DegreesView(db.session, name='Degrees'))
admin.add_view(CoursesView(db.session, name='Courses'))
admin.add_view(EnrolmentsView(db.session, name='Enrolments'))
admin.add_view(CheckInsView(db.session, name='Check-ins'))
admin.add_view(UsersView(db.session, name='Users'))
admin.add_view(CategoriesView(db.session, name='Categories'))


@app.route('/')
def root():
    return redirect('/admin/')


@app.route('/download')
def download():
    return redirect(config.ANDROID_URL)


# -- API stuff
class BarkError(Exception):
    pass


@app.route('/api', methods=['POST'])
def api():
    success = True
    error = None

    resp = {}

    try:
        data = request.json

        if data is None:
            raise BarkError('You screwed up the JSON badly')

        if type(data) is not dict:
            raise BarkError('You screwed up the JSON')

        if 'token' not in data:
            raise BarkError('Token is missing')
        token = data['token']

        # check token against events
        results = Event.query.filter(Event.token == token).all()
        if len(results):
            # woo, match
            event = results[0]
        else:
            raise BarkError('Invalid token')

        # check if event is currently running
        now = datetime.now()
        running = (event.start - config.EVENT_LEEWAY <= now and now <= event.end + config.EVENT_LEEWAY)

        # check action
        if 'action' not in data:
            raise BarkError('Action is missing')
        action = data['action']

        if action == 'check_in':
            # event must be running
            if not running:
                raise BarkError('Event is not currently running')

            # check zid
            zid = data['zid']
            if not validate_zid(zid):
                raise BarkError('zID is not valid')

            max_scans = data['max_scans']
            if type(max_scans) is not int or max_scans < 1:
                raise BarkError('Max scans is not valid')

            user_info = udb_service.get_user(zid)

            if user_info:
                results = Student.query.filter(Student.zid == zid).all()
                if len(results):
                    # student exists in the system
                    student = results[0]
                else:
                    # student doesn't exist in the system
                    student = Student()
                    student.zid = zid
                    student.given_names = user_info['given_names']
                    student.surname = user_info['surname']
            else:
                # student doesn't exist in UDB
                student = Student()
                student.zid = zid
                student.given_names = 'Unknown'
                student.surname = 'Student'

            # look up check-in
            check_in = CheckIn.query.filter(CheckIn.student == student).filter(CheckIn.event == event).first()
            if check_in:
                # check-in already exists
                if check_in.number_of_scans + 1 > max_scans:
                    if check_in.number_of_scans == 1:
                        s = 'once'
                    elif check_in.number_of_scans == 2:
                        s = 'twice'
                    else:
                        s = '%d times' % check_in.number_of_scans

                    raise BarkError('Student has already checked in ' + s)

                check_in.number_of_scans += 1
            else:
                # check-in doesn't exist
                check_in = CheckIn()
                check_in.student = student
                check_in.event = event

                if user_info and len(user_info['degrees']):
                    degree_info = max(user_info['degrees'], key=lambda deg: deg['expiry'])
                else:
                    # no degree. might be doing COMP as a gened or something
                    degree_info = {'code': 0, 'expiry': datetime.fromtimestamp(0).date()}

                courses_info = user_info['courses'] if user_info else []

                expiry = datetime.fromtimestamp(0).date()  # max(expiry of all degrees & courses)

                # handle degree
                results = Degree.query.filter(Degree.code == degree_info['code']).all()
                if len(results):
                    # degree exists
                    degree = results[0]
                else:
                    # degree doesn't exist
                    degree = Degree()
                    degree.code = degree_info['code']
                    degree.name = degree_name(degree_info['code'])
                    degree.is_cse = True  # TODO: wat

                expiry = max(expiry, degree_info['expiry'])

                check_in.degree = degree

                # handle courses
                for course_info in courses_info:
                    results = Course.query.filter(Course.code == course_info['code']).all()
                    if len(results):
                        # course exists
                        course = results[0]
                    else:
                        # course doesn't exist
                        course = Course()
                        course.code = course_info['code']
                        course.name = course_name(course_info['code'])

                    expiry = max(expiry, course_info['expiry'])

                    # create enrolment entry
                    enrolment = Enrolment()
                    enrolment.check_in = check_in
                    enrolment.course = course

                if expiry > datetime.now().date() or student.override_cse:
                    check_in.is_cse = True
                else:
                    check_in.is_cse = False

            resp['name'] = '%s %s' % (student.given_names, student.surname)
            resp['num_scans'] = check_in.number_of_scans
            resp['is_arc'] = student.is_arc
            resp['is_cse'] = check_in.is_cse

            resp['degree'] = unicode(check_in.degree)
            if student.override_cse:
                resp['degree'] += ' (Overridden)'

            courses = []
            for enrolment in check_in.enrolments:
                courses.append(unicode(enrolment.course))
            resp['courses'] = courses

            if not check_in.is_cse and event.check_cse:
                # discard the check in and student details
                db.session.expunge(check_in)
                db.session.expunge(student)
            db.session.commit()
        elif action == 'update_arc':
            # event must be running
            if not running:
                raise BarkError('Event is not currently running')

            # check zid
            zid = data['zid']
            if not validate_zid(zid):
                raise BarkError('zID is not valid')

            if not 'is_arc' in data:
                raise BarkError('is_arc is missing')

            is_arc = data['is_arc']
            if type(is_arc) is not bool:
                raise BarkError('is_arc should be a boolean')

            results = Student.query.filter(Student.zid == zid).all()
            if len(results):
                # student exists in the system
                student = results[0]

                student.is_arc = is_arc

                db.session.commit()
            else:
                raise BarkError('Student has not checked in before')
        elif action == 'get_event_info':
            resp['name'] = event.name
            resp['location'] = event.location
            resp['start_time'] = time.mktime(event.start.timetuple())
            resp['end_time'] = time.mktime(event.end.timetuple())
            resp['running'] = running
        else:
            raise BarkError('Invalid action')

    except BarkError as e:
        success = False
        error = e.message
    except IOError as e:
        success = False
        error = e.message

    if not success:
        resp = {}
    if error:
        resp['error'] = error
    resp['success'] = success

    return json.dumps(resp)
