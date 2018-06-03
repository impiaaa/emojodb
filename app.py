from flask import Flask
from flask_apscheduler import APScheduler
from flask_sqlalchemy import SQLAlchemy

app = Flask("emojodb")
app.config.from_object('config')

def refresh_all_instances():
	from models import Instance
	from instance_import import getInstanceEmoji, getInstanceInfo, startGetInstanceEmojiTask
	with db.app.app_context():
		for instance in Instance.query.all():
			if instance.pending: startGetInstanceEmojiTask(instance.uri)
			else:
				try: getInstanceEmoji(getInstanceInfo(instance.uri))
				except Exception as e: print(e)

app.config['JOBS'] = [
	{
		'id': 'refresh_all_instances',
		'func': refresh_all_instances,
		'trigger': 'interval',
		'days': 1,
		'replace_existing': True,
		'max_instances': 1
	}
]

db = SQLAlchemy(app)

scheduler = APScheduler()
scheduler.init_app(app)

@app.before_first_request
def init():
	db.create_all()
	scheduler.start()

import routes
from instance_import import import_instance
