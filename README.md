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

![image](https://github.com/MorvanZhou/rethink/blob/main/img/notes-page.png?raw=true)

![editor](https://github.com/MorvanZhou/rethink/blob/main/img/editor.png?raw=true)

![phone](https://github.com/MorvanZhou/rethink/blob/main/img/phone.png?raw=true)

## Install

```shell
pip install rethink-note
```

To update:

```shell
pip install -U rethink-note
```

## Usage

Quickly start the note web service with `rethink.run()`, and save your note data locally:

```python
import rethink

rethink.run()
```

If you need to customize settings, you can set the parameters in `rethink.run()`:

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
and the `.data` folder will be created in your `path` directory.

English and Chinese languages are supported, and the default is English `en`.
If you want to use Chinese `zh`, you can use `language="zh"` parameter.
