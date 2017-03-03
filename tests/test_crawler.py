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
from unittest import mock

from siteqa.crawler import Crawler

localhost = 'http://localhost:8000'


#####################################################################
# TEST Crawler.check
#####################################################################
def test_check_200():
    resp = mock.Mock()
    resp.status = 200
    resp.history = None

    c = Crawler(localhost)
    out = c.check(resp)
    assert out == resp
    assert not c.errors
    assert not c.server_errors
    assert not c.redirects


def test_check_204():
    resp = mock.Mock()
    resp.status = 204
    resp.history = None

    c = Crawler(localhost)
    out = c.check(resp)
    assert out == resp
    assert not c.errors
    assert not c.server_errors
    assert not c.redirects


def test_check_404_no_source():
    resp = mock.Mock()
    resp.status = 404
    resp.history = None

    c = Crawler(localhost)
    out = c.check(resp)
    assert out is None
    assert c.errors[None] == ['']
    assert not c.server_errors
    assert not c.redirects


def test_check_404_source():
    resp = mock.Mock()
    resp.status = 404
    resp.history = None

    c = Crawler(localhost)
    out = c.check(resp, url='/test', source=localhost)
    assert out is None
    assert c.errors[localhost] == ['/test']
    assert not c.server_errors
    assert not c.redirects


def test_check_500_no_source():
    resp = mock.Mock()
    resp.status = 500
    resp.history = None

    c = Crawler(localhost)
    out = c.check(resp)
    assert out is None
    assert c.server_errors[None] == ['']
    assert not c.errors
    assert not c.redirects


def test_check_500_source():
    resp = mock.Mock()
    resp.status = 500
    resp.history = None

    c = Crawler(localhost)
    out = c.check(resp, url='/test', source=localhost)
    assert out is None
    assert c.server_errors[localhost] == ['/test']
    assert not c.errors
    assert not c.redirects


def test_check_301_no_source():
    redir = mock.Mock()
    redir.status = 301
    resp = mock.Mock()
    resp.status = 200
    resp.url = localhost + '/redir'
    resp.history = [redir]

    c = Crawler(localhost)
    out = c.check(resp)
    assert out == resp
    assert not c.server_errors
    assert not c.errors
    assert c.redirects[None] == [('', resp.url)]


def test_check_301_source():
    redir = mock.Mock()
    redir.status = 301
    resp = mock.Mock()
    resp.status = 200
    resp.url = localhost + '/redir'
    resp.history = [redir]

    c = Crawler(localhost)
    out = c.check(resp, url='/test', source=localhost)
    assert out == resp
    assert not c.server_errors
    assert not c.errors
    assert c.redirects[localhost] == [('/test', resp.url)]
