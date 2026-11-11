"""Build the individual report for section 3.2 (Lê Đạt) — Jenkins CLI arbitrary file read, CVE-2024-23897."""
from pathlib import Path
import hashlib, json
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs'
QA = ROOT / 'evidence/bao-cao-tong-hop'  # reuse already-rendered transcript PNGs (cli-before.png / cli-after.png)
EV32 = ROOT / 'evidence/3.2-jenkins-cli-fileread'

DOC = Document()
sec = DOC.sections[0]
sec.page_width = Cm(21); sec.page_height = Cm(29.7)
sec.top_margin = Cm(2.2); sec.bottom_margin = Cm(2.1); sec.left_margin = Cm(2.8); sec.right_margin = Cm(2.0)
sec.header_distance = Cm(0.9); sec.footer_distance = Cm(1)
for name, size in [('Normal', 13), ('Title', 20), ('Subtitle', 13), ('Heading 1', 16), ('Heading 2', 14), ('Heading 3', 13), ('Caption', 11)]:
    s = DOC.styles[name]; s.font.name = 'Times New Roman'; s.font.size = Pt(size); s.font.color.rgb = RGBColor(0, 0, 0)
    s.paragraph_format.space_after = Pt(6); s.paragraph_format.line_spacing = 1.15
    if name.startswith('Heading'):
        s.font.bold = True; s.paragraph_format.keep_with_next = True; s.paragraph_format.space_before = Pt(12)
DOC.styles['Normal'].paragraph_format.widow_control = True
DOC.core_properties.title = 'Báo cáo mục 3.2 Jenkins CLI và đọc file qua tham số'
DOC.core_properties.subject = 'CVE-2024-23897 Jenkins CLI arbitrary file read'
DOC.core_properties.author = 'Lê Đạt'
DOC.core_properties.keywords = 'Jenkins CLI CVE-2024-23897 args4j CI/CD'

footer = sec.footer.paragraphs[0]; footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
f = OxmlElement('w:fldSimple'); f.set(qn('w:instr'), 'PAGE')
rr = OxmlElement('w:r'); tt = OxmlElement('w:t'); tt.text = '1'; rr.append(tt); f.append(rr); footer._p.append(f)
head = sec.header.paragraphs[0]; head.text = 'MỤC 3.2  JENKINS CLI  CVE-2024-23897'; head.alignment = WD_ALIGN_PARAGRAPH.RIGHT
for r in head.runs: r.font.size = Pt(9)

FIGS = []; TABLES = []

def p(t='', style=None):
    x = DOC.add_paragraph(t, style)
    x.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY if not style else None
    return x

def h(t, l=2):
    return DOC.add_heading(t, l)

def page(t=None, l=2):
    if t:
        x = h(t, l); x.paragraph_format.page_break_before = True
    else:
        DOC.add_page_break()

def paras(t):
    for x in t.strip().split('\n\n'):
        p(x.strip())

def code(t):
    for line in t.strip().splitlines():
        x = p(line); x.alignment = WD_ALIGN_PARAGRAPH.LEFT; x.paragraph_format.space_after = Pt(0)
        for r in x.runs:
            r.font.name = 'Courier New'; r.font.size = Pt(9)

def table(headers, rows, caption=None, widths=None):
    if caption:
        x = p(caption, 'Caption'); x.paragraph_format.keep_with_next = True; TABLES.append(caption)
    t = DOC.add_table(rows=1, cols=len(headers)); t.alignment = WD_TABLE_ALIGNMENT.CENTER; t.autofit = False
    widths = widths or [16.2 / len(headers)] * len(headers)
    for i, v in enumerate(headers): t.rows[0].cells[i].text = str(v)
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row): cells[i].text = str(v)
    for ri, row in enumerate(t.rows):
        pr = row._tr.get_or_add_trPr(); pr.append(OxmlElement('w:cantSplit'))
        if ri == 0: pr.append(OxmlElement('w:tblHeader'))
        for ci, cell in enumerate(row.cells):
            cell.width = Cm(widths[ci]); cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            tc = cell._tc.get_or_add_tcPr(); b = OxmlElement('w:tcBorders')
            for edge in ['top', 'left', 'bottom', 'right']:
                v = OxmlElement('w:' + edge); v.set(qn('w:val'), 'single'); v.set(qn('w:sz'), '4'); v.set(qn('w:color'), 'D9D9D9'); b.append(v)
            tc.append(b)
            m = OxmlElement('w:tcMar')
            for edge in ['top', 'left', 'bottom', 'right']:
                v = OxmlElement('w:' + edge); v.set(qn('w:w'), '90'); v.set(qn('w:type'), 'dxa'); m.append(v)
            tc.append(m)
            if ri == 0 or ri % 2 == 0:
                sh = OxmlElement('w:shd'); sh.set(qn('w:fill'), 'E8EDF2' if ri == 0 else 'F6F7F8'); tc.append(sh)
            for pa in cell.paragraphs:
                pa.paragraph_format.space_after = Pt(3); pa.paragraph_format.line_spacing = 1.05
                for r in pa.runs: r.font.size = Pt(11); r.bold = (ri == 0)
    return t

def fig(path, cap, maxh=8.3):
    im = Image.open(path); w, hh = im.size; wi = 16.2; hi = wi * hh / w
    if hi > maxh: wi *= maxh / hi
    x = p(); x.alignment = WD_ALIGN_PARAGRAPH.CENTER; x.paragraph_format.keep_with_next = True
    x.add_run().add_picture(str(path), width=Cm(wi))
    y = p(cap, 'Caption'); y.alignment = WD_ALIGN_PARAGRAPH.CENTER; FIGS.append(cap)

# ---------------------------------------------------------------- Cover
for text, size in [('ĐẠI HỌC ĐÀ NẴNG', 14), ('TRƯỜNG ĐẠI HỌC CÔNG NGHỆ THÔNG TIN', 14), ('VÀ TRUYỀN THÔNG VIỆT HÀN', 14), ('KHOA KHOA HỌC MÁY TÍNH', 14)]:
    x = p(); x.alignment = WD_ALIGN_PARAGRAPH.CENTER; r = x.add_run(text); r.bold = True; r.font.size = Pt(size)
p(); p()
x = p('BÁO CÁO MỤC 3.2', 'Title'); x.alignment = WD_ALIGN_PARAGRAPH.CENTER
x = p('JENKINS CLI VÀ ĐỌC FILE TÙY Ý QUA THAM SỐ  —  CVE-2024-23897', 'Subtitle'); x.alignment = WD_ALIGN_PARAGRAPH.CENTER
p()
x = p('Thuộc đồ án: Nghiên cứu, khai thác và đề xuất giải pháp phòng chống các lỗ hổng bảo mật trên hệ thống CI/CD')
x.alignment = WD_ALIGN_PARAGRAPH.CENTER
p(); p('Môn học  Bảo mật và An toàn Hệ thống Thông tin 3')
table(['Sinh viên thực hiện', 'Vai trò'], [('Lê Đạt', 'Trưởng nhóm — phụ trách mục 3.2')], widths=[8, 8.2])
p(); x = p('Đà Nẵng tháng 11 năm 2026'); x.alignment = WD_ALIGN_PARAGRAPH.CENTER

# ---------------------------------------------------------------- Tóm tắt
page('TÓM TẮT', 1)
paras('''Báo cáo trình bày việc dựng lab, kiểm chứng và khắc phục lỗ hổng CVE-2024-23897 trên Jenkins CLI — bộ phân tích tham số args4j cho phép mở rộng tham số dạng @đường_dẫn thành nội dung file trên controller. Lab gồm hai Jenkins controller chạy Docker nội bộ, chỉ bind 127.0.0.1: bản 2.441 (bị ảnh hưởng) và bản 2.442 (đã vá), dùng cùng file marker vô hại và /etc/hostname để đối chứng.

Kết quả quan sát: trên Jenkins 2.441, phản hồi lỗi cú pháp của lệnh CLI chứa nguyên văn nội dung file marker và hostname của container — xác nhận parser đã đọc và đưa dữ liệu file vào kênh phản hồi trước khi từ chối lệnh. Trên Jenkins 2.442, cùng phép thử giữ nguyên chuỗi tham số dạng @đường_dẫn, không còn mở rộng thành nội dung file — xác nhận bản vá có hiệu lực trong điều kiện đã thử.

Thực nghiệm giới hạn ở mức proof-of-concept vô hại (file marker tự tạo, /etc/hostname), không trích xuất secret thật, không chạy mã tùy ý. Báo cáo nêu rõ ranh giới giữa kết quả đã quan sát và suy luận về phạm vi ảnh hưởng lý thuyết (ví dụ các file credential nằm trong khả năng đọc của tiến trình Jenkins).''')

# ---------------------------------------------------------------- 1. Định danh
page('1. ĐỊNH DANH LỖ HỔNG', 1)
table(['Thuộc tính', 'Thông tin đối chiếu'], [
    ('Mã lỗ hổng', 'CVE-2024-23897; Jenkins SECURITY-3314'),
    ('CVSS 3.1', '9.8 Critical; vector AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H'),
    ('Thành phần', 'Jenkins built-in CLI; bộ phân tích tham số args4j'),
    ('Phân loại', 'Đọc file tùy ý qua xử lý tham số CLI; liên hệ CWE-22'),
    ('Phiên bản bị ảnh hưởng', 'Weekly đến 2.441; LTS đến 2.426.2'),
    ('Phiên bản vá theo advisory', 'Weekly 2.442; LTS 2.426.3 (hoặc 2.440.1)'),
    ('Image dùng trong lab', 'jenkins/jenkins:2.441-jdk17 (trước vá); jenkins/jenkins:2.442-jdk17 (sau vá)'),
], widths=[5.2, 11], caption='Bảng 1.1 Thông tin lỗ hổng theo Jenkins Security Advisory và NVD [J1][J4]')
paras('''args4j là thư viện phân tích tham số dòng lệnh được Jenkins CLI sử dụng. Thư viện này hỗ trợ cú pháp @đường_dẫn: khi gặp một tham số bắt đầu bằng ký tự @, nó sẽ đọc file tại đường dẫn theo sau và thay tham số đó bằng nội dung file. Trong các phiên bản Jenkins bị ảnh hưởng, tính năng này không được tắt (setExpandAtFiles(false)) và không giới hạn phạm vi file có thể tham chiếu, nên một yêu cầu CLI — kể cả chưa xác thực — có thể khiến controller đọc và đưa nội dung một file bất kỳ vào phản hồi lỗi.

Nguồn chính thức: Jenkins Security Advisory 2024-01-24 (mục SECURITY-3314) và bản ghi NVD CVE-2024-23897 [J1][J4]. Báo cáo không sao chép mã khai thác công khai; mô tả cơ chế dựa trên nội dung advisory và đối chiếu bằng thực nghiệm riêng trên lab cô lập.''')

# ---------------------------------------------------------------- 2. Môi trường lab
page('2. THIẾT LẬP MÔI TRƯỜNG LAB', 1)
paras('''Lab chạy hoàn toàn bằng Docker Compose, cổng duy nhất được publish chỉ bind 127.0.0.1:8080, mạng Docker đặt ở chế độ internal (không có đường ra Internet từ container). Không có bước nào expose lab ra ngoài máy thực nghiệm.''')
table(['Thành phần', 'Giá trị'], [
    ('Image trước vá', 'jenkins/jenkins:2.441-jdk17'),
    ('Image sau vá', 'jenkins/jenkins:2.442-jdk17'),
    ('Cổng publish', '127.0.0.1:8080 → 8080 (chỉ loopback)'),
    ('Mạng Docker', 'internal: true (không route ra Internet)'),
    ('Khởi tạo', 'init.groovy.d — tạo tài khoản lab, tắt quyền đọc ẩn danh, ghi file lab-marker.txt'),
    ('File đối chứng', 'lab-marker.txt (hai dòng tự tạo) và /etc/hostname'),
], widths=[4.5, 11.7], caption='Bảng 2.1 Cấu hình Docker Compose của lab 3.2')
p('Các bước dựng lab:')
code('''# 1) Dựng bản bị ảnh hưởng (Jenkins 2.441)
cd labs/3.2-jenkins-cli-fileread
docker compose up -d
curl -s -o /dev/null -w "%{http_code}\\n" http://127.0.0.1:8080/login   # 200 khi sẵn sàng

# 2) Lấy CLI client từ chính instance đang chạy (đúng hướng dẫn chính thức Jenkins)
curl -s http://127.0.0.1:8080/jnlpJars/jenkins-cli.jar -o scripts/jenkins-cli.jar

# 3) Phép thử đối chứng — dùng file marker tự tạo và /etc/hostname, không đọc secret
java -jar scripts/jenkins-cli.jar -s http://127.0.0.1:8080/ help @/var/jenkins_home/lab-marker.txt
java -jar scripts/jenkins-cli.jar -s http://127.0.0.1:8080/ help @/etc/hostname

# 4) Dừng bản cũ, dựng bản đã vá (Jenkins 2.442) để đối chứng
docker compose down
docker compose -f docker-compose.patched.yml up -d
# lặp lại đúng bước 2-3 trên container mới''')

# ---------------------------------------------------------------- 3. Kiểm chứng trước vá
page('3. KIỂM CHỨNG TRƯỚC KHI VÁ (JENKINS 2.441)', 1)
paras('''File lab-marker.txt do script khởi tạo tạo ra gồm hai dòng: dòng đầu "CICD-LAB32-HARMLESS-MARKER", dòng thứ hai "SECOND-LINE-DEMO". Hostname của controller là "lab32-controller" (đặt trong docker-compose.yml). Hai giá trị này dùng làm dấu hiệu nhận biết: nếu chúng xuất hiện trong phản hồi CLI, đó là bằng chứng server đã đọc nội dung file tương ứng.''')
if (QA / 'cli-before.png').exists():
    fig(QA / 'cli-before.png', 'Hình 3.1 Log đối chứng trên Jenkins 2.441 — tham số marker và hostname bị mở rộng thành nội dung file', maxh=12)
paras('''Phản hồi của lệnh CLI (dù kết thúc bằng lỗi cú pháp "Too many arguments") chứa nguyên văn "CICD-LAB32-HARMLESS-MARKER" khi tham số là @lab-marker.txt, và chứa "lab32-controller" khi tham số là @/etc/hostname. Hai giá trị này không phải do người gọi gửi lên — chúng chỉ có thể xuất hiện nếu Jenkins đã đọc file tương ứng trên máy chủ và chèn nội dung vào vị trí tham số trước khi phân tích lệnh.

Mã thoát khác 0 (lỗi cú pháp "Too many arguments") không được coi là bằng chứng không có rò rỉ: dữ liệu đã lọt vào kênh phản hồi trước khi lệnh bị từ chối. Đây là điểm kỹ thuật quan trọng của CVE-2024-23897 — việc mở rộng @file xảy ra ở giai đoạn phân tích tham số, trước khi Jenkins kiểm tra quyền hoặc tính hợp lệ của lệnh.

Lab không thực hiện đọc master.key, secrets/ hoặc credentials.xml. Về lý thuyết, các file này nằm trong phạm vi mà tiến trình Jenkins (và do đó cơ chế đọc file này) có thể truy cập, nhưng việc đó không được thực hiện trong lab để tránh trích xuất secret thật, dù chỉ là secret của lab.''')
table(['Phép thử', 'Tham số CLI', 'Dữ liệu mong đợi nếu bị đọc', 'Kết quả quan sát trên 2.441'], [
    ('Marker hai dòng', '@/var/jenkins_home/lab-marker.txt', 'CICD-LAB32-HARMLESS-MARKER / SECOND-LINE-DEMO', 'Nội dung marker xuất hiện trong thông báo lỗi'),
    ('Hostname', '@/etc/hostname', 'lab32-controller', 'Chuỗi lab32-controller xuất hiện trong thông báo lỗi'),
], widths=[3.2, 5.5, 4.8, 3.2], caption='Bảng 3.1 Tổng hợp kết quả kiểm chứng trước vá')

# ---------------------------------------------------------------- 4. Nguyên nhân gốc
page('4. NGUYÊN NHÂN GỐC', 1)
paras('''Nguyên nhân gốc là bộ phân tích tham số args4j chấp nhận cú pháp @đường_dẫn và tự động mở rộng nó thành nội dung file trên máy chủ, trong khi Jenkins ở các phiên bản bị ảnh hưởng không gọi API tắt tính năng này (setExpandAtFiles(false)) cho CLI, và không giới hạn phạm vi đường dẫn được phép tham chiếu.

Một điểm quan trọng là việc mở rộng file xảy ra ở giai đoạn phân tích cú pháp tham số — trước khi Jenkins kiểm tra quyền Overall/Read hoặc quyền thực hiện lệnh cụ thể. Vì vậy, kiểm tra quyền ở tầng xử lý lệnh là không đủ để chặn rò rỉ: dữ liệu đã được đọc và có thể lọt ra qua thông báo lỗi trước khi bước kiểm tra quyền được chạy. Đây chính là lý do một yêu cầu CLI chưa xác thực vẫn có thể gây rò rỉ dữ liệu, theo mô tả trong advisory [J1].

Bản vá (Jenkins 2.442 / LTS 2.426.3) vô hiệu hóa việc mở rộng @-file đối với CLI theo mặc định. Khi đó, tham số @đường_dẫn được xử lý như một chuỗi ký tự thông thường, không còn bị thay bằng nội dung file.''')

# ---------------------------------------------------------------- 5. Vá & kiểm chứng sau vá
page('5. ÁP BẢN VÁ VÀ KIỂM CHỨNG SAU VÁ (JENKINS 2.442)', 1)
if (QA / 'cli-after.png').exists():
    fig(QA / 'cli-after.png', 'Hình 5.1 Log đối chứng trên Jenkins 2.442 — tham số @đường_dẫn giữ nguyên dạng chuỗi, không còn bị mở rộng', maxh=12)
paras('''Trên Jenkins 2.442, cùng phép thử với cùng tham số (@lab-marker.txt, @/etc/hostname) trả về thông báo lỗi chứa nguyên văn chuỗi tham số, ví dụ "Too many arguments: @/etc/hostname" — nghĩa là ký tự @ và đường dẫn được giữ lại như một chuỗi bình thường, không bị thay bằng nội dung file. Đây là khác biệt quan sát trực tiếp so với hành vi trên 2.441 và là bằng chứng cho hiệu lực của bản vá trong điều kiện đã kiểm thử.

Một phép thử riêng chỉ gửi tham số marker (không kèm tham số kiểm soát thứ hai) trên bản đã vá trả về yêu cầu xác thực, phù hợp với cấu hình không cấp quyền đọc ẩn danh của lab. Báo cáo ưu tiên trình bày cặp phép thử dùng cùng tham số kiểm soát ở hai phiên bản vì nó cho thấy rõ sự thay đổi hành vi của parser, tránh nhầm hiệu quả của bản vá với một thay đổi về chính sách xác thực riêng biệt.

Hai bản 2.441/2.442 là các bản lịch sử dùng để đối chứng đúng CVE-2024-23897 trong lab; vận hành thực tế cần nâng lên nhánh Jenkins đang được hỗ trợ và theo dõi các advisory tiếp theo, không dừng ở việc lên đúng một bản cũ.''')
table(['Phép thử', 'Jenkins 2.441 (trước vá)', 'Jenkins 2.442 (sau vá)'], [
    ('Marker có tham số kiểm soát', 'Nội dung marker xuất hiện trong phản hồi', 'Giữ nguyên chuỗi @đường_dẫn'),
    ('Hostname có tham số kiểm soát', 'lab32-controller xuất hiện trong phản hồi', 'Giữ nguyên chuỗi @/etc/hostname'),
    ('Secret thật (master.key, credentials.xml)', 'Không thực hiện', 'Không thực hiện'),
    ('Thực thi mã (RCE)', 'Không thực hiện', 'Không thực hiện'),
], widths=[5.2, 5.5, 5.5], caption='Bảng 5.1 Đối chứng tổng hợp trước/sau bản vá')

# ---------------------------------------------------------------- 6. Biện pháp phòng chống
page('6. BIỆN PHÁP PHÒNG CHỐNG', 1)
h('6.1 Biện pháp chính', 3)
paras('''Nâng cấp Jenkins lên bản đã vá (≥ 2.442 nhánh weekly, ≥ 2.426.3 nhánh LTS, hoặc bản LTS hiện hành đang được hỗ trợ) là biện pháp duy nhất loại bỏ hoàn toàn cơ chế gây lỗ hổng, vì nó sửa trực tiếp hành vi của parser trước khi bước kiểm tra quyền được chạy.''')
h('6.2 Biện pháp tạm thời nếu chưa nâng cấp được', 3)
paras('''Vô hiệu hóa Jenkins CLI nếu không sử dụng, theo hướng dẫn chính thức của Jenkins [J3]. Cần lưu ý: chặn riêng cổng TCP 50000 là không đủ, vì cổng này chủ yếu phục vụ kết nối agent (JNLP), còn CLI hiện đại có thể hoạt động qua HTTP hoặc WebSocket trên cùng cổng web (8080/443) — do đó phải kiểm tra và chặn toàn bộ endpoint CLI (/cli) qua reverse proxy hoặc tường lửa ứng dụng, không chỉ chặn một cổng.''')
h('6.3 Biện pháp phòng thủ theo lớp', 3)
paras('''Bật Authorization chặt chẽ (Matrix-based hoặc Role-based), không cấp quyền Overall/Read cho người dùng ẩn danh, giới hạn truy cập mạng tới cổng quản trị Jenkins, giới hạn quyền đọc file của tài khoản hệ điều hành chạy tiến trình Jenkins (hạn chế phạm vi dữ liệu có thể bị đọc nếu lỗ hổng tương tự lặp lại), và theo dõi định kỳ Jenkins Security Advisory để kiểm kê phiên bản.''')
h('6.4 Hệ thống hoặc tình huống tương tự', 3)
paras('''Mọi công cụ cung cấp CLI hoặc API nhận tham số từ xa và dùng thư viện phân tích tham số hỗ trợ cú pháp tham chiếu file (args4j hoặc tương đương) đều có nguy cơ cùng loại nếu không kiểm soát phạm vi đường dẫn và không tắt tính năng mở rộng theo mặc định. Nguyên tắc chung cần áp dụng: không tin dữ liệu đầu vào có thể tham chiếu tài nguyên phía máy chủ, và kiểm tra quyền phải xảy ra trước mọi bước xử lý có khả năng đọc dữ liệu, không phải sau.''')

# ---------------------------------------------------------------- 7. Giới hạn
page('7. GIỚI HẠN THỰC NGHIỆM', 1)
paras('''Lab chỉ kiểm chứng việc đọc được nội dung file văn bản ngắn (marker tự tạo, /etc/hostname) qua thông báo lỗi của lệnh help; không kiểm chứng khả năng đọc file nhị phân, file lớn, hoặc việc trích xuất toàn vẹn một file nhiều dòng qua các lệnh CLI khác. Không thực hiện đọc master.key/credentials.xml hoặc bất kỳ thao tác nào vượt mức proof-of-concept vô hại.

Hai phiên bản 2.441/2.442 là các bản lịch sử dùng riêng cho mục đích đối chứng CVE-2024-23897 trong lab; chúng không phản ánh phiên bản Jenkins nên dùng trong môi trường vận hành thực tế hiện nay.''')

# ---------------------------------------------------------------- 8. Tài liệu tham khảo
page('TÀI LIỆU THAM KHẢO', 1)
refs = [
    ('J1', 'Jenkins Security Advisory 2024-01-24 (SECURITY-3314)', 'https://www.jenkins.io/security/advisory/2024-01-24/'),
    ('J3', 'Jenkins CLI — tài liệu chính thức', 'https://www.jenkins.io/doc/book/managing/cli/'),
    ('J4', 'NVD CVE-2024-23897', 'https://nvd.nist.gov/vuln/detail/CVE-2024-23897'),
]
for key, title, url in refs:
    p(f'[{key}] {title}. {url}')
p('Nguồn trực tuyến được đối chiếu khi hoàn thiện báo cáo ngày 11–12/11/2026.')

# ---------------------------------------------------------------- Appendix: figures/tables index
page('PHỤ LỤC  DANH MỤC HÌNH VÀ BẢNG', 1)
h('Danh mục hình')
for t in FIGS: p(t)
h('Danh mục bảng')
for t in TABLES: p(t)
h('Nguồn bằng chứng gốc')
p('Log gốc (văn bản thuần, chưa qua dàn trang): evidence/3.2-jenkins-cli-fileread/before_patch.txt, after_patch.txt, before_patch_comparison.txt, after_patch_comparison.txt. Ảnh trong báo cáo là bản kết xuất log thành hình, có ghi rõ trong chú thích, không phải ảnh chụp giao diện trình duyệt.')

settings = DOC.settings.element
upd = OxmlElement('w:updateFields'); upd.set(qn('w:val'), 'true'); settings.append(upd)

final = OUT / 'BaoCao_3.2_JenkinsCLI_LeDat.docx'
DOC.save(final)

manifest = {
    'generated_on': '2026-11-12',
    'report': str(final.relative_to(ROOT)),
    'inputs': [
        {'path': str(f.relative_to(ROOT)), 'sha256': hashlib.sha256(f.read_bytes()).hexdigest()}
        for f in [
            EV32 / 'before_patch.txt', EV32 / 'after_patch.txt',
            EV32 / 'before_patch_comparison.txt', EV32 / 'after_patch_comparison.txt',
        ] if f.exists()
    ],
    'figures': len(FIGS),
    'tables': len(TABLES),
}
(OUT / 'BaoCao_3.2_JenkinsCLI_LeDat.manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
print('OK ->', final)
print('Figures:', len(FIGS), 'Tables:', len(TABLES))
