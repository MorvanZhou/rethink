# Rethink

[![Unittest](https://github.com/MorvanZhou/rethink/actions/workflows/python-tests.yml/badge.svg)](https://github.com/MorvanZhou/rethink/actions/workflows/python-tests.yml)
[![License](https://img.shields.io/github/license/MorvanZhou/rethink)](https://github.com/MorvanZhou/rethink/blob/master/LICENSE)
<a href="https://pypi.org/project/retk" target="_blank">
<img src="https://img.shields.io/pypi/v/retk?color=%2334D058&label=pypi%20package" alt="Package version">
</a>
<a href="https://pypi.org/project/retk" target="_blank">
<img src="https://img.shields.io/pypi/pyversions/retk.svg?color=%2334D058" alt="Supported Python versions">
</a>

<p align="center">
  <strong>English</strong> | <a href="README_ZH.md" target="_blank">简体中文</a>
</p>

Rethink is my understanding of self-developing.

Every time a new thought is recorded,
the relevant old thought will automatically emerge,
cross-connect, and continuously analogize and upgrade cognition.

The official web version can be found at [https://rethink.run](https://rethink.run).

![demo](https://github.com/MorvanZhou/rethink/raw/main/img/demo.gif)

## Let ideas find you rather than you find them

Let people who love to record with no useless thought.
Even with a continuous stream of input, you don't need to worry about finding it.

We introduce a recommendation mechanism that allows old records to come back while recording a new thought.
Making the new thought more connectable and memorable.

## Features

1. **Bi-directional links**: To @ link in the note with one click;
2. **Markdown syntax**: Seamless support for Markdown syntax;
3. **Automatic association**: Automatically recommend related notes while writing,
   actively assist you in forming a knowledge network.
4. **Local storage**: Rethink attaches great importance to data security.
   You can store data in a local storage.
   Or the online version [https://rethink.run](https://rethink.run),
   which makes it easy to synchronize across multiple platforms.
5. **Multi-language**: Support multiple languages, including Chinese and English.

## Install

First install:

```shell
pip install retk
```

To update:

```shell
pip install -U retk
```

## Usage

Quickly start the note web service with `retk.run()`, and save your note data locally,
The default save path is the `.data` folder under the path of this script:

```python
import retk

retk.run()
```

If you need to customize settings, you can set the parameters in `retk.run()`:

```python
import retk

retk.run(
   path='.',  # path to store notes, default is current directory
   host="127.0.0.1",  # host ip, default is localhost
   port=8080,  # port number, default is 8080
   language="zh",  # language, default is English, optional: zh, en
   password="12345678",  # authorization password, default is None
   headless=False,  # set True to not auto open browser, default is False
   debug=False,  # set True to print debug info, default is False
)
```

All notes will be stored in the path specified by `path`,
and the `.data` folder will be created in your `path` directory.

English and Chinese languages are supported, and the default is English `en`.
If you want to use Chinese `zh`, you can use `language="zh"` parameter.

Open your browser and visit `http://127.0.0.1:8080` to start recording your ideas.

## Star History

<a href="https://star-history.com/?utm_source=bestxtools.com#MorvanZhou/rethink&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=MorvanZhou/rethink&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=MorvanZhou/rethink&type=Date" />
    <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=MorvanZhou/rethink&type=Date" />
  </picture>
</a>

