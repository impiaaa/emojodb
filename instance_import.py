import apscheduler, boto3, click, imagehash, json, os, tempfile
from app import app, db
from datetime import datetime
from models import Emoji, Instance, HASH_LENGTH, instanceHasEmoji
from PIL import Image
from urllib.error import URLError
from urllib.request import urlopen
from urllib.parse import urlparse
from uuid import uuid4
from werkzeug.utils import secure_filename

def getjson(uri, method):
    assert uri.islower()
    with urlopen('https://{}/api/v1/{}'.format(uri, method)) as doc:
        contenttype = doc.info()['content-type'].split(';')
        assert contenttype[0] == 'application/json'
        params = dict([s.strip().casefold().split('=') for s in contenttype[1:]])
        codec = params['charset']
        return json.loads(doc.read().decode(codec))

def getInstanceInfo(uri):
    print("Getting information on {}".format(uri))
    instancedata = getjson(uri, 'instance')
    
    instance = Instance.query.filter_by(uri=uri).first()
    if instance is None:
        instance = Instance(pending=True)
        print("Adding instance to DB")
        db.session.add(instance)
    for k, v in instancedata.items():
        setattr(instance, k, v)
    
    db.session.commit()
    
    return instance

@app.cli.command()
@click.argument("uri")
def import_instance(uri):
    getInstanceEmoji(getInstanceInfo(uri))

rgb2xyz = (
    0.412453, 0.357580, 0.180423, 0,
    0.212671, 0.715160, 0.072169, 0,
    0.019334, 0.119193, 0.950227, 0 )

def process(im):
    im = im.convert('RGBA')
    rgb, alpha = im.convert('RGB'), im.getchannel('A')
    xyz = rgb.convert('RGB', rgb2xyz)
    channels = xyz.split()+(alpha,)
    im2 = Image.new('L', tuple(w*2 for w in im.size))
    for i, c in enumerate(channels):
        im2.paste(c, box=(im.size[0]*(i%2), im.size[1]*(i//2)))
    return im2

def gethash(fname):
    return imagehash.whash(process(Image.open(fname)), hash_size=HASH_LENGTH).hash

def getInstanceEmoji(instanceOrUri):
    if isinstance(instanceOrUri, Instance):
        instance = instanceOrUri
    else:
        instance = Instance.query.filter_by(uri=instanceOrUri).first()
    print("Loading emoji for {}".format(instance.uri))
    
    addedEmoji = []
    
    s3 = boto3.client('s3')
    
    for emojidata in getjson(instance.uri, 'custom_emojis'):
        print("Loading :{}:".format(emojidata['shortcode']))
        with tempfile.TemporaryFile('wb+') as tmp:
            try:
                with urlopen(emojidata['url']) as doc:
                    headers = doc.info()
                    tmp.write(doc.read())
            except URLError as e:
                print(e)
                continue
            
            tmp.seek(0)
            hash = gethash(tmp)
        
            emoji = Emoji.query.filter_by(shortcode=emojidata['shortcode'], hash=hash).first()
            if emoji is None:
                urlpath = urlparse(emojidata['url']).path
                basename = urlpath[urlpath.rfind('/')+1:]
                source_filename = secure_filename(basename)
                source_extension = os.path.splitext(source_filename)[1]
                filename = uuid4().hex + source_extension
                
                # TODO: Emoji with the same image hash should use the same file
                tmp.seek(0)
                print("Uploading :{emoji}: as {file}".format(emoji=emojidata['shortcode'], file=filename))
                s3.upload_fileobj(tmp, app.config['S3_BUCKET'], filename)
                
                emoji = Emoji(shortcode=emojidata['shortcode'], hash=hash, filename=filename)
                print("Adding :{}: to DB".format(emojidata['shortcode']))
                db.session.add(emoji)
        
        db.session.flush()
        
        if emoji in instance.emoji:
            # TODO: changes to "hidden" should update last_touched
            a = instanceHasEmoji.update().where(instanceHasEmoji.c.emoji_id==emoji.id and instanceHasEmoji.c.instance_id==instance.id).values(hidden=not emojidata['visible_in_picker'])
        else:
            print("Adding :{emoji}: to {instance}".format(emoji=emoji.shortcode, instance=instance.uri))
            a = instanceHasEmoji.insert().values(emoji_id=emoji.id,
                                                 instance_id=instance.id,
                                                 hidden=not emojidata['visible_in_picker'],
                                                 last_touched=datetime.now())
        db.session.execute(a)
        
        addedEmoji.append(emoji)
    
    for emoji in instance.emoji:
        if emoji not in addedEmoji:
            print("Removing :{emoji}: from {instance}".format(emoji=emoji.shortcode, instance=instance.uri))
            instanceHasEmoji.delete().where(emoji_id=emoji.id,
                                            instance_id=instance.id)
    
    print("Done fetching emoji for {}".format(instance.uri))
    
    instance.pending = False
    
    db.session.commit()
    
    return addedEmoji

def getInstanceEmojiWithContext(instance):
    with db.app.app_context():
        getInstanceEmoji(instance)

def startGetInstanceEmojiTask(uri):
    from app import scheduler
    try:
        scheduler.add_job(id='getInstanceEmoji:'+uri,
                          func=getInstanceEmojiWithContext,
                          args=[uri],
                          trigger='date',
                          max_instances=1)
    except apscheduler.jobstores.base.ConflictingIdError:
        pass
