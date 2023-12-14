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

## 为什么有 Rethink

Rethink 的诞生源于我无法找到一款真正满足我的需求的记笔记应用。我对记笔记应用的期望包括：

1. **轻松记录**：在捕捉想法时，Rethink 提供了快速且无缝的记录过程；
2. **便捷应用**：为了实现便捷应用，仅仅记录笔记是不够的。记录的信息应该能够形成一个知识网络，
   使您积累的知识随着时间的推移不断增值。这个基础使得有效应用成为可能，
   每个新记录的想法都有助于加强和巩固现有的知识网络。

## Rethink 主要有的特点

1. **双向链接**：知识网络至关重要。Rethink 允许您在笔记中一键 @ 链接到其他笔记；
2. **Markdown 语法**：无缝支持 Markdown 语法，笔记格式更易控制；
3. **自动关联**：笔记太多？记不住以前写过什么？无法有效形成笔记网络？Rethink 在您编写时自动推荐相关笔记，积极帮助您建立知识网络；（正在开发中）
4. **本地存储**：Rethink 非常重视数据安全。您可以将数据存储在本地存储中。或者，您也可以使用在线版本 https://rethink.run
   ，便于在多个平台之间同步；
5. **多语言**：支持多种语言，包括中文和英文。

## 安装

首次安装：

```shell
pip install rethink-note
```

更新：

```shell
pip install -U rethink-note
```

## 使用

使用 `rethink.run()` 方式，快速启动笔记 web 服务，并将你的笔记数据本地化保存，
默认保存路径为此脚本路径下的 `.data` 文件夹：

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

打开浏览器，访问 `http://127.0.0.1:8080`，开始记录想法。
