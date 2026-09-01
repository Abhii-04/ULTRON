import subprocess
import os 
from dotenv import load_dotenv
from typing import List
import re

# PLAYWRIGHT_CLI_SESSION= browser-profile #INSERT THE SESSION FOLDER HERE
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


def open(url):
    subprocess.run(["playwright-cli","open","--browser=chrome","--headed","--persistent",url])