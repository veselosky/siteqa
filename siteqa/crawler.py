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

import asyncio
import collections
import logging
from urllib.parse import urljoin, urlparse, urlunparse, urldefrag

import aiohttp
from bs4 import BeautifulSoup


class Crawler(object):

    def __init__(self, starturl, max_requests=1, timeout=10, **kwargs):
        super().__init__()
        self.starturl = starturl
        self.max_requests = max_requests
        self.timeout = timeout
        self.errors = collections.defaultdict(list)
        self.server_errors = collections.defaultdict(list)
        self.redirects = collections.defaultdict(list)

        # To determine internal links
        start = urlparse(self.starturl, scheme='http')
        self.base = urlunparse((start[0], start[1], '', '', '', ''))

        self.queue = None
        self.loop = None
        self.seen = collections.defaultdict(lambda: False)
        self.session = None
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
        return self.is_local(resp.url) and \
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

    async def head(self, url, source=None):
        with aiohttp.Timeout(self.timeout):
            async with self.session.head(url) as response:
                return response

    def check(self, response, url='', source=None):
        "Records errors. Returns None if error, response if OK."
        if response.status < 300 and not response.history:
            return response
        elif 400 <= response.status < 500:
            self.errors[source].append(url)
            return None
        elif response.status >= 500:
            self.server_errors[source].append(url)
            return None

        if response.history:  # redirected
            if response.history[0].status == 301:
                self.redirects[source].append((url, response.url))
            return response

    async def crawlpage(self, url):
        with aiohttp.Timeout(self.timeout):
            async with self.session.get(url) as response:
                response.raise_for_status()
                text = await response.text()
                for link in self.extract_links(text):
                    await self.queue.put((url, link))

    async def worker(self):
        self.logger.debug("ENTERED worker")
        try:
            while True:
                if self.queue.empty():
                    self.logger.error("Queue is empty!")
                    return
                self.logger.debug("Getting item from queue")
                source, url = await self.queue.get()
                self.logger.debug("GOT " + url)
                if not self.seen[url]:
                    self.logger.debug(url)
                    self.seen[url] = True
                    resp = await self.head(url)
                    self.check(resp, url, source)
                    if self.is_crawlable(resp):
                        await self.crawlpage(url)
                        self.logger.info("Crawled page " + url)
                else:
                    self.logger.debug("SEEN " + url)
                self.queue.task_done()
        except asyncio.CancelledError:
            pass

    async def crawlsite(self):
        """
        Crawl website asynchronously until all found links are crawled
        """
        self.logger.debug("ENTERED crawlsite")
        async with aiohttp.ClientSession(loop=self.loop) as session:
            self.session = session
            workers = [
                asyncio.Task(self.worker())
                for _ in range(self.max_requests)
            ]

            await self.queue.join()  # join == drain

            # Cancel worker after everything is done
            for w in workers:
                w.cancel()

    def crawl(self):
        self.loop = asyncio.get_event_loop()
        self.queue = asyncio.Queue(1000, loop=self.loop)
        self.queue.put_nowait(('', self.starturl))
        self.logger.debug("commencing loop")
        self.loop.run_until_complete(self.crawlsite())
        self.loop.close()


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
