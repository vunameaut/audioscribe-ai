import os
import uuid
import json
import shutil
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import UPLOAD_DIR, STATIC_DIR, DEFAULT_GEMINI_MODEL, DEFAULT_WHISPER_MODEL
from .audio_utils import get_audio_metadata, optimize_audio_for_gemini, extract_audio_from_media, is_video_file
from .gemini_transcriber import GeminiTranscriber
from .local_transcriber import LocalTranscriber
from .export_service import ExportService

app = FastAPI(title="AudioScribe AI", description="Multi-speaker Audio Transcription & Intelligence Summary")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# In-memory job store (persisted to uploads/<job_id>/data.json)
JOBS: Dict[str, Dict[str, Any]] = {}

def get_job_dir(job_id: str) -> Path:
    jdir = UPLOAD_DIR / job_id
    jdir.mkdir(parents=True, exist_ok=True)
    return jdir

def save_job_state(job_id: str):
    if job_id in JOBS:
        jdir = get_job_dir(job_id)
        data_file = jdir / "data.json"
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(JOBS[job_id], f, ensure_ascii=False, indent=2)

def load_job_state(job_id: str) -> Optional[Dict[str, Any]]:
    data_file = get_job_dir(job_id) / "data.json"
    if data_file.exists():
        with open(data_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            JOBS[job_id] = data
            return data
    return None

class ChatRequest(BaseModel):
    job_id: str
    question: str
    api_key: Optional[str] = None

class RenameSpeakerRequest(BaseModel):
    job_id: str
    old_name: str
    new_name: str

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    fav_path = STATIC_DIR / "favicon.svg"
    if fav_path.exists():
        return FileResponse(path=str(fav_path), media_type="image/svg+xml")
    return HTMLResponse("")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h2>AudioScribe AI is initializing...</h2>")

@app.get("/api/status")
async def system_status():
    has_gpu = False
    gpu_name = "None"
    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count() > 0:
            has_gpu = True
            gpu_name = "NVIDIA CUDA GPU"
    except Exception:
        pass

    return {
        "status": "ready",
        "has_gpu": has_gpu,
        "gpu_name": gpu_name,
        "default_gemini_model": DEFAULT_GEMINI_MODEL,
        "default_whisper_model": DEFAULT_WHISPER_MODEL
    }

class VerifyKeyRequest(BaseModel):
    api_key: str

@app.post("/api/verify-key")
async def verify_api_key(req: VerifyKeyRequest):
    key = req.api_key.strip()
    if not key or len(key) < 15:
        return {"valid": False, "message": "API Key quá ngắn hoặc để trống."}
    try:
        from google import genai
        client = genai.Client(api_key=key)
        resp = client.models.generate_content(
            model=DEFAULT_GEMINI_MODEL,
            contents="hello"
        )
        return {"valid": True, "message": "API Key chính xác và kết nối thành công tới Gemini AI!"}
    except Exception as e:
        err = str(e)
        if "API_KEY_INVALID" in err or "API key not valid" in err:
            return {"valid": False, "message": "API Key không hợp lệ! Khóa Google AI Studio chuẩn thường bắt đầu bằng 'AIzaSy...'. Vui lòng lấy mã khóa miễn phí tại: https://aistudio.google.com/app/apikey"}
        return {"valid": False, "message": f"Lỗi xác thực: {err[:120]}"}

@app.post("/api/upload")
async def upload_audio(file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())[:8]
    job_dir = get_job_dir(job_id)

    # Save uploaded file
    file_ext = Path(file.filename or "media.mp3").suffix or ".mp3"
    saved_path = job_dir / f"original{file_ext}"

    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Extract metadata using ffprobe
    metadata = get_audio_metadata(saved_path)

    # If it is a video file, extract audio for fast transcription & universal playback
    is_video = metadata.get("is_video", False) or is_video_file(saved_path)
    if is_video:
        try:
            extracted_audio_path = job_dir / "extracted_audio.mp3"
            extract_audio_from_media(saved_path, extracted_audio_path)
            audio_path = extracted_audio_path
            message = "Đã nhận diện file Video và trích xuất luồng âm thanh tối ưu thành công!"
        except Exception as e:
            # Fallback to original if audio extraction fails
            print(f"[Upload] Warning: Audio extraction failed: {e}")
            audio_path = saved_path
            message = "Đã nhận diện file Video và sẵn sàng xử lý"
    else:
        audio_path = saved_path
        message = "File âm thanh đã sẵn sàng xử lý"

    JOBS[job_id] = {
        "job_id": job_id,
        "filename": file.filename,
        "media_path": str(saved_path),
        "audio_path": str(audio_path),
        "video_path": str(saved_path) if is_video else "",
        "is_video": is_video,
        "metadata": metadata,
        "status": "uploaded",
        "progress": 0,
        "message": message,
        "result": None
    }
    save_job_state(job_id)

    return {
        "job_id": job_id,
        "filename": file.filename,
        "is_video": is_video,
        "metadata": metadata
    }

def run_transcription_task(
    job_id: str,
    mode: str,
    api_key: Optional[str],
    expected_speakers: Optional[int],
    speaker_hints: Optional[str],
    meeting_context: Optional[str],
    model_name: Optional[str]
):
    try:
        job = JOBS.get(job_id)
        if not job:
            return

        job["status"] = "processing"
        job["progress"] = 5
        job["message"] = "Đang khởi tạo bộ xử lý AI..."
        save_job_state(job_id)

        audio_file = Path(job["audio_path"])

        def progress_cb(msg: str, pct: int):
            job["message"] = msg
            job["progress"] = pct
            save_job_state(job_id)

        if mode == "gemini":
            gemini_model = model_name if (model_name and "gemini" in model_name) else DEFAULT_GEMINI_MODEL
            transcriber = GeminiTranscriber(
                api_key=api_key or os.getenv("GEMINI_API_KEY", ""),
                model_name=gemini_model
            )
            result = transcriber.transcribe_and_summarize(
                audio_path=audio_file,
                expected_speakers=expected_speakers,
                speaker_hints=speaker_hints,
                meeting_context=meeting_context,
                progress_callback=progress_cb
            )
        else: # local faster-whisper
            valid_whisper_models = {"tiny", "tiny.en", "base", "base.en", "small", "small.en", "medium", "medium.en", "large-v1", "large-v2", "large-v3", "turbo"}
            whisper_model = model_name if (model_name and model_name in valid_whisper_models) else DEFAULT_WHISPER_MODEL
            transcriber = LocalTranscriber(
                model_size=whisper_model
            )
            result = transcriber.transcribe_and_summarize(
                audio_path=audio_file,
                expected_speakers=expected_speakers,
                speaker_hints=speaker_hints,
                meeting_context=meeting_context,
                progress_callback=progress_cb
            )

        job["status"] = "completed"
        job["progress"] = 100
        job["message"] = "Hoàn tất nhận diện và tóm tắt thành công!"
        job["result"] = result
        save_job_state(job_id)

    except Exception as e:
        err_msg = str(e)
        if job_id in JOBS:
            JOBS[job_id]["status"] = "failed"
            JOBS[job_id]["message"] = f"Lỗi: {err_msg}"
            save_job_state(job_id)
        try:
            safe_msg = f"[Error in job {job_id}]: {err_msg}".encode("ascii", errors="replace").decode("ascii")
            print(safe_msg)
        except Exception:
            pass

@app.post("/api/process")
async def start_process(
    background_tasks: BackgroundTasks,
    job_id: str = Form(...),
    mode: str = Form("gemini"),
    api_key: Optional[str] = Form(None),
    expected_speakers: Optional[int] = Form(None),
    speaker_hints: Optional[str] = Form(None),
    meeting_context: Optional[str] = Form(None),
    model_name: Optional[str] = Form(None)
):
    if job_id not in JOBS:
        loaded = load_job_state(job_id)
        if not loaded:
            raise HTTPException(status_code=404, detail="Không tìm thấy file ghi âm.")

    background_tasks.add_task(
        run_transcription_task,
        job_id,
        mode,
        api_key,
        expected_speakers,
        speaker_hints,
        meeting_context,
        model_name
    )

    return {"status": "started", "job_id": job_id}

@app.get("/api/job/{job_id}")
async def get_job_info(job_id: str):
    job = JOBS.get(job_id)
    # Always check disk if not in memory or still marked uploaded/processing
    if not job or job.get("status") not in ("completed", "failed"):
        disk_job = load_job_state(job_id)
        if disk_job:
            job = disk_job

    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên làm việc.")
    return job

@app.get("/api/audio/{job_id}")
async def stream_audio(job_id: str):
    job = JOBS.get(job_id) or load_job_state(job_id)
    if not job or not job.get("audio_path"):
        raise HTTPException(status_code=404, detail="Không tìm thấy audio.")
    audio_path = Path(job["audio_path"])
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="File âm thanh không tồn tại trên máy chủ.")

    mime_map = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".aac": "audio/aac",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
        ".webm": "audio/webm",
        ".opus": "audio/opus"
    }
    mime_type = mime_map.get(audio_path.suffix.lower(), "audio/mpeg")

    return FileResponse(path=str(audio_path), media_type=mime_type)

@app.get("/api/video/{job_id}")
async def stream_video(job_id: str):
    job = JOBS.get(job_id) or load_job_state(job_id)
    if not job or not job.get("video_path"):
        raise HTTPException(status_code=404, detail="Không tìm thấy video.")
    video_path = Path(job["video_path"])
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="File video không tồn tại trên máy chủ.")

    mime_map = {
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".mov": "video/quicktime",
        ".mkv": "video/x-matroska",
        ".avi": "video/x-msvideo",
        ".m4v": "video/mp4",
        ".flv": "video/x-flv"
    }
    mime_type = mime_map.get(video_path.suffix.lower(), "video/mp4")

    return FileResponse(path=str(video_path), media_type=mime_type)

@app.post("/api/rename-speaker")
async def rename_speaker(req: RenameSpeakerRequest):
    job = JOBS.get(req.job_id) or load_job_state(req.job_id)
    if not job or not job.get("result"):
        raise HTTPException(status_code=404, detail="Không tìm thấy kết quả của phiên làm việc.")

    result = job["result"]
    old_name = req.old_name.strip()
    new_name = req.new_name.strip()

    if not new_name:
        raise HTTPException(status_code=400, detail="Tên người nói không được để trống.")

    # Update in transcript
    for seg in result.get("transcript", []):
        if seg.get("speaker") == old_name:
            seg["speaker"] = new_name

    # Update in speakers list
    for spk in result.get("speakers", []):
        if spk.get("name") == old_name:
            spk["name"] = new_name

    # Update in summary viewpoints
    for vp in result.get("summary", {}).get("speaker_viewpoints", []):
        if vp.get("speaker") == old_name:
            vp["speaker"] = new_name

    # Update in action items
    for act in result.get("summary", {}).get("action_items", []):
        if act.get("assignee") == old_name:
            act["assignee"] = new_name

    # Update full_transcript_text
    lines = []
    for seg in result.get("transcript", []):
        spk = seg.get("speaker", "Người nói")
        start = seg.get("start", "00:00")
        end = seg.get("end", "")
        t_str = f"[{start} - {end}]" if end else f"[{start}]"
        lines.append(f"{t_str} {spk}:\n{seg.get('text', '')}")
    result["full_transcript_text"] = "\n\n".join(lines)

    save_job_state(req.job_id)
    return {"status": "success", "result": result}

@app.post("/api/chat")
async def meeting_chat(req: ChatRequest):
    job = JOBS.get(req.job_id) or load_job_state(req.job_id)
    if not job or not job.get("result"):
        raise HTTPException(status_code=404, detail="Không tìm thấy kết quả để trò chuyện.")

    result = job["result"]
    transcript = result.get("transcript", [])
    summary = result.get("summary", {})

    transcript_lines = [
        f"[{item.get('start')}] {item.get('speaker')}: {item.get('text')}"
        for item in transcript
    ]
    transcript_text = "\n".join(transcript_lines)

    api_key = req.api_key or os.getenv("GEMINI_API_KEY", "")
    transcriber = GeminiTranscriber(api_key=api_key)

    answer = transcriber.ask_chat(transcript_text, summary, req.question)
    return {"answer": answer}

@app.get("/api/export/{job_id}/{format_type}")
async def export_job(job_id: str, format_type: str):
    job = JOBS.get(job_id) or load_job_state(job_id)
    if not job or not job.get("result"):
        raise HTTPException(status_code=404, detail="Không tìm thấy dữ liệu để xuất file.")

    jdir = get_job_dir(job_id)
    clean_title = "".join(c for c in job["result"].get("summary", {}).get("title", "bien_ban_cuoc_hop") if c.isalnum() or c in (' ', '_', '-')).strip()
    clean_title = clean_title.replace(" ", "_")[:40] or "meeting_transcript"

    if format_type == "docx":
        out_file = jdir / f"{clean_title}.docx"
        ExportService.export_to_docx(job["result"], out_file)
        return FileResponse(path=str(out_file), filename=f"{clean_title}.docx", media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    elif format_type == "md":
        out_file = jdir / f"{clean_title}.md"
        ExportService.export_to_markdown(job["result"], out_file)
        return FileResponse(path=str(out_file), filename=f"{clean_title}.md", media_type="text/markdown")

    elif format_type == "txt":
        out_file = jdir / f"{clean_title}.txt"
        ExportService.export_to_txt(job["result"], out_file)
        return FileResponse(path=str(out_file), filename=f"{clean_title}.txt", media_type="text/plain")

    elif format_type == "full_txt":
        out_file = jdir / f"{clean_title}_toan_van.txt"
        ExportService.export_to_full_txt(job["result"], out_file)
        return FileResponse(path=str(out_file), filename=f"{clean_title}_toan_van.txt", media_type="text/plain; charset=utf-8")

    elif format_type == "srt":
        out_file = jdir / f"{clean_title}.srt"
        ExportService.export_to_srt(job["result"], out_file)
        return FileResponse(path=str(out_file), filename=f"{clean_title}.srt", media_type="application/x-subrip")

    elif format_type == "json":
        out_file = jdir / f"{clean_title}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(job["result"], f, ensure_ascii=False, indent=2)
        return FileResponse(path=str(out_file), filename=f"{clean_title}.json", media_type="application/json")

    else:
        raise HTTPException(status_code=400, detail="Định dạng xuất file không được hỗ trợ.")
