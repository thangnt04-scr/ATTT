# Truyền-Tải-Hợp-Đồng-An-Toàn (Secure-Contract-Transfer)

`Secure-Contract-Transfer` là một ứng dụng Python minh họa phương thức truyền tải tệp tin an toàn giữa hai bên qua mạng. Ứng dụng có giao diện người dùng đồ họa (GUI) được xây dựng bằng Tkinter và sử dụng chiến lược mã hóa lai để đảm bảo tính bảo mật, toàn vẹn và xác thực của dữ liệu được truyền đi. Ứng dụng cung cấp hai chế độ truyền tải: giao tiếp socket trực tiếp và truyền tải qua đám mây bằng Google Drive API.

---

## Tính Năng

* **Giao diện Người dùng Đồ họa (GUI)**: Giao diện đơn giản và trực quan được xây dựng bằng Tkinter cho cả người gửi và người nhận.
* **Cơ Chế Mã Hóa Lai**:
    * **Mã Hóa Bất Đối Xứng (RSA)**: Dùng để trao đổi khóa phiên đối xứng một cách an toàn và ký chữ ký số lên siêu dữ liệu (metadata). RSA-2048 được sử dụng để tạo các cặp khóa công khai/riêng tư.
    * **Mã Hóa Đối Xứng (TripleDES)**: Mã hóa nội dung tệp tin thực tế để đảm bảo an toàn và hiệu suất, sử dụng một khóa phiên được tạo ngẫu nhiên.
* **Chữ Ký Số**: Người gửi ký lên siêu dữ liệu của tệp và mỗi phần tệp đã được mã hóa bằng khóa riêng tư RSA của họ. Người nhận xác minh các chữ ký này bằng khóa công khai của người gửi để đảm bảo tính toàn vẹn và xác thực của dữ liệu.
* **Kiểm Tra Toàn Vẹn Dữ Liệu**: Sử dụng hàm băm SHA-512 để xác minh các phần của tệp không bị hỏng hoặc bị thay đổi trong quá trình truyền.
* **Hai Chế Độ Truyền Tải**:
    1.  **Truyền Tải Socket Trực Tiếp**: Tệp được chia thành ba phần, mã hóa và gửi trực tiếp đến người nhận qua một socket TCP.
    2.  **Truyền Tải Tích Hợp Đám Mây**: Người gửi tải tệp lên một thư mục được chỉ định trên Google Drive, và chỉ có siêu dữ liệu của tệp (bao gồm ID trên Drive) được gửi đến người nhận, sau đó người nhận sẽ tải tệp trực tiếp từ đám mây.
* **Tích Hợp Google Drive API**: Xác thực bằng OAuth 2.0 và sử dụng tệp `token.json` cho các lệnh gọi API tiếp theo để tải lên và tải xuống tệp.
* **Ghi Log**: Ghi lại các sự kiện và lỗi quan trọng vào các tệp `sender_log.log` và `receiver_log.log` để gỡ lỗi và theo dõi.

---

## Cách Hoạt Động

1.  **Tạo Khóa**: Trong lần chạy đầu tiên, cả ứng dụng người gửi và người nhận đều tạo ra các cặp khóa công khai/riêng tư RSA của riêng mình (`sender_private_key.pem`, `receiver_public_key.pem`, v.v.). Trong các lần chạy tiếp theo, chúng sẽ tải các khóa hiện có.
2.  **Bắt Tay & Trao Đổi Khóa**: Người gửi khởi tạo kết nối với người nhận. Họ thực hiện một quá trình "bắt tay" đơn giản và sau đó trao đổi các khóa công khai của mình.
3.  **Truyền Siêu Dữ Liệu và Khóa Phiên**:
    * Người gửi tạo siêu dữ liệu cho tệp (tên tệp, kích thước, dấu thời gian và tùy chọn là ID Google Drive).
    * Siêu dữ liệu này được ký bằng khóa riêng tư của người gửi.
    * Người gửi tạo một khóa phiên TripleDES ngẫu nhiên. Khóa phiên này được mã hóa bằng khóa công khai của người nhận.
    * Siêu dữ liệu đã ký và khóa phiên đã mã hóa được gửi đến người nhận.
4.  **Xác Minh Phía Người Nhận**:
    * Người nhận xác minh chữ ký của siêu dữ liệu bằng khóa công khai của người gửi.
    * Người nhận giải mã khóa phiên bằng khóa riêng tư của chính mình.
5.  **Truyền Tệp**:
    * **Chế Độ Đám Mây**: Nếu siêu dữ liệu chứa ID Google Drive, người nhận sẽ sử dụng thông tin xác thực của mình để tải tệp từ Google Drive.
    * **Chế Độ Trực Tiếp**: Nếu không có ID đám mây, người gửi sẽ chia tệp thành ba phần. Mỗi phần được mã hóa bằng khóa phiên, được băm (SHA-512) và ký. Người nhận nhận từng phần, xác minh hàm băm và chữ ký, giải mã và gửi lại một thông báo xác nhận (ACK).
6.  **Ghép Tệp**: Người nhận ghép các phần đã giải mã lại để tái tạo tệp gốc và lưu vào thư mục `received_contracts`.

---

## Cài Đặt và Thiết Lập

### Yêu Cầu

* Python 3.x
* Một tài khoản Google

### 1. Sao chép (Clone) Repository

```bash
git clone <your-repository-url>
cd Secure-Contract-Transfer
