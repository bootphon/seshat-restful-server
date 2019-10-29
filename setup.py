# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


setup(
    name='seshat',
    version='0.1.0',
    description='A self-hosted tool to manage and ensure quality of audio annotations',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://gitlab.com/bootphon/seshat',
    author='Hadrien Titeux',
    author_email='hadrien.titeux@ens.fr',
    license="MIT",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6'
    ],
    keywords='',
    namespace_packages=['seshat'],
    packages=find_packages(exclude=['docs', 'tests']),
    setup_requires=['pytest-runner', 'setuptools>=38.6.0'],  # >38.6.0 needed for markdown README.md
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'add-admin = seshat.cli_apps.add_admin:main',
            'change-password = seshat.cli_apps.check_password:main',
            'check-parser = seshat.cli_apps.check_parser:main',
            'check-dataset = seshat.cli_apps.check_dataset:main',
        ]
    }
)
