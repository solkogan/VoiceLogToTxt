import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit,
    QFileDialog, QLabel, QProgressBar
)
from PyQt5.QtCore import QThread, pyqtSignal
from bs4 import BeautifulSoup
import re
import whisper

def transcribe_audio(file_path: str) -> str:
    # Загружаем модель 'tiny' для использования на слабых устройствах
    model = whisper.load_model("medium")
    
    # Выполняем транскрипцию аудиофайла
    result = model.transcribe(file_path)
    
    # Возвращаем текстовую расшифровку
    return result['text']

name = ''

import warnings
warnings.filterwarnings("ignore")

def has_txt_file(directory):
    """
    Проверяет, есть ли в указанной папке файлы с расширением .txt.

    :param directory: Путь к папке
    :return: True, если есть хотя бы один .txt файл, иначе False
    """
    for filename in os.listdir(directory):
        if filename.endswith('.txt'):
            return filename
    return False

def remove_invisible_characters(s):
    return ''.join(c for c in s if c.isprintable())

class Worker(QThread):
    update_progress = pyqtSignal(int)
    append_text = pyqtSignal(str)

    def __init__(self, input_folder):
        super().__init__()
        self.input_folder = input_folder

    def run(self):

       
        output_file = 'output/output.txt'
        max_number = len(os.listdir(self.input_folder))
        cur = 0

        fname = has_txt_file(self.input_folder)

        if os.path.exists(os.path.join(self.input_folder, f'messages.html')):
            with open(output_file, 'w', encoding='utf-8') as out_file:
                while cur < max_number:
                    s = f"{cur + 1}"
                    if s == '0' or s == '1':
                        s = ''
                    html_file = os.path.join(self.input_folder, f'messages{s}.html')
                    if os.path.exists(html_file):
                        self.parse_messages(html_file, out_file)
                    cur += 1
                    self.update_progress.emit(int((cur / max_number) * 100))

        elif fname:
            f = open(output_file, 'w', encoding = 'UTF-8')
            with open(os.path.join(self.input_folder, fname), 'r', encoding='utf-8') as file:
                # Проходим по всем строкам файла
                for line in file:
                    # Используем регулярное выражение для поиска .opus файлов
                    match = re.search(r'([^\s]+\.opus)', line)
                    if match:
                        # Если найдено соответствие, печатаем имя файла
                        oggfile = str(self.input_folder).strip() + '/' +  remove_invisible_characters(str(match.group(1)).strip())                                                
                        txt = transcribe_audio(oggfile)
                        line = line.replace(remove_invisible_characters(str(match.group(1)).strip()) , txt).replace('(файл добавлен)', '')
                    if not 'null' in line:
                        f.write(line.strip() + '\n')
                        self.append_text.emit(line)
            f.close()

        

        self.append_text.emit(f"Сообщения сохранены в файл: {output_file}")

    def parse_messages(self, html_file, out_file):
        name = ''
        with open(html_file, 'r', encoding='utf-8') as file:
            content = file.read()

        soup = BeautifulSoup(content, 'html.parser')
        messages = soup.find_all('div', class_='message')

        for message in messages:
            time = message.find('div', class_='date')
            time = time['title'].strip() if time else ''

            name2 = message.find('div', class_='from_name')
            if name2:
                name = name2.text.strip()
            
            text = ''
            text_div = message.find('div', class_='text')
            if text_div:
                text = text_div.get_text(separator='\n').strip()
                text = re.sub(r'\n+', '\n', text).replace('\n', ' ')

            text_div = message.find('a', class_='media')
            if text_div:
                text = text_div.get('href')
                if '.ogg' in text:
                    text = transcribe_audio(os.path.join(self.input_folder, text))
                    
            text_div = message.find('div', class_='media')
            if text_div:
                text = '(Присылает медиафайл)'

            if text and time:
                output_text = f"{time} | {name} | {text.strip()}\n"
                self.append_text.emit(output_text)
                out_file.write(output_text)

class App(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Telegram Message Analyzer')
        self.setGeometry(100, 100, 900, 900)

        layout = QVBoxLayout()

        self.label = QLabel('Выберите папку с HTML файлами:')
        layout.addWidget(self.label)

        self.button = QPushButton('Выбрать папку')
        self.button.clicked.connect(self.open_folder)
        layout.addWidget(self.button)

        self.progress = QProgressBar()
        layout.addWidget(self.progress)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)

        self.setLayout(layout)

    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if folder:
            self.start_analysis(folder)

    def start_analysis(self, folder):
        self.worker = Worker(folder)
        self.worker.update_progress.connect(self.update_progress)
        self.worker.append_text.connect(self.append_text)
        self.worker.start()

    def update_progress(self, value):
        self.progress.setValue(value)

    def append_text(self, text):
        self.text_edit.append(text)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    ex.show()
    sys.exit(app.exec_())
