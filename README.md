# Rethink

[![Unittest](https://github.com/MorvanZhou/rethink/actions/workflows/python-app.yml/badge.svg)](https://github.com/MorvanZhou/rethink/actions/workflows/python-app.yml)
[![License](https://img.shields.io/github/license/MorvanZhou/rethink)](https://github.com/MorvanZhou/rethink/blob/master/LICENSE)
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

![demo](https://github.com/MorvanZhou/rethink/raw/main/img/demo.gif)

## Why Rethink

Rethink was born out of my inability to find a note-taking app that truly catered to my needs. My vision for a
note-taking app includes:

1. **Effortless Recording**: When capturing ideas, rethink provides with a swift and seamless recording process.
2. **Easy Application**: To facilitate easy application, merely jotting down notes is insufficient.
   The recorded information should be able to form a knowledge network,
   enabling your accumulated knowledge to compound over time.
   This foundation allows for effective application and each new idea recorded serves to reinforce
   and strengthen the existing knowledge network.

## Features

1. **Bi-directional links**: A knowledge network is important.
   Rethink allows you to @ link to other notes in the note with one click;
2. **Markdown syntax**: Seamless support for Markdown syntax, the format of notes is more controllable;
3. **Automatic association**: Too many notes? Don't remember what you wrote before?
   Unable to effectively form a note network?
   Rethink automatically recommend related notes while writing,
   actively assist you in forming a knowledge network.
4. **Local storage**: Rethink attaches great importance to data security.
   You can store data in a local storage.
   Or you can also use the online version [https://rethink.run](https://rethink.run),
   which makes it easy to synchronize across multiple platforms.
5. **Multi-language**: Support multiple languages, including Chinese and English.

## Install

First install:

```shell
pip install rethink-note
```

To update:

```shell
pip install -U rethink-note
```

## Usage

Quickly start the note web service with `rethink.run()`, and save your note data locally,
The default save path is the `.data` folder under the path of this script:

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

Open your browser and visit `http://127.0.0.1:8080` to start recording your ideas.
