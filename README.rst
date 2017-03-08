===========================================
SiteQA: tools for testing website quality
===========================================

.. image:: https://img.shields.io/pypi/v/siteqa.svg
        :target: https://pypi.python.org/pypi/siteqa

Quick facts::

    'Development Status :: 3 - Alpha',
    'License :: OSI Approved :: Apache Software License',
    'Programming Language :: Python :: 3 :: Only',
    'Programming Language :: Python :: 3.5',

Why?
=======================================================================

There are a number of commercially available Fremium tools for checking for
broken links and other aspects of web site quality. However, most of these are
hosted services, and very few are open source. I started this project because I
wanted a tool that met these criteria:

* Could be run against a dev site running on localhost
* Is free (gratis)
* Is extensible to add custom checks to fit my definition of "quality"
* Could be automated as part of a continuous integration system for site builds
* Could (eventually) be taught to update source files to fix errors automatically

Features
=======================================================================

None currently, but...

The siteqa command performs various checks for website quality. Checks may
include:

* [X] Check hrefs for broken links, both internal and external
* [X] Check src attributes for broken links
* [ ] Check srcset attributes for broken links
* [ ] Check opengraph and other social metadata for validity and best practices
* [ ] Check on-page SEO factors for best practices
* [ ] Check for invalid or bad practice HTML usage
* [ ] Check microformats and schema.org metadata usage
* [ ] Check for accessibility factors
