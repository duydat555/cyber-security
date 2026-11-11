# Lab 3.4 — CI/CD Runner thiếu cách ly, rò rỉ secret giữa project (misconfiguration)

**Người phụ trách gốc:** Mỹ Duyên — tái hiện lại bởi Lê Đạt, tái sử dụng GitLab instance của lab 3.3
(`lab33-gitlab`, cổng `127.0.0.1:8929`) theo đúng quyết định của nhóm (không dựng GitLab thứ hai
để tiết kiệm tài nguyên; chạy tuần tự, không song song với 3.3).

> ⚠️ Lab nội bộ, chỉ bind `127.0.0.1`. Secret dùng trong lab là giá trị giả, không phải credential
> thật. PoC chỉ in biến môi trường/đường dẫn job, không khai thác sâu hơn.

## 1. Tóm tắt
Shared Runner dùng **shell executor** chạy trực tiếp trên host (không cô lập filesystem/tiến
trình theo container riêng cho mỗi job). Nếu 2 project dùng chung runner và CI/CD variable
không được đặt `Protected`, một job ở project ít tin cậy hơn có thể:
- Thấy dấu vết file/tiến trình của job project khác chạy trên cùng runner (do dùng chung máy).
- Chạy pipeline với biến CI/CD "protected" nếu job được kích hoạt từ nhánh không được bảo vệ.

## 2. Thiết lập (tái dùng GitLab của 3.3)
```bash
# GitLab đã chạy từ lab 3.3 tại 127.0.0.1:8929, đăng nhập root/<GITLAB_ROOT_PASSWORD của 3.3>
docker compose up -d        # chỉ khởi động gitlab-runner, GitLab dùng lại container lab33-gitlab
```
`docker-compose.yml` của lab này **không tự chạy GitLab riêng** — chỉ chạy `gitlab-runner` và
join vào network của `cicd-lab33` để tới được `lab33-gitlab`.

## 3. Kịch bản thực nghiệm
1. Tạo 2 project: `project-a` (thường) và `project-b` (có CI/CD variable `DEPLOY_SECRET` dạng
   **plain**, KHÔNG tick Protected, KHÔNG tick Masked).
2. Đăng ký 1 shared runner (shell executor) cho cả group/cả hai project.
3. Pipeline `project-b/.gitlab-ci.yml`: job in `echo $DEPLOY_SECRET` (chỉ in ra log CI nội bộ
   của lab, không log ra ngoài) và ghi 1 file tạm vào `/tmp/lab34-job-trace-<id>`.
4. Pipeline `project-a/.gitlab-ci.yml`: job liệt kê `/tmp/lab34-job-trace-*` và `env | grep DEPLOY`
   — mục tiêu là xem job A có thấy dấu vết của job B hay biến của B hay không.
5. Thử tạo Merge Request từ một nhánh không phải default trên `project-b` và kiểm tra biến
   Protected có được cấp cho pipeline của nhánh đó hay không.

## 4. Chứng minh (cấu hình KHÔNG an toàn) — ĐÃ THỰC HIỆN THẬT, xem `evidence/`

**4.1 Rò rỉ chéo project qua filesystem dùng chung (shell executor)**
- Job `job-b` (project-b) ghi: `echo $DEPLOY_SECRET > /tmp/lab34-job-trace-project-b`.
- Job `job-a` (project-a, **project khác**) chạy trên **cùng runner** (shared shell executor):
  ```
  $ cat /tmp/lab34-job-trace-* 2>/dev/null || echo "khong doc duoc"
  LAB34-FAKE-SECRET-VALUE-0xBEEF
  ```
  ⇒ Job của project A đọc được secret của project B qua file dùng chung trên `/tmp`.
- Đồng thời xác nhận: `env | grep -i DEPLOY` ở job A **không** thấy biến — GitLab vẫn scope biến
  CI/CD đúng theo project qua environment; rò rỉ chỉ xảy ra qua **filesystem dùng chung**, không
  qua biến môi trường.
  Ảnh/log: `evidence/01-runner-shell-shared-config.png`,
  `evidence/02-project-b-variable-unprotected.png`,
  `evidence/03-cross-project-trace-leak-shell-executor.png`.

**4.2 Biến Protected chưa bật vẫn được cấp cho nhánh không bảo vệ**
- `DEPLOY_SECRET` ban đầu `protected=false`. Tạo nhánh `feature-x` (không Protected), pipeline
  kiểm tra biến:
  ```
  DEPLOY_SECRET DA duoc cap, gia tri dai 30 ky tu
  ```
  ⇒ Secret bị cấp cho pipeline chạy trên nhánh chưa được tin cậy.
  Ảnh/log: `evidence/04-unprotected-variable-on-unprotected-branch.png`.

## 5. Nguyên nhân gốc
- Shell executor không tạo môi trường thực thi mới cho mỗi job — job trên cùng runner có thể để
  lại hoặc nhìn thấy tài nguyên (file tạm, biến môi trường shell, tiến trình) của job khác nếu
  không dọn dẹp đúng cách.
- CI/CD variable không đặt `Protected` → được cấp cho pipeline chạy trên **mọi** nhánh/tag, kể cả
  nhánh không được bảo vệ (branch của Merge Request từ fork/không tin cậy).

## 6. Vá & chứng minh khắc phục — ĐÃ THỰC HIỆN THẬT

**6.1 Đặt biến `DEPLOY_SECRET` → Protected**
```bash
curl --header "PRIVATE-TOKEN: $TOK" -X PUT ".../projects/3/variables/DEPLOY_SECRET" \
  --data-urlencode "protected=true"
```
Chạy lại **chính xác cùng pipeline trên cùng nhánh `feature-x`** (không đổi gì khác):
```
DEPLOY_SECRET KHONG duoc cap (trong)
```
⇒ Nhánh không bảo vệ không còn nhận được secret.

**6.2 Đổi executor sang `docker` (ephemeral)**: đăng ký thêm 1 runner dùng docker executor,
mỗi job chạy trong 1 container `alpine:latest` riêng, hủy sau khi job kết thúc:
```toml
[[runners]]
  executor = "docker"
  clone_url = "http://lab33-gitlab/"
  [runners.docker]
    image = "alpine:latest"
    network_mode = "cicd-lab33_default"
```
Lặp lại phép thử trace: job B ghi file trong container riêng của nó; job A (project khác, chạy
trên docker executor):
```
$ ls -la /tmp/lab34-job-trace-* 2>/dev/null || echo "khong tim thay file trace nao (moi truong rieng)"
khong tim thay file trace nao (moi truong rieng)
```
⇒ Không còn thấy dấu vết của job B. Ảnh/log: `evidence/04-unprotected-variable-on-unprotected-branch.png`,
`evidence/05-after-docker-executor-isolation.png`.

### Biện pháp phòng chống
- Ưu tiên executor cô lập theo container/VM dùng một lần (Docker ephemeral, Kubernetes executor).
- Luôn đặt Protected + Masked cho mọi biến CI/CD nhạy cảm.
- Không cấp runner có quyền triển khai production cho pipeline chạy trên nhánh MR từ fork không
  tin cậy theo mặc định.
- Tách runner theo mức độ tin cậy của project/nhóm.

### Hệ thống tương tự
Mọi hệ thống CI/CD dùng chung máy thực thi (self-hosted runner, Jenkins agent dùng chung) đều có
rủi ro rò rỉ chéo nếu không cách ly theo job và không kiểm soát phạm vi biến nhạy cảm.

## 7. Dọn dẹp
```bash
docker compose down -v
# GitLab của lab 3.3 dừng riêng tại labs/3.3-gitlab-ssrf (docker compose down -v)
```
