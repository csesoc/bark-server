from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


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
