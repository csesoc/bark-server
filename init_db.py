from app import create_app
from app.db import Degree, User, db
from config import Development

config = Development()
app = create_app(config)
db.create_all()

username = raw_input('Initial user to add (zID): ')
user = User()
user.zid = username
db.session.add(user)

degree = Degree()
degree.code = 0
degree.name = 'Unknown'

db.session.commit()
