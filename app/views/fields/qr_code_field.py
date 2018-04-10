import StringIO
import base64
import os

import qrcode

from wtforms import fields
from wtforms.widgets import HTMLString


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

    def process_formdata(self, valuelist):
        if not self.data:
            self.data = generate_token()

    def _value(self):
        return self.data


def generate_token():
    b = os.urandom(32)
    s = b.encode('hex')
    return s
