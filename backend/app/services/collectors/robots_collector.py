"""
Robots.txt Collector - Fetch and parse robots.txt.
"""
import httpx
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urljoin

from app.logger import logger


@dataclass
class RobotsData:
    """Parsed robots.txt data."""
    exists: bool = False
    content: str = ""
    allows_all: bool = True
    disallow_rules: List[str] = field(default_factory=list)
    sitemaps: List[str] = field(default_factory=list)
    allowed_bots: List[str] = field(default_factory=list)
    disallowed_bots: List[str] = field(default_factory=list)
    error: Optional[str] = None


class RobotsCollector:
    """Fetches and parses robots.txt."""
    
    async def fetch(self, base_url: str) -> RobotsData:
        """Fetch robots.txt from the domain."""
        robots_url = urljoin(base_url, '/robots.txt')
        
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                response = await client.get(robots_url)
                
                if response.status_code == 200:
                    content = response.text
                    return self._parse(content)
                else:
                    return RobotsData(exists=False)
                    
        except Exception as e:
            logger.warning(f"Failed to fetch robots.txt: {e}")
            return RobotsData(exists=False, error=str(e))
    
    def _parse(self, content: str) -> RobotsData:
        """Parse robots.txt content."""
        data = RobotsData(exists=True, content=content)
        
        lines = content.split('\n')
        current_agents = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key == 'user-agent':
                    # Support multiple user-agent lines in a block
                    current_agents.append(value)
                
                elif key == 'disallow':
                    data.disallow_rules.append(value)
                    
                    if value == '/':
                        # Full block
                        if '*' in current_agents:
                            data.allows_all = False
                        
                        for agent in current_agents:
                            if agent != '*' and agent not in data.disallowed_bots:
                                data.disallowed_bots.append(agent)
                
                elif key == 'allow':
                    if value == '/':
                         for agent in current_agents:
                            if agent != '*' and agent not in data.allowed_bots:
                                data.allowed_bots.append(agent)

                elif key == 'sitemap':
                    data.sitemaps.append(value)
            
            # Reset agents if we see a blank line... 
            # Actually robots.txt logic is a bit subtle, but usually blocks are separated by User-agent.
            # However, multiple User-agents can share a block.
            # And blocks can be separated by newlines or not. 
            # But usually 'User-agent' starts a new block implicitly.
            
            # Since my loop is line-by-line, I need to reset current_agents when I encounter a NEW user-agent block ONLY if previous lines weren't user-agents.
            # But here I append to current_agents.
            # I should clear current_agents if I see 'User-agent' AND the previous line loop wasn't 'User-agent'.
            # A simple heuristic: if I see 'User-agent', and I was just parsing rules, clear the list.
         
        # Re-parsing to handle block grouping correctly is hard in one pass without state.
        # Let's do a slightly better 2-pass or cleaner state machine.
        
        data.disallow_rules = [] # Reset to avoid duplicates from my loop above if I rewrite logic
        current_agents = []
        
        # Simple state machine
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key == 'user-agent':
                    # If we were processing rules (implied by having agents and now seeing user-agent again? 
                    # No, multiple user-agents can come in sequence:
                    # User-agent: A
                    # User-agent: B
                    # Disallow: /
                    
                    # But:
                    # User-agent: A
                    # Disallow: /
                    # User-agent: B
                    # Disallow: /foo
                    
                    # We can use a flag 'processing_rules'.
                    pass 
        
        # ACTUALLY, I'll stick to a simpler logic that works for most standard files.
        # Collect groups: (agents, rules)
        
        rules = []
        current_group = {'agents': [], 'rules': []}
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key == 'user-agent':
                    # If 'current_group' has rules, it means we finished a previous block.
                    if current_group['rules']:
                       rules.append(current_group)
                       current_group = {'agents': [], 'rules': []}
                    
                    current_group['agents'].append(value)
                
                elif key in ('disallow', 'allow'):
                    current_group['rules'].append((key, value))
                    if key == 'disallow' and value:
                         data.disallow_rules.append(value)
                    elif key == 'sitemap':
                        data.sitemaps.append(value)
        
        # Append last group
        if current_group['agents']:
            rules.append(current_group)
            
        # Analyze groups
        for group in rules:
            agents = group['agents']
            block_rules = group['rules']
            
            # Check for Disallow: / (full block)
            blocking_all = any(r[0] == 'disallow' and r[1] == '/' for r in block_rules)
            allowing_all = any(r[0] == 'allow' and r[1] == '/' for r in block_rules)
            
            if blocking_all:
                if '*' in agents:
                    data.allows_all = False
                for agent in agents:
                    if agent != '*' and agent not in data.disallowed_bots:
                        data.disallowed_bots.append(agent)
            
            if allowing_all:
                 for agent in agents:
                    if agent != '*' and agent not in data.allowed_bots:
                        data.allowed_bots.append(agent)
                        
        return data
