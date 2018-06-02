from app import db, uploaded_photos

HASH_LENGTH = 8

instanceHasEmoji = db.Table('instanceHasEmoji',
    db.Column('emoji_id', db.Integer, db.ForeignKey('emoji.id'), primary_key=True),
    db.Column('instance_id', db.Integer, db.ForeignKey('instance.id'), primary_key=True),
    db.Column('hidden', db.Boolean),
    db.Column('last_touched', db.DateTime)
)

class Emoji(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shortcode = db.Column(db.String, nullable=False, index=True)
    hash = db.Column(db.LargeBinary(length=HASH_LENGTH), nullable=False)
    filename = db.Column(db.String)
    
    __table_args__ = (db.UniqueConstraint('shortcode', 'hash'),)
    
    @property
    def imgsrc(self):
        return uploaded_photos.url(self.filename)

class Instance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uri = db.Column(db.String(length=100), unique=True, nullable=False, index=True)
    title = db.Column(db.String(length=80))
    description = db.Column(db.String)
    email = db.Column(db.String(length=80))
    version = db.Column(db.String(length=10))
    thumbnail = db.Column(db.String(length=200))
    
    emoji = db.relationship('Emoji', secondary=instanceHasEmoji, lazy='select', backref=db.backref('instances', lazy=True, order_by='Instance.uri'), order_by='Emoji.shortcode')

