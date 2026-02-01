import os
import re
import json
import random
from bs4 import BeautifulSoup
from datetime import datetime
import glob

# Configuration
DOMAIN = "https://claudemai.top"
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BLOG_DIR = os.path.join(ROOT_DIR, 'blog')
INDEX_PATH = os.path.join(ROOT_DIR, 'index.html')

class SiteBuilder:
    def __init__(self):
        self.assets = {
            'nav': None,
            'footer': None,
            'icons': []
        }
        self.posts_metadata = []

    def run(self):
        print("🚀 Starting build process...")
        
        # Phase 1: Smart Extraction
        print("Phase 1: Extracting assets from index.html...")
        self.extract_assets()
        
        # Phase 1.5: Collect Metadata (for Recommendations and Homepage)
        print("Phase 1.5: Collecting blog metadata...")
        self.collect_metadata()
        
        # Phase 2 & 3: Process Blog Posts
        print("Phase 2 & 3: Processing blog posts...")
        self.process_blog_posts()
        
        # Phase 3.4: Global Update (Homepage)
        print("Phase 3.4: Updating homepage...")
        self.update_homepage()
        
        # Phase 3.5: Process Blog Index
        print("Phase 3.5: Processing blog index...")
        self.process_blog_index()
        
        # Phase 4: Generate Sitemap
        print("Phase 4: Generating sitemap.xml...")
        self.generate_sitemap()
        
        print("✅ Build completed successfully.")

    def clean_link(self, url):
        if not url:
            return url
        # Handle anchors
        if url.startswith('#'):
            return url
        # Handle external links
        if url.startswith('http'):
            return url
        
        # Normalize paths
        # If it's index.html, it becomes /
        if url == 'index.html' or url == '/index.html':
            return '/'
        
        # Remove .html extension
        if url.endswith('.html'):
            url = url[:-5]
        
        # Ensure root relative for internal links (basic heuristic)
        if not url.startswith('/') and not url.startswith('#'):
             # If it's just "blog/", it's fine. If it's "blog/foo", fine.
             # But we want to ensure consistency. 
             # For this specific site, let's assume links in nav/footer are relative to root or absolute.
             # In index.html, they are likely relative or absolute.
             # We should make them absolute path relative to root (starting with /) to work on blog pages.
             pass
        
        # Fix specific cases based on observation
        if url == 'blog/' or url == '/blog/':
            return '/blog/'
            
        return url

    def standardize_url(self, url, is_asset=False):
        """
        Standardizes URLs to be root-relative.
        For assets (images, icons), keeps extensions.
        For pages, removes .html.
        """
        if not url or url.startswith(('http', 'data:', 'mailto:')):
            return url
            
        # Handle anchors - for extracted assets (nav/footer) that will be used on other pages,
        # we need to make them absolute paths to the homepage anchors.
        if url.startswith('#'):
            return '/' + url

        # Remove ./ if present
        if url.startswith('./'):
            url = url[2:]

        # If it's already root relative
        if url.startswith('/'):
            path = url
        else:
            # Assume it was relative to root in index.html, so prepend /
            path = '/' + url

        if is_asset:
            return path
        
        # Page link standardization
        if path.endswith('/index.html'):
            return path.replace('/index.html', '/')
        if path.endswith('index.html'):
            return path.replace('index.html', '/')
        if path.endswith('.html'):
            return path[:-5]
        
        return path

    def process_links(self, container):
        if not container:
            return
        for a in container.find_all('a'):
            if a.get('href'):
                # Standardize
                a['href'] = self.standardize_url(a['href'])
                
                # Protect External
                url = a['href']
                if url.startswith('http') and DOMAIN not in url:
                    rel = a.get('rel', [])
                    if isinstance(rel, str):
                        rel = rel.split()
                    
                    for val in ['nofollow', 'noopener', 'noreferrer']:
                        if val not in rel:
                            rel.append(val)
                    a['rel'] = rel

    def extract_assets(self):
        if not os.path.exists(INDEX_PATH):
            raise FileNotFoundError(f"index.html not found at {INDEX_PATH}")

        with open(INDEX_PATH, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')

        # 1. Extract Nav
        nav = soup.find('nav')
        if nav:
            # Clean links in nav
            self.process_links(nav)
            self.assets['nav'] = nav
        else:
            print("⚠️ Warning: <nav> not found in index.html")

        # 2. Extract Footer
        footer = soup.find('footer')
        if footer:
            # Clean links in footer
            self.process_links(footer)
            self.assets['footer'] = footer
        else:
            print("⚠️ Warning: <footer> not found in index.html")

        # 3. Extract Icons
        # <link rel="icon">, <link rel="shortcut icon">, <link rel="apple-touch-icon">
        head = soup.find('head')
        if head:
            icon_rels = ['icon', 'shortcut icon', 'apple-touch-icon']
            for link in head.find_all('link'):
                if any(rel in link.get('rel', []) for rel in icon_rels):
                    # Force root relative path
                    href = link.get('href', '')
                    if href:
                        if not href.startswith('http'):
                            # Ensure it starts with /
                            if not href.startswith('/'):
                                href = '/' + href
                        link['href'] = href
                        self.assets['icons'].append(link)

    def collect_metadata(self):
        # Find all html files in blog_dir
        blog_files = glob.glob(os.path.join(BLOG_DIR, '*.html'))
        for file_path in blog_files:
            filename = os.path.basename(file_path)
            if filename == 'index.html':
                continue # Handle index separately or skip for now if it's an aggregation page

            with open(file_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')

            title = soup.title.string if soup.title else filename
            if title:
                title = title.strip()
                # Remove year numbers (4 digits) from title for evergreen content
                import re
                title = re.sub(r'\s*20\d{2}\s*', ' ', title).strip()
                title = re.sub(r'\s+', ' ', title) # Clean up multiple spaces
            
            # Extract description
            desc_tag = soup.find('meta', attrs={'name': 'description'})
            description = desc_tag['content'].strip() if desc_tag and desc_tag.get('content') else ''

            # Extract date (try to find it in the content as seen in example)
            # Example: <span class="...">2026-01-13</span>
            # Heuristic: Find a span with date format
            date_str = datetime.now().strftime('%Y-%m-%d')
            
            # 1. Try to find in existing JSON-LD
            json_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_scripts:
                try:
                    data = json.loads(script.string)
                    # Handle if it's a list or dict
                    if isinstance(data, list):
                        for item in data:
                            if item.get('@type') == 'BlogPosting' and item.get('datePublished'):
                                date_str = item['datePublished']
                                break
                    elif isinstance(data, dict):
                         if data.get('@type') == 'BlogPosting' and data.get('datePublished'):
                            date_str = data['datePublished']
                except:
                    pass
            
            # 2. If not found in JSON-LD or it's today's date (default), try to find in text but avoid scripts
            if date_str == datetime.now().strftime('%Y-%m-%d'):
                date_pattern = re.compile(r'\d{4}-\d{2}-\d{2}')
                # Find all text nodes that match the pattern
                text_nodes = soup.find_all(string=date_pattern)
                for node in text_nodes:
                    # Check parent to ensure it's not a script or style or existing JSON-LD
                    if node.parent.name not in ['script', 'style', 'head', 'title', 'meta']:
                        date_str = node.strip()
                        break
            
            # Validation: Ensure date_str is actually a date (YYYY-MM-DD)
            # If it contains JSON or is too long, reset it or try to extract valid date
            date_match = re.search(r'\d{4}-\d{2}-\d{2}', str(date_str))
            if date_match:
                date_str = date_match.group(0)
            else:
                # Fallback if no valid date found
                date_str = datetime.now().strftime('%Y-%m-%d')

            # Extract first image for thumbnail if possible, else default
            # In the example, there is no specific image in the content, but og:image is set
            og_image = soup.find('meta', property='og:image')
            image = og_image['content'] if og_image else 'https://claudemai.top/og-cover.svg'

            url = f"/blog/{filename.replace('.html', '')}"

            self.posts_metadata.append({
                'title': title.split(' - ')[0].strip(), # Remove site name suffix if present
                'description': description,
                'date': date_str,
                'url': url,
                'image': image,
                'filename': filename,
                'file_path': file_path
            })
        
        # Sort by date descending (assuming string sort works for YYYY-MM-DD)
        self.posts_metadata.sort(key=lambda x: x['date'], reverse=True)

    def process_blog_posts(self):
        for post in self.posts_metadata:
            print(f"  Processing {post['filename']}...")
            self.reconstruct_page(post)

    def reconstruct_page(self, post):
        file_path = post['file_path']
        with open(file_path, 'r', encoding='utf-8') as f:
            original_soup = BeautifulSoup(f.read(), 'html.parser')

        # Create new soup
        new_soup = BeautifulSoup('<!DOCTYPE html><html lang="zh-CN" class="scroll-smooth"></html>', 'html.parser')
        html = new_soup.html
        
        # --- HEAD RECONSTRUCTION ---
        head = new_soup.new_tag('head')
        html.append(head)

        # Group A: Basic Metadata
        head.append(new_soup.new_tag('meta', charset='utf-8'))
        head.append(new_soup.new_tag('meta', attrs={'name': 'viewport', 'content': 'width=device-width, initial-scale=1.0'}))
        title_tag = new_soup.new_tag('title')
        title_tag.string = f"{post['title']} - ClaudeMai"
        head.append(title_tag)
        head.append(BeautifulSoup('\n', 'html.parser'))

        # Group B: SEO Core
        head.append(new_soup.new_tag('meta', attrs={'name': 'description', 'content': post['description']}))
        
        keywords_tag = original_soup.find('meta', attrs={'name': 'keywords'})
        keywords = keywords_tag['content'] if keywords_tag else "Claude, Claude AI, Claude 3.5 Sonnet, Opus 4.1"
        head.append(new_soup.new_tag('meta', attrs={'name': 'keywords', 'content': keywords}))
        
        canonical_url = f"{DOMAIN}{post['url']}"
        head.append(new_soup.new_tag('link', rel='canonical', href=canonical_url))
        head.append(BeautifulSoup('\n', 'html.parser'))

        # Group C: Indexing & Geo
        head.append(new_soup.new_tag('meta', attrs={'name': 'robots', 'content': 'index, follow'}))
        head.append(new_soup.new_tag('meta', attrs={'http-equiv': 'content-language', 'content': 'zh-cn'}))
        head.append(new_soup.new_tag('link', rel='alternate', hreflang='x-default', href=canonical_url))
        head.append(new_soup.new_tag('link', rel='alternate', hreflang='zh', href=canonical_url))
        head.append(new_soup.new_tag('link', rel='alternate', hreflang='zh-CN', href=canonical_url))
        head.append(BeautifulSoup('\n', 'html.parser'))

        # Group D: Brand & Resources
        # Favicons
        for icon in self.assets['icons']:
            head.append(icon) # This copies the tag
        
        # CSS/JS (Tailwind, Fonts) - Hardcoded based on requirements/existing file
        head.append(new_soup.new_tag('script', src="https://cdn.tailwindcss.com"))
        head.append(new_soup.new_tag('link', href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;700;800&family=JetBrains+Mono:wght@400&display=swap", rel="stylesheet"))
        
        # Tailwind Config
        tailwind_config = """
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: {
                        sans: ['Inter', 'Noto Sans SC', 'sans-serif'],
                        mono: ['JetBrains Mono', 'monospace'],
                        serif: ['Georgia', 'serif'],
                    },
                    colors: {
                        claude: {
                            50: '#fdf8f6',
                            100: '#f2e8e5',
                            500: '#e56f48',
                            600: '#da7756',
                            700: '#c55f3e',
                            900: '#4a2b20',
                        }
                    }
                }
            }
        }
        """
        script_tag = new_soup.new_tag('script')
        script_tag.string = tailwind_config
        head.append(script_tag)
        
        # Preserve custom styles if any
        style_tag = original_soup.find('style')
        if style_tag:
            head.append(style_tag)
        head.append(BeautifulSoup('\n', 'html.parser'))

        # Group E: Schema
        schema_data = {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": post['title'],
            "description": post['description'],
            "datePublished": post['date'],
            "author": {
                "@type": "Organization",
                "name": "ClaudeMai"
            },
            "publisher": {
                "@type": "Organization",
                "name": "ClaudeMai",
                "logo": {
                    "@type": "ImageObject",
                    "url": "https://claudemai.top/logo.svg"
                }
            },
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": canonical_url
            }
        }
        
        breadcrumb_data = {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": 1,
                    "name": "首页",
                    "item": "https://claudemai.top/"
                },
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": "博客",
                    "item": "https://claudemai.top/blog/"
                },
                {
                    "@type": "ListItem",
                    "position": 3,
                    "name": post['title'],
                    "item": canonical_url
                }
            ]
        }
        
        schema_script = new_soup.new_tag('script', type='application/ld+json')
        schema_script.string = json.dumps([schema_data, breadcrumb_data], ensure_ascii=False, indent=2)
        head.append(schema_script)

        # --- BODY RECONSTRUCTION ---
        body = new_soup.new_tag('body', attrs={'class': 'bg-slate-50 text-slate-900 font-sans antialiased selection:bg-claude-600 selection:text-white'})
        html.append(body)

        # 1. Inject Nav (Layout Sync)
        if self.assets['nav']:
            body.append(self.assets['nav'])

        # 2. Main Content
        # We need to extract the 'main' content from the original file.
        # Assuming the original file has a <main> tag or we grab the article.
        original_main = original_soup.find('main')
        if original_main:
            # We need to process links inside main as well (Phase 46.1)
            self.process_links(original_main)
            
            # 2.1 Inject Recommendation at bottom of article
            article = original_main.find('article')
            if article:
                # Remove existing recommendations to avoid duplication
                # Look for divs with specific class or content "推荐阅读"
                for div in article.find_all('div', class_='mt-12 pt-8 border-t border-slate-200'):
                    if div.find('h3', string=re.compile('推荐阅读')):
                        div.decompose()

                recommendation_html = self.generate_recommendations(current_post_url=post['url'])
                recommendation_soup = BeautifulSoup(recommendation_html, 'html.parser')
                article.append(recommendation_soup)
            
            body.append(original_main)
        else:
            # Fallback if no main tag (should not happen in good structure)
            body.append(new_soup.new_tag('main'))

        # 3. Inject Footer (Layout Sync)
        if self.assets['footer']:
            body.append(self.assets['footer'])

        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(str(new_soup.prettify()))

    def generate_recommendations(self, current_post_url):
        # Pick 3 posts excluding current one
        candidates = [p for p in self.posts_metadata if p['url'] != current_post_url]
        recommendations = candidates[:3] # Take top 3 recent ones
        
        if not recommendations:
            return ""

        html = """
        <div class="mt-12 pt-8 border-t border-slate-200">
            <h3 class="text-xl font-bold text-slate-900 mb-6">推荐阅读</h3>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        """
        
        for rec in recommendations:
            style = self.determine_post_style(rec['title'], rec.get('filename', ''))

            html += f"""
                <a href="{rec['url']}" class="group bg-white rounded-xl border border-slate-200 overflow-hidden hover:shadow-lg hover:-translate-y-1 transition-all duration-300">
                    <div class="h-32 bg-gradient-to-br {style['bg_gradient']} flex items-center justify-center relative overflow-hidden">
                        <div class="absolute inset-0 opacity-10 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')]"></div>
                        <div class="text-4xl transform group-hover:scale-110 transition-transform duration-300 drop-shadow-sm">{style['icon']}</div>
                    </div>
                    <div class="p-4">
                        <div class="flex items-center gap-2 mb-2">
                            <span class="px-2 py-0.5 rounded-full {style['badge_color']} text-[10px] font-bold border">{style['badge_text']}</span>
                            <span class="text-slate-400 text-xs">{rec['date']}</span>
                        </div>
                        <h4 class="font-bold text-slate-900 group-hover:text-claude-600 transition-colors mb-2 line-clamp-2 text-sm md:text-base">{rec['title']}</h4>
                    </div>
                </a>
            """
        
        html += """
            </div>
        </div>
        """
        return html

    def determine_post_style(self, title, filename=""):
        title = title.lower()
        
        # Specific filename mapping to ensure unique icons
        if filename:
            if 'academic-writing' in filename:
                return {
                    "icon": "🎓",
                    "bg_gradient": "from-purple-100 to-purple-50",
                    "text_color": "text-purple-600",
                    "badge_color": "bg-purple-50 text-purple-600 border-purple-100",
                    "badge_text": "学术科研"
                }
            elif 'usage-limits' in filename:
                return {
                    "icon": "🛡️",
                    "bg_gradient": "from-red-100 to-red-50",
                    "text_color": "text-red-600",
                    "badge_color": "bg-red-50 text-red-600 border-red-100",
                    "badge_text": "避坑指南"
                }
            elif 'vs-chatgpt' in filename:
                return {
                    "icon": "⚖️",
                    "bg_gradient": "from-teal-100 to-teal-50",
                    "text_color": "text-teal-600",
                    "badge_color": "bg-teal-50 text-teal-600 border-teal-100",
                    "badge_text": "深度评测"
                }
            elif 'buy-claude-pro' in filename:
                return {
                    "icon": "💳", 
                    "bg_gradient": "from-indigo-100 to-indigo-50",
                    "text_color": "text-indigo-600",
                    "badge_color": "bg-indigo-50 text-indigo-600 border-indigo-100",
                    "badge_text": "购买指南"
                }
            elif 'register-claude' in filename:
                return {
                    "icon": "🆔",
                    "bg_gradient": "from-emerald-100 to-emerald-50",
                    "text_color": "text-emerald-600",
                    "badge_color": "bg-emerald-50 text-emerald-600 border-emerald-100",
                    "badge_text": "注册教程"
                }
            elif 'how-to-use-claude' in filename:
                return {
                    "icon": "🧭", 
                    "bg_gradient": "from-amber-100 to-amber-50",
                    "text_color": "text-amber-600",
                    "badge_color": "bg-amber-50 text-amber-600 border-amber-100",
                    "badge_text": "新手必读"
                }
            elif 'what-is-claude-code' in filename:
                return {
                    "icon": "⚡", 
                    "bg_gradient": "from-sky-100 to-sky-50",
                    "text_color": "text-sky-600",
                    "badge_color": "bg-sky-50 text-sky-600 border-sky-100",
                    "badge_text": "效率工具"
                }
            elif 'what-is-claude' in filename: # General what-is-claude
                return {
                    "icon": "🤖",
                    "bg_gradient": "from-orange-100 to-orange-50",
                    "text_color": "text-orange-600",
                    "badge_color": "bg-orange-50 text-orange-600 border-orange-100",
                    "badge_text": "入门指南"
                }

        # Fallback to keyword matching if filename not matched or not provided
        # Default
        style = {
            "icon": "📄",
            "bg_gradient": "from-gray-100 to-gray-50",
            "text_color": "text-gray-600",
            "badge_color": "bg-gray-100 text-gray-600 border-gray-100",
            "badge_text": "资讯"
        }

        # 1. Security / Account (Red)
        if any(k in title for k in ['封号', '限制', '解封', '安全', 'ban', 'account']):
            style.update({
                "icon": "🛡️",
                "bg_gradient": "from-red-100 to-red-50",
                "text_color": "text-red-600",
                "badge_color": "bg-red-50 text-red-600 border-red-100",
                "badge_text": "避坑指南"
            })
        
        # 2. Coding / Tech (Blue)
        elif any(k in title for k in ['code', '代码', '编程', 'python', 'api', '开发']):
            style.update({
                "icon": "💻",
                "bg_gradient": "from-blue-100 to-blue-50",
                "text_color": "text-blue-600",
                "badge_color": "bg-blue-50 text-blue-600 border-blue-100",
                "badge_text": "编程开发"
            })
            if "tool" in title or "工具" in title or "code" in title:
                style["badge_text"] = "效率工具"
                style["icon"] = "⚡"
                style["bg_gradient"] = "from-sky-100 to-sky-50"

        # 3. Academic / Writing (Purple)
        elif any(k in title for k in ['论文', '写作', '学术', '润色', 'writing', 'research']):
            style.update({
                "icon": "🎓",
                "bg_gradient": "from-purple-100 to-purple-50",
                "text_color": "text-purple-600",
                "badge_color": "bg-purple-50 text-purple-600 border-purple-100",
                "badge_text": "学术科研"
            })

        # 4. Comparison (Teal)
        elif any(k in title for k in ['vs', '对比', '区别', '哪个好']):
            style.update({
                "icon": "⚖️",
                "bg_gradient": "from-teal-100 to-teal-50",
                "text_color": "text-teal-600",
                "badge_color": "bg-teal-50 text-teal-600 border-teal-100",
                "badge_text": "深度评测"
            })

        # 5. Registration (Green)
        elif any(k in title for k in ['注册', 'register', 'sign up', 'login']):
            style.update({
                "icon": "🆔",
                "bg_gradient": "from-emerald-100 to-emerald-50",
                "text_color": "text-emerald-600",
                "badge_color": "bg-emerald-50 text-emerald-600 border-emerald-100",
                "badge_text": "注册教程"
            })

        # 6. General Claude (Orange)
        elif "claude" in title:
            style.update({
                "icon": "🤖",
                "bg_gradient": "from-orange-100 to-orange-50",
                "text_color": "text-orange-600",
                "badge_color": "bg-orange-50 text-orange-600 border-orange-100",
                "badge_text": "入门指南"
            })
            
        return style

    def update_homepage(self):
        if not os.path.exists(INDEX_PATH):
            return

        with open(INDEX_PATH, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
        
        # Locate the blog section
        # Based on file read earlier: id="blog"
        blog_section = soup.find(id='blog')
        if not blog_section:
            print("⚠️ Warning: #blog section not found in index.html")
            return
            
        # Find the container for cards. 
        # Structure: <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
        grid_container = blog_section.find('div', class_=lambda x: x and 'grid-cols-1' in x and 'md:grid-cols-3' in x)
        
        if not grid_container:
            print("⚠️ Warning: Blog grid container not found in index.html")
            return
            
        # Clear existing cards
        grid_container.clear()
        
        # Add latest 3 posts
        latest_posts = self.posts_metadata[:3]
        
        for post in latest_posts:
            style = self.determine_post_style(post['title'], post.get('filename', ''))
            
            card_html = f"""
            <a href="{post['url']}" class="group bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden hover:shadow-xl hover:-translate-y-1 transition-all duration-300">
                <div class="h-48 bg-gradient-to-br {style['bg_gradient']} flex items-center justify-center relative overflow-hidden">
                    <div class="absolute inset-0 opacity-10 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')]"></div>
                    <div class="text-6xl transform group-hover:scale-110 transition-transform duration-300 drop-shadow-sm">{style['icon']}</div>
                </div>
                <div class="p-6">
                    <div class="flex items-center gap-2 mb-3">
                        <span class="px-2.5 py-0.5 rounded-full {style['badge_color']} text-xs font-bold border">{style['badge_text']}</span>
                        <span class="text-slate-400 text-xs">{post['date']}</span>
                    </div>
                    <h3 class="text-xl font-bold text-slate-900 mb-3 group-hover:text-claude-600 transition-colors line-clamp-2">{post['title']}</h3>
                    <p class="text-slate-600 text-sm line-clamp-3 mb-4">
                        {post['description']}
                    </p>
                    <div class="flex items-center text-claude-600 text-sm font-semibold group-hover:underline decoration-2 underline-offset-2">
                        阅读全文 <svg class="w-4 h-4 ml-1 transform group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3"></path></svg>
                    </div>
                </div>
            </a>
            """
            grid_container.append(BeautifulSoup(card_html, 'html.parser'))
            
        # Final Polish: Process ALL links in homepage to ensure external link protection
        self.process_links(soup)

        with open(INDEX_PATH, 'w', encoding='utf-8') as f:
            f.write(str(soup.prettify()))

    def process_blog_index(self):
        blog_index_path = os.path.join(BLOG_DIR, 'index.html')
        if not os.path.exists(blog_index_path):
            return

        with open(blog_index_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
            
        # 1. Update Content (Sync with metadata)
        # Find the main article container: <div class="lg:col-span-8 space-y-8">
        article_container = soup.find('div', class_=lambda x: x and 'lg:col-span-8' in x and 'space-y-8' in x)
        
        if article_container:
            # Identify pagination to preserve it
            pagination = article_container.find('div', class_=lambda x: x and 'flex' in x and 'justify-center' in x and 'border-t' in x)
            
            # Save pagination element
            pagination_element = pagination.extract() if pagination else None
            
            # Clear all content (including comments and existing articles)
            article_container.clear()
            
            # Generate new articles from metadata
            new_articles = []
            for post in self.posts_metadata:
                style = self.determine_post_style(post['title'], post.get('filename', ''))

                card_html = f"""
                <article class="group bg-white rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-all overflow-hidden">
                    <div class="flex flex-col sm:flex-row h-full">
                        <div class="sm:w-64 h-48 sm:h-auto bg-gradient-to-br {style['bg_gradient']} flex items-center justify-center relative shrink-0 overflow-hidden">
                             <div class="absolute inset-0 opacity-10 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')]"></div>
                             <div class="text-6xl transform group-hover:scale-110 transition-transform duration-300 drop-shadow-sm">{style['icon']}</div>
                        </div>
                        <div class="p-8 flex flex-col justify-center flex-1">
                             <div class="flex items-center gap-3 text-sm text-slate-500 mb-3">
                                  <span class="px-2.5 py-0.5 rounded-full {style['badge_color']} text-xs font-bold border">{style['badge_text']}</span>
                                  <span>{post['date']}</span>
                             </div>
                             <h2 class="text-2xl font-bold text-slate-900 mb-3 group-hover:text-claude-600 transition-colors">
                                  <a href="{post['url']}" class="hover:underline">{post['title']}</a>
                             </h2>
                             <p class="text-slate-600 leading-relaxed mb-6 line-clamp-3">
                                  {post['description']}
                             </p>
                             <a href="{post['url']}" class="inline-flex items-center text-sm font-semibold text-claude-600 hover:text-claude-700">
                                  阅读全文 <svg class="w-4 h-4 ml-1 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3"></path></svg>
                             </a>
                        </div>
                    </div>
                </article>
                """
                new_articles.append(BeautifulSoup(card_html, 'html.parser'))

            # Append new articles
            for tag in new_articles:
                article_container.append(tag)
                
            # Restore pagination
            if pagination_element:
                article_container.append(pagination_element)
        
        # 2. Standardize links in main content
        main = soup.find('main')
        if main:
            self.process_links(main)
        
        # Standardize links in nav and footer (just in case they were manual)
        nav = soup.find('nav')
        if nav:
            self.process_links(nav)

        footer = soup.find('footer')
        if footer:
            self.process_links(footer)
                    
        with open(blog_index_path, 'w', encoding='utf-8') as f:
            f.write(str(soup.prettify()))

    def generate_sitemap(self):
        sitemap_path = os.path.join(ROOT_DIR, 'sitemap.xml')
        
        urls = []
        
        # 1. Homepage
        urls.append({
            'loc': DOMAIN + '/',
            'lastmod': datetime.now().strftime('%Y-%m-%d'),
            'changefreq': 'daily',
            'priority': '1.0'
        })
        
        # 2. Blog Index
        urls.append({
            'loc': DOMAIN + '/blog/',
            'lastmod': datetime.now().strftime('%Y-%m-%d'),
            'changefreq': 'daily',
            'priority': '0.9'
        })
        
        # 3. Legal
        legal_path = os.path.join(ROOT_DIR, 'legal.html')
        if os.path.exists(legal_path):
             urls.append({
                'loc': DOMAIN + '/legal',
                'lastmod': datetime.now().strftime('%Y-%m-%d'),
                'changefreq': 'monthly',
                'priority': '0.3'
            })

        # 4. Blog Posts
        for post in self.posts_metadata:
            # post['url'] is already clean (e.g. /blog/foo)
            urls.append({
                'loc': DOMAIN + post['url'],
                'lastmod': post['date'],
                'changefreq': 'weekly',
                'priority': '0.8'
            })
            
        # Generate XML
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        
        for url in urls:
            xml += '  <url>\n'
            xml += f"    <loc>{url['loc']}</loc>\n"
            xml += f"    <lastmod>{url['lastmod']}</lastmod>\n"
            xml += f"    <changefreq>{url['changefreq']}</changefreq>\n"
            xml += f"    <priority>{url['priority']}</priority>\n"
            xml += '  </url>\n'
            
        xml += '</urlset>'
        
        with open(sitemap_path, 'w', encoding='utf-8') as f:
            f.write(xml)
        print(f"  Generated sitemap with {len(urls)} URLs.")

if __name__ == "__main__":
    builder = SiteBuilder()
    builder.run()
