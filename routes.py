import jinja2
from app import app
from bleach import clean
from flask import abort, redirect, render_template, request, url_for
from models import Instance, Emoji

def sanitize_html(text):
    return jinja2.Markup(scrubber.Scrubber().scrub(text))

app.jinja_env.filters['clean'] = lambda text: jinja2.Markup(clean(text))
app.jinja_env.filters['strip'] = lambda text: jinja2.Markup(clean(text, strip=True))

@app.route('/')
def index():
    instances = Instance.query.all()
    return render_template('index.html', instances=instances)

@app.route('/instance/<instance>')
def instancesearch(instance):
    instance = Instance.query.filter_by(uri=instance).first()
    if instance is None: abort(404)
    return render_template('instance.html', instance=instance)

@app.route('/instance', methods=['POST'])
def instanceredir():
    return redirect(url_for('instancesearch', instance=request.form['instance']))

@app.route('/emoji/<int:id>')
def emoji(id):
    emoji = Emoji.query.filter_by(id=id).first()
    if emoji is None: abort(404)
    return render_template('emoji.html', emoji=emoji)

