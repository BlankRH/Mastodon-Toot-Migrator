# Intro

This is a tool to assist your migration to a new Mastodon instance! 

Currently the instance support exporting your toots, but not importing them. This tool provides a way to upload your toots to your account. Supports attachments.

Any suggestions or contribution is welcomed!

Example format:

[2000-01-01T00:00:00Z]
Hello World!

# Setup

## Requirements
python version >= 3.9

## Steps
1. clone the repo
```bash
git clone 
cd mastodon_toot_migrator
```
2. install the packages

```bash
pip3 install -r requirements.txt
pip3 install Mastodon.py
```

# Usage

run the script

```bash
python3 toot_migrator.py
```

## Parameters

# Acknowledgement
Thanks to Mastodon.py https://github.com/halcy/Mastodon.py