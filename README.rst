About enuma-elish
---------------

This project is https://github.com/shadowsocks/shadowsocks clone. I JUST add some extension and change some code.
so this is a more powerful ss.

enuma-elish
===========

|PyPI version| |Build Status| |Coverage Status|

A fast tunnel proxy that helps you bypass firewalls.
recommand use python3 to run this.

Server
------

Install
~~~~~~~

Debian / Ubuntu:

::

    apt-get install python-pip
    pip install x-mroy-9

CentOS:

::

    yum install python-setuptools && easy_install pip
    pip install x-mroy-9

Windows:


Usage
~~~~~

::

    ea -p 443 -k password -m rc4-md5

To run in the background:

::

    sudo ea -p 443 -k password -m rc4-md5 --user nobody -d start

To stop:

::

    sudo ea -d stop

To check the log:

::

    sudo less /var/log/enuma-elish.log


License
-------

Copyright 2018 qingluan

Licensed under the Gnu License 2.0 (the "License"); you may
not use this file except in compliance with the License. You may obtain
a copy of the License at

::
