import os

from setuptools import find_packages, setup


# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

with open('VERSION', 'r') as vfile:
    VERSION = vfile.read().strip()

with open('README.rst', 'r') as rfile:
    README = rfile.read()

setup(
    name='django-snow',
    version=VERSION,
    author='Pradeep Kumar Rajasekaran',
    author_email='prajasekaran@godaddy.com',
    license='MIT',
    description='Django package for creation of ServiceNow Tickets',
    long_description=README,
    packages=find_packages(),
    include_package_data=True,
    url='https://github.com/godaddy/django-snow',
    download_url='https://github.com/godaddy/django-snow/archive/master.tar.gz',
    install_requires=[
        'Django>=1.8',
        'pysnow>=0.6.4',
    ],
    tests_require=[
        'six',
    ],

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Framework :: Django',
        'Framework :: Django :: 1.8',
        'Framework :: Django :: 1.9',
        'Framework :: Django :: 1.10',
        'Framework :: Django :: 1.11',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    zip_safe=False,
    test_suite='runtests.runtests'
)
