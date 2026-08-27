#!/usr/bin/env python3

from flask import Flask, request, jsonify, make_response

from commons import *
from endpoints import *

app = Flask(__name__)

@app.context_processor
def inject_app_info():
    return {'app_name': APP_NAME, 'app_version': APP_VERSION}

@app.route("/")
def url_index():
    return get_page_index()

@app.route("/ajax/genba-data", methods=["POST"])
def url_ajax_genba_data():
    response_data = get_ajax_genba_data( request.json )
    return make_response(jsonify( response_data ), 200)

@app.route("/ajax/export-xls", methods=["POST"])
def url_ajax_export_xls():
    response_data = get_ajax_export_xls( request.json )
    return make_response(jsonify( response_data ), 200)

@app.route("/backend/clear-data-file")
def url_backend_clear_data_file():
    data_file_init()
    return 'Fatto!'

@app.route("/test")
def url_test():
    get_test()
    return 'Test!'