import json
import re
import time
from datetime import datetime

import requests
from flask import request
from flask.views import MethodView

from app.db import Event, Student, CheckIn, Degree, Course, Enrolment, db


class BarkError(Exception):
    pass


class ApiView(MethodView):
    def __init__(self, udb_service, event_leeway):
        self._event_leeway = event_leeway
        self._udb_service = udb_service

    def post(self):
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
            running = (event.start - self._event_leeway <= now and now <= event.end + self._event_leeway)

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

                user_info = self._udb_service.get_user(zid)

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


def validate_zid(zid):
    return re.match(r'^z[0-9]{7}$', zid) is not None


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
