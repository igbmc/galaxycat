# galaxycat

The GalaxyCat is an online catalog that lists all the tools available on various Galaxy instances and thus allows through a simple web interface to quickly find on which instances a tool is usable.

The GalaxyCat package includes all scripts to automatically feed the catalog database through the command line and the web application interface. The tool uses Bioblend to recover the list of all available tools in Galaxy instances.

An example of the deployment of Galaxycat is available [here](http://galaxycat.france-bioinformatique.fr).

## Requirements

  * Python 2.7
  * virtualenv
  * A Postgresql server and the psycopg2 Python package

## Install for developer

Clone the repository :

    $ git clone git@github.com:igbmc/galaxycat.git
    $ cd galaxycat

Create a Python virtual environment :

    $ virtualenv env
    $ source env/bin/activate

Install the galaxycat package :

    $ pip install -e .

## Install for production

    $ pip install git+https://github.com/igbmc/galaxycat.git#egg=galaxycat

## Configure

Create a file called app.cfg as follow :

    SQLALCHEMY_DATABASE_URI = 'postgresql:///username:password@dbhost/db'

Create the database schema :

    $ galaxycat create_database

## Register a galaxy instance

Run the galaxycat CLI as follow :

    $ galaxycat add_galaxy_instance --url=instance_full_url

You can update the catalog at anytime with the following command :

    $ galaxycat update_catalog

## Run the webapp

### Using Flask server

    $ galaxycat serve

### Using GreenUnicorn

    $ gunicorn galaxycat.app:app

*See Gunicorn documentation for more options*

## Search for tools using the webapp
Tools can be searched by one or many key words. Example: samtools.

Search can be limited using filters such as:
  * EDAM ontology topics (see available topics in the Topics tab). Example: topics:conversion
  * Instances. It requires from the instance to have a defined brand. Exemple: instance:galaxeast.

# Coming up
  * Pagination ~~and stats on search results~~
