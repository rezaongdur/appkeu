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
            uraian TEXT,
            nilai REAL
        )
    ''')
    conn.commit()
    conn.close()

# Jalankan inisialisasi tabel di awal
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

def insert_to_db(file, tanggal, uraian, nilai):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO transaksi (file, tanggal, uraian, nilai)
        VALUES (?, ?, ?, ?)
    ''', (file, tanggal, uraian, nilai))
    conn.commit()
    conn.close()

def update_in_db(id_transaksi, file, tanggal, uraian, nilai):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE transaksi 
        SET file = ?, tanggal = ?, uraian = ?, nilai = ?
        WHERE id = ?
    ''', (file, tanggal, uraian, nilai, id_transaksi))
    conn.commit()
    conn.close()

def delete_from_db(id_transaksi):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM transaksi WHERE id = ?', (id_transaksi,))
    conn.commit()
    conn.close()

# ----------------------------------------------------
# 3. Fungsi OCR 100% Dinamis (Murni Ekstraksi Gambar)
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
    cursor.execute("SELECT file, tanggal, uraian, nilai FROM transaksi WHERE id = ?", (st.session_state.edit_id,))
    edit_data = cursor.fetchone()
    conn.close()

uploaded_file = st.sidebar.file_uploader("Upload File Nota (PNG, JPG, JPEG)", type=["png", "jpg", "jpeg"])

if edit_data and uploaded_file is None:
    st.session_state.form_file = edit_data[0]
    st.session_state.form_tanggal = datetime.strptime(edit_data[1], '%Y-%m-%d').date() if edit_data[1] else datetime.now().date()
    st.session_state.form_uraian = edit_data[2]
    st.session_state.form_nilai = edit_data[3]
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
    tanggal_input = st.date_input("Tanggal", value=st.session_state.form_tanggal)
    uraian_input = st.text_input("Uraian", value=st.session_state.form_uraian, placeholder="Misal: Nama Toko - Barang")
    nilai_input = st.number_input("Nilai (Rp)", value=float(st.session_state.form_nilai), min_value=0.0, step=1000.0)
    
    submit_label = "Update Transaksi" if st.session_state.edit_id is not None else "Simpan Transaksi"
    
    # Membuat 2 kolom untuk tombol Simpan/Update dan Clear Form
    col_sub1, col_sub2 = st.columns(2)
    with col_sub1:
        submit_button = st.form_submit_button(label=submit_label)
    with col_sub2:
        clear_button = st.form_submit_button(label="Clear Form")

# Logika ketika tombol "Clear Form" ditekan
if clear_button:
    st.session_state.edit_id = None
    st.session_state.form_tanggal = datetime.now().date()
    st.session_state.form_uraian = ""
    st.session_state.form_nilai = 0.0
    st.session_state.form_file = "Manual Input"
    st.rerun()

# Logika ketika tombol "Simpan Transaksi" / "Update Transaksi" ditekan
if submit_button:
    if st.session_state.edit_id is not None:
        update_in_db(
            id_transaksi=st.session_state.edit_id,
            file=st.session_state.form_file,
            tanggal=str(tanggal_input),
            uraian=uraian_input if uraian_input else "Bahan Konstruksi",
            nilai=nilai_input
        )
        st.sidebar.success(f"Transaksi ID {st.session_state.edit_id} berhasil diupdate!")
        st.session_state.edit_id = None
    else:
        insert_to_db(
            file=st.session_state.form_file,
            tanggal=str(tanggal_input),
            uraian=uraian_input if uraian_input else "Bahan Konstruksi",
            nilai=nilai_input
        )
        st.sidebar.success("Transaksi berhasil disimpan ke database!")
    
    # Reset form input menjadi kosong / default setelah disimpan
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
st.title("📊 Dashboard Laporan Keuangan")

df = get_data_from_db()

if not df.empty:
    df = df.rename(columns={'id': 'No', 'file': 'File', 'tanggal': 'Tanggal', 'uraian': 'Uraian', 'nilai': 'Nilai'})
    df['Tanggal'] = pd.to_datetime(df['Tanggal'], errors='coerce')
    df['Tahun'] = df['Tanggal'].dt.year.astype('Int64').astype(str)

    # Filter Tahun untuk Grafik
    st.markdown("### 📈 Grafik Tren Pengeluaran Tahunan")
    available_years = sorted(df['Tahun'].dropna().unique().tolist(), reverse=True)
    if available_years:
        selected_graph_year = st.selectbox("Pilih Tahun untuk Grafik", available_years, key="graph_year_select")
        graph_df = df[df['Tahun'] == selected_graph_year].copy()
    else:
        graph_df = df.copy()

    if not graph_df.empty:
        graph_df['Bulan'] = graph_df['Tanggal'].dt.strftime('%B')
        monthly_data = graph_df.groupby(graph_df['Tanggal'].dt.to_period('M'))['Nilai'].sum().reset_index()
        monthly_data['Bulan_Str'] = monthly_data['Tanggal'].dt.strftime('%b %Y')
        
        fig, ax = plt.subplots(figsize=(10, 4.2))
        x = monthly_data['Bulan_Str']
        y = monthly_data['Nilai']

        ax.plot(x, y, color='#f6ad55', marker='o', markerfacecolor='#ed8936', markeredgecolor='#2d3748', markersize=8, linewidth=2.5)
        ax.fill_between(x, y, color='#fbd38d', alpha=0.4)

        ax.set_facecolor('#ffffff')
        fig.patch.set_facecolor('#ffffff')
        ax.grid(axis='x', linestyle='--', alpha=0.5)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#cbd5e0')
        ax.spines['bottom'].set_color('#cbd5e0')
        
        ax.set_ylabel("Nilai (Rp)", fontsize=10, color='#4a5568')
        ax.tick_params(axis='x', rotation=30, labelsize=9)
        ax.tick_params(axis='y', labelsize=9)

        plt.tight_layout()
        st.pyplot(fig, use_container_width=True)
    else:
        st.info("Tidak ada data transaksi pada tahun tersebut untuk ditampilkan ke grafik.")

    st.markdown("---")

    # Filter Bulan untuk Tabel
    df['Bulan_Tahun'] = df['Tanggal'].dt.to_period('M').astype(str)
    st.markdown("### 🔍 Filter Tabel Berdasarkan Periode Bulan")
    available_months = ['Semua Bulan'] + sorted(df['Bulan_Tahun'].dropna().unique().tolist(), reverse=True)
    selected_month = st.selectbox("Pilih Periode Bulan", available_months)

    if selected_month != 'Semua Bulan':
        filtered_df = df[df['Bulan_Tahun'] == selected_month].copy()
    else:
        filtered_df = df.copy()

    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    total_transaksi = len(filtered_df)
    total_pengeluaran = filtered_df['Nilai'].sum() if not filtered_df.empty else 0
    rata_rata = filtered_df['Nilai'].mean() if not filtered_df.empty else 0

    col1.metric("Total Transaksi", f"{total_transaksi}")
    col2.metric("Total Pengeluaran", f"Rp {total_pengeluaran:,.0f}")
    col3.metric("Rata-rata Pengeluaran", f"Rp {rata_rata:,.0f}")

    st.markdown("---")

    st.subheader("📋 Tabel Data Keuangan")
    
    search_query = st.text_input("🔍 Cari transaksi (Uraian / Nama File)...", placeholder="Ketik untuk mencari...")
    
    if search_query:
        mask = (
            filtered_df['Uraian'].str.contains(search_query, case=False, na=False) | 
            filtered_df['File'].str.contains(search_query, case=False, na=False)
        )
        table_df = filtered_df[mask]
    else:
        table_df = filtered_df

    col_act1, col_act2 = st.columns([1, 4])
    with col_act1:
        output = io.BytesIO()
        import openpyxl
        from openpyxl.drawing.image import Image as XLImage
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Laporan Keuangan'
        
        headers = ['No', 'Uraian', 'Tanggal', 'Nilai (Rp)', 'Nama File', 'Gambar Nota']
        ws.append(headers)
        
        ws.column_dimensions['A'].width = 6
        ws.column_dimensions['B'].width = 35
        ws.column_dimensions['C'].width = 15
        ws.column_dimensions['D'].width = 18
        ws.column_dimensions['E'].width = 20
        ws.column_dimensions['F'].width = 22
        
        for _, r in table_df.iterrows():
            tgl_str = r['Tanggal'].strftime('%Y-%m-%d') if pd.notnull(r['Tanggal']) else "-"
            row_num = ws.max_row + 1
            
            ws.cell(row=row_num, column=1, value=r['No'])
            ws.cell(row=row_num, column=2, value=str(r['Uraian']))
            ws.cell(row=row_num, column=3, value=tgl_str)
            ws.cell(row=row_num, column=4, value=r['Nilai'])
            ws.cell(row=row_num, column=5, value=str(r['File']))
            
            ws.row_dimensions[row_num].height = 80
            
            filename = r['File']
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            if filename != "Manual Input" and os.path.exists(file_path):
                try:
                    img = XLImage(file_path)
                    img.width = 90
                    img.height = 70
                    cell_loc = f"F{row_num}"
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
                            <th>Uraian</th>
                            <th>Tanggal</th>
                            <th>Nilai</th>
                            <th>File</th>
                        </tr>
            """
            for _, r in table_df.iterrows():
                tgl = r['Tanggal'].strftime('%Y-%m-%d') if pd.notnull(r['Tanggal']) else "-"
                print_html += f"<tr><td>{r['No']}</td><td>{r['Uraian']}</td><td>{tgl}</td><td>Rp {r['Nilai']:,.0f}</td><td>{r['File']}</td></tr>"
            
            total_sum = table_df['Nilai'].sum()
            print_html += f"""
                    </table>
                    <p class="total">Total Pengeluaran: Rp {total_sum:,.0f}</p>
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

    h1, h2, h3, h4, h5, h6 = st.columns([0.5, 2.2, 1.1, 1.3, 1.1, 1.4])
    h1.markdown("**No**")
    h2.markdown("**Uraian**")
    h3.markdown("**Tanggal**")
    h4.markdown("**Nilai**")
    h5.markdown("**File**")
    h6.markdown("**Aksi**")
    st.divider()

    if not paginated_df.empty:
        for index, row in paginated_df.iterrows():
            c1, c2, c3, c4, c5, c6 = st.columns([0.5, 2.2, 1.1, 1.3, 1.1, 1.4])
            
            c1.write(str(row['No']))
            c2.write(str(row['Uraian']))
            
            tgl_str = row['Tanggal'].strftime('%Y-%m-%d') if pd.notnull(row['Tanggal']) else "-"
            c3.write(tgl_str)
            c4.write(f"Rp {row['Nilai']:,.0f}")
            
            with c5:
                if st.button("📁 Buka", key=f"btn_file_{row['No']}"):
                    show_nota_popup(row['File'])
            
            with c6:
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
        st.info("Tidak ada data yang cocok dengan pencarian.")
else:
    st.info("Tabel transaksi masih kosong. Silakan upload nota atau input data melalui sidebar.")