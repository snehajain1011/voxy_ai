import logging
import os
import uuid
from contextlib import asynccontextmanager
from tempfile import NamedTemporaryFile

import boto3
import torch
import torchaudio
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from gen_wav import SAMPLE_RATE, gen_wav, initialize_model
from vocoder.bigvgan.models import VocoderBigVGAN
import soundfile as sf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
sampler = None
vocoder = None
API_KEY = os.getenv("API_KEY")
device = 'cuda' if torch.cuda.is_available() else 'cpu'

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

S3_PREFIX = os.getenv("S3_PREFIX", "make-an-audio-outputs")
S3_BUCKET = os.getenv("S3_BUCKET", "elevenlabs-clone")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global sampler, vocoder
    logger.info("Loading Make-an-Audio model...")
    try:
        sampler = initialize_model(
            'configs/text_to_audio/txt2audio_args.yaml', 'useful_ckpts/maa1_full.ckpt')
        vocoder = VocoderBigVGAN('useful_ckpts/bigvgan', device=device)

        logger.info("Make-an-Audio model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise

    yield

    logger.info("Shutting down Make-an-Audio API")

app = FastAPI(title="Make-an-Audio API",
              lifespan=lifespan)


class GenerateRequest(BaseModel):
    prompt: str


@app.post("/generate", dependencies=[Depends(verify_api_key)])
async def generate_speech(request: GenerateRequest, background_tasks: BackgroundTasks):
    if not sampler or not vocoder:
        raise HTTPException(status_code=500, detail="Models not loaded")

    try:
        wav_list = gen_wav(sampler, vocoder, prompt=request.prompt, ddim_steps=100,
                           scale=3.0, duration=10, n_samples=1)

        audio = wav_list[0]

        # Generate a unique filename
        audio_id = str(uuid.uuid4())
        output_filename = f"{audio_id}.wav"
        local_path = f"/tmp/{output_filename}"

        sf.write(local_path, audio, samplerate=SAMPLE_RATE)

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
        logger.error(f"Error generating audio: {e}")
        raise HTTPException(
            status_code=500, detail="Error generating audio")


@app.get("/health", dependencies=[Depends(verify_api_key)])
async def health_check():
    if vocoder and sampler:
        return {"status": "healthy", "model": "loaded"}
    return {"status": "unhealthy", "model": "not loaded"}
