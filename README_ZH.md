# Rethink

[![测试](https://github.com/MorvanZhou/rethink/actions/workflows/python-app.yml/badge.svg)](https://github.com/MorvanZhou/rethink/actions/workflows/python-app.yml)
[![License](https://img.shields.io/github/license/MorvanZhou/rethink)](https://github.com/MorvanZhou/rethink/blob/master/LICENSE)
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

![image](https://github.com/MorvanZhou/rethink/blob/main/img/notes-page.png?raw=true)

![editor](https://github.com/MorvanZhou/rethink/blob/main/img/editor.png?raw=true)

![phone](https://github.com/MorvanZhou/rethink/blob/main/img/phone.png?raw=true)

## 安装

```shell
pip install rethink-note
```

更新：

```shell
pip install -U rethink-note
```

## 使用

使用 `rethink.run()` 方式，快速启动笔记 web 服务，并将你的笔记数据本地化保存：

```python
import rethink

rethink.run()
```

如果需要更多自定义运行设置，可以使用 `rethink.run()` 的参数：

```python
import rethink

rethink.run(
    path='.',  # 存储笔记的路径，默认为当前目录
    host="127.0.0.1",  # 主机 IP，默认为 localhost
    port=8080,  # 端口号，默认为 8080
    language="zh"  # 语言，默认为英语。可选值：zh, en
)
```

所有笔记都会被存储在 `path` 路径下，默认会在当前目录下创建 `.data`
文件夹。如果你想在其他路径创建数据文件夹，可以使用 `path` 参数。

当前语言暂时只英语和中文，且默认为英文 `en`，如果你想使用中文 `zh`，可以使用 `language` 参数。
