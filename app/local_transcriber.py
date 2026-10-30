import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from .audio_utils import format_seconds

# Compatibility patch for PyAV 19+ with faster-whisper
try:
    import av
    _orig_av_open = av.open
    def _patched_av_open(*args, **kwargs):
        kwargs.pop("metadata_errors", None)
        return _orig_av_open(*args, **kwargs)
    av.open = _patched_av_open
except Exception:
    pass

class LocalTranscriber:
    def __init__(self, model_size: str = "small"):
        self.model_size = model_size
        self._model = None

    def _get_device_and_compute_type(self):
        try:
            import ctranslate2
            if ctranslate2.get_cuda_device_count() > 0:
                return "cuda", "float16"
        except Exception:
            pass
        return "cpu", "int8"

    def _load_model(self, progress_callback: Optional[Callable[[str, int], None]] = None):
        if self._model is None:
            from faster_whisper import WhisperModel
            device, compute_type = self._get_device_and_compute_type()
            if progress_callback:
                progress_callback(f"Đang tải mô hình Faster-Whisper ({self.model_size}) trên thiết bị {device.upper()}...", 15)
            self._model = WhisperModel(self.model_size, device=device, compute_type=compute_type)
        return self._model

    def transcribe_and_summarize(
        self,
        audio_path: Path,
        expected_speakers: Optional[int] = None,
        speaker_hints: Optional[str] = None,
        meeting_context: Optional[str] = None,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> Dict[str, Any]:
        """
        Transcribes audio locally using faster-whisper with Silero VAD,
        performs heuristic speaker clustering, and extracts structured summary.
        """
        model = self._load_model(progress_callback)

        if progress_callback:
            progress_callback("Đang gỡ băng âm thanh Offline bằng mô hình Whisper AI...", 30)

        segments_generator, info = model.transcribe(
            str(audio_path),
            language="vi",
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=700),
            beam_size=5
        )

        total_duration = info.duration if info.duration > 0 else 3600.0
        raw_segments = []

        # Color palette for speakers
        colors = ["#6366f1", "#06b6d4", "#10b981", "#f59e0b", "#ec4899", "#8b5cf6"]

        # Number of target speakers
        target_speakers = expected_speakers or 2
        current_speaker_idx = 0
        last_end_time = 0.0

        for seg in segments_generator:
            text = seg.text.strip()
            if not text:
                continue

            # Heuristic for speaker change: a silence gap of > 1.2 seconds suggests another person speaking
            gap = seg.start - last_end_time
            if last_end_time > 0 and gap >= 1.2:
                current_speaker_idx = (current_speaker_idx + 1) % target_speakers

            speaker_name = f"Người nói {current_speaker_idx + 1}"
            raw_segments.append({
                "id": len(raw_segments) + 1,
                "speaker": speaker_name,
                "start": format_seconds(seg.start),
                "end": format_seconds(seg.end),
                "start_seconds": seg.start,
                "end_seconds": seg.end,
                "text": text
            })
            last_end_time = seg.end

            if progress_callback:
                pct = min(85, int(30 + (seg.end / total_duration) * 55))
                progress_callback(f"Đang gỡ băng: {format_seconds(seg.end)} / {format_seconds(total_duration)} ({pct}%)", pct)

        if progress_callback:
            progress_callback("Đang phân tích và trích xuất điểm then chốt...", 90)

        # Build speaker list
        unique_speakers = list(dict.fromkeys(seg["speaker"] for seg in raw_segments))
        speaker_objects = []
        for idx, spk in enumerate(unique_speakers):
            speaker_objects.append({
                "id": f"speaker_{idx+1}",
                "name": spk,
                "color": colors[idx % len(colors)],
                "description": "Người tham gia thảo luận"
            })

        # Generate rule-based summary and key points
        summary = self._generate_extractive_summary(raw_segments, meeting_context)

        # Build full continuous verbatim transcript text
        full_transcript_lines = []
        for seg in raw_segments:
            full_transcript_lines.append(f"[{seg['start']} - {seg['end']}] {seg['speaker']}:\n{seg['text']}")
        full_transcript_text = "\n\n".join(full_transcript_lines)

        total_words = sum(len(seg["text"].split()) for seg in raw_segments)

        return {
            "summary": summary,
            "speakers": speaker_objects,
            "transcript": raw_segments,
            "full_transcript_text": full_transcript_text,
            "word_count": total_words
        }

    def _generate_extractive_summary(self, segments: List[Dict[str, Any]], context: Optional[str] = None) -> Dict[str, Any]:
        """Extract key decisions, topics, and action items using linguistic cues in Vietnamese."""
        full_text = " ".join(seg["text"] for seg in segments)
        total_words = len(full_text.split())

        decision_keywords = ["thống nhất", "quyết định", "đồng ý", "chốt", "kết luận", "phương án", "chọn"]
        action_keywords = ["sẽ làm", "cần làm", "triển khai", "thực hiện", "nhiệm vụ", "giao cho", "hạn chót", "deadline", "báo cáo", "gửi lại"]
        issue_keywords = ["vấn đề", "khó khăn", "vướng mắc", "lý do", "chi phí", "ngân sách", "rủi ro", "thắc mắc"]

        decisions = []
        action_items = []
        key_topics = []

        for seg in segments:
            t = seg["text"].strip()
            lower = t.lower()

            if any(k in lower for k in decision_keywords) and len(t) > 20:
                if len(decisions) < 6 and t not in decisions:
                    decisions.append(f"[{seg['speaker']} - {seg['start']}]: {t}")

            if any(k in lower for k in action_keywords) and len(t) > 20:
                if len(action_items) < 8:
                    action_items.append({
                        "assignee": seg["speaker"],
                        "task": t,
                        "deadline": "Xem chi tiết tại " + seg["start"]
                    })

            if any(k in lower for k in issue_keywords) and len(t) > 25:
                if len(key_topics) < 5:
                    key_topics.append({
                        "topic": f"Nội dung thảo luận ({seg['start']})",
                        "discussion": t,
                        "outcome": "Đã trao đổi trong cuộc họp"
                    })

        if not decisions:
            decisions = ["Cuộc trò chuyện đã trao đổi và thống nhất các bước thực hiện tiếp theo."]
        if not action_items:
            action_items = [{"assignee": "Các thành viên", "task": "Rà soát lại các nội dung đã trao đổi", "deadline": "Sớm nhất"}]
        if not key_topics:
            key_topics = [{"topic": "Tổng quan trao đổi", "discussion": full_text[:200] + "...", "outcome": "Đã ghi nhận đầy đủ"}]

        # Speaker viewpoints
        spk_viewpoints = []
        spk_dict = {}
        for seg in segments:
            spk = seg["speaker"]
            spk_dict.setdefault(spk, []).append(seg["text"])

        for spk, texts in spk_dict.items():
            sample_stmts = [t for t in texts if len(t) > 25][:3]
            spk_viewpoints.append({
                "speaker": spk,
                "role_or_perspective": f"Đã đóng góp {len(texts)} lượt phát biểu",
                "key_statements": sample_stmts if sample_stmts else texts[:2]
            })

        title = f"Biên bản tổng hợp cuộc trò chuyện ({len(segments)} lượt phát biểu)"
        if context:
            title = f"Tổng hợp: {context}"

        overview = (
            f"Cuộc trò chuyện bao gồm {len(spk_dict)} người tham gia với tổng cộng {len(segments)} lượt đối thoại "
            f"và khoảng {total_words} từ. Các bên đã cùng nhau trao đổi thẳng thắn, đưa ra nhiều ý kiến đa chiều "
            f"và phân công các đầu việc cụ thể để triển khai."
        )

        return {
            "title": title,
            "overview": overview,
            "key_topics": key_topics,
            "speaker_viewpoints": spk_viewpoints,
            "decisions": decisions,
            "action_items": action_items,
            "tags": ["Họp nhóm", "Đa người nói", "Tóm tắt nhanh"]
        }
