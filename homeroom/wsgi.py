import os
import json
import threading
import time

from flask import Flask
from flask import render_template

from kubernetes.client.rest import ApiException
from kubernetes.client.configuration import Configuration
from kubernetes.config.incluster_config import load_incluster_config
from kubernetes.client.api_client import ApiClient
from openshift.dynamic import DynamicClient

# Work out namespace operating in.

service_account_path = '/var/run/secrets/kubernetes.io/serviceaccount'

with open(os.path.join(service_account_path, 'namespace')) as fp:
    namespace = fp.read().strip()

# Setup REST API client access.

load_incluster_config()

import urllib3
urllib3.disable_warnings()
instance = Configuration()
instance.verify_ssl = False
Configuration.set_default(instance)

api_client = DynamicClient(ApiClient())

route_resource = api_client.resources.get(
        api_version='route.openshift.io/v1', kind='Route')

# Setup loading or workshops or live monitor.

workshops = []

application_name = os.environ.get('APPLICATION_NAME')

def filter_out_hidden(workshops):
    for workshop in workshops:
        if workshop.get('visibility', 'visible') != 'hidden':
            yield workshop

def lookup_route_host(name):
    route = route_resource.get(namespace=namespace, name=name)

    scheme = 'http'

    if route.tls and route.tls.termination:
        scheme = 'https'

    return '%s://%s' % (scheme, route.spec.host)

def monitor_workshops():
    global workshops

    while True:
        active_workshops = []

        try:
            routes = route_resource.get(namespace=namespace)

            for route in routes.items:
                annotations = route.metadata.annotations
                if annotations:
                    if annotations.get('homeroom/group') == application_name:
                        name = route.metadata.name
                        title = annotations.get('homeroom/title') or name
                        description = annotations.get('homeroom/description') or ''

                        scheme = 'http'
                        if route.tls and route.tls.termination:
                            scheme = 'https'

                        url = '%s://%s' % (scheme, route.spec.host)

                        active_workshops.append(dict(title=title,
                                description=description, url=url))

            if workshops != active_workshops:
                workshops[:] = active_workshops
                print('WORKSHOPS', workshops)

        except ApiException as e:
            print('ERROR: Error looking up routes. %s' % e)

        except Exception as e:
            print('ERROR: Error looking up routes. %s' % e)

        time.sleep(15)

if os.path.exists('/opt/app-root/configs/workshops.json'):
    with open('/opt/app-root/configs/workshops.json') as fp:
        workshops = list(filter_out_hidden(json.load(fp)))

if not workshops:
    monitor_thread = threading.Thread(target=monitor_workshops)
    monitor_thread.daemon = True
    monitor_thread.start()

# Setup the Flask application.

app = Flask(__name__)

banner_images = {
    'homeroom': 'homeroom-logo.png',
    'openshift': 'openshift-logo.svg',
    'dedicated': 'openshift-dedicated-logo.svg',
    'okd': 'okd-logo.svg',
} 

@app.route('/')
def index():
    title = os.environ.get('HOMEROOM_TITLE', 'Workshops')
    branding = os.environ.get('HOMEROOM_BRANDING', 'openshift')
    banner_image = banner_images.get(branding, banner_images['openshift'])

    visible_workshops = list(filter_out_hidden(workshops))

    return render_template('workshops.html', title=title,
            banner_image=banner_image, workshops=visible_workshops)
