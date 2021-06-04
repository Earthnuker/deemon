---
layout: default
title: Download
parent: Commands
---

# Download
{: .no_toc }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---
deemon includes a command line interface to the deemix library allowing you to download by artist, artist ID, album ID or URL.

## By Artist
```bash
$ deemon download My Awesome Band
```

## By Artist ID
```bash
$ deemon download --artist-id 1234
```

## By Album ID
```bash
$ deemon download --album-id 1234
```

## By URL
Monitoring by URL was implemented with the intention of using it for integration with automation tools like Siri Shortcuts.

```bash
$ deemon download --url https://www.deezer.com/us/artist/1234
```

## Configuration Overrides
You can override the config.json and specify one-off settings for downloads such as bitrate and record type:

```bash
## Download all album releases in FLAC format by My Band

$ deemon download My Band --bitrate 9 --record-type album
```