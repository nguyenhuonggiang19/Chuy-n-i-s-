<img width="1616" height="558" alt="image" src="https://github.com/user-attachments/assets/91147696-b983-4ae3-a4bd-90e624234ab7" /> 

## 📑 Mục lục
- [📌 Giới thiệu](#-giới-thiệu)
- [🚀 Tính năng chính](#-tính-năng-chính)
- [🧭 Luồng sử dụng](#-luồng-sử-dụng)
- [🛠️ Công nghệ sử dụng](#️-công-nghệ-sử-dụng)
- [📁 Cấu trúc dự án](#-cấu-trúc-dự-án)
- [📸 Giao diện](#-giao-diện)
- [🗺️ Roadmap (GFI)](#️-roadmap-gfi)
- [🚀 Hướng dẫn cài đặt](#-hướng-dẫn-cài-đặt)

---

## 📌 Giới thiệu  
Ứng dụng web cho phép người dùng tải tài liệu (PDF), nhập topic, và tự động tạo bộ flashcard để luyện tập. Hệ thống hỗ trợ làm bài trắc nghiệm A–D, highlight đáp án đúng/sai, tính thời gian, và hiển thị điểm số sau khi hoàn thành. Dự án được xây dựng nhằm tạo ra một công cụ hỗ trợ học tập hiệu quả hơn so với các phương pháp học truyền thống.
---

## 🚀 Tính năng chính  

- Dashboard trực quan: 2 lựa chọn chính Create a flashcard / Create a summary + slider giới thiệu.  
- Upload & xử lý tài liệu: Kiểm tra định dạng/MIME, số lượng file, chống trùng lặp; progress/“GENERATING”.  
- Tạo flashcard tự động: Sinh câu hỏi – 4 đáp án A–D; lưu đáp án đúng trong data-attribute.  
- Làm bài có timer: Bấm chọn là chấm ngay; highlight xanh/đỏ; hiển thị session ID & thời gian.  
- Score page: Tính % đúng, số câu đúng/tổng, thời gian; nút TRY AGAIN để luyện lại.  
- Responsive UI/UX: Tông cam–trắng, menu đáy 5 nút (Home, History, Upload, Meditation, Setting).  
- GFI (mở rộng tương lai): Hỗ trợ DOCX/PPTX/CSV, batch upload, AI/NLP gợi ý câu trả lời, OCR từ ảnh, export CSV/PDF.  

---

## 🧭 Luồng sử dụng  

- Dashboard → chọn Create a flashcard.  
- Upload → chọn file + nhập topic → GENERATE (hiển thị trạng thái xử lý).  
- Flashcard → làm bài: chọn A–D, hệ thống highlight đúng/sai + đếm giờ.  
- Score → xem điểm, % chính xác, thời gian; TRY AGAIN để luyện tiếp.  

---

## 🛠️ Công nghệ sử dụng  

- Frontend: HTML5, CSS3 (TailwindCSS*), JavaScript.  
- Logic quiz: Vanilla JS (event listener, timer, chấm điểm client-side).  
- Xử lý tài liệu (hiện tại): PDF text extraction.  
- GFI: CSV parser, DOCX/PPTX parser, OCR, NLP (gợi ý câu trả lời), export CSV/PDF.  
* TailwindCSS có thể thay bằng CSS thuần tùy repo của bạn.  

---

## 📁 Cấu trúc dự án  
<img width="717" height="757" alt="Screenshot 2025-08-31 212712" src="https://github.com/user-attachments/assets/cf15cccf-e679-4147-9092-c3860f05c4d1" />  

---

## 📸 Giao diện  

- Dashboard với 2 nút chính + slider thương hiệu.  
- Upload có icon kéo–thả; trạng thái “GENERATING”.  
- Flashcard hiển thị câu + 4 đáp án; highlight tức thì; timer góc trên.  
- Score hiển thị điểm lớn trong vòng tròn + nút TRY AGAIN.  

<img width="1257" height="684" alt="image" src="https://github.com/user-attachments/assets/7a468f72-612d-484b-940e-379e490859fc" />
<img width="892" height="522" alt="image" src="https://github.com/user-attachments/assets/cdab645f-9e5b-4183-9857-bcec7239b9d8" />

---

## 🗺️ Roadmap (GFI)  

- Định dạng: PDF  
- AI/NLP: Gợi ý câu trả lời, tạo câu hỏi từ đoạn văn; summarization.  
- OCR: Tạo flashcard từ ảnh chụp/tài liệu scan.  
- Quản lý học tập: History, phân loại theo topic/độ khó/ngày; export CSV/PDF.  

---

## 🚀 Hướng dẫn cài đặt  

OpenAI API Key, thay thế vào đoạn mã sau trong app.py:  
```python
client = OpenAI(api_key=“your-API-Key”)
```
Tạo database theo câu lệnh:
```
CREATE DATABASE flashcardGeneratorDB;
```
Cài đặt các thư viện:
```
pip install -r requirements.txt
```
Chạy chương trình qua Terminal
```
python app1.py
```
