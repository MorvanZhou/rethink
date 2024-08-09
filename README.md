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


Rethink represents rethinking and is an AI (Large Language Model, LLM)
based personal knowledge and cognitive growth assistant tool.
Rethink will assist your knowledge and cognitive growth in the following two aspects:

1. Going beyond note-taking software,
   it automatically recommends and links existing knowledge and cognition when recording,
   building a more solid knowledge network;
2. AI knowledge expansion based on the large language model LLM,
   allowing your cognition to continuously iterate and extend.

Each time you record new cognition, relevant old cognition will automatically emerge,
intersecting and connecting, and new and old cognition will continuously analogize and transfer.
This allows each record to have the opportunity to shine again.

Please visit [https://rethink.run](https://rethink.run) to experience or view detailed introductions.

Go beyond note-taking software, automatically recommend links
within the existing knowledge system when recording new cognition and knowledge:

![internal link](https://github.com/MorvanZhou/rethink/raw/main/img/demo.gif)

AI knowledge expansion based on the large language model LLM,
allowing your cognition to continuously iterate and extend:

![AI recommend](https://github.com/MorvanZhou/rethink/raw/main/img/ai_recommend.gif)

## Main Features of Rethink

1. **Personal Cognitive Growth Tool**: [Record](https://rethink.run/guide/use/record.html) and extend your thinking,
   assisting you in efficient growth;
2. **AI Recommendation**: AI [knowledge expansion](https://rethink.run/guide/use/ai-extend.html) based on the large
   language model LLM, allowing your cognition to continuously iterate and extend;
3. **Bidirectional Linking**: Use [@ linking](https://rethink.run/guide/use/linking.html)
   or [automatic recommendation](https://rethink.run/guide/use/recommend.html) to other notes;
4. **Markdown Syntax**: Seamless support for [Markdown syntax](https://rethink.run/guide/use/markdown.html);
5. **Local Storage**: Rethink highly values data security and provides
   a [local deployment solution](https://rethink.run/guide/self-hosted/install.html).
   In addition, there is an online version at [https://rethink.run/r/login](https://rethink.run/r/login) for
   synchronization between multiple platforms;
6. **History Version Tracking**: Supports [history version tracking](https://rethink.run/guide/use/history.html), making
   it easy to view and restore historical versions;

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

