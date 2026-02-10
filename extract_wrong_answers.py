import json
import os
import shutil
import argparse
from pathlib import Path

def extract_wrong_answers(
    task,
    game,
    results_json_path,
    annotation_json_path,
    benchmark_images_dir,
    output_dir
):
    """
    Extract all incorrectly answered samples and create a mini-benchmark.
    
    Output has the same structure as original benchmark for re-evaluation.
    """
    
    # Load results and annotations
    with open(results_json_path, 'r') as f:
        results = json.load(f)
    
    with open(annotation_json_path, 'r') as f:
        annotations = json.load(f)
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    wrong_annotations = []
    task_results = results[task][game]
    
    # Find all wrong answers
    new_index = 0
    for i, result in enumerate(task_results):
        # Skip null results
        if result is None or result.get('raw') is None:
            continue
        
        # Get ground truth
        gt = annotations['annotations'][i]['gt']
        correct_index = gt.get('correct_index', 0)
        
        # Parse model output
        model_output = result['raw']
        predicted_index = parse_answer(model_output)
        
        # Check if wrong
        if predicted_index != correct_index:
            # Copy original annotation
            original_annotation = annotations['annotations'][i].copy()
            
            # Handle different task types for image copying
            if task == 'inverse_dynamics':
                # Copy both images with new sequential numbering
                for suffix in ['before', 'after']:
                    img_src = os.path.join(benchmark_images_dir, f'{i:07d}_{suffix}.jpg')
                    img_dst = os.path.join(output_dir, f'{new_index:07d}_{suffix}.jpg')
                    if os.path.exists(img_src):
                        shutil.copy(img_src, img_dst)
                
                # Update file references in annotation
                original_annotation['file_before'] = f'{new_index:07d}_before.jpg'
                original_annotation['file_after'] = f'{new_index:07d}_after.jpg'
                        
            elif task == 'reward_modeling':
                # Copy single image
                img_src = os.path.join(benchmark_images_dir, f'{i:07d}.jpg')
                img_dst = os.path.join(output_dir, f'{new_index:07d}.jpg')
                if os.path.exists(img_src):
                    shutil.copy(img_src, img_dst)
                
                # Update file reference
                original_annotation['file'] = f'{new_index:07d}.jpg'
                    
            elif task == 'forward_dynamics':
                # Copy before image and all choice images
                img_src = os.path.join(benchmark_images_dir, f'{i:07d}_before.jpg')
                img_dst = os.path.join(output_dir, f'{new_index:07d}_before.jpg')
                if os.path.exists(img_src):
                    shutil.copy(img_src, img_dst)
                
                for choice_idx in range(4):
                    img_src = os.path.join(benchmark_images_dir, f'{i:07d}_choice_{choice_idx}.jpg')
                    img_dst = os.path.join(output_dir, f'{new_index:07d}_choice_{choice_idx}.jpg')
                    if os.path.exists(img_src):
                        shutil.copy(img_src, img_dst)
                
                # Update file reference
                original_annotation['file_before'] = f'{new_index:07d}_before.jpg'
            
            wrong_annotations.append(original_annotation)
            new_index += 1
    
    # Calculate statistics
    valid_samples = [r for r in task_results if r is not None and r.get('raw') is not None]
    total_valid = len(valid_samples)
    wrong_count = len(wrong_annotations)
    accuracy = 1 - (wrong_count / total_valid) if total_valid > 0 else 0
    
    # Create annotation.json with same structure as original
    output_annotation = {
        'task': task,
        'game': game,
        'annotations': wrong_annotations
    }
    
    annotation_path = os.path.join(output_dir, 'annotation.json')
    with open(annotation_path, 'w') as f:
        json.dump(output_annotation, f, indent=2)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"Task: {task} | Game: {game}")
    print(f"{'='*60}")
    print(f"Total samples: {len(task_results)}")
    print(f"Valid samples: {total_valid}")
    print(f"Wrong answers extracted: {wrong_count}")
    print(f"Original accuracy: {accuracy*100:.1f}%")
    print(f"\n✓ Created mini-benchmark at: {output_dir}")
    print(f"  - annotation.json ({wrong_count} samples)")
    if task == 'inverse_dynamics':
        print(f"  - {wrong_count * 2} images (before + after)")
    elif task == 'forward_dynamics':
        print(f"  - {wrong_count * 5} images (before + 4 choices)")
    else:
        print(f"  - {wrong_count} images")
    

    return wrong_annotations

def parse_answer(model_output):
    """Extract answer number from model output."""
    import re
    
    if not model_output:
        return None
    
    patterns = [
        r'Answer:\s*([0-3])',
        r'choice\s*([0-3])',
        r'\b([0-3])\b'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, str(model_output), re.IGNORECASE)
        if match:
            return int(match.group(1))
    
    return None

def main():
    parser = argparse.ArgumentParser(description='Extract wrong answers as mini-benchmark')
    parser.add_argument('--task', type=str, required=True, 
                       choices=['inverse_dynamics', 'reward_modeling', 'forward_dynamics'],
                       help='Task name')
    parser.add_argument('--game', type=str, default='tictactoe',
                       help='Game name')
    parser.add_argument('--results', type=str, required=True,
                       help='Path to results JSON file')
    
    args = parser.parse_args()
    
    # Auto-construct paths
    annotation_path = f'benchmark/{args.task}/{args.game}/annotation.json'
    benchmark_images_dir = f'benchmark/{args.task}/{args.game}/'
    output_dir = f'analysis/{args.task}/{args.game}'
    
    extract_wrong_answers(
        task=args.task,
        game=args.game,
        results_json_path=args.results,
        annotation_json_path=annotation_path,
        benchmark_images_dir=benchmark_images_dir,
        output_dir=output_dir
    )

if __name__ == '__main__':
    main()

