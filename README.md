# AudioScribe AI 🎙️
### Công cụ Chuyển Âm Thanh Thành Text & Tóm Tắt Đa Người Nói Thông Minh

Hỗ trợ gỡ băng lời thoại, tách người nói (Speaker Diarization) và tóm tắt điều hành chuyên sâu cho các file ghi âm dài (> 1 giờ) có nhiều người trao đổi.

---

## 🌟 Tính Năng Nổi Bật

1. **Nhận Diện Đa Người Nói (Multi-Speaker Diarization)**:
   - Tự động nhận diện và phân biệt từng người nói: `Người nói 1`, `Người nói 2`, `Người nói 3`... hoặc theo tên thực tế được xưng hô.
   - Gán màu đại diện riêng cho từng người nói.
   - Cho phép đổi tên người nói nhanh chỉ bằng 1 cú nhấp chuột (ví dụ: đổi `Người nói 1` thành `Anh Nam`), tự động cập nhật đồng bộ trong toàn bộ biên bản.

2. **Tóm Tắt & Điểm Then Chốt (Executive Meeting Summary)**:
   - **Tổng quan cuộc trò chuyện**: Bối cảnh, mục đích cuộc họp.
   - **Các quyết định chính (Decisions Made)**: Những điểm đã được chốt và thống nhất.
   - **Danh sách việc cần làm (Action Items)**: Người phụ trách, nhiệm vụ cụ thể, deadline.
   - **Phân tích theo từng người nói**: Lập trường, quan điểm và ý kiến cốt lõi của từng thành viên.
   - **Diễn biến thảo luận theo chủ đề**: Chi tiết các vấn đề được đưa ra tranh luận.

3. **Hai Chế Độ Xử Lý Linh Hoạt**:
   - **Gemini Cloud AI (Khuyên dùng)**: Sử dụng Gemini File API (Gemini 2.5 Flash / 1.5 Flash), xử lý file > 1 giờ chỉ mất 1-2 phút, độ chính xác tiếng Việt 99%, hiểu tiếng lóng và ngữ cảnh hoàn hảo. Hỗ trợ lấy API Key miễn phí từ Google AI Studio.
   - **Local Whisper (Offline)**: Chạy hoàn toàn trên card đồ họa máy tính (NVIDIA GeForce RTX 3050 CUDA), bảo mật nội bộ 100%, không cần kết nối mạng.

4. **Trình Phát Audio Đồng Bộ (Interactive Audio Player)**:
   - Nhấp vào bất kỳ mốc thời gian `[00:14:25]` nào để phát lại ngay đoạn âm thanh đó.
   - Thanh tiến trình hiển thị người đang phát biểu theo thời gian thực.
   - Tùy chỉnh tốc độ nghe: 1.0x, 1.25x, 1.5x, 2.0x.

5. **Trợ Lý AI Hỏi & Đáp (Meeting Chatbot)**:
   - Chat trực tiếp với nội dung file ghi âm: hỏi về bất kỳ con số, cam kết, deadline hay tranh luận nào trong cuộc họp.

6. **Xuất Báo Cáo Đa Định Dạng**:
   - **Microsoft Word (.docx)**: Bìa chuyên nghiệp, bảng Action Items, màu người nói chuẩn chỉnh.
   - **Markdown (.md)**: Lưu trữ trên Notion, Obsidian, GitHub.
   - **Plain Text (.txt)**: File văn bản nhẹ.
   - **Phụ đề Subtitle (.srt)**: Dùng cho Premiere, CapCut, DaVinci Resolve.
   - **JSON (.json)**: Dữ liệu cấu trúc đầy đủ.

---

## 🚀 Hướng Dẫn Khởi Chạy Nhanh

### Cách 1: Khởi chạy bằng 1 cú nhấp (Khuyên dùng)
Nhấp đúp chuột vào file:
```
start.bat
```
Ứng dụng sẽ tự động khởi tạo môi trường, kiểm tra thư viện và mở trình duyệt tại địa chỉ `http://127.0.0.1:8000`.

### Cách 2: Khởi chạy bằng dòng lệnh
```powershell
# Kích hoạt môi trường ảo
.\.venv\Scripts\activate

# Khởi chạy máy chủ
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Mở trình duyệt truy cập: `http://127.0.0.1:8000`

---

## 🔑 Hướng Dẫn Cài Đặt Gemini API Key (Miễn phí)
1. Truy cập [Google AI Studio](https://aistudio.google.com/app/apikey) và đăng nhập tài khoản Google.
2. Nhấn nút **Create API key** và sao chép mã khóa (bắt đầu bằng `AIza...`).
3. Mở giao diện ứng dụng, nhấp vào nút **Cài đặt API** ở góc trên bên phải, dán key vào và nhấn **Lưu Cài Đặt**. Key sẽ được lưu an toàn trong trình duyệt của bạn.
