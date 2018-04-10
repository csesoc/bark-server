from flask.views import MethodView
from flask import redirect

class AdminRedirectView(MethodView):
    def get(self):
        return redirect('/admin/')
