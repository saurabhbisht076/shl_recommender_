import asyncio
import json
import logging
import re
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from tqdm.asyncio import tqdm_asyncio

# Setup logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# File paths
DATA_DIR = Path("data")
RAW_DATA_PATH = DATA_DIR / "raw" / "shl_catalog_raw.json"
DETAILED_DATA_PATH = DATA_DIR / "processed" / "shl_assessments_detailed.json"

# Ensure directories exist
RAW_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
DETAILED_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)

# ---------- Helper Functions ----------

def clean_text(text):
    """Clean and normalize text"""
    if not text:
        return None
    return re.sub(r'\s+', ' ', text).strip()

def clean_job_levels(raw_list):
    """
    Clean and filter job level strings
    """
    if not raw_list:
        return []
    
    valid_keywords = [
        'manager', 'graduate', 'professional', 'sales', 'technolog', 
        'contact center', 'retail', 'manufacturing', 'bpo', 'early',
        'entry', 'executive', 'senior', 'junior', 'supervisor', 'lead'
    ]
    
    cleaned = []
    for text in raw_list:
        text = clean_text(text)
        if text and any(kw in text.lower() for kw in valid_keywords) and len(text.split()) < 10:
            cleaned.append(text)
    
    return list(set(cleaned))

def extract_languages(raw_list):
    """
    Extract valid languages from text or list
    """
    if not raw_list:
        return []
    
    # Common language names and variations
    language_pattern = r'\b(english|spanish|french|german|chinese|japanese|korean|russian|portuguese|italian|dutch|arabic|hindi|turkish|swedish|norwegian|danish|finnish|polish|czech|hungarian|romanian|bulgarian|greek|hebrew|thai|vietnamese|indonesian|malay|tagalog|simplified chinese|traditional chinese|中文|简体中文|繁體中文)(?:\s*\([^)]*\))?\b'
    
    languages = []
    for item in raw_list:
        if not item:
            continue
        matches = re.findall(language_pattern, item.lower())
        languages.extend(matches)
    
    return list(set(languages))

def determine_test_type(name, description):
    """
    Determine assessment type based on name and description
    """
    name = (name or "").lower()
    description = (description or "").lower()
    combined_text = f"{name} {description}"
    
    if any(kw in combined_text for kw in ['cognitive', 'reasoning', 'verbal', 'numerical', 'abstract', 'inductive', 'deductive', 'critical thinking']):
        return "Cognitive Assessment"
    elif any(kw in combined_text for kw in ['personality', 'behavioral', 'behaviour', 'behavior', 'occupational', 'preference', 'type', 'trait']):
        return "Personality Assessment"
    elif any(kw in combined_text for kw in ['skill', 'ability', 'competency', 'proficiency', 'coding', 'programming', 'language', 'technical']):
        return "Skill Assessment"
    else:
        return "General Assessment"

def extract_duration(text):
    """
    Extract duration information from text
    """
    if not text:
        return None
    
    # Add pattern specific to "Approximate Completion Time in minutes = X" format
    approximate_pattern = r'approximate completion time in minutes\s*=\s*(\d+)'
    match = re.search(approximate_pattern, text.lower())
    if match:
        minutes = match.group(1)
        return f"{minutes} minutes"
    
    duration_patterns = [
        r'(\d+)\s*(?:to|-)\s*(\d+)\s*(minutes|mins|min|hours|hrs|hour)',  # Range: 15-20 minutes
        r'(\d+)\s*(minutes|mins|min|hours|hrs|hour)',  # Single: 15 minutes
        r'(less than|approximately|approx\.?|about|around)\s+(\d+)\s*(minutes|mins|min|hours|hrs|hour)',  # Approximate: about 15 minutes
        r'(time to completion|completion time|assessment.*?takes|takes.*?complete).*?(\d+)[-\s](\d+)\s*(minutes|mins|min|hours|hrs|hour)',  # Context-aware: time to completion is 15-20 minutes
        r'(time to completion|completion time|assessment.*?takes|takes.*?complete).*?(\d+)\s*(minutes|mins|min|hours|hrs|hour)',  # Context-aware single: time to completion is 15 minutes
        r'(duration|time required|completion time|test time)[:;]\s*(\d+[-–]?\d*)\s*(minutes|mins|min|hours|hrs|hour)',  # Duration formats
        r'(duration|time required|completion time|test time).*?(\d+[-–]?\d*)\s*(minutes|mins|min|hours|hrs|hour)'  # More flexible duration patterns
    ]
    
    for pattern in duration_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)
    
    # Look for "Approximate Completion Time" headers and adjacent content
    completion_time_pattern = re.search(r'approximate completion time.*?(\d+)', text, re.IGNORECASE | re.DOTALL)
    if completion_time_pattern:
        minutes = completion_time_pattern.group(1)
        return f"{minutes} minutes"
    
    # Try to extract duration via paragraph or section analysis
    # Look for sections that might discuss time or duration
    time_sections = re.findall(r'(?:duration|time required|time to complete|time to take|completion time).*?(\d+[^\.]*)(?:\.|$)', 
                              text, re.IGNORECASE | re.DOTALL)
    
    for section in time_sections:
        if re.search(r'\d+\s*(minutes|mins|min|hours|hrs|hour)', section, re.IGNORECASE):
            return clean_text(section)
    
    return None

# ---------- Scraper Classes ----------

class SHLCatalogScraper:
    def __init__(self, base_url="https://www.shl.com/solutions/products/product-catalog/"):
        self.base_url = base_url
        self.page = None
    
    async def init_page(self, browser):
        context = await browser.new_context()
        self.page = await context.new_page()
        await self.page.set_viewport_size({"width": 1280, "height": 800})
    
    async def get_assessment_links(self):
        try:
            await self.page.goto(self.base_url, timeout=60000)
            
            # Wait for any content to load
            await self.page.wait_for_selector("body", timeout=10000)
            logger.info("Page loaded, extracting links")
            
            # Scroll through the page to load any lazy-loaded content
            for _ in range(10):
                await self.page.evaluate("window.scrollBy(0, 500)")
                await asyncio.sleep(0.5)
            
            # Debug: Take a screenshot
            await self.page.screenshot(path="debug_catalog_page.png")
            logger.info("Saved screenshot to debug_catalog_page.png")
            
            # Get the content
            content = await self.page.content()
            
            # Save raw HTML for debugging
            with open("debug_catalog_page.html", "w", encoding="utf-8") as f:
                f.write(content)
            logger.info("Saved HTML to debug_catalog_page.html")
            
            soup = BeautifulSoup(content, "html.parser")
            
            # Generic approach to finding assessment links
            assessment_links = []
            
            # First, try to find any element that looks like it might contain product items
            product_containers = []
            
            # Try various selectors that might contain product items
            potential_selectors = [
                "div[class*='product']", "div[class*='catalog']", "div[class*='assessment']",
                "li[class*='product']", "li[class*='catalog']", "li[class*='assessment']",
                "article", ".card", ".item"
            ]
            
            for selector in potential_selectors:
                containers = soup.select(selector)
                if containers:
                    product_containers.extend(containers)
            
            logger.info(f"Found {len(product_containers)} potential product containers")
            
            # Extract links from these containers
            for container in product_containers:
                for link in container.find_all("a"):
                    href = link.get("href")
                    if href:
                        # Check if the link looks like a product link
                        if any(keyword in href.lower() for keyword in ['/product/', '/products/', '/assessment/', '/assessments/']):
                            full_url = href if href.startswith("http") else urljoin(self.base_url, href)
                            title = clean_text(link.get_text())
                            if title:  # Only add links with actual text
                                assessment_links.append({"url": full_url, "title": title})
            
            # If no links found in containers, try all links on the page
            if not assessment_links:
                logger.info("No links found in containers, trying all links")
                # Find all links that might be products
                for link in soup.find_all("a"):
                    href = link.get("href")
                    if href:
                        # Check if the link looks like a product link
                        if any(keyword in href.lower() for keyword in ['/product/', '/products/', '/assessment/', '/assessments/']):
                            full_url = href if href.startswith("http") else urljoin(self.base_url, href)
                            title = clean_text(link.get_text())
                            if title:  # Only add links with actual text
                                assessment_links.append({"url": full_url, "title": title})
            
            # Try one more approach - find all headings and see if they have accompanying links
            if not assessment_links:
                logger.info("Still no links, trying headings")
                for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                    # Look for a link within this heading or its next sibling
                    link = heading.find("a")
                    if not link:
                        next_elem = heading.find_next_sibling()
                        if next_elem:
                            link = next_elem.find("a")
                    
                    if link and link.get("href"):
                        href = link.get("href")
                        if any(keyword in href.lower() for keyword in ['/product/', '/products/', '/assessment/', '/assessments/']):
                            full_url = href if href.startswith("http") else urljoin(self.base_url, href)
                            title = clean_text(heading.get_text()) or clean_text(link.get_text())
                            if title:
                                assessment_links.append({"url": full_url, "title": title})
            
            # Remove duplicates while preserving order
            unique_links = []
            seen_urls = set()
            for item in assessment_links:
                if item["url"] not in seen_urls:
                    seen_urls.add(item["url"])
                    unique_links.append(item)
            
            logger.info(f"Found {len(unique_links)} unique assessment links")
            
            # If still no links, try to extract links directly via JS
            if not unique_links:
                logger.info("Attempting to extract links via JavaScript")
                # Use JavaScript to extract all links that look like product links
                js_links = await self.page.evaluate("""
                    () => {
                        const links = Array.from(document.querySelectorAll('a'));
                        return links
                            .filter(link => {
                                const href = link.href.toLowerCase();
                                return href.includes('/product/') || 
                                       href.includes('/products/') || 
                                       href.includes('/assessment/') || 
                                       href.includes('/assessments/');
                            })
                            .map(link => ({
                                url: link.href,
                                title: link.textContent.trim()
                            }))
                            .filter(item => item.title);  // Only include links with text
                    }
                """)
                
                # Add these to our unique links
                for item in js_links:
                    if item["url"] not in seen_urls:
                        seen_urls.add(item["url"])
                        unique_links.append(item)
                
                logger.info(f"Found {len(unique_links)} unique assessment links after JS extraction")
            
            # If STILL no links, try an alternative approach - look at the site's navigation
            if not unique_links:
                logger.info("Attempting to navigate to an alternative catalog page")
                # Try to find and click on a "Products" or "Assessments" link
                try:
                    # Look for navigation links
                    navigation_links = await self.page.query_selector_all('nav a, header a, .menu a')
                    for link in navigation_links:
                        text = await link.text_content()
                        if 'product' in text.lower() or 'assessment' in text.lower() or 'catalog' in text.lower():
                            await link.click()
                            await self.page.wait_for_load_state('networkidle')
                            
                            # Now try to extract links again
                            content = await self.page.content()
                            soup = BeautifulSoup(content, "html.parser")
                            
                            for link in soup.find_all("a"):
                                href = link.get("href")
                                if href and any(keyword in href.lower() for keyword in ['/product/', '/products/', '/assessment/', '/assessments/']):
                                    full_url = href if href.startswith("http") else urljoin(self.base_url, href)
                                    title = clean_text(link.get_text())
                                    if title and full_url not in seen_urls:
                                        seen_urls.add(full_url)
                                        unique_links.append({"url": full_url, "title": title})
                            
                            logger.info(f"Found {len(unique_links)} unique assessment links after navigation")
                            break
                except Exception as e:
                    logger.error(f"Error during navigation attempt: {e}")
            
            return unique_links
            
        except Exception as e:
            logger.error(f"Error scraping catalog page: {e}")
            return []

class SHLDetailScraper:
    def __init__(self):
        self.page = None
    
    async def init_page(self, browser):
        context = await browser.new_context()
        self.page = await context.new_page()
        await self.page.set_viewport_size({"width": 1280, "height": 800})
    
    async def get_details(self, url, title=None):
        try:
            logger.info(f"Scraping details for: {url}")
            await self.page.goto(url, timeout=60000)
            
            # Wait for content
            await self.page.wait_for_selector("body", timeout=10000)
            await asyncio.sleep(2)  # Wait longer for dynamic content
            
            # Scroll through the page to ensure all content is loaded
            for _ in range(5):
                await self.page.evaluate("window.scrollBy(0, 300)")
                await asyncio.sleep(0.5)
            
            # Take a screenshot for debugging specific pages
            debug_filename = f"debug_details_{url.split('/')[-2]}.png"
            await self.page.screenshot(path=debug_filename)
            logger.info(f"Saved screenshot to {debug_filename}")
            
            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            # Extract name (try multiple selectors)
            name = None
            for selector in ["h1", "h2.product-title", ".product-detail__title", ".product-catalogue__item-header", ".page-title"]:
                name_tags = soup.select(selector)
                for tag in name_tags:
                    potential_name = clean_text(tag.get_text())
                    if potential_name and len(potential_name) > 3:
                        name = potential_name
                        break
                if name:
                    break
            
            # Use title from catalog as fallback
            if not name and title:
                name = title
            
            # Extract description (try multiple selectors)
            description = None
            for selector in [
                ".product-detail__description", 
                "div.component.rich-text p", 
                "div.single-product__intro p", 
                ".product-catalogue__training-description",
                ".product-detail p",
                ".rich-text p",
                "div[class*='description'] p",
                "section p"
            ]:
                desc_tags = soup.select(selector)
                if desc_tags:
                    combined_text = " ".join(clean_text(tag.get_text()) for tag in desc_tags[:2])
                    if combined_text and len(combined_text) > 20:  # Ensure it's a proper description
                        description = combined_text
                        break
            
            # If still no description, try a more general approach
            if not description:
                # Look for paragraphs near the title
                if name:
                    for h_tag in soup.find_all(['h1', 'h2']):
                        if name in h_tag.get_text():
                            # Look at next siblings for paragraphs
                            next_elem = h_tag.find_next_sibling()
                            while next_elem and next_elem.name not in ['h1', 'h2', 'h3']:
                                if next_elem.name == 'p':
                                    text = clean_text(next_elem.get_text())
                                    if text and len(text) > 20:
                                        description = text
                                        break
                                next_elem = next_elem.find_next_sibling()
                            if description:
                                break
            
            # Try a more aggressive approach for description
            if not description:
                # Look for any paragraphs in the main content area
                content_areas = soup.select("main, article, .content, [role='main']")
                if content_areas:
                    for area in content_areas:
                        paras = area.select("p")
                        if paras:
                            # Get the first 1-2 substantive paragraphs
                            candidates = []
                            for p in paras:
                                text = clean_text(p.get_text())
                                if text and len(text) > 30 and not any(x in text.lower() for x in ["cookie", "copyright", "privacy"]):
                                    candidates.append(text)
                            if candidates:
                                description = " ".join(candidates[:2])
                                break
            
            # Check meta description
            if not description:
                meta_desc = soup.select_one("meta[name='description']")
                if meta_desc:
                    meta_content = meta_desc.get("content")
                    if meta_content and len(meta_content) > 20:
                        description = meta_content
            
            # If still no description, try JavaScript evaluation
            if not description:
                try:
                    # Use JS to find paragraphs with reasonable length
                    js_desc = await self.page.evaluate("""
                        () => {
                            const paragraphs = Array.from(document.querySelectorAll('p'));
                            const candidates = paragraphs
                                .filter(p => {
                                    const text = p.textContent.trim();
                                    return text.length > 30 && 
                                           !text.toLowerCase().includes('cookie') && 
                                           !text.toLowerCase().includes('copyright');
                                })
                                .map(p => p.textContent.trim())
                                .slice(0, 2);
                            return candidates.join(' ');
                        }
                    """)
                    if js_desc and len(js_desc) > 30:
                        description = js_desc
                except Exception as e:
                    logger.error(f"JavaScript description extraction failed: {e}")
            
            # Extract full text for searching
            full_text = soup.get_text().lower()
            
            # UPDATED: Direct approach for the specific h4 format we're looking for
            duration = None
            
            # 1. First, directly look for h4 with "Approximate Completion Time" text
            for h4 in soup.find_all('h4'):
                if 'approximate completion time' in h4.get_text().lower():
                    # Look for the next paragraph tag which should contain the duration
                    next_p = h4.find_next('p')
                    if next_p:
                        p_text = next_p.get_text().strip()
                        # Try to extract the number from format "= X" or just the number
                        match = re.search(r'=\s*(\d+)', p_text)
                        if match:
                            duration = f"{match.group(1)} minutes"
                            break
                        else:
                            # Look for just a number that might be minutes
                            match = re.search(r'(\d+)', p_text)
                            if match:
                                duration = f"{match.group(1)} minutes"
                                break
            
            # 2. If not found through h4 approach, try direct regex on full text
            if not duration:
                match = re.search(r'approximate completion time in minutes\s*=\s*(\d+)', full_text)
                if match:
                    duration = f"{match.group(1)} minutes"
            
            # 3. Fall back to the existing extract_duration approach
            if not duration:
                duration = extract_duration(full_text)
            
            # 4. Try JavaScript to extract duration as a last resort
            if not duration:
                try:
                    js_duration = await self.page.evaluate("""
                        () => {
                            // First try to find h4 with "Approximate Completion Time"
                            const h4Elements = Array.from(document.querySelectorAll('h4'));
                            for (const h4 of h4Elements) {
                                if (h4.textContent.toLowerCase().includes('approximate completion time')) {
                                    // Find the next paragraph
                                    let nextP = h4.nextElementSibling;
                                    while (nextP && nextP.tagName !== 'P') {
                                        nextP = nextP.nextElementSibling;
                                    }
                                    
                                    if (nextP) {
                                        const pText = nextP.textContent.trim();
                                        // Try to extract "= X" format
                                        const equalsMatch = pText.match(/=\\s*(\\d+)/);
                                        if (equalsMatch) {
                                            return `${equalsMatch[1]} minutes`;
                                        }
                                        
                                        // Try to extract just the number
                                        const numMatch = pText.match(/\\d+/);
                                        if (numMatch) {
                                            return `${numMatch[0]} minutes`;
                                        }
                                    }
                                }
                            }
                            
                            // Direct search in document body
                            const bodyText = document.body.textContent.toLowerCase();
                            const approxMatch = bodyText.match(/approximate completion time in minutes\\s*=\\s*(\\d+)/);
                            if (approxMatch) {
                                return `${approxMatch[1]} minutes`;
                            }
                            
                            return null;
                        }
                    """)
                    if js_duration:
                        duration = js_duration
                except Exception as e:
                    logger.error(f"JavaScript duration extraction failed: {e}")
            
            # Extract PDF link
            pdf_link = None
            for pdf_tag in soup.find_all("a", href=lambda h: h and ".pdf" in h.lower()):
                href = pdf_tag.get("href")
                if href:
                    pdf_link = href if href.startswith("http") else urljoin(url, href)
                    break
            
            # Extract job levels
            job_levels = []
            # Method 1: Look for specific headers
            for header in soup.find_all(["h2", "h3", "h4", "strong", "b", "dt"]):
                header_text = header.get_text(strip=True).lower()
                if "job level" in header_text or "job role" in header_text or "suitable for" in header_text:
                    # Look for adjacent list or paragraphs
                    next_elem = header.find_next(["ul", "ol", "p", "div", "dd"])
                    if next_elem:
                        if next_elem.name in ["ul", "ol"]:
                            job_levels.extend([li.get_text(strip=True) for li in next_elem.find_all("li")])
                        else:
                            text = next_elem.get_text(strip=True)
                            job_levels.extend([item.strip() for item in re.split(r'[,;]', text) if item.strip()])
            
            # Method 2: Look for specific sections
            for section in soup.select("[class*='info'], [class*='details'], [class*='specs']"):
                section_text = section.get_text(strip=True).lower()
                if "job level" in section_text or "job role" in section_text or "suitable for" in section_text:
                    # Extract list items if present
                    for li in section.select("li"):
                        job_levels.append(li.get_text(strip=True))
                    # Or extract paragraph text
                    if not job_levels:
                        for p in section.select("p"):
                            p_text = p.get_text(strip=True)
                            job_levels.extend([item.strip() for item in re.split(r'[,;]', p_text) if item.strip()])
            
            # Method 3: Look for job level or role info in the page text using regex
            if not job_levels:
                job_level_sections = re.findall(r'(?:job levels?|job roles?|suitable for)[:\s]+(.*?)(?:\.|$)', full_text, re.IGNORECASE)
                for section in job_level_sections:
                    job_levels.extend([item.strip() for item in re.split(r'[,;]', section) if item.strip()])
            
            # Clean and filter job levels
            job_levels = clean_job_levels(job_levels)
            
            # Extract languages
            languages = []
            # Method 1: Look for specific headers
            for header in soup.find_all(["h2", "h3", "h4", "strong", "b", "dt"]):
                header_text = header.get_text(strip=True).lower()
                if "language" in header_text or "available in" in header_text:
                    # Look for adjacent list or paragraphs
                    next_elem = header.find_next(["ul", "ol", "p", "div", "dd"])
                    if next_elem:
                        if next_elem.name in ["ul", "ol"]:
                            languages.extend([li.get_text(strip=True) for li in next_elem.find_all("li")])
                        else:
                            text = next_elem.get_text(strip=True)
                            languages.extend([item.strip() for item in re.split(r'[,;]', text) if item.strip()])
            
            # Method 2: Look for specific sections
            for section in soup.select("[class*='info'], [class*='details'], [class*='specs']"):
                section_text = section.get_text(strip=True).lower()
                if "language" in section_text or "available in" in section_text:
                    # Extract list items if present
                    for li in section.select("li"):
                        languages.append(li.get_text(strip=True))
                    # Or extract paragraph text
                    if not languages:
                        for p in section.select("p"):
                            p_text = p.get_text(strip=True)
                            languages.extend([item.strip() for item in re.split(r'[,;]', p_text) if item.strip()])
            
            # Method 3: Look for language info in the page text using regex
            if not languages:
                language_sections = re.findall(r'(?:languages?|available in)[:\s]+(.*?)(?:\.|$)', full_text, re.IGNORECASE)
                for section in language_sections:
                    languages.extend([item.strip() for item in re.split(r'[,;]', section) if item.strip()])
            
            # Clean and extract valid languages
            languages = extract_languages(languages)
            
            # Check for remote testing support
            remote_keywords = ['remote testing', 'remote assessment', 'online assessment', 'virtual assessment']
            remote_testing_support = any(kw in full_text for kw in remote_keywords)
            
            # Check for adaptive IRT support
            adaptive_keywords = ['adaptive', 'irt', 'item response theory', 'computer adaptive']
            adaptive_irt_support = any(kw in full_text for kw in adaptive_keywords)
            
            # Determine test type
            test_type = determine_test_type(name, description)
            
            return {
                "name": name,
                "url": url,
                "description": description,
                "job_levels": job_levels or None,
                "languages": languages or None,
                "duration": duration,
                "remote_testing_support": remote_testing_support,
                "adaptive_irt_support": adaptive_irt_support,
                "pdf_link": pdf_link,
                "test_type": test_type
            }
            
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")
            return {
                "name": title,
                "url": url,
                "description": None,
                "job_levels": None,
                "languages": None,
                "duration": None,
                "remote_testing_support": None,
                "adaptive_irt_support": None,
                "pdf_link": None,
                "test_type": "General Assessment"
            }

# ---------- Alternative Link Collection Method ----------

async def collect_assessment_links_via_search(browser):
    """
    Alternative approach to find assessment links through search or site navigation
    """
    base_url = "https://www.shl.com/"
    search_terms = ["assessment", "product", "cognitive", "personality", "behavioral", "skill"]
    search_url = f"{base_url}search"
    
    context = await browser.new_context()
    page = await context.new_page()
    
    all_links = []
    seen_urls = set()
    
    for term in search_terms:
        try:
            logger.info(f"Searching for term: {term}") 
                        # Try to navigate to search page
            await page.goto(search_url, timeout=60000)
            await page.wait_for_selector("input[type='search'], [class*='search']", timeout=5000)
            
            # Try to find and use search input
            search_input = await page.query_selector("input[type='search'], [class*='search']")
            if search_input:
                await search_input.fill(term)
                await search_input.press("Enter")
                await page.wait_for_load_state("networkidle")
                
                # Extract search results
                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")
                
                # Find assessment links in search results
                for link in soup.find_all("a"):
                    href = link.get("href")
                    if href and any(keyword in href.lower() for keyword in ['/product/', '/products/', '/assessment/', '/assessments/']):
                        full_url = href if href.startswith("http") else urljoin(base_url, href)
                        title = clean_text(link.get_text())
                        if title and full_url not in seen_urls:
                            seen_urls.add(full_url)
                            all_links.append({"url": full_url, "title": title})
                
                await asyncio.sleep(1)  # Be respectful with rate limiting
                
        except Exception as e:
            logger.error(f"Error searching for term '{term}': {e}")
    
    await context.close()
    return all_links

async def scrape_catalog():
    """Scrape the catalog page to get all assessment links"""
    assessment_links = []
    
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        
        # First try the direct catalog page approach
        catalog_scraper = SHLCatalogScraper()
        await catalog_scraper.init_page(browser)
        assessment_links = await catalog_scraper.get_assessment_links()
        
        # If that didn't work, try the alternative approach
        if not assessment_links:
            logger.info("Trying alternative approach to find assessment links")
            assessment_links = await collect_assessment_links_via_search(browser)
        
        await browser.close()
    
    # Save raw links to file with metadata
    data_to_save = {
        "metadata": {
            "scrape_time": "2025-04-05 15:40:54",  # Current UTC time
            "scraper_user": "saurabhbisht076",      # Current user
        },
        "links": assessment_links
    }
    
    with open(RAW_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, indent=2)
    
    logger.info(f"Saved {len(assessment_links)} raw links to {RAW_DATA_PATH}")
    return assessment_links

async def scrape_details(assessment_links=None):
    """Scrape detailed information for each assessment"""
    if not assessment_links:
        try:
            with open(RAW_DATA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                assessment_links = data.get("links", [])
            logger.info(f"Loaded {len(assessment_links)} links from {RAW_DATA_PATH}")
        except FileNotFoundError:
            logger.error(f"Raw file not found: {RAW_DATA_PATH}")
            assessment_links = await scrape_catalog()
    
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        detail_scraper = SHLDetailScraper()
        await detail_scraper.init_page(browser)
        
        detailed_assessments = []
        for entry in tqdm_asyncio(assessment_links, desc="Scraping assessment details"):
            url = entry["url"]
            title = entry.get("title")
            
            details = await detail_scraper.get_details(url, title)
            if details:
                # Add metadata to each assessment
                details["metadata"] = {
                    "scrape_time": "2025-04-05 15:40:54",  # Current UTC time
                    "scraper_user": "saurabhbisht076"      # Current user
                }
                detailed_assessments.append(details)
                # Add small delay to be respectful to the server
                await asyncio.sleep(1)
        
        await browser.close()
    
    # Save detailed data to file
    data_to_save = {
        "metadata": {
            "scrape_time": "2025-04-05 15:40:54",  # Current UTC time
            "scraper_user": "saurabhbisht076",      # Current user
            "total_assessments": len(detailed_assessments)
        },
        "assessments": detailed_assessments
    }
    
    with open(DETAILED_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, indent=2)
    
    logger.info(f"Saved {len(detailed_assessments)} detailed assessments to {DETAILED_DATA_PATH}")
    return detailed_assessments

async def main():
    """Main function to run the entire scraping process"""
    logger.info(f"Starting SHL assessment catalog scraper at 2025-04-05 15:40:54 by user saurabhbisht076")
    
    try:
        # Step 1: Scrape the catalog page for all assessment links
        assessment_links = await scrape_catalog()
        
        # Step 2: Scrape detailed information for each assessment
        detailed_assessments = await scrape_details(assessment_links)
        
        logger.info(f"Completed scraping {len(detailed_assessments)} SHL assessments")
        
    except Exception as e:
        logger.error(f"Error in main scraping process: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())