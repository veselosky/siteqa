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

import collections
import logging
from urllib.parse import urljoin, urlparse, urlunparse, urldefrag

import requests
from bs4 import BeautifulSoup


class Crawler(object):

    def __init__(self, starturl, timeout=10, **kwargs):
        super().__init__()
        self.starturl = starturl
        self.timeout = timeout
        self.session = None
        self.queue = None

        self.seen = collections.defaultdict(lambda: False)
        self.errors = collections.defaultdict(list)
        self.server_errors = collections.defaultdict(list)
        self.redirects = collections.defaultdict(list)

        # To determine internal links
        start = urlparse(self.starturl, scheme='http')
        self.base = urlunparse((start[0], start[1], '', '', '', ''))

        self.logger = kwargs.get("logger", logging.getLogger(__name__))

    def can_parse_type(self, content_type):
        "Return true if we know how to extract links from this content type"
        if content_type.startswith('text/html'):
            return True
        else:
            return False

    def is_local(self, url):
        "Return true if the URL is on the same site as starturl"
        return url.startswith(self.base)

    def is_crawlable(self, resp):
        """Return true if we can crawl this object for links"""
        return resp.ok and self.is_local(resp.url) and \
            self.can_parse_type(resp.headers.get("content-type", ''))

    def normalize(self, url):
        "Normalize a (possibly partial) URL, returning tuple of (url, fragment)"
        fixedurl = urljoin(self.starturl, url)
        return urldefrag(fixedurl)

    def parse_html(self, html):
        return BeautifulSoup(html)

    def extract_links(self, text):
        "Return list of URLs referenced by the document"
        doc = self.parse_html(text)
        links = []
        for item in doc.find_all(href=True):
            link, fragment = self.normalize(item["href"])
            if not self.seen[link]:
                links.append(link)
        # TODO Also check src and srcset attrs, any others?
        return links

    def head(self, url):
        return self.session.head(url,
                                 timeout=self.timeout,
                                 allow_redirects=True)

    def get(self, url):
        return self.session.get(url, timeout=self.timeout, allow_redirects=True)

    def add_to_queue(self, item):
        self.queue.append(item)

    def next_in_queue(self):
        return self.queue.popleft()

    def queue_empty(self):
        return len(self.queue) == 0

    def done_with(self, url):
        pass

    def check(self, response, url='', source=None):
        "Records errors. Returns None if error, response if OK."
        if response.status_code < 300 and not response.history:
            return response
        elif 400 <= response.status_code < 500:
            self.errors[source].append(url)
            return None
        elif response.status_code >= 500:
            self.server_errors[source].append(url)
            return None

        if response.history:  # redirected
            if response.history[0].status_code == 301:
                self.redirects[source].append((url, response.url))
            return response

    def crawlpage(self, url):
        response = self.get(url)
        response.raise_for_status()
        text = response.text
        for link in self.extract_links(text):
            if not self.seen[link]:
                self.add_to_queue((url, link))

    def crawlsite(self):
        """
        Crawl website asynchronously until all found links are crawled
        """
        try:
            while True:
                source, url = self.next_in_queue()
                self.logger.debug("GOT " + url)
                if not self.seen[url]:
                    self.logger.debug(url)
                    self.seen[url] = True
                    resp = self.head(url)
                    self.check(resp, url, source)
                    if self.is_crawlable(resp):
                        self.crawlpage(url)
                        self.logger.info("Crawled page " + url)
                else:
                    self.logger.debug("SEEN " + url)
                self.done_with(url)
        except IndexError:  # next_in_queue will raise when empty
            pass

    def crawl(self):
        self.queue = collections.deque()
        self.add_to_queue(('', self.starturl))
        self.session = requests.Session()
        self.crawlsite()


# Algorithm:
# Add starturl to DOCS queue
# PROCESS:
# Pull doc from DOCS queue
# If doc is 404, return an error (this should not happen unless it is starturl)
# Parse the doc, add links to CHECK queue
# For each link in CHECK queue, HEAD
# If not 2xx, add to NotFoundList
# If link is local to starturl, add to DOCS queue
# When CHECK queue is empty, pull a document from the DOCS queue
# Errors want to be grouped by the page that had the error, to make fixes
# easier. Within each page, errors should be grouped by type:
# 4xx: MUST update or remove the link
# 301: MAY want to update the link
# 5xx: MAY want to investigate
