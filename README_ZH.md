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


[Rethink](https://rethink.run/zh) 表示重新思考，是基于 AI (大语言模型 LLM) 的个人知识、认知成长辅助工具。
[Rethink](https://rethink.run/zh) 在如下两个方面会协助你的知识、认知成长：

1. 超越笔记软件，在记录中，自动推荐、链接已有知识、认知，构建更加坚实的知识网络；

![internal link](https://github.com/MorvanZhou/rethink/raw/main/img/linking.gif)

2. 基于大语言模型 LLM 的 AI 知识扩展，让你的认知不断迭代、延展。

![AI recommend](https://github.com/MorvanZhou/rethink/raw/main/img/ai-recommend.gif)

## Rethink 主要有的特点

1. **个人认知成长工具**：[记录](https://rethink.run/zh/guide/use/record.html)、扩展你的思考，协助你高效成长；
2. **AI 推荐**：基于大语言模型 LLM 的 AI [知识扩展](https://rethink.run/zh/guide/use/ai-extend.html)，让你的认知不断迭代、延展；
3. **双向链接**：使用 [@ 链接](https://rethink.run/zh/guide/use/linking.html)
   或 [自动推荐](https://rethink.run/zh/guide/use/recommend.html) 到其它笔记；
4. **Markdown 语法**：无缝支持 [Markdown 语法](https://rethink.run/zh/guide/use/markdown.html)；
5. **本地存储**：Rethink 非常重视数据安全，并提供了[本地部署方案](https://rethink.run/zh/guide/self-hosted/install.html)。
   另外，也有在线版本 [https://rethink.run/r/zh/login](https://rethink.run/r/zh/login)，便于在多个平台之间同步；
6. **历史版本回溯**：支持[历史版本回溯](https://rethink.run/zh/guide/use/history.html)，方便查看和恢复历史版本；

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
