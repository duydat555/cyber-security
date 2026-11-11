"""Build the Vietnamese group report from member reports and local lab evidence."""
from pathlib import Path
from io import BytesIO
import re, json, hashlib
from docx import Document
from docx.shared import Cm, Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.table import Table
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/bao-cao-tong-hop'; OUT.mkdir(parents=True,exist_ok=True)
QA=ROOT/'evidence/bao-cao-tong-hop'; QA.mkdir(parents=True,exist_ok=True)
DOC=Document()
sec=DOC.sections[0]
sec.page_width=Cm(21);sec.page_height=Cm(29.7)
sec.top_margin=Cm(2.2);sec.bottom_margin=Cm(2.1);sec.left_margin=Cm(2.8);sec.right_margin=Cm(2.0)
sec.header_distance=Cm(0.9);sec.footer_distance=Cm(1)
for name,size in [('Normal',13),('Title',20),('Subtitle',13),('Heading 1',16),('Heading 2',14),('Heading 3',13),('Caption',11)]:
 s=DOC.styles[name];s.font.name='Times New Roman';s.font.size=Pt(size);s.font.color.rgb=RGBColor(0,0,0)
 s.paragraph_format.space_after=Pt(6);s.paragraph_format.line_spacing=1.15
 if name.startswith('Heading'):
  s.font.bold=True;s.paragraph_format.keep_with_next=True;s.paragraph_format.space_before=Pt(12)
DOC.styles['Normal'].paragraph_format.widow_control=True
DOC.core_properties.title='Báo cáo bảo mật hệ thống CI CD'
DOC.core_properties.subject='Nghiên cứu lỗ hổng và giải pháp phòng chống trên hệ thống CI/CD'
DOC.core_properties.author='Nhóm 5 thành viên'
DOC.core_properties.keywords='Jenkins GitLab Runner Dependency Confusion CVE-2024-23897'
footer=sec.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
f=OxmlElement('w:fldSimple');f.set(qn('w:instr'),'PAGE')
rr=OxmlElement('w:r');tt=OxmlElement('w:t');tt.text='1';rr.append(tt);f.append(rr);footer._p.append(f)
head=sec.header.paragraphs[0];head.text='BẢO MẬT VÀ AN TOÀN HỆ THỐNG THÔNG TIN';head.alignment=WD_ALIGN_PARAGRAPH.RIGHT
for r in head.runs:r.font.size=Pt(9)

FIGS=[]; TABLES=[]
def p(t='',style=None):
 x=DOC.add_paragraph(t,style);x.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY if not style else None;return x
def h(t,l=2):return DOC.add_heading(t,l)
def page(t=None,l=2):
 if t:
  x=h(t,l);x.paragraph_format.page_break_before=True
 else:DOC.add_page_break()
def paras(t):
 for x in t.strip().split('\n\n'):p(x.strip())
def table(headers,rows,caption=None,widths=None):
 if caption:
  x=p(caption,'Caption');x.paragraph_format.keep_with_next=True;TABLES.append(caption)
 t=DOC.add_table(rows=1,cols=len(headers));t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=False
 widths=widths or [16.2/len(headers)]*len(headers)
 for i,v in enumerate(headers):t.rows[0].cells[i].text=str(v)
 for row in rows:
  cells=t.add_row().cells
  for i,v in enumerate(row):cells[i].text=str(v)
 for ri,row in enumerate(t.rows):
  pr=row._tr.get_or_add_trPr();pr.append(OxmlElement('w:cantSplit'))
  if ri==0:pr.append(OxmlElement('w:tblHeader'))
  for ci,cell in enumerate(row.cells):
   cell.width=Cm(widths[ci]);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
   tc=cell._tc.get_or_add_tcPr();b=OxmlElement('w:tcBorders')
   for edge in ['top','left','bottom','right']:
    v=OxmlElement('w:'+edge);v.set(qn('w:val'),'single');v.set(qn('w:sz'),'4');v.set(qn('w:color'),'D9D9D9');b.append(v)
   tc.append(b)
   m=OxmlElement('w:tcMar')
   for edge in ['top','left','bottom','right']:
    v=OxmlElement('w:'+edge);v.set(qn('w:w'),'90');v.set(qn('w:type'),'dxa');m.append(v)
   tc.append(m)
   if ri==0 or ri%2==0:
    sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'E8EDF2' if ri==0 else 'F6F7F8');tc.append(sh)
   for pa in cell.paragraphs:
    pa.paragraph_format.space_after=Pt(3);pa.paragraph_format.line_spacing=1.05
    for r in pa.runs:r.font.size=Pt(11);r.bold=(ri==0)
 return t
def code(t):
 for line in t.strip().splitlines():
  x=p(line);x.alignment=WD_ALIGN_PARAGRAPH.LEFT;x.paragraph_format.space_after=Pt(0)
  for r in x.runs:r.font.name='Courier New';r.font.size=Pt(9)
 p()
def fig(path,cap,maxh=8.3):
 im=Image.open(path);w,hh=im.size;wi=16.2;hi=wi*hh/w
 if hi>maxh:wi*=maxh/hi
 x=p();x.alignment=WD_ALIGN_PARAGRAPH.CENTER;x.paragraph_format.keep_with_next=True
 x.add_run().add_picture(str(path),width=Cm(wi))
 y=p(cap,'Caption');y.alignment=WD_ALIGN_PARAGRAPH.CENTER;FIGS.append(cap)
def srcfig(key,i,cap,maxh=8.3):
 assets=QA/'assets';assets.mkdir(exist_ok=True)
 dest=assets/f'{key}-{i}.png'
 if not dest.exists():
  pattern={'31':'*3_1*','33':'*3_3*','34':'*3_4*','35':'*3_5*'}[key]
  source=Document(next((ROOT/'docs/bao-cao-thanh-vien').glob(pattern+'.docx')))
  n=0
  for para in source.paragraphs:
   for b in para._p.xpath('.//a:blip'):
    rid=b.get(qn('r:embed'))
    if not rid:continue
    n+=1
    if n==i:
     im=Image.open(BytesIO(source.part.related_parts[rid].blob));im.save(dest)
 if not dest.exists():raise RuntimeError(f'Missing source image {key}-{i}')
 limit=6.5 if key=='34' and i in (10,11) else 7.1
 fig(dest,cap,min(maxh,limit) if key=='34' else maxh)
def transcript(src,dest,title):
 lines=[title,'Bản trình bày lại log thực nghiệm ngày 11/11/2026','']+src.read_text().splitlines()
 font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Courier New.ttf',20)
 im=Image.new('RGB',(1250,38*len(lines)+40),'white');d=ImageDraw.Draw(im)
 for i,line in enumerate(lines):d.text((24,20+38*i),line,font=font,fill='black')
 im.save(dest)

# Cover: institution follows the academic context, no unrelated student IDs or teacher names.
for text,size in [('ĐẠI HỌC ĐÀ NẴNG',14),('TRƯỜNG ĐẠI HỌC CÔNG NGHỆ THÔNG TIN',14),('VÀ TRUYỀN THÔNG VIỆT HÀN',14),('KHOA KHOA HỌC MÁY TÍNH',14)]:
 x=p();x.alignment=WD_ALIGN_PARAGRAPH.CENTER;r=x.add_run(text);r.bold=True;r.font.size=Pt(size)
p();p()
x=p('BÁO CÁO BẢO MẬT HỆ THỐNG CI CD','Title');x.alignment=WD_ALIGN_PARAGRAPH.CENTER
x=p('Nghiên cứu khai thác và đề xuất giải pháp phòng chống các lỗ hổng bảo mật trên hệ thống tích hợp và triển khai liên tục','Subtitle');x.alignment=WD_ALIGN_PARAGRAPH.CENTER
p();p('Môn học  Bảo mật và An toàn Hệ thống Thông tin 3')
table(['Thành viên','Nội dung phụ trách'],[
 ('Lê Đạt','Trưởng nhóm; Jenkins CLI; tổng quan và tổng hợp'),('Đỗ Thảo Dương','Jenkins Script Console'),('Lê Quang Hiển','GitLab SSRF'),('Mỹ Duyên','CI/CD Runner và bảo vệ secret'),('Phan Thị Hạ Duy','Dependency Confusion')],widths=[5,11.2])
p();x=p('Đà Nẵng tháng 11 năm 2026');x.alignment=WD_ALIGN_PARAGRAPH.CENTER

page('TÓM TẮT BÁO CÁO',1)
paras('''Hệ thống tích hợp và triển khai liên tục là nơi mã nguồn, thông tin xác thực và quyền phát hành phần mềm gặp nhau. Một lỗi trong bộ điều khiển, một job chạy quá nhiều quyền hoặc một nguồn package không đáng tin cậy có thể ảnh hưởng đến toàn bộ quy trình phát hành. Đề tài nghiên cứu năm tình huống tiêu biểu trên Jenkins, GitLab và môi trường thực thi pipeline; mục tiêu là xác định nguyên nhân, kiểm chứng trong lab và đánh giá giải pháp khắc phục.

Kết quả cho thấy mỗi nhóm lỗi cần một lớp kiểm soát riêng. Script Console cần phân quyền quản trị; Jenkins CLI cần bản vá loại bỏ mở rộng tham số thành nội dung file; webhook cần kiểm soát đích kết nối; Runner cần cách ly job và giới hạn phạm vi secret; dependency cần định tuyến registry rõ ràng cùng lockfile đã được rà soát. Không biện pháp đơn lẻ nào bao phủ được cả năm tình huống.

Mục 3.2 bổ sung thực nghiệm đối chứng trên Jenkins 2.441 và 2.442. Với cùng yêu cầu CLI chưa xác thực và cùng file marker vô hại, bản 2.441 đưa nội dung file vào thông báo lỗi; bản 2.442 giữ nguyên chuỗi đường dẫn. Các mục còn lại tổng hợp thực nghiệm của từng thành viên cùng ảnh minh chứng đi kèm. Báo cáo phân biệt kết quả quan sát, tác động có thể xảy ra và các biện pháp chưa được kiểm thử.

Năm thực nghiệm đã được Lê Đạt tự tái hiện độc lập (bổ sung cho bốn báo cáo thành viên): mục 3.3 (GitLab SSRF) nay có cả bằng chứng kích hoạt webhook tới dịch vụ nội bộ lẫn bằng chứng sau khi áp dụng biện pháp giảm thiểu ở tầng mạng (network segmentation, do bản 10.5.5 không có tùy chọn allowlist outbound ở tầng ứng dụng); mối liên hệ chính xác giữa phiên bản lab và CVE-2018-8801 vẫn còn cần đối chiếu thêm. Mục 3.1 (Script Console) có bộ bằng chứng mới xác nhận lại việc chặn người ẩn danh. Mục 3.4 (Runner) có bằng chứng thật về rò rỉ secret chéo project qua shell executor và khắc phục bằng Docker executor + Protected variable. Mục 3.5 (Dependency Confusion) nay có phép thử publish và cài đặt package thật qua hai registry Verdaccio, không chỉ mô phỏng bằng đổi cấu hình. Những giới hạn còn lại (CVE 3.3, một số điểm của 3.1/3.4/3.5 chưa kiểm thử hết) được giữ trong kết luận để bảo đảm tính chính xác của báo cáo.''')
table(['Tình huống','Kết quả chính','Đối chứng sau xử lý'],[
('Script Console','Ẩn danh truy cập được và chạy Groovy','Chuyển về đăng nhập (tái hiện độc lập xác nhận lại)'),('Jenkins CLI','Rò marker và hostname ở 2.441','2.442 giữ nguyên đường dẫn'),('GitLab SSRF','Webhook gửi POST đến dịch vụ nội bộ','Network segmentation chặn được (mức mạng, không phải bản vá ứng dụng)'),('Runner','Đọc marker chéo project; nhánh nhận biến chưa Protected','Docker cách ly; biến Protected bị giới hạn (tái hiện với secret giả thật)'),('Dependency','Nguồn ngoài mô phỏng/thật cung cấp bản 9.9.9','Nguồn nội bộ và npm ci trả bản 1.0.0 (registry Verdaccio thật)')],widths=[3.3,6.3,6.6])

page('MỤC LỤC',1)
p('Mục lục thể hiện các chương và các phần thực nghiệm chính. Số trang được cập nhật khi kết xuất tài liệu.')
toc_entries=[
 'CHƯƠNG 1 TỔNG QUAN ĐỀ TÀI',
 'CHƯƠNG 2 CƠ SỞ LÝ THUYẾT VÀ PHƯƠNG PHÁP',
 'CHƯƠNG 3 PHÂN TÍCH VÀ THỰC NGHIỆM',
 '3.1 Jenkins Script Console và phân quyền quản trị',
 '3.2 Jenkins CLI và đọc file qua tham số',
 '3.3 GitLab SSRF qua webhook',
 '3.4 CI CD Runner và bảo vệ secret',
 '3.5 Dependency Confusion trong chuỗi cung ứng',
 'CHƯƠNG 4 GIẢI PHÁP PHÒNG CHỐNG TỔNG THỂ',
 'KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN',
 'PHÂN CÔNG VÀ KHỐI LƯỢNG CÔNG VIỆC',
 'TÀI LIỆU THAM KHẢO',
 'PHỤ LỤC A CHỈ MỤC BẰNG CHỨNG',
 'PHỤ LỤC B QUY TRÌNH TÁI KIỂM THỬ AN TOÀN',
 'PHỤ LỤC C DANH MỤC HÌNH VÀ BẢNG']
toc_map=json.loads((OUT/'toc_pages.json').read_text()) if (OUT/'toc_pages.json').exists() else {}
for entry in toc_entries:
 x=p(entry+'\t'+str(toc_map.get(entry,'')));x.alignment=WD_ALIGN_PARAGRAPH.LEFT
 x.paragraph_format.tab_stops.add_tab_stop(Cm(15.8),WD_TAB_ALIGNMENT.RIGHT,WD_TAB_LEADER.DOTS)
 for run in x.runs:run.font.size=Pt(12)

page('DANH MỤC TỪ VIẾT TẮT',1)
table(['Thuật ngữ','Diễn giải'],[
('CI / CD','Continuous Integration / Continuous Delivery hoặc Deployment'),('CVE','Mã định danh lỗ hổng bảo mật đã công bố'),('CWE','Phân loại điểm yếu phần mềm'),('CVSS','Hệ thống chấm điểm mức độ nghiêm trọng của lỗ hổng'),('CLI','Giao diện dòng lệnh'),('RCE','Thực thi mã từ xa'),('SSRF','Giả mạo yêu cầu từ phía máy chủ'),('RBAC','Kiểm soát truy cập theo vai trò'),('PBAC','Kiểm soát truy cập dựa trên pipeline'),('MR','Merge Request'),('PoC','Bằng chứng khái niệm'),('Secret','Thông tin xác thực hoặc dữ liệu bí mật dùng trong pipeline'),('Registry','Kho phân phối package'),('Ephemeral','Môi trường tạm thời được hủy sau khi sử dụng')],widths=[4,12.2])
h('Cách đọc kết quả',2)
p('“Đã kiểm chứng” dùng cho hành vi có log hoặc ảnh thực nghiệm trong phạm vi đã mô tả. “Khuyến nghị” dùng cho biện pháp có cơ sở kỹ thuật nhưng chưa được thử đầy đủ trong lab. Điểm CVSS của CVE không được dùng thay cho đánh giá riêng của các lỗi cấu hình không có CVE.')

page('CHƯƠNG 1 TỔNG QUAN ĐỀ TÀI',1)
h('1.1 Bối cảnh và vấn đề nghiên cứu')
paras('''CI/CD giảm công việc thủ công khi tích hợp mã, chạy kiểm thử, đóng gói và triển khai. Tự động hóa cũng khiến một thay đổi trong repository có thể được đưa qua nhiều hệ thống bằng tài khoản dịch vụ. Nếu chuỗi tin cậy này không được kiểm soát, quyền của công cụ tự động hóa trở thành mục tiêu có giá trị cao.

Đối tượng cần bảo vệ không chỉ là giao diện Jenkins hoặc GitLab. Mã nguồn, tệp pipeline, môi trường Runner, registry, artifact và token triển khai đều thuộc phạm vi bảo mật. Một build thành công về chức năng vẫn có thể không an toàn nếu dependency đến từ nguồn sai hoặc job được cấp secret vượt quá nhu cầu.

Đề tài chọn năm tình huống để thể hiện cả lỗi phần mềm lẫn lỗi cấu hình, kiến trúc và nguồn cung ứng. Cách tiếp cận này giúp đánh giá quan hệ giữa cập nhật bản vá và các chính sách vận hành: bản vá giải quyết cơ chế cụ thể, còn phân quyền, phân vùng mạng và quản trị secret giới hạn tác động khi một lớp kiểm soát thất bại.''')
h('1.2 Mục tiêu và phạm vi')
paras('''Mục tiêu thứ nhất là giải thích được điều kiện phát sinh và nguyên nhân gốc của từng tình huống. Mục tiêu thứ hai là thu được bằng chứng dễ đối chiếu bằng file marker, nhật ký hoặc thao tác không phá hoại. Mục tiêu thứ ba là thử lại sau xử lý khi có điều kiện, sau đó xây dựng giải pháp tổng thể có thứ tự ưu tiên.

Lab được giới hạn trên thiết bị cá nhân, máy ảo và Docker của nhóm. Không kiểm thử hệ thống bên thứ ba, không dùng secret thật và không phát tán package mô phỏng lên registry công khai. Các phiên bản cũ chỉ phục vụ tái hiện lịch sử; không được xem là khuyến nghị triển khai mới.''')

page('1.3 Tài sản và ranh giới tin cậy')
table(['Tài sản','Rủi ro nếu mất kiểm soát','Ranh giới cần bảo vệ'],[
('Mã nguồn và pipeline','Sửa logic build, thêm bước lấy dữ liệu','Developer → nhánh được bảo vệ'),('Controller CI/CD','Điều khiển job và cấu hình toàn hệ thống','Người dùng → chức năng quản trị'),('Runner hoặc agent','Đọc file chéo job, duy trì trạng thái độc hại','Project A → Project B'),('Secret triển khai','Mạo danh dịch vụ, truy cập môi trường đích','Job chưa tin cậy → môi trường sản xuất'),('Package và registry','Chạy dependency không được phê duyệt','Registry bên ngoài → pipeline'),('Artifact','Phát hành sản phẩm không đúng mã đã duyệt','Build → deploy')],widths=[3.8,6.0,6.4],caption='Bảng 1.1 Tài sản và ranh giới tin cậy')
paras('''Một ranh giới tin cậy có thể nằm ngay trong cùng máy chủ. Hai project dùng chung tài khoản Runner không đồng nghĩa chúng có cùng chủ sở hữu hoặc cùng mức độ tin cậy. Tương tự, việc webhook được tạo bởi người đã đăng nhập không có nghĩa người đó được phép truy cập mọi địa chỉ mà máy chủ GitLab kết nối được.

Trong đánh giá tác động, cần tách quyền ứng dụng khỏi quyền hệ điều hành. Script Console thực thi trong ngữ cảnh tiến trình Jenkins; mức ảnh hưởng lên máy host phụ thuộc quyền tiến trình, volume và các dịch vụ được gắn vào container. Không thể từ việc đọc một marker suy ra đã chiếm toàn bộ máy host.

Mô hình đe dọa của nhóm gồm người dùng ẩn danh, người có tài khoản quyền thấp, người có quyền sửa pipeline và tác nhân kiểm soát nguồn dependency. Mỗi vai trò được gắn với một điều kiện kiểm thử cụ thể; báo cáo không dùng tài khoản quản trị để chứng minh một kịch bản vốn yêu cầu quyền thấp.''')

page('1.4 Tiêu chí đánh giá và cấu trúc báo cáo')
table(['Tiêu chí','Câu hỏi kiểm tra'],[
('Khả năng tái lập','Có phiên bản, cấu hình và dữ liệu thử rõ ràng không?'),('Bằng chứng','Có gắn yêu cầu đầu vào với phản hồi hoặc log ở đích không?'),('Nguyên nhân','Có chỉ ra chính sách hoặc cơ chế xử lý gây hành vi không?'),('Hiệu quả khắc phục','Cùng phép thử có bị chặn sau xử lý không?'),('Đối chứng chức năng','Tác vụ hợp lệ có còn chạy được không?'),('Phạm vi kết luận','Kết luận có giới hạn trong điều kiện đã thử không?')],widths=[4.2,12],caption='Bảng 1.2 Tiêu chí đánh giá thực nghiệm')
paras('''Đề tài không lấy số lượng lệnh hoặc số ảnh làm thước đo duy nhất. Một bằng chứng tốt cần đủ ngữ cảnh để người đọc biết phiên bản, tài khoản và trạng thái hệ thống. Thông báo lỗi cũng có thể là bằng chứng rò rỉ nếu nó chứa nội dung file ngoài quyền dự kiến của người gọi.

Đối với các lỗi cấu hình, mức độ nguy hiểm được trình bày bằng tài sản bị ảnh hưởng và quyền cần có. Không tự gán điểm CVSS chính thức cho Script Console, Runner hoặc dependency confusion khi chưa định nghĩa một lỗ hổng sản phẩm cụ thể cùng vector chấm điểm.

Chương 2 trình bày nền tảng kỹ thuật và phương pháp. Chương 3 tổng hợp năm thực nghiệm. Chương 4 chuyển các kết quả thành kiến trúc và quy trình phòng chống. Phần kết luận nêu kết quả, giới hạn và khối lượng công việc; phụ lục cung cấp chỉ mục bằng chứng, quy trình tái kiểm thử và tài liệu tham khảo.''')

page('CHƯƠNG 2 CƠ SỞ LÝ THUYẾT VÀ PHƯƠNG PHÁP',1)
h('2.1 Thành phần của một pipeline CI CD')
paras('''Luồng cơ bản bắt đầu từ thay đổi mã nguồn. Máy chủ quản lý phiên bản kiểm tra điều kiện kích hoạt và lập pipeline; controller phân phối job cho Runner hoặc agent. Job lấy mã, tải dependency, chạy kiểm thử, tạo artifact và có thể gửi sản phẩm sang môi trường triển khai.

Jenkins tổ chức tự động hóa bằng job và pipeline, có controller quản lý cấu hình cùng agent thực thi. GitLab kết hợp repository, merge request và pipeline, còn GitLab Runner thực thi job thông qua executor. Dù khác cách tổ chức, cả hai đều phải xử lý mã hoặc cấu hình do người dùng đưa vào.

Registry cung cấp package cho bước build. Lockfile ghi lại phiên bản và thông tin phân giải dependency của một lần cài đặt đã chốt. Những tệp này trở thành đầu vào có ảnh hưởng trực tiếp đến sản phẩm cuối cùng và cần được review cùng mã nguồn.

Secret có thể được cấp qua biến môi trường, file hoặc dịch vụ quản lý bí mật. Khi một secret đã được cấp cho job, việc che nó trên giao diện không làm job mất quyền sử dụng. Vì vậy kiểm soát thời điểm và đối tượng được cấp secret có ý nghĩa lớn hơn việc chỉ che chuỗi trong log.''')
table(['Giai đoạn','Đầu vào cần kiểm soát','Ví dụ kiểm soát'],[
('Commit và review','Người sửa mã, file pipeline','Nhánh bảo vệ; người duyệt độc lập'),('Build và test','Dependency, executor, script','Registry xác định; container riêng'),('Đóng gói','Artifact và nguồn build','Checksum; lưu vết commit và job'),('Deploy','Secret và môi trường đích','Approval; credential ngắn hạn')],widths=[3.8,6,6.4],caption='Bảng 2.1 Kiểm soát theo giai đoạn pipeline')

page('2.2 Phân biệt các nhóm lỗi')
paras('''Lỗi phần mềm xuất hiện khi cách triển khai một thành phần cho phép hành vi ngoài thiết kế bảo mật. Trong mục 3.2, parser của Jenkins mở rộng tham số bắt đầu bằng ký tự @ thành dữ liệu từ file. Bản vá thay đổi cơ chế xử lý đó, nên đối chứng phiên bản giúp đánh giá trực tiếp hiệu quả sửa lỗi.

Lỗi cấu hình xuất hiện khi công cụ có tính năng mạnh nhưng chính sách sử dụng quá rộng. Script Console là chức năng quản trị hợp lệ; vấn đề của lab là người ẩn danh được tiếp cận chức năng này. Cập nhật Jenkins mà vẫn giữ quyền “Anyone can do anything” không thay thế việc sửa chính sách truy cập.

Lỗi kiến trúc xuất hiện khi các đối tượng có mức tin cậy khác nhau chia sẻ tài nguyên không được cách ly. Shell executor dùng chung cho nhiều project là ví dụ: một job đọc được file tạm của job khác dù biến project không tự được chuyển sang.

Rủi ro chuỗi cung ứng xuất hiện khi pipeline chấp nhận đầu vào từ nguồn không được kiểm chứng. Dependency confusion liên quan đến tên package, nguồn registry, quy tắc phân giải phiên bản và lockfile; không thể đánh giá chỉ bằng số phiên bản của ứng dụng CI/CD.''')
table(['Nhóm','Kiểm soát trực tiếp','Kiểm soát bổ sung'],[
('Lỗi parser CLI','Vá thành phần bị ảnh hưởng','Chặn CLI; hạn chế mạng'),('Phân quyền quản trị','Authorization theo vai trò','SSO; rà soát tài khoản'),('SSRF','Kiểm soát URL và địa chỉ đích','Egress firewall; nhật ký đích'),('Thiếu cách ly job','Executor và tài nguyên riêng','Runner theo mức tin cậy'),('Nguồn dependency sai','Scope và registry rõ ràng','Lockfile; review thay đổi')],widths=[4.2,6,6],caption='Bảng 2.2 Nhóm lỗi và lớp kiểm soát')

page('2.3 Quy trình thực nghiệm và quản lý bằng chứng')
paras('''Quy trình gồm bốn bước: ghi nhận trạng thái ban đầu, thực hiện phép thử vô hại, phân tích nguyên nhân và áp dụng biện pháp rồi chạy lại. Mỗi lần thử cần lưu tài khoản sử dụng, phiên bản, cấu hình liên quan và thời điểm. Dữ liệu thử phải đủ đặc trưng để nhận ra trong phản hồi nhưng không có giá trị bí mật.

Đối với rò file, nhóm dùng marker do mình tạo và hostname. Đối với SSRF, đích là dịch vụ nội bộ giả lập trong mạng Docker; log tại đích cho phép kiểm tra yêu cầu có thực sự xuất phát từ GitLab hay không. Đối với Runner, file marker và trạng thái set hoặc NOT set của biến giúp phân biệt đường file với đường cấp biến.

Trong báo cáo tổng hợp, ảnh của các thành viên là bằng chứng của môi trường mà thành viên đã mô tả, không phải khẳng định các lab đó vừa được chạy lại trên cùng một máy. Riêng mục 3.2 có log mới thu trực tiếp trong lần hoàn thiện này. Việc tách nguồn bằng chứng giúp người đọc hiểu giới hạn tái lập.

Ảnh được chọn theo nội dung chứng minh; ảnh cài đặt lặp lại hoặc chứa mật khẩu khởi tạo không được đưa vào bản tổng hợp. Bản trình bày log của mục 3.2 được ghi rõ là log kết xuất thành ảnh, không phải ảnh chụp giao diện. Các file log gốc được giữ trong thư mục evidence để đối chiếu.''')
table(['Loại bằng chứng','Điều chứng minh','Điều chưa đủ chứng minh'],[
('Trang phiên bản','Build đang quan sát','Mọi cấu hình đều bị khai thác được'),('Marker trong phản hồi','Dữ liệu thử bị đọc hoặc chuyển qua ranh giới','Đã lấy secret hoặc chiếm host'),('Log HTTP ở đích','Có yêu cầu từ dịch vụ nguồn','Đọc được mọi dịch vụ nội bộ'),('Job Passed','Job chạy xong theo điều kiện định nghĩa','Pipeline an toàn về bảo mật'),('Thông báo từ chối','Phép thử cụ thể bị chặn','Mọi đường khai thác đều đã đóng')],widths=[3.9,6.0,6.3],caption='Bảng 2.3 Diễn giải bằng chứng đúng phạm vi')

page('CHƯƠNG 3 PHÂN TÍCH VÀ THỰC NGHIỆM',1)
h('3.1 Jenkins Script Console và phân quyền quản trị')
p('Người phụ trách: Đỗ Thảo Dương. Bằng chứng gốc: báo cáo thực nghiệm mục 3.1 của thành viên.')
h('3.1.1 Khái niệm và điều kiện phát sinh',3)
paras('''Script Console là giao diện chạy Groovy để quản trị Jenkins. Trong một cấu hình đúng, quyền sử dụng chức năng này chỉ được cấp cho người quản trị đáng tin cậy. Trong lab, Authorization được đổi thành “Anyone can do anything”, làm cho người chưa đăng nhập cũng truy cập được endpoint /script.

Đây là lỗi cấu hình quyền truy cập, không có một CVE duy nhất áp dụng cho mọi Jenkins có Script Console. Báo cáo không gán điểm CVSS chính thức; tác động được đánh giá theo quyền của tiến trình Jenkins và tài nguyên mà tiến trình đó có thể sử dụng. Tài liệu chức năng của Jenkins là cơ sở để xác định tính nhạy cảm của quyền này [J2].

Mục tiêu thực nghiệm là kiểm tra quyền truy cập ẩn danh, quan sát kết quả một thao tác Groovy vô hại, sau đó yêu cầu xác thực trở lại và kiểm tra bằng cửa sổ ẩn danh. Kết quả không cần bao gồm việc đọc credential hoặc chạy lệnh phá hoại để chứng minh chính sách truy cập không an toàn.''')
table(['Thành phần','Cấu hình thực nghiệm'],[('Host','Windows 11 và Docker Desktop'),('Image','jenkins/jenkins:lts-jdk21; tag thay đổi theo thời gian'),('Cổng lab','127.0.0.1:18080 → 8080'),('Kiểm tra','Trình duyệt ẩn danh tại /script'),('Thao tác','Groovy liệt kê plugin Jenkins')],widths=[4.2,12],caption='Bảng 3.1.1 Môi trường Script Console')

page('3.1.2 Thiết lập và cấu hình sai',3)
paras('''Thành viên khởi tạo Jenkins bằng Docker Compose, hoàn tất trình hướng dẫn và tạo tài khoản quản trị. Cổng host đổi sang 18080 do cổng 8080 trên máy thực nghiệm không bind được. Việc bind loopback giữ giao diện lab trong phạm vi truy cập cục bộ.

Trạng thái ban đầu sử dụng “Logged-in users can do anything”. Sau đó người quản trị đổi Authorization thành “Anyone can do anything” để tạo điều kiện thử có chủ đích. Cần phân biệt đây là một thay đổi cấu hình trong lab với nhận định rằng Jenkins mặc định luôn mở Script Console.''')
srcfig('31',7,'Hình 3.1.1 Authorization yêu cầu đăng nhập trước khi tạo cấu hình sai')
srcfig('31',8,'Hình 3.1.2 Authorization được đổi thành Anyone can do anything')

page('3.1.3 Kiểm chứng truy cập và thực thi Groovy',3)
paras('''Một cửa sổ ẩn danh được dùng để tránh kế thừa phiên đăng nhập quản trị. Khi truy cập /script, giao diện Script Console vẫn hiển thị. Đó là bằng chứng trực tiếp rằng lớp kiểm soát truy cập cho người ẩn danh đã không hoạt động theo mục tiêu bảo mật.

Thao tác Groovy liệt kê plugin trả kết quả trong giao diện. Quan sát này chứng minh chức năng thực thi Groovy có thể được sử dụng trong trạng thái cấu hình sai. Không diễn giải ảnh danh sách plugin thành bằng chứng đã đọc bí mật, thực thi lệnh hệ điều hành hoặc chiếm quyền host.''')
srcfig('31',9,'Hình 3.1.3 Script Console hiển thị trong cửa sổ ẩn danh')
srcfig('31',11,'Hình 3.1.4 Kết quả Groovy liệt kê plugin trong lab')

page('3.1.4 Khắc phục và đối chứng',3)
paras('''Thành viên khôi phục Authorization về “Logged-in users can do anything”, lưu cấu hình rồi mở lại /script bằng cửa sổ ẩn danh. Jenkins chuyển người dùng tới trang đăng nhập. Cặp ảnh trước/sau chứng minh người chưa xác thực không còn tiếp cận trực tiếp chức năng này trong điều kiện đã thử.

Chính sách trên vẫn cấp quyền rộng cho mọi người đã đăng nhập. Khắc phục đầy đủ trên môi trường dùng nhiều tài khoản cần Matrix-based hoặc Role-based Authorization, chỉ cấp quyền quản trị cho nhóm được phê duyệt và chạy đối chứng bằng tài khoản thường. Bước này là khuyến nghị, chưa có bằng chứng kiểm thử trong lab thành viên.''')
srcfig('31',13,'Hình 3.1.5 Khôi phục chính sách yêu cầu đăng nhập')
srcfig('31',14,'Hình 3.1.6 Truy cập ẩn danh sau xử lý chuyển tới trang đăng nhập')

page('3.1.5 Nguyên nhân tác động và giới hạn',3)
table(['Tiêu chí','Trước xử lý','Sau xử lý đã thử'],[
('Authorization','Anyone can do anything','Logged-in users can do anything'),('Người ẩn danh vào /script','Được hiển thị giao diện','Chuyển tới đăng nhập'),('Thao tác Groovy ẩn danh','Có kết quả','Bị chặn bởi yêu cầu xác thực'),('Tài khoản thường','Chưa đánh giá riêng','Chưa có kiểm thử quyền tối thiểu')],widths=[4.5,5.8,5.9],caption='Bảng 3.1.2 Đối chứng Script Console')
paras('''Nguyên nhân trực tiếp là Authorization trao quyền vượt quá nhu cầu. Tác động có thể bao gồm thay đổi job, pipeline hoặc dữ liệu mà Jenkins có quyền quản trị. Nếu tiến trình được gắn credential hoặc volume nhạy cảm, phạm vi ảnh hưởng có thể mở rộng; đây là phân tích nguy cơ, không phải những hành vi đã thực hiện trong lab.

Ngoài phân quyền, cần hạn chế mạng quản trị, dùng HTTPS và cơ chế xác thực tập trung khi phù hợp, rà soát tài khoản định kỳ và lưu nhật ký thay đổi chính sách. Reverse proxy hoặc SSO chỉ hỗ trợ xác thực, không thay thế chính sách cấp quyền bên trong Jenkins.

Tình huống tương tự có thể xảy ra với console debug, trang quản trị hoặc endpoint chạy script trên các công cụ tự động hóa khác. Điều kiện chung là chức năng có ảnh hưởng lớn được cấp cho đối tượng chưa đủ tin cậy.

Kết luận của mục này là lỗi phân quyền đã được minh họa bằng truy cập ẩn danh và thực thi Groovy; yêu cầu đăng nhập đã chặn được đối tượng đó. Chưa đủ cơ sở kết luận đã triển khai đặc quyền tối thiểu cho người dùng đã xác thực. Tag image lts-jdk21 cũng cần thay bằng phiên bản hoặc digest trong hồ sơ tái lập.''')

page('3.1.6 Tái hiện độc lập bởi Lê Đạt',3)
L31=ROOT/'labs/3.1-jenkins-script-console/evidence'
paras('''Ngoài báo cáo gốc của Đỗ Thảo Dương, lab này đã được Lê Đạt tự dựng lại độc lập ngày 12/11/2026 bằng Docker Compose riêng (jenkins/jenkins:lts-jdk17, bind 127.0.0.1, bỏ qua setup wizard). Mục tiêu là có một bộ bằng chứng mới, không phụ thuộc vào ảnh của báo cáo thành viên, cùng xác nhận lại kết luận của mục 3.1.

Kiểm tra API /api/json xác nhận ngay sau khi khởi động, Jenkins ở trạng thái useSecurity:false — không có Realm hay Authorization nào được bật, không riêng gì Script Console. Yêu cầu GET /script của người dùng ẩn danh trả về HTTP 200 kèm giao diện Script Console đầy đủ.''')
fig(L31/'01-script-console-anon-before.png','Hình 3.1.7 (tái hiện) Script Console hiển thị đầy đủ cho người dùng chưa đăng nhập',maxh=9)
paras('''PoC thực thi: gửi Groovy "id".execute().text và "hostname".execute().text qua endpoint /scriptText (kèm CSRF token và cookie phiên ẩn danh hợp lệ, không cần tài khoản). Phản hồi trả về nguyên văn uid=1000(jenkins) gid=1000(jenkins) groups=1000(jenkins) và hostname của container — xác nhận thực thi mã ở quyền tiến trình Jenkins khi chưa xác thực.''')
fig(L31/'02-groovy-exec-anon-output.png','Hình 3.1.8 (tái hiện) Kết quả thực thi Groovy ẩn danh: uid/gid và hostname container',maxh=7)
paras('''Khắc phục: bật HudsonPrivateSecurityRealm và FullControlOnceLoggedInAuthorizationStrategy (allowAnonymousRead=false) qua chính Script Console (một lần, khi quyền còn mở). Dùng một phiên hoàn toàn mới, không mang cookie cũ, gửi lại đúng ba yêu cầu: GET /script trả 403 kèm chuyển hướng /login; POST /scriptText trả 403; GET /api/json trả 403.''')
fig(L31/'03-script-console-anon-after-fix.png','Hình 3.1.9 (tái hiện) Sau khi bật Authorization: /script yêu cầu đăng nhập',maxh=9)
fig(L31/'04-after-fix-summary.png','Hình 3.1.10 (tái hiện) Tổng hợp ba endpoint đều trả 403 cho phiên ẩn danh mới',maxh=7)
paras('''Kết quả tái hiện độc lập khớp với kết luận của báo cáo gốc: nguyên nhân là Authorization chưa được bật ngay sau cài đặt (không riêng một cấu hình "Anyone can do anything" được chọn thủ công), và việc bật Security Realm cùng Authorization Strategy chặn được toàn bộ truy cập ẩn danh, không chỉ riêng /script.''')

page('3.2 Jenkins CLI và đọc file qua tham số')
p('Người phụ trách: Lê Đạt. Thực nghiệm bổ sung và lưu log ngày 11/11/2026.')
h('3.2.1 Định danh và cơ chế',3)
table(['Thuộc tính','Thông tin đối chiếu'],[
('Mã lỗ hổng','CVE-2024-23897; Jenkins SECURITY-3314'),('CVSS 3.1','9.8 Critical; vector AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H'),('Bị ảnh hưởng','Weekly đến 2.441; LTS đến 2.426.2'),('Bản vá trong advisory','Weekly 2.442; LTS 2.426.3 hoặc 2.440.1'),('Lab đối chứng','jenkins/jenkins:2.441-jdk17 và 2.442-jdk17'),('Phân loại','Đọc file tùy ý qua xử lý tham số CLI; liên hệ CWE-22')],widths=[4.5,11.7],caption='Bảng 3.2.1 Thông tin Jenkins CLI theo advisory Jenkins và CVE [J1] [J4]')
paras('''Trong các phiên bản bị ảnh hưởng, bộ phân tích args4j có thể thay tham số bắt đầu bằng @ và đường dẫn thành nội dung file trên controller. Nếu dữ liệu đã thay thế đi vào lỗi cú pháp, người gọi có thể thấy một phần dữ liệu trong phản hồi. Quyền Overall/Read ảnh hưởng phạm vi dữ liệu đọc được; người không có quyền này vẫn có thể đọc một số dòng trong những tình huống advisory nêu [J1].

Phép thử của nhóm giới hạn ở yêu cầu chưa xác thực, file marker tự tạo và /etc/hostname. Mục tiêu là chứng minh parser xử lý file trước khi từ chối hoặc hoàn tất lệnh, không nhằm trích xuất credential. Báo cáo không xem kết quả marker là bằng chứng đã thực hiện RCE.''')

page('3.2.2 Môi trường và thiết kế đối chứng',3)
paras('''Môi trường có hai Jenkins controller chạy trong cùng mạng Docker nội bộ, dùng hai vùng dữ liệu độc lập. Bản 2.441 là container lab đang có trong dự án; bản 2.442 được dựng riêng để đối chứng, không mở cổng host. Cả hai tải CLI client từ chính instance qua endpoint jnlpJars và gửi yêu cầu HTTP tới loopback bên trong container.

Script khởi tạo tạo tài khoản lab, không cấp Overall/Read cho người ẩn danh và tạo file lab-marker.txt với hai dòng nhận diện vô hại. Lệnh help được dùng để tạo phản hồi kiểm tra cú pháp, không sửa job hay cấu hình. Hai phép thử đối chứng dùng cùng tên lệnh, cùng tham số kiểm soát và cùng đường dẫn ở hai phiên bản.

Marker có nội dung dòng đầu CICD-LAB32-HARMLESS-MARKER và dòng thứ hai SECOND-LINE-DEMO. Hostname của controller bản 2.441 là lab32-controller. Đó là dữ liệu đối chiếu, không phải secret. Bản ghi ban đầu thử marker hai dòng còn cho thấy cả dòng thứ hai trong lỗi tham số; phép so sánh cuối dùng tham số LAB32-CONTROL nhất quán trên cả hai phiên bản.''')
table(['Điều kiện','Bản bị ảnh hưởng','Bản vá đối chứng'],[
('Phiên bản qua header','X-Jenkins: 2.441','X-Jenkins: 2.442'),('Xác thực yêu cầu','Không gửi thông tin đăng nhập','Không gửi thông tin đăng nhập'),('Lệnh','help với tham số kiểm soát','Giống phía trước vá'),('File kiểm tra','lab-marker.txt và /etc/hostname','Cùng đường dẫn'),('Tác động mong muốn','Chỉ quan sát phản hồi','Chỉ quan sát phản hồi')],widths=[4.4,5.9,5.9],caption='Bảng 3.2.2 Điều kiện kiểm thử trước và sau vá')

page('3.2.3 Bằng chứng trước bản vá',3)
before=ROOT/'evidence/3.2-jenkins-cli-fileread/before_patch_comparison.txt'
after=ROOT/'evidence/3.2-jenkins-cli-fileread/after_patch_comparison.txt'
transcript(before,QA/'cli-before.png','JENKINS CLI 2.441  BEFORE PATCH')
transcript(after,QA/'cli-after.png','JENKINS CLI 2.442  AFTER PATCH')
fig(QA/'cli-before.png','Hình 3.2.1 Log đối chứng trên Jenkins 2.441 với marker và hostname',maxh=12)
paras('''Phản hồi của phép thử marker chứa “Too many arguments: CICD-LAB32-HARMLESS-MARKER”. Với hostname, phản hồi chứa “Too many arguments: lab32-controller”. Các chuỗi này là nội dung ở phía máy chủ, không phải đường dẫn đã gửi trong tham số.

Mặc dù lệnh kết thúc bằng lỗi cú pháp, dữ liệu vẫn đã xuất hiện trong kênh phản hồi tới người gọi. Do đó mã thoát khác 0 không thể được dùng làm bằng chứng rằng không có rò rỉ. Điều kiện xác nhận là nhận diện nội dung file trong phản hồi, đối chiếu với dữ liệu thử đã biết.

Không có yêu cầu đọc master.key, credentials.xml hoặc file chứa secret thật. Đối với file nhị phân, encoding và cách lệnh phản hồi có thể hạn chế dữ liệu quan sát; kết quả hai file văn bản không chứng minh khả năng đọc nguyên vẹn mọi file.''')

page('3.2.4 Bằng chứng sau bản vá',3)
fig(QA/'cli-after.png','Hình 3.2.2 Log đối chứng trên Jenkins 2.442 giữ nguyên chuỗi đường dẫn',maxh=12)
paras('''Trên bản 2.442, cùng phép thử trả về “Too many arguments: @/var/jenkins_home/lab-marker.txt” hoặc “Too many arguments: @/etc/hostname”. Phản hồi giữ nguyên chuỗi tham số thay vì chứa nội dung file. Đây là khác biệt quan sát trực tiếp so với bản 2.441.

Một lần thử riêng với duy nhất tham số marker sau vá trả về yêu cầu xác thực, phù hợp với chính sách không cấp quyền đọc cho người ẩn danh. Tuy nhiên báo cáo chọn cặp lệnh cùng tham số kiểm soát làm đối chứng chính vì nó thể hiện rõ hành vi parser, tránh nhầm hiệu quả bản vá với sự thay đổi chính sách xác thực.

Kết quả xác nhận việc mở rộng @ đã không xảy ra trong các lệnh thử trên 2.442. Đây là bản vá lịch sử dùng để so sánh riêng CVE-2024-23897; vận hành thực tế cần nâng lên nhánh Jenkins đang được hỗ trợ và kiểm tra các advisory khác, không dừng ở một bản cũ chỉ vì phép thử này đã bị chặn.''')

page('3.2.5 Nguyên nhân và biện pháp phòng chống',3)
table(['Phép thử','Jenkins 2.441','Jenkins 2.442'],[
('Marker có tham số kiểm soát','Nội dung marker xuất hiện','Giữ nguyên @ và đường dẫn'),('Hostname có tham số kiểm soát','lab32-controller xuất hiện','Giữ nguyên @/etc/hostname'),('Secret thật','Không thực hiện','Không thực hiện'),('RCE','Không thực hiện','Không thực hiện')],widths=[4.8,5.7,5.7],caption='Bảng 3.2.3 Tổng hợp đối chứng Jenkins CLI')
paras('''Nguyên nhân gốc nằm ở việc bộ phân tích chấp nhận cú pháp đọc file trong đầu vào CLI từ xa. Kiểm tra quyền ở giai đoạn thực thi lệnh không đủ nếu parser đã đọc file và đường báo lỗi đã đưa dữ liệu ra ngoài. Bản vá của Jenkins vô hiệu hóa chức năng mở rộng @ cho CLI; quản trị viên không nên bật lại tùy chọn allowAtSyntax trên hệ thống có người không phải quản trị truy cập được [J1].

Biện pháp chính là cập nhật Jenkins. Nếu chưa cập nhật được, cần vô hiệu hóa truy cập CLI theo hướng dẫn của Jenkins và kiểm tra cả các phương thức truyền đang hoạt động. Cổng TCP 50000 thường phục vụ kết nối agent, không đại diện cho toàn bộ CLI; chỉ chặn cổng này không đủ để đóng đường HTTP hoặc WebSocket của CLI.

Các lớp bổ sung gồm hạn chế mạng quản trị, không cấp quyền ẩn danh rộng hơn nhu cầu, kiểm soát quyền đọc file của tài khoản hệ điều hành chạy Jenkins và giám sát truy cập endpoint nhạy cảm. Phân quyền làm giảm tác động nhưng không thay thế bản vá khi parser có thể xử lý dữ liệu trước kiểm tra quyền.

Hệ thống tương tự cần rà soát là công cụ CLI từ xa hoặc API dùng thư viện có cú pháp tham chiếu file. Cần tìm rõ hành vi mở rộng tham số, thời điểm đọc file và kênh phản hồi lỗi thay vì chỉ tìm kiểm tra đường dẫn trong phần thực thi lệnh.''')

page('3.3 GitLab SSRF qua webhook')
p('Người phụ trách: Lê Quang Hiển. Bằng chứng gốc: báo cáo mục 3.3 và bốn ảnh thực nghiệm của thành viên.')
h('3.3.1 Khái niệm và phạm vi định danh',3)
paras('''SSRF phát sinh khi máy chủ thực hiện yêu cầu tới đích do người dùng lựa chọn mà không kiểm soát đầy đủ. Trong lab, webhook của GitLab gửi yêu cầu tới một dịch vụ Nginx chỉ có trong mạng Docker. Người dùng không truy cập trực tiếp dịch vụ này từ bên ngoài; GitLab đóng vai trò phát sinh kết nối.

Báo cáo thành viên gắn lab GitLab CE 10.5.5 với CVE-2018-8801 và các bản vá 10.5.6, 10.4.6, 10.3.9. Tuy nhiên mô tả NVD hiện nêu phạm vi từ 8.3 đến trước 10.3, trong khi hồ sơ gói Debian ghi nhận CVE được xử lý trong gói 10.5.6. Vì phạm vi chưa nhất quán, kết quả dưới đây được trình bày là hành vi SSRF quan sát trên phiên bản lab, chưa coi ảnh phiên bản là chứng minh cuối cùng cho định danh CVE [G1] [G2].

CVE-2018-8801 được NVD phân loại CWE-918, điểm CVSS 3.0 là 6.5 với quyền thấp. Điểm này thuộc hồ sơ CVE, không phải điểm chấm riêng của phép thử trên 10.5.5. Các CVE import khác và mã CVE chưa xác minh trong tài liệu gốc không được dùng để mở rộng kết luận của thực nghiệm.''')
table(['Thuộc tính','Giá trị trong lab'],[('Nền tảng','Kali Linux trong máy ảo; Docker Compose'),('GitLab','CE 10.5.5; image 10.5.5-ce.0'),('Cổng','127.0.0.1:8929 → 80'),('Đích thử','internal-service; Nginx trong cùng mạng Docker'),('Tài khoản','Tài khoản thường Hienlq; không dùng Admin để tạo yêu cầu')],widths=[4.2,12],caption='Bảng 3.3.1 Môi trường SSRF được thành viên ghi nhận')

page('3.3.2 Xác nhận phiên bản và đích nội bộ',3)
paras('''Trang /help ghi nhận GitLab Community Edition 10.5.5 với commit c7e4919. Phiên bản này xác định môi trường quan sát, nhưng cần được ghép với chính sách outbound, quyền tài khoản và trạng thái cấu hình mới đủ phân tích vì sao một URL nội bộ được phép kết nối.

Trong project ssrf-lab, thành viên thêm webhook tới http://internal-service/ssrf-check-hienlq. Tên internal-service được Docker phân giải trong mạng lab. Dịch vụ đích không publish cổng ra host, nhờ đó log ở đích thể hiện một kết nối nội bộ từ phía GitLab.''')
srcfig('33',1,'Hình 3.3.1 Phiên bản GitLab CE 10.5.5 trên trang trợ giúp')
srcfig('33',2,'Hình 3.3.2 Webhook trỏ tới dịch vụ nội bộ giả lập')

page('3.3.3 Phản hồi và nhật ký tại đích',3)
paras('''Chức năng Test với Push events được dùng để kích hoạt webhook. Giao diện hiển thị phản hồi 404 cùng nội dung HTML từ Nginx. Mã 404 chỉ có nghĩa đường dẫn thử không tồn tại ở đích; nó không phủ nhận việc kết nối HTTP đã đến được dịch vụ nội bộ.

Nhật ký internal-service ghi POST /ssrf-check-hienlq từ địa chỉ 172.18.0.3, được báo cáo thành viên xác định là container GitLab. Kết hợp URL cấu hình, thời điểm thử và log ở đích tạo bằng chứng mạnh hơn việc chỉ quan sát thông báo lỗi trên giao diện.''')
srcfig('33',3,'Hình 3.3.3 Giao diện Test webhook hiển thị phản hồi từ dịch vụ đích')
srcfig('33',4,'Hình 3.3.4 Nhật ký Nginx ghi nhận POST từ phía GitLab',maxh=9)

page('3.3.4 Phân tích nguyên nhân và kiểm soát kết nối',3)
paras('''Điều kiện quan sát là webhook được phép gọi tới mạng nội bộ trong môi trường lab. Về cơ chế tổng quát, chấp nhận URL của người dùng đòi hỏi kiểm tra giao thức, tên đích, địa chỉ sau phân giải và chính sách redirect. Tên miền không đủ để xác định một đích có an toàn hay không vì một tên có thể trỏ tới loopback, mạng riêng hoặc nhiều địa chỉ IPv4/IPv6.

Không có phép thử redirect hoặc DNS rebinding trong bốn ảnh đã cung cấp. Vì vậy hai kỹ thuật này được xem là tình huống cần bổ sung trong thiết kế phòng thủ, không phải nguyên nhân đã được thực nghiệm xác nhận của lần POST nội bộ. Tương tự, phản hồi Nginx không chứng minh đã truy cập Redis, metadata cloud hoặc trích xuất IAM key.

Tài liệu GitLab mô tả các tùy chọn kiểm soát outbound requests và danh sách cho phép. Thiết kế vận hành cần đặt chính sách mặc định hạn chế, chỉ cho phép tích hợp nội bộ cụ thể khi có nhu cầu được phê duyệt, và triển khai egress firewall bổ sung [G3].

Nếu tự xây dựng bộ lọc URL, việc phân giải DNS rồi kiểm tra nhưng thư viện HTTP lại phân giải lần nữa vẫn có thể tạo khoảng trống giữa kiểm tra và kết nối. Do đó mã tham khảo chỉ kiểm tra DNS một lần không đủ để tuyên bố chống DNS rebinding. Giải pháp cần bảo đảm địa chỉ đã kiểm tra là địa chỉ thực sự kết nối, đồng thời giữ kiểm tra TLS, Host và redirect phù hợp.''')
table(['Đối tượng kiểm tra','Mục tiêu phòng thủ'],[
('Giao thức và cổng','Chỉ cho phép HTTP/HTTPS và cổng có nhu cầu'),('Địa chỉ đích','Chặn loopback, private, link-local và IPv6 tương ứng theo chính sách'),('Redirect','Tắt hoặc kiểm tra từng bước chuyển hướng'),('DNS và kết nối','Không để bước kết nối dùng địa chỉ khác bước kiểm tra'),('Tầng mạng','Giới hạn outbound theo dịch vụ và cổng được phép')],widths=[4.8,11.4],caption='Bảng 3.3.2 Các lớp kiểm soát SSRF đề xuất')

page('3.3.5 Khắc phục đề xuất và giới hạn kết luận',3)
table(['Tiêu chí','Kết quả có bằng chứng','Trạng thái sau xử lý'],[
('URL webhook nội bộ','Đã được thêm','Đã kiểm chứng (xem 3.3.6)'),('POST tới dịch vụ nội bộ','Có log ở đích','Đã kiểm chứng lại sau xử lý'),('Admin Area có outbound-request allowlist?','Đã kiểm tra trực tiếp trên 10.5.5','KHÔNG có (tính năng bổ sung ở bản sau)'),('Nâng cấp GitLab','Chưa thực hiện (giới hạn thời gian)','Khuyến nghị; xem biện pháp giảm thiểu mạng ở 3.3.6')],widths=[5.5,5.0,5.7],caption='Bảng 3.3.3 Trạng thái kiểm chứng SSRF (cập nhật sau tái hiện 12/11/2026)')
paras('''Ưu tiên khắc phục là đưa GitLab về phiên bản đang được hỗ trợ theo lộ trình nâng cấp chính thức, cấu hình lọc outbound và chỉ cho phép những endpoint nội bộ có chủ đích. Việc có một bản vá lịch sử trong nhánh 10.x không khiến nhánh đó phù hợp cho vận hành hiện nay.

Những chức năng khác có ranh giới tương tự gồm import repository, tải ảnh từ URL, preview liên kết, webhook và công cụ render tài liệu có tải tài nguyên ngoài. Chúng cần được đánh giá theo quyền mạng của máy chủ thay vì chỉ dựa vào quyền giao diện của người dùng.''')

page('3.3.6 Tái hiện độc lập và bổ sung bằng chứng sau xử lý (Lê Đạt)',3)
L33=ROOT/'labs/3.3-gitlab-ssrf/evidence'
paras('''Lab được Lê Đạt tự dựng lại ngày 12/11/2026: GitLab CE 10.5.5-ce.0 (amd64 qua QEMU) + một dịch vụ nginx nội bộ không publish cổng ra host, cùng mạng Docker riêng. Qua API, tạo project, một webhook trỏ tới http://internal-target/ (hostname chỉ phân giải được trong mạng Docker của lab) với một marker định danh duy nhất cho mỗi lần thử.''')
fig(L33/'01-version-and-webhook-config.png','Hình 3.3.5 (tái hiện) Phiên bản GitLab 10.5.5 và cấu hình webhook trỏ internal-target',maxh=9)
fig(L33/'02-before-baseline-internal-target-log.png','Hình 3.3.6 (tái hiện) Log baseline — chưa có request nào tới dịch vụ đích',maxh=6)
paras('''Kích hoạt Test → Push events trên webhook. Log truy cập của dịch vụ đích ghi nhận hai request POST tới đúng marker, xuất phát từ địa chỉ IP nội bộ của chính container GitLab — xác nhận GitLab (server) đã tự thực hiện request tới địa chỉ do người dùng cấu hình.''')
fig(L33/'03-ssrf-poc-internal-target-access-log.png','Hình 3.3.7 (tái hiện) Dịch vụ đích ghi nhận POST đến từ IP nội bộ của GitLab',maxh=9)
paras('''Kiểm tra Admin Area → Settings xác nhận bản 10.5.5 không có mục "Outbound requests" — tính năng allow/deny-list cho outbound request chỉ được GitLab bổ sung ở các bản sau. Vì vậy không thể trình diễn đúng "bản vá ứng dụng" cho phiên bản lab này; thay vào đó áp dụng biện pháp giảm thiểu ở tầng mạng: ngắt kết nối dịch vụ đích khỏi mạng Docker của GitLab (docker network disconnect). Kích hoạt lại đúng phép thử: log production.log của GitLab ghi nhận lỗi "Failed to open TCP connection to internal-target:80 (getaddrinfo: Name or service not known)", và log dịch vụ đích không có thêm dòng nào.''')
fig(L33/'04-mitigation-network-segmentation.png','Hình 3.3.8 (tái hiện) Sau cách ly mạng: GitLab không còn kết nối được tới đích; log server xác nhận lỗi phân giải tên',maxh=12)
paras('''Khoảng trống "chưa có bằng chứng sau xử lý" của báo cáo gốc đã được bổ sung bằng phép thử trên, với lưu ý quan trọng: đây là biện pháp giảm nhẹ ở tầng mạng (network segmentation), không phải bản vá chính thức ở tầng ứng dụng cho đúng CVE đã nêu. Về định danh CVE, kết quả tái hiện tiếp tục giữ nguyên thận trọng như 3.3.1: trình bày là hành vi SSRF quan sát được qua webhook trên GitLab 10.5.5, chưa khẳng định chắc chắn đây chính xác là CVE-2018-8801 do hai nguồn tham chiếu (NVD và hồ sơ gói Debian) chưa khớp hoàn toàn phạm vi phiên bản.''')

def import_member(key):
 pattern='*3_4*' if key=='34' else '*3_5*'
 f=next((ROOT/'docs/bao-cao-thanh-vien').glob(pattern+'.docx'))
 d=Document(f);started=False;imgn=0
 for el in d.element.body:
  if el.tag==qn('w:p'):
   pa=Paragraph(el,d);t=pa.text.strip()
   if t.startswith('3.4.10.') or t=='Tài liệu tham khảo':break
   if key=='35' and t.startswith('3.5. CI/CD'):continue
   if key=='35' and (t=='(DEPENDENCY CONFUSION)' or t.startswith('Báo cáo thực nghiệm')):continue
   if key=='34' and t.startswith('3.4. CI/CD'):continue
   # Central source keys avoid ambiguous per-section [1] references.
   pref='R' if key=='34' else 'D'
   t=re.sub(r'\[(\d+)\]',lambda m:f'[{pref}{m[1]}]',t)
   # Source comparison uses a harmless marker, not actual extracted credentials.
   if key=='34':
    t=t.replace('Rò rỉ','Nguy cơ được minh họa') if t=='Rò rỉ' else t
    t=t.replace('Developer lấy được biến','Job nhánh Developer được cấp biến')
   if t:
    if re.match(r'3\.[45]\.\d+\.',t):
     level=3
     if any(t.startswith(x) for x in ['3.4.2.','3.4.3.','3.4.4.','3.4.5.','3.4.6.','3.5.3.','3.5.4.','3.5.5.','3.5.7.','3.5.8.']):page()
     h(t,level)
    elif t.startswith('Hình '):
     t=re.sub(r'^Hình (\d+)',lambda m:f'Hình 3.{key[-1]}.{m[1]}',t)
     pp=p(t,'Caption');pp.alignment=WD_ALIGN_PARAGRAPH.CENTER;FIGS.append(t)
    elif t.startswith('Bảng '):
     t=re.sub(r'^Bảng (\d+)',lambda m:f'Bảng 3.{key[-1]}.{m[1]}',t)
     pp=p(t,'Caption');pp.paragraph_format.keep_with_next=True;TABLES.append(t)
    elif re.match(r'^\d+\. ',t) or re.match(r'^[a-e]\) ',t):h(t,3)
    elif any(x in t for x in ['stages:\n','script:\n','create_lab_marker:\n','registry=http://']):code(t)
    else:p(t)
   for b in el.xpath('.//a:blip'):
    rid=b.get(qn('r:embed'))
    if not rid:continue
    imgn+=1;blob=d.part.related_parts[rid].blob;im=Image.open(BytesIO(blob));wi=16.2;hi=wi*im.height/im.width
    if hi>8.5:wi*=8.5/hi
    pp=p();pp.alignment=WD_ALIGN_PARAGRAPH.CENTER;pp.paragraph_format.keep_with_next=True
    pp.add_run().add_picture(BytesIO(blob),width=Cm(wi))
  elif el.tag==qn('w:tbl'):
   tt=Table(el,d);rows=[[c.text for c in row.cells] for row in tt.rows]
   if rows:table(rows[0],rows[1:])

page('3.4 CI CD Runner và bảo vệ secret')
p('Người phụ trách: Mỹ Duyên. Kết quả và hình được tổng hợp từ báo cáo thực nghiệm Runner của thành viên.')
h('3.4.1 Bối cảnh và mô hình thực nghiệm',3)
paras('''Runner thực thi các lệnh trong job, vì vậy quyền sửa pipeline có thể trở thành quyền thực thi mã trong môi trường Runner. Rủi ro tăng khi nhiều project có mức tin cậy khác nhau dùng chung hệ thống file hoặc tài khoản thực thi. GitLab khuyến cáo chỉ dùng shell executor cho build đáng tin cậy; Docker executor cũng cần cấu hình không đặc quyền và giới hạn tài nguyên chia sẻ [R2] [R3].

Lab gồm Project A do root quản lý, Project B và một bản fork do user attacker quản lý. User attacker là tài khoản thường và được cấp Developer trong Project A ở kịch bản kiểm tra biến. Hai Runner loại Instance được dùng để so sánh: Runner số 1 với tag shared-shell và shell executor; Runner số 2 với tag shared-docker, Docker executor, image job alpine:3.20 và privileged=false.

Báo cáo thành viên ghi nhận GitLab CE và Runner 19.5.0 trên Windows/Docker Desktop, nhưng cấu hình image dùng latest. Các số phiên bản này là thông tin do thành viên ghi nhận, chưa được tái xác nhận bằng log image trong lần tổng hợp. Cần bổ sung digest hoặc manifest để khóa môi trường tái lập. Secret kiểm tra là các biến giả; job chỉ in trạng thái có hoặc không được cấp biến.''')
srcfig('34',1,'Hình 3.4.1 Kiến trúc lab Runner và các project thử nghiệm')

page('3.4.2 Kịch bản A tài nguyên dùng chung',3)
paras('''Project A tạo file marker trong /tmp với chuỗi LAB_MARKER_FROM_PROJECT_A và quyền đọc phù hợp. Sau đó job của Project B chạy trên cùng shell Runner và kiểm tra đường dẫn này. Log cho thấy Project B đọc thấy marker. Bằng chứng minh họa thiếu cách ly hệ thống file, không phải lấy một secret thật.

Nhóm đồng thời chạy đối chứng biến: FAKE_API_KEY, FAKE_TOKEN và FAKE_CONTROL_A chỉ được khai báo tại Project A. Các job của Project B trên cùng Runner đều ghi NOT set. Như vậy dùng chung Runner không tự động khiến mọi biến của Project A được truyền sang Project B; đường chia sẻ file và đường cấp biến cần được phân tích riêng.''')
srcfig('34',3,'Hình 3.4.2 Project B đọc thấy marker do Project A tạo trên shell Runner')
srcfig('34',4,'Hình 3.4.3 Đối chứng cho thấy biến của Project A không được cấp sang Project B')

page('3.4.3 Kịch bản B phạm vi cấp biến',3)
paras('''User attacker có vai trò Developer trong Project A tạo nhánh feature-x và thay đổi pipeline để kiểm tra trạng thái biến. Khi FAKE_API_KEY và FAKE_TOKEN chưa Protected, job trên nhánh này ghi nhận cả hai biến đều set. Sau khi người quản trị bật Protected, job ở commit mới trên cùng nhánh ghi cả hai NOT set.

Kết quả chứng minh khác biệt về phạm vi cấp biến theo trạng thái bảo vệ nhánh. Nó không chứng minh job đã đưa giá trị biến ra ngoài vì phép thử chỉ in trạng thái. Tuy nhiên việc job do người sửa pipeline điều khiển được cấp biến là điều kiện cần được xem xét về độ tin cậy của mã [R4].

Masked và Protected giải quyết hai vấn đề khác nhau. Masked che giá trị trên log trong những điều kiện được hỗ trợ; mã của job đã nhận biến vẫn có thể sử dụng biến. Protected giới hạn ngữ cảnh được cấp biến. Lab này không kiểm tra khả năng che chuỗi của Masked, nên không kết luận hiệu quả của chức năng che log.''')
srcfig('34',5,'Hình 3.4.4 Nhánh feature-x được cấp biến khi chưa Protected')
srcfig('34',6,'Hình 3.4.5 Cùng nhánh không được cấp biến sau khi bật Protected')

page('3.4.4 Merge request từ fork và cách ly executor',3)
paras('''Trong bản fork, job kiểm tra FAKE_API_KEY ghi NOT set và tab pipeline của merge request hiển thị 0. File CI của lab chưa khai báo rules cho sự kiện merge request; vì vậy kết luận chỉ áp dụng cho cấu hình này. Không được suy ra mọi MR từ fork luôn an toàn, đặc biệt khi có người chủ động chạy pipeline trong project gốc.

Biện pháp cách ly được kiểm chứng bằng Runner Docker. Project A tạo marker trong container job của mình, sau đó Project B chạy job kiểm tra trên container khác và ghi marker is not visible. Shell Runner được tạm dừng; job còn tag shared-shell bị kẹt vì không có Runner phù hợp. Việc tạm dừng là một lớp kiểm soát vận hành cần được giữ ổn định.

Phép thử trước xử lý cho thấy marker vẫn tồn tại ở môi trường shell. Đối chứng Docker vì thế minh họa thay đổi môi trường thực thi thay vì chỉ xóa file. Lỗi clone_url gặp lúc đầu cũng được thành viên xử lý để job Docker có thể truy cập đúng địa chỉ GitLab trong mạng container.''')
srcfig('34',10,'Hình 3.4.6 Project A tạo marker bên trong container job Docker')
srcfig('34',11,'Hình 3.4.7 Job Docker của Project B không thấy marker của Project A')

page('3.4.5 Bảo vệ nhánh và đối chứng chức năng',3)
paras('''Nhánh main được giới hạn quyền push và merge cho Maintainer; force push tắt. Thành viên ghi nhận Developer sửa trực tiếp pipeline trên main bị từ chối. Các biến giả được đặt Protected. Ngoài ra, vai trò tối thiểu để truyền pipeline variables được đặt Maintainer; tác động riêng của tùy chọn này chưa được đo bằng phép thử.

Đối chứng trên Docker executor gồm job ở main do root chạy và job ở feature-x do attacker chạy. Main vẫn nhận biến, feature-x không nhận. Cặp kết quả cho thấy chính sách không chỉ làm mọi job mất biến mà giới hạn theo bối cảnh nhánh trong điều kiện thử.

Tùy chọn cho MR pipeline truy cập protected variables và runners đang bật trong ảnh cấu hình của thành viên, nhưng chưa được khảo sát. Đây là điểm cần review tiếp trước khi áp dụng mô hình cho môi trường sản xuất, cùng với quyền của người có thể sửa file CI và quyền phê duyệt chạy pipeline.''')
srcfig('34',14,'Hình 3.4.8 Job trên main tin cậy vẫn được cấp biến Protected')
srcfig('34',15,'Hình 3.4.9 Job trên feature-x không được cấp biến Protected')

page('3.4.6 Tổng hợp tác động và biện pháp',3)
table(['Điều kiện','Quan sát','Ý nghĩa'],[
('Shell dùng chung','Project B thấy marker A','Thiếu cách ly file giữa các job'),('Biến chỉ ở Project A','Project B ghi NOT set','Không có bằng chứng tự truyền biến chéo project'),('feature-x và biến chưa Protected','Job ghi set','Biến đến mã pipeline trên nhánh chưa bảo vệ'),('feature-x và biến Protected','Job ghi NOT set','Phạm vi cấp biến đã bị giới hạn'),('Docker không chia sẻ /tmp','Project B không thấy marker','Đường file thử nghiệm đã được cách ly'),('main và biến Protected','Job ghi set','Luồng tin cậy vẫn được cấp biến')],widths=[5.0,5.5,5.7],caption='Bảng 3.4.1 Tổng hợp đối chứng Runner')
paras('''Vấn đề này không có một CVE duy nhất; mức nguy hiểm phụ thuộc quyền của Runner, mức tin cậy của project và giá trị của credential. Các nhóm rủi ro OWASP liên quan là Poisoned Pipeline Execution, Insufficient PBAC, Insufficient Credential Hygiene và Insecure System Configuration [R1].

Cách ly job và giới hạn cấp biến cần được thực hiện đồng thời. Chuyển sang Docker không ngăn một pipeline đã được cấp secret sử dụng secret đó; Protected variables cũng không ngăn file nhạy cảm bị ghi vào vùng tài nguyên chung. Cần giới hạn Runner theo nhóm project tin cậy, tránh đặc quyền, kiểm soát volume và thay credential khi nghi ngờ đã bị tiếp cận.

Container quản lý Runner trong lab được gắn Docker socket để tạo container job. Không có bằng chứng job được gắn socket, nhưng quyền điều khiển Docker daemon vẫn là một ranh giới nhạy cảm. Kết quả không thấy marker chỉ chứng minh cách ly đường file đã thử, không xác nhận an toàn toàn bộ host.

Các nền tảng khác dùng self-hosted runner hoặc agent dùng lại lâu dài cũng cần đánh giá theo cùng ranh giới. Lab chưa đo job đồng thời, chưa khảo sát đầy đủ MR protected resources và chưa chứng minh việc xóa hoàn toàn shell Runner; các điểm này cần bổ sung khi nghiệm thu kiến trúc vận hành.''')

page('3.4.7 Tái hiện độc lập bởi Lê Đạt',3)
L34=ROOT/'labs/3.4-cicd-runner-secret/evidence'
paras('''Lê Đạt tự tái hiện lab này ngày 12/11/2026, tái sử dụng GitLab 10.5.5 của mục 3.3 (cùng instance, chạy tuần tự không song song, theo đúng quyết định của nhóm) và một gitlab-runner riêng đăng ký làm shared runner. Hai project thật được tạo qua API: project-a và project-b; project-b có biến CI/CD DEPLOY_SECRET (giá trị giả) ban đầu protected=false.''')
fig(L34/'01-runner-shell-shared-config.png','Hình 3.4.10 (tái hiện) Runner dùng chung, shell executor, không cách ly filesystem giữa job',maxh=7)
fig(L34/'02-project-b-variable-unprotected.png','Hình 3.4.11 (tái hiện) Biến DEPLOY_SECRET của project-b chưa Protected',maxh=6)
paras('''Job của project-b ghi giá trị DEPLOY_SECRET ra /tmp/lab34-job-trace-project-b. Job của project-a — project khác, chạy trên cùng runner shell executor — đọc được chính file này và in ra nguyên văn giá trị secret giả của project-b. Đồng thời, env | grep DEPLOY ở job A không thấy biến — xác nhận GitLab vẫn scope đúng biến môi trường theo project; rò rỉ chỉ xảy ra qua filesystem /tmp dùng chung.''')
fig(L34/'03-cross-project-trace-leak-shell-executor.png','Hình 3.4.12 (tái hiện) Job project-a đọc được secret của project-b qua file dùng chung trên shell executor',maxh=12)
paras('''Thử trên nhánh feature-x (không Protected) của project-b trong khi DEPLOY_SECRET vẫn protected=false: job nhận được secret bình thường. Sau khi đặt protected=true cho đúng biến đó, chạy lại chính xác cùng pipeline trên cùng nhánh feature-x: biến trống, không còn được cấp.''')
fig(L34/'04-unprotected-variable-on-unprotected-branch.png','Hình 3.4.13 (tái hiện) Trước/sau khi bật Protected cho biến trên cùng một nhánh chưa bảo vệ',maxh=12)
paras('''Khắc phục rò rỉ filesystem: đăng ký thêm một runner dùng docker executor (image alpine:latest, mỗi job một container, hủy sau khi chạy). Lặp lại đúng phép thử trace: job project-a trên docker executor không còn tìm thấy hay đọc được file trace nào của project-b.''')
fig(L34/'05-after-docker-executor-isolation.png','Hình 3.4.14 (tái hiện) Sau khi chuyển sang Docker executor: không còn thấy dấu vết job của project khác',maxh=12)
paras('''Hai kết quả tái hiện củng cố trực tiếp hai kết luận chính của báo cáo gốc: (1) shell executor dùng chung gây rò rỉ chéo project qua filesystem dù biến môi trường vẫn được scope đúng; (2) biến chưa Protected bị cấp cho cả nhánh không bảo vệ, và việc bật Protected khắc phục đúng vấn đề đó mà không cần đổi gì khác.''')

page('3.5 Dependency Confusion trong chuỗi cung ứng')
p('Người phụ trách: Phan Thị Hạ Duy. Kết quả và hình được tổng hợp từ báo cáo Dependency Confusion của thành viên.')
h('3.5.1 Khái niệm và giới hạn mô phỏng',3)
paras('''Dependency confusion là rủi ro nhận package từ nguồn không mong muốn khi tên và quy tắc phân giải dependency nội bộ chưa được quản lý đúng. Trong lab, hai registry Verdaccio cục bộ đóng vai nguồn nội bộ và nguồn bên ngoài mô phỏng. Package ngoài chỉ in dấu hiệu nhận diện, không thu thập dữ liệu hay thực hiện payload độc hại.

Package không scope ten-noi-bo-demo-pkg có bản 1.0.0 ở nguồn nội bộ và bản 9.9.9 ở nguồn bên ngoài. Package @internal/ten-noi-bo-demo-pkg có bản 1.0.0 ở registry nội bộ. Jenkins cài và kiểm tra các package trong workspace riêng được sao chép từ /lab-source chỉ đọc.

Kịch bản cấu hình sai chủ động đổi registry mặc định sang nguồn bên ngoài và đổi phạm vi phiên bản từ ^1.0.0 thành *. Đây là mô phỏng tác động của chọn sai nguồn, không phải bằng chứng npm mặc định tra cứu mọi registry rồi chọn số phiên bản cao nhất. Phạm vi ^1.0.0 cũng không chấp nhận 9.9.9, nên hai thay đổi cấu hình phải được nêu cùng khi giải thích kết quả.''')
srcfig('35',1,'Hình 3.5.1 Kiến trúc Jenkins và hai registry Verdaccio cục bộ',maxh=9)

page('3.5.2 Môi trường và thiết kế pipeline',3)
table(['Thành phần','Địa chỉ','Vai trò'],[
('Jenkins','localhost:18080','Thực thi pipeline và lưu console output'),('internal-registry','Trong Docker :4873; host :4873','Nguồn package nội bộ'),('external-registry','Trong Docker :4873; host :4874','Nguồn bên ngoài mô phỏng'),('Consumer','Workspace Jenkins','In nguồn và phiên bản dependency')],widths=[4.3,6,5.9],caption='Bảng 3.5.1 Thành phần môi trường Dependency Confusion')
table(['Stage','Nội dung'],[
('Prepare Workspace','Sao chép source; chuẩn bị cấu hình registry'),('Install Dependency','Cài package theo ^1.0.0'),('Verify Dependency','Xác nhận nguồn và dấu hiệu INTERNAL PACKAGE'),('Simulate Dependency Confusion','Đổi registry và phạm vi; kiểm tra package có scope'),('Fixed Configuration','Khôi phục nguồn nội bộ và ^1.0.0'),('Verify Scope Registry and Lockfile','Kiểm tra resolved; chạy npm ci và xác minh phiên bản')],widths=[6.8,9.4],caption='Bảng 3.5.2 Sáu stage của pipeline thực nghiệm')
paras('''Xóa node_modules và lockfile ở các stage mô phỏng giúp buộc cài mới theo cấu hình của từng kịch bản. Đây là thao tác trong thư mục thử nghiệm riêng, không phải khuyến nghị xóa lockfile trong pipeline sản xuất. Mỗi lần cài được đối chiếu bằng log phiên bản và dấu hiệu nhận diện của package.

Ảnh môi trường và registry trong báo cáo thành viên cho thấy hai nguồn cục bộ độc lập. Hệ thống không publish package giả lên npm công khai. Để tái lập chính xác hơn cần ghi phiên bản Jenkins, Node.js, npm và image Verdaccio hoặc digest; các ảnh hiện có chưa cung cấp đủ toàn bộ thông tin đó.''')

page('3.5.3 Kết quả SAFE và MISCONFIGURED',3)
paras('''Ở SAFE, registry mặc định là internal-registry và dependency không scope dùng ^1.0.0. Package 1.0.0 được cài; ci-check ghi INTERNAL PACKAGE và kết thúc PASS. Kết quả phản ánh cấu hình nguồn nội bộ đúng trong điều kiện thử.

Ở MISCONFIGURED, registry mặc định chuyển thành external-registry, phạm vi không scope thành *, còn @internal:registry vẫn trỏ về nguồn nội bộ. Package không scope trở thành 9.9.9 và in EXTERNAL PACKAGE. Cùng điều kiện đó, package có scope vẫn được cài bản 1.0.0 từ nguồn nội bộ. Điều này phù hợp với cơ chế liên kết scope và registry của npm [D4].''')
srcfig('35',4,'Hình 3.5.2 SAFE cài package 1.0.0 từ registry nội bộ')
srcfig('35',5,'Hình 3.5.3 MISCONFIGURED cài bản ngoài 9.9.9 nhưng scope vẫn về nội bộ')

page('3.5.4 Khôi phục cấu hình và kiểm tra nguồn',3)
paras('''Ở FIXED, registry mặc định và registry của scope @internal được đưa về nội bộ; dependency không scope trở lại ^1.0.0. Sau cài lại, ci-check ghi nhận phiên bản 1.0.0, nguồn nội bộ và PASS. Sự khác biệt quan sát được gắn với cấu hình có chủ đích chứ không phải một thay đổi tự động ở npm.

Stage lockfile tạo thư mục thử độc lập, khai báo package có scope và không scope ở 1.0.0, tạo package-lock.json rồi kiểm tra trường resolved. Log ghi cả hai URL thuộc internal-registry. Đây là bằng chứng về nguồn được ghi trong lockfile, không tự xác nhận chất lượng hoặc sự vô hại của mọi nội dung package.''')
srcfig('35',6,'Hình 3.5.4 FIXED khôi phục registry nội bộ và package 1.0.0')
srcfig('35',7,'Hình 3.5.5 Lockfile ghi resolved của hai package về registry nội bộ')

page('3.5.5 Cài tái lập và tổng hợp kết quả',3)
paras('''Lệnh npm ci chạy trong thư mục kiểm tra theo lockfile đã tạo. Bước xác minh ghi package có scope và không scope đều ở 1.0.0; pipeline kết thúc PASS: all lab stages completed và Finished: SUCCESS. Trạng thái SUCCESS có nghĩa sáu stage chạy đúng điều kiện đã định nghĩa, bao gồm cả stage cố tình cấu hình sai; nó không có nghĩa mọi stage đều an toàn.

Lockfile và npm ci giúp tránh phân giải lại tùy ý theo phạm vi phiên bản, nhưng chỉ bảo vệ bộ dependency đã được duyệt nếu chính lockfile cũng được review và nguồn package được kiểm soát. Việc đổi registry hoặc tạo lại lockfile cần có dấu vết và kiểm tra tương ứng [D5].''')
srcfig('35',8,'Hình 3.5.6 npm ci xác nhận phiên bản và pipeline hoàn thành',maxh=8)
table(['Kịch bản','Không scope','Có scope','Kết luận'],[
('SAFE','1.0.0 nội bộ','Không đo riêng','Cấu hình gốc đúng'),('MISCONFIGURED','9.9.9 nguồn ngoài mô phỏng','1.0.0 nội bộ','Scope routing giới hạn nguồn'),('FIXED','1.0.0 nội bộ','Không đo riêng','Khôi phục nguồn đúng'),('Lockfile và npm ci','1.0.0; resolved nội bộ','1.0.0; resolved nội bộ','Cài tái lập theo lockfile')],widths=[3.6,4.5,4.4,3.7],caption='Bảng 3.5.3 Đối chiếu các kịch bản dependency')

page('3.5.6 Sự cố thực tế và biện pháp phòng chống',3)
paras('''Nghiên cứu do Alex Birsan công bố năm 2021 mô tả dependency confusion trong các hệ sinh thái npm, PyPI và RubyGems; đây là nguồn do tác giả nghiên cứu công bố và được báo cáo thành viên dùng để đặt vấn đề [D1]. Báo cáo tổng hợp không coi các tổ chức trong nghiên cứu đó là đối tượng kiểm thử của nhóm.

PyTorch công bố sự cố torchtriton của bản nightly trên Linux cài bằng pip trong khoảng 25–30/12/2022. Package trùng tên trên PyPI được cài thay nguồn của PyTorch; thông báo cho biết bản stable không bị ảnh hưởng. Đây là ví dụ thực tế về rủi ro nguồn dependency ở hệ sinh thái khác, không phải kết quả tái hiện của lab npm [D2].

Biện pháp đã thử gồm định tuyến registry rõ ràng, dùng scope @internal, khôi phục phạm vi ^1.0.0, kiểm tra resolved và chạy npm ci. Trong vận hành, cần thêm giới hạn quyền publish, bảo vệ cấu hình registry, review lockfile, kiểm tra integrity và rà soát dependency. Đăng ký tên hoặc scope phù hợp giúp quản trị namespace nhưng không thay thế kiểm soát nguồn.

Lab chưa mô phỏng proxy/uplink, tự động fallback giữa registry hoặc nhiều package manager. Hai biến được thay cùng lúc ở MISCONFIGURED là nguồn và phạm vi phiên bản, nên không thể cô lập tác động từng biến từ phép thử này. Kết luận phù hợp là cấu hình nguồn sai có thể khiến pipeline sử dụng package không mong muốn, còn scope và lockfile hỗ trợ kiểm soát trong phạm vi đã thử.''')
table(['Biện pháp','Trạng thái trong lab'],[
('Registry nội bộ rõ ràng','Có đối chứng SAFE và FIXED'),('Scope trỏ registry riêng','Có đối chứng cùng kịch bản MISCONFIGURED'),('Lockfile và npm ci','Có log kiểm tra resolved và phiên bản'),('Quét dependency và kiểm soát publish','Khuyến nghị; chưa có đối chứng riêng'),('Proxy hoặc nhiều package manager','Chưa kiểm thử')],widths=[7.4,8.8],caption='Bảng 3.5.4 Biện pháp đã thử và khuyến nghị bổ sung')

page('3.5.7 Tái hiện độc lập bởi Lê Đạt',3)
L35=ROOT/'labs/3.5-dependency-confusion/evidence'
paras('''Lê Đạt tự dựng lại độc lập ngày 12/11/2026 bằng hai registry Verdaccio thật (không mô phỏng bằng mô tả): một registry "nội bộ" (:4873) và một registry "public" giả lập (:4874), cả hai cấu hình uplinks rỗng nên không có đường proxy ra npm thật. Gói ten-noi-bo-demo-pkg được publish thật: bản 1.0.0 lên registry nội bộ, bản 9.9.9 (giả lập kẻ tấn công, script postinstall chỉ console.log) lên registry public. Dependency trong project demo khai báo "*" (không ghim chặt phạm vi).''')
paras('''.npmrc cấu hình sai (registry mặc định trỏ sang public giả lập). Chạy npm install --foreground-scripts lần đầu (chưa có lockfile):''')
code('''> ten-noi-bo-demo-pkg@9.9.9 postinstall
> node -e "console.log('[ATTACKER-SIMULATION] postinstall da chay tu ban 9.9.9 ...')"
[ATTACKER-SIMULATION] postinstall da chay tu ban 9.9.9 tren registry PUBLIC gia lap ...''')
paras('''npm chọn đúng bản 9.9.9 từ nguồn public giả lập và script postinstall của gói giả mạo đã thực thi thật (không phải suy luận lý thuyết). Khắc phục: .npmrc chỉ còn registry nội bộ, xoá lockfile và cài lại — lockfile mới ghi resolved trỏ đúng tarball trên registry nội bộ:''')
code('''"ten-noi-bo-demo-pkg": "1.0.0"
"resolved": "http://127.0.0.1:4873/ten-noi-bo-demo-pkg/-/ten-noi-bo-demo-pkg-1.0.0.tgz"''')
paras('''Kiểm chứng bằng npm ci (chỉ dựa vào lockfile, không phụ thuộc .npmrc tại thời điểm cài): vẫn cài đúng bản 1.0.0, script postinstall an toàn chạy ("...tu registry noi bo - AN TOAN"). Khác với mô phỏng trong 3.5.1-3.5.6 (chỉ đổi cấu hình để minh họa cơ chế), lần tái hiện này publish và cài đặt package thật qua registry thật, nên trực tiếp xác nhận: (1) không ghim registry/scope khiến npm có thể chọn nhầm nguồn không tin cậy; (2) lockfile ghi resolved theo registry cụ thể và npm ci tôn trọng đúng nguồn đó bất kể .npmrc hiện tại là gì.''')

page('CHƯƠNG 4 GIẢI PHÁP PHÒNG CHỐNG TỔNG THỂ',1)
h('4.1 Kiến trúc bảo vệ theo ranh giới tin cậy')
paras('''Các thực nghiệm chỉ ra rằng quyền quản trị, quyền chạy job và quyền cung cấp dependency cần được quản lý riêng. Controller nên ở vùng quản trị; Runner thực thi mã chưa tin cậy không được có đường đi mặc định tới cơ sở dữ liệu hoặc môi trường sản xuất. Registry nội bộ và kho artifact cần có cơ chế xác thực, phân quyền publish và nhật ký thay đổi.

Luồng đề xuất là Developer gửi thay đổi vào nhánh review; pipeline kiểm thử chạy trên Runner tạm thời không có secret triển khai; artifact được gắn với commit và kết quả kiểm tra. Sau khi người có thẩm quyền duyệt, job triển khai riêng mới nhận credential phù hợp môi trường. Thiết kế này giảm khả năng một thay đổi ở nhánh thường sử dụng ngay quyền sản xuất.

Controller không nên vừa là điểm quản trị vừa là môi trường chạy mọi build tùy ý. Khi bắt buộc dùng Docker executor, cần tránh privileged, host PID, host filesystem và việc đưa Docker socket vào container job. Socket ở container quản lý Runner cũng là một phần nhạy cảm cần kiểm soát truy cập; thành công của phép thử cách ly /tmp không chứng minh toàn bộ host đã an toàn.

Đối với webhook, mạng nên có một tuyến outbound được giám sát và chỉ cho phép những đích tích hợp đã phê duyệt. Nếu cần gọi một dịch vụ nội bộ, chính sách phải nêu rõ dịch vụ, cổng, mục đích và người sở hữu; không mở toàn bộ dải nội bộ để tiện cấu hình.''')
table(['Vùng','Thành phần','Quyền tối thiểu'],[
('Quản trị','Controller Jenkins/GitLab','Quản lý pipeline; truy cập quản trị có kiểm soát'),('Thực thi chưa tin cậy','Runner build/test','Lấy mã và dependency được duyệt; không có deploy secret'),('Cung ứng','Registry và artifact store','Read cho build; publish riêng theo vai trò'),('Triển khai','Runner triển khai','Chỉ nhận artifact và credential đúng môi trường')],widths=[4,5.2,7],caption='Bảng 4.1 Phân vùng và trách nhiệm bảo vệ')

page('4.2 Chính sách danh tính và thông tin xác thực')
paras('''Mọi tài khoản có khả năng thay đổi chính sách bảo mật, chạy Script Console hoặc sửa cấu hình Runner phải được xem là tài khoản đặc quyền. Cần hạn chế số người giữ quyền, dùng danh tính riêng thay vì tài khoản chia sẻ và lưu lịch sử thay đổi. SSO hỗ trợ quản lý danh tính tập trung nhưng chính sách quyền trong Jenkins/GitLab vẫn phải được cấu hình đúng.

Secret chỉ được cấp cho công việc cần dùng, vào thời điểm cần dùng và ở môi trường được chỉ định. Biến Protected cần đi cùng nhánh hoặc tag được bảo vệ, review thay đổi file pipeline và giới hạn người được chạy pipeline ở bối cảnh tin cậy. Masked là lớp che log, không phải ranh giới bảo mật đối với mã đã nhận được biến.

Đối với pipeline từ fork hoặc nhánh chưa được duyệt, mặc định nên chạy kiểm thử không có secret triển khai. Nếu cần chạy trong project gốc, người duyệt phải xem cả mã nguồn và nội dung pipeline sẽ được thực thi, thay vì chỉ nhìn trạng thái merge request.

Sau khi nghi ngờ secret bị đọc bởi job hoặc controller bị xâm nhập, cần thu hồi và cấp lại credential tương ứng, kiểm tra log sử dụng ở dịch vụ đích và xác định artifact nào được tạo trong khoảng thời gian đó. Chỉ sửa cấu hình pipeline không làm secret đã lộ trở lại an toàn.''')
table(['Loại quyền','Chủ sở hữu đề xuất','Phép thử nghiệm thu'],[
('Quản trị controller','Nhóm quản trị CI/CD','Ẩn danh và tài khoản thường không chạy được console'),('Sửa pipeline tin cậy','Maintainer được phân công','Developer không push trực tiếp vào nhánh bảo vệ'),('Nhận secret triển khai','Job triển khai được duyệt','Nhánh thường không được cấp biến'),('Publish package','Tài khoản dịch vụ riêng','Build thường không thể phát hành đè package')],widths=[4.4,5.2,6.6],caption='Bảng 4.2 Chính sách quyền và phép thử tương ứng')

page('4.3 Quản lý phiên bản và nguồn dependency')
paras('''Danh mục tài sản cần ghi phiên bản ứng dụng, plugin, Runner, image job và registry đang sử dụng. Với lab hoặc môi trường cần tái lập, tag latest hoặc lts nên được thay bằng phiên bản cụ thể, tốt hơn là bổ sung digest. Nhật ký cập nhật phải ghi advisory liên quan, phạm vi ảnh hưởng, kiểm thử hồi quy và người phê duyệt triển khai.

Khi cập nhật Jenkins hoặc GitLab, cần chọn nhánh đang được nhà cung cấp hỗ trợ và tuân thủ lộ trình nâng cấp. Một phiên bản lịch sử đã sửa CVE của lab chỉ chứng minh một thay đổi cụ thể, không phải tiêu chuẩn bảo mật đầy đủ cho hệ thống hiện hành.

Đối với dependency nội bộ, đặt scope thuộc tổ chức và cấu hình registry theo scope giúp giảm nhầm nguồn. Pipeline cần kiểm tra cấu hình hiệu lực trước cài đặt vì cấu hình ở cấp user hoặc môi trường có thể ghi đè mong đợi ở dự án. Các thay đổi .npmrc, package.json và lockfile phải được review cùng nhau.

Lockfile đã được duyệt kết hợp npm ci giúp cài đặt theo bộ dependency đã chốt. Trường resolved và integrity cung cấp dữ liệu để kiểm tra nguồn và tính nhất quán, nhưng không xác nhận package là vô hại. Nếu ngay từ đầu lockfile ghi nhận package không tin cậy, cài lặp lại chính xác vẫn có thể tái tạo rủi ro.''')
table(['Đối tượng','Bằng chứng cần lưu','Điều kiện chặn phát hành'],[
('Controller và plugin','Version; advisory; log kiểm thử','Phiên bản có lỗ hổng chưa xử lý theo mức ưu tiên'),('Image Runner/job','Tag và digest; quyền container','Privileged hoặc mount nhạy cảm ngoài thiết kế'),('Dependency','Scope; registry; lockfile; resolved','Nguồn không được duyệt hoặc thay đổi chưa review'),('Artifact','Commit; job; checksum','Không truy được nguồn build đã phê duyệt')],widths=[4,6,6.2],caption='Bảng 4.3 Hồ sơ phiên bản và nguồn cung ứng')

page('4.4 Giám sát và ứng phó sự cố')
paras('''Nhật ký cần trả lời được ai thay đổi chính sách, job nào nhận credential, webhook nào gọi đến đâu và artifact nào được phát hành. Không nên dựa riêng vào log console của job vì người sửa pipeline có thể chủ động thay đổi nội dung được in ra. Nên kết hợp log quản trị, log ở dịch vụ đích và dữ liệu từ hệ thống cấp secret.

Các dấu hiệu cần xem xét gồm truy cập chức năng quản trị từ tài khoản không phù hợp, lỗi CLI có chuỗi đường dẫn nhạy cảm, webhook gọi nhiều địa chỉ nội bộ, job thay đổi registry hoặc lockfile không qua review và hoạt động bất thường của credential triển khai. Cảnh báo cần gắn với bối cảnh thay đổi hợp lệ để tránh coi mọi thao tác quản trị là sự cố.

Khi có sự cố, bước đầu là giới hạn tiếp diễn: tạm dừng Runner hoặc pipeline liên quan, vô hiệu hóa đường quản trị bị lạm dụng và thu hồi credential có khả năng bị ảnh hưởng. Sau đó bảo toàn log, xác định thời điểm, commit, job và artifact; tái dựng môi trường thực thi từ nguồn sạch trước khi khôi phục.

Đối với Runner dùng lại lâu dài, xóa một file marker hoặc sửa một job không đủ chứng minh trạng thái sạch. Cần đánh giá khả năng trạng thái độc hại còn lưu trong workspace, cache, home hoặc dịch vụ của Runner. Môi trường tạm thời giúp giảm dữ liệu tồn dư nhưng vẫn cần kiểm soát image và các tài nguyên được chia sẻ.''')
table(['Giai đoạn','Hoạt động chính','Đầu ra'],[
('Phát hiện','Đối chiếu cảnh báo, log và thay đổi','Phạm vi nghi ngờ ban đầu'),('Cô lập','Dừng job/Runner hoặc đường truy cập liên quan','Giảm khả năng tiếp tục tác động'),('Điều tra','Xác định credential, artifact và commit','Danh sách ảnh hưởng có bằng chứng'),('Khôi phục','Tái dựng từ nguồn sạch; cấp lại quyền','Môi trường được kiểm tra trước khi mở lại'),('Rút kinh nghiệm','Bổ sung chính sách và phép thử','Kiểm soát ngăn tái diễn')],widths=[3.2,7.3,5.7],caption='Bảng 4.4 Quy trình ứng phó đề xuất')

page('4.5 Lộ trình thực hiện và tiêu chí nghiệm thu')
table(['Ưu tiên','Việc thực hiện','Chủ trì','Tiêu chí hoàn tất'],[
('P0','Đóng console ẩn danh; tắt CLI chưa vá; cô lập lab cũ','Quản trị CI/CD','Phép thử truy cập trái quyền bị từ chối'),('P1','Cập nhật controller; tách Runner theo mức tin cậy','Quản trị nền tảng','Version và log đối chứng được lưu'),('P1','Protected variables và review pipeline','Maintainer','Nhánh thường không nhận deploy secret'),('P1','Registry scope và lockfile đã review','Phụ trách build','Nguồn và phiên bản phù hợp chính sách'),('P2','Giám sát, kiểm kê và diễn tập ứng phó','Nhóm vận hành','Truy vết được thay đổi tới artifact')],widths=[1.5,6.4,3.2,5.1],caption='Bảng 4.5 Lộ trình triển khai đề xuất')
paras('''Các mức ưu tiên là thứ tự triển khai đề xuất, không phải thời hạn hoặc cam kết thực tế của nhóm. Việc hoàn tất cần được xác nhận bằng kết quả kiểm thử, không chỉ bằng ảnh tùy chọn cấu hình đã được bật.

Đối với từng thay đổi, cần có phép thử phủ định để xác nhận đối tượng không được phép đã bị chặn và phép thử chức năng để xác nhận luồng hợp lệ vẫn chạy. Ví dụ, biến Protected không đến nhánh thường nhưng vẫn có ở main tin cậy; webhook bị chặn tới đích ngoài allowlist nhưng vẫn gọi được tích hợp được duyệt.

Những khoảng trống của đồ án có thể đưa vào vòng hoàn thiện tiếp theo gồm đối chứng SSRF sau xử lý, kiểm tra quyền tài khoản thường tại Script Console, ghim lại toàn bộ image và kiểm thử tác động của tùy chọn MR pipeline. Không nên đánh dấu những mục này hoàn tất chỉ dựa trên khuyến nghị trong báo cáo.''')

page('KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN',1)
h('Kết quả đạt được')
paras('''Đề tài đã tổng hợp năm tình huống có tác động trực tiếp tới tính bí mật, toàn vẹn và khả năng kiểm soát của quy trình CI/CD. Kết quả làm rõ sự khác nhau giữa lỗi phần mềm cần bản vá và rủi ro do cấu hình hoặc thiết kế vận hành cần thay đổi chính sách.

Jenkins Script Console minh họa quyền quản trị được mở cho người ẩn danh; sau xử lý, yêu cầu bị chuyển tới trang đăng nhập — kết luận này đã được Lê Đạt tái hiện độc lập và xác nhận lại bằng một lab riêng (mục 3.1.6). Jenkins CLI có đối chứng trực tiếp giữa hai phiên bản: dữ liệu marker và hostname xuất hiện trong phản hồi bản 2.441, còn 2.442 giữ nguyên tham số đường dẫn. GitLab webhook ghi nhận yêu cầu POST đến dịch vụ nội bộ; sau khi áp dụng network segmentation (do bản 10.5.5 không có allowlist outbound ở tầng ứng dụng), log server xác nhận request không còn tới được đích (mục 3.3.6).

Lab Runner thể hiện hai đường cần xử lý riêng: file dùng chung có thể bị đọc chéo project (đã tái hiện và xác nhận bằng dữ liệu thật ở mục 3.4.7 — job project khác đọc được nguyên văn secret giả), trong khi biến project không tự động được chuyển sang project khác qua biến môi trường; biến không Protected bị cấp cho pipeline trên nhánh không bảo vệ, và việc bật Protected đã được kiểm chứng khắc phục đúng vấn đề đó trên cùng một nhánh. Docker executor cách ly được hoàn toàn dấu vết filesystem giữa các job khác project. Lab dependency confusion nay có phép thử publish và cài đặt package thật qua hai registry Verdaccio (mục 3.5.7), không chỉ mô phỏng bằng đổi cấu hình, cho kết quả cùng chiều với phần mô phỏng ban đầu.

Giải pháp tổng thể được đề xuất dựa trên ranh giới tin cậy: bảo vệ controller, cách ly môi trường thực thi, kiểm soát cấp secret, quản lý nguồn package và truy vết artifact. Những biện pháp này hỗ trợ nhau và cần được kiểm tra cùng luồng chức năng hợp lệ.''')
h('Hạn chế và hướng phát triển')
paras('''Dù mục 3.3 nay đã có bằng chứng sau xử lý, đó là biện pháp giảm nhẹ ở tầng mạng chứ không phải bản vá ứng dụng cho đúng CVE, và liên hệ chính xác với CVE-2018-8801 vẫn cần đối chiếu thêm. Một số môi trường thành viên còn dùng tag thay đổi theo thời gian. Script Console (cả bản gốc lẫn bản tái hiện) chưa có đối chứng tài khoản thường; Runner chưa kiểm thử mọi tùy chọn MR và rủi ro Docker socket; dependency confusion (cả mô phỏng lẫn tái hiện bằng registry thật) chưa thử proxy/uplink hay nhiều hệ sinh thái package khác ngoài npm.

Hướng phát triển là tự động hóa bộ phép thử an toàn, chuẩn hóa image bằng digest, bổ sung chính sách mạng có đối chứng, dùng credential ngắn hạn và lưu provenance cho artifact. Các phép thử cần chạy trong môi trường riêng, dùng dữ liệu giả và tránh đưa secret vào log hoặc ảnh báo cáo.''')

page('PHÂN CÔNG VÀ KHỐI LƯỢNG CÔNG VIỆC',1)
table(['Thành viên','Hạng mục','Sản phẩm và trách nhiệm'],[
('Lê Đạt','Mục 3.2 (chính); tái hiện độc lập 3.1, 3.3, 3.4, 3.5; tổng quan; giải pháp chung; tổng hợp','Lab Jenkins 2.441/2.442 (3.2); dựng lại thật và chụp bằng chứng mới cho 3.1/3.3/3.4/3.5; nội dung chương 1, 2, 4 và tổng hợp báo cáo'),('Đỗ Thảo Dương','Mục 3.1','Nghiên cứu phân quyền; lab Script Console; ảnh truy cập ẩn danh và sau xử lý; báo cáo riêng'),('Lê Quang Hiển','Mục 3.3','Lab webhook; ảnh phiên bản, cấu hình, phản hồi và log đích; phân tích SSRF'),('Mỹ Duyên','Mục 3.4','Hai kịch bản Runner; đối chứng file/biến; Docker executor và Protected variables; báo cáo riêng'),('Phan Thị Hạ Duy','Mục 3.5','Lab hai registry; pipeline sáu stage; scope, lockfile và npm ci; báo cáo riêng')],widths=[3.5,4.1,8.6],caption='Bảng K.1 Phân công và sản phẩm theo kế hoạch nhóm')
p('Phần tái hiện độc lập của Lê Đạt (mục 3.1.6, 3.3.6, 3.4.7, 3.5.7) là bằng chứng bổ sung dựng mới hoàn toàn trên Docker của trưởng nhóm, không thay thế nội dung và đánh giá gốc của từng thành viên.')
p('Khối lượng được thống kê theo hạng mục và sản phẩm, không quy đổi thành số giờ hoặc tỷ lệ đóng góp vì chưa có nhật ký công việc định lượng để xác nhận. Việc tổng hợp không thay thế trách nhiệm của mỗi thành viên trong việc kiểm tra nội dung và bằng chứng thuộc phần mình.')
h('Các nội dung còn cần hoàn thiện thực nghiệm')
table(['Hạng mục','Nội dung cần bổ sung'],[
('3.1','Tái hiện độc lập ĐÃ bổ sung (3.1.6); còn thiếu đối chứng tài khoản thường, image được ghim'),('3.3','Bằng chứng sau xử lý ĐÃ bổ sung (3.3.6, mức mạng); còn cần chốt chính xác liên hệ CVE và thử bản vá ứng dụng nếu nâng cấp được'),('3.4','Đối chứng cross-project và Protected/Docker executor ĐÃ bổ sung (3.4.7); còn thiếu rà soát quyền Docker socket, volume và tùy chọn MR pipeline'),('3.5','Tái hiện bằng registry thật ĐÃ bổ sung (3.5.7); còn thiếu ghim image, thử proxy/uplink và hệ sinh thái package khác'),('Chung','Xác nhận thông tin lớp, mã sinh viên và giảng viên nếu được yêu cầu')],widths=[3.1,13.1],caption='Bảng K.2 Khoảng trống nghiệm thu cần theo dõi (cập nhật sau tái hiện 12/11/2026)')

page('TÀI LIỆU THAM KHẢO',1)
refs=[
('J1','Jenkins Security Advisory 2024-01-24','https://www.jenkins.io/security/advisory/2024-01-24/'),
('J2','Jenkins Script Console','https://www.jenkins.io/doc/book/managing/script-console/'),
('J3','Jenkins CLI','https://www.jenkins.io/doc/book/managing/cli/'),
('J4','NVD CVE-2024-23897','https://nvd.nist.gov/vuln/detail/CVE-2024-23897'),
('G1','NVD CVE-2018-8801','https://nvd.nist.gov/vuln/detail/CVE-2018-8801'),
('G2','Debian bug 893905 về các CVE GitLab và gói 10.5.6','https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=893905'),
('G3','GitLab Filtering outbound requests','https://docs.gitlab.com/security/webhooks/'),
('R1','OWASP Top 10 CI/CD Security Risks','https://owasp.org/www-project-top-10-ci-cd-security-risks/'),
('R2','GitLab The Shell executor','https://docs.gitlab.com/runner/executors/shell/'),
('R3','GitLab Security for self-managed runners','https://docs.gitlab.com/runner/security/'),
('R4','GitLab CI/CD variables','https://docs.gitlab.com/ci/variables/'),
('D1','Alex Birsan Dependency Confusion; công bố của tác giả nghiên cứu','https://medium.com/@alex.birsan/dependency-confusion-4a5d60fec610'),
('D2','PyTorch Compromised nightly dependency chain December 2022','https://pytorch.org/blog/compromised-nightly-dependency/'),
('D3','OpenSSF Package Manager Best Practices npm','https://github.com/ossf/package-manager-best-practices/blob/main/published/npm.md'),
('D4','npm Scopes','https://docs.npmjs.com/cli/v11/using-npm/scope/'),
('D5','npm ci','https://docs.npmjs.com/cli/v11/commands/npm-ci/'),
]
for key,title,url in refs:
 p(f'[{key}] {title}. {url}')
p('Nguồn trực tuyến được đối chiếu khi tổng hợp ngày 11/11/2026 đối với các nội dung Jenkins CLI, Script Console, phạm vi CVE GitLab, outbound requests, Runner, npm scope và sự cố PyTorch. Những nguồn khác được kế thừa từ tài liệu thành viên và giữ nhãn tương ứng trong phần nội dung.')

page('PHỤ LỤC A CHỈ MỤC BẰNG CHỨNG',1)
table(['Mục','Nguồn trong dự án','Nội dung'],[
('3.1','docs/bao-cao-thanh-vien/ báo cáo Script Console','6 ảnh được chọn từ báo cáo gốc; loại ảnh chứa mật khẩu khởi tạo'),
('3.1 (tái hiện)','labs/3.1-jenkins-script-console/evidence/','4 ảnh + log API thật: truy cập ẩn danh, exec Groovy, sau khi bật Authorization'),
('3.2','evidence/3.2-jenkins-cli-fileread/','before_patch.txt; after_patch.txt; hai log comparison'),
('3.3','docs/bao-cao-thanh-vien/ báo cáo GitLab SSRF','4 ảnh: phiên bản, webhook, phản hồi, log Nginx'),
('3.3 (tái hiện)','labs/3.3-gitlab-ssrf/evidence/','4 ảnh + log: baseline, PoC webhook, mitigation mạng, production.log GitLab'),
('3.4','docs/bao-cao-thanh-vien/ báo cáo Runner','15 hình; bảng đối chứng shell/Docker và biến'),
('3.4 (tái hiện)','labs/3.4-cicd-runner-secret/evidence/','5 ảnh + job trace thật: rò rỉ secret chéo project, Protected variable, Docker executor'),
('3.5','docs/bao-cao-thanh-vien/ báo cáo Dependency Confusion','8 hình; pipeline, registry, scope và lockfile'),
('3.5 (tái hiện)','labs/3.5-dependency-confusion/evidence/','log npm install/ci thật qua 2 registry Verdaccio; package-lock.json ghim nguồn')],widths=[2.3,6.1,7.8],caption='Bảng A.1 Chỉ mục nguồn bằng chứng')
h('Kiểm tra tính toàn vẹn')
p('Manifest đi kèm bản báo cáo lưu SHA-256 của tài liệu đầu vào và các log mới. Hash giúp nhận biết thay đổi tệp sau khi tổng hợp; nó không tự xác nhận tính đúng đắn của nội dung trong ảnh hoặc kết quả thực nghiệm.')
h('Phạm vi môi trường')
p('Các ảnh của thành viên được tạo trên các host và thời điểm khác nhau. Địa chỉ IP, hostname và phiên bản trong từng phần thuộc môi trường riêng. Không ghép log của hai môi trường thành một chuỗi khai thác liên tục. Log mới của mục 3.2 dùng tên container riêng để phân biệt trước và sau bản vá.')

page('PHỤ LỤC B QUY TRÌNH TÁI KIỂM THỬ AN TOÀN',1)
table(['Bước','Nội dung','Kết quả cần lưu'],[
('1','Xác nhận máy lab, phiên bản, mạng và tài khoản','Cấu hình Compose; phiên bản; quyền truy cập'),('2','Tạo marker giả và ghi trạng thái ban đầu','Nội dung marker; thời điểm; log đầu vào'),('3','Thực hiện phép thử đúng phạm vi','Phản hồi; log ở dịch vụ đích hoặc job'),('4','Thay bản vá hoặc cấu hình cần đánh giá','Thay đổi cụ thể; người thực hiện'),('5','Chạy lại cùng điều kiện','Cặp kết quả trước và sau'),('6','Kiểm tra tác vụ được phép','Luồng hợp lệ vẫn hoạt động'),('7','Khôi phục trạng thái an toàn','Dừng lab dễ tổn thương; thu hồi tài khoản thử')],widths=[1.4,8.1,6.7],caption='Bảng B.1 Quy trình tái kiểm thử')
paras('''Đối với Jenkins CLI, dùng file marker và hostname; không đọc file bí mật. Cần tải CLI client từ đúng instance và ghi rõ phương thức HTTP, WebSocket hoặc SSH được dùng. Tắt riêng cổng agent không phải phép kiểm tra đầy đủ cho việc vô hiệu hóa CLI.

Đối với SSRF, dịch vụ đích cần có marker đường dẫn riêng cho từng lần thử, log có thời điểm và không chứa dữ liệu thực. Không dùng địa chỉ metadata cloud thật hoặc dịch vụ nội bộ của tổ chức khác làm đích.

Đối với Runner, ghi nhận riêng file dùng chung và biến được cấp theo project. Job đối chứng chỉ in trạng thái set hoặc NOT set; dữ liệu marker không mang giá trị bí mật. Khi kiểm tra Docker executor, rà soát cả volume và quyền daemon thay vì chỉ kiểm tra sự vắng mặt của file.

Đối với dependency, chỉ publish package giả lên registry cục bộ. Khi thay nhiều biến cấu hình cùng lúc, cần ghi rõ để không quy mọi khác biệt cho một nguyên nhân duy nhất. Không phát hành package trùng tên của tổ chức thật lên registry công khai.''')

page('PHỤ LỤC C DANH MỤC HÌNH VÀ BẢNG',1)
h('Danh mục hình')
for t in FIGS:p(t)
h('Danh mục bảng')
for t in TABLES:p(t)

# Final consistency fixes inherited references and claims.
for pa in DOC.paragraphs:
 if 'Một ví dụ khác là sự cố PyTorch' in pa.text:
  pa.text='PyTorch công bố sự cố dependency torchtriton của bản nightly trên Linux cài qua pip trong khoảng 25–30/12/2022. Package trùng tên trên PyPI được chọn thay cho nguồn của PyTorch; bản stable không bị ảnh hưởng theo thông báo. Đây là sự cố thật để đối chiếu rủi ro nguồn dependency, không phải kết quả tái hiện của lab npm [D2].'
 if pa.text.startswith('Theo tài liệu GitLab'):
  pass
for shape in DOC.inline_shapes:
 try:
  dp=shape._inline.docPr
  if not dp.get('descr'):dp.set('descr','Ảnh minh chứng thực nghiệm CI CD được mô tả trong chú thích liền sau')
 except Exception:pass
settings=DOC.settings.element
upd=OxmlElement('w:updateFields');upd.set(qn('w:val'),'true');settings.append(upd)
final=OUT/'Bao_Cao_Tong_Hop_CICD_Security.docx'
DOC.save(final)
inputs=([ROOT/'docs/ke-hoach/KeHoach_CICD_Security.docx']
 +list((ROOT/'docs/bao-cao-thanh-vien').glob('*.docx'))
 +list((ROOT/'evidence/3.2-jenkins-cli-fileread').glob('*.txt'))
 +list((ROOT/'labs/3.1-jenkins-script-console/evidence').glob('*.txt'))
 +list((ROOT/'labs/3.3-gitlab-ssrf/evidence').glob('*.txt'))
 +list((ROOT/'labs/3.4-cicd-runner-secret/evidence').glob('*.txt')))
manifest={'generated_on':'2026-11-12','report':str(final.relative_to(ROOT)),'inputs':[{'path':str(f.relative_to(ROOT)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in inputs],'figures':len(FIGS),'tables':len(TABLES)}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
verification={
 'date':'2026-11-12',
 'figures':len(FIGS),'tables':len(TABLES),
 'docx_sha256':hashlib.sha256(final.read_bytes()).hexdigest(),
 'resolved_gaps':[
  'GitLab (3.3): bo sung bang chung sau xu ly (network segmentation), xac nhan bang production.log va access log dich',
  '3.1, 3.4, 3.5: da tai hien doc lap bang Docker that cua Le Dat, khong con chi dua vao anh muon cua thanh vien',
 ],
 'known_evidence_gaps':[
  'GitLab (3.3): bien phap da kiem thu la muc mang (network segmentation), chua phai ban va ung dung chinh thuc; lien he chinh xac voi CVE-2018-8801 van can doi chieu them',
  'Script Console (3.1): chua co doi chung tai khoan thuong (chi moi kiem tra an danh vs da dang nhap)',
  'Runner (3.4): chua ra soat rui ro Docker socket va cac tuy chon MR pipeline',
  'Dependency confusion (3.5): chua thu proxy/uplink hoac he sinh thai package khac ngoai npm',
 ],
}
(ROOT/'evidence/bao-cao-tong-hop/verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2))
print(final);print('figures',len(FIGS),'tables',len(TABLES))
