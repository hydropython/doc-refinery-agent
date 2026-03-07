"""
GPT-4 Mini Summary Generator for PageIndex
Location: src/agents/summary_generator.py
"""

import os
import json
import hashlib
from typing import List, Dict
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


class SummaryGenerator:
    """Generate GPT-4 Mini summaries for PageIndex sections"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.cache_dir = Path(".refinery/summary_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.api_key or not self.api_key.startswith("sk-"):
            print("    OPENAI_API_KEY not valid")
            self.client = None
        else:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
                print(f"   GPT-4 Mini initialized ({self.model})")
            except Exception as e:
                print(f"    OpenAI init error: {e}")
                self.client = None
    
    def _get_cache_key(self, title: str, content: str) -> str:
        """Generate cache key"""
        text = f"{title}:{content[:500]}"
        return hashlib.sha256(text.encode()).hexdigest()[:16]
    
    def _get_cached_summary(self, cache_key: str) -> str:
        """Get from cache"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            with open(cache_file) as f:
                data = json.load(f)
                return data.get("summary")
        return None
    
    def _cache_summary(self, cache_key: str, summary: str):
        """Save to cache"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        with open(cache_file, "w") as f:
            json.dump({
                "summary": summary,
                "timestamp": datetime.now().isoformat(),
                "model": self.model
            }, f, indent=2)
    
    def generate_summary(self, section_title: str, content_preview: str) -> str:
        """Generate 2-3 sentence summary"""
        
        # Check cache first
        cache_key = self._get_cache_key(section_title, content_preview)
        cached = self._get_cached_summary(cache_key)
        if cached:
            print(f"     Cache hit: {section_title}")
            return cached
        
        # No client = return placeholder
        if not self.client:
            return f"[Summary: {section_title}]"
        
        # Build prompt (2-3 sentences, max 50 words)
        prompt = f"""Summarize this document section in exactly 2-3 sentences (max 50 words):

Section: {section_title}

Content: {content_preview[:800]}

Summary:"""

        # Generate summary
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=80
            )
            summary = response.choices[0].message.content.strip()
            
            # Cache it
            self._cache_summary(cache_key, summary)
            
            return summary
            
        except Exception as e:
            return f"[Summary error: {str(e)[:50]}]"
    
    def generate_batch(self, sections: List[Dict]) -> List[Dict]:
        """Generate summaries for multiple sections"""
        print(f"\n  Generating {len(sections)} section summaries...")
        
        for i, section in enumerate(sections, 1):
            print(f"    [{i}/{len(sections)}] {section['title']}...", end=" ", flush=True)
            section["summary"] = self.generate_summary(
                section["title"],
                section["content"]
            )
            print("")
        
        return sections
