"""Video composition for YouTube Shorts.

Combines AI-generated video scenes with subtitles and voice narration
into a final vertical format (1080x1920) video ready for upload.
"""

import os
import textwrap
import uuid

from moviepy import (
    AudioFileClip,
    CompositeVideoClip,
    TextClip,
    VideoFileClip,
    concatenate_videoclips,
)

import config


def compose_video(scene_paths, audio_path, script_data, output_path=None):
    """Compose the final video from scenes, audio, and script data.

    Combines video scenes, overlays subtitles, and mixes in narration
    audio to create a complete YouTube Short.

    Args:
        scene_paths: List of paths to video scene files.
        audio_path: Path to the narration audio file.
        script_data: Script dictionary with narration text.
        output_path: Path for the output video. If None, auto-generated.

    Returns:
        str: Path to the composed video file.
    """
    config.ensure_directories()

    if output_path is None:
        video_id = uuid.uuid4().hex[:8]
        output_path = os.path.join(config.VIDEO_DIR, f"short_{video_id}.mp4")

    video_clips = []
    for path in scene_paths:
        clip = VideoFileClip(path)
        clip = _resize_to_vertical(clip)
        video_clips.append(clip)

    if len(video_clips) == 1:
        base_video = video_clips[0]
    else:
        base_video = concatenate_videoclips(video_clips, method="compose")

    audio_clip = AudioFileClip(audio_path)

    if base_video.duration < audio_clip.duration:
        base_video = base_video.loop(duration=audio_clip.duration)
    elif base_video.duration > audio_clip.duration + 1:
        padding = config.VIDEO_AUDIO_PADDING_SECONDS
        base_video = base_video.subclipped(0, audio_clip.duration + padding)

    base_video = base_video.with_audio(audio_clip)

    subtitle_clips = _create_subtitle_clips(script_data, base_video.duration)

    final = CompositeVideoClip(
        [base_video] + subtitle_clips,
        size=(config.VIDEO_WIDTH, config.VIDEO_HEIGHT),
    )

    final.write_videofile(
        output_path,
        fps=config.VIDEO_FPS,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        threads=4,
    )

    for clip in video_clips:
        clip.close()
    audio_clip.close()
    final.close()

    return output_path


def _resize_to_vertical(clip):
    """Resize a clip to vertical format preserving aspect ratio.

    Scales the clip to fill the target vertical dimensions, cropping
    the excess rather than distorting the image.

    Args:
        clip: A MoviePy VideoFileClip to resize.

    Returns:
        VideoFileClip: The resized clip at VIDEO_WIDTH x VIDEO_HEIGHT.
    """
    target_w = config.VIDEO_WIDTH
    target_h = config.VIDEO_HEIGHT
    target_ratio = target_w / target_h

    clip_ratio = clip.w / clip.h

    if clip_ratio > target_ratio:
        # Clip is wider: scale by height, crop width
        clip = clip.resized(height=target_h)
        excess = clip.w - target_w
        if excess > 0:
            clip = clip.cropped(
                x1=excess // 2, x2=clip.w - (excess - excess // 2)
            )
    else:
        # Clip is taller: scale by width, crop height
        clip = clip.resized(width=target_w)
        excess = clip.h - target_h
        if excess > 0:
            clip = clip.cropped(
                y1=excess // 2, y2=clip.h - (excess - excess // 2)
            )

    return clip


def _create_subtitle_clips(script_data, total_duration):
    """Create subtitle text overlay clips from script data.

    Args:
        script_data: Script dictionary containing narration segments.
        total_duration: Total video duration in seconds.

    Returns:
        list: TextClip objects positioned for subtitle overlay.
    """
    content_type = script_data.get("content_type", "curiosity_fact")

    if content_type == "curiosity_fact":
        segments = [
            script_data.get("hook", ""),
            script_data.get("fact", ""),
        ]
    else:
        segments = [
            script_data.get("hook", ""),
            script_data.get("tension", ""),
            script_data.get("resolution", ""),
            script_data.get("twist", ""),
        ]

    segments = [s for s in segments if s]
    if not segments:
        return []

    segment_duration = total_duration / len(segments)
    subtitle_clips = []

    for i, text in enumerate(segments):
        wrapped = textwrap.fill(text, width=25)
        start_time = i * segment_duration
        end_time = start_time + segment_duration

        txt_clip = (
            TextClip(
                text=wrapped,
                font_size=config.SUBTITLE_FONT_SIZE,
                color=config.SUBTITLE_FONT_COLOR,
                stroke_color=config.SUBTITLE_STROKE_COLOR,
                stroke_width=config.SUBTITLE_STROKE_WIDTH,
                method="caption",
                size=(config.VIDEO_WIDTH - 100, None),
                text_align="center",
            )
            .with_position(("center", config.VIDEO_HEIGHT * 0.7))
            .with_start(start_time)
            .with_duration(end_time - start_time)
        )

        subtitle_clips.append(txt_clip)

    return subtitle_clips


def compose_video_with_timestamps(scene_paths, audio_path, timestamps,
                                  output_path=None):
    """Compose video with word-level synchronized subtitles.

    Uses word-level timestamps from voice generation for precise
    subtitle synchronization.

    Args:
        scene_paths: List of paths to video scene files.
        audio_path: Path to the narration audio file.
        timestamps: Word-level timestamps from generate_voice.
        output_path: Path for the output video. If None, auto-generated.

    Returns:
        str: Path to the composed video file.
    """
    config.ensure_directories()

    if output_path is None:
        video_id = uuid.uuid4().hex[:8]
        output_path = os.path.join(config.VIDEO_DIR, f"short_{video_id}.mp4")

    video_clips = []
    for path in scene_paths:
        clip = VideoFileClip(path)
        clip = _resize_to_vertical(clip)
        video_clips.append(clip)

    if len(video_clips) == 1:
        base_video = video_clips[0]
    else:
        base_video = concatenate_videoclips(video_clips, method="compose")

    audio_clip = AudioFileClip(audio_path)

    if base_video.duration < audio_clip.duration:
        base_video = base_video.loop(duration=audio_clip.duration)

    base_video = base_video.with_audio(audio_clip)

    word_groups = _group_words_into_phrases(timestamps)
    subtitle_clips = []

    for group in word_groups:
        phrase = " ".join(w["text"] for w in group)
        wrapped = textwrap.fill(phrase, width=25)
        start = group[0]["start"]
        end = group[-1]["end"]

        txt_clip = (
            TextClip(
                text=wrapped,
                font_size=config.SUBTITLE_FONT_SIZE,
                color=config.SUBTITLE_FONT_COLOR,
                stroke_color=config.SUBTITLE_STROKE_COLOR,
                stroke_width=config.SUBTITLE_STROKE_WIDTH,
                method="caption",
                size=(config.VIDEO_WIDTH - 100, None),
                text_align="center",
            )
            .with_position(("center", config.VIDEO_HEIGHT * 0.7))
            .with_start(start)
            .with_duration(max(end - start, 0.1))
        )

        subtitle_clips.append(txt_clip)

    final = CompositeVideoClip(
        [base_video] + subtitle_clips,
        size=(config.VIDEO_WIDTH, config.VIDEO_HEIGHT),
    )

    final.write_videofile(
        output_path,
        fps=config.VIDEO_FPS,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        threads=4,
    )

    for clip in video_clips:
        clip.close()
    audio_clip.close()
    final.close()

    return output_path


def _group_words_into_phrases(timestamps, max_words=5):
    """Group individual word timestamps into displayable phrases.

    Args:
        timestamps: List of word timestamp dicts.
        max_words: Maximum words per subtitle phrase.

    Returns:
        list[list[dict]]: Grouped word timestamp lists.
    """
    groups = []
    current_group = []

    for word in timestamps:
        current_group.append(word)
        if len(current_group) >= max_words:
            groups.append(current_group)
            current_group = []

    if current_group:
        groups.append(current_group)

    return groups
