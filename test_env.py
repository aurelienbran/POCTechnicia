from dotenv import load_dotenv
import os

load_dotenv()
print(f"MAX_UPLOAD_SIZE: {os.getenv('MAX_UPLOAD_SIZE')}")
