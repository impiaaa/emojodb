import click, imagehash, json, os, tempfile
from app import app, db, uploaded_photos
from models import Emoji, Instance, HASH_LENGTH, instanceHasEmoji
from PIL import Image
from urllib.request import urlopen
from urllib.parse import urlparse
from werkzeug.datastructures import FileStorage
from datetime import datetime

def getjson(uri, method):
    with urlopen('https://{}/api/v1/{}'.format(uri, method)) as doc:
        contenttype = doc.info()['content-type'].split(';')
        assert contenttype[0] == 'application/json'
        params = dict([s.strip().casefold().split('=') for s in contenttype[1:]])
        codec = params['charset']
        return json.loads(doc.read().decode(codec))

@app.cli.command()
@click.argument("uri")
def import_instance(uri):
    print("Getting information on {}".format(uri))
    instancedata = getjson(uri, 'instance')
    
    instance = Instance.query.filter_by(uri=uri).first()
    if instance is None:
        instance = Instance()
        print("Adding instance to DB")
        db.session.add(instance)
    for k, v in instancedata.items():
        setattr(instance, k, v)
    
    print("Set instance info, loading emoji")
    
    addedEmoji = []
    
    for emojidata in getjson(uri, 'custom_emojis'):
        print("Loading :{}:".format(emojidata['shortcode']))
        with urlopen(emojidata['url']) as doc:
            headers = doc.info()
            basename = urlparse(emojidata['url']).path
            basename = basename[basename.rfind('/')+1:]
            
            tmp = tempfile.TemporaryFile('wb+')
            tmp.write(doc.read())
            tmp.seek(0)
            
            storage = FileStorage(tmp, basename, headers=headers)
            filename = uploaded_photos.save(storage)
        fullpath = os.path.join(uploaded_photos.config.destination, filename)
        hash = imagehash.average_hash(Image.open(fullpath), hash_size=HASH_LENGTH).hash
        
        emoji = Emoji.query.filter_by(shortcode=emojidata['shortcode'], hash=hash).first()
        if emoji is None:
            # TODO: Emoji with the same image hash should use the same file
            print("Adding emoji to DB")
            emoji = Emoji(shortcode=emojidata['shortcode'], hash=hash, filename=filename)
            db.session.add(emoji)
        else:
            os.remove(fullpath)
        
        db.session.flush()
        
        if emoji in instance.emoji:
            # TODO: changes to "hidden" should update last_touched
            a = instanceHasEmoji.update().where(instanceHasEmoji.c.emoji_id==emoji.id and instanceHasEmoji.c.instance_id==instance.id).values(hidden=not emojidata['visible_in_picker'])
        else:
            print("Adding emoji to instance")
            a = instanceHasEmoji.insert().values(emoji_id=emoji.id,
                                                 instance_id=instance.id,
                                                 hidden=not emojidata['visible_in_picker'],
                                                 last_touched=datetime.now())
        db.session.execute(a)
        
        addedEmoji.append(emoji)
    
    for emoji in instance.emoji:
        if emoji not in addedEmoji:
            print("Removing :{}:".format(emoji.shortcode))
            db.session.delete(emoji)
    
    db.session.commit()

