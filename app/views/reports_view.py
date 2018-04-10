import StringIO
import csv
import re

from flask import request, Response
from flask_admin import BaseView, expose
from flask_login import current_user

from app.db import Event, CheckIn


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

