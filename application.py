from flask import Flask
from flask_apscheduler import APScheduler
from flask_sqlalchemy import SQLAlchemy

application = Flask(__name__)
application.config.from_object('config')

def refresh_all_instances():
	from models import Instance
	from instance_import import getInstanceEmoji, getInstanceInfo, startGetInstanceEmojiTask
	with db.app.app_context():
		for instance in Instance.query.all():
			if instance.pending: startGetInstanceEmojiTask(instance.uri)
			else:
				try: getInstanceEmoji(getInstanceInfo(instance.uri))
				except Exception as e: print(e)

application.config['JOBS'] = [
	{
		'id': 'refresh_all_instances',
		'func': refresh_all_instances,
		'trigger': 'interval',
		'days': 1,
		'replace_existing': True,
		'max_instances': 1
	}
]

db = SQLAlchemy(application)

scheduler = APScheduler()
scheduler.init_app(application)

@application.before_first_request
def init():
	db.create_all()
	scheduler.start()

app = application





import boto3
from sqlalchemy.orm import validates

HASH_LENGTH = 32

instanceHasEmoji = db.Table('instanceHasEmoji',
    db.Column('emoji_id', db.Integer, db.ForeignKey('emoji.id'), primary_key=True),
    db.Column('instance_id', db.Integer, db.ForeignKey('instance.id'), primary_key=True),
    db.Column('hidden', db.Boolean),
    db.Column('last_touched', db.DateTime)
)

s3 = boto3.client('s3')

class Emoji(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shortcode = db.Column(db.String(length=80), nullable=False, index=True)
    hash = db.Column(db.LargeBinary(length=HASH_LENGTH), nullable=False)
    filename = db.Column(db.String)
    
    __table_args__ = (db.UniqueConstraint('shortcode', 'hash'),)
    
    @property
    def imgsrc(self):
        return s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': app.config['S3_BUCKET'],
                'Key': self.filename
            }
        )
	
    @validates('shortcode')
    def validate_code(self, key, value):
        max_len = getattr(self.__class__, key).prop.columns[0].type.length
        if value and len(value) > max_len:
            return value[:max_len]
        return value

class Instance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uri = db.Column(db.String(length=100), unique=True, nullable=False, index=True)
    title = db.Column(db.String(length=80))
    description = db.Column(db.String(length=1000))
    email = db.Column(db.String(length=80))
    version = db.Column(db.String(length=10))
    thumbnail = db.Column(db.String(length=200))
    pending = db.Column(db.Boolean)
    
    emoji = db.relationship('Emoji', secondary=instanceHasEmoji, lazy='select', backref=db.backref('instances', lazy=True, order_by='Instance.uri'), order_by='Emoji.shortcode')

    @validates('uri', 'title', 'description', 'email', 'version', 'thumbnail')
    def validate_code(self, key, value):
        max_len = getattr(self.__class__, key).prop.columns[0].type.length
        if value and len(value) > max_len:
            return value[:max_len]
        return value


import jinja2, re
from bleach import clean
from flask import abort, redirect, render_template, request, url_for
from sqlalchemy import text

def sanitize_html(text):
    return jinja2.Markup(scrubber.Scrubber().scrub(text))

app.jinja_env.filters['clean'] = lambda text: jinja2.Markup(clean(text))
app.jinja_env.filters['strip'] = lambda text: jinja2.Markup(clean(text, strip=True))

@app.route('/')
def index():
    return render_template('index.html')

domainNameDisallowed = re.compile(u"[\x00-,/:-@[-`{-\x7f]", flags=re.UNICODE)

@app.route('/instance/<uri>')
def instancesearch(uri):
    uri = domainNameDisallowed.sub("", uri.lower())
    instance = Instance.query.filter_by(uri=uri).first()
    if instance is None:
        from instance_import import getInstanceInfo
        try:
            instance = getInstanceInfo(uri)
        except Exception as e:
            print(e)
            abort(404)
    if instance.pending:
        from instance_import import startGetInstanceEmojiTask
        startGetInstanceEmojiTask(instance.uri)
    return render_template('instance.html', instance=instance)

@app.route('/instance', methods=['POST'])
def instanceredir():
    return redirect(url_for('instancesearch', uri=request.form['instance']))

@app.route('/emoji/<int:id>')
def emoji(id):
    emoji = Emoji.query.filter_by(id=id).first()
    if emoji is None: abort(404)
    similar = Emoji.query\
                   .filter(Emoji.hash == emoji.hash)\
                   .filter(Emoji.id != id)\
                   .order_by(Emoji.shortcode)\
                   .all()
    return render_template('emoji.html', emoji=emoji, similar=similar)

@app.route('/emoji')
def emojisearch():
    emoji = db.session.query(Emoji)\
                      .filter(Emoji.shortcode.ilike(text("'%' || :query || '%'"))).params(query=request.args['query'])\
                      .order_by(Emoji.shortcode)\
                      .limit(100)\
                      .all()
    if len(emoji) == 1: return redirect(url_for('emoji', id=emoji[0].id))
    else: return render_template('emojisearch.html', emoji=emoji, shortcode=request.args['query'])

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404






import instance_import

if __name__ == '__main__':
	application.debug = True
	application.run()
