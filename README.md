# Rethink

[![Unittest](https://github.com/MorvanZhou/rethink/actions/workflows/python-app.yml/badge.svg)](https://github.com/MorvanZhou/rethink/actions/workflows/python-app.yml)
[![GitHub license](https://img.shields.io/github/license/MorvanZhou/rethink)](https://github.com/MorvanZhou/rethink/blob/master/LICENSE)
<a href="https://pypi.org/project/rethink-note" target="_blank">
<img src="https://img.shields.io/pypi/v/rethink-note?color=%2334D058&label=pypi%20package" alt="Package version">
</a>
<a href="https://pypi.org/project/rethink-note" target="_blank">
<img src="https://img.shields.io/pypi/pyversions/rethink-note.svg?color=%2334D058" alt="Supported Python versions">
</a>

<p align="center">
  <strong>English</strong> | <a href="README_ZH.md" target="_blank">简体中文</a>
</p>

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

Quickly start the note web service with `rethink.run()`:

```python
import rethink

rethink.run()
```

If you need more custom running settings, you can use the parameters of `rethink.run()`:

```python
import rethink

rethink.run(
    path='.',  # path to store notes, default is current directory
    host="127.0.0.1",  # host ip, default is localhost
    port=8080,  # port number, default is 8080
    language="zh"  # language, default is English, optional: zh, en
)
```

All notes will be stored in the path specified by `path`,
and the `.data` folder will be created in the current directory by default.
If you want to create a data folder in another path, you can use the `path` parameter.

English and Chinese languages are supported, and the default is English `en`.
If you want to use Chinese `zh`, you can use `language="zh"` parameter.
