#!/usr/local/bin/python3
"""
analyze_swipe_quality.py

Extract behavioral quality signals from real-player swipe data.

Key insight: swipes are behavioral rejection signals — when a player swipes,
they're telling us "none of these responses were acceptable enough to continue."
We can't always know which model generated which response (model labels are not
in the data), but we CAN extract meaningful variance and quality signals.

Output: per-scenario statistics + aggregate quality metrics.
"""

import json
import os
import re
import sys
from collections import defaultdict
from typing import Dict, List, Any


def compute_text_metrics(text: str) -> Dict[str, float]:
    """Compute prose quality metrics for a single response."""
    if not text or not text.strip():
        return {
            'word_count': 0,
            'sentence_count': 0,
            'avg_word_length': 0,
            'unique_word_ratio': 0,
            'repetition_score': 0,
            'exclamation_density': 0,
            'ellipsis_density': 0,
        }
    
    words = re.findall(r'\b[a-zA-Zа-яА-ЯёЁ]+\b', text.lower())
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    word_count = len(words)
    sentence_count = max(len(sentences), 1)
    unique_words = len(set(words))
    unique_word_ratio = unique_words / max(word_count, 1)
    
    # Repetition score: higher = more repetitive
    # Count bigram repetitions
    if len(words) < 3:
        repetition_score = 0
    else:
        bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]
        total_bigrams = len(bigrams)
        unique_bigrams = len(set(bigrams))
        repetition_score = 1 - (unique_bigrams / max(total_bigrams, 1))
    
    # Exclamation density (overuse of ! suggests emotional/prose issues)
    exclamation_count = text.count('!')
    ellipsis_count = text.count('...')
    
    return {
        'word_count': word_count,
        'sentence_count': sentence_count,
        'avg_word_length': sum(len(w) for w in words) / max(word_count, 1),
        'unique_word_ratio': unique_word_ratio,
        'repetition_score': repetition_score,
        'exclamation_density': exclamation_count / max(word_count, 1) * 100,
        'ellipsis_density': ellipsis_count / max(word_count, 1) * 100,
    }


def compute_variant_diversity(variants: List[Dict]) -> Dict[str, float]:
    """
    Compute diversity metrics across response variants.
    High diversity = model produces very different responses on regeneration.
    This can indicate instability or creative range.
    """
    if len(variants) < 2:
        return {
            'num_variants': len(variants),
            'length_variance': 0,
            'content_diversity': 0,
        }
    
    texts = [v.get('text_clean', '') or '' for v in variants]
    lengths = [len(t.split()) for t in texts if t]
    
    if not lengths:
        return {'num_variants': len(variants), 'length_variance': 0, 'content_diversity': 0}
    
    # Length variance (normalized by mean)
    mean_len = sum(lengths) / len(lengths)
    variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
    length_variance = variance / max(mean_len, 1)
    
    # Content diversity: Jaccard similarity of word sets
    word_sets = [set(re.findall(r'\b[a-zA-Zа-яА-ЯёЁ]+\b', t.lower())) for t in texts if t]
    if len(word_sets) < 2:
        content_diversity = 0
    else:
        intersection = set.intersection(*word_sets) if word_sets else set()
        union = set.union(*word_sets) if word_sets else set()
        content_diversity = 1 - (len(intersection) / max(len(union), 1))
    
    return {
        'num_variants': len(variants),
        'length_variance': length_variance,
        'content_diversity': content_diversity,
    }


def analyze_swipe_file(filepath: str) -> Dict[str, Any]:
    """Analyze a single swipe file and return metrics."""
    with open(filepath) as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        return {}
    
    source = os.path.basename(filepath).replace('_swipes.json', '').replace('_', ' ')
    
    total_swipes = 0
    total_variants = 0
    all_metrics = []
    diversity_metrics = []
    
    for item in data:
        num_swipes = item.get('num_swipes', 0)
        variants = item.get('variants', [])
        
        total_swipes += num_swipes
        total_variants += len(variants)
        
        # Compute metrics per variant
        for v in variants:
            text = v.get('text_clean', '') or ''
            metrics = compute_text_metrics(text)
            metrics['num_swipes'] = num_swipes
            all_metrics.append(metrics)
        
        # Diversity across variants for this prompt
        div = compute_variant_diversity(variants)
        div['num_swipes'] = num_swipes
        diversity_metrics.append(div)
    
    return {
        'source': source,
        'file': os.path.basename(filepath),
        'num_prompts': len(data),
        'total_swipes': total_swipes,
        'total_variants': total_variants,
        'avg_swipes_per_prompt': total_swipes / max(len(data), 1),
        'avg_variants_per_prompt': total_variants / max(len(data), 1),
        'metrics': all_metrics,
        'diversity': diversity_metrics,
    }


def aggregate_metrics(results: List[Dict]) -> Dict[str, Any]:
    """Aggregate metrics across all scenarios."""
    if not results:
        return {}
    
    # Flatten all per-variant metrics
    all_variant_metrics = []
    all_diversity_metrics = []
    
    for r in results:
        all_variant_metrics.extend(r.get('metrics', []))
        all_diversity_metrics.extend(r.get('diversity', []))
    
    # Compute per-metric averages
    metric_keys = ['word_count', 'sentence_count', 'avg_word_length', 
                   'unique_word_ratio', 'repetition_score', 
                   'exclamation_density', 'ellipsis_density']
    
    aggregated = {}
    for key in metric_keys:
        values = [m[key] for m in all_variant_metrics if key in m]
        if values:
            aggregated[f'avg_{key}'] = sum(values) / len(values)
            aggregated[f'std_{key}'] = (
                (sum((v - aggregated[f'avg_{key}']) ** 2 for v in values) / len(values)) ** 0.5
            )
    
    # Aggregate diversity
    div_keys = ['length_variance', 'content_diversity']
    for key in div_keys:
        values = [d[key] for d in all_diversity_metrics if key in d]
        if values:
            aggregated[f'avg_{key}'] = sum(values) / len(values)
    
    return aggregated


def main():
    scenarios_dir = 'scenarios'
    swipe_files = sorted([
        os.path.join(scenarios_dir, f) 
        for f in os.listdir(scenarios_dir) 
        if 'swipe' in f and f.endswith('.json') and f != 'swipe_comparisons.json'
    ])
    
    print(f"Found {len(swipe_files)} swipe files\n")
    
    results = []
    for fp in swipe_files:
        try:
            result = analyze_swipe_file(fp)
            results.append(result)
        except Exception as e:
            print(f"Error processing {fp}: {e}")
    
    # Sort by total swipes (most informative first)
    results.sort(key=lambda r: r.get('total_swipes', 0), reverse=True)
    
    # Print per-scenario summary
    print("=" * 80)
    print("PER-SCENARIO SWIPE STATISTICS")
    print("=" * 80)
    print()
    
    for r in results:
        print(f"  {r['source']}")
        print(f"    Prompts: {r['num_prompts']}, Swipes: {r['total_swipes']}, "
              f"Variants: {r['total_variants']}")
        print(f"    Avg swipes/prompt: {r['avg_swipes_per_prompt']:.2f}, "
              f"Avg variants/prompt: {r['avg_variants_per_prompt']:.2f}")
        
        # Per-metric summary for this scenario
        metrics = r.get('metrics', [])
        if metrics:
            wc = [m['word_count'] for m in metrics if m.get('word_count', 0) > 0]
            rep = [m['repetition_score'] for m in metrics if m.get('repetition_score', 0) > 0]
            uwr = [m['unique_word_ratio'] for m in metrics if m.get('unique_word_ratio', 0) > 0]
            
            if wc:
                print(f"    Words/response: {sum(wc)/len(wc):.0f} ± {((sum((x - sum(wc)/len(wc))**2 for x in wc)/len(wc))**0.5):.0f}")
            if rep:
                print(f"    Repetition score: {sum(rep)/len(rep):.3f}")
            if uwr:
                print(f"    Unique word ratio: {sum(uwr)/len(uwr):.3f}")
        print()
    
    # Aggregate across all scenarios
    agg = aggregate_metrics(results)
    
    print("=" * 80)
    print("AGGREGATE SWIPE QUALITY METRICS (across all scenarios)")
    print("=" * 80)
    print()
    
    print("  PROSE QUALITY (per-response averages):")
    print(f"    Word count:        {agg.get('avg_word_count', 0):.1f} ± {agg.get('std_word_count', 0):.1f}")
    print(f"    Sentence count:    {agg.get('avg_sentence_count', 0):.1f} ± {agg.get('std_sentence_count', 0):.1f}")
    print(f"    Avg word length:   {agg.get('avg_avg_word_length', 0):.2f}")
    print(f"    Unique word ratio: {agg.get('avg_unique_word_ratio', 0):.3f}  (higher = more diverse vocabulary)")
    print(f"    Repetition score:  {agg.get('avg_repetition_score', 0):.3f}  (lower = less repetitive)")
    print(f"    Exclamation density: {agg.get('avg_exclamation_density', 0):.2f}/100 words")
    print(f"    Ellipsis density:    {agg.get('avg_ellipsis_density', 0):.2f}/100 words")
    print()
    
    print("  RESPONSE DIVERSITY (across variants per prompt):")
    print(f"    Length variance:   {agg.get('avg_length_variance', 0):.3f}  (higher = more unstable lengths)")
    print(f"    Content diversity:  {agg.get('avg_content_diversity', 0):.3f}  (higher = more varied content)")
    print()
    
    # Save results
    output = {
        'per_scenario': [
            {k: v for k, v in r.items() if k not in ['metrics', 'diversity']}
            for r in results
        ],
        'aggregate': agg,
        'summary': {
            'total_scenario_files': len(results),
            'total_prompts': sum(r['num_prompts'] for r in results),
            'total_swipes': sum(r['total_swipes'] for r in results),
            'total_variants': sum(r['total_variants'] for r in results),
        }
    }
    
    os.makedirs('results', exist_ok=True)
    output_path = 'results/swipe_quality_analysis.json'
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults saved to {output_path}")
    
    return output


if __name__ == '__main__':
    main()
