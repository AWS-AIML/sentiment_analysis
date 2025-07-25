from contextlib import closing
from datetime import datetime
import os
import subprocess
import sys
import boto3
import boto3.session
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv

load_dotenv()

session = boto3.session.Session()
translateClient = session.client('translate')
pollyClient = session.client('polly')
transcribeClient = session.client('transcribe')
comprehendClient = session.client('comprehend')
s3Client = session.client('s3')
text = None
audio_file_name = f'audio_file_{datetime.now().strftime("%Y%m%d%H%M%S")}.mp3'
analysis_file_name = f'analysis_file_{datetime.now().strftime("%Y%m%d%H%M%S")}.mp3'


output_dir = os.path.join(os.getcwd(), 'outputs')
os.makedirs(output_dir, exist_ok=True)
# Create full file path
try:
    responseText = translateClient.translate_text(
    Text =  'Hi This program will Translate text from English to Spanish using AWS Translate and then convert text to speech using AWS polly',
    SourceLanguageCode = 'en',
    TargetLanguageCode = 'es',      
               
    )
except(BotoCoreError, ClientError) as e:
    raise Exception(e, "==== Error in Translate ====")


text = responseText['TranslatedText']      
print(text) 

try:
    responseSpeech = pollyClient.synthesize_speech(
        OutputFormat = 'mp3',
        Text = text,
        VoiceId = 'Joanna',
        Engine = 'standard',
        LanguageCode = 'es-MX'
    )
except(BotoCoreError, ClientError) as e:
    # logger.error('=== Error in Polly API ===', e)
    raise Exception(e, "==== Error in polly ====")
    

if 'AudioStream' in responseSpeech:
    with closing(responseSpeech['AudioStream']) as stream:
        output =  os.path.join(output_dir, audio_file_name)
        try:
            with open(output, 'wb') as file:
                audio_data = stream.read()
                file.write(audio_data)
                s3Client.upload_file(output, 'ysharif-bucket', audio_file_name)
                print(f"Audio file uploaded to S3 bucket: {audio_file_name}")
                if sys.platform == 'win32':
                    os.startfile(output)
                elif sys.platform == 'darwin': # For MacOS
                    subprocess.call(['Open', output])
        except IOError as e:
            raise Exception(e, "==== Error in writing file ====")     
else:
    raise Exception("==== Could Not Stream Audio ====")

