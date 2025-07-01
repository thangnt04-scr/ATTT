import tkinter as tk
from tkinter import messagebox
import socket
import threading
import json
import os
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
from googleapiclient.http import MediaIoBaseDownload
import io

# Cấu hình
PORT = 12345
HOST = 'localhost'  # Mặc định, sẽ được cập nhật từ GUI
status_queue = Queue()
logging.basicConfig(filename='receiver_log.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Hàm tạo và lưu cặp khóa RSA
def generate_and_save_key_pair(prefix):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    with open(f"{prefix}_private_key.pem", "wb") as f:
        f.write(private_pem)
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

# Luồng xử lý của người nhận
def receiver_thread(status_queue, host):
    global HOST
    HOST = host  # Cập nhật HOST từ GUI
    try:
        # Tải hoặc tạo cặp khóa người nhận
        if not os.path.exists("receiver_private_key.pem"):
            private_key, public_key = generate_and_save_key_pair("receiver")
            status_queue.put("Đã tạo cặp khóa mới cho người nhận")
            logging.info("Generated new receiver key pair")
        else:
            private_key, public_key = load_key_pair("receiver")
            status_queue.put("Đã tải cặp khóa hiện có của người nhận")
            logging.info("Loaded existing receiver key pair")
        
        # Bắt đầu lắng nghe
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            server_sock.bind((HOST, PORT))
        except socket.error as e:
            status_queue.put(f"Lỗi: Không thể bind tới cổng {PORT} trên {HOST}. {str(e)}")
            logging.error(f"Bind failed: {str(e)}")
            messagebox.showerror("Lỗi", f"Không thể bind tới cổng {PORT} trên {HOST}.")
            return
        server_sock.listen(1)
        status_queue.put(f"Đang lắng nghe trên {HOST}:{PORT}")
        logging.info(f"Receiver listening on {HOST}:{PORT}")
        
        sock, addr = server_sock.accept()
        status_queue.put(f"Kết nối từ {addr}")
        logging.info(f"Connection from {addr}")
        
        # Handshake
        # request = receive_message(sock)
        # if request is None or request.decode() != "Hello!":
        #     raise ValueError("Yêu cầu handshake không hợp lệ")
        # send_message(sock, "Ready!")
        request_bytes = sock.recv(1024)
        if not request_bytes or request_bytes.decode() != "Hello!":
            raise ValueError(f"Yêu cầu handshake không hợp lệ. Nhận được: {request_bytes!r}")
        sock.sendall("Ready!".encode())
        status_queue.put("Handshake thành công")
        logging.info("Handshake successful")
        
        # Trao đổi khóa công khai
        sender_public_key_pem = receive_message(sock)
        if sender_public_key_pem is None:
            raise ValueError("Không nhận được khóa công khai của người gửi")
        sender_public_key = serialization.load_pem_public_key(sender_public_key_pem)
        with open("receiver_public_key.pem", "rb") as f:
            send_message(sock, f.read())
        status_queue.put("Hoàn tất trao đổi khóa")
        logging.info("Key exchange completed")
        
        # Nhận metadata và session key
        metadata_json = receive_message(sock)
        if metadata_json is None:
            raise ValueError("Không nhận được metadata")
        metadata_json = metadata_json.decode()
        signature = receive_message(sock)
        if signature is None:
            raise ValueError("Không nhận được chữ ký")
        encrypted_session_key = receive_message(sock)
        if encrypted_session_key is None:
            raise ValueError("Không nhận được khóa phiên")
        
        metadata = json.loads(metadata_json)
        sender_public_key.verify(signature, metadata_json.encode(), padding.PKCS1v15(), hashes.SHA512())
        status_queue.put("Đã xác minh metadata")
        logging.info("Metadata verified")
        session_key = private_key.decrypt(encrypted_session_key, padding.PKCS1v15())
        status_queue.put("Đã giải mã khóa session")
        logging.info("Session key decrypted")
        
        # Xử lý nguồn file (Local hoặc Cloud)
        file_data = b""
        if "cloud_id" in metadata and metadata["cloud_id"]:
            temp_file = f"temp_{metadata['filename']}"
            download_from_cloud(metadata["cloud_id"], temp_file)
            with open(temp_file, 'rb') as f:
                file_data = f.read()
            os.remove(temp_file)
        else:
            # Nhận file qua socket
            received_parts = []
            for i in range(3):
                packet = json.loads(receive_message(sock).decode())
                iv = base64.b64decode(packet["iv"])
                encrypted_part = base64.b64decode(packet["cipher"])
                hash_value = bytes.fromhex(packet["hash"])
                signature = base64.b64decode(packet["sig"])
                
                # Tính hash kiểm tra
                hasher = hashes.Hash(hashes.SHA512())
                hasher.update(iv + encrypted_part)
                computed_hash = hasher.finalize()
                if computed_hash != hash_value:
                    send_message(sock, "NACK: Hash mismatch")
                    raise ValueError(f"Hash không khớp cho phần {i+1}")
                
                # Kiểm tra chữ ký
                sender_public_key.verify(signature, encrypted_part, padding.PKCS1v15(), hashes.SHA512())
                
                # Giải mã
                cipher = Cipher(algorithms.TripleDES(session_key), modes.CBC(iv))
                decryptor = cipher.decryptor()
                padded_data = decryptor.update(encrypted_part) + decryptor.finalize()
                unpadder = PKCS7(64).unpadder()
                part = unpadder.update(padded_data) + unpadder.finalize()
                received_parts.append(part)
                status_queue.put(f"Đã nhận và xác minh phần {i+1}/3")
                logging.info(f"Received and verified part {i+1}/3")
                send_message(sock, "ACK")
            file_data = b"".join(received_parts)

        # Lưu file
        output_path = os.path.join("received_contracts", metadata["filename"])
        os.makedirs("received_contracts", exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(file_data)
        status_queue.put(f"Đã lưu file dưới dạng {output_path}")
        logging.info(f"File saved as {output_path}")
    except Exception as e:
        status_queue.put(f"Lỗi khi nhận: {str(e)}")
        logging.error(f"Error in receiver: {str(e)}")
        if 'sock' in locals():
            send_message(sock, f"NACK: {str(e)}")
    finally:
        if 'sock' in locals():
            sock.close()
        if 'server_sock' in locals():
            server_sock.close()

# Thiết lập GUI
def update_status(status_text, root):
    while not status_queue.empty():
        message = status_queue.get()
        status_text.insert(tk.END, f"{message}\n")
        status_text.see(tk.END)
    root.after(100, lambda: update_status(status_text, root))

def receive_contract(status_text, root, host_entry):
    global HOST
    HOST = host_entry.get() or "localhost"
    threading.Thread(target=receiver_thread, args=(status_queue, HOST), daemon=True).start()
    update_status(status_text, root)

def main():
    root = tk.Tk()
    root.title("Người Nhận Hợp Đồng")
    root.geometry("600x400")

    # Nhãn và trường nhập HOST
    host_label = tk.Label(root, text="Nhập HOST (mặc định localhost):", font=("Arial", 10, "bold"), fg="blue")
    host_label.pack(pady=5)
    host_entry = tk.Entry(root)
    host_entry.pack(pady=5)
    host_entry.insert(0, "localhost")

    # Nhãn hướng dẫn
    instruction_label = tk.Label(
        root, text="Hướng dẫn: Khởi động trước khi người gửi kết nối.",
        wraplength=580, font=("Arial", 10, "bold"), fg="blue"
    )
    instruction_label.pack(pady=10)

    # Nút điều khiển
    button_frame = tk.Frame(root)
    button_frame.pack(pady=5)

    receive_button = tk.Button(button_frame, text="Nhận Hợp Đồng", command=lambda: receive_contract(status_text, root, host_entry))
    receive_button.pack(side=tk.LEFT, padx=10)

    quit_button = tk.Button(button_frame, text="Thoát", command=root.quit)
    quit_button.pack(side=tk.LEFT, padx=10)

    # Khu vực hiển thị trạng thái
    status_text = tk.Text(root, height=15, width=70)
    status_text.pack(pady=10)

    # Cập nhật trạng thái định kỳ
    update_status(status_text, root)

    root.mainloop()

if __name__ == "__main__":
    main()