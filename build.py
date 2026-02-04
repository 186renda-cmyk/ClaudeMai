import os
import re
import json
import random
import math
import shutil
from bs4 import BeautifulSoup
from datetime import datetime
import glob

# Configuration
DOMAIN = "https://claudemai.top"
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BLOG_DIR = os.path.join(ROOT_DIR, 'blog')
INDEX_PATH = os.path.join(ROOT_DIR, 'index.html')

POSTS_PER_PAGE = 6

# Helper for Slug Generation (Automated approach)
SLUG_MAPPING = {
    # 1. Tutorial / Guide (新手必读)
    "注册教程": "tutorial",
    "新手必读": "tutorial",
    "入门指南": "tutorial",
    "购买指南": "tutorial",
    "使用教程": "tutorial",
    
    # 2. Safety (避坑指南)
    "避坑指南": "safety",
    
    # 3. Tools / Efficiency (效率工具)
    "效率工具": "tools",
    "编程开发": "tools",
    "学术科研": "tools",
    "前沿技术": "tools",
    
    # 4. Reviews / Models (深度评测)
    "深度评测": "reviews",
    "旗舰模型": "reviews",
    
    # 5. News (资讯)
    "资讯": "news"
}

SLUG_DISPLAY_NAMES = {
    "academic": "学术科研",
    "safety": "避坑指南",
    "reviews": "深度评测",
    "models": "旗舰模型",
    "pricing": "购买指南",
    "tutorial": "新手必读", 
    "tools": "效率工具",
    "coding": "编程开发",
    "news": "资讯",
    "guide": "使用教程"
}

class SiteBuilder:
    def __init__(self):
        self.assets = {
            'nav': None,
            'footer': None,
            'icons': []
        }
        self.posts_metadata = []
        self.categories = {} # {slug: {name: str, posts: []}}

    def run(self):
        print("🚀 Starting build process...")
        
        # Phase 1: Smart Extraction
        print("Phase 1: Extracting assets from index.html...")
        self.extract_assets()
        
        # Phase 1.5: Collect Metadata
        print("Phase 1.5: Collecting blog metadata...")
        self.collect_metadata()
        
        # Phase 2 & 3: Process Blog Posts
        print("Phase 2 & 3: Processing blog posts...")
        self.process_blog_posts()
        
        # Phase 3.4: Global Update (Homepage)
        print("Phase 3.4: Updating homepage...")
        self.update_homepage()
        
        # Phase 3.5: Process Blog Index (Intelligent Single Page)
        print("Phase 3.5: Processing blog index (SPA Mode)...")
        self.process_blog_index_spa()
        
        # Phase 4: Generate Sitemap
        print("Phase 4: Generating sitemap.xml...")
        self.generate_sitemap()
        
        print("✅ Build completed successfully.")

    # ... (clean_link, standardize_url, process_links, extract_assets methods remain same)
    def clean_link(self, url):
        if not url: return url
        if url.startswith('#') or url.startswith('http'): return url
        if url == 'index.html' or url == '/index.html': return '/'
        if url.endswith('.html'): url = url[:-5]
        if url == 'blog/' or url == '/blog/': return '/blog/'
        return url

    def standardize_url(self, url, is_asset=False):
        if not url or url.startswith(('http', 'data:', 'mailto:')): return url
        if url.startswith('#'): return '/' + url
        if url.startswith('./'): url = url[2:]
        if url.startswith('/'): path = url
        else: path = '/' + url
        if is_asset: return path
        if path.endswith('/index.html'): return path.replace('/index.html', '/')
        if path.endswith('index.html'): return path.replace('index.html', '/')
        if path.endswith('.html'): return path[:-5]
        return path

    def process_links(self, container):
        if not container: return
        for a in container.find_all('a'):
            if a.get('href'):
                a['href'] = self.standardize_url(a['href'])
                url = a['href']
                if url.startswith('http') and DOMAIN not in url:
                    rel = a.get('rel', [])
                    if isinstance(rel, str): rel = rel.split()
                    for val in ['nofollow', 'noopener', 'noreferrer']:
                        if val not in rel: rel.append(val)
                    a['rel'] = rel

    def extract_assets(self):
        if not os.path.exists(INDEX_PATH):
            raise FileNotFoundError(f"index.html not found at {INDEX_PATH}")
        with open(INDEX_PATH, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
        nav = soup.find('nav')
        if nav:
            self.process_links(nav)
            self.assets['nav'] = nav
        footer = soup.find('footer')
        if footer:
            self.process_links(footer)
            self.assets['footer'] = footer
        head = soup.find('head')
        if head:
            icon_rels = ['icon', 'shortcut icon', 'apple-touch-icon']
            for link in head.find_all('link'):
                if any(rel in link.get('rel', []) for rel in icon_rels):
                    href = link.get('href', '')
                    if href:
                        if not href.startswith('http') and not href.startswith('/'):
                            href = '/' + href
                        link['href'] = href
                        self.assets['icons'].append(link)

    def collect_metadata(self):
        blog_files = glob.glob(os.path.join(BLOG_DIR, '*.html'))
        for file_path in blog_files:
            filename = os.path.basename(file_path)
            if filename == 'index.html': continue

            with open(file_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')

            title = soup.title.string if soup.title else filename
            if title:
                title = title.strip()
                title = re.sub(r'\s*20\d{2}\s*', ' ', title).strip()
                title = re.sub(r'\s+', ' ', title)
            
            desc_tag = soup.find('meta', attrs={'name': 'description'})
            description = desc_tag['content'].strip() if desc_tag and desc_tag.get('content') else ''

            date_str = None
            json_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, list):
                        for item in data:
                            if item.get('@type') == 'BlogPosting' and item.get('datePublished'):
                                date_str = item['datePublished']
                                break
                    elif isinstance(data, dict):
                         if data.get('@type') == 'BlogPosting' and data.get('datePublished'):
                            date_str = data['datePublished']
                except: pass
            if not date_str:
                date_str = datetime.now().strftime('%Y-%m-%d')
                date_pattern = re.compile(r'\d{4}-\d{2}-\d{2}')
                text_nodes = soup.find_all(string=date_pattern)
                for node in text_nodes:
                    if node.parent.name not in ['script', 'style', 'head', 'title', 'meta']:
                        date_str = node.strip()
                        break
            
            date_match = re.search(r'\d{4}-\d{2}-\d{2}', str(date_str))
            if date_match: date_str = date_match.group(0)
            else: date_str = datetime.now().strftime('%Y-%m-%d')

            og_image = soup.find('meta', property='og:image')
            image = og_image['content'] if og_image else 'https://claudemai.top/og-cover.svg'
            url = f"/blog/{filename.replace('.html', '')}"
            style = self.determine_post_style(title, filename)
            
            category_name = style['badge_text']
            category_slug = SLUG_MAPPING.get(category_name, 'news')

            post_data = {
                'title': title.split(' - ')[0].strip(),
                'description': description,
                'date': date_str,
                'url': url,
                'image': image,
                'filename': filename,
                'file_path': file_path,
                'style': style,
                'category_name': category_name,
                'category_slug': category_slug
            }
            
            self.posts_metadata.append(post_data)

            if category_slug not in self.categories:
                # Use standardized display name
                display_name = SLUG_DISPLAY_NAMES.get(category_slug, category_name)
                self.categories[category_slug] = {'name': display_name, 'posts': []}
            self.categories[category_slug]['posts'].append(post_data)
        
        self.posts_metadata.sort(key=lambda x: x['date'], reverse=True)
        for cat in self.categories.values():
            cat['posts'].sort(key=lambda x: x['date'], reverse=True)

    def process_blog_posts(self):
        for post in self.posts_metadata:
            print(f"  Processing {post['filename']}...")
            self.reconstruct_page(post)

    def reconstruct_page(self, post):
        # ... (Same as before, reusing logic)
        file_path = post['file_path']
        with open(file_path, 'r', encoding='utf-8') as f:
            original_soup = BeautifulSoup(f.read(), 'html.parser')

        new_soup = BeautifulSoup('<!DOCTYPE html><html lang="zh-CN" class="scroll-smooth"></html>', 'html.parser')
        html = new_soup.html
        
        head = new_soup.new_tag('head')
        html.append(head)
        head.append(new_soup.new_tag('meta', charset='utf-8'))
        head.append(new_soup.new_tag('meta', attrs={'name': 'viewport', 'content': 'width=device-width, initial-scale=1.0'}))
        title_tag = new_soup.new_tag('title')
        title_tag.string = f"{post['title']} - ClaudeMai"
        head.append(title_tag)
        head.append(new_soup.new_tag('meta', attrs={'name': 'description', 'content': post['description']}))
        keywords_tag = original_soup.find('meta', attrs={'name': 'keywords'})
        keywords = keywords_tag['content'] if keywords_tag else "Claude, Claude AI"
        head.append(new_soup.new_tag('meta', attrs={'name': 'keywords', 'content': keywords}))
        canonical_url = f"{DOMAIN}{post['url']}"
        head.append(new_soup.new_tag('link', rel='canonical', href=canonical_url))
        head.append(new_soup.new_tag('meta', attrs={'name': 'robots', 'content': 'index, follow'}))
        
        for icon in self.assets['icons']: head.append(icon) 
        head.append(new_soup.new_tag('script', src="https://cdn.tailwindcss.com"))
        head.append(new_soup.new_tag('link', href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;700;800&family=JetBrains+Mono:wght@400&display=swap", rel="stylesheet"))
        
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
                        claude: { 50: '#fdf8f6', 100: '#f2e8e5', 500: '#e56f48', 600: '#da7756', 700: '#c55f3e', 900: '#4a2b20' }
                    }
                }
            }
        }
        """
        script_tag = new_soup.new_tag('script')
        script_tag.string = tailwind_config
        head.append(script_tag)
        style_tag = original_soup.find('style')
        if style_tag: head.append(style_tag)

        # Schema (Simplified for brevity in this tool call)
        schema_data = {
            "@context": "https://schema.org", "@type": "BlogPosting",
            "headline": post['title'], "description": post['description'], "datePublished": post['date'],
            "author": { "@type": "Organization", "name": "ClaudeMai" }
        }
        schema_script = new_soup.new_tag('script', type='application/ld+json')
        schema_script.string = json.dumps(schema_data, ensure_ascii=False)
        head.append(schema_script)

        body = new_soup.new_tag('body', attrs={'class': 'bg-slate-50 text-slate-900 font-sans antialiased selection:bg-claude-600 selection:text-white'})
        html.append(body)

        if self.assets['nav']: body.append(self.assets['nav'])

        original_main = original_soup.find('main')
        if original_main:
            self.process_links(original_main)
            
            # Sync visual date with metadata date
            time_tag = original_main.find('time', itemprop='datePublished')
            if time_tag:
                time_tag['datetime'] = post['date']
                time_tag.string = post['date']

            article = original_main.find('article')
            if article:
                for div in article.find_all('div', class_='mt-12 pt-8 border-t border-slate-200'):
                    if div.find('h3', string=re.compile('推荐阅读')): div.decompose()
                recommendation_html = self.generate_recommendations(current_post_url=post['url'])
                article.append(BeautifulSoup(recommendation_html, 'html.parser'))
            body.append(original_main)
        else: body.append(new_soup.new_tag('main'))

        if self.assets['footer']: body.append(self.assets['footer'])

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(str(new_soup.prettify()))

    def generate_recommendations(self, current_post_url):
        candidates = [p for p in self.posts_metadata if p['url'] != current_post_url]
        recommendations = candidates[:3]
        if not recommendations: return ""
        html = """<div class="mt-12 pt-8 border-t border-slate-200"><h3 class="text-xl font-bold text-slate-900 mb-6">推荐阅读</h3><div class="grid grid-cols-1 md:grid-cols-3 gap-6">"""
        for rec in recommendations:
            style = rec['style']
            html += f"""<a href="{rec['url']}" class="group bg-white rounded-xl border border-slate-200 overflow-hidden hover:shadow-lg hover:-translate-y-1 transition-all duration-300"><div class="h-32 bg-gradient-to-br {style['bg_gradient']} flex items-center justify-center relative overflow-hidden"><div class="absolute inset-0 opacity-10 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')]"></div><div class="text-4xl transform group-hover:scale-110 transition-transform duration-300 drop-shadow-sm">{style['icon']}</div></div><div class="p-4"><div class="flex items-center gap-2 mb-2"><span class="px-2 py-0.5 rounded-full {style['badge_color']} text-[10px] font-bold border">{style['badge_text']}</span><span class="text-slate-400 text-xs">{rec['date']}</span></div><h4 class="font-bold text-slate-900 group-hover:text-claude-600 transition-colors mb-2 line-clamp-2 text-sm md:text-base">{rec['title']}</h4></div></a>"""
        html += "</div></div>"
        return html

    def determine_post_style(self, title, filename=""):
        # (Logic same as before, condensed for brevity)
        title = title.lower()
        if filename:
            if 'academic' in filename: return {"icon": "🎓", "bg_gradient": "from-purple-100 to-purple-50", "text_color": "text-purple-600", "badge_color": "bg-purple-50 text-purple-600 border-purple-100", "badge_text": "学术科研"}
            if 'usage' in filename or 'trouble' in filename: return {"icon": "🛡️", "bg_gradient": "from-red-100 to-red-50", "text_color": "text-red-600", "badge_color": "bg-red-50 text-red-600 border-red-100", "badge_text": "避坑指南"}
            if 'vs' in filename: return {"icon": "⚖️", "bg_gradient": "from-teal-100 to-teal-50", "text_color": "text-teal-600", "badge_color": "bg-teal-50 text-teal-600 border-teal-100", "badge_text": "深度评测"}
            if 'buy' in filename: return {"icon": "💳", "bg_gradient": "from-indigo-100 to-indigo-50", "text_color": "text-indigo-600", "badge_color": "bg-indigo-50 text-indigo-600 border-indigo-100", "badge_text": "购买指南"}
            if 'register' in filename: return {"icon": "🆔", "bg_gradient": "from-emerald-100 to-emerald-50", "text_color": "text-emerald-600", "badge_color": "bg-emerald-50 text-emerald-600 border-emerald-100", "badge_text": "注册教程"}
            if 'how-to' in filename: return {"icon": "🧭", "bg_gradient": "from-amber-100 to-amber-50", "text_color": "text-amber-600", "badge_color": "bg-amber-50 text-amber-600 border-amber-100", "badge_text": "新手必读"}
            if 'opus' in filename: return {"icon": "🧠", "bg_gradient": "from-purple-100 to-purple-50", "text_color": "text-purple-600", "badge_color": "bg-purple-50 text-purple-600 border-purple-100", "badge_text": "旗舰模型"}
            if 'what-is-claude-agent' in filename: return {"icon": "🕵️", "bg_gradient": "from-slate-100 to-slate-50", "text_color": "text-slate-600", "badge_color": "bg-slate-50 text-slate-600 border-slate-100", "badge_text": "前沿技术"}
            if 'code' in filename: return {"icon": "⚡", "bg_gradient": "from-sky-100 to-sky-50", "text_color": "text-sky-600", "badge_color": "bg-sky-50 text-sky-600 border-sky-100", "badge_text": "效率工具"}
            if 'what-is-claude-for-excel' in filename: return {"icon": "📊", "bg_gradient": "from-green-100 to-green-50", "text_color": "text-green-600", "badge_color": "bg-green-50 text-green-600 border-green-100", "badge_text": "效率工具"}
            if 'what-is' in filename: return {"icon": "🤖", "bg_gradient": "from-orange-100 to-orange-50", "text_color": "text-orange-600", "badge_color": "bg-orange-50 text-orange-600 border-orange-100", "badge_text": "入门指南"}

        style = {"icon": "📄", "bg_gradient": "from-gray-100 to-gray-50", "text_color": "text-gray-600", "badge_color": "bg-gray-100 text-gray-600 border-gray-100", "badge_text": "资讯"}
        if any(k in title for k in ['封号', '限制', '解封', '安全']): style.update({"icon": "🛡️", "bg_gradient": "from-red-100 to-red-50", "text_color": "text-red-600", "badge_color": "bg-red-50 text-red-600 border-red-100", "badge_text": "避坑指南"})
        elif any(k in title for k in ['code', '代码', '编程']): style.update({"icon": "💻", "bg_gradient": "from-blue-100 to-blue-50", "text_color": "text-blue-600", "badge_color": "bg-blue-50 text-blue-600 border-blue-100", "badge_text": "编程开发"})
        return style

    def update_homepage(self):
        if not os.path.exists(INDEX_PATH): return
        with open(INDEX_PATH, 'r', encoding='utf-8') as f: soup = BeautifulSoup(f.read(), 'html.parser')
        blog_section = soup.find(id='blog')
        if not blog_section: return
        grid_container = blog_section.find('div', class_=lambda x: x and 'grid-cols-1' in x and 'md:grid-cols-3' in x)
        if not grid_container: return
        grid_container.clear()
        
        latest_posts = self.posts_metadata[:3]
        for post in latest_posts:
            style = post['style']
            card_html = f"""<a href="{post['url']}" class="group bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden hover:shadow-xl hover:-translate-y-1 transition-all duration-300"><div class="h-48 bg-gradient-to-br {style['bg_gradient']} flex items-center justify-center relative overflow-hidden"><div class="absolute inset-0 opacity-10 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')]"></div><div class="text-6xl transform group-hover:scale-110 transition-transform duration-300 drop-shadow-sm">{style['icon']}</div></div><div class="p-6"><div class="flex items-center gap-2 mb-3"><span class="px-2.5 py-0.5 rounded-full {style['badge_color']} text-xs font-bold border">{style['badge_text']}</span><span class="text-slate-400 text-xs">{post['date']}</span></div><h3 class="text-xl font-bold text-slate-900 mb-3 group-hover:text-claude-600 transition-colors line-clamp-2">{post['title']}</h3><p class="text-slate-600 text-sm line-clamp-3 mb-4">{post['description']}</p><div class="flex items-center text-claude-600 text-sm font-semibold group-hover:underline decoration-2 underline-offset-2">阅读全文 <svg class="w-4 h-4 ml-1 transform group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3"></path></svg></div></div></a>"""
            grid_container.append(BeautifulSoup(card_html, 'html.parser'))
        self.process_links(soup)
        with open(INDEX_PATH, 'w', encoding='utf-8') as f: f.write(str(soup.prettify()))

    def process_blog_index_spa(self):
        blog_index_path = os.path.join(BLOG_DIR, 'index.html')
        if not os.path.exists(blog_index_path): return

        with open(blog_index_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')

        # 0. Clean up existing injected scripts (Prevent duplication)
        for s in soup.find_all('script'):
            if s.string and 'const POSTS =' in s.string:
                s.decompose()

        # 1. Clean up existing static content & scripts
        article_container = soup.find('div', class_=lambda x: x and 'lg:col-span-8' in x and 'space-y-8' in x)
        if article_container: article_container.clear()
        
        # Remove old SPA scripts to prevent duplication
        for script in soup.find_all('script'):
            if script.string and ('const POSTS =' in script.string or 'const CATEGORIES =' in script.string):
                script.decompose()

        # 2. Inject Search & Filter UI
        ui_html = """
        <div class="space-y-6 mb-8">
            <!-- Search -->
            <div class="relative">
                <input type="text" id="searchInput" placeholder="搜索文章..." class="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-200 focus:border-claude-500 focus:ring-2 focus:ring-claude-200 transition-all outline-none">
                <svg class="w-5 h-5 text-slate-400 absolute left-3 top-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
            </div>
            <!-- Categories -->
            <div class="flex flex-wrap gap-2 overflow-x-auto pb-2 scrollbar-hide" id="categoryContainer">
                <!-- Injected by JS -->
            </div>
        </div>
        <!-- Posts Container -->
        <div id="postsContainer" class="space-y-6 min-h-[400px]">
            <!-- Injected by JS -->
        </div>
        <!-- Pagination -->
        <div id="paginationContainer" class="flex justify-center items-center gap-2 pt-8 border-t border-slate-200 mt-8">
            <!-- Injected by JS -->
        </div>
        """
        
        # Generate static fallback for SEO/No-JS
        noscript_html = '<noscript><div class="prose max-w-none mt-8"><h2>所有文章</h2><ul class="space-y-2">'
        for post in self.posts_metadata:
            noscript_html += f'<li><a href="{post["url"]}" class="text-claude-600 hover:underline">{post["title"]}</a> <span class="text-slate-400 text-sm">({post["date"]})</span></li>'
        noscript_html += '</ul></div></noscript>'

        if article_container:
            article_container.append(BeautifulSoup(ui_html + noscript_html, 'html.parser'))

        # 3. Clean sidebar (Remove static categories)
        self.update_sidebar(soup)

        # 4. Inject Data & Logic
        # Prepare data
        categories_list = [{'slug': 'all', 'name': '全部', 'count': len(self.posts_metadata)}]
        sorted_cats = sorted(self.categories.items(), key=lambda x: len(x[1]['posts']), reverse=True)
        for slug, data in sorted_cats:
            categories_list.append({'slug': slug, 'name': data['name'], 'count': len(data['posts'])})

        # Serialize data
        posts_json = json.dumps(self.posts_metadata, ensure_ascii=False)
        cats_json = json.dumps(categories_list, ensure_ascii=False)

        # JS Logic
        script_content = f"""
        const POSTS = {posts_json};
        const CATEGORIES = {cats_json};
        const POSTS_PER_PAGE = {POSTS_PER_PAGE};
        
        let state = {{
            category: 'all',
            page: 1,
            search: ''
        }};

        // Init
        document.addEventListener('DOMContentLoaded', () => {{
            // Restore state from URL
            const params = new URLSearchParams(window.location.search);
            if(params.has('category')) state.category = params.get('category');
            if(params.has('page')) state.page = parseInt(params.get('page'));
            if(params.has('search')) state.search = params.get('search');
            
            document.getElementById('searchInput').value = state.search;
            
            render();
            
            // Listeners
            document.getElementById('searchInput').addEventListener('input', (e) => {{
                state.search = e.target.value.toLowerCase();
                state.page = 1;
                updateURL();
                render();
            }});
        }});

        function updateURL() {{
            const url = new URL(window.location);
            if(state.category !== 'all') url.searchParams.set('category', state.category);
            else url.searchParams.delete('category');
            
            if(state.page > 1) url.searchParams.set('page', state.page);
            else url.searchParams.delete('page');
            
            if(state.search) url.searchParams.set('search', state.search);
            else url.searchParams.delete('search');
            
            window.history.pushState({{}}, '', url);
        }}

        function setCategory(slug) {{
            state.category = slug;
            state.page = 1;
            updateURL();
            render();
        }}

        function setPage(p) {{
            state.page = p;
            updateURL();
            render();
            window.scrollTo({{ top: 0, behavior: 'smooth' }});
        }}

        function render() {{
            renderCategories();
            
            // Filter
            let filtered = POSTS.filter(p => {{
                const matchCat = state.category === 'all' || p.category_slug === state.category;
                const matchSearch = !state.search || 
                    p.title.toLowerCase().includes(state.search) || 
                    p.description.toLowerCase().includes(state.search);
                return matchCat && matchSearch;
            }});
            
            // Paginate
            const totalPages = Math.ceil(filtered.length / POSTS_PER_PAGE) || 1;
            if (state.page > totalPages) state.page = 1;
            
            const start = (state.page - 1) * POSTS_PER_PAGE;
            const end = start + POSTS_PER_PAGE;
            const pagePosts = filtered.slice(start, end);
            
            renderPosts(pagePosts);
            renderPagination(state.page, totalPages);
        }}

        function renderCategories() {{
            const container = document.getElementById('categoryContainer');
            container.innerHTML = CATEGORIES.map(cat => {{
                const isActive = cat.slug === state.category;
                const baseClass = "px-4 py-2 rounded-full text-sm font-medium transition-colors border cursor-pointer whitespace-nowrap";
                const activeClass = isActive ? "bg-slate-900 text-white border-slate-900" : "bg-white text-slate-600 border-slate-200 hover:border-slate-300 hover:text-slate-900";
                return `<button onclick="setCategory('${{cat.slug}}')" class="${{baseClass}} ${{activeClass}}">
                    ${{cat.name}}
                </button>`;
            }}).join('');
        }}

        function renderPosts(posts) {{
            const container = document.getElementById('postsContainer');
            if (posts.length === 0) {{
                container.innerHTML = `<div class="text-center py-20 text-slate-500">
                    <p class="text-4xl mb-4">🔍</p>
                    <p>没有找到相关文章</p>
                </div>`;
                return;
            }}
            
            container.innerHTML = posts.map(post => {{
                const style = post.style;
                return `
                <article class="group bg-white rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-all overflow-hidden">
                    <div class="flex flex-col sm:flex-row h-full">
                        <div class="sm:w-64 h-48 sm:h-auto bg-gradient-to-br ${{style.bg_gradient}} flex items-center justify-center relative shrink-0 overflow-hidden">
                             <div class="absolute inset-0 opacity-10 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')]"></div>
                             <div class="text-6xl transform group-hover:scale-110 transition-transform duration-300 drop-shadow-sm">${{style.icon}}</div>
                        </div>
                        <div class="p-8 flex flex-col justify-center flex-1">
                             <div class="flex items-center gap-3 text-sm text-slate-500 mb-3">
                                  <span class="px-2.5 py-0.5 rounded-full ${{style.badge_color}} text-xs font-bold border">${{post.category_name}}</span>
                                  <span>${{post.date}}</span>
                             </div>
                             <h2 class="text-2xl font-bold text-slate-900 mb-3 group-hover:text-claude-600 transition-colors">
                                  <a href="${{post.url}}" class="hover:underline">${{post.title}}</a>
                             </h2>
                             <p class="text-slate-600 leading-relaxed mb-6 line-clamp-3">
                                  ${{post.description}}
                             </p>
                             <a href="${{post.url}}" class="inline-flex items-center text-sm font-semibold text-claude-600 hover:text-claude-700">
                                  阅读全文 <svg class="w-4 h-4 ml-1 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3"></path></svg>
                             </a>
                        </div>
                    </div>
                </article>`;
            }}).join('');
        }}

        function renderPagination(current, total) {{
            const container = document.getElementById('paginationContainer');
            if (total <= 1) {{
                container.innerHTML = '';
                return;
            }}
            
            let html = '';
            // Prev
            if (current > 1) {{
                html += `<button onclick="setPage(${{current - 1}})" class="px-4 py-2 text-sm font-medium text-slate-600 bg-white rounded-lg border border-slate-200 hover:bg-slate-50">上一页</button>`;
            }} else {{
                html += `<span class="px-4 py-2 text-sm font-medium text-slate-400 bg-slate-50 rounded-lg border border-slate-200 cursor-not-allowed">上一页</span>`;
            }}
            
            // Pages
            for(let i=1; i<=total; i++) {{
                if(i === current) {{
                    html += `<span class="px-4 py-2 text-sm font-medium text-white bg-claude-600 rounded-lg shadow-sm shadow-claude-600/30">${{i}}</span>`;
                }} else {{
                    html += `<button onclick="setPage(${{i}})" class="px-4 py-2 text-sm font-medium text-slate-600 bg-white rounded-lg border border-slate-200 hover:bg-slate-50">${{i}}</button>`;
                }}
            }}
            
            // Next
            if (current < total) {{
                html += `<button onclick="setPage(${{current + 1}})" class="px-4 py-2 text-sm font-medium text-slate-600 bg-white rounded-lg border border-slate-200 hover:bg-slate-50">下一页</button>`;
            }} else {{
                html += `<span class="px-4 py-2 text-sm font-medium text-slate-400 bg-slate-50 rounded-lg border border-slate-200 cursor-not-allowed">下一页</span>`;
            }}
            
            container.innerHTML = html;
        }}
        """
        
        script_tag = soup.new_tag('script')
        script_tag.string = script_content
        soup.body.append(script_tag)

        with open(blog_index_path, 'w', encoding='utf-8') as f:
            f.write(str(soup.prettify()))

    def update_sidebar(self, soup):
        aside = soup.find('aside')
        if not aside: return
        container = aside.find('div', class_='sticky')
        if not container: return
        for div in container.find_all('div', recursive=False):
            h3 = div.find('h3')
            if h3:
                text = h3.get_text()
                if '分类浏览' in text or 'Categories' in text:
                    div.decompose()
                    continue

    def generate_sitemap(self):
        sitemap_path = os.path.join(ROOT_DIR, 'sitemap.xml')
        urls = []
        urls.append({'loc': DOMAIN + '/', 'lastmod': datetime.now().strftime('%Y-%m-%d'), 'changefreq': 'daily', 'priority': '1.0'})
        urls.append({'loc': DOMAIN + '/blog/', 'lastmod': datetime.now().strftime('%Y-%m-%d'), 'changefreq': 'daily', 'priority': '0.9'})
        if os.path.exists(os.path.join(ROOT_DIR, 'legal.html')):
             urls.append({'loc': DOMAIN + '/legal', 'lastmod': datetime.now().strftime('%Y-%m-%d'), 'changefreq': 'monthly', 'priority': '0.3'})
        for post in self.posts_metadata:
            urls.append({'loc': DOMAIN + post['url'], 'lastmod': post['date'], 'changefreq': 'weekly', 'priority': '0.8'})
            
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        for url in urls:
            xml += f"  <url>\n    <loc>{url['loc']}</loc>\n    <lastmod>{url['lastmod']}</lastmod>\n    <changefreq>{url['changefreq']}</changefreq>\n    <priority>{url['priority']}</priority>\n  </url>\n"
        xml += '</urlset>'
        with open(sitemap_path, 'w', encoding='utf-8') as f: f.write(xml)
        print(f"  Generated sitemap with {len(urls)} URLs.")

if __name__ == "__main__":
    builder = SiteBuilder()
    builder.run()
