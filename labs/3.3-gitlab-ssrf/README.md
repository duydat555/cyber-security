# Lab 3.3 — GitLab Webhook SSRF (outbound request tới dịch vụ nội bộ)

**Người phụ trách gốc:** Lê Quang Hiển — tái hiện lại bởi Lê Đạt ngày 12/11/2026 trên GitLab CE
10.5.5 (amd64 qua QEMU trên máy Apple Silicon).

> ⚠️ Lab nội bộ, GitLab chỉ bind `127.0.0.1:8929`. Dịch vụ đích là nginx tự dựng, nằm hoàn toàn
> trong mạng Docker nội bộ, không phải hệ thống bên thứ ba thật. Request chỉ là GET/POST vô hại
> tới một marker path tự đặt, không đọc dữ liệu nhạy cảm.

## ⚠️ Lưu ý về định danh CVE
Báo cáo gốc của thành viên gắn lab với **CVE-2018-8801**. Khi đối chiếu lại: NVD ghi phạm vi ảnh
hưởng **trước 10.3**, trong khi hồ sơ gói Debian (bug 893905) ghi nhận bản vá liên quan nằm trong
**10.5.6**. Vì hai nguồn chưa khớp hoàn toàn với phiên bản lab (10.5.5), báo cáo này trình bày kết
quả là **hành vi SSRF quan sát được qua tính năng webhook** trên GitLab 10.5.5, không khẳng định
chắc chắn đây chính xác là CVE-2018-8801. Cần đối chiếu thêm changelog chi tiết của GitLab trước
khi dùng làm kết luận cuối cùng cho báo cáo chính thức.

## 1. Tóm tắt
GitLab cho phép cấu hình webhook để gửi request tới một URL do người dùng (có quyền trong
project) chỉ định. Trên GitLab 10.5.5, không có cơ chế allowlist/denylist nào kiểm soát địa chỉ
đích — webhook có thể trỏ tới bất kỳ host nào mà server GitLab tới được, kể cả các dịch vụ chỉ
tồn tại trong mạng nội bộ. Đây là hành vi SSRF: **server (GitLab) thực hiện request tới đích do
người dùng chọn**, không phải người dùng tự kết nối trực tiếp.

## 2. Dựng lab
```bash
docker compose up -d
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8929/   # chờ GitLab sẵn sàng (302)
```
`docker-compose.yml`: GitLab CE 10.5.5 (`platform: linux/amd64`, chạy qua QEMU) +
`internal-target` (nginx) — nginx **không publish port ra host**, chỉ gọi được từ bên trong
mạng Docker `cicd-lab33_default`, mô phỏng đúng "dịch vụ nội bộ" mà SSRF nhắm tới.

## 3. Chứng minh (PoC vô hại) — đã thực hiện thật, log tại `evidence/`
1. Đăng nhập `root`, lấy Personal Access Token qua `/profile/personal_access_tokens`.
2. Tạo project `ssrf-demo-project` + 1 commit (để webhook test hoạt động được).
3. Tạo webhook: `url = http://internal-target/ssrf-poc-marker-<timestamp>` (đường dẫn có marker
   duy nhất để tránh nhầm với truy cập khác).
4. Baseline: `docker logs lab33-internal-target` → không có dòng access-log nào.
5. Kích hoạt **Test → Push events** trên webhook (UI dùng GET
   `/root/ssrf-demo-project/hooks/1/test?trigger=push_events`).
6. Kiểm tra lại log đích:
   ```
   172.21.0.2 - - [...] "POST /ssrf-poc-marker-1794417417 HTTP/1.1" 200 19 "-" "-"
   ```
   `172.21.0.2` là IP của chính container `lab33-gitlab` trong mạng Docker.

**Kết luận:** GitLab (server) đã tự thực hiện request tới địa chỉ nội bộ do người dùng cấu hình,
không có cảnh báo hay chặn nào. Ảnh/log: `evidence/01-version-and-webhook-config.png`,
`evidence/02-before-baseline-internal-target-log.png`,
`evidence/03-ssrf-poc-internal-target-access-log.png`.

## 4. Nguyên nhân gốc
GitLab 10.5.5 không kiểm tra hoặc giới hạn địa chỉ đích khi thực hiện outbound request từ tính
năng webhook (và các tính năng tương tự như import project, fetch avatar...). Không có tầng
allowlist/denylist ở mức ứng dụng để ngăn request tới địa chỉ nội bộ/loopback/link-local.

## 5. Giảm thiểu & kiểm chứng — đã thực hiện thật
**Đã kiểm tra:** Admin Area → Settings **không có** mục "Outbound requests" trên bản 10.5.5 (tính
năng allow/deny-list cho outbound request chỉ được GitLab bổ sung ở các bản sau). Vì vậy báo cáo
**không thể** trình diễn đúng "bản vá chính thức ở tầng ứng dụng" cho phiên bản lab này.

**Biện pháp giảm thiểu đã kiểm thử: cô lập ở tầng mạng (network segmentation)**
```bash
docker network disconnect cicd-lab33_default lab33-internal-target
```
Kích hoạt lại Test → Push events. Kết quả:
```
GitLab production.log:
WebHook Error => Failed to open TCP connection to internal-target:80
                 (getaddrinfo: Name or service not known)
```
`docker logs lab33-internal-target` sau đó **không có** dòng access-log mới nào. ⇒ Request không
còn tới được đích sau khi cách ly mạng. Ảnh/log: `evidence/04-mitigation-network-segmentation.png`.

**Lưu ý quan trọng:** đây là biện pháp giảm nhẹ **ở tầng mạng**, không phải bản vá ứng dụng cho
đúng CVE. Trong vận hành thực tế, biện pháp đúng đắn là nâng cấp lên bản GitLab có tính năng
allowlist/denylist outbound request và bật kiểm soát đó, kết hợp với network segmentation làm
lớp phòng thủ bổ sung.

### Biện pháp phòng chống (tổng hợp)
- Nâng cấp GitLab lên bản có tính năng "Outbound requests" (Admin Area → Network) và bật chặn
  request tới mạng nội bộ/loopback cho webhook, import, integrations.
- Network segmentation: đặt GitLab trong mạng không có đường trực tiếp tới các dịch vụ nội bộ
  nhạy cảm (metadata cloud, API quản trị nội bộ...).
- Giám sát log outbound request bất thường từ các tính năng tích hợp.

### Hệ thống tương tự
Mọi tính năng server-side fetch theo URL người dùng cung cấp (webhook, import by URL, fetch
avatar/preview, URL-based image proxy...) đều có nguy cơ SSRF nếu không kiểm soát đích kết nối.

## 6. Dọn dẹp
```bash
docker compose down -v
```
(Nếu tái sử dụng GitLab này cho lab 3.4, không chạy lệnh trên cho tới khi hoàn tất 3.4.)
