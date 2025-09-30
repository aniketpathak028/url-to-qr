from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import qrcode
import boto3
from botocore.config import Config
import os
from io import BytesIO
import logging

# Loading Environment variable (AWS Access Key and Secret Key)
from dotenv import load_dotenv
load_dotenv()


# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Allowing CORS for local testing
origins = [
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AWS S3 Configuration
s3 = boto3.client(
    "s3",
    region_name="ap-south-1",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
    config=Config(signature_version="s3v4")
)

bucket_name = 'qrcodebucket123'

@app.post("/generate-qr/")
async def generate_qr(url: str):
    logger.info(f"Received request to generate QR for URL: {url}")
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        logger.info("QR code generated successfully.")

        # Save QR Code to BytesIO object
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)

        # Generate file name for S3
        file_name = f"qr_codes/{url.split('//')[-1]}.png"
        logger.info(f"Uploading QR code to S3 bucket '{bucket_name}' with key '{file_name}'")

        # Upload to S3
        s3.put_object(
            Bucket=bucket_name,
            Key=file_name,
            Body=img_byte_arr,
            ContentType='image/png'
        )

        s3_url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': file_name, 'ResponseContentType': 'image/png'},
            ExpiresIn=3600
        )

        logger.info("Presigned URL:", s3_url);

        return {"qr_code_url": s3_url}
    
    except Exception as e:
        logger.error(f"Error in QR code generation or S3 upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))
