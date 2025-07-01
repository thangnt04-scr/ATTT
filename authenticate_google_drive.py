from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import os.path
import json

# Định nghĩa scope (quyền truy cập)
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def authenticate_google_drive():
    creds = None
    # Kiểm tra nếu file token.json tồn tại và hợp lệ
    if os.path.exists('token.json'):
        try:
            with open('token.json', 'r') as token_file:
                token_data = token_file.read()
                if token_data:  # Kiểm tra nếu file không trống
                    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
                else:
                    print("File token.json trống. Tạo mới token...")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"File token.json không hợp lệ: {str(e)}. Tạo mới token...")
            creds = None

    # Nếu không có token hoặc token không hợp lệ, yêu cầu đăng nhập
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Kiểm tra file credentials.json
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError("File credentials.json không tồn tại. Vui lòng tạo file credentials.json.")
            # Sử dụng file credentials.json để xác thực
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Lưu token vào file token.json
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

if __name__ == "__main__":
    try:
        authenticate_google_drive()
        print("Đã tạo file token.json thành công! - Thời gian: 01:31 PM +07, 03/06/2025")
    except Exception as e:
        print(f"Lỗi khi xác thực: {str(e)} - Thời gian: 01:31 PM +07, 03/06/2025")