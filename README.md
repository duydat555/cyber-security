# Nghiên cứu, khai thác và đề xuất giải pháp phòng chống lỗ hổng bảo mật CI/CD

Đồ án môn **Bảo mật và An toàn Hệ thống Thông tin 3** — nhóm 5 thành viên, Trường Đại học Công
nghệ Thông tin và Truyền thông Việt–Hàn, Khoa Khoa học Máy tính.

**Đề tài:** Nghiên cứu, khai thác và đề xuất giải pháp phòng chống các lỗ hổng bảo mật trên hệ
thống tích hợp và triển khai liên tục (CI/CD).

## Nhóm thực hiện

| Thành viên | Mục phụ trách |
|---|---|
| **Lê Đạt** (Trưởng nhóm) | 3.2 Jenkins CLI (CVE-2024-23897); tổng quan, giải pháp chung và tổng hợp báo cáo; tái hiện độc lập 3.1/3.3/3.4/3.5 |
| Đỗ Thảo Dương | 3.1 Jenkins Script Console |
| Lê Quang Hiển | 3.3 GitLab SSRF |
| Mỹ Duyên | 3.4 CI/CD Runner và bảo vệ secret |
| Phan Thị Hạ Duy | 3.5 Dependency Confusion |

## Nguyên tắc an toàn

Mọi lab chạy **nội bộ qua Docker Compose**, chỉ bind `127.0.0.1` hoặc mạng Docker riêng, **không
expose ra Internet**. Khai thác chỉ dừng ở mức **proof-of-concept vô hại** (đọc file test tự tạo,
`id`/`whoami`, giá trị secret giả), không trích xuất dữ liệu thật. Mỗi lỗ hổng theo quy trình 4
bước: (1) ghi nhận trạng thái ban đầu → (2) chứng minh lỗ hổng → (3) phân tích nguyên nhân gốc →
(4) áp bản vá/cấu hình lại và kiểm chứng lại.

## Cấu trúc thư mục

```
cyber-security/
├── docs/
│   ├── ke-hoach/                       # Kế hoạch gốc của nhóm
│   ├── mau/                            # Template trang bìa/định dạng của trường
│   ├── bao-cao-thanh-vien/             # 4 báo cáo gốc của các thành viên (nguồn)
│   ├── bao-cao-tong-hop/               # Báo cáo nhóm hoàn chỉnh (đầu ra 2) + manifest
│   └── BaoCao_3.2_JenkinsCLI_LeDat.docx  # Báo cáo riêng mục 3.2 (đầu ra 1)
├── labs/
│   ├── 3.1-jenkins-script-console/     # Jenkins Script Console (misconfig)
│   ├── 3.2-jenkins-cli-fileread/       # Jenkins CLI — CVE-2024-23897 (việc chính của trưởng nhóm)
│   ├── 3.3-gitlab-ssrf/                # GitLab Webhook SSRF
│   ├── 3.4-cicd-runner-secret/         # CI/CD Runner thiếu cách ly (tái dùng GitLab của 3.3)
│   └── 3.5-dependency-confusion/       # Dependency Confusion (2 registry Verdaccio)
│       mỗi lab: docker-compose.yml, README.md (các bước tái lập), scripts/, evidence/ (ảnh/log)
├── evidence/
│   ├── 3.2-jenkins-cli-fileread/       # Log thật thu từ lab 3.2
│   └── bao-cao-tong-hop/               # Ảnh/log dùng chèn báo cáo tổng hợp
└── tools/                              # Script dựng .docx, chụp ảnh evidence
```

## Chạy lại một lab

```bash
cd labs/<id>
docker compose up -d
# xem README.md của từng lab để biết các bước kiểm chứng và dọn dẹp
docker compose down -v
```

## Báo cáo

- **Đầu ra 1:** [`docs/BaoCao_3.2_JenkinsCLI_LeDat.docx`](docs/BaoCao_3.2_JenkinsCLI_LeDat.docx)
  — báo cáo riêng phần 3.2 của trưởng nhóm.
- **Đầu ra 2:** [`docs/bao-cao-tong-hop/Bao_Cao_Tong_Hop_CICD_Security.docx`](docs/bao-cao-tong-hop/Bao_Cao_Tong_Hop_CICD_Security.docx)
  — báo cáo hoàn chỉnh cả nhóm, theo khung trang bìa/định dạng của trường.

Cả hai đều được build từ script Python (`tools/build_report_3_2.py`,
`tools/build_group_report.py`) dùng `python-docx`, lấy bằng chứng trực tiếp từ `evidence/` và
`labs/*/evidence/` — không ảnh/log nào trong báo cáo được dựng thủ công.

## Giới hạn đã biết

Xem `evidence/bao-cao-tong-hop/verification.json` để biết danh sách khoảng trống thực nghiệm còn
tồn tại (ví dụ: biện pháp cho GitLab SSRF mới ở mức giảm thiểu mạng, chưa phải bản vá ứng dụng
chính thức; định danh CVE của 3.3 còn cần đối chiếu thêm).
