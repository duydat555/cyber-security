# Lab 3.5 — Dependency Confusion (npm / Verdaccio)

**Người phụ trách gốc:** Phan Thị Hạ Duy — tái hiện lại bởi Lê Đạt ngày 12/11/2026 bằng registry riêng (không CVE, đây là lỗi cấu hình quản lý nguồn dependency).

> ⚠️ Lab nội bộ, hai registry chỉ bind `127.0.0.1`, `uplinks: {}` nên **không có kết nối ra
> npm thật**. Gói "giả mạo" chỉ `console.log` một chuỗi vô hại, không có payload thật.

## 1. Tóm tắt
Dependency confusion xảy ra khi công cụ quản lý package (ở đây là npm) có thể lấy một package
từ nhiều nguồn registry, và không có cấu hình/khóa phiên bản rõ ràng buộc nó phải lấy từ nguồn
nội bộ đáng tin cậy. Kẻ tấn công publish một package **cùng tên** với package nội bộ lên
registry công khai với version cao hơn; nếu dự án không ghim registry/scope, công cụ cài đặt
có thể chọn nhầm bản của kẻ tấn công.

## 2. Dựng lab
```bash
docker compose up -d
curl -s http://127.0.0.1:4873/-/ping   # registry NỘI BỘ
curl -s http://127.0.0.1:4874/-/ping   # registry "PUBLIC" giả lập (mô phỏng npmjs.org)
```
- `scripts/internal-config/config.yaml`, `scripts/public-config/config.yaml`: cấu hình Verdaccio,
  `uplinks: {}` — không proxy ra Internet thật.
- Hai gói nguồn: `pkg-internal/` (hợp lệ, v1.0.0) và `pkg-attacker/` (mô phỏng kẻ tấn công, v9.9.9),
  **cùng tên** `ten-noi-bo-demo-pkg`.

## 3. Chứng minh (PoC vô hại) — đã thực hiện thật, log tại `evidence/`
Publish hai bản lên hai registry:
```bash
cd pkg-internal  && npm publish --registry http://127.0.0.1:4873/   # ten-noi-bo-demo-pkg@1.0.0
cd pkg-attacker  && npm publish --registry http://127.0.0.1:4874/   # ten-noi-bo-demo-pkg@9.9.9
```
`demo-project/package.json` khai báo dependency không ghim chặt: `"ten-noi-bo-demo-pkg": "*"`.

**`.npmrc` CẤU HÌNH SAI** (không gắn scope riêng, trỏ thẳng registry mặc định về bản "public"):
```
registry=http://127.0.0.1:4874/
```
```bash
cd demo-project && rm -rf node_modules package-lock.json
npm install --foreground-scripts
```
**Kết quả quan sát (thật, 12/11/2026):**
```
> ten-noi-bo-demo-pkg@9.9.9 postinstall
[ATTACKER-SIMULATION] postinstall da chay tu ban 9.9.9 tren registry PUBLIC gia lap ...
```
⇒ npm chọn **nhầm bản 9.9.9** từ registry "public" giả lập, script postinstall của gói giả mạo
**đã thực thi**. Ảnh/log: `evidence/01-npmrc-misconfig-before.txt`,
`evidence/02-npm-install-before-output.png`.

## 4. Nguyên nhân gốc
Dependency không được ghim theo registry/scope cố định; `.npmrc` trỏ default registry về nguồn
không đáng tin cậy; không có lockfile từ trước để chốt nguồn+version hợp lệ. npm ưu tiên bản mới
nhất thỏa điều kiện semver trên registry đang cấu hình, bất kể registry đó có đáng tin hay không.

## 5. Vá & chứng minh khắc phục — đã thực hiện thật
**`.npmrc` ĐÃ VÁ** (chỉ dùng registry nội bộ, không còn fallback "public"):
```
registry=http://127.0.0.1:4873/
```
```bash
rm -rf node_modules package-lock.json
npm install --foreground-scripts    # tạo lockfile MỚI, ghim đúng nguồn nội bộ
```
**Kết quả:** cài đặt bản 1.0.0, script postinstall an toàn chạy:
```
[INTERNAL-PACKAGE] install ten-noi-bo-demo-pkg@1.0.0 tu registry noi bo - AN TOAN
```
`package-lock.json` ghi nhận `resolved: http://127.0.0.1:4873/.../ten-noi-bo-demo-pkg-1.0.0.tgz`
— tức lockfile đã **chốt cứng nguồn + version**. Kiểm chứng lại bằng `npm ci` (dùng đúng lockfile,
không phụ thuộc `.npmrc` tại thời điểm cài):
```bash
rm -rf node_modules && npm ci --foreground-scripts
```
→ vẫn cài đúng bản 1.0.0 từ registry nội bộ. Ảnh/log: `evidence/03-npmrc-fixed-after.txt`,
`evidence/04-npm-ci-after-output.png`, `evidence/05-package-lock-pinned.json`.

| Tiêu chí | Trước vá (misconfig) | Sau vá |
|---|---|---|
| `.npmrc` registry | `http://127.0.0.1:4874/` (public giả lập) | `http://127.0.0.1:4873/` (nội bộ) |
| Version cài | 9.9.9 (của "kẻ tấn công") | 1.0.0 (hợp lệ) |
| Lockfile trước khi cài | Không có | Có, ghim registry nội bộ |
| Script postinstall chạy | `[ATTACKER-SIMULATION]` | `[INTERNAL-PACKAGE] ... AN TOAN` |

### Biện pháp phòng chống
- Ghim registry theo scope cố định (ví dụ `@congty:registry=...`) cho mọi package nội bộ.
- Luôn commit `package-lock.json`/`npm-shrinkwrap.json` và cài bằng `npm ci` trong CI/CD, không
  dùng `npm install` không kiểm soát.
- Đăng ký trước (squat) tên scope/package nội bộ trên registry công khai nếu buộc phải dùng tên
  không scope, để kẻ tấn công không chiếm được tên đó.
- Bật audit log registry nội bộ, giám sát các lần publish version bất thường.

### Hệ thống tương tự
Mọi hệ sinh thái package có registry công khai + registry nội bộ dùng chung namespace (pip/PyPI,
Maven/Nexus, RubyGems, NuGet...) đều có rủi ro tương tự nếu không ghim nguồn rõ ràng.

## 6. Dọn dẹp
```bash
docker compose down -v
```
