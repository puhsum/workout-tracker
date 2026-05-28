#!/usr/bin/env python3
import re
from pathlib import Path
from datetime import datetime

def parse_frontmatter(content):
    """Parse frontmatter and return dict of keys and body."""
    pattern = r'^---\n(.*?)\n---\n(.*)$'
    match = re.match(pattern, content, re.DOTALL)
    if not match:
        return {}, content
    
    fm_text, body = match.groups()
    fm_dict = {}
    for line in fm_text.split('\n'):
        line = line.strip()
        if not line or line.startswith('-'):
            continue
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            fm_dict[key] = value
    
    return fm_dict, body

def parse_time(time_str):
    """Parse ISO time format: 2024-10-17T09:23:00 or 2024-10-17T09:55:00"""
    if not time_str or 'T' not in time_str:
        return None
    time_str = time_str.split('.')[0]  # Remove milliseconds
    return datetime.fromisoformat(time_str.replace('Z', '+00:00'))

def format_datetime(dt, fmt):
    """Format datetime object."""
    if not dt:
        return ""
    if fmt == "YYYY-MM-DD HH:mm":
        return dt.strftime("%Y-%m-%d %H:%M")
    elif fmt == "YYYY-MM-DD":
        return dt.strftime("%Y-%m-%d")
    elif fmt == "HH:mm":
        return dt.strftime("%H:%M")
    return ""

def expand_abbreviations(name):
    """Expand Bb→Barbell, Db→Dumbbell."""
    name = re.sub(r'\bBb\b', 'Barbell', name, flags=re.IGNORECASE)
    name = re.sub(r'\bDb\b', 'Dumbbell', name, flags=re.IGNORECASE)
    return name

def title_case_exercise(name):
    """Title case the exercise name."""
    words = name.split()
    result = []
    for word in words:
        if word and word[0].isalpha():
            result.append(word[0].upper() + word[1:].lower())
        else:
            result.append(word)
    return ' '.join(result)

def clean_exercise_name(name):
    """Clean and standardize exercise name."""
    name = name.strip()
    name = expand_abbreviations(name)
    name = title_case_exercise(name)
    return name

def parse_sets(exercise_line):
    """Parse exercise line and extract name and sets."""
    line = exercise_line.strip()
    
    # Remove markdown bold markers
    line = re.sub(r'^\*\*', '', line)
    line = re.sub(r'\*\*$', '', line)
    
    # Check if it's a duration-based exercise (e.g., "3mins run", "5min walk")
    duration_match = re.match(r'^(.+?)\s+(\d+\.?\d*)\s*(min|mins|sec|secs)(.*)$', line, re.IGNORECASE)
    if duration_match:
        exercise_name = duration_match.group(1).strip()
        duration = duration_match.group(2)
        unit = duration_match.group(3).lower()
        if unit in ['min', 'mins']:
            return clean_exercise_name(exercise_name), f"duration: {duration}min"
        else:
            return clean_exercise_name(exercise_name), f"duration: {duration}{unit}"
    
    # Try to extract weight/sets format
    # Pattern: ExerciseName weight(reps) or ExerciseName reps
    sets_pattern = r'(\d+\.?\d*)\s*kg?\s*\((\d+)\)|(\d+\.?\d*)\s*kg?\s+(\d+)\s*x\s*(\d+)|(\d+)\s*x\s*(\d+)|(\d+\.?\d*)\s*kg?(?:\s|,|$)'
    
    # Find where the exercise name ends and numbers begin
    match = re.search(r'(\d+\.?\d*\s*(?:kg|x|\(|\d))', line)
    
    if match:
        exercise_name = line[:match.start()].strip()
        sets_part = line[match.start():].strip()
    else:
        return clean_exercise_name(line), "(?) # TODO: check format"
    
    # Parse the sets part
    sets_list = []
    
    # Handle format like "50(10), 65(10), 65(10)" or "30 3x10" or "15kg, 17.5kg"
    if '(' in sets_part:
        # Format: weight(reps), weight(reps)
        entries = [e.strip() for e in sets_part.split(',')]
        for entry in entries:
            entry_match = re.match(r'(\d+\.?\d*)\s*kg?\s*\((\d+)\)', entry)
            if entry_match:
                weight = entry_match.group(1)
                reps = entry_match.group(2)
                sets_list.append(f"{weight}({reps})")
            else:
                sets_list.append(entry)
    elif 'x' in sets_part.lower():
        # Format: weight 3x10 or 1x10, 2x10
        entries = [e.strip() for e in sets_part.split(',')]
        weights_and_reps = []
        for entry in entries:
            match = re.match(r'(\d+\.?\d*)\s*kg?\s+(\d+)\s*x\s*(\d+)', entry)
            if match:
                weight = match.group(1)
                num_sets = int(match.group(2))
                reps = match.group(3)
                for _ in range(num_sets):
                    weights_and_reps.append((weight, reps))
            else:
                match = re.match(r'(\d+\.?\d*)\s*kg?\s+(\d+)\s*x\s*(\d+)', entry)
                if match:
                    weights_and_reps.append((match.group(1), match.group(3)))
        
        for w, r in weights_and_reps:
            sets_list.append(f"{w}({r})")
    else:
        # Format: just numbers like "10, 10, 6" or weights like "15kg, 17.5kg"
        entries = [e.strip() for e in sets_part.split(',')]
        for entry in entries:
            match = re.match(r'^(\d+\.?\d*)\s*kg?$', entry)
            if match:
                sets_list.append(f"{match.group(1)}(?) # TODO: check format")
            else:
                sets_list.append(f"({entry}) # TODO: check format")
    
    if not sets_list:
        return clean_exercise_name(exercise_name), sets_part + " # TODO: check format"
    
    return clean_exercise_name(exercise_name), ', '.join(sets_list)

def extract_exercises_and_notes(body):
    """Extract exercises and notes from body."""
    lines = body.strip().split('\n')
    exercises = []
    notes_lines = []
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        
        # Check if line looks like an exercise (contains numbers or known exercise keywords)
        if (re.search(r'\d+\s*(?:x|kg|\(|\))', line_stripped) or
            re.search(r'min|mins|sec|secs', line_stripped, re.IGNORECASE)):
            # Try to parse as exercise
            name, sets = parse_sets(line_stripped)
            if name:
                exercises.append({'name': name, 'sets': sets})
            else:
                notes_lines.append(line_stripped)
        else:
            notes_lines.append(line_stripped)
    
    notes = '\n'.join(notes_lines).strip()
    return exercises, notes

def convert_file(input_path, output_path):
    """Convert a single file from Notion to Obsidian format."""
    content = input_path.read_text(encoding='utf-8')
    fm_dict, body = parse_frontmatter(content)
    
    # Parse frontmatter values
    created_time = parse_time(fm_dict.get('Created time', ''))
    last_edited_time = parse_time(fm_dict.get('Last edited time', ''))
    date_str = fm_dict.get('Date', '')
    done = fm_dict.get('Done', 'false').lower() == 'true'
    
    # Build Obsidian frontmatter
    created_str = format_datetime(created_time, "YYYY-MM-DD HH:mm") if created_time else ""
    log_in_str = format_datetime(created_time, "HH:mm") if created_time else ""
    log_out_str = format_datetime(last_edited_time, "HH:mm") if last_edited_time else ""
    
    # Calculate duration
    duration = ""
    if created_time and last_edited_time:
        diff = (last_edited_time - created_time).total_seconds()
        duration = str(int(diff / 60))
    
    # Extract exercises and notes
    exercises, notes = extract_exercises_and_notes(body)
    
    # Build new frontmatter
    output_fm = f"created: {created_str}\n"
    output_fm += f"date: {date_str}\n"
    output_fm += f"log-in: {log_in_str}\n"
    output_fm += f"log-out: {log_out_str}\n"
    output_fm += f"duration: {duration}\n"
    output_fm += "tags:\n"
    output_fm += "  - project/workout\n"
    output_fm += f"  - status/{'done' if done else 'not-started'}\n"
    
    if exercises:
        output_fm += "exercises:\n"
        for ex in exercises:
            output_fm += f"  - name: {ex['name']}\n"
            output_fm += f"    sets: {ex['sets']}\n"
    
    # Build output content
    output_content = f"---\n{output_fm}---\n\n## Notes\n\n"
    if notes:
        output_content += notes + "\n"
    else:
        output_content += "<!-- No notes imported from Notion -->\n"
    
    output_path.write_text(output_content, encoding='utf-8')

def main():
    source_dir = Path(r"c:\Users\gabrsc\OneDrive - ASSA ABLOY Group\Desktop\gym-logs\Notion\workout-tracker")
    output_dir = Path(r"c:\Users\gabrsc\OneDrive - ASSA ABLOY Group\Desktop\gym-logs\workout-converted")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    md_files = sorted(source_dir.glob("*.md"))
    print(f"Found {len(md_files)} markdown files to convert")
    
    for i, md_file in enumerate(md_files, 1):
        try:
            output_file = output_dir / md_file.name
            convert_file(md_file, output_file)
            print(f"[{i}/{len(md_files)}] Converted: {md_file.name}")
        except Exception as e:
            print(f"ERROR converting {md_file.name}: {e}")
    
    print(f"\nConversion complete! Files saved to {output_dir}")

if __name__ == "__main__":
    main()
