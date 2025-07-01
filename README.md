
# 🚀 Truyền-Tải-Hợp-Đồng-An-Toàn (Secure-Contract-Transfer)

`Secure-Contract-Transfer` là một ứng dụng Python minh họa phương thức truyền tải tệp tin an toàn giữa hai bên qua mạng. Ứng dụng có giao diện người dùng đồ họa (GUI) được xây dựng bằng **Tkinter** và sử dụng chiến lược **mã hóa lai** để đảm bảo tính bảo mật, toàn vẹn và xác thực của dữ liệu. Ứng dụng cung cấp hai chế độ truyền tải: giao tiếp socket trực tiếp và truyền tải qua đám mây bằng Google Drive API.

-----

## ✨ Tính Năng Nổi Bật

  * **🖥️ Giao diện Người dùng Đồ họa (GUI)**: Giao diện đơn giản và trực quan được xây dựng bằng Tkinter cho cả người gửi và người nhận.

  * **🔒 Cơ Chế Mã Hóa Lai**:

      * **Mã Hóa Bất Đối Xứng (RSA)**: Dùng để trao đổi khóa phiên đối xứng một cách an toàn và ký chữ ký số lên siêu dữ liệu. Sử dụng **RSA-2048** để tạo các cặp khóa.
      * **Mã Hóa Đối Xứng (TripleDES)**: Mã hóa nội dung tệp tin để đảm bảo an toàn và hiệu suất, sử dụng một khóa phiên ngẫu nhiên.

  * **✍️ Chữ Ký Số**: Người gửi ký lên siêu dữ liệu và mỗi phần của tệp bằng khóa riêng tư RSA của họ. Người nhận xác minh các chữ ký này bằng khóa công khai của người gửi để đảm bảo tính toàn vẹn và xác thực.

  * **✅ Kiểm Tra Toàn Vẹn Dữ Liệu**: Sử dụng hàm băm **SHA-512** để xác minh các phần của tệp không bị thay đổi trong quá trình truyền.

  * **📡 Hai Chế Độ Truyền Tải**:

    1.  **Truyền Tải Trực Tiếp (Socket)**: Tệp được chia nhỏ, mã hóa và gửi trực tiếp đến người nhận qua socket TCP.
    2.  **Truyền Tải qua Đám Mây (Google Drive)**: Người gửi tải tệp lên Google Drive, chỉ siêu dữ liệu (bao gồm ID tệp trên Drive) được gửi đến người nhận để họ tải xuống.

  * **☁️ Tích Hợp Google Drive API**: Xác thực bằng OAuth 2.0 và sử dụng tệp `token.json` để tải lên và tải xuống tệp một cách liền mạch.

  * **📝 Ghi Log (Logging)**: Ghi lại các sự kiện và lỗi quan trọng vào tệp `sender_log.log` và `receiver_log.log` để gỡ lỗi và theo dõi.

-----

## ⚙️ Cách Hoạt Động

1.  **Tạo Khóa**: Lần đầu chạy, ứng dụng sẽ tạo các cặp khóa RSA. Các lần sau, nó sẽ tải các khóa đã có.
2.  **Bắt Tay & Trao Đổi Khóa**: Người gửi và người nhận kết nối và trao đổi các khóa công khai của họ.
3.  **Gửi Siêu Dữ Liệu & Khóa Phiên**:
      * Người gửi tạo siêu dữ liệu (tên tệp, kích thước, v.v.) và ký bằng khóa riêng tư của mình.
      * Một khóa phiên TripleDES ngẫu nhiên được tạo và mã hóa bằng khóa công khai của người nhận.
      * Siêu dữ liệu đã ký và khóa phiên đã mã hóa được gửi đi.
4.  **Xác Minh Phía Người Nhận**:
      * Người nhận xác minh chữ ký của siêu dữ liệu bằng khóa công khai của người gửi.
      * Giải mã khóa phiên bằng khóa riêng tư của chính mình.
5.  **Truyền Tệp**:
      * **Chế Độ Đám Mây**: Người nhận dùng ID trên Drive trong siêu dữ liệu để tải tệp trực tiếp từ Google Drive.
      * **Chế Độ Trực Tiếp**: Người gửi mã hóa, băm và ký từng phần của tệp rồi gửi đi. Người nhận xác minh, giải mã và gửi lại xác nhận (ACK) cho mỗi phần.
6.  **Ghép Tệp**: Người nhận ghép các phần đã giải mã lại để tái tạo tệp gốc.

-----

## 🛠️ Cài Đặt và Thiết Lập

### Yêu Cầu

  * Python 3.x
  * Một tài khoản Google

### 1\. Tải Mã Nguồn (Clone Repository)

```bash
git clone https://github.com/your-username/Secure-Contract-Transfer.git
cd Secure-Contract-Transfer
```

### 2\. Thiết Lập Môi Trường Ảo (Khuyến khích)

```bash
# Lệnh tạo môi trường ảo
python -m venv venv

# Kích hoạt trên Windows
venv\Scripts\activate

# Kích hoạt trên macOS/Linux
source venv/bin/activate
```

### 3\. Cài Đặt Các Gói Phụ Thuộc

Tạo một tệp `requirements.txt` với nội dung sau:

```
cryptography
google-api-python-client
google-auth-httplib2
google-auth-oauthlib
```

Sau đó, chạy lệnh cài đặt:

```bash
pip install -r requirements.txt
```

### 4\. Cấu Hình Google Drive API

1.  Truy cập [Google Cloud Console](https://console.cloud.google.com/).
2.  Tạo một dự án mới và kích hoạt **Google Drive API**.
3.  Vào mục **Credentials** (Thông tin xác thực) -\> **Create Credentials** -\> **OAuth client ID**.
4.  Cấu hình màn hình chấp thuận, chọn loại ứng dụng là **Desktop app**.
5.  Nhấp **Create** và tải tệp JSON chứa thông tin xác thực về.
6.  Đổi tên tệp đã tải thành `credentials.json` và đặt nó vào thư mục gốc của dự án.

-----

## 📖 Hướng Dẫn Sử Dụng

#### **Bước 1: Xác Thực với Google Drive**

Trước tiên, bạn phải tạo tệp `token.json`. Chạy tập lệnh sau từ terminal:

```bash
python authenticate_google_drive.py
```

Thao tác này sẽ mở trình duyệt để bạn đăng nhập và cấp quyền. Sau khi hoàn tất, tệp `token.json` sẽ được tạo. Bạn chỉ cần làm điều này một lần.

#### **Bước 2: Khởi Động Người Nhận**

Chạy ứng dụng người nhận để bắt đầu lắng nghe kết nối.

```bash
python receiver.py
```

*Bạn có thể chỉ định địa chỉ IP máy chủ trong GUI (mặc định là `localhost`).*
***Lưu ý: Người nhận phải được chạy trước khi người gửi kết nối.***

#### **Bước 3: Khởi Động Người Gửi và Gửi Tệp**

Chạy ứng dụng người gửi trong một terminal khác.

```bash
python sender.py
```

1.  Nhập địa chỉ **IP HOST** của người nhận.
2.  **Để gửi qua Google Drive**: Đánh dấu vào ô "Sử dụng Cloud (Google Drive)".
3.  **Để gửi trực tiếp**: Để trống ô này.
4.  Nhấp vào nút **"Gửi Hợp Đồng"** và chọn tệp bạn muốn chuyển.
5.  Theo dõi tiến trình truyền tệp trong cửa sổ trạng thái.
