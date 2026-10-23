"""Record of where each policy source file came from (link + download date).

The manuscript cites these as documents of the issuing agency (issuer, title, date), with no URL.
The link and download date are kept here for provenance only. Download dates are local time (UTC+7)
from the Chrome download history (read 2026-10-09), matched on byte count and saved path. Fill them in this table and re-run, never in the CSV directly.
Writes Data/policy_sources/SOURCE_LINKS.csv (UTF-8 with BOM so Excel shows Thai).
"""
import csv
import hashlib

from _paths import BASE, out_path

SRC_DIR = BASE / "Data" / "policy_sources"

# (policy ID, manuscript ref no. or "", file name, issuer, url, download date, note)
ROWS = [
    ("P2a", "49", "ประกาศ กกพ. เชิญชวนการรับซื้อ Solar rooftop ภาคประชาชน พ.ศ. 2569.pdf", "ERC",
     "https://www.erc.or.th/web-upload/200xf869baf82be74c18cc110e974eea8d5c/tinymce/21-4763a2012e437a8e2cc87f4be44fa17e/Solar%20Rooftop%20%E0%B8%9B%E0%B8%A3%E0%B8%B0%E0%B8%8A%E0%B8%B2%E0%B8%8A%E0%B8%99%202569/%E0%B8%9B%E0%B8%A3%E0%B8%B0%E0%B8%81%E0%B8%B2%E0%B8%A8%20%E0%B8%81%E0%B8%81%E0%B8%9E.%20%E0%B9%80%E0%B8%8A%E0%B8%B4%E0%B8%8D%E0%B8%8A%E0%B8%A7%E0%B8%99%E0%B8%81%E0%B8%B2%E0%B8%A3%E0%B8%A3%E0%B8%B1%E0%B8%9A%E0%B8%8B%E0%B8%B7%E0%B9%89%E0%B8%AD%20Solar%20rooftop%20%E0%B8%A0%E0%B8%B2%E0%B8%84%E0%B8%9B%E0%B8%A3%E0%B8%B0%E0%B8%8A%E0%B8%B2%E0%B8%8A%E0%B8%99%20%E0%B8%9E.%E0%B8%A8.%202569.pdf",
     "2026-10-08 11:08", "Chrome download history"),
    ("P1", "50", "ERC_reg_community_solar_2569.pdf", "ERC",
     "https://www.erc.or.th/th/power-purchasing3/3505", "2026-10-08",
     "fetched by the analysis session from the PDF link on that page (full link in .url.txt)"),
    ("P1", "50", "ระเบียบ กกพ. ว่าด้วยการจัดหาไฟฟ้าจากโครงการโซลาร์ฟาร์มชุมชน (Community-based Solar Power Generation Project) พ.ศ. 2569.pdf",
     "ERC", "https://www.erc.or.th/web-upload/200xf869baf82be74c18cc110e974eea8d5c/tinymce/21-4763a2012e437a8e2cc87f4be44fa17e/%E0%B9%82%E0%B8%84%E0%B8%A3%E0%B8%87%E0%B8%81%E0%B8%B2%E0%B8%A3%E0%B9%82%E0%B8%8B%E0%B8%A5%E0%B8%B2%E0%B8%A3%E0%B9%8C%E0%B8%9F%E0%B8%B2%E0%B8%A3%E0%B9%8C%E0%B8%A1%E0%B8%8A%E0%B8%B8%E0%B8%A1%E0%B8%8A%E0%B8%99/%E0%B8%A3%E0%B8%B0%E0%B9%80%E0%B8%9A%E0%B8%B5%E0%B8%A2%E0%B8%9A%20%E0%B8%81%E0%B8%81%E0%B8%9E.%20%E0%B8%A7%E0%B9%88%E0%B8%B2%E0%B8%94%E0%B9%89%E0%B8%A7%E0%B8%A2%E0%B8%81%E0%B8%B2%E0%B8%A3%E0%B8%88%E0%B8%B1%E0%B8%94%E0%B8%AB%E0%B8%B2%E0%B9%84%E0%B8%9F%E0%B8%9F%E0%B9%89%E0%B8%B2%E0%B8%88%E0%B8%B2%E0%B8%81%E0%B9%82%E0%B8%84%E0%B8%A3%E0%B8%87%E0%B8%81%E0%B8%B2%E0%B8%A3%E0%B9%82%E0%B8%8B%E0%B8%A5%E0%B8%B2%E0%B8%A3%E0%B9%8C%E0%B8%9F%E0%B8%B2%E0%B8%A3%E0%B9%8C%E0%B8%A1%E0%B8%8A%E0%B8%B8%E0%B8%A1%E0%B8%8A%E0%B8%99%20(Community-based%20Solar%20Power%20Generation%20Project)%20%E0%B8%9E.%E0%B8%A8.%202569.pdf",
     "2026-10-08 10:29", "Chrome download history, byte-identical to the file above"),
    ("P9", "51", "04-ประกาศ กฟภ. ข้อกำหนดการเชื่อมต่อระบบโครงข่ายไฟฟ้าสำหรับผู้ผลิตไฟฟ้าโครงการโซลาร์ภาคประชาชน พ.ศ. 2569.pdf",
     "PEA", "https://ppim.pea.co.th/app/v1/project/getfile/6a435d59ed157096cb04fac1",
     "2026-10-08 10:58", "Chrome download history (PEA PPIM system)"),
    ("P4", "52", "พระราชบัญญัติการส่งเสริมการอนุรักษ์พลังงาน พ.ศ. 2535 แก้ไขเพิ่มเติม.pdf", "Royal Thai Government",
     "https://law.energy.go.th/web-upload/2xdccaaf3d7f6ae30ba6ae1459eaf3dd66/m_laws/6738/32732/file_download/321c780a71a4d75a23f74bbcb1b17a06.pdf",
     "2026-10-08 12:52", "Chrome download history, consolidated text, page https://law.energy.go.th/laws/detail/32732"),
    ("P4", "52", "พระราชบัญญัติการส่งเสริมการอนุรักษ์พลังงาน พ.ศ. 2550 (ฉบับที่ 2).pdf", "Royal Thai Government",
     "https://law.energy.go.th/web-upload/2xdccaaf3d7f6ae30ba6ae1459eaf3dd66/m_laws/6738/32732/file_download/54f5cf9f92db3e6bf444488397a3b665.pdf",
     "2026-10-08 12:51", "Chrome download history, amending Act No. 2, page https://law.energy.go.th/laws/detail/32732"),
    ("P7", "53", "เอกสารเผยแพร่-Ft-งวด-ก.ย-ธ.ค.69__Final.pdf", "ERC",
     "https://www.erc.or.th/web-upload/200xf869baf82be74c18cc110e974eea8d5c/tinymce/21-4763a2012e437a8e2cc87f4be44fa17e/FT/%E0%B9%80%E0%B8%AD%E0%B8%81%E0%B8%AA%E0%B8%B2%E0%B8%A3%E0%B9%80%E0%B8%9C%E0%B8%A2%E0%B9%81%E0%B8%9E%E0%B8%A3%E0%B9%88-Ft-%E0%B8%87%E0%B8%A7%E0%B8%94-%E0%B8%81.%E0%B8%A2-%E0%B8%98.%E0%B8%84.69__Final.pdf",
     "2026-10-08 10:53", "Chrome download history"),
    # register entries used in Supplementary S11 but not in the reference list
    ("P2", "", "การรับซื้อไฟฟ้าโครงการผลิตไฟฟ้าจากพลังงานแสงอาทิตย์ที่ติดตั้งบนหลังคา.pdf", "MEA",
     "https://static.mea.or.th/uploads/temp/63685261-7376-423b-aa0a-3460d925cb70/file_n3ua6dbs.pdf",
     "2026-10-08 10:22", "Chrome download history, MEA 'uploads/temp' path, the link may not be permanent"),
    ("P8", "", "05-ประกาศ กฟภ. รายละเอียดที่เกี่ยวข้องกับรับซื้อไฟฟ้า โครงการโซลาร์ภาคประชาชน พ.ศ. 2569.pdf", "PEA",
     "https://ppim.pea.co.th/app/v1/project/getfile/6a435d662e4a44098b071d7b",
     "2026-10-08 10:59", "Chrome download history (PEA PPIM system)"),
    ("P10", "", "01-ระเบียบ กฟภ. ว่าด้วยข้อกำหนดการใช้บริการระบบโครงข่ายไฟฟ้า พ.ศ. 2559.pdf", "PEA",
     "https://ppim.pea.co.th/app/v1/project/getfile/6a435d32ed157096cb04fab9",
     "2026-10-08 10:59", "Chrome download history (PEA PPIM system)"),
    ("P6", "", "ERC_hearing_progressive_tariff_2569.pdf", "ERC",
     "https://www.erc.or.th/web-upload/200xf869baf82be74c18cc110e974eea8d5c/202605/m_publichearing/8776/596/file_download/8550fc135fe068ed8e7ed7cf1eb760d2.pdf",
     "2026-10-08", "public-hearing file"),
    ("P11", "", "2.1 โครงการโซลาร์ฟาร์มชุมชน (Community-based Solar Power Generation Project).pdf", "EPPO",
     "https://reso.eppo.go.th/main", "2026-10-08 12:46",
     "Chrome download history, generated in-page (blob URL), so the page is the only stable link, context only"),
]

out = out_path("Data", "policy_sources", "SOURCE_LINKS.csv")
with open(out, "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["policy_id", "manuscript_ref", "file", "sha256", "issuer", "url", "download_date", "note"])
    for pid, ref, name, issuer, url, date, note in ROWS:
        p = SRC_DIR / name
        assert p.exists(), name
        w.writerow([pid, ref, name, hashlib.sha256(p.read_bytes()).hexdigest(), issuer, url, date, note])

listed = {r[2] for r in ROWS}
unlisted = [p.name for p in SRC_DIR.glob("*.pdf") if p.name not in listed]
assert not unlisted, unlisted
todo = [r for r in ROWS if not r[4] or not r[5]]
print(f"{out.name}: {len(ROWS)} files, {len(todo)} missing url or download date")
