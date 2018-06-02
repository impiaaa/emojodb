from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from flask import Flask
from flask_apscheduler import APScheduler
from flask_sqlalchemy import SQLAlchemy
from flask_uploads import UploadSet, configure_uploads, IMAGES

app = Flask("emojodb")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['UPLOADED_PHOTOS_DEST'] = 'emojodb'
app.config['SCHEDULER_API_ENABLED'] = True
app.config['SCHEDULER_JOBSTORES'] = {
    'default': SQLAlchemyJobStore(url='sqlite:///flask_context.db')
}

def refresh_all_instances():
	from models import Instance
	from instance_import import import_instance
	with db.app.app_context():
		for instance in Instance.query.all():
			try: import_instance(instance.uri)
			except Exception as e: print(e)

app.config['JOBS'] = [
	{
		'id': 'refresh_all_instances',
		'func': refresh_all_instances,
		'trigger': 'interval',
		'days': 1
	}
]

db = SQLAlchemy(app)

uploaded_photos = UploadSet('photos', IMAGES)
configure_uploads(app, uploaded_photos)

@app.before_first_request
def init():
	scheduler = APScheduler()
	scheduler.init_app(app)
	scheduler.start()

import routes
from instance_import import import_instance
