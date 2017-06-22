# galaxycat

The GalaxyCat is an online catalog that lists all the tools available on various Galaxy instances and thus allows through a simple web interface to quickly find on which instances a tool is usable.

The GalaxyCat package includes all scripts to automatically feed the catalog database through the command line and the web application interface. The tool uses Bioblend to recover the list of all available tools in Galaxy instances.

An example of the deployment of Galaxycat is available [here](galaxycat.france-bioinformatique.fr).

## Requirements

  * Python 2.7
  * virtualenv
  * A mongodb server

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

    MONGODB_HOST = your_mongodb_server
    MONGODB_PORT = your_mongodb_port
    MONGODB_DB = your_mongodb_db

*By default galaxycat tries to connect to localhost on port 27017 to the galaxycat db.*

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

## Search for tools
Tools can be searched by:
  * Key words. Example: samtools
  * EDAM ontology topics (see available topics in the Topics tab). Example: topics:conversion
  * Instances to list all tools available on a given Galaxy instance. It requires from the instance to have a brand. Exemple: instance:galaxeast.

# Coming up

  * EDAM data integration
  * ~~Better search engine~~
  * Pagination ~~and stats on search results~~
  * ~~Direct link to instance terms~~
