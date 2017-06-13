# coding=utf-8

from flask import Flask
from flask import abort, render_template, request
from galaxycat import __version__
from galaxycat.config import config
from galaxycat.catalog import Instance, Tool

app = Flask(__name__)
app.config.from_mapping(config)


@app.context_processor
def utility_processor():
    return {'version': __version__}


@app.route("/")
def search():

    search = request.args.get('search', None)

    tools = []
    if search is not None:
        tools = Tool.search(search)
    else:
        tools = Tool.objects()

    return render_template('search.html', search=search, tools=tools)


@app.route("/tools/<id>")
def tool(id):

    try:
        tool = Tool.objects.get(id=id)
    except Tool.DoesNotExist:
        abort(404)

    return render_template('tool.html', tool=tool)


@app.route("/instances")
def instances():

    instances = Instance.objects()

    return render_template('instances.html', instances=instances)
