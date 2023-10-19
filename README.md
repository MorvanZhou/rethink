# Rethink

[![Unittest](https://github.com/MorvanZhou/rethink/actions/workflows/python-app.yml/badge.svg)](https://github.com/MorvanZhou/rethink/actions/workflows/python-app.yml)
[![GitHub license](https://img.shields.io/github/license/MorvanZhou/rethink)](https://github.com/MorvanZhou/rethink/blob/master/LICENSE)

A note-taking app dependent on python.
The official web version can be found at [https://rethink.run](https://rethink.run).

## Install

```shell
pip install rethink-note
```

To update:

```shell
pip install -U rethink-note
```

## Usage

Run with default settings:

```python
import rethink

rethink.run()
```

Run with custom settings:

```python
import rethink

rethink.run(
    path='.',  # path to store notes, default is current directory
    host="127.0.0.1",  # host ip, default is localhost
    port=8080,  # port number, default is 8080
    language="zh"  # language, default is English
)
```
