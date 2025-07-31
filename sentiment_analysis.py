from contextlib import closing
from datetime import datetime
import json
import os
import subprocess
import sys
import time
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
audio_file_name = f'audio_file_{datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}.mp3'
analysis_file_name = f'analysis_file_{datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}.json'
transcribe_file_name = f"transcribe_file_{datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}.json"
transcription_job_name = f"analysis_job_{datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}"
output_bucket = f"{os.getenv('S3_BUCKET')}"
sentiment_results = []


output_dir = os.path.join(os.getcwd(), 'outputs')
os.makedirs(output_dir, exist_ok = True)
audio_file_path = os.path.join(output_dir, audio_file_name)

# Create full file path

# input_text = input('Enter Your Text : ')

# === Translate ===

def analyze_text(input_text):
    try:
        translatedText = translateClient.translate_text(
        Text =  input_text,
        SourceLanguageCode = 'en',
        TargetLanguageCode = 'hi',      
        )['TranslatedText']
    except(BotoCoreError, ClientError) as e:
        raise Exception(e, "==== Error in Translate ====")   
    print(translatedText) 

# === Text to Speech ===
    try:
        responseSpeech = pollyClient.synthesize_speech(
            OutputFormat = 'mp3',
            Text = translatedText,
            VoiceId = 'Aditi',
            Engine = 'standard',
            LanguageCode = 'hi-IN'
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
                    s3Client.upload_file(output, output_bucket, audio_file_name)
                    print(f"Audio file uploaded to S3 bucket: {audio_file_name}")
                    '''if sys.platform == 'win32':
                        os.startfile(output)
                    elif sys.platform == 'darwin': # For MacOS
                        subprocess.call(['Open', output])'''
            except IOError as e:
                raise Exception(e, "==== Error in writing file ====")     
    else:
        raise Exception("==== Could Not Stream Audio ====")

# === Transcribe ===

    try:
        response = transcribeClient.start_transcription_job(
            TranscriptionJobName = transcription_job_name,
            LanguageCode = "hi-IN",
            MediaFormat = "mp3",
            Media = {
                "MediaFileUri" : f"s3://{output_bucket}/{audio_file_name}"
            },
            OutputBucketName = output_bucket,
            OutputKey = f"{transcribe_file_name}"
        )
        print(f"Transcription job started: {transcription_job_name}")
        while True:
            job_status = transcribeClient.get_transcription_job(
                TranscriptionJobName = transcription_job_name
            )
            status = job_status['TranscriptionJob']['TranscriptionJobStatus']
            if status == 'COMPLETED':
                print(f"Transcription job completed: {transcription_job_name}")
                break
            elif status == 'FAILED':
                print(f"Transcription job failed: {transcription_job_name}")
                break
                time.sleep(10)
    except(BotoCoreError, ClientError) as e:
        raise Exception(e, "==== Error in Transcribe ====")


    try:
        # Download and parse the transcription JSON
        response = s3Client.get_object(
            Bucket = output_bucket,
            Key = f'{transcribe_file_name}'
        )
        transcription_json = json.loads(response['Body'].read())
        # Extract transcript text
        text_to_analyze = transcription_json['results']['transcripts'][0]['transcript']
        print('================== Transcription Text is : ', text_to_analyze)
        if text_to_analyze:
            # Detect Language Using Amazon Comprehend
            language_response = comprehendClient.detect_dominant_language(
                Text = text_to_analyze
            )
            detected_languages = language_response['Languages']
            primary_language_code = detected_languages[0]['LanguageCode']
            print('================== Detected Language is : ', primary_language_code)
            # Run Sentiment Analysis
            sentiment_response = comprehendClient.detect_sentiment(
                Text = text_to_analyze, 
                LanguageCode = primary_language_code
            )
            sentiment = sentiment_response['Sentiment']
            sentiment_score = sentiment_response['SentimentScore']  
            print('================== Detected Sentiment is : ', sentiment_response['Sentiment'])
            analysis_result = {
                'original_file' : analysis_file_name,
                'sentiment' : sentiment_response['Sentiment'],
                'sentiment_score' : sentiment_response['SentimentScore']
            }
            
            # print(analysis_result)
            
            # Save results to s3
            s3Client.put_object(
                Bucket = output_bucket,
                Key = f'{analysis_file_name}',
                Body = json.dumps(analysis_result)

        )
    except(BotoCoreError, ClientError) as e:
        raise Exception(e, "==== Error in Comprehend ====")

    return translatedText, sentiment, json.dumps(sentiment_score, indent = 2), audio_file_path
    
        
    