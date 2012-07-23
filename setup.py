#!/usr/bin/env python

from distutils.core import setup
from glob import glob

setup(name='django-sagepay',
      version='0.1',
      requires=['django', 'jsonfield', 'requests'],
      description='Django interface for Sagepay payment gateway',
      author='David Evans',
      author_email='devans@timetric.com',
      url='http://github.com/timetric/django-sagepay',
      packages=['django_sagepay']
      )
