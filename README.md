# Seshat RESTful Server

[![Python Support](https://img.shields.io/badge/Python-3.6-green.svg)]()
[![OpenAPI version](https://img.shields.io/badge/OpenAPI-3.0.1-blue.svg)](https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.1.md)
[![Mongo Version](https://img.shields.io/badge/MongoDB-3.x-blue.svg)]()
[![Documentation](https://readthedocs.org/projects/seshat-annotation/badge/?version=latest)](https://seshat-annotation.readthedocs.io/en/latest/)

This is the repository for [Seshat](https://github.com/bootphon/seshat)'s RESTful API server. 

## Depencencies

Seshat's API server relies on the following dependencies :

* A working python 3.6>= (default Python version on Ubuntu 18.04)
* A mongoDB 3.6>= install (it could work with earlier versions)
* An FFmpeg install (used for FFprobe)

## Quick install

This is a quick manual installation overview, **just aimed at installing the server**.
We provide more complete for both Seshat's server and [client](https://github.com/bootphon/seshat-angular-client) 
installation instructions in [our install tutorial](https://seshat-annotation.readthedocs.io/en/latest/).

First, git clone the repository, set up its virtual environment, install its dependencies ,
and set the server's config to `prod` via a dotenv file:

```shell script
git clone https://github.com/bootphon/seshat-restful-server
cd seshat-restful-server
python3 -m venv venv/
. venv/bin/activate
python setup.py install
echo FLASK_CONFIG=prod > .env
```

Then, just run the server with: 
```shell script
python app.py
```
