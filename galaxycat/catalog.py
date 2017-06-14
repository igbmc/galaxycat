# coding=utf-8

""" Uses Bioblend to connect to Galaxy instances and stores data about tools in a MongoDB database """

from bioblend.galaxy import GalaxyInstance
from bioblend.galaxy.tools import ToolClient
from datetime import datetime
from galaxycat.config import config
from mongoengine import connect
from mongoengine import Document
from mongoengine import BooleanField, DateTimeField, ListField, ReferenceField, StringField
from mongoengine.queryset.visitor import Q


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
    meta = {'collection': 'instances'}

    # ftp_upload_site : ftp.galaxeast.fr
    # mailing_lists : https://wiki.galaxyproject.org/MailingLists
    # nginx_upload_path : /_upload
    # communication_server_host : http://localhost
    # enable_unique_workflow_defaults : False
    # wiki_url : http://wiki.galaxeast.fr
    # support_url : https://wiki.galaxyproject.org/Support
    # persistent_communication_rooms : []
    # remote_user_logout_href : None
    # logo_src : /static/images/galaxyIcon_noText.png
    # enable_communication_server : False
    # has_user_tool_filters : False
    # biostar_url_redirect : http://use.galaxeast.fr/biostar/biostar_redirect
    # message_box_visible : True
    # ftp_upload_dir : /galaxeast_ftp/galaxy
    # enable_openid : False
    # logo_url : /
    # search_url : http://galaxyproject.org/search/usegalaxy/
    # screencasts_url : None
    # ga_code : None
    # communication_server_port : 7070
    # lims_doc_url : https://usegalaxy.org/u/rkchak/p/sts
    # inactivity_box_content : Your account has not been activated yet. Feel free to browse around and see what's available, but you won't be able to upload data or run jobs until you have verified your email address.
    # citation_url : https://wiki.galaxyproject.org/CitingGalaxy
    # is_admin_user : False
    # allow_user_dataset_purge : True
    # server_startttime : 1496916251
    # biostar_url : None
    # message_box_content : From now on, to authenticate on the FTP server you will have to use your Galaxeast <strong>username</strong>. <a href="http://wiki.galaxeast.fr/doku.php?id=doc:ftp_login">More information...</a>
    # use_remote_user : None
    # datatypes_disable_auto : False
    # message_box_class : warning

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
        instance.save()

        Tool.retrieve_tools_from_instance(instance=instance)

    def get_tools_count(self):
        tool_versions = ToolVersion.objects(instances=self)
        seen = set()
        unique_tool = [tool_version for tool_version in tool_versions if not (tool_version.name in seen or seen.add(tool_version.name))]
        return len(unique_tool)


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
