import os
import re
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable

class GeminiTranscriber:
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-3.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model_name = model_name

    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 10)

    def transcribe_and_summarize(
        self,
        audio_path: Path,
        expected_speakers: Optional[int] = None,
        speaker_hints: Optional[str] = None,
        meeting_context: Optional[str] = None,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> Dict[str, Any]:
        """
        Uploads audio to Gemini File API and performs multi-speaker transcription & smart summary.
        """
        if not self.is_configured():
            raise ValueError("Chưa cấu hình Gemini API Key. Vui lòng nhập API Key để tiếp tục!")

        if progress_callback:
            progress_callback("Đang kết nối tới Google Gemini AI...", 10)

        # Primary modern GenAI SDK
        try:
            return self._process_with_google_genai(
                audio_path, expected_speakers, speaker_hints, meeting_context, progress_callback
            )
        except Exception as e:
            err_str = str(e)
            if "API_KEY_INVALID" in err_str or "API key not valid" in err_str:
                raise ValueError("Gemini API Key không hợp lệ! Khóa Google AI Studio chuẩn thường bắt đầu bằng 'AIzaSy...'. Vui lòng kiểm tra lại tại aistudio.google.com/app/apikey")
            raise RuntimeError(f"Lỗi khi xử lý qua Gemini AI: {err_str}")

    def _build_prompt(
        self,
        expected_speakers: Optional[int],
        speaker_hints: Optional[str],
        meeting_context: Optional[str]
    ) -> str:
        prompt = """Bạn là một chuyên gia gỡ băng âm thanh/video và thư ký cuộc họp chuyên nghiệp cấp cao.
Đây là file âm thanh/video ghi lại cuộc trao đổi, thảo luận hoặc cuộc họp bằng tiếng Việt (có thể có nhiều người nói).

NHIỆM VỤ QUAN TRỌNG NHẤT CỦA BẠN:

1. BẢN GHI CHÉP LỜI TOÀN BỘ NGUYÊN VĂN 100% (FULL VERBATIM TRANSCRIPT):
   - Bạn PHẢI gỡ băng NGUYÊN VĂN TOÀN BỘ từng câu từng chữ từ đầu đến cuối file mà không được bỏ sót, không nhảy cóc.
   - TUYỆT ĐỐI KHÔNG ĐƯỢC TÓM TẮT, KHÔNG CẮT BỚT NỘI DUNG LỜI THOẠI. Giữ nguyên vẹn toàn bộ các câu trao đổi, tranh luận, giải thích.
   - Phân biệt chính xác từng người nói (Speaker Diarization). Đặt tên nhất quán: "Người nói 1", "Người nói 2",... hoặc tên cụ thể nếu có xưng hô.
   - Mỗi lượt thoại (transcript segment) PHẢI có mốc thời gian bắt đầu và kết thúc chính xác dạng HH:MM:SS (hoặc MM:SS).
   - Tuyệt đối không gộp lời thoại của hai người khác nhau vào cùng một lượt.
   - Cung cấp thêm chuỗi `full_transcript_text`: toàn bộ bản gỡ băng đầy đủ liên tục theo định dạng văn bản đọc liền mạch, mỗi lượt nói xuống dòng rõ ràng kèm mốc thời gian và tên người phát biểu.

2. TỔNG HỢP VÀ TÓM TẮT ĐIỀU HÀNH ĐỂ NẮM BẮT NHANH TOÀN BỘ NỘI DUNG:
   - Viết phần TỔNG QUAN súc tích, mạch lạc (Bối cảnh, mục đích cuộc gặp, kết quả chung).
   - Liệt kê CHI TIẾT CÁC Ý CHÍNH theo từng chủ đề thảo luận.
   - TỔNG HỢP QUAN ĐIỂM & ĐÓNG GÓP của từng người nói (Người A muốn gì, Người B phản biện ra sao).
   - Danh sách CÁC QUYẾT ĐỊNH / ĐIỂM THỐNG NHẤT quan trọng.
   - Danh sách VIỆC CẦN LÀM (ACTION ITEMS): Ai làm, việc gì, thời hạn nếu có.

3. THÔNG TIN BỔ SUNG TỪ NGƯỜI DÙNG:
"""
        if expected_speakers:
            prompt += f"- Số lượng người nói dự kiến: {expected_speakers} người.\n"
        if speaker_hints:
            prompt += f"- Danh sách tên/đặc điểm người nói gợi ý: {speaker_hints}\n"
        if meeting_context:
            prompt += f"- Ngữ cảnh/chủ đề cuộc trò chuyện: {meeting_context}\n"

        prompt += """
ĐỊNH DẠNG KẾT QUẢ ĐẦU RA:
BẮT BUỘC chỉ trả về duy nhất một chuỗi JSON hợp lệ (không kèm lời dẫn Markdown bên ngoài, hoặc nằm trong khối ```json ... ```) tuân thủ cấu trúc sau:

{
  "summary": {
    "title": "Tiêu đề cô đọng, chuyên nghiệp của cuộc họp/trò chuyện",
    "overview": "Đoạn văn 3-5 câu tóm tắt toàn bộ bối cảnh, mục đích và kết quả tổng thể",
    "key_topics": [
      {
        "topic": "Tên vấn đề/chủ đề thảo luận",
        "discussion": "Chi tiết các ý kiến được đưa ra trong cuộc trao đổi",
        "outcome": "Kết luận hoặc giải pháp cho vấn đề này"
      }
    ],
    "speaker_viewpoints": [
      {
        "speaker": "Tên hoặc nhãn Người nói",
        "role_or_perspective": "Vai trò hoặc lập trường chính",
        "key_statements": ["Ý kiến then chốt 1", "Ý kiến then chốt 2"]
      }
    ],
    "decisions": [
      "Quyết định / thỏa thuận quan trọng 1",
      "Quyết định / thỏa thuận quan trọng 2"
    ],
    "action_items": [
      {
        "assignee": "Tên người phụ trách (hoặc Người nói X)",
        "task": "Nhiệm vụ cụ thể cần triển khai",
        "deadline": "Thời hạn (hoặc 'Cần xác định thêm')"
      }
    ],
    "tags": ["Từ khóa 1", "Từ khóa 2", "Từ khóa 3"]
  },
  "speakers": [
    {
      "id": "speaker_1",
      "name": "Người nói 1",
      "color": "#6366f1",
      "description": "Đặc điểm giọng nói hoặc vai trò"
    }
  ],
  "transcript": [
    {
      "id": 1,
      "speaker": "Người nói 1",
      "start": "00:00:03",
      "end": "00:00:25",
      "text": "Lời phát biểu chính xác đầy đủ..."
    }
  ],
  "full_transcript_text": "[00:00:03] Người nói 1: Lời phát biểu đầy đủ nguyên văn...\\n\\n[00:00:26] Người nói 2: Lời phát biểu đầy đủ..."
}
"""
        return prompt

    def _process_with_google_genai(
        self,
        audio_path: Path,
        expected_speakers: Optional[int],
        speaker_hints: Optional[str],
        meeting_context: Optional[str],
        progress_callback: Optional[Callable[[str, int], None]]
    ) -> Dict[str, Any]:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.api_key)

        if progress_callback:
            progress_callback(f"Đang tải file âm thanh lên Gemini File API ({audio_path.name})...", 20)

        # Upload audio file
        uploaded_file = client.files.upload(file=str(audio_path))
        print(f"[GeminiTranscriber] File uploaded: {uploaded_file.name}, state: {uploaded_file.state}")

        # Wait until file processing completes if needed
        time_elapsed = 0
        while uploaded_file.state.name == "PROCESSING":
            time.sleep(3)
            time_elapsed += 3
            if progress_callback:
                progress_callback(f"Đang chuẩn bị file âm thanh trên máy chủ ({time_elapsed}s)...", 30)
            uploaded_file = client.files.get(name=uploaded_file.name)

        if uploaded_file.state.name != "ACTIVE":
            raise RuntimeError(f"File upload không sẵn sàng: trạng thái {uploaded_file.state.name}")

        prompt = self._build_prompt(expected_speakers, speaker_hints, meeting_context)

        if progress_callback:
            progress_callback("AI đang lắng nghe toàn bộ âm thanh, nhận diện từng người nói và tạo bản tóm tắt...", 50)

        # Generate content with model fallback
        models_to_try = [self.model_name]
        for fallback in ["gemini-3.8-flash", "gemini-flash-latest", "gemini-1.5-flash"]:
            if fallback not in models_to_try:
                models_to_try.append(fallback)

        response = None
        last_error = None
        for m in models_to_try:
            try:
                response = client.models.generate_content(
                    model=m,
                    contents=[
                        uploaded_file,
                        prompt
                    ],
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                        response_mime_type="application/json"
                    )
                )
                break
            except Exception as e:
                last_error = e
                err_text = str(e).lower()
                if "404" in err_text or "not found" in err_text or "no longer available" in err_text:
                    continue
                raise e

        if response is None and last_error:
            raise last_error

        if progress_callback:
            progress_callback("Đang xử lý kết quả phân tích...", 85)

        # Clean up remote file
        try:
            client.files.delete(name=uploaded_file.name)
        except Exception:
            pass

        return self._parse_json_response(response.text)

    def _process_with_generativeai(
        self,
        audio_path: Path,
        expected_speakers: Optional[int],
        speaker_hints: Optional[str],
        meeting_context: Optional[str],
        progress_callback: Optional[Callable[[str, int], None]]
    ) -> Dict[str, Any]:
        import google.generativeai as genai

        genai.configure(api_key=self.api_key)

        if progress_callback:
            progress_callback(f"Đang tải file âm thanh lên Gemini ({audio_path.name})...", 20)

        uploaded_file = genai.upload_file(str(audio_path))
        print(f"[GeminiTranscriber] File uploaded: {uploaded_file.name}, state: {uploaded_file.state.name}")

        time_elapsed = 0
        while uploaded_file.state.name == "PROCESSING":
            time.sleep(3)
            time_elapsed += 3
            if progress_callback:
                progress_callback(f"Đang tiền xử lý âm thanh ({time_elapsed}s)...", 30)
            uploaded_file = genai.get_file(uploaded_file.name)

        if uploaded_file.state.name != "ACTIVE":
            raise RuntimeError(f"File upload không sẵn sàng: trạng thái {uploaded_file.state.name}")

        prompt = self._build_prompt(expected_speakers, speaker_hints, meeting_context)

        if progress_callback:
            progress_callback("AI đang nhận diện người nói và tổng hợp nội dung cuộc trò chuyện...", 55)

        model = genai.GenerativeModel(model_name=self.model_name)
        response = model.generate_content(
            [uploaded_file, prompt],
            generation_config={"temperature": 0.2}
        )

        if progress_callback:
            progress_callback("Đang hoàn thiện cấu trúc dữ liệu...", 85)

        try:
            genai.delete_file(uploaded_file.name)
        except Exception:
            pass

        return self._parse_json_response(response.text)

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Safely parse JSON response from LLM, stripping markdown wrappers if present."""
        text = text.strip()
        # Remove ```json and ``` if present
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Try to locate the outermost { }
            match = re.search(r"(\{.*\})", text, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
            else:
                raise ValueError("Không thể phân tích dữ liệu JSON trả về từ Gemini AI")

        # Color palette for speakers
        colors = [
            "#6366f1", "#06b6d4", "#10b981", "#f59e0b",
            "#ec4899", "#8b5cf6", "#14b8a6", "#ef4444"
        ]

        # Ensure speakers have colors and uniform structure
        speakers = data.get("speakers", [])
        speaker_map = {}
        for idx, s in enumerate(speakers):
            s_name = s.get("name", f"Người nói {idx+1}")
            if "color" not in s:
                s["color"] = colors[idx % len(colors)]
            speaker_map[s_name] = s

        # Auto-populate missing speakers from transcript if any
        transcript = data.get("transcript", [])
        for item in transcript:
            spk_name = item.get("speaker", "Người nói")
            if spk_name not in speaker_map:
                color = colors[len(speaker_map) % len(colors)]
                speaker_obj = {
                    "id": f"speaker_{len(speaker_map)+1}",
                    "name": spk_name,
                    "color": color,
                    "description": ""
                }
                speaker_map[spk_name] = speaker_obj
                speakers.append(speaker_obj)

        data["speakers"] = speakers

        # Build / normalize full_transcript_text
        full_transcript_text = data.get("full_transcript_text", "").strip()
        if not full_transcript_text and transcript:
            lines = []
            for item in transcript:
                spk = item.get("speaker", "Người nói")
                start = item.get("start", "00:00")
                end = item.get("end", "")
                time_tag = f"[{start} - {end}]" if end else f"[{start}]"
                text = item.get("text", "").strip()
                lines.append(f"{time_tag} {spk}:\n{text}")
            full_transcript_text = "\n\n".join(lines)

        data["full_transcript_text"] = full_transcript_text

        # Compute word count
        total_words = sum(len(item.get("text", "").split()) for item in transcript)
        data["word_count"] = total_words

        return data

    def ask_chat(self, transcript_text: str, summary_data: Dict[str, Any], question: str) -> str:
        """Interactive Q&A assistant with the meeting content."""
        if not self.is_configured():
            return "Vui lòng cung cấp Gemini API Key để trò chuyện với nội dung cuộc họp."

        prompt = f"""Bạn là trợ lý thông minh về nội dung cuộc họp/trò chuyện đã được ghi âm.
Dưới đây là thông tin tóm tắt và bản ghi chép chi tiết:

TỔNG QUAN CUỘC HỌP:
Tiêu đề: {summary_data.get('title', '')}
Bối cảnh: {summary_data.get('overview', '')}
Các quyết định: {json.dumps(summary_data.get('decisions', []), ensure_ascii=False)}
Việc cần làm: {json.dumps(summary_data.get('action_items', []), ensure_ascii=False)}

BẢN GHI LỜI THOẠI CHI TIẾT (TRANSCRIPT):
{transcript_text[:150000]}

CÂU HỎI CỦA NGƯỜI DÙNG:
{question}

HƯỚNG DẪN TRẢ LỜI:
- Trả lời bằng tiếng Việt, chính xác, súc tích, đi thẳng vào vấn đề.
- Chỉ ra rõ người nào đã phát biểu điều đó và kèm mốc thời gian nếu có.
- Nếu thông tin không có trong văn bản, hãy nói rõ là trong cuộc trò chuyện không đề cập đến.
"""
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            resp = client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return resp.text
        except Exception:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model_name)
            resp = model.generate_content(prompt)
            return resp.text
