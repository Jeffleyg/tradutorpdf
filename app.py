import os
import pdfplumber
import pytesseract
from PIL import Image
from flask import Flask, request, render_template, flash, redirect, url_for
from deep_translator import GoogleTranslator
from googletrans import Translator
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from sumy.summarizers.lex_rank import LexRankSummarizer
from sumy.summarizers.luhn import LuhnSummarizer
import nltk
nltk.download('punkt')
nltk.download('punkt_tab')

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # Limite de 10MB
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
MAX_FILE_SIZE = 10 * 1024 * 1024

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/translate", methods=["POST"])
def translate():
    if request.method == "POST":
        text = request.form.get('text', '')
        file = request.files.get('file')
        idioma_destino = request.form.get('idioma', 'en')
        context_aware = request.form.get('context_aware') == 'on'

        if not text and not file:
            flash('Por favor, insira um texto ou selecione um arquivo.', 'error')
            return redirect(url_for('index'))

        if file and file.filename != '':
            if not allowed_file(file.filename):
                flash('Tipo de arquivo não permitido. Apenas PDF, PNG, JPG são aceitos.', 'error')
                return redirect(url_for('index'))

            if request.content_length > MAX_FILE_SIZE:
                flash('Arquivo muito grande. O tamanho máximo é 10MB.', 'error')
                return redirect(url_for('index'))

            try:
                filepath = os.path.join(UPLOAD_FOLDER, file.filename)
                file.save(filepath)
                
                if file.filename.lower().endswith('.pdf'):
                    text = extract_text_from_pdf(filepath)
                else:
                    text = extract_text_from_image(filepath)
                
                os.remove(filepath)
            except Exception as e:
                flash(f'Ocorreu um erro ao processar o arquivo: {str(e)}', 'error')
                return redirect(url_for('index'))

        if not text.strip():
            flash('Nenhum texto encontrado para traduzir.', 'error')
            return redirect(url_for('index'))

        try:
            if context_aware:
                translated_text = translate_with_context(text, idioma_destino)
            else:
                translated_text = translate_text(text, idioma_destino)
            
            return render_template("index.html", result=translated_text)
        except Exception as e:
            flash(f'Ocorreu um erro ao traduzir: {str(e)}', 'error')
            return redirect(url_for('index'))

@app.route("/summarize", methods=["POST"])
def summarize():
    if request.method == "POST":
        text = request.form.get('text', '')
        file = request.files.get('file')
        length = request.form.get('length', 'medium')

        if not text and not file:
            flash('Por favor, insira um texto ou selecione um arquivo.', 'error')
            return redirect(url_for('index'))

        if file and file.filename != '':
            if not allowed_file(file.filename):
                flash('Tipo de arquivo não permitido. Apenas PDF, PNG, JPG são aceitos.', 'error')
                return redirect(url_for('index'))

            if request.content_length > MAX_FILE_SIZE:
                flash('Arquivo muito grande. O tamanho máximo é 10MB.', 'error')
                return redirect(url_for('index'))

            try:
                filepath = os.path.join(UPLOAD_FOLDER, file.filename)
                file.save(filepath)
                
                if file.filename.lower().endswith('.pdf'):
                    text = extract_text_from_pdf(filepath)
                else:
                    text = extract_text_from_image(filepath)
                
                os.remove(filepath)
            except Exception as e:
                flash(f'Ocorreu um erro ao processar o arquivo: {str(e)}', 'error')
                return redirect(url_for('index'))

        if not text.strip():
            flash('Nenhum texto encontrado para resumir.', 'error')
            return redirect(url_for('index'))

        try:
            summary = generate_summary(text, length)
            return render_template("index.html", result=summary)
        except Exception as e:
            flash(f'Ocorreu um erro ao gerar o resumo: {str(e)}', 'error')
            return redirect(url_for('index'))

def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

def extract_text_from_image(image_path):
    return pytesseract.image_to_string(Image.open(image_path))

def translate_text(text, dest_lang="en"):
    try:
        translator = GoogleTranslator(source='auto', target=dest_lang)
        max_chunk_size = 5000
        chunks = [text[i:i+max_chunk_size] for i in range(0, len(text), max_chunk_size)]
        translated_text = ""
        for chunk in chunks:
            translated_text += translator.translate(chunk)
        return translated_text
    except Exception as e:
        print(f"GoogleTranslator error: {str(e)}")
        translator = Translator()
        return translator.translate(text, dest=dest_lang).text

def translate_with_context(text, dest_lang="en"):
    # Implementação mais sofisticada com preservação de contexto
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    translated_paragraphs = []
    
    for para in paragraphs:
        try:
            # Tenta traduzir parágrafos maiores para manter o contexto
            translated = GoogleTranslator(source='auto', target=dest_lang).translate(para)
            translated_paragraphs.append(translated)
        except Exception:
            # Fallback para o tradutor alternativo
            translated = Translator().translate(para, dest=dest_lang).text
            translated_paragraphs.append(translated)
    
    return '\n\n'.join(translated_paragraphs)

def generate_summary(text, length="medium"):
    # Configura o resumidor baseado no comprimento desejado
    if length == "short":
        sentences_count = 3
    elif length == "long":
        sentences_count = 10
    else:  # medium
        sentences_count = 5
    
    # Baixa recursos do NLTK se necessário
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt')
    
    # Usa o Sumy para gerar o resumo
    parser = PlaintextParser.from_string(text, Tokenizer("portuguese"))
    summarizer = LsaSummarizer()
    
    summary_sentences = summarizer(parser.document, sentences_count)
    summary = " ".join([str(sentence) for sentence in summary_sentences])
    
    return summary

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)