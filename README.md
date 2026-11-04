# appkeu
Laporan untuk SPJ
-install pyton
-install git


git clone https://github.com/rezaongdur/appkeu
cd appkeu
pip install 
streamlit run app.py / python -m streamlit run app.py


Download & Install Tesseract OCR (untuk Windows: download installer Tesseract-OCR, untuk Linux/Mac bisa pakai sudo apt install tesseract-ocr atau brew install tesseract).
# Jika menggunakan Windows, atur path tesseract.exe jika belum masuk ke System PATH: pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
simpan dibawah import pytesseract :
Contoh :
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
