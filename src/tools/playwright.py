from pickle import NONE
import subprocess
import re
from dataclasses import dataclass
from tracemalloc import Snapshot
from typing import List
from langchain_core.tools import tool
from typing import Any

POSITIVE_PHRASES = {
    "apply": 20,
    "apply now": 50,
    "apply here": 50,
    "easy apply": 45,
    "start application": 45,
    "continue application": 35,
    "submit application": 20,
}
NEGATIVE_PHRASES = [
    "already applied",
    "application deadline",
    "application status",
    "application submitted",
    "who can apply",
    "how to apply",
    "apply filters",
    "apply coupon",
    "terms apply",
]

@tool
def open_browser(url):
    """open a browser or to peform browser automation in browser"""
    CurrentPage = subprocess.Popen(["playwright-cli","open","--browser=chrome","--headed","--persistent",url])
    print("ran open_browser command")
    return CurrentPage

@tool
def snapshot(filename):
    """take a snapshot of the current page in browser """
    Snapshot = subprocess.run(["playwright-cli","snapshot","--filename=f "], capture_output=True, text=True)
    print("ran snapshot command")
    return Snapshot



@tool
def goforward():
    """go forward in a url/Currentpage in browser"""
    go_forward = subprocess.run(["playwright-cli","go-forward"])
    print("ran go_forward command")
    return go_forward

@tool
def reload():
    """reload a page in browser"""
    reload = subprocess.run(["playwright-cli","reload"])
    print("ran reload command")
    return reload

@tool
def Press(key):
    """press a key (eg : Enter, ArrowLeft) in browser"""
    press = subprocess.run(["playwright-cli","press",key])
    print("ran Press command")
    return press

@tool
def scroll(dx,dy):
    """scroll up or down in a page by providing dx and dy measurements in browser"""
    scroll = subprocess.run(["playwright-cli","mousewheel",str(dx),str(dy)])
    print("ran scroll command...")
    return scroll

@tool
def save_storage_state(filename):
    """save storage state(cookies,localstorage) in browser"""
    storage = subprocess.run(["playwright-cli","state-save",[filename]])
    print("ran save_storage command...")
    return storage

@tool
def type(text:str):
    """type a text in browser"""
    type = subprocess.run(["playwright-cli","type",text])
    print("ran type command")
    return type

@tool
def run_headed_browser(url):
    """run headed browser"""
    run_headed = subprocess.Popen(["playwright-cli","open",url,"--headed"])
    print("ran run_headed command")
    return run_headed

@tool 
def click(button_name):
    """click a button"""
    click = subprocess.run(["playwright-cli","click",button_name])
    print("ran click command")
    return click