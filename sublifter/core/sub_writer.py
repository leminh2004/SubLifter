import os

def format_srt_time(seconds: float) -> str:
    """Convert seconds to SRT timestamp format: HH:MM:SS,mmm"""
    if seconds < 0:
        seconds = 0.0
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms >= 1000:
        ms = 0
        secs += 1
        if secs >= 60:
            secs = 0
            mins += 1
            if mins >= 60:
                mins = 0
                hrs += 1
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{ms:03d}"

def format_ass_time(seconds: float) -> str:
    """Convert seconds to ASS timestamp format: H:MM:SS.cc"""
    if seconds < 0:
        seconds = 0.0
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 0
        secs += 1
        if secs >= 60:
            secs = 0
            mins += 1
            if mins >= 60:
                mins = 0
                hrs += 1
    return f"{hrs:d}:{mins:02d}:{secs:02d}.{cs:02d}"

def write_srt(subtitles: list, output_path: str):
    """
    Write a list of subtitles to an SRT file.
    Each item in subtitles list should be a dict:
    {
        'start': float (seconds),
        'end': float (seconds),
        'text': str
    }
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        for idx, sub in enumerate(subtitles, 1):
            start_str = format_srt_time(sub['start'])
            end_str = format_srt_time(sub['end'])
            # Replace newlines with standard newlines
            text = sub['text'].replace('\\N', '\n').strip()
            f.write(f"{idx}\n{start_str} --> {end_str}\n{text}\n\n")

def write_ass(subtitles: list, output_path: str):
    """Write a list of subtitles to an ASS file."""
    header = (
        "[Script Info]\n"
        "Title: Extracted Subtitles\n"
        "ScriptType: v4.00+\n"
        "WrapStyle: 0\n"
        "PlayResX: 1920\n"
        "PlayResY: 1080\n"
        "ScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,22,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,2,2,10,10,10,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(header)
        for sub in subtitles:
            start_str = format_ass_time(sub['start'])
            end_str = format_ass_time(sub['end'])
            # ASS uses \N for newlines
            text = sub['text'].replace('\n', '\\N').strip()
            f.write(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{text}\n")
