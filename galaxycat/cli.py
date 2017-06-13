# coding=utf-8

import click


from galaxycat.catalog import Instance, Tool


@click.group()
def cli():
    pass


@cli.command()
@click.option('--url', prompt='Galaxy URL', help='Galaxy instance url to add to the catalog')
def add_instance(url):
    Instance.add_galaxy_instance(url)


@cli.command()
def update_catalog():
    Tool.retrieve_tools_from_instance()


@cli.command()
@click.option('--search', prompt='Tool name', help='The tool to search for')
def search(search):
    for tool in Tool.search(search):
        print tool.name
