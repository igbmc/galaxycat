# coding=utf-8

from flask import Flask
from flask import render_template, request
from flask_sqlalchemy import SQLAlchemy
from galaxycat import __version__
from galaxycat.config import config

app = Flask(__name__)
app.config.from_mapping(config)
db = SQLAlchemy(app)

from galaxycat.catalog import EDAMOperation, Instance, Tool  # NOQA


@app.context_processor
def utility_processor():
    return {'version': __version__}


@app.route("/")
def search():

    search = request.args.get('search', None)
    tools = Tool.search(search)

    return render_template('search.html', search=search, tools=tools)


@app.route("/tools/<id>")
def tool(id):

    tool = Tool.query.get_or_404(id)

    return render_template('tool.html', tool=tool)


@app.route("/instances")
def instances():

    instances = Instance.query.all()

    return render_template('instances.html', instances=instances)


@app.route("/topics")
def topics():

    topics = EDAMOperation.query.order_by(EDAMOperation.label).all()
    max_tools_by_topic = max([len(topic.tools) for topic in topics])
    for topic in topics:
        topic.font_size = int((float(len(topic.tools)) / float(max_tools_by_topic)) * 20.0 + 10.0)

    return render_template('topics.html', topics=topics)


@app.route("/about")
def about():

    return render_template('about.html', topics=topics)
