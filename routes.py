from emojodb import app
from models import Instance, Emoji, instanceHasEmoji
from flask import render_template

@app.route('/')
def index():
    instances = Instance.query.all()
    return render_template('index.html', instances=instances)

