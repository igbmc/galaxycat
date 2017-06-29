# coding=utf-8

import click


from galaxycat.app import db
from galaxycat.catalog import EDAMOperation, Instance, Tool, ToolVersion  # NOQA


@click.group()
def cli():
    pass


@cli.command(help="Create the GalaxyCat SQL database")
def create_database():
    db.create_all()


@cli.command(help="Add a Galaxy instance to the catalog")
@click.option('--url', prompt='Galaxy URL', help='Galaxy instance url to add to the catalog')
def add_instance(url):
    Instance.add_instance(url=url)


@cli.command(help="Update the catalog")
def update_catalog():
    Tool.update_catalog()


@cli.command(help="Create Whoosh index")
def create_index():
    Tool.create_whoosh_index()


@cli.command(help="Serve the GalaxyCat webapp (not suitable for production)")
@click.option('--host', default="127.0.0.1", help='Host bind to the webapp')
@click.option('--port', type=int, default=5000, help='Port bind to the webapp')
def serve(host, port):
    from galaxycat.app import app
    app.run(host=host, port=port)


@cli.command(help="Search the catalog")
@click.option('--search', prompt='Tool name', help='The tool to search for')
def search(search):
    for tool in Tool.search(search):
        print tool.name
