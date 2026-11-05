import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
import re
from datetime import datetime
import os
import sqlite3
import io
import time
import streamlit.components.v1 as components

# Konfigurasi halaman
st.set_page_config(page_title="Dashboard Laporan Keuangan", layout="wide")

# Konfigurasi Tesseract OCR (Sesuaikan path jika diperlukan di komputer Anda)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Konfigurasi Folder & Database
UPLOAD_FOLDER = "uploaded_notas"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

DB_NAME = "keuangan.db"

# ----------------------------------------------------
# 1. Inisialisasi Database SQLite
# ----------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transaksi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file TEXT,
            tanggal TEXT,
            status TEXT,
            uraian TEXT,
            nilai REAL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ----------------------------------------------------
# 2. Fungsi Helper untuk Database
# ----------------------------------------------------
def get_data_from_db():
    init_db()
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM transaksi", conn)
    conn.close()
    return df

def insert_to_db(file, tanggal, status, uraian, nilai):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO transaksi (file, tanggal, status, uraian, nilai)
        VALUES (?, ?, ?, ?, ?)
    ''', (file, tanggal, status, uraian, nilai))
    conn.commit()
    conn.close()

def update_in_db(id_transaksi, file, tanggal, status, uraian, nilai):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE transaksi 
        SET file = ?, tanggal = ?, status = ?, uraian = ?, nilai = ?
        WHERE id = ?
    ''', (file, tanggal, status, uraian, nilai, id_transaksi))
    conn.commit()
    conn.close()

def delete_from_db(id_transaksi):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM transaksi WHERE id = ?', (id_transaksi,))
    conn.commit()
    conn.close()

# ----------------------------------------------------
# 3. Fungsi OCR 100% Dinamis
# ----------------------------------------------------
def ocr_nota(image, filename=""):
    parsed_date = datetime.now().date()
    nama_toko = ""
    items_list = []
    nilai = 0.0
    text = ""

    gray_image = image.convert('L')
    configs = ['--oem 3 --psm 6', '--oem 3 --psm 3', '--oem 3 --psm 4']
    for cfg in configs:
        try:
            current_text = pytesseract.image_to_string(gray_image, lang='ind+eng', config=cfg)
            if len(current_text.strip()) > len(text.strip()):
                text = current_text
        except:
            continue
        time.sleep(0.05)

    lines = [line.strip() for line in text.split('\n') if line.strip()]

    for line in lines[:5]:
        line_clean = line.strip()
        if len(line_clean) > 2 and not any(kw in line_clean.lower() for kw in ['nota', 'tgl', 'tanggal', 'jl.', 'jalan', 'telp', 'faktur', 'kontan']):
            nama_toko = line_clean
            break
    if not nama_toko and lines:
        nama_toko = lines[0]

    bulan_dict = {
        'januari': '01', 'februari': '02', 'maret': '03', 'april': '04', 
        'mei': '05', 'juni': '06', 'juli': '07', 'agustus': '08', 
        'september': '09', 'oktober': '10', 'november': '11', 'desember': '12',
        'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'jun': '06', 
        'jul': '07', 'agu': '08', 'sep': '09', 'okt': '10', 'nov': '11', 'des': '12'
    }

    date_found = False
    for line in lines:
        line_lower = line.lower()
        for b_name, b_num in bulan_dict.items():
            if b_name in line_lower:
                match_txt = re.search(r'(\d{1,2})\s*[-]?\s*' + b_name + r'\s*[-]?\s*(\d{4})', line_lower)
                if match_txt:
                    day, year = match_txt.groups()
                    try:
                        parsed_date = datetime.strptime(f"{year}-{b_num}-{int(day):02d}", '%Y-%m-%d').date()
                        date_found = True
                        break
                    except:
                        pass
        if date_found:
            break

    if not date_found:
        for line in lines:
            date_match = re.search(r'(\d{4}[-/.]\d{2}[-/.]\d{2})|(\d{2}[-/.]\d{2}[-/.]\d{4})', line)
            if date_match:
                raw_date = date_match.group(0).replace('/', '-').replace('.', '-')
                try:
                    parts = raw_date.split('-')
                    if len(parts[0]) == 4:
                        parsed_date = datetime.strptime(raw_date, '%Y-%m-%d').date()
                    else:
                        parsed_date = datetime.strptime(raw_date, '%d-%m-%Y').date()
                    date_found = True
                    break
                except:
                    pass

    for line in lines:
        line_lower = line.lower()
        ignore_keywords = [
            'nota', 'tgl', 'tanggal', 'alamat', 'telp', 'kepada', 'pemesan', 
            'kasir', 'total', 'jumlah', 'tunai', 'kembali', 'subtotal', 'sub total', 
            'lunas', 'terimakasih', 'sisa', 'perhatian', 'barangnya', 'harga', 'banyak'
        ]
        if any(kw in line_lower for kw in ignore_keywords):
            continue
        if len(line) > 3 and not re.match(r'^[\d\.,\s]+$', line):
            if line.lower() != nama_toko.lower():
                items_list.append(line)

    if items_list:
        uraian = f"{nama_toko} - " + ", ".join(items_list[:4]) if nama_toko else ", ".join(items_list[:4])
    else:
        uraian = f"{nama_toko} - Pembelian Barang" if nama_toko else "Pembelian Barang"

    found_total = False
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if 'total' in line_lower or 'jumlah' in line_lower:
            search_window = " ".join(lines[max(0, i-1):min(len(lines), i+2)])
            amounts = re.findall(r'(?:Rp\.?\s*)?(\d{1,3}(?:\.\d{3})+|\d+)', search_window)
            valid_amounts = []
            for val in amounts:
                clean_val = val.replace('.', '').replace(',', '')
                if clean_val.isdigit() and int(clean_val) >= 100:
                    valid_amounts.append(int(clean_val))
            if valid_amounts:
                nilai = float(max(valid_amounts))
                found_total = True
                break

    if not found_total or nilai == 0.0:
        bottom_lines = lines[len(lines)//2:] if len(lines) > 4 else lines
        all_amounts = []
        for line in bottom_lines:
            amounts = re.findall(r'(?:Rp\.?\s*)?(\d{1,3}(?:\.\d{3})+|\d+)', line)
            for val in amounts:
                clean_val = val.replace('.', '').replace(',', '')
                if clean_val.isdigit() and int(clean_val) >= 100:
                    all_amounts.append(int(clean_val))
        if all_amounts:
            nilai = float(max(all_amounts))

    return parsed_date, uraian, float(nilai), True

# ----------------------------------------------------
# 4. Fungsi Dialog Popup untuk Menampilkan Nota
# ----------------------------------------------------
@st.dialog("📄 Preview File Nota")
def show_nota_popup(filename):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if filename != "Manual Input" and os.path.exists(file_path):
        image = Image.open(file_path)
        img_width = st.slider("Sesuaikan Lebar Gambar (Pixel)", min_value=200, max_value=800, value=400, step=50)
        st.image(image, width=img_width, caption=filename)
    else:
        st.warning("Tidak ada file gambar fisik yang di-upload untuk transaksi ini (Input Manual).")
    
    if st.button("Tutup"):
        st.rerun()

# ----------------------------------------------------
# 5. Kelola State untuk Mode Edit & Form Reset
# ----------------------------------------------------
if 'edit_id' not in st.session_state:
    st.session_state.edit_id = None

if 'form_status' not in st.session_state:
    st.session_state.form_status = "Pengeluaran"
if 'form_tanggal' not in st.session_state:
    st.session_state.form_tanggal = datetime.now().date()
if 'form_uraian' not in st.session_state:
    st.session_state.form_uraian = ""
if 'form_nilai' not in st.session_state:
    st.session_state.form_nilai = 0.0
if 'form_file' not in st.session_state:
    st.session_state.form_file = "Manual Input"

# ----------------------------------------------------
# 6. Sidebar Form Input / Edit / Upload Nota
# ----------------------------------------------------
st.sidebar.header("📝 Form Transaksi Keuangan")

edit_data = None
if st.session_state.edit_id is not None:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT file, tanggal, status, uraian, nilai FROM transaksi WHERE id = ?", (st.session_state.edit_id,))
    edit_data = cursor.fetchone()
    conn.close()

uploaded_file = st.sidebar.file_uploader("Upload File Nota (PNG, JPG, JPEG)", type=["png", "jpg", "jpeg"])

if edit_data and uploaded_file is None:
    st.session_state.form_file = edit_data[0]
    st.session_state.form_tanggal = datetime.strptime(edit_data[1], '%Y-%m-%d').date() if edit_data[1] else datetime.now().date()
    st.session_state.form_status = edit_data[2] if edit_data[2] else "Pengeluaran"
    st.session_state.form_uraian = edit_data[3]
    st.session_state.form_nilai = edit_data[4]
    st.sidebar.info(f"Mode Edit untuk Transaksi ID: {st.session_state.edit_id}")
elif uploaded_file is not None:
    saved_file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.name)
    with open(saved_file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    st.session_state.form_file = uploaded_file.name
    image = Image.open(uploaded_file)
    st.sidebar.image(image, caption=f"Tersimpan: {st.session_state.form_file}", use_container_width=True)
    
    with st.spinner('Membaca data nota secara dinamis dari gambar...'):
        raw_ocr_text = pytesseract.image_to_string(image.convert('L'), lang='ind+eng', config='--oem 3 --psm 6')
        ocr_date, ocr_uraian, ocr_nilai, _ = ocr_nota(image, filename=uploaded_file.name)
        
        if ocr_date: st.session_state.form_tanggal = ocr_date
        if ocr_uraian: st.session_state.form_uraian = ocr_uraian
        if ocr_nilai > 0: st.session_state.form_nilai = ocr_nilai
        
        st.sidebar.success("OCR berhasil membaca data nota!")
        st.sidebar.markdown("### 📄 Hasil Scan OCR Keseluruhan:")
        st.sidebar.code(raw_ocr_text if raw_ocr_text.strip() else "(Tidak ada teks terdeteksi)", language="text")

with st.sidebar.form(key='form_nota'):
    status_input = st.selectbox("Status Transaksi", ["Pengeluaran", "Pemasukan"], index=0 if st.session_state.form_status == "Pengeluaran" else 1)
    tanggal_input = st.date_input("Tanggal", value=st.session_state.form_tanggal)
    uraian_input = st.text_input("Uraian", value=st.session_state.form_uraian, placeholder="Misal: Nama Toko - Barang")
    nilai_input = st.number_input("Nilai (Rp)", value=float(st.session_state.form_nilai), min_value=0.0, step=1000.0)
    
    submit_label = "Update Transaksi" if st.session_state.edit_id is not None else "Simpan Transaksi"
    
    col_sub1, col_sub2 = st.columns(2)
    with col_sub1:
        submit_button = st.form_submit_button(label=submit_label)
    with col_sub2:
        clear_button = st.form_submit_button(label="Clear Form")

if clear_button:
    st.session_state.edit_id = None
    st.session_state.form_status = "Pengeluaran"
    st.session_state.form_tanggal = datetime.now().date()
    st.session_state.form_uraian = ""
    st.session_state.form_nilai = 0.0
    st.session_state.form_file = "Manual Input"
    st.rerun()

if submit_button:
    if st.session_state.edit_id is not None:
        update_in_db(
            id_transaksi=st.session_state.edit_id,
            file=st.session_state.form_file,
            tanggal=str(tanggal_input),
            status=status_input,
            uraian=uraian_input if uraian_input else "Bahan Konstruksi",
            nilai=nilai_input
        )
        st.sidebar.success(f"Transaksi ID {st.session_state.edit_id} berhasil diupdate!")
        st.session_state.edit_id = None
    else:
        insert_to_db(
            file=st.session_state.form_file,
            tanggal=str(tanggal_input),
            status=status_input,
            uraian=uraian_input if uraian_input else "Bahan Konstruksi",
            nilai=nilai_input
        )
        st.sidebar.success("Transaksi berhasil disimpan ke database!")
    
    st.session_state.form_status = "Pengeluaran"
    st.session_state.form_tanggal = datetime.now().date()
    st.session_state.form_uraian = ""
    st.session_state.form_nilai = 0.0
    st.session_state.form_file = "Manual Input"
    st.rerun()

if st.session_state.edit_id is not None:
    if st.sidebar.button("Batal Edit"):
        st.session_state.edit_id = None
        st.rerun()

# ----------------------------------------------------
# 7. Main Dashboard UI
# ----------------------------------------------------
st.markdown("<h2 style='font-size: 24px; font-weight: bold;'>📊 Dashboard Laporan Keuangan</h2>", unsafe_allow_html=True)

df = get_data_from_db()

if not df.empty:
    df = df.rename(columns={'id': 'No', 'file': 'File', 'tanggal': 'Tanggal', 'status': 'Status', 'uraian': 'Uraian', 'nilai': 'Nilai'})
    df['Tanggal'] = pd.to_datetime(df['Tanggal'], errors='coerce')
    df['Tahun'] = df['Tanggal'].dt.year.astype('Int64').astype(str)
    df['Bulan_Tahun'] = df['Tanggal'].dt.to_period('M').astype(str)

    # Filter Periode Bulan
    st.markdown("### 🔍 Filter Periode & Status")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        available_months = ['Semua Bulan'] + sorted(df['Bulan_Tahun'].dropna().unique().tolist(), reverse=True)
        selected_month = st.selectbox("Pilih Periode Bulan", available_months)
    with col_f2:
        # FILTER STATUS PENGELUARAN / PEMASUKAN
        selected_status_filter = st.selectbox("Filter Status Transaksi", ["Semua Status", "Pemasukan", "Pengeluaran"])

    if selected_month != 'Semua Bulan':
        filtered_df = df[df['Bulan_Tahun'] == selected_month].copy()
    else:
        filtered_df = df.copy()

    # Terapkan filter status tambahan untuk tabel
    if selected_status_filter != "Semua Status":
        table_base_df = filtered_df[filtered_df['Status'] == selected_status_filter].copy()
    else:
        table_base_df = filtered_df.copy()

    st.markdown("---")

    # Metrik Atas
    col1, col2, col3, col4 = st.columns(4)
    total_transaksi = len(filtered_df)
    total_pengeluaran = filtered_df[filtered_df['Status'] == 'Pengeluaran']['Nilai'].sum() if not filtered_df.empty else 0
    total_pemasukan = filtered_df[filtered_df['Status'] == 'Pemasukan']['Nilai'].sum() if not filtered_df.empty else 0
    saldo_terakhir = total_pemasukan - total_pengeluaran

    col1.metric("Total Transaksi", f"{total_transaksi}")
    col2.metric("Total Pengeluaran", f"Rp {total_pengeluaran:,.0f}")
    col3.metric("Total Pemasukan", f"Rp {total_pemasukan:,.0f}")
    col4.metric("Saldo Terakhir", f"Rp {saldo_terakhir:,.0f}")

    st.markdown("---")

    st.markdown("<h3 style='font-size: 18px;'>📋 Tabel Data Keuangan</h3>", unsafe_allow_html=True)
    
    search_query = st.text_input("🔍 Cari transaksi (Uraian / Nama File)...", placeholder="Ketik untuk mencari...")
    
    if search_query:
        mask = (
            table_base_df['Uraian'].str.contains(search_query, case=False, na=False) | 
            table_base_df['File'].str.contains(search_query, case=False, na=False)
        )
        table_df = table_base_df[mask]
    else:
        table_df = table_base_df

    col_act1, col_act2 = st.columns([1, 4])
    with col_act1:
        output = io.BytesIO()
        import openpyxl
        from openpyxl.drawing.image import Image as XLImage
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Laporan Keuangan'
        
        headers = ['No', 'Status', 'Uraian', 'Tanggal', 'Nilai (Rp)', 'Nama File', 'Gambar Nota']
        ws.append(headers)
        
        ws.column_dimensions['A'].width = 6
        ws.column_dimensions['B'].width = 15
        ws.column_dimensions['C'].width = 30
        ws.column_dimensions['D'].width = 15
        ws.column_dimensions['E'].width = 18
        ws.column_dimensions['F'].width = 20
        ws.column_dimensions['G'].width = 22
        
        for _, r in table_df.iterrows():
            tgl_str = r['Tanggal'].strftime('%Y-%m-%d') if pd.notnull(r['Tanggal']) else "-"
            row_num = ws.max_row + 1
            
            ws.cell(row=row_num, column=1, value=r['No'])
            ws.cell(row=row_num, column=2, value=str(r['Status']))
            ws.cell(row=row_num, column=3, value=str(r['Uraian']))
            ws.cell(row=row_num, column=4, value=tgl_str)
            ws.cell(row=row_num, column=5, value=r['Nilai'])
            ws.cell(row=row_num, column=6, value=str(r['File']))
            
            ws.row_dimensions[row_num].height = 80
            
            filename = r['File']
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            if filename != "Manual Input" and os.path.exists(file_path):
                try:
                    img = XLImage(file_path)
                    img.width = 90
                    img.height = 70
                    cell_loc = f"G{row_num}"
                    ws.add_image(img, cell_loc)
                except Exception as e:
                    pass
                    
        wb.save(output)
        excel_data = output.getvalue()

        st.download_button(
            label="📥 Export ke Excel (+ Gambar Nota)",
            data=excel_data,
            file_name="Laporan_Keuangan_Dengan_Nota.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    with col_act2:
        if st.button("🖨️ Cetak / Simpan PDF Laporan"):
            print_html = f"""
            <html>
                <head>
                    <title>Laporan Keuangan</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 20px; }}
                        h2 {{ text-align: center; color: #333; }}
                        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 12px; }}
                        th {{ background-color: #2b5c8f; color: white; }}
                        .total {{ font-weight: bold; text-align: right; margin-top: 15px; }}
                    </style>
                </head>
                <body>
                    <h2>Laporan Keuangan Periode: {selected_month}</h2>
                    <table>
                        <tr>
                            <th>No</th>
                            <th>Status</th>
                            <th>Uraian</th>
                            <th>Tanggal</th>
                            <th>Nilai</th>
                            <th>File</th>
                        </tr>
            """
            for _, r in table_df.iterrows():
                tgl = r['Tanggal'].strftime('%Y-%m-%d') if pd.notnull(r['Tanggal']) else "-"
                print_html += f"<tr><td>{r['No']}</td><td>{r['Status']}</td><td>{r['Uraian']}</td><td>{tgl}</td><td>Rp {r['Nilai']:,.0f}</td><td>{r['File']}</td></tr>"
            
            print_html += f"""
                    </table>
                    <p class="total">Total Pemasukan: Rp {total_pemasukan:,.0f} | Total Pengeluaran: Rp {total_pengeluaran:,.0f}</p>
                    <p class="total">Saldo Terakhir: Rp {saldo_terakhir:,.0f}</p>
                    <script>
                        window.onload = function() {{ window.print(); }}
                    </script>
                </body>
            </html>
            """
            components.html(print_html, height=0)

    st.markdown("")

    ITEMS_PER_PAGE = 15
    total_items = len(table_df)
    total_pages = max(1, (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

    if 'page_num' not in st.session_state:
        st.session_state.page_num = 1

    if st.session_state.page_num > total_pages:
        st.session_state.page_num = 1

    if total_items > ITEMS_PER_PAGE:
        col_p1, col_p2, col_p3 = st.columns([1, 2, 1])
        with col_p2:
            page_choice = st.selectbox(
                f"Halaman (Total {total_items} data)", 
                range(1, total_pages + 1), 
                index=st.session_state.page_num - 1,
                key="pagination_select"
            )
            st.session_state.page_num = page_choice

    start_idx = (st.session_state.page_num - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    paginated_df = table_df.iloc[start_idx:end_idx]

    # TABEL DATA UTAMA
    h1, h2, h3, h4, h5, h6, h7 = st.columns([0.5, 1.2, 2.0, 1.1, 1.3, 1.1, 1.4])
    h1.markdown("**No**")
    h2.markdown("**Status**")
    h3.markdown("**Uraian**")
    h4.markdown("**Tanggal**")
    h5.markdown("**Nilai**")
    h6.markdown("**File**")
    h7.markdown("**Aksi**")
    st.divider()

    if not paginated_df.empty:
        for index, row in paginated_df.iterrows():
            c1, c2, c3, c4, c5, c6, c7 = st.columns([0.5, 1.2, 2.0, 1.1, 1.3, 1.1, 1.4])
            
            c1.write(str(row['No']))
            
            status_val = str(row['Status'])
            if status_val == "Pemasukan":
                c2.markdown(f"<span style='color: green; font-weight: bold;'>{status_val}</span>", unsafe_allow_html=True)
            else:
                c2.markdown(f"<span style='color: red; font-weight: bold;'>{status_val}</span>", unsafe_allow_html=True)
                
            c3.write(str(row['Uraian']))
            
            tgl_str = row['Tanggal'].strftime('%Y-%m-%d') if pd.notnull(row['Tanggal']) else "-"
            c4.write(tgl_str)
            c5.write(f"Rp {row['Nilai']:,.0f}")
            
            with c6:
                if st.button("📁 Buka", key=f"btn_file_{row['No']}"):
                    show_nota_popup(row['File'])
            
            with c7:
                col_edit, col_del = st.columns(2)
                with col_edit:
                    if st.button("✏️", key=f"edit_{row['No']}", help="Edit Data"):
                        st.session_state.edit_id = int(row['No'])
                        st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"del_{row['No']}", help="Hapus Data"):
                        delete_from_db(int(row['No']))
                        st.success(f"Data ID {row['No']} berhasil dihapus!")
                        st.rerun()
            
            st.divider()
    else:
        st.info("Tidak ada data yang cocok dengan pencarian atau filter.")

    st.markdown("---")

    # ----------------------------------------------------
    # GRAFIK 3D DENGAN TOOLTIP / LABEL NILAI DI ATAS BATANG
    # ----------------------------------------------------
    st.markdown("<h3 style='font-size: 18px;'>📈 Grafik Tren Keuangan Tahunan</h3>", unsafe_allow_html=True)
    available_years = sorted(df['Tahun'].dropna().unique().tolist(), reverse=True)
    if available_years:
        selected_graph_year = st.selectbox("Pilih Tahun untuk Grafik", available_years, key="graph_year_select")
        graph_df = df[df['Tahun'] == selected_graph_year].copy()
    else:
        graph_df = df.copy()

    if not graph_df.empty:
        monthly_data = graph_df.groupby([graph_df['Tanggal'].dt.to_period('M'), 'Status'])['Nilai'].sum().unstack(fill_value=0).reset_index()
        monthly_data['Bulan_Str'] = monthly_data['Tanggal'].dt.strftime('%b')
        
        fig = plt.figure(figsize=(8, 3.5))
        ax = fig.add_subplot(projection='3d')
        
        months = monthly_data['Bulan_Str']
        xpos = range(len(months))
        ypos_pemasukan = 0
        ypos_pengeluaran = 1
        
        zpos = [0] * len(months)
        dx = 0.35
        dy = 0.35
        
        dz_masuk = monthly_data['Pemasukan'] if 'Pemasukan' in monthly_data.columns else [0]*len(months)
        dz_keluar = monthly_data['Pengeluaran'] if 'Pengeluaran' in monthly_data.columns else [0]*len(months)

        # Gambar bar 3D
        ax.bar3d(xpos, ypos_pemasukan, zpos, dx, dy, dz_masuk, color='#00F5D4', alpha=0.85, shade=True, label='Pemasukan')
        ax.bar3d(xpos, ypos_pengeluaran, zpos, dx, dy, dz_keluar, color='#F72585', alpha=0.85, shade=True, label='Pengeluaran')

        # TOOLTIP / ANOTASI NILAI DI ATAS MASING-MASING BATANG GRAFIK
        for i, val in enumerate(dz_masuk):
            if val > 0:
                ax.text(xpos[i], ypos_pemasukan, val + (max(max(dz_masuk), max(dz_keluar))*0.05), f"{val:,.0f}", fontsize=6, color='black', ha='center', weight='bold')

        for i, val in enumerate(dz_keluar):
            if val > 0:
                ax.text(xpos[i], ypos_pengeluaran, val + (max(max(dz_masuk), max(dz_keluar))*0.05), f"{val:,.0f}", fontsize=6, color='black', ha='center', weight='bold')

        fig.patch.set_facecolor('none')
        ax.set_facecolor('none')
        
        ax.xaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
        ax.yaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
        ax.zaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
        
        ax.xaxis._axinfo['grid']['color'] = (0.5, 0.5, 0.5, 0.2)
        ax.yaxis._axinfo['grid']['color'] = (0.5, 0.5, 0.5, 0.2)
        ax.zaxis._axinfo['grid']['color'] = (0.5, 0.5, 0.5, 0.2)

        ax.set_xticks(list(xpos))
        ax.set_xticklabels(months, fontsize=8)
        ax.set_yticks([0.2, 1.2])
        ax.set_yticklabels(['Masuk', 'Keluar'], fontsize=8)
        ax.tick_params(axis='z', labelsize=8)
        
        from matplotlib.patheffects import Normal, Stroke
        stroke_effect = [Stroke(linewidth=1.5, foreground='white'), Normal()]

        for txt in ax.get_xticklabels() + ax.get_yticklabels() + ax.get_zticklabels():
            txt.set_path_effects(stroke_effect)
            txt.set_color('#222222')

        ax.set_zlabel("Nilai (Rp)", fontsize=9)
        ax.legend(loc='upper right', fontsize=8, facecolor='none', edgecolor='none')

        plt.tight_layout()
        st.pyplot(fig, use_container_width=True)
    else:
        st.info("Tidak ada data transaksi pada tahun tersebut untuk ditampilkan ke grafik.")
else:
    st.info("Tabel transaksi masih kosong. Silakan upload nota atau input data melalui sidebar.")
