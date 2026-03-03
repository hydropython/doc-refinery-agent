#!/usr/bin/env python3
"""
Document Density & Geometry Profiler (pdfplumber)
Analyzes PDF structure to determine extraction strategy
"""

import pdfplumber
import pandas as pd
from pathlib import Path
from datetime import datetime
from tabulate import tabulate


def analyze_document_physics(folder_path: str) -> dict:
    """
    Analyze PDF density and geometry
    
    Args:
        folder_path: Path to PDF file or folder
        
    Returns:
        Dict with metrics (text_chars, images_found, recommended_strategy, etc.)
    """
    pdf_path = Path(folder_path)
    
    if pdf_path.is_dir():
        pdf_files = list(pdf_path.glob("*.pdf"))
    else:
        pdf_files = [pdf_path]
    
    all_metrics = []
    
    for pdf_file in pdf_files:
        metrics = analyze_single_pdf(pdf_file)
        all_metrics.append(metrics)
    
    # Save to CSV
    save_metrics_to_csv(all_metrics)
    
    # Print summary table
    print("\n📊 DOCUMENT DENSITY & GEOMETRY PROFILING")
    print(tabulate(all_metrics, headers="keys", tablefmt="grid"))
    
    return all_metrics[0] if len(all_metrics) == 1 else all_metrics


def analyze_single_pdf(pdf_path: Path) -> dict:
    """Analyze a single PDF file"""
    
    metrics = {
        'filename': pdf_path.name,
        'text_chars': 0,
        'vector_chars': 0,
        'images_found': 0,
        'recommended_strategy': 'Strategy B (Layout-Aware)'
    }
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_chars = 0
            total_vector_chars = 0
            total_images = 0
            
            for page in pdf.pages:
                chars = page.chars
                total_chars += len(chars)
                
                vector_chars = len(page.vector_chars) if hasattr(page, 'vector_chars') else len(chars)
                total_vector_chars += vector_chars
                
                total_images += len(page.images)
            
            metrics['text_chars'] = total_chars
            metrics['vector_chars'] = total_vector_chars
            metrics['images_found'] = total_images
            metrics['recommended_strategy'] = determine_strategy(metrics)
            
    except Exception as e:
        metrics['error'] = str(e)
        metrics['recommended_strategy'] = 'Strategy C (VLM/OCR) - Error Fallback'
    
    return metrics


def determine_strategy(metrics: dict) -> str:
    """Determine extraction strategy based on empirical thresholds"""
    
    text_chars = metrics.get('text_chars', 0)
    images = metrics.get('images_found', 0)
    
    # Phase 0 empirically-derived thresholds
    if text_chars < 50 and images >= 1:
        return "Strategy C (VLM/OCR)"
    elif text_chars > 1000 and images == 0:
        return "Strategy A (Fast Text)"
    else:
        return "Strategy B (Layout-Aware)"


def save_metrics_to_csv(metrics_list: list):
    """Save metrics to .refinery/phase0_pdfplumber_metrics.csv"""
    
    output_dir = Path('./.refinery')
    output_dir.mkdir(exist_ok=True)
    
    csv_path = output_dir / 'phase0_pdfplumber_metrics.csv'
    
    # Add timestamp
    for m in metrics_list:
        m['analyzed_at'] = datetime.now().isoformat()
    
    # Append or write
    if csv_path.exists():
        existing_df = pd.read_csv(csv_path)
        existing_files = set(existing_df['filename'].tolist())
        new_metrics = [m for m in metrics_list if m['filename'] not in existing_files]
        
        if new_metrics:
            new_df = pd.DataFrame(new_metrics)
            pd.concat([existing_df, new_df], ignore_index=True).to_csv(csv_path, index=False)
            print(f"✅ Appended {len(new_metrics)} records to: {csv_path}")
    else:
        df = pd.DataFrame(metrics_list)
        df.to_csv(csv_path, index=False)
        print(f"✅ Created: {csv_path}")