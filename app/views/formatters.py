from flask_admin.model import typefmt
from datetime import datetime

DEFAULT_FORMATTERS = dict(typefmt.BASE_FORMATTERS)
DEFAULT_FORMATTERS.update({
    datetime: lambda v, d: d.strftime('%I:%M%p %d/%m/%Y'),
})
