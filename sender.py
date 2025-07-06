import tkinter as tk
from tkinter import filedialog, messagebox
import socket
import threading
import json
import os
import time
from datetime import datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7
from queue import Queue
import logging
import base64
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io

# Cấu hình
PORT = 12345
HOST = 'localhost'  # Mặc định, sẽ được cập nhật từ GUI
FOLDER_ID = '1N51qw2efApqID2qQnszXkd5148RG2rjL'  # ID thư mục Google Drive
status_queue = Queue()
logging.basicConfig(filename='sender_log.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Hàm tạo và lưu cặp khóa RSA
def generate_and_save_key_pair(prefix):
    # Tạo một cặp khóa RSA 2048-bit, đủ an toàn cho hiện tại.
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    # Chuyển đổi khóa riêng tư sang định dạng PEM.
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    # Ghi khóa riêng tư vào file.
    with open(f"{prefix}_private_key.pem", "wb") as f:
        f.write(private_pem)
        # Chuyển đổi và ghi khóa công khai vào file.
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    with open(f"{prefix}_public_key.pem", "wb") as f:
        f.write(public_pem)
    return private_key, public_key

# Hàm tải cặp khóa RSA
def load_key_pair(prefix):
    with open(f"{prefix}_private_key.pem", "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)
    with open(f"{prefix}_public_key.pem", "rb") as f:
        public_key = serialization.load_pem_public_key(f.read())
    return private_key, public_key

# Hàm gửi dữ liệu qua socket
def send_message(sock, message):
    if isinstance(message, str):
        message = message.encode()
    length = len(message)
    sock.sendall(length.to_bytes(4, 'big') + message)

# Hàm nhận dữ liệu từ socket
def receive_message(sock):
    try:
        length_bytes = sock.recv(4)
        if not length_bytes:
            return None
        length = int.from_bytes(length_bytes, 'big')
        data = sock.recv(length)
        while len(data) < length:
            data += sock.recv(length - len(data))
        return data
    except (socket.error, ValueError):
        return None

# Kiểm tra xem người nhận có sẵn sàng không (Hàm này không còn được sử dụng để chặn luồng chính)
def is_receiver_ready():
    for attempt in range(3):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((HOST, PORT))
            sock.close()
            return True
        except (ConnectionRefusedError, socket.timeout):
            time.sleep(2)
    return False

# Hàm upload file lên Google Drive
def upload_to_cloud(file_path):
    creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/drive.file'])
    service = build('drive', 'v3', credentials=creds)
    file_metadata = {
        'name': os.path.basename(file_path),
        'parents': [FOLDER_ID]  # Upload vào thư mục cụ thể
    }
    media = MediaFileUpload(file_path)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    status_queue.put(f"Đã upload file lên Cloud với ID: {file.get('id')}")
    logging.info(f"Uploaded file to Cloud with ID: {file.get('id')}")
    return file.get('id')

# Hàm tải file từ Google Drive
def download_from_cloud(file_id, output_path):
    creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/drive.file'])
    service = build('drive', 'v3', credentials=creds)
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
        status_queue.put(f"Đang tải file từ Cloud: {int(status.progress() * 100)}%")
        logging.info(f"Download progress: {int(status.progress() * 100)}%")
    with open(output_path, 'wb') as f:
        fh.seek(0)
        f.write(fh.read())
    status_queue.put(f"Đã tải file từ Cloud: {output_path}")
    logging.info(f"Downloaded file from Cloud: {output_path}")
    return output_path

# Luồng xử lý của người gửi
def sender_thread(file_path, status_queue, host, use_cloud):
    global HOST
    HOST = host  # Cập nhật HOST từ GUI
    try:
        # Tải hoặc tạo cặp khóa người gửi
        if not os.path.exists("sender_private_key.pem"):
            private_key, public_key = generate_and_save_key_pair("sender")
            status_queue.put("Đã tạo cặp khóa mới cho người gửi")
            logging.info("Generated new sender key pair")
        else:
            private_key, public_key = load_key_pair("sender")
            status_queue.put("Đã tải cặp khóa hiện có của người gửi")
            logging.info("Loaded existing sender key pair")
        
        # # Kiểm tra người nhận -- KHỐI NÀY ĐÃ ĐƯỢC BÌNH LUẬN/VÔ HIỆU HÓA
        # status_queue.put("Đang kiểm tra xem người nhận đã sẵn sàng...")
        # if not is_receiver_ready():
        #     status_queue.put("Lỗi: Người nhận chưa sẵn sàng. Vui lòng khởi động người nhận trước.")
        #     logging.error("Receiver not ready")
        #     messagebox.showerror("Lỗi", "Người nhận chưa sẵn sàng. Vui lòng khởi động người nhận trước.")
        #     return
        status_queue.put("Người gửi sẽ thử kết nối trực tiếp. Đảm bảo người nhận đang chạy.")
        
        # Kết nối tới người nhận
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((HOST, PORT))
        status_queue.put(f"Đã kết nối tới {HOST}:{PORT}")
        logging.info(f"Connected to {HOST}:{PORT}")
        
        # Handshake
        sock.sendall("Hello!".encode())
        response_bytes = sock.recv(1024)
        if not response_bytes or response_bytes.decode() != "Ready!":
            raise ValueError(f"Phản hồi handshake không hợp lệ. Nhận được: {response_bytes!r}")
        status_queue.put("Handshake thành công")
        logging.info("Handshake successful")
        
        # Trao đổi khóa công khai
        with open("sender_public_key.pem", "rb") as f:
            send_message(sock, f.read())
        receiver_public_key_pem = receive_message(sock)
        if receiver_public_key_pem is None:
            raise ValueError("Không nhận được khóa công khai của người nhận")
        receiver_public_key = serialization.load_pem_public_key(receiver_public_key_pem)
        status_queue.put("Hoàn tất trao đổi khóa")
        logging.info("Key exchange completed")
        
        # Chuẩn bị metadata
        filename = os.path.basename(file_path)
        timestamp = datetime.now().isoformat()
        file_size = os.path.getsize(file_path)
        cloud_id = None
        if use_cloud:
            cloud_id = upload_to_cloud(file_path)
        metadata = {"filename": filename, "timestamp": timestamp, "size": file_size, "cloud_id": cloud_id}
        metadata_json = json.dumps(metadata, sort_keys=True)
        signature = private_key.sign(metadata_json.encode(), padding.PKCS1v15(), hashes.SHA512())
        send_message(sock, metadata_json)
        send_message(sock, signature)
        status_queue.put("Đã gửi metadata")
        logging.info("Sent metadata")
        
        # Tạo và mã hóa SessionKey
        session_key = os.urandom(24)
        encrypted_session_key = receiver_public_key.encrypt(session_key, padding.PKCS1v15())
        send_message(sock, encrypted_session_key)
        status_queue.put("Đã gửi khóa phiên")
        logging.info("Sent session key")
        
        # Đọc file (từ Local hoặc Cloud)
        file_data = b""
        if cloud_id:
            temp_file = f"temp_{filename}"
            download_from_cloud(cloud_id, temp_file)
            with open(temp_file, 'rb') as f:
                file_data = f.read()
            os.remove(temp_file)
        else:
            with open(file_path, 'rb') as f:
                file_data = f.read()
        
        # Chia và mã hóa file
        num_expected_parts = 3
        parts = [b''] * num_expected_parts # Khởi tạo với 3 chuỗi byte rỗng

        if file_data: # Chỉ xử lý nếu file_data không rỗng
            total_length = len(file_data)
            
            base_part_size = total_length // num_expected_parts
            remainder = total_length % num_expected_parts
            
            current_pos = 0
            for i in range(num_expected_parts):
                part_size_actual = base_part_size + (1 if i < remainder else 0)
                parts[i] = file_data[current_pos : current_pos + part_size_actual]
                current_pos += part_size_actual
        
        if not use_cloud:  # Chỉ gửi qua socket nếu không dùng Cloud
            for i, part_content in enumerate(parts):
                iv = os.urandom(8)
                cipher = Cipher(algorithms.TripleDES(session_key), modes.CBC(iv))
                encryptor = cipher.encryptor()
                padder = PKCS7(algorithms.TripleDES.block_size).padder() # Sử dụng block_size từ algorithm
                padded_data = padder.update(part_content) + padder.finalize()
                encrypted_part = encryptor.update(padded_data) + encryptor.finalize()
                
                # Tính hash
                hasher = hashes.Hash(hashes.SHA512())
                hasher.update(iv + encrypted_part)
                hash_value = hasher.finalize()
                
                # Ký số
                signature = private_key.sign(encrypted_part, padding.PKCS1v15(), hashes.SHA512())
                
                # Gói tin JSON
                packet = {
                    "iv": base64.b64encode(iv).decode(),
                    "cipher": base64.b64encode(encrypted_part).decode(),
                    "hash": hash_value.hex(),
                    "sig": base64.b64encode(signature).decode()
                }
                send_message(sock, json.dumps(packet))
                status_queue.put(f"Đã gửi phần {i+1}/{len(parts)}")
                logging.info(f"Sent file part {i+1}/{len(parts)}")
                
                # Nhận ACK/NACK
                ack = receive_message(sock)
                if ack is None or ack.decode().startswith("NACK"):
                    raise ValueError(f"Phản hồi NACK: {ack.decode() if ack else 'Kết nối đóng'}")
                status_queue.put(f"Nhận ACK cho phần {i+1}")
                logging.info(f"Received ACK for part {i+1}")
        
        status_queue.put("Hoàn tất truyền file")
        logging.info("File transfer completed")
    except Exception as e:
        status_queue.put(f"Lỗi khi gửi: {str(e)}")
        logging.error(f"Error in sender: {str(e)}")
    finally:
        if 'sock' in locals() and sock.fileno() != -1: # Kiểm tra socket có hợp lệ không trước khi đóng
            sock.close()

# Thiết lập GUI
def update_status(status_text, root):
    while not status_queue.empty():
        message = status_queue.get()
        status_text.insert(tk.END, f"{message}\n")
        status_text.see(tk.END)
    root.after(100, lambda: update_status(status_text, root))

def send_contract(status_text, root, host_entry, use_cloud_var):
    file_path = filedialog.askopenfilename(title="Chọn file hợp đồng")
    if file_path:
        threading.Thread(target=sender_thread, args=(file_path, status_queue, host_entry.get() or "localhost", use_cloud_var.get()), daemon=True).start()
        # update_status(status_text, root) # Gọi update_status định kỳ từ main loop là đủ

def upload_to_cloud_action(status_text, root, file_path):
    if file_path:
        # Chạy upload trong một thread riêng để không làm treo GUI
        threading.Thread(target=upload_to_cloud, args=(file_path,), daemon=True).start()
        # update_status(status_text, root) # Gọi update_status định kỳ từ main loop là đủ

def main():
    root = tk.Tk()
    root.title("Người Gửi Hợp Đồng")
    root.geometry("600x400")

    # Nhãn và trường nhập HOST
    host_label = tk.Label(root, text="Nhập HOST (mặc định localhost):", font=("Arial", 10, "bold"), fg="blue")
    host_label.pack(pady=5)
    host_entry = tk.Entry(root)
    host_entry.pack(pady=5)
    host_entry.insert(0, "localhost")

    # Checkbox cho Cloud
    use_cloud_var = tk.BooleanVar()
    use_cloud_check = tk.Checkbutton(root, text="Sử dụng Cloud (Google Drive)", variable=use_cloud_var)
    use_cloud_check.pack(pady=5)

    # Nhãn hướng dẫn
    instruction_label = tk.Label(
        root, text="Hướng dẫn: Khởi động 'Người Nhận Hợp Đồng' trước, sau đó chọn file.",
        wraplength=580, font=("Arial", 10, "bold"), fg="blue"
    )
    instruction_label.pack(pady=10)

    # Nút điều khiển
    button_frame = tk.Frame(root)
    button_frame.pack(pady=5)

    send_button = tk.Button(button_frame, text="Gửi Hợp Đồng", command=lambda: send_contract(status_text, root, host_entry, use_cloud_var))
    send_button.pack(side=tk.LEFT, padx=5)

    upload_button = tk.Button(button_frame, text="Upload to Cloud", command=lambda: upload_to_cloud_action(status_text, root, filedialog.askopenfilename(title="Chọn file để upload")))
    upload_button.pack(side=tk.LEFT, padx=5)

    quit_button = tk.Button(button_frame, text="Thoát", command=root.quit)
    quit_button.pack(side=tk.LEFT, padx=5)

    # Khu vực hiển thị trạng thái
    status_text = tk.Text(root, height=15, width=70)
    status_text.pack(pady=10)

    # Cập nhật trạng thái định kỳ
    update_status(status_text, root)

    root.mainloop()

if __name__ == "__main__":
    main()