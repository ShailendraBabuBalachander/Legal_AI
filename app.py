from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import os
import google.generativeai as genai
#import uuid
#import cv2
#import numpy as np

app = Flask(__name__, template_folder='templates')

pytesseract.pytesseract.tesseract_cmd = r'C:/Users/Software Testing/AppData/Local/Programs/Tesseract-OCR/tesseract.exe'


UPLOAD_FOLDER = 'uploads'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


genai.configure(api_key="AIzaSyB4kcOA9nB661FF8tFcbUtH1Lxbyle7y3A")
model = genai.GenerativeModel("gemini-1.5-flash")


extracted_text = ""  
def is_pdf(file_path):
    return file_path.lower().endswith('.pdf')

def convert_image_to_pdf(image_path):
    image = Image.open(image_path)
    pdf_path = os.path.splitext(image_path)[0] + ".pdf"
    image.convert("RGB").save(pdf_path)
    return pdf_path



def extract_text_from_scanned_pdf(pdf_path, use_custom_config=True):
    pdf_document = fitz.open(pdf_path)
    text_psm6 = ""
    text_psm11 = ""
    
    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        pix = page.get_pixmap()
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        

        
        if use_custom_config:
            # Try both PSM values (6 and 11)
            custom_config_psm6 = r'--oem 3 --psm 6'
            text_psm6 += pytesseract.image_to_string(img, config=custom_config_psm6) + "\n"
            
            custom_config_psm11 = r'--oem 3 --psm 11'
            text_psm11 += pytesseract.image_to_string(img, config=custom_config_psm11) + "\n"
        
        else:
            # Default custom config (e.g., psm 6)
            custom_config = r'--oem 3 --psm 6'  # You can choose psm 6 or 11 here
            text_psm6 += pytesseract.image_to_string(img, config=custom_config) + "\n"
    
    pdf_document.close()


    return text_psm6, text_psm11
     
        



def process_file(input_file):
    if is_pdf(input_file):
        return extract_text_from_scanned_pdf(input_file)
    else:
        pdf_path = convert_image_to_pdf(input_file)
        return extract_text_from_scanned_pdf(pdf_path)

@app.route('/')
def index():
    return render_template('index.html')

def add_bullet_points(content):
   
    sentences = content.split(". ")
    
    sentences = [f"• {sentence.strip()}." for sentence in sentences if sentence.strip()]
   
    return "\n".join(sentences)




@app.route('/upload', methods=['POST'])
def upload_file():
    global extracted_text
    if 'file' not in request.files or 'user_input' not in request.form:
        return redirect(request.url)

    file = request.files['file']
    user_input = request.form['user_input'] 

    if file.filename == '':
        return redirect(request.url)

  
    input_file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(input_file_path)

    
    extracted_text = process_file(input_file_path)

    

    
    responses = {}


    if user_input.strip(): 
        combined_input = f"Based on the agreement, {user_input} Here is the agreement text: {extracted_text}"
        user_input_response = model.generate_content(combined_input)
        responses['user_input_response.txt'] = user_input_response.text if user_input_response.text else "No relevant information found."


    key_info_input = f"Identify key information in: {extracted_text}"
    key_info_response = model.generate_content(key_info_input)
    key_info_text = key_info_response.text if key_info_response.text else "No key information found."
    responses['summary.txt'] = key_info_text 

    point_against_first_party_input = f"Identify point against first party in:{extracted_text}"
    point_against_first_party_response = model.generate_content(point_against_first_party_input)
    point_against_first_party_text = point_against_first_party_response.text if point_against_first_party_response.text else "No information found"
    responses['point_against_first_party.txt'] = point_against_first_party_text

    point_against_second_party_input = f"Identify point against second party in:{extracted_text}"
    point_against_second_party_response = model.generate_content(point_against_second_party_input)
    point_against_second_party_text = point_against_second_party_response.text if point_against_second_party_response.text else "No information found"
    responses['point_against_second_party.txt'] = point_against_second_party_text

    date_input = f"Extract date from: {extracted_text}"  
    date_response = model.generate_content(date_input)  
    date_text = date_response.text if date_response.text else "No date found."
    responses['date.txt'] = date_text 


    certificate_input = f"Extract certificate number from: {extracted_text}"
    certificate_response = model.generate_content(certificate_input)
    certificate_text = certificate_response.text if certificate_response.text else "No certificate number found."
    responses['certificate_number.txt'] = certificate_text 


    agreement_input = f"Identify agreement type in: {extracted_text}"
    agreement_response = model.generate_content(agreement_input)
    agreement_text = agreement_response.text if agreement_response.text else "No agreement type found."
    responses['agreement_type.txt'] = agreement_text 

    


    file_paths = []
    for filename, content in responses.items():
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
        file_paths.append(filename)

    print("Generated Files:", file_paths)

    return render_template('index.html', 
                           response_text="Responses generated successfully!", 
                           report_paths=file_paths)




@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)