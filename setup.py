import codecs
from setuptools import setup
from setuptools import find_packages


setup(
    name="enuma-elish",
    version="0.0.2",
    license='http://www.apache.org/licenses/LICENSE-2.0',
    description="A fast tunnel proxy  extension from ss ,which help you get through firewalls",
    author='f0cklinux',
    author_email='no-one-controll@gmail.com',
    url='https://github.com/f0cklinux/enuma-elish',
    # packages=['enuma_elish', 'enuma_elish.crypto'],
    packages=find_packages(),
    package_data={
        'enuma_elish': ['README.md','LICENSE']
    },
    install_requires=[],
    include_package_data=True,
    entry_points="""
    [console_scripts]
    ea_local = enuma_elish.local:main
    ea = enuma_elish.server:main
    """,
    # classifiers=[
    #     'License :: OSI Approved :: Apache Software License',
    #     'Programming Language :: Python :: 3',
    #     'Programming Language :: Python :: 3.3',
    #     'Programming Language :: Python :: 3.4',
    #     'Programming Language :: Python :: 3.6',
    #     'Programming Language :: Python :: 3.7',
    #     'Programming Language :: Python :: Implementation :: CPython',
    #     'Programming Language :: Python :: Implementation :: PyPy',
    #     'Topic :: Internet :: Proxy Servers',
    # ],
)
