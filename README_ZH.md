# Rethink

[![测试](https://github.com/MorvanZhou/rethink/actions/workflows/python-tests.yml/badge.svg)](https://github.com/MorvanZhou/rethink/actions/workflows/python-tests.yml)
[![License](https://img.shields.io/github/license/MorvanZhou/rethink)](https://github.com/MorvanZhou/rethink/blob/master/LICENSE)
<a href="https://pypi.org/project/retk" target="_blank">
<img src="https://img.shields.io/pypi/v/retk?color=%2334D058&label=pypi%20package" alt="Package version">
</a>
<a href="https://pypi.org/project/retk" target="_blank">
<img src="https://img.shields.io/pypi/pyversions/retk.svg?color=%2334D058" alt="Supported Python versions">
</a>

<p align="center">
  <a href="README.md" target="_blank">English</a> | <strong>简体中文</strong>
</p>


Rethink 表示重新思考，是对个人成长的新理解。

每次记下新的认知时，相关的老认知都会自动涌现，交叉贯通，新旧认知不断 类比-迁移。
使得每次记录都有再次发光的机会。所以 Rethink 的中文名是 比移。

官方网页版可以在 [https://rethink.run](https://rethink.run) 找到。

![demo](https://github.com/MorvanZhou/rethink/raw/main/img/demo.gif)

## 让想法主动找你

让爱记录的人，没有无效记录。即使有源源不断的信息输入，也不用担心找不到，想不起。

我们引入推荐机制，让每一条记录都可以再次发光。 让它在未来的某个时刻，会再次回到面前，成为新认知的一部分。

## Rethink 主要有的特点

1. **双向链接**：使用 @ 链接到其它笔记；
2. **Markdown 语法**：无缝支持 Markdown 语法；
3. **自动关联**：在编写时自动推荐相关笔记，积极帮助您建立知识网络；
4. **本地存储**：Rethink 非常重视数据安全。您可以将数据存储在本地存储中。另外，也有在线版本 https://rethink.run
   ，便于在多个平台之间同步；
5. **多语言**：支持多种语言，包括中文和英文。

安装部署方式：

- [使用 Docker 容器化部署](#使用-docker-容器化部署)
- [使用 Python 部署](#使用-python-部署)

## 使用 Docker 容器化部署

### 拉取镜像：

```shell
docker pull morvanzhou/rethink
```

### 运行容器：

为了保证数据安全，您应该将本地路径挂载到容器中。

```shell
docker run \
 -p 8080:8080 \
 -v /your/data/path:/.data \
 morvanzhou/rethink
```

现在你可以在浏览器中访问 `http://127.0.0.1:8080` 使用服务。

如果你想自定义其他端口，你除了需要修改 `-p` 参数的前半部分，还需要添加一个环境变量 `API_URL` 来重定向前端服务中的 API 的地址：
请确保 `API_URL` 里的端口号和 `-p` 参数的前半部分一致 (在下面案例中的 `8001` 端口)。

```shell 
docker run \
 -e API_URL=http://127.0.0.1:8081 \
 -p 8081:8080 \
 -v /your/data/path:/.data \
 morvanzhou/rethink
```

如果你想做为 Rethink 鉴权，你可以添加环境变量 `APP_PASSWORD`：

```shell
docker run \
 -e APP_PASSWORD=12345678 \
 -p 8080:8080 \
 -v /your/data/path:/.data \
 morvanzhou/rethink
```

### 全部可配置的环境变量：

- `API_URL`：前端服务中 API 的地址，默认为 `http://127.0.0.1:8080`
- `APP_PASSWORD`：鉴权密码，默认为 None
- `APP_LANGUAGE`：语言，默认为英语，可选值：zh, en

## 使用 Python 部署

### 通过 pip 安装

第二种安装使用 Rethink 的方法是通过 pip 安装。然后用 python 直接启动服务。

首次安装：

```shell
pip install retk
```

更新：

```shell
pip install -U retk
```

### 通过 Python 配置

使用 `retk.run()` 方式，快速启动笔记 web 服务，并将你的笔记数据本地化保存，
默认保存路径为此脚本路径下的 `.data` 文件夹：

```python
import retk

retk.run()
```

如果需要更多自定义运行设置，可以使用 `retk.run()` 的参数：

```python
import retk

retk.run(
   path='.',  # 存储笔记的路径，默认为当前目录
   host="127.0.0.1",  # 主机 IP，默认为 localhost
   port=8080,  # 端口号，默认为 8080
   language="zh",  # 语言，默认为英语。可选值：zh, en
   password="12345678",  # 鉴权密码，默认为 None
   headless=False,  # 设置为 True 时不自动打开浏览器，默认为 False
   debug=False,  # 设置为 True 时打印调试信息，默认为 False
)
```

所有笔记都会被存储在 `path` 路径下，默认会在当前目录下创建 `.data`
文件夹。如果你想在其他路径创建数据文件夹，可以使用 `path` 参数。

当前语言暂时只英语和中文，且默认为英文 `en`，如果你想使用中文 `zh`，可以使用 `language` 参数。

打开浏览器，访问 `http://127.0.0.1:8080`，开始记录想法。

## Star History

<a href="https://star-history.com/?utm_source=bestxtools.com#MorvanZhou/rethink&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=MorvanZhou/rethink&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=MorvanZhou/rethink&type=Date" />
    <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=MorvanZhou/rethink&type=Date" />
  </picture>
</a>
