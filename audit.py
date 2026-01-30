#!/usr/bin/env python3
import os
import re
import sys
import concurrent.futures
from urllib.parse import urlparse, urljoin, unquote
from collections import defaultdict, Counter
from pathlib import Path
import time

# Try to import required libraries
try:
    from bs4 import BeautifulSoup
    import requests
    from colorama import init, Fore, Style
except ImportError as e:
    print(f"Missing required library: {e.name}")
    print("Please run: pip install beautifulsoup4 requests colorama")
    sys.exit(1)

# Initialize colorama
init(autoreset=True)

class SEOAudit:
    def __init__(self, root_dir='.'):
        self.root_dir = os.path.abspath(root_dir)
        self.base_url = None
        self.keywords = []
        self.files_to_scan = []
        
        # Stats
        self.score = 100
        self.stats = {
            'pages_scanned': 0,
            'internal_links': 0,
            'external_links': 0,
            'dead_links_local': 0,
            'dead_links_external': 0,
            'warnings': 0,
            'h1_missing': 0,
            'h1_multiple': 0,
            'schema_missing': 0,
            'orphans': 0
        }
        
        # Graph for Link Equity
        self.inbound_links = defaultdict(int) # target -> count
        self.all_pages = set() # Set of all scanned absolute file paths
        
        # Issues storage
        self.issues = [] # List of dicts: {'type': 'ERROR'|'WARN', 'msg': str, 'file': str}
        self.external_links = set() # Set of tuples: (url, source_file)

        # Configs
        self.ignore_paths = ['.git', 'node_modules', '__pycache__', 'MasterTool']
        self.ignore_url_prefixes = ['/go/', 'cdn-cgi', 'javascript:', 'mailto:', '#', 'tel:']
        self.ignore_files_contain = ['google', '404.html', 'baidu_verify']

    def log(self, type_str, msg, file_path=None):
        """Log an issue and deduct points"""
        weight = 0
        if type_str == 'ERROR':
            if 'Dead Link' in msg: weight = 10
            elif 'H1' in msg: weight = 5
            elif 'External Dead Link' in msg: weight = 5
        elif type_str == 'WARN':
            if 'URL' in msg: weight = 2
            elif 'Schema' in msg: weight = 2
            elif 'Orphan' in msg: weight = 5
        
        self.score = max(0, self.score - weight)
        
        entry = {'type': type_str, 'msg': msg, 'file': file_path}
        self.issues.append(entry)
        
        # Immediate console output for errors/warns? Maybe just store and print later or print as we go.
        # Let's print as we go for better UX
        color = Fore.RED if type_str == 'ERROR' else Fore.YELLOW
        prefix = f"[{type_str}]"
        
        rel_path = os.path.relpath(file_path, self.root_dir) if file_path else "Global"
        print(f"{color}{prefix} {rel_path}: {msg}")

    def auto_configure(self):
        print(f"{Fore.CYAN}[INFO] Auto-configuring...")
        index_path = os.path.join(self.root_dir, 'index.html')
        
        if os.path.exists(index_path):
            try:
                with open(index_path, 'r', encoding='utf-8', errors='ignore') as f:
                    soup = BeautifulSoup(f, 'html.parser')
                    
                    # Base URL
                    canonical = soup.find('link', rel='canonical')
                    if canonical and canonical.get('href'):
                        self.base_url = canonical['href']
                    else:
                        og_url = soup.find('meta', property='og:url')
                        if og_url and og_url.get('content'):
                            self.base_url = og_url['content']
                    
                    if not self.base_url:
                        print(f"{Fore.YELLOW}[WARN] Could not detect Base URL from index.html (canonical or og:url). Assuming relative paths.")
                    else:
                        print(f"{Fore.GREEN}[SUCCESS] Base URL detected: {self.base_url}")
                    
                    # Keywords
                    meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
                    if meta_keywords and meta_keywords.get('content'):
                        self.keywords = [k.strip() for k in meta_keywords['content'].split(',')]
                        print(f"{Fore.GREEN}[SUCCESS] Keywords detected: {self.keywords}")
                        
            except Exception as e:
                print(f"{Fore.RED}[ERROR] Failed to parse index.html: {e}")
        else:
            print(f"{Fore.YELLOW}[WARN] Root index.html not found.")

    def is_ignored_path(self, path):
        for ignore in self.ignore_paths:
            if ignore in path:
                return True
        return False

    def is_ignored_file(self, filename):
        for ignore in self.ignore_files_contain:
            if ignore in filename:
                return True
        return False

    def is_ignored_url(self, url):
        for prefix in self.ignore_url_prefixes:
            if url.startswith(prefix):
                return True
        return False

    def crawl_local(self):
        print(f"{Fore.CYAN}[INFO] Scanning local files...")
        for root, dirs, files in os.walk(self.root_dir):
            # Filter directories
            dirs[:] = [d for d in dirs if d not in self.ignore_paths]
            
            for file in files:
                if not file.endswith('.html'):
                    continue
                if self.is_ignored_file(file):
                    continue
                
                full_path = os.path.join(root, file)
                self.files_to_scan.append(full_path)
                self.all_pages.add(full_path)

        print(f"{Fore.CYAN}[INFO] Found {len(self.files_to_scan)} HTML files to audit.")

    def audit_file(self, file_path):
        self.stats['pages_scanned'] += 1
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                soup = BeautifulSoup(content, 'html.parser')
                
                # C. Semantics
                # H1 Check
                h1s = soup.find_all('h1')
                if len(h1s) == 0:
                    self.log('ERROR', 'Missing <h1> tag', file_path)
                    self.stats['h1_missing'] += 1
                elif len(h1s) > 1:
                    self.log('WARN', 'Multiple <h1> tags found', file_path)
                    self.stats['h1_multiple'] += 1
                
                # Schema Check
                schema = soup.find('script', type='application/ld+json')
                if not schema:
                    self.log('WARN', 'Missing Schema.org JSON-LD', file_path)
                    self.stats['schema_missing'] += 1
                
                # Breadcrumb Check
                # aria-label="breadcrumb" or class="breadcrumb"
                breadcrumb = soup.find(attrs={'aria-label': 'breadcrumb'}) or \
                             soup.find(class_=re.compile(r'breadcrumb', re.I))
                # Note: Breadcrumb check is usually INFO or WARN if strictly required. 
                # Requirement says "Check...", let's just log if missing? 
                # The requirements didn't specify penalty for breadcrumb explicitly in Reporting section, 
                # but put it under Semantics. I'll add a mild warning if easy, or just skip penalty to avoid noise if not strictly enforced.
                # Let's treat it as info/debug for now unless strictly required to penalize.
                # Actually, requirement #3 Reporting says: "[WARN]: ... 缺少 Schema (-2分), 孤岛页面 (-5分)".
                # Breadcrumb is not listed in penalty. I won't log WARN for breadcrumb to avoid clutter, 
                # or maybe just INFO.
                
                # A. Smart Path Resolution & Dead Link
                links = soup.find_all('a', href=True)
                for link in links:
                    href = link['href'].strip()
                    
                    # Check External Link Protection
                    if href.startswith('http') and 'claudemai.top' not in href:
                         rel = link.get('rel', [])
                         if isinstance(rel, str): rel = rel.split()
                         
                         missing = []
                         for req in ['nofollow', 'noopener', 'noreferrer']:
                             if req not in rel:
                                 missing.append(req)
                         
                         if missing:
                             self.log('WARN', f"External link missing rel attributes ({', '.join(missing)}): {href}", file_path)
                             self.stats['warnings'] += 1

                    self.check_link(file_path, href)

        except Exception as e:
            print(f"{Fore.RED}[ERROR] Error processing {file_path}: {e}")

    def resolve_local_path(self, source_file, href):
        """
        Resolve href to absolute file path.
        Returns: (resolved_path_or_None, is_directory_match)
        """
        # Strip query params and hash
        href_clean = href.split('#')[0].split('?')[0]
        
        # If absolute URL matching base_url (if set)
        if self.base_url and href_clean.startswith(self.base_url):
            path_part = href_clean[len(self.base_url):]
            if not path_part.startswith('/'):
                path_part = '/' + path_part
        elif href_clean.startswith('http') or href_clean.startswith('//'):
            return None, False # External
        else:
            path_part = href_clean

        # Handle root relative vs relative
        if path_part.startswith('/'):
            # Root relative
            # e.g. /blog/post -> root_dir/blog/post
            target_path = os.path.join(self.root_dir, path_part.lstrip('/'))
        else:
            # Relative
            # e.g. post -> current_dir/post
            target_path = os.path.join(os.path.dirname(source_file), path_part)
            
        # Check possibilities
        # 1. Exact match (rare for clean URLs unless file ext is present)
        if os.path.isfile(target_path):
            return target_path, False
            
        # 2. As .html
        if os.path.isfile(target_path + '.html'):
            return target_path + '.html', False
            
        # 3. As directory (index.html)
        if os.path.isdir(target_path):
            index_path = os.path.join(target_path, 'index.html')
            if os.path.isfile(index_path):
                return index_path, True
                
        return None, False

    def check_link(self, source_file, href):
        if not href or self.is_ignored_url(href):
            return

        # External Links
        if href.startswith('http') or href.startswith('//'):
            # Check if it's actually internal (matches base_url)
            if self.base_url and href.startswith(self.base_url):
                # Treat as internal, but warn about absolute path usage?
                self.log('WARN', f"Internal link uses full domain: {href}. Should be path-only.", source_file)
                # Continue to resolve locally
            else:
                self.external_links.add((href, source_file))
                self.stats['external_links'] += 1
                return

        self.stats['internal_links'] += 1

        # Warnings for internal links
        if not href.startswith('/') and not href.startswith('#'):
             self.log('WARN', f"Relative path used: {href}. Recommended: start with /", source_file)
        
        if '.html' in href.split('/')[-1]: # Check if filename part has .html
             self.log('WARN', f"Link contains .html extension: {href}. Recommended: Clean URL", source_file)

        # Dead Link Detection
        resolved_path, is_dir = self.resolve_local_path(source_file, href)
        
        if resolved_path:
            # Valid internal link
            self.inbound_links[resolved_path] += 1
        else:
            self.log('ERROR', f"Dead Link (Local): {href}", source_file)
            self.stats['dead_links_local'] += 1

    def check_external_links(self):
        print(f"{Fore.CYAN}[INFO] Checking {len(self.external_links)} external links...")
        
        def check_url(item):
            url, source = item
            try:
                # Use HEAD request
                headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                r = requests.head(url, headers=headers, timeout=5, allow_redirects=True)
                
                # Special handling for 403 (Cloudflare/WAF) on known valid sites
                if r.status_code == 403 and any(d in url for d in ['claude.ai', 'anthropic.com']):
                    return None

                if r.status_code >= 400:
                    # Retry with GET just in case HEAD is blocked
                    r = requests.get(url, headers=headers, timeout=5, stream=True)
                    
                    if r.status_code == 403 and any(d in url for d in ['claude.ai', 'anthropic.com']):
                        return None
                        
                    if r.status_code >= 400:
                        return (url, source, r.status_code)
            except requests.RequestException as e:
                return (url, source, str(e))
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(check_url, item) for item in self.external_links]
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    url, source, error = result
                    self.log('ERROR', f"External Dead Link: {url} (Status/Error: {error})", source)
                    self.stats['dead_links_external'] += 1

    def analyze_graph(self):
        print(f"{Fore.CYAN}[INFO] Analyzing site structure...")
        
        # Orphans
        # Filter out index.html from root as it's the entry point (usually)
        # Also, pages might be linked from navigation which is in every file, so they shouldn't be orphans.
        # But if we just scan <a> tags, and headers are in files, it should be fine.
        
        # Root index is naturally an orphan if nothing links TO it, but that's expected for home.
        root_index = os.path.join(self.root_dir, 'index.html')
        
        for page in self.all_pages:
            if page == root_index:
                continue
            if self.inbound_links[page] == 0:
                self.log('WARN', "Orphan Page (No incoming links)", page)
                self.stats['orphans'] += 1
                
        # Top Pages
        print(f"\n{Fore.BLUE}=== Top 10 Pages by Inbound Links ===")
        sorted_pages = sorted(self.inbound_links.items(), key=lambda x: x[1], reverse=True)[:10]
        for path, count in sorted_pages:
            rel = os.path.relpath(path, self.root_dir)
            print(f"{rel}: {count} links")

    def run(self):
        start_time = time.time()
        print(f"{Fore.MAGENTA}=== Starting SEO Audit ==={Style.RESET_ALL}")
        
        self.auto_configure()
        self.crawl_local()
        
        if not self.files_to_scan:
            print(f"{Fore.RED}[ERROR] No HTML files found to scan.")
            return

        for file in self.files_to_scan:
            self.audit_file(file)
            
        self.check_external_links()
        self.analyze_graph()
        
        duration = time.time() - start_time
        self.generate_report(duration)

    def generate_report(self, duration):
        print(f"\n{Fore.MAGENTA}=== Audit Report ==={Style.RESET_ALL}")
        print(f"Time Taken: {duration:.2f}s")
        print(f"Pages Scanned: {self.stats['pages_scanned']}")
        print(f"Internal Links: {self.stats['internal_links']}")
        print(f"External Links: {self.stats['external_links']}")
        print("-" * 30)
        
        print(f"{Fore.RED}Errors (Dead Links/H1): {self.stats['dead_links_local'] + self.stats['dead_links_external'] + self.stats['h1_missing']}")
        print(f"{Fore.YELLOW}Warnings (URL/Schema/Orphans): {self.stats['warnings'] + self.stats['schema_missing'] + self.stats['orphans']}")
        
        print("-" * 30)
        score_color = Fore.GREEN
        if self.score < 80: score_color = Fore.YELLOW
        if self.score < 50: score_color = Fore.RED
        
        print(f"Final Score: {score_color}{self.score}/100{Style.RESET_ALL}")
        
        if self.score < 100:
            print(f"\n{Fore.CYAN}Actionable Advice:{Style.RESET_ALL}")
            if self.stats['dead_links_local'] > 0:
                print("- Fix local dead links immediately.")
            if self.stats['h1_missing'] > 0:
                print("- Ensure every page has exactly one <h1> tag.")
            if self.stats['schema_missing'] > 0:
                print("- Add structured data (JSON-LD) to your pages.")
            if self.stats['orphans'] > 0:
                print("- Link to orphan pages from other parts of your site.")
            print("- Consider running a fix script if available.")

if __name__ == "__main__":
    audit = SEOAudit()
    audit.run()
