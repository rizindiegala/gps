#!/usr/bin/env python3

import webbrowser
from threading import Timer
from flask import Flask
from flask_app import *

def open_browser():
    webbrowser.open_new("http://127.0.0.1:2000")

if __name__ == "__main__":
    Timer(1, open_browser).start()
    app.run(port=2000)