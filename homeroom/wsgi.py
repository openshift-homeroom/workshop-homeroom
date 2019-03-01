import os
import json

from flask import Flask
from flask import render_template

app = Flask(__name__)

workshops = []

if os.path.exists('/opt/app-root/configs/workshops.json'):
    with open('/opt/app-root/configs/workshops.json') as fp:
        workshops = json.load(fp)

if not workshops:
    for i in range(10):
        workshops.append(dict(title='Workshop #%s'%i,
            description='This is workshop #%s.'%i, url='http://www.example.com'))

@app.route('/')
def index():
    return render_template('workshops.html', workshops=workshops)
