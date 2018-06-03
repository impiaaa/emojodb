import jinja2, re
from app import app, db
from bleach import clean
from flask import abort, redirect, render_template, request, url_for
from models import Instance, Emoji
from sqlalchemy import text

def sanitize_html(text):
    return jinja2.Markup(scrubber.Scrubber().scrub(text))

app.jinja_env.filters['clean'] = lambda text: jinja2.Markup(clean(text))
app.jinja_env.filters['strip'] = lambda text: jinja2.Markup(clean(text, strip=True))

@app.route('/')
def index():
    instances = Instance.query.all()
    return render_template('index.html', instances=instances)

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
