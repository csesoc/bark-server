from flask.views import MethodView
from flask import redirect


class AppDownloadView(MethodView):
    def __init__(self, android_url):
        self._android_url = android_url

    def get(self):
        return redirect(self._android_url)
