"""
Module that contains the command line app.
"""
import os
import io
import argparse
import shutil
import glob
from google.cloud import storage
from google.cloud import speech
from google.cloud import texttospeech
from googletrans import Translator
import ffmpeg
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from tempfile import TemporaryDirectory

# Generate the inputs arguments parser
parser = argparse.ArgumentParser(description="Command description.")

gcp_project = "APCOMP215"
bucket_name = "mega-pipeline-bucket-215"
input_audios = "input_audios"
text_prompts = "text_prompts" # THIS IS THE TRANSCRIBED TEXT
text_paragraphs = "text_paragraphs" # THIS IS THE LLM GENERATED TEXT
text_audios = "text_audios" # ENGLISH AUDIOS
text_translated = "text_translated"
output_audios = "output_audios" # TRANSLATED AUDIOS

#############################################################################
#                            Initialize the model                           #
vertexai.init(project=gcp_project, location="us-central1")
model = GenerativeModel(model_name="gemini-1.5-flash-001",)
generation_config = GenerationConfig(
    temperature=0.01
)
#############################################################################

# Instantiates a client
client = texttospeech.TextToSpeechLongAudioSynthesizeClient()

translator = Translator()

def makedirs():
    os.makedirs(input_audios, exist_ok=True)
    os.makedirs(text_prompts, exist_ok=True)
    os.makedirs(text_paragraphs, exist_ok=True)
    os.makedirs(text_audios, exist_ok=True)
    os.makedirs(text_translated, exist_ok=True)
    os.makedirs(output_audios, exist_ok=True)


def download_audio():
    print("downloading audio")

    # Clear
    shutil.rmtree(input_audios, ignore_errors=True, onerror=None)
    makedirs()

    client = storage.Client()
    bucket = client.get_bucket(bucket_name)

    blobs = bucket.list_blobs(prefix=input_audios+"/")
    for blob in blobs:
        print(blob.name)
        if not blob.name.endswith("/"):
            blob.download_to_filename(blob.name)


def transcribe_audio():
    print("transcribing audio")
    makedirs()

    # Speech client
    client = speech.SpeechClient()

    # Get the list of audio file
    audio_files = os.listdir(input_audios)

    for audio_path in audio_files:
        uuid = audio_path.replace(".mp3", "")
        audio_path = os.path.join(input_audios, audio_path)
        text_file = os.path.join(text_prompts, uuid + ".txt")

        if os.path.exists(text_file):
            continue

        print("Transcribing:", audio_path)
        with TemporaryDirectory() as audio_dir:
            flac_path = os.path.join(audio_dir, "audio.flac")
            stream = ffmpeg.input(audio_path)
            stream = ffmpeg.output(stream, flac_path)
            ffmpeg.run(stream)

            with io.open(flac_path, "rb") as audio_file:
                content = audio_file.read()

            # Transcribe
            audio = speech.RecognitionAudio(content=content)
            config = speech.RecognitionConfig(language_code="en-US")
            operation = client.long_running_recognize(config=config, audio=audio)
            response = operation.result(timeout=90)
            print("response:", response)
            text = "None"
            if len(response.results) > 0:
                text = response.results[0].alternatives[0].transcript
                print(text)

            # Save the transcription
            with open(text_file, "w") as f:
                f.write(text)


def upload_transcribed_audio_text():
    print("uploading transcribed text from audio")
    makedirs()

    # Upload to bucket
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    # Get the list of text file
    text_files = glob.glob(os.path.join(text_prompts, "input-*.txt"))

    for text_file in text_files:
        filename = os.path.basename(text_file)
        destination_blob_name = os.path.join(text_prompts, filename)
        blob = bucket.blob(destination_blob_name)
        print("Uploading:",destination_blob_name, text_file)
        blob.upload_from_filename(text_file)

def download_text_prompts():
    print("downloading text prompts")

    # Clear
    shutil.rmtree(text_prompts, ignore_errors=True, onerror=None)
    makedirs()

    storage_client = storage.Client(project=gcp_project)
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs(match_glob=f"{text_prompts}/input-*.txt")
    for blob in blobs:
        blob.download_to_filename(blob.name)

def generate_text_paragraph():
    print("generating LLM outputs from prompts")
    makedirs()

    # Get the list of text file
    text_files = glob.glob(os.path.join(text_prompts, "input-*.txt"))
    for text_file in text_files:
        uuid = os.path.basename(text_file).replace(".txt", "")
        paragraph_file = os.path.join(text_paragraphs, uuid + ".txt")

        if os.path.exists(paragraph_file):
            continue

        with open(text_file) as f:
            input_text = f.read()


        # Generate output
        input_prompt = f"""
            Create a transcript for the podcast about cheese with 1000 or more words.
            Use the below text as a starting point for the cheese podcast.
            Output the transcript as paragraphs and not with who is talking or any "Sound" or any other extra information.
            Do not highlight or make words bold.
            The host's name is Pavlos Protopapas.
            {input_text}
        """
        print(input_prompt,"\n\n\n")
        response = model.generate_content(input_prompt,generation_config=generation_config)
        paragraph = response.text


        print("Generated text:")
        print(paragraph)

        # Save the transcription
        with open(paragraph_file, "w") as f:
            f.write(paragraph)

def upload_text_paragraph():
    print("uploading text paragraphs")
    makedirs()

    # Upload to bucket
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    # Get the list of text file
    text_files = glob.glob(os.path.join(text_paragraphs, "input-*.txt"))

    for text_file in text_files:
        filename = os.path.basename(text_file)
        destination_blob_name = os.path.join(text_paragraphs, filename)
        blob = bucket.blob(destination_blob_name)
        print("Uploading:",destination_blob_name, text_file)
        blob.upload_from_filename(text_file)

def download_text_paragraphs():
    print("downloading text paragraphs")

    # Clear
    shutil.rmtree(text_paragraphs, ignore_errors=True, onerror=None)
    makedirs()

    storage_client = storage.Client(project=gcp_project)
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs(match_glob=f"{text_paragraphs}/input-*.txt")
    for blob in blobs:
        blob.download_to_filename(blob.name)

def synthesis_en_audios():
    print("synthesizing English audios")
    makedirs()

    language_code = "en-US" # https://cloud.google.com/text-to-speech/docs/voices
    language_name = "en-US-Standard-B" # https://cloud.google.com/text-to-speech/docs/voices

    # Get the list of text file
    text_files = glob.glob(os.path.join(text_paragraphs, "input-*.txt"))
    for text_file in text_files:
        uuid = os.path.basename(text_file).replace(".txt", "")
        audio_file = os.path.join(text_audios, uuid + ".mp3")

        if os.path.exists(audio_file):
            continue

        with open(text_file) as f:
            input_text = f.read()
        
        # Check if audio file already exists
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        audio_blob_name = f"{text_audios}/{uuid}.mp3"
        blob = bucket.blob(audio_blob_name)

        if not blob.exists():
            # Set the text input to be synthesized
            input = texttospeech.SynthesisInput(text=input_text)
            # Build audio config / Select the type of audio file you want returned
            audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.LINEAR16)
            # voice config
            voice = texttospeech.VoiceSelectionParams(language_code=language_code, name=language_name)

            parent = f"projects/{gcp_project}/locations/us-central1"
            output_gcs_uri = f"gs://{bucket_name}/{audio_blob_name}"

            request = texttospeech.SynthesizeLongAudioRequest(
                parent=parent,
                input=input,
                audio_config=audio_config,
                voice=voice,
                output_gcs_uri=output_gcs_uri,
            )

            operation = client.synthesize_long_audio(request=request)
            # Set a deadline for your LRO to finish. 300 seconds is reasonable, but can be adjusted depending on the length of the input.
            result = operation.result(timeout=300)
            print("Audio file will be saved to GCS bucket automatically.")

def translate_text_paragraphs_en_fr():
    print("translate")
    makedirs()

    # Get the list of text file
    text_files = glob.glob(os.path.join(text_paragraphs, "input-*.txt"))
    for text_file in text_files:
        uuid = os.path.basename(text_file).replace(".txt", "")
        translated_file = os.path.join(text_translated, uuid + ".txt")

        if os.path.exists(translated_file):
            continue

        with open(text_file) as f:
            input_text = f.read()

        results = translator.translate(input_text, src="en", dest="fr")
        print(results.text)

        # Save the translation
        with open(translated_file, "w") as f:
            f.write(results.text)

def upload_text_translate():
    print("uploading translated text from English to French")
    makedirs()

    # Upload to bucket
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    # Get the list of text file
    text_files = glob.glob(os.path.join(text_translated, "input-*.txt"))

    for text_file in text_files:
        filename = os.path.basename(text_file)
        destination_blob_name = os.path.join(text_translated, filename)
        blob = bucket.blob(destination_blob_name)
        print("Uploading:",destination_blob_name, text_file)
        blob.upload_from_filename(text_file)

def download_text_translate():
    print("downloading translated text from English to French")

    # Clear
    shutil.rmtree(text_translated, ignore_errors=True, onerror=None)
    makedirs()

    storage_client = storage.Client(project=gcp_project)
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs(match_glob=f"{text_translated}/input-*.txt")
    for blob in blobs:
        blob.download_to_filename(blob.name)

def synthesis_audio_fr():
    print("synthesizing French audio from translated text")
    makedirs()

    language_code = "fr-FR" # https://cloud.google.com/text-to-speech/docs/voices
    language_name = "fr-FR-Standard-C" # https://cloud.google.com/text-to-speech/docs/voices

    # Get the list of text file
    text_files = glob.glob(os.path.join(text_translated, "input-*.txt"))
    for text_file in text_files:
        uuid = os.path.basename(text_file).replace(".txt", "")
        audio_file = os.path.join(output_audios, uuid + ".mp3")

        if os.path.exists(audio_file):
            continue

        with open(text_file) as f:
            input_text = f.read()
        
        # Check if audio file already exists
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        audio_blob_name = f"{output_audios}/{uuid}.mp3"
        blob = bucket.blob(audio_blob_name)

        if not blob.exists():
            # Set the text input to be synthesized
            input = texttospeech.SynthesisInput(text=input_text)
            # Build audio config / Select the type of audio file you want returned
            audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.LINEAR16)
            # voice config
            voice = texttospeech.VoiceSelectionParams(language_code=language_code, name=language_name)

            parent = f"projects/{gcp_project}/locations/us-central1"
            output_gcs_uri = f"gs://{bucket_name}/{audio_blob_name}"

            request = texttospeech.SynthesizeLongAudioRequest(
                parent=parent,
                input=input,
                audio_config=audio_config,
                voice=voice,
                output_gcs_uri=output_gcs_uri,
            )

            operation = client.synthesize_long_audio(request=request)
            # Set a deadline for your LRO to finish. 300 seconds is reasonable, but can be adjusted depending on the length of the input.
            result = operation.result(timeout=300)
            print("Audio file will be saved to GCS bucket automatically.") 



def main(args=None):
    print("Args:", args)

    if args.download_audio:
        download_audio()
    if args.transcribe_audio:
        transcribe_audio()
    if args.upload_transcribed_audio_text:
        upload_transcribed_audio_text()
    if args.download_text_prompts:
        download_text_prompts()
    if args.generate_text_paragraph:
        generate_text_paragraph()
    if args.upload_text_paragraph:
        upload_text_paragraph()
    if args.download_text_paragraphs:
        download_text_paragraphs()
    if args.synthesis_en_audios:
        synthesis_en_audios()
    if args.translate_text_paragraphs_en_fr:
        translate_text_paragraphs_en_fr()
    if args.upload_text_translate:
        upload_text_translate()
    if args.download_text_translate:
        download_text_translate()
    if args.synthesis_audio_fr:
        synthesis_audio_fr()


if __name__ == "__main__":
    # Generate the inputs arguments parser
    # if you type into the terminal 'python cli.py --help', it will provide the description
    parser = argparse.ArgumentParser(description="Transcribe audio file to text")

    parser.add_argument(
        "--download_audio",
        action="store_true",
        help="Download audio files from GCS bucket",
    )

    parser.add_argument(
        "--transcribe_audio", 
        action="store_true", 
        help="Transcribe audio files to text"
    )

    parser.add_argument(
        "--upload_transcribed_audio_text",
        action="store_true",
        help="Upload transcribed text to GCS bucket",
    )

    parser.add_argument(
        "--download_text_prompts",
        action="store_true",
        help="Download text prompts from GCS bucket",
    )

    parser.add_argument(
        "--generate_text_paragraph", 
        action="store_true", 
        help="Generate a text paragraph"
    )

    parser.add_argument(
        "--upload_text_paragraph",
        action="store_true",
        help="Upload paragraph text to GCS bucket",
    )

    parser.add_argument(
        "--download_text_paragraphs",
        action="store_true",
        help="Download paragraph of text from GCS bucket",
    )

    parser.add_argument(
        "--synthesis_en_audios", 
        action="store_true", 
        help="Synthesis audio"
    )

    parser.add_argument(
        "--translate_text_paragraphs_en_fr", 
        action="store_true", 
        help="Translate text")

    parser.add_argument(
        "--upload_text_translate",
        action="store_true",
        help="Upload translated text to GCS bucket",
    )

    parser.add_argument(
        "--download_text_translate",
        action="store_true",
        help="Download translated text from GCS bucket",
    )

    parser.add_argument(
        "--synthesis_audio_fr", 
        action="store_true", 
        help="Synthesis audio"
    )

    args = parser.parse_args()

    main(args)
