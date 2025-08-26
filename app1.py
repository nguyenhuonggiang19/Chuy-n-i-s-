from flask import Flask, render_template, request, redirect, url_for
import pdfplumber
from openai import OpenAI
from openai import APIConnectionError, APIError, RateLimitError
import os
import uuid
import json
import re
import pyodbc
import time
from werkzeug.utils import secure_filename
import hashlib
import shutil

app = Flask(__name__)

# Cấu hình
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILES = 3
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

SQL_SERVER_CONFIG = {
    'server': r'LAPTOP-QLF7564Q\SQLEXPRESS01',
    'database': 'flashcardGeneratorDB',
    'driver': 'ODBC Driver 17 for SQL Server'
}

# Khởi tạo OpenAI client
client = OpenAI(api_key="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")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def check_upload_folder():
    """Kiểm tra thư mục upload có thể ghi được không"""
    upload_path = app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_path):
        try:
            os.makedirs(upload_path)
        except OSError as e:
            print(f"Không thể tạo thư mục upload: {e}")
            return False
    
    # Kiểm tra quyền ghi
    test_file = os.path.join(upload_path, 'test.txt')
    try:
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        return True
    except IOError as e:
        print(f"Không có quyền ghi vào thư mục upload: {e}")
        return False

def connect_to_db():
    try:
        # Tạo chuỗi kết nối với các tham số phù hợp cho macOS
        connection_string = (
            f"DRIVER={{{SQL_SERVER_CONFIG['driver']}}};"
            f"SERVER={SQL_SERVER_CONFIG['server']};"
            f"DATABASE={SQL_SERVER_CONFIG['database']};"
            f"Trusted_Connection=yes;"
        )
        print("Đang thử kết nối đến SQL Server...")
        cnxn = pyodbc.connect(connection_string)
        cursor = cnxn.cursor()
        
        # Kiểm tra và tạo bảng Flashcards
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Flashcards' AND xtype='U')
        BEGIN
            CREATE TABLE Flashcards (
                id INT NOT NULL,
                session_id VARCHAR(15) NOT NULL,  -- Đã sửa từ VARCHAR(MAX) thành VARCHAR(15)
                topic NVARCHAR(255) NOT NULL,
                question NVARCHAR(MAX) NOT NULL,
                option_a NVARCHAR(MAX) NOT NULL,
                option_b NVARCHAR(MAX) NOT NULL,
                option_c NVARCHAR(MAX) NOT NULL,
                option_d NVARCHAR(MAX) NOT NULL,
                correct_answer NVARCHAR(1) NOT NULL,
                content_hash NVARCHAR(64) NULL,
                created_at DATETIME DEFAULT GETDATE(),
                PRIMARY KEY (id, session_id)
            );
            
            PRINT 'Bảng Flashcards đã được tạo thành công';
        END
        """)
        
        # Tạo sequence nếu chưa tồn tại (đã sửa để tương thích với SQL Server)
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.sequences WHERE name = 'FlashcardIdSeq')
        BEGIN
            CREATE SEQUENCE FlashcardIdSeq 
                AS INT
                START WITH 1
                INCREMENT BY 1;
            PRINT 'Sequence FlashcardIdSeq đã được tạo';
        END
        """)
        
        cnxn.commit()
        print("Kết nối và khởi tạo database thành công!")
        return cnxn, cursor
        
    except pyodbc.InterfaceError as e:
        print(f"Lỗi Driver ODBC: {str(e)}")
        print("Hãy chắc chắn bạn đã cài đặt ODBC Driver 17 for SQL Server trên macOS")
    except pyodbc.OperationalError as e:
        print(f"Lỗi kết nối: {str(e)}")
        print("Kiểm tra:")
        print("- SQL Server có đang chạy không")
        print("- Cổng 1433 có mở không")
        print("- Tài khoản sa có được phép đăng nhập từ xa không")
    except Exception as e:
        print(f"Lỗi không xác định khi kết nối database: {str(e)}")
    
    return None, None

def save_flashcards_to_db(flashcards, session_id, topic, content_hash):
    cnxn, cursor = connect_to_db()
    if cnxn and cursor:
        try:
            # Kiểm tra xem content_hash và topic đã tồn tại
            cursor.execute("""
                SELECT COUNT(*) 
                FROM Flashcards 
                WHERE content_hash = ? AND topic = ?
            """, (content_hash, topic))
            exists = cursor.fetchone()[0] > 0

            if exists:
                # Lấy session_id hiện có
                cursor.execute("""
                    SELECT TOP 1 session_id 
                    FROM Flashcards 
                    WHERE content_hash = ? AND topic = ?
                """, (content_hash, topic))
                existing_session_id = cursor.fetchone()[0]
                
                # Truy vấn flashcard cũ
                cursor.execute("""
                    SELECT id, question, option_a, option_b, option_c, option_d, correct_answer 
                    FROM Flashcards 
                    WHERE content_hash = ? AND topic = ?
                    ORDER BY id
                """, (content_hash, topic))
                rows = cursor.fetchall()
                old_flashcards = [
                    {
                        'id': row[0],
                        'question': row[1],
                        'options': [row[2], row[3], row[4], row[5]],
                        'answer': row[6]
                    }
                    for row in rows
                ]
                return {
                    'type': 'existing',
                    'flashcards': old_flashcards,
                    'session_id': existing_session_id
                }

            # Nếu chưa tồn tại, lưu flashcard mới
            new_cards_count = 0
            
            # Lấy ID bắt đầu cho session này
            cursor.execute("""
                SELECT ISNULL(MAX(id), 0) + 1 
                FROM Flashcards 
                WHERE session_id = ?
            """, (session_id,))
            next_id = cursor.fetchone()[0] or 1
            
            for card in flashcards:
                if not all(key in card for key in ['question', 'options', 'answer']):
                    print(f"Flashcard không hợp lệ: {card}")
                    continue
                if len(card['options']) != 4:
                    print(f"Flashcard thiếu đáp án: {card}")
                    continue
                if card['answer'].upper() not in ['A', 'B', 'C', 'D']:
                    print(f"Đáp án không hợp lệ: {card['answer']}")
                    continue

                question = card['question']
                options = card['options']
                answer = card['answer'].upper()

                insert_query = """
                INSERT INTO Flashcards 
                (id, session_id, topic, question, option_a, option_b, option_c, option_d, correct_answer, content_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """
                cursor.execute(insert_query, 
                            next_id,
                            session_id,
                            topic,
                            question,
                            options[0],
                            options[1],
                            options[2],
                            options[3],
                            answer,
                            content_hash)
                next_id += 1
                new_cards_count += 1
                    
            cnxn.commit()
            return {
                'type': 'new',
                'new_cards_count': new_cards_count
            }
        except Exception as e:
            print(f"Lỗi khi lưu flashcard vào SQL Server: {e}")
            cnxn.rollback()
            return {
                'type': 'error',
                'error': str(e),
                'new_cards_count': 0
            }
        finally:
            cursor.close()
            cnxn.close()
    return {
        'type': 'error',
        'error': 'Không thể kết nối database',
        'new_cards_count': 0
    }

def extract_text_from_pdf(filepath):
    text = ""
    try:
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text
    except Exception as e:
        print(f"Lỗi khi trích xuất từ PDF: {e}")
        return None

def decide_question_count(text: str) -> int:
    """Auto decide number of questions based on text length."""
    wc = len(text.split())
    if wc < 500:
        return 3
    elif wc < 1500:
        return 5
    else:
        return 10

def generate_flashcards(text, count):
    truncated_text = text[:15000]
    
    prompt = f"""
    Từ nội dung sau, hãy tạo {count} câu hỏi trắc nghiệm dạng JSON với cấu trúc:
    [
        {{
            "question": "Câu hỏi?",
            "options": ["Đáp án A", "Đáp án B", "Đáp án C", "Đáp án D"],
            "answer": "A"
        }}
    ]
    Mỗi câu hỏi phải có đúng 4 đáp án. Đáp án đúng (answer) phải là một chữ cái: 'A', 'B', 'C', hoặc 'D'. 
    Output chỉ là JSON hợp lệ, không kèm giải thích, không thêm chữ nào ngoài JSON.
    Nội dung:
    {truncated_text}
    """
    
    try:
        for attempt in range(3):
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Bạn là một trợ lý tạo quiz trắc nghiệm."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=2000
                )
                raw_content = response.choices[0].message.content.strip()
                
                # Xử lý response linh hoạt
                if not raw_content.startswith('['):
                    json_match = re.search(r'\[.*\]', raw_content, re.DOTALL)
                    if json_match:
                        raw_content = json_match.group(0)
                
                flashcards = json.loads(raw_content)
                
                # Kiểm tra và sửa dữ liệu
                valid_flashcards = []
                for card in flashcards:
                    if (isinstance(card, dict) and
                        all(key in card for key in ['question', 'options', 'answer']) and
                        isinstance(card['options'], list) and
                        len(card['options']) == 4 and
                        card['answer'].upper() in ['A', 'B', 'C', 'D']):
                        valid_flashcards.append({
                            'question': card['question'],
                            'options': card['options'],
                            'answer': card['answer'].upper()
                        })
                    else:
                        print(f"Flashcard không hợp lệ: {card}")
                
                if not valid_flashcards:
                    raise ValueError("Không có flashcard hợp lệ được tạo")
                
                return valid_flashcards
                
            except (APIError, APIConnectionError, RateLimitError) as e:
                print(f"Lỗi API lần {attempt + 1}: {str(e)}")
                if attempt == 2:
                    raise
                time.sleep(2)
                
    except Exception as e:
        print(f"Lỗi khi tạo flashcard: {str(e)}")
        raise
    
    return None

@app.route('/')
def welcome():
    return render_template('welcome.html')

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'GET':
        return render_template('upload.html')
        
    if request.method == 'POST':
        # Kiểm tra thư mục upload
        if not check_upload_folder():
            return render_template('upload.html', error="Hệ thống không thể lưu file tải lên")
            
        topic = request.form.get('flashcard_topic', '').strip()
        if not topic:
            return render_template('upload.html', error="Vui lòng nhập chủ đề")
            
        if 'file' not in request.files:
            return render_template('upload.html', error="Vui lòng chọn file PDF")
            
        files = request.files.getlist('file')
        if not files or not files[0].filename:
            return render_template('upload.html', error="Vui lòng chọn file PDF hợp lệ")
            
        valid_files = []
        for f in files:
            if f and f.filename and allowed_file(f.filename):
                # Kiểm tra kích thước file
                f.seek(0, os.SEEK_END)
                file_size = f.tell()
                f.seek(0)
                if file_size > MAX_FILE_SIZE:
                    continue
                valid_files.append(f)
        
        if not valid_files:
            return render_template('upload.html', error="Vui lòng chọn file PDF hợp lệ (đuôi .pdf, tối đa 10MB)")
        
        if len(valid_files) > MAX_FILES:
            return render_template('upload.html', error=f"Chỉ được upload tối đa {MAX_FILES} file")
        
        combined_text = ""
        temp_files = []
        try:
            for file in valid_files[:MAX_FILES]:
                try:
                    filename = secure_filename(file.filename)
                    if not filename:
                        raise ValueError("Tên file không hợp lệ")
                        
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    
                    # Lưu file tạm
                    file.save(filepath)
                    temp_files.append(filepath)
                    
                    print(f"Đang xử lý file: {filename}, kích thước: {os.path.getsize(filepath)} bytes")
                    
                    text = extract_text_from_pdf(filepath)
                    if not text or not text.strip():
                        raise ValueError(f"Không thể đọc nội dung từ file {filename}")
                        
                    combined_text += f"\n\n--- {filename} ---\n\n{text}"
                    
                except Exception as e:
                    print(f"Lỗi khi xử lý file: {str(e)}")
                    # Xóa các file tạm đã lưu
                    for f in temp_files:
                        try:
                            os.remove(f)
                        except:
                            pass
                    return render_template('upload.html', error=f"Lỗi khi xử lý file: {str(e)}")
            
            if not combined_text.strip():
                return render_template('upload.html', error="Nội dung trích xuất trống")
            
            print(f"Độ dài text trích xuất: {len(combined_text)} ký tự")
            
            # Tính hash của nội dung
            content_hash = hashlib.md5(combined_text.encode('utf-8')).hexdigest()
            
            try:
                question_count = decide_question_count(combined_text)
                flashcards = generate_flashcards(combined_text, question_count)
                if not flashcards:
                    raise ValueError("Không thể tạo câu hỏi từ nội dung")
            except Exception as e:
                print(f"Lỗi khi tạo flashcard: {str(e)}")
                return render_template('upload.html', error=f"Lỗi khi tạo câu hỏi: {str(e)}")
            
            # Tạo session ID mới
            session_id = f"S{time.strftime('%y%m%d%H%M')}"  # Ví dụ: S2508190915 cho ngày 19/08/2025 09:15
            
            try:
                result = save_flashcards_to_db(flashcards, session_id, topic, content_hash)
                if result['type'] == 'existing':
                    return render_template('result.html', 
                                        questions=result['flashcards'],
                                        topic=topic,
                                        session_id=result['session_id'],
                                        new_cards_count=0)
                elif result['type'] == 'new':
                    if result['new_cards_count'] == 0:
                        return render_template('upload.html', error="Không thể lưu flashcard vào cơ sở dữ liệu")
                    else:
                        return render_template('result.html', 
                                            questions=flashcards,
                                            topic=topic,
                                            session_id=session_id,
                                            new_cards_count=result['new_cards_count'])
                else:  # error
                    return render_template('upload.html', error=f"Lỗi database: {result.get('error', 'Không xác định')}")
            except Exception as e:
                print(f"Lỗi khi lưu database: {str(e)}")
                return render_template('upload.html', error="Lỗi khi lưu kết quả")
                
        finally:
            # Dọn dẹp file tạm
            for f in temp_files:
                try:
                    os.remove(f)
                except:
                    pass

@app.route('/score')
def score():
    session_id = request.args.get('session_id')
    correct_answers = int(request.args.get('correct', 0))
    total_questions = int(request.args.get('total', 1))
    time_spent = int(request.args.get('time', 0))  # Convert to integer
    
    return render_template('score.html', 
                         session_id=session_id,
                         correct_answers=correct_answers,
                         total_questions=total_questions,
                         time=time_spent)  # Pass as integer

@app.route('/result')
def result():
    session_id = request.args.get('session_id')
    # Lấy dữ liệu flashcard từ database dựa trên session_id
    cnxn, cursor = connect_to_db()
    if cnxn and cursor:
        try:
            cursor.execute("""
                SELECT question, option_a, option_b, option_c, option_d, correct_answer 
                FROM Flashcards 
                WHERE session_id = ?
                ORDER BY id
            """, (session_id,))
            rows = cursor.fetchall()
            flashcards = [
                {
                    'question': row[0],
                    'options': [row[1], row[2], row[3], row[4]],
                    'answer': row[5]
                }
                for row in rows
            ]
            
            # Lấy topic
            cursor.execute("""
                SELECT TOP 1 topic FROM Flashcards WHERE session_id = ?
            """, (session_id,))
            topic = cursor.fetchone()[0]
            
            return render_template('result.html', 
                                questions=flashcards,
                                topic=topic,
                                session_id=session_id,
                                new_cards_count=len(flashcards))
        except Exception as e:
            print(f"Lỗi khi truy vấn flashcard: {e}")
            return redirect(url_for('index'))
        finally:
            cursor.close()
            cnxn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Tạo thư mục upload nếu chưa có
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True, port=5000)