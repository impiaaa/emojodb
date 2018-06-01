from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_uploads import UploadSet, configure_uploads, IMAGES

app = Flask("emojodb")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['UPLOADED_PHOTOS_DEST'] = 'emojodb'

db = SQLAlchemy(app)

uploaded_photos = UploadSet('photos', IMAGES)
configure_uploads(app, uploaded_photos)

import routes
from instance_import import import_instance

