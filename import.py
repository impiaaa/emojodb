from models import Emoji, Instance
from app import db
import json
from urllib.request import urlopen

def importInstance(uri):
    endpoint = "https://{}/api/v1/".format(uri)
    
    doc = urlopen(endpoint+"instance")
    contenttype = doc.info()["content-type"].split(';')
    assert contenttype[0] == "application/json"
    params = dict([s.strip().casefold().split('=') for s in contenttype[1:]])
    codec = params['charset']
    instancedata = json.loads(doc.read().decode(codec))
    doc.close()
    
    instance = Instance.query.filter_by(uri=uri).first()
    if instance is None:
        instance = Instance()
        db.session.add(instance)
    for k, v in instancedata.items():
        setattr(instance, k, v)
    db.session.commit()

if __name__ == '__main__':
    import sys
    importInstance(sys.argv[1])

