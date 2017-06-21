# coding=utf-8

""" Uses Bioblend to connect to Galaxy instances and stores data about tools in a MongoDB database """

import requests
import urllib

from bioblend import ConnectionError
from bioblend.galaxy import GalaxyInstance
from bioblend.galaxy.tools import ToolClient
from datetime import datetime
from galaxycat.config import config
from mongoengine import connect
from mongoengine import Document
from mongoengine import BooleanField, DateTimeField, FloatField, ListField, ReferenceField, StringField
from mongoengine.queryset.visitor import Q
from pyparsing import Group, Literal, OneOrMore, QuotedString, Word
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

        try:
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
            try:
                instance_location = requests.get('http://ip-api.com/json/%s' % url_data.netloc)
            except requests.exceptions.ConnectionError:
                print "Unable to get location data for %s" % url_data.netloc
            else:
                try:
                    instance_location = instance_location.json()
                except ValueError:
                    print "Unable to decode location data for %s" % url_data.netloc
                else:
                    instance.city = instance_location['city']
                    instance.zipcode = instance_location['zip']
                    instance.country = instance_location['country']
                    instance.country_code = instance_location['countryCode']
                    instance.latitude = instance_location['lat']
                    instance.longitude = instance_location['lon']

            instance.save()

            Tool.retrieve_tools_from_instance(instance=instance)
        except ConnectionError:
            print "Unable to add or update %s" % url

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


class EDAMOperation(Document):

    operation_id = StringField(required=True)
    iri = StringField(required=True)
    label = StringField(required=True)
    description = StringField(required=False)

    @classmethod
    def get_from_id(cls, operation_id, allow_creation=False):

        try:
            edam_operation = EDAMOperation.objects.get(operation_id=operation_id)
        except EDAMOperation.DoesNotExist:
            edam_operation = None
            if allow_creation:
                iri = 'http://edamontology.org/%s' % operation_id
                api_url = 'http://www.ebi.ac.uk/ols/api/ontologies/edam/terms/%s' % urllib.quote(urllib.quote(iri, safe=''), safe='')
                edam_response = requests.get(api_url)
                if edam_response.status_code == 200:
                    edam_data = edam_response.json()
                    edam_operation = EDAMOperation(operation_id=operation_id,
                                                   iri=iri,
                                                   label=edam_data['label'],
                                                   description=" ".join(edam_data['description']))
                    edam_operation.save()

        return edam_operation


class ToolVersion(Document):

    name = StringField(required=True)
    version = StringField(required=True)
    tool_shed = StringField(required=False)
    owner = StringField(required=False)
    changeset = StringField(required=False)
    # FIXME: we should use EmbeddedDocument to store instance data for each tool version (improve perf)
    instances = ListField(ReferenceField(Instance))


class Tool(Document):

    name = StringField(required=True, unique=True)
    description = StringField()
    display_name = StringField()
    versions = ListField(ReferenceField(ToolVersion))
    edam_operations = ListField(ReferenceField(EDAMOperation))
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

                for edam_opetation_id in element['edam_operations']:
                    edam_operation = EDAMOperation.get_from_id(edam_opetation_id, allow_creation=True)
                    if edam_operation is not None and edam_operation not in tool.edam_operations:
                        tool.edam_operations.append(edam_operation)

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
        if search is None or len(search) == 0:
            return []

        q = None
        instances = []
        nodes = parse_search_query(search)
        for node in nodes:
            q_part = None
            if type(node) == ComparisonNode:
                key = node[0]
                value = u" ".join(node[2])
                if key == u"topic":
                    try:
                        edam_operation = EDAMOperation.objects().get(label=value)
                    except EDAMOperation.DoesNotExist:
                        return []
                    else:
                        q_part = Q(edam_operations=edam_operation)
                elif key == u"instance":
                    try:
                        instance = Instance.objects().get(brand=value)
                    except Instance.DoesNotExist:
                        return []
                    else:
                        instances.append(instance)
                else:
                    # unknown key
                    return []
            else:
                term = " ".join(node)
                q_part = (Q(name__icontains=term) | Q(description__icontains=term) | Q(display_name__icontains=term))

            if q_part is not None:
                if q is None:
                    q = q_part
                else:
                    q = q & q_part

        tools = Tool.objects(q)
        selected_tools = []
        if len(instances) > 0:
            for tool in tools:
                for version in tool.versions:
                    if len(filter(lambda x: x in version.instances, instances)) == len(instances):
                        selected_tools.append(tool)
        else:
            selected_tools = tools

        return selected_tools

    @classmethod
    def update_catalog(cls):

        # delete all Tool and ToolVersion documents
        ToolVersion.objects().delete()
        Tool.objects().delete()

        for instance in Instance.objects():
            Instance.add_instance(url=instance.url)


class Node(list):
    def __eq__(self, other):
        return list.__eq__(self, other) and self.__class__ == other.__class__

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, list.__repr__(self))

    @classmethod
    def group(cls, expr):
        def group_action(s, l, t):
            try:
                lst = t[0].asList()
            except (IndexError, AttributeError):
                lst = t
            return [cls(lst)]

        return Group(expr).setParseAction(group_action)

    def get_query(self):
        raise NotImplementedError()


class TextNode(Node):
    pass


class ExactNode(Node):
    pass


class ComparisonNode(Node):
    pass


def parse_search_query(query):

    unicode_printables = u''.join(unichr(c) for c in xrange(65536) if not unichr(c).isspace())
    word = TextNode.group(Word(unicode_printables))
    exact = ExactNode.group(QuotedString('"', unquoteResults=True, escChar='\\'))
    term = exact | word
    comparison_name = Word(unicode_printables, excludeChars=':')
    comparison = ComparisonNode.group(comparison_name + Literal(':') + term)
    content = OneOrMore(comparison | term)

    return content.parseString(query)
