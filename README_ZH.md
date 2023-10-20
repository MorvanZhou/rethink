# Rethink

[![单元测试](https://github.com/MorvanZhou/rethink/actions/workflows/python-app.yml/badge.svg)](https://github.com/MorvanZhou/rethink/actions/workflows/python-app.yml)
[![GitHub 许可证](https://img.shields.io/github/license/MorvanZhou/rethink)](https://github.com/MorvanZhou/rethink/blob/master/LICENSE)
<a href="https://pypi.org/project/rethink-note" target="_blank">
<img src="https://img.shields.io/pypi/v/rethink-note?color=%2334D058&label=pypi%20package" alt="Package version">
</a>
<a href="https://pypi.org/project/rethink-note" target="_blank">
<img src="https://img.shields.io/pypi/pyversions/rethink-note.svg?color=%2334D058" alt="Supported Python versions">
</a>

<p align="center">
  <a href="README.md" target="_blank">English</a> | <strong>简体中文</strong>
</p>


一个依赖于 Python 的笔记应用。
官方网页版可以在 [https://rethink.run](https://rethink.run) 找到。

## 安装

```shell
pip install rethink-note
```

更新：

```shell
pip install -U rethink-note
```

## 使用

使用默认设置运行：

```python
import rethink

rethink.run()
```

使用自定义设置运行：

```python
import rethink

rethink.run(
    path='.',  # 存储笔记的路径，默认为当前目录
    host="127.0.0.1",  # 主机 IP，默认为 localhost
    port=8080,  # 端口号，默认为 8080
    language="zh"  # 语言，默认为英语。可选值：zh, en
)
```
