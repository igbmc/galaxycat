# galaxycat

galaxycat is a python package that let you setup easily an online Galaxy instances and tools catalog.

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

You can uupdate the catalog at anytime with the following command :

    $ galaxycat update_catalog

## Run the webapp

### Using Flask server

    $ export FLASK_APP=galaxycat.app:app
    $ flask run

*See Flask documentation for more options*

### Using GreenUnicorn

    $ gunicorn galaxycat.app:app

*See Gunicorn documentation for more options*
