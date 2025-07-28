from contextlib import asynccontextmanager
import uuid
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Header
import logging
import os
import re
from fastapi.security import APIKeyHeader
import numpy as np
import soundfile as sf
import boto3
from pydantic import BaseModel
from libri_inference import StyleTTS2Inference
# from dotenv import load_dotenv
# load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
synthesizer = None
reference_style = None
API_KEY = os.getenv("API_KEY")

api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


async def verify_api_key(authorization: str = Header(None)):
    if not authorization:
        logger.warning("No API key provided")
        raise HTTPException(status_code=401, detail="API key is missing")

    if authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
    else:
        token = authorization

    if token != API_KEY:
        logger.warning("Invalid API key provided")
        raise HTTPException(status_code=401, detail="Invalid API key")

    return token


def get_s3_client():
    client_kwargs = {'region_name': os.getenv("AWS_REGION", "us-east-1")}

    if os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
        client_kwargs.update({
            'aws_access_key_id': os.getenv("AWS_ACCESS_KEY_ID"),
            'aws_secret_access_key': os.getenv("AWS_SECRET_ACCESS_KEY")
        })

    return boto3.client('s3', **client_kwargs)


s3_client = get_s3_client()

S3_PREFIX = os.getenv("S3_PREFIX", "styletts2-output")
S3_BUCKET = os.getenv("S3_BUCKET", "elevenlabs-clone")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global synthesizer, reference_style
    logger.info("Loading StyleTTS2 model...")
    try:
        synthesizer = StyleTTS2Inference(
            config_path=os.getenv("CONFIG_PATH", "Models/LibriTTS/config.yml"),
            model_path=os.getenv(
                "MODEL_PATH", "Models/LibriTTS/epoch_2nd_00074.pth")
        )

        logger.info("StyleTTS2 model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load StyleTTS2 model: {e}")
        raise

    yield

    logger.info("Shutting down StyleTTS2 API")

app = FastAPI(title="StyleTTS2 API",
              lifespan=lifespan)

TARGET_VOICES = {
    "andreas": "Models/LibriTTS/andreas1.wav",
    "woman": "Models/LibriTTS/woman1.wav",
}


def text_chunker(text, max_chunk_size=125):
    if len(text) <= max_chunk_size:
        return [text]

    chunks = []
    current_pos = 0
    text_len = len(text)

    while current_pos < text_len:
        if current_pos + max_chunk_size >= text_len:
            chunks.append(text[current_pos:])
            break

        chunk_end = current_pos + max_chunk_size
        search_text = text[current_pos:chunk_end]

        sentence_ends = [m.end() for m in re.finditer(r'[.!?]+', search_text)]

        if sentence_ends:
            last_sentence_end = sentence_ends[-1]
            chunks.append(text[current_pos:current_pos + last_sentence_end])
            current_pos += last_sentence_end
        else:
            last_space = search_text.rfind(' ')
            if last_space > 0:
                chunks.append(text[current_pos:current_pos + last_space])
                current_pos += last_space + 1
            else:
                chunks.append(text[current_pos:chunk_end])
                current_pos = chunk_end

        while current_pos < text_len and text[current_pos].isspace():
            current_pos += 1

    return chunks


class TextOnlyRequest(BaseModel):
    text: str
    target_voice: str


@app.post("/generate", dependencies=[Depends(verify_api_key)])
async def generate_speech(request: TextOnlyRequest, background_tasks: BackgroundTasks):
    if len(request.text) > 5000:
        raise HTTPException(
            status_code=400, detail="Text length exceeds the limit of 5000 characters")

    if not synthesizer:
        raise HTTPException(status_code=500, detail="Model not loaded")

    if request.target_voice not in TARGET_VOICES:
        raise HTTPException(
            status_code=400, detail=f"Target voice not supported. Choose from: {', '.join(TARGET_VOICES.keys())}")

    try:
        ref_audio_path = TARGET_VOICES[request.target_voice]

        # Compute style for requested voice
        current_style = synthesizer.compute_style(ref_audio_path)
        logger.info(
            f"Using voice {request.target_voice} from {ref_audio_path}")

        # Generate a unique filename
        audio_id = str(uuid.uuid4())
        output_filename = f"{audio_id}.wav"
        local_path = f"/tmp/{output_filename}"

        # Split text into manageable chunks
        text_chunks = text_chunker(request.text)
        logger.info(f"Text split into chunks: {len(text_chunks)}")

        audio_segments = []

        for i, chunk in enumerate(text_chunks):
            logger.info(f"Processing chunk {i+1}/{len(text_chunks)}")

            audio_chunk = synthesizer.inference(
                text=chunk,
                ref_s=current_style
            )

            audio_segments.append(audio_chunk)

            if i < len(text_chunks) - 1:
                silence = np.zeros(int(24000 * 0.3))
                audio_segments.append(silence)

        if len(audio_segments) > 1:
            full_audio = np.concatenate(audio_segments)
        else:
            full_audio = audio_segments[0]

        sf.write(local_path, full_audio, 24000)

        # Upload to S3
        s3_key = f"{S3_PREFIX}/{output_filename}"
        s3_client.upload_file(local_path, S3_BUCKET, s3_key)

        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': s3_key},
            ExpiresIn=3600
        )

        background_tasks.add_task(os.remove, local_path)

        return {
            "audio_url": presigned_url,
            "s3_key": s3_key
        }
    except Exception as e:
        logger.error(f"Failed to generate speech: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to generate speech")


@app.get("/voices", dependencies=[Depends(verify_api_key)])
async def list_voices():
    return {"voices": list(TARGET_VOICES.keys())}


@app.get("/health", dependencies=[Depends(verify_api_key)])
async def health_check():
    if synthesizer:
        return {"status": "healthy", "model": "loaded"}
    return {"status": "unhealthy", "model": "not loaded"}
