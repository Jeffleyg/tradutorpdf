import os
import pdfplumber
from flask import Flask, request, render_template, flash, redirect
from deep_translator import GoogleTranslator
from googletrans import Translator

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # Limite de 10MB
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/", methods=["GET", "POST"])
def upload_file():
    conversation = []

    if request.method == "POST":
        if 'file' not in request.files:
            flash('Nenhum arquivo enviado!', 'error')
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            flash('Nenhum arquivo selecionado!', 'error')
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash('Tipo de arquivo não permitido. Apenas PDFs são aceitos.', 'error')
            return redirect(request.url)

        if request.content_length > MAX_FILE_SIZE:
            flash('Arquivo muito grande. O tamanho máximo é 10MB.', 'error')
            return redirect(request.url)

        idioma_destino = request.form.get('idioma', 'en')

        try:
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)

            original_text = extract_text_from_pdf(filepath)
            translated_text = translate_text(original_text, idioma_destino)

            os.remove(filepath)

            # Adicionando a tradução na conversa
            conversation.append({
                "sender": "chatbot",
                "message": translated_text
            })

        except Exception as e:
            flash(f'Ocorreu um erro ao processar o arquivo: {str(e)}', 'error')
            return redirect(request.url)

    return render_template("index.html", conversation=conversation)

def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

def translate_text(text, dest_lang="en"):
    try:
        translator = GoogleTranslator(source='auto', target=dest_lang)
        max_chunk_size = 5000
        chunks = [text[i:i+max_chunk_size] for i in range(0, len(text), max_chunk_size)]
        translated_text = ""
        for chunk in chunks:
            translated_text += translator.translate(chunk)
        return translated_text

    except Exception:
        translator = Translator()
        return translator.translate(text, dest=dest_lang).text

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)