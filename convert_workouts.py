#!/usr/bin/env python3
import os
import re
from datetime import datetime
from pathlib import Path

SOURCE_DIR = r"c:\Users\gabrsc\OneDrive - ASSA ABLOY Group\Desktop\gym-logs\Notion\workout-tracker"
OUTPUT_DIR = r"c:\Users\gabrsc\OneDrive - ASSA ABLOY Group\Desktop\gym-logs\workout-converted"

def parse_frontmatter(content):
    """Parse YAML frontmatter from markdown file."""
    match = re.match(r'^---\n(.*?)\n---\n(.*)', content, re.DOTALL)
    if not match:
        return {}, content
    
    try:
        fm_text = match.group(1)
        # Simple YAML parser
        fm = {}
        for line in fm_text.split('\n'):
            line = line.strip()
            if ':' in line and not line.startswith('-'):
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                # Handle lists
                if value.startswith('['):
                    # Skip list parsing for now
                    continue
                elif value.lower() == 'true':
                    fm[key] = True
                elif value.lower() == 'false':
                    fm[key] = False
                else:
                    fm[key] = value
        body = match.group(2)
        return fm, body
    except:
        return {}, content

def parse_time(time_str):
    """Parse ISO 8601 datetime string."""
    if not time_str:
        return None
    try:
        dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        return dt
    except:
        return None

def time_to_hhmm(dt):
    """Convert datetime to HH:mm format."""
    if not dt:
        return ""
    return dt.strftime("%H:%M")

def time_to_full(dt):
    """Convert datetime to YYYY-MM-DD HH:mm format."""
    if not dt:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M")

def calculate_duration(start_dt, end_dt):
    """Calculate duration in minutes."""
    if not start_dt or not end_dt:
        return ""
    delta = end_dt - start_dt
    return int(delta.total_seconds() // 60)

def expand_abbreviations(text):
    """Expand common exercise abbreviations."""
    text = re.sub(r'\bBb\b', 'Barbell', text, flags=re.IGNORECASE)
    text = re.sub(r'\bDb\b', 'Dumbbell', text, flags=re.IGNORECASE)
    text = re.sub(r'\bBB\b', 'Barbell', text)
    text = re.sub(r'\bDB\b', 'Dumbbell', text)
    return text

def title_case_exercise(name):
    """Title case exercise name, preserving some words."""
    words = name.split()
    result = []
    for word in words:
        if word.lower() in ['and', 'or', 'with', 'to']:
            result.append(word.lower())
        else:
            result.append(word.capitalize())
    return ' '.join(result)

def parse_sets(exercise_line):
    """Parse sets from exercise line. Returns (weight_unit, sets_list)."""
    sets_info = []
    
    # Look for patterns like "30kg 3x10" or "50kg 1x10, 65 2x10" or just "3x10"
    # Extract everything after exercise name
    
    # Try to find weight unit
    weight_match = re.search(r'(\d+(?:\.\d+)?)\s*(kg|lb|lbs)?', exercise_line)
    weight_unit = 'kg'  # default
    
    if weight_match and weight_match.group(2):
        weight_unit = weight_match.group(2)
    
    # Pattern 1: "Nkg Nx(reps)" - single weight with multiple sets
    pattern1 = re.search(r'(\d+(?:\.\d+)?)\s*kg\s+(\d+)\s*x\s*(\d+)', exercise_line, re.IGNORECASE)
    if pattern1:
        weight = pattern1.group(1)
        sets_count = int(pattern1.group(2))
        reps = pattern1.group(3)
        for _ in range(sets_count):
            sets_info.append(f"{weight}({reps})")
        return weight_unit, ', '.join(sets_info)
    
    # Pattern 2: "Nkg Nx(reps), Nkg Nx(reps), ..." - multiple weights
    pattern2_matches = re.findall(r'(\d+(?:\.\d+)?)\s*kg?\s*[,x]?\s*(\d+)\s*x\s*(\d+)', exercise_line, re.IGNORECASE)
    if pattern2_matches and len(pattern2_matches) > 1:
        for weight, count, reps in pattern2_matches:
            sets_count = int(count)
            for _ in range(sets_count):
                sets_info.append(f"{weight}({reps})")
        return weight_unit, ', '.join(sets_info)
    
    # Pattern 3: "Nkg 1x10, N 2x10" - shorthand with multiple entries
    pattern3_matches = re.findall(r'(\d+(?:\.\d+)?)\s*(?:kg)?\s+(\d+)\s*x\s*(\d+)', exercise_line, re.IGNORECASE)
    if pattern3_matches:
        for weight, count, reps in pattern3_matches:
            sets_count = int(count)
            for _ in range(sets_count):
                sets_info.append(f"{weight}({reps})")
        if sets_info:
            return weight_unit, ', '.join(sets_info)
    
    # Pattern 4: Just "Nx(reps)" without weight
    pattern4_matches = re.findall(r'(\d+)\s*x\s*(\d+)', exercise_line)
    if pattern4_matches:
        for count, reps in pattern4_matches:
            sets_count = int(count)
            for _ in range(sets_count):
                sets_info.append(f"({reps})")
        if sets_info:
            return weight_unit, ', '.join(sets_info) + " # TODO: check format — no weight found"
    
    # Pattern 5: Just numbers like "6, 6, 6"
    pattern5_matches = re.findall(r'\b(\d+)\b', exercise_line)
    if pattern5_matches and len(pattern5_matches) > 1:
        for num in pattern5_matches:
            sets_info.append(f"({num})")
        return weight_unit, ', '.join(sets_info) + " # TODO: check format — no weight found"
    
    # Couldn't parse - return as-is with TODO
    return weight_unit, exercise_line + " # TODO: check format"

def is_exercise_line(line):
    """Determine if a line is an exercise or a note."""
    line = line.strip()
    if not line:
        return False
    
    # Common note keywords
    note_keywords = ['note', 'felt', 'sore', 'sick', 'injury', 'pain', 'mood', 'comment', 'weather', 'tired']
    lower_line = line.lower()
    
    for keyword in note_keywords:
        if keyword in lower_line:
            return False
    
    # Exercise lines typically contain sets/reps patterns
    if re.search(r'\d+\s*x\s*\d+', line) or re.search(r'\(\d+\)', line) or re.search(r'min', line, re.IGNORECASE):
        return True
    
    # Check for exercise keywords
    exercise_keywords = ['run', 'walk', 'squat', 'press', 'pull', 'push', 'row', 'curl', 'dips', 'sit', 'crunch', 'yoga', 'stretch', 'pulse', 'meditation', 'lift']
    for keyword in exercise_keywords:
        if keyword in lower_line:
            return True
    
    # Default: treat as exercise if it doesn't look like a note
    return True

def parse_exercises(body):
    """Parse exercises from body text."""
    exercises = []
    notes_lines = []
    
    for line in body.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        
        if is_exercise_line(line):
            # Parse exercise
            exercise_name = re.sub(r'\s*\d+.*', '', line).strip()
            exercise_name = expand_abbreviations(exercise_name)
            exercise_name = title_case_exercise(exercise_name)
            
            # Handle duration-based exercises (cardio, yoga, etc.)
            duration_match = re.search(r'(\d+(?:\.\d+)?)\s*min', line, re.IGNORECASE)
            if duration_match:
                duration = duration_match.group(1)
                exercises.append({
                    'name': exercise_name,
                    'sets': f'duration: {duration}min'
                })
            else:
                weight_unit, sets = parse_sets(line)
                exercises.append({
                    'name': exercise_name,
                    'sets': sets
                })
        else:
            notes_lines.append(line)
    
    return exercises, '\n'.join(notes_lines) if notes_lines else ""

def build_yaml(fm_dict):
    """Manually build YAML frontmatter."""
    lines = []
    for key in ['created', 'date', 'log-in', 'log-out', 'duration', 'tags', 'exercises']:
        if key not in fm_dict:
            continue
        
        value = fm_dict[key]
        if key == 'tags':
            lines.append('tags:')
            for tag in value:
                lines.append(f'  - {tag}')
        elif key == 'exercises':
            lines.append('exercises:')
            for exc in value:
                lines.append(f'  - name: {exc["name"]}')
                lines.append(f'    sets: {exc["sets"]}')
        else:
            if value == "":
                lines.append(f'{key}:')
            else:
                lines.append(f'{key}: {value}')
    
    return '\n'.join(lines)


    """Convert a single workout file."""
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    fm, body = parse_frontmatter(content)
    
    # Parse frontmatter fields
    created_time = parse_time(fm.get('Created time', ''))
    last_edited = parse_time(fm.get('Last edited time', ''))
    date = fm.get('Date', '')
    done = fm.get('Done', False)
    
    # Build new frontmatter
    new_fm = {
        'created': time_to_full(created_time),
        'date': date,
        'log-in': time_to_hhmm(created_time),
        'log-out': time_to_hhmm(last_edited),
        'duration': calculate_duration(created_time, last_edited),
        'tags': ['project/workout']
    }
    
    if done:
        new_fm['tags'].append('status/done')
    else:
        new_fm['tags'].append('status/not-started')
    
    # Parse exercises
    exercises, notes = parse_exercises(body)
    new_fm['exercises'] = exercises
    
    # Build new content
    fm_yaml = build_yaml(new_fm)
    
    new_content = f"---\n{fm_yaml}\n---\n\n## Notes\n\n"
    if notes:
        new_content += notes
    else:
        new_content += "<!-- No notes imported from Notion -->"
    
    return new_content

def main():
    """Convert all workout files."""
    source = Path(SOURCE_DIR)
    output = Path(OUTPUT_DIR)
    
    md_files = list(source.glob('*.md'))
    print(f"Found {len(md_files)} markdown files to convert")
    
    success = 0
    errors = 0
    
    for md_file in sorted(md_files):
        try:
            converted = convert_file(md_file)
            output_file = output / md_file.name
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(converted)
            
            success += 1
            if success % 50 == 0:
                print(f"  Converted {success} files...")
        except Exception as e:
            errors += 1
            print(f"ERROR converting {md_file.name}: {e}")
    
    print(f"\nConversion complete: {success} succeeded, {errors} failed")

if __name__ == '__main__':
    main()
