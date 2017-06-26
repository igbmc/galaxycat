# coding=utf-8

""" Uses Bioblend to connect to Galaxy instances and stores data about tools in a MongoDB database """

import requests
import urllib

from bioblend import ConnectionError
from bioblend.galaxy import GalaxyInstance
from bioblend.galaxy.tools import ToolClient
from datetime import datetime
from galaxycat.app import db
from pyparsing import Group, Literal, OneOrMore, QuotedString, Word
from sqlalchemy import func
from urlparse import urlparse


toolversion_instance = db.Table('toolversion_instance',
                                db.Column('tool_version_id', db.Integer, db.ForeignKey('tool_version.id')),
                                db.Column('instance_id', db.Integer, db.ForeignKey('instance.id')))

tool_edam_operation = db.Table('tool_edam_operation',
                               db.Column('tool_id', db.Integer, db.ForeignKey('tool.id')),
                               db.Column('edam_operation_id', db.Unicode, db.ForeignKey('edam_operation.operation_id')))


class Instance(db.Model):

    __tablename__ = 'instance'

    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.Unicode, unique=True, nullable=False)
    creation_date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    update_date = db.Column(db.DateTime())
    allow_user_creation = db.Column(db.Boolean())
    brand = db.Column(db.Unicode())
    enable_quotas = db.Column(db.Boolean())
    require_login = db.Column(db.Boolean())
    terms_url = db.Column(db.Unicode())
    version = db.Column(db.Unicode())
    city = db.Column(db.Unicode())
    zipcode = db.Column(db.Unicode())
    country = db.Column(db.Unicode())
    country_code = db.Column(db.Unicode())
    latitude = db.Column(db.Float())
    longitude = db.Column(db.Float())

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

        instance = Instance.query.filter_by(url=url).first()
        if instance is None:
            instance = Instance(url=url)
            db.session.add(instance)

        try:
            galaxy_instance = GalaxyInstance(url=url)
            instance_config = galaxy_instance.config.get_config()

            instance.update_date = datetime.now()
            instance.allow_user_creation = instance_config['allow_user_creation']
            instance.brand = instance_config['brand']
            instance.enable_quotas = 'enable_quotas' in instance_config and instance_config['enable_quotas']
            instance.require_login = 'require_login' in instance_config and instance_config['require_login']
            instance.terms_url = instance_config['terms_url']
            instance.version = instance_config['version_major']

            url_data = urlparse(url)
            try:
                instance_location = requests.get('http://ip-api.com/json/%s' % url_data.netloc)
            except requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout:
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

            db.session.commit()

            Tool.retrieve_tools_from_instance(instance=instance)
        except ConnectionError:
            print "Unable to add or update %s" % url

    def get_tools_count(self):
        return len(Tool.query.outerjoin(EDAMOperation, Tool.edam_operations).join(ToolVersion).join(Instance, ToolVersion.instances).filter(Instance.id == self.id).all())

    @property
    def location(self):
        if self.city is not None and self.country is not None:
            return "%s, %s" % (self.city, self.country)
        else:
            return "Unknown"


class EDAMOperation(db.Model):

    __tablename__ = 'edam_operation'

    operation_id = db.Column(db.Unicode(), primary_key=True)
    iri = db.Column(db.Unicode(), nullable=False)
    label = db.Column(db.Unicode(), nullable=False)
    description = db.Column(db.Unicode())

    @classmethod
    def get_from_id(cls, operation_id, allow_creation=False):

        edam_operation = EDAMOperation.query.filter_by(operation_id=operation_id).first()
        if edam_operation is None and allow_creation:
            iri = 'http://edamontology.org/%s' % operation_id
            api_url = 'http://www.ebi.ac.uk/ols/api/ontologies/edam/terms/%s' % urllib.quote(urllib.quote(iri, safe=''), safe='')
            edam_response = requests.get(api_url)
            if edam_response.status_code == 200:
                edam_data = edam_response.json()
                edam_operation = EDAMOperation(operation_id=operation_id,
                                               iri=iri,
                                               label=edam_data['label'],
                                               description=" ".join(edam_data['description']))
                db.session.add(edam_operation)

        return edam_operation


class ToolVersion(db.Model):

    __tablename__ = 'tool_version'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(), nullable=False)
    version = db.Column(db.Unicode(), nullable=False)
    tool_shed = db.Column(db.Unicode())
    owner = db.Column(db.Unicode())
    changeset = db.Column(db.Unicode())
    tool_id = db.Column(db.Integer, db.ForeignKey('tool.id'))
    instances = db.relationship('Instance', secondary=toolversion_instance, backref=db.backref('tool_versions'))


class Tool(db.Model):

    __tablename__ = 'tool'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(), nullable=False, unique=True)
    description = db.Column(db.Unicode())
    display_name = db.Column(db.Unicode())
    versions = db.relationship('ToolVersion', backref='tool')
    edam_operations = db.relationship('EDAMOperation', secondary=tool_edam_operation, backref=db.backref('tools'))

    @classmethod
    def retrieve_tools_from_instance(cls, instance):

        galaxy_instance = GalaxyInstance(url=instance.url)
        tool_client = ToolClient(galaxy_instance)
        for element in tool_client.get_tools():
            if element['model_class'] == 'Tool':

                tool_name = element['id']
                if '/' in tool_name:
                    tool_name = tool_name.split('/')[-2]

                tool = Tool.query.filter_by(name=tool_name).first()
                if tool is None:
                    tool = Tool(name=tool_name)
                    db.session.add(tool)

                tool.description = element['description']
                tool.display_name = element['name']

                for edam_opetation_id in element['edam_operations']:
                    edam_operation = EDAMOperation.get_from_id(edam_opetation_id, allow_creation=True)
                    if edam_operation is not None and edam_operation not in tool.edam_operations:
                        tool.edam_operations.append(edam_operation)

                if 'tool_shed_repository' in element:
                    tool_version = ToolVersion.query\
                                              .filter_by(name=tool_name)\
                                              .filter_by(changeset=element['tool_shed_repository']['changeset_revision'])\
                                              .filter_by(tool_shed=element['tool_shed_repository']['tool_shed'])\
                                              .filter_by(owner=element['tool_shed_repository']['owner'])\
                                              .first()
                else:
                    tool_version = ToolVersion.query\
                                              .filter_by(name=tool_name)\
                                              .filter_by(version=element['version'])\
                                              .filter_by(tool_shed=None)\
                                              .filter_by(owner=None)\
                                              .first()
                if tool_version is None:
                    tool_version = ToolVersion(name=tool_name,
                                               version=element['version'])
                    db.session.add(tool_version)

                if 'tool_shed_repository' in element:
                    tool_version.changeset = element['tool_shed_repository']['changeset_revision']
                    tool_version.tool_shed = element['tool_shed_repository']['tool_shed']
                    tool_version.owner = element['tool_shed_repository']['owner']

                if instance not in tool_version.instances:
                    tool_version.instances.append(instance)

                if tool_version not in tool.versions:
                    tool.versions.append(tool_version)

                db.session.commit()

    @classmethod
    def search(cls, search):
        if search is None or len(search) == 0:
            return []

        query = Tool.query.outerjoin(EDAMOperation, Tool.edam_operations).join(ToolVersion).join(Instance, ToolVersion.instances)
        nodes = parse_search_query(search)
        for node in nodes:
            if type(node) == ComparisonNode:
                key = node[0]
                value = u" ".join(node[2]).lower()
                if key == u"topic":
                    query = query.filter(func.lower(EDAMOperation.label) == value)
                elif key == u"instance":
                    query = query.filter(func.lower(Instance.brand) == value)
                else:
                    # unknown key
                    return []
            else:
                term = "%{0}%".format(" ".join(node).lower())
                query = query.filter(Tool.name.ilike(term) | Tool.description.ilike(term) | Tool.display_name.ilike(term))

        return query.all()

    @classmethod
    def update_catalog(cls):

        # delete all Tool and ToolVersion
        ToolVersion.query.delete()
        Tool.query.delete()
        db.session.commit()

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
