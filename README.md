# Rethink

---
[![Unittest](https://github.com/MorvanZhou/rethink/actions/workflows/python-package.yml/badge.svg)](https://github.com/MorvanZhou/rethink/actions/workflows/python-package.yml)
[![GitHub license](https://img.shields.io/github/license/MorvanZhou/rethink)](https://github.com/MorvanZhou/rethink/blob/master/LICENSE)

A note-taking app dependent on python.
The official web version can be found at [https://rethink.run](https://rethink.run).

## Installation

```shell
pip install rethink-note
```

## Usage

```python
import rethink

rethink.run()
```

```python
import rethink

rethink.run(
    path='.',
    host="127.0.0.1",
    port=8080,
    language="zh"
)
```
