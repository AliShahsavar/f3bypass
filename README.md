
# f3bypass
![Built With Python](https://img.shields.io/badge/Built%20With-Python-3776AB?logo=python&logoColor=white)
![MIT License](https://img.shields.io/badge/License-MIT-green)
![Security Testing](https://img.shields.io/badge/Purpose-Security%20Testing-red)<br>

A fast and lightweight 403 bypass testing tool for authorized security assessments.
`f3bypass` automates common access-control bypass techniques and helps security researchers identify misconfigured web servers, reverse proxies, load balancers, and authorization mechanisms that may incorrectly expose restricted resources.

## Features

* Path manipulation testing
* Header-based bypass testing
* HTTP method testing
* Protocol switching tests (HTTP ↔ HTTPS)
* User-Agent spoofing
* Content-Type manipulation
* Host header testing
* CRLF injection testing
* Null-byte injection testing
* IPv4 and IPv6 header variations
* Multi-threaded scanning
* Colored terminal output
* Automatic baseline comparison
* Result export support

## Installation

### Clone the repository

```bash
git clone https://github.com/yourusername/f3bypass.git
cd f3bypass
```

### Install dependencies

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install requests urllib3
```

## Usage

### Basic Scan

```bash
python3 f3bypass.py https://target.com/admin
```

### Custom Threads

```bash
python3 f3bypass.py https://target.com/admin -t 50
```

### Custom Timeout

```bash
python3 f3bypass.py https://target.com/admin -T 15
```

### Show All Responses

```bash
python3 f3bypass.py https://target.com/admin --all
```

### Save Results

```bash
python3 f3bypass.py https://target.com/admin -o results.txt
```

## Available Options

```text
-t, --threads          Number of worker threads
-T, --timeout          Request timeout in seconds
-d, --delay            Delay between requests
-a, --all              Show all responses
-o, --output           Save results to a file

--skip-path            Skip path manipulation tests
--skip-headers         Skip header injection tests
--skip-methods         Skip HTTP method tests
--skip-protocol        Skip protocol tests
--skip-useragent       Skip User-Agent tests
--skip-content-type    Skip Content-Type tests
--skip-host            Skip Host header tests
--skip-crlf            Skip CRLF injection tests
--skip-nullbyte        Skip null-byte tests
--skip-ipv6            Skip IPv6 header tests
```

## Example

```bash
python3 f3bypass.py https://target.com/secret -t 30 --all
```

Example output:

```text
[200] [HEADER] IP Header: X-Forwarded-For: 127.0.0.1
<<< POSSIBLE BYPASS!

[302] [METHOD] HTTP Method: OPTIONS

[403] [PATH] Path Bypass: /secret/
```

## How It Works

The tool first performs a baseline request to determine the original response status.

It then generates hundreds of access-control bypass variations and compares the results against the baseline. Responses that differ from the original access-denied response may indicate a potential authorization bypass and should be manually verified.

## Disclaimer

This tool is intended for:

* Security research
* Penetration testing
* Bug bounty programs
* Internal security assessments

Only test systems you own or have explicit permission to assess.

The author assumes no responsibility for misuse or damage caused by this software.

## License

MIT License
