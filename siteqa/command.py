# vim: set fileencoding=utf-8 :
#
#   Copyright 2017 Vince Veselosky and contributors
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
"""
SiteQA command line interface.

Usage:
    siteqa [-v] URL

Options:
    -v --verbose            Verbose logging

"""
import logging

import colorlog
from docopt import docopt

from siteqa.crawler import Crawler

# Ugh! Why does logging have to be so damned hard?
logger = None


def getLogger(options=None):
    global logger
    level = logging.INFO
    if "verbose" in options:
        level = logging.DEBUG
    if logger is None:
        handler = colorlog.StreamHandler()
        handler.setFormatter(colorlog.ColoredFormatter(
            '%(log_color)s%(levelname)s: %(message)s', log_colors={
                'DEBUG': 'white', 'INFO': 'cyan', 'WARNING': 'yellow',
                'ERROR': 'red', 'CRITICAL': 'red,bg_white',
            }, ))
        logger = colorlog.getLogger('webquills')
        logger.addHandler(handler)
        logger.setLevel(level)
    return logger


def configure(param):
    cfg = {}
    for key, value in param.items():
        if key.startswith("--") and value is not None:
            cfg[key[2:]] = value
        elif value is not None:
            cfg[key] = value
    return cfg


def main():
    param = docopt(__doc__)
    cfg = configure(param)
    logger = getLogger(cfg)
    crawler = Crawler(cfg["URL"], logger=logger)
    crawler.crawl()
    print(repr(crawler.errors))
