# appkeu
Laporan untuk SPJ
-install pyton
-install git
-[(ahref](https://release-assets.githubusercontent.com/github-production-release-asset/22887094/f3dcad95-7c41-41cb-aa4a-5918f7e10778?sp=r&sv=2018-11-09&sr=b&spr=https&se=2026-11-04T12%3A46%3A38Z&rscd=attachment%3B+filename%3Dtesseract-ocr-w64-setup-5.5.3.20260724.exe&rsct=application%2Foctet-stream&skoid=96c2d410-5711-43a1-aedd-ab1947aa7ab0&sktid=398a6654-997b-47e9-b12b-9515b896b4de&skt=2026-11-04T11%3A46%3A13Z&ske=2026-11-04T12%3A46%3A38Z&sks=b&skv=2018-11-09&sig=bpDJ0ju%2BbuFk9YzAJgddBBhPSMr7BYjkgw2FBLWPh9o%3D&jwt=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmVsZWFzZS1hc3NldHMuZ2l0aHVidXNlcmNvbnRlbnQuY29tIiwia2V5Ijoia2V5MSIsImV4cCI6MTc5Mzc5NjE5MSwibmJmIjoxNzkzNzk0MzkxLCJwYXRoIjoicmVsZWFzZWFzc2V0cHJvZHVjdGlvbi5ibG9iLmNvcmUud2luZG93cy5uZXQifQ.1QBBpl-tL8YHKhLSL3DtgvRWtFoct_bK6u-iwJxwyy0&response-content-disposition=attachment%3B%20filename%3Dtesseract-ocr-w64-setup-5.5.3.20260724.exe&response-content-type=application%2Foctet-stream)

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
