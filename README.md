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


[Rethink](https://rethink.run) represents rethinking and is an AI (Large Language Model, LLM)
based personal knowledge and cognitive growth assistant tool.
[Rethink](https://rethink.run) will assist your knowledge and cognitive growth in the following two aspects:

1. Going beyond note-taking software,
   it automatically recommends and links existing knowledge and cognition when recording,
   building a more solid knowledge network;

![internal link](https://github.com/MorvanZhou/rethink/raw/main/img/linking.gif)

2. AI knowledge expansion based on the LLM, allowing your cognition to continuously iterate and extend.

![AI recommend](https://github.com/MorvanZhou/rethink/raw/main/img/ai-recommend.gif)

## Main Features of Rethink

1. **[Personal Cognitive Growth Tool](https://rethink.run/start/#personal-cognitive-growth-tool)**:
   Record and extend your thinking, assisting you in efficient growth;
2. **[AI Recommendation](https://rethink.run/guide/use/ai-extend.html)**:
   AI knowledge expansion based on the large language model LLM, allowing your cognition to continuously iterate and
   extend;
3. **[Bidirectional Linking](https://rethink.run/guide/use/recommend.html)**:
   Use @ linking or automatic recommendation to other notes;
4. **[Markdown Syntax](https://rethink.run/guide/use/markdown.html)**: Seamless support for Markdown syntax;
5. **[Local Storage](https://rethink.run/guide/self-hosted/install.html)**:
   Rethink highly values data security and provides a local deployment solution.
   In addition, there is an online version at [https://rethink.run/r/login](https://rethink.run/r/login) for
   synchronization between multiple platforms;
6. **[History Version Tracking](https://rethink.run/guide/use/history.html)**:
   Supports history version tracking, making it easy to view and restore historical versions;

Installation and deployment methods:

- [Deploy using Docker containerization](#deploy-using-docker-containerization)
- [Deploy using Python](#deploy-using-python)

## Deploy using Docker containerization

### Pull the image:

```shell
docker pull morvanzhou/rethink
```

### Run the container:

To ensure data security, you should mount the local path to the container.

```shell
docker run \
 -p 8080:8080 \
 -v /your/data/path:/.data \
 morvanzhou/rethink
```

Now you can access `http://127.0.0.1:8080` in your browser to use the service.

If you want to customize other ports, in addition to modifying the first half of the `-p` parameter, you also need to
add an environment variable `API_URL` to redirect the API address in the frontend service:
Make sure the port number in `API_URL` is consistent with the first half of the `-p` parameter (port `8001` in the
following example).

```shell 
docker run \
 -e API_URL=http://127.0.0.1:8081 \
 -p 8081:8080 \
 -v /your/data/path:/.data \
 morvanzhou/rethink
```

If you want to use Rethink authentication, you can add the environment variable `APP_PASSWORD`:

```shell
docker run \
 -e APP_PASSWORD=12345678 \
 -p 8080:8080 \
 -v /your/data/path:/.data \
 morvanzhou/rethink
```

### All configurable environment variables:

- `API_URL`: API address in the frontend service, default is `http://127.0.0.1:8080`
- `APP_PASSWORD`: Authentication password, default is None
- `APP_LANGUAGE`: Language, default is English, optional values: zh, en

## Deploy using Python

### Install via pip

The second way to install and use Rethink is through pip installation. Then start the service directly with Python.

Initial installation:

```shell
pip install retk
```

Update:

```shell
pip install -U retk
```

### Configure with Python

Use the `retk.run()` method to quickly start

## Star History

<a href="https://star-history.com/?utm_source=bestxtools.com#MorvanZhou/rethink&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=MorvanZhou/rethink&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=MorvanZhou/rethink&type=Date" />
    <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=MorvanZhou/rethink&type=Date" />
  </picture>
</a>

