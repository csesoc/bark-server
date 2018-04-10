from bark_server import db, User, Degree
db.create_all()

username = raw_input('Initial user to add (zID): ')

user = User()
user.zid = username
db.session.add(user)

degree = Degree()
degree.code = 0
degree.name = 'Unknown'

db.session.commit()
