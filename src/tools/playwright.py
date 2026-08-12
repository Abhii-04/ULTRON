from pickle import NONE
import subprocess
import re
from dataclasses import dataclass
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
    """Open a persistent headed Chrome browser at the given URL."""
    CurrentPage = subprocess.Popen(["playwright-cli","open","--browser=chrome","--headed","--persistent",url])
    print("ran open_browser command")
    return CurrentPage




@tool
def goforward():
    """Navigate the current browser page forward."""
    go_forward = subprocess.run(["playwright-cli","go-forward"])
    print("ran go_forward command")
    return go_forward

@tool
def reload():
    """Reload the current browser page."""
    reload = subprocess.run(["playwright-cli","reload"])
    print("ran reload command")
    return reload

@tool
def Press(key):
    """Press a keyboard key in the current browser page."""
    press = subprocess.run(["playwright-cli","press",key])
    print("ran Press command")
    return press

@tool
def scroll(dx,dy):
    """Scroll the current browser page by the provided x/y wheel amounts."""
    scroll = subprocess.run(["playwright-cli","mousewheel",str(dx),str(dy)])
    print("ran scroll command...")
    return scroll

@tool
def save_storage_state(filename):
    """Save current browser cookies and storage state to a file."""
    storage = subprocess.run(["playwright-cli","state-save",[filename]])
    print("ran save_storage command...")
    return storage

@tool
def type(text:str):
    """Type text into the current focused browser element."""
    type = subprocess.run(["playwright-cli","type",text])
    print("ran type command")
    return type

@tool
def run_headed_browser(url):
    """Open a headed browser window at the given URL."""
    run_headed = subprocess.Popen(["playwright-cli","open",url,"--headed"])
    print("ran run_headed command")
    return run_headed

@tool 
def click(button_name):
    """Click a browser element by its visible name or selector."""
    click = subprocess.run(["playwright-cli","click",button_name])
    print("ran click command")
    return click
