# coding=utf-8

""" Uses Bioblend to connect to Galaxy instances and stores data about tools in a MongoDB database """

import requests

from bioblend.galaxy import GalaxyInstance
from bioblend.galaxy.tools import ToolClient
from datetime import datetime
from galaxycat.config import config
from mongoengine import connect
from mongoengine import Document
from mongoengine import BooleanField, DateTimeField, FloatField, ListField, ReferenceField, StringField
from mongoengine.queryset.visitor import Q
from urlparse import urlparse

connect(db=config['MONGODB_DB'], host=config['MONGODB_HOST'], port=config['MONGODB_PORT'])


class Instance(Document):

    url = StringField(required=True, unique=True)
    creation_date = DateTimeField(required=True, default=datetime.now)
    update_date = DateTimeField()
    allow_user_creation = BooleanField()
    brand = StringField()
    enable_quotas = BooleanField()
    require_login = BooleanField()
    terms_url = StringField()
    version = StringField()
    city = StringField()
    zipcode = StringField()
    country = StringField()
    country_code = StringField()
    latitude = FloatField()
    longitude = FloatField()
    meta = {'collection': 'instances'}

    # {
    #     "as":"AS2259 UNIVERSITE DE STRASBOURG",
    #     "city":"Strasbourg",
    #     "country":"France",
    #     "countryCode":"FR",
    #     "isp":"Universite De Strasbourg",
    #     "lat":48.6004,
    #     "lon":7.7874,
    #     "org":"Universite De Strasbourg",
    #     "query":"130.79.78.25",
    #     "region":"GES",
    #     "regionName":"Grand-Est",
    #     "status":"success",
    #     "timezone":"Europe/Paris",
    #     "zip":"67000"
    # }

    @classmethod
    def add_instance(cls, url):
        try:
            instance = Instance.objects.get(url=url)
        except Instance.DoesNotExist:
            instance = Instance(url=url)

        galaxy_instance = GalaxyInstance(url=url)
        instance_config = galaxy_instance.config.get_config()

        instance.update_date = datetime.now()
        instance.allow_user_creation = instance_config['allow_user_creation']
        instance.brand = instance_config['brand']
        instance.enable_quotas = 'enable_quotas' in instance_config and instance_config['enable_quotas']
        instance.require_login = instance_config['require_login']
        instance.terms_url = instance_config['terms_url']
        instance.version = instance_config['version_major']

        url_data = urlparse(url)
        instance_location = requests.get('http://ip-api.com/json/%s' % url_data.netloc)
        instance_location = instance_location.json()
        instance.city = instance_location['city']
        instance.zipcode = instance_location['zip']
        instance.country = instance_location['country']
        instance.country_code = instance_location['countryCode']
        instance.latitude = instance_location['lat']
        instance.longitude = instance_location['lon']

        instance.save()

        Tool.retrieve_tools_from_instance(instance=instance)

    def get_tools_count(self):
        tool_versions = ToolVersion.objects(instances=self)
        seen = set()
        unique_tool = [tool_version for tool_version in tool_versions if not (tool_version.name in seen or seen.add(tool_version.name))]
        return len(unique_tool)

    @property
    def location(self):
        if self.city is not None and self.country is not None:
            return "%s, %s" % (self.city, self.country)
        else:
            return "Unknown"


class ToolVersion(Document):

    name = StringField(required=True)
    version = StringField(required=True)
    tool_shed = StringField(required=False)
    owner = StringField(required=False)
    changeset = StringField(required=False)
    instances = ListField(ReferenceField(Instance))


class Tool(Document):

    name = StringField(required=True, unique=True)
    description = StringField()
    display_name = StringField()
    versions = ListField(ReferenceField(ToolVersion))
    meta = {'collection': 'tools'}

    @classmethod
    def retrieve_tools_from_instance(cls, instance):

        galaxy_instance = GalaxyInstance(url=instance.url)
        tool_client = ToolClient(galaxy_instance)
        for element in tool_client.get_tools():
            if element['model_class'] == 'Tool':
                tool_name = element['id']
                if '/' in tool_name:
                    tool_name = tool_name.split('/')[-2]

                try:
                    tool = Tool.objects.get(name=tool_name)
                except Tool.DoesNotExist:
                    tool = Tool(name=tool_name)

                tool.description = element['description']
                tool.display_name = element['name']

                try:
                    if 'tool_shed_repository' in element:
                        tool_version = ToolVersion.objects.get(name=tool_name,
                                                               changeset=element['tool_shed_repository']['changeset_revision'],
                                                               tool_shed=element['tool_shed_repository']['tool_shed'],
                                                               owner=element['tool_shed_repository']['owner'])
                    else:
                        tool_version = ToolVersion.objects.get(name=tool_name,
                                                               version=element['version'],
                                                               tool_shed=None,
                                                               owner=None)
                except ToolVersion.DoesNotExist:
                    tool_version = ToolVersion(name=tool_name,
                                               version=element['version'])

                if 'tool_shed_repository' in element:
                    tool_version.changeset = element['tool_shed_repository']['changeset_revision']
                    tool_version.tool_shed = element['tool_shed_repository']['tool_shed']
                    tool_version.owner = element['tool_shed_repository']['owner']

                if instance not in tool_version.instances:
                    tool_version.instances.append(instance)

                tool_version.save()

                if tool_version not in tool.versions:
                    tool.versions.append(tool_version)

                tool.save()

    @classmethod
    def search(cls, search):
        q = None
        for term in search.split(' '):
            q_part = (Q(name__icontains=term) | Q(description__icontains=term) | Q(display_name__icontains=term))
            if q is None:
                q = q_part
            else:
                q = q & q_part

        return Tool.objects(q)

    @classmethod
    def update_catalog(cls):

        # delete all Tool and ToolVersion documents
        ToolVersion.objects().delete()
        Tool.objects().delete()

        for instance in Instance.objects():
            Instance.add_instance(url=instance.url)
