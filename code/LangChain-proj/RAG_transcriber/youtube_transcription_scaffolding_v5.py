# -*- coding: utf-8 -*-
"""youtube_transcription_scaffolding_v5.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1-eLy6YxVFJCvwyYJsL5AgKxE-lIWDoJO

# -*- coding: utf-8 -*-
'''youtube_scaffolding_v5.ipynb

A scaffolding script to invoke the YouTube transcriber module and verify its output.
Designed to run in Google Colab.
'''
"""

import subprocess
import sys

def install_requirements():
    """Install required packages using pip."""
    packages = [
        'importlib',
        'pathlib'
    ]
    try:
        for package in packages:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", package])
    except Exception as e:
        print(f"Error installing requirements: {str(e)}")
        sys.exit(1)

# Install required packages
install_requirements()

# Import required libraries
import os
import importlib
import importlib.util
import traceback
import time
import logging
from pathlib import Path
from google.colab import drive

# Mount Google Drive
drive.mount('/content/drive')

# VARS: Set these variables
version_number = 'v38'
youtube_url = "https://www.youtube.com/watch?v=cdiD-9MMpb0"
code_version = 'v17'  # Updated to match current transcriber version
base_dir = "/content/drive/My Drive/python-projects/kaggle_experiments/transcriber/"
fnm = "youtube_transcriber" + "_" + code_version + ".py"
cur_fnm = fnm
full_fnm = base_dir + cur_fnm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def verify_transcript_file(transcript_dir):
    """
    Verify that the transcript file exists and is not empty.

    Args:
        transcript_dir (str): Directory where transcript should be located

    Returns:
        tuple: (bool, str) - (Success status, Full path of transcript file if found)
    """
    transcript_path = os.path.join(transcript_dir, "transcript.txt")

    if not os.path.exists(transcript_path):
        logger.error(f"Transcript file not found at: {transcript_path}")
        return False, None

    if os.path.getsize(transcript_path) == 0:
        logger.error(f"Transcript file is empty: {transcript_path}")
        return False, None

    # Read first and last lines to verify content
    try:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            # Go to the end and read last line
            f.seek(0, 2)  # Go to end
            pos = f.tell() - 2
            while pos > 0 and f.read(1) != "\n":
                pos -= 1
                f.seek(pos, 0)
            last_line = f.readline().strip()

        if not first_line or not last_line:
            logger.error(f"Transcript file appears incomplete: {transcript_path}")
            return False, None

        logger.info(f"Transcript file verified at: {transcript_path}")
        return True, transcript_path

    except Exception as e:
        logger.error(f"Error verifying transcript file: {str(e)}")
        return False, None

def get_transcript_dir(base_dir, version_num):
    """
    Construct the full path to the transcript directory.

    Args:
        base_dir (str): Base directory path
        version_num (str): Version number for directory

    Returns:
        str: Full path to transcript directory
    """
    return os.path.join(base_dir, f"transcriber_{version_num}")

def monitor_transcript_progress(transcript_dir):
    """
    Monitor progress by checking for the existence and growth of audio chunks.

    Args:
        transcript_dir (str): Directory to monitor
    """
    chunks_dir = os.path.join(transcript_dir, "chunks")
    if os.path.exists(chunks_dir):
        files = os.listdir(chunks_dir)
        return len(files)
    return 0

def import_transcriber_module(full_fnm, base_dir):
    """
    Import the transcriber module safely.

    Args:
        full_fnm (str): Full path to the module file
        base_dir (str): Base directory path

    Returns:
        module: Imported module object
    """
    try:
        # Add base directory to Python path
        if base_dir not in sys.path:
            sys.path.append(base_dir)

        # Get module name without .py extension
        module_name = os.path.splitext(os.path.basename(full_fnm))[0]

        # Import the module using spec
        spec = importlib.util.spec_from_file_location(module_name, full_fnm)
        if spec is None:
            raise ImportError(f"Could not load spec for module {module_name}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        return module

    except Exception as e:
        logger.error(f"Error importing transcriber module: {str(e)}")
        raise

def invoke_youtube_transcriber_args(full_fnm, base_dir, url, version_num, clean_dir=False):
    """
    Invoke the YouTube transcriber module and verify its output.

    Args:
        full_fnm (str): Full path to the transcriber module
        base_dir (str): Base directory path
        url (str): YouTube URL to process
        version_num (str): Version number for directory naming
        clean_dir (bool): Whether to clean existing directory

    Returns:
        tuple: (bool, str) - (Success status, Full path of transcript file if successful)
    """
    try:
        # Verify transcriber module exists
        if not os.path.exists(full_fnm):
            logger.error(f"Transcriber module not found at: {full_fnm}")
            return False, None

        # Import the module
        module = import_transcriber_module(full_fnm, base_dir)

        # Get transcript directory path
        transcript_dir = get_transcript_dir(base_dir, version_num)

        # Process the video - this is a blocking call
        logger.info(f"Starting transcription process for URL: {url}")
        logger.info("This process may take 30+ minutes depending on video length...")

        start_time = time.time()

        # Start the processing in the main thread (blocking call)
        processing_completed = False
        try:
            module.process_video(
                youtube_url=url,
                version_num=version_num,
                clean_dir=clean_dir,
                base_dir=base_dir,
            )
            processing_completed = True
        except Exception as e:
            logger.error(f"Error in process_video: {str(e)}")
            raise

        if not processing_completed:
            logger.error("Processing did not complete successfully")
            return False, None

        # Additional verification after completion
        elapsed_time = time.time() - start_time
        logger.info(f"Processing completed after {elapsed_time:.1f} seconds")

        # Verify transcript
        success, transcript_path = verify_transcript_file(transcript_dir)

        if success:
            logger.info("Transcription process completed successfully")
            return True, transcript_path
        else:
            logger.error("Failed to verify transcript file")
            return False, None

    except Exception as e:
        logger.error(f"Error during transcription: {str(e)}")
        traceback.print_exc()
        return False, None

def display_transcript_sample(transcript_path, num_lines=5):
    """
    Display the first few lines of the transcript.

    Args:
        transcript_path (str): Path to the transcript file
        num_lines (int): Number of lines to display
    """
    try:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            logger.info(f"\nFirst {num_lines} lines of transcript:")
            for i, line in enumerate(f):
                if i < num_lines:
                    print(line.strip())
                else:
                    break
    except Exception as e:
        logger.error(f"Error reading transcript: {str(e)}")

def process_transcription():
    """Main execution function."""
    logger.info(f"Starting transcription process with video: {youtube_url}")

    try:
        # Change to correct directory
        cwd = os.getcwd()
        if not os.path.samefile(cwd, base_dir):
            os.chdir(base_dir)
        logger.info(f"Working directory: {os.getcwd()}")

        # Verify transcriber file exists
        if not os.path.exists(full_fnm):
            logger.error(f"Transcriber file not found: {full_fnm}")
            sys.exit(1)

        # Invoke transcriber with long-running process handling
        logger.info("Starting transcription process - this may take 30+ minutes...")
        success, transcript_path = invoke_youtube_transcriber_args(
            full_fnm,
            base_dir,
            youtube_url,
            version_number,
            clean_dir=True
        )

        if success:
            logger.info(f"Transcription completed successfully")
            logger.info(f"Transcript file location: {transcript_path}")

            # Display sample of transcript
            display_transcript_sample(transcript_path)
        else:
            logger.error("Transcription process failed")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

def transcribe_video():
    try:
        process_transcription()
    except Exception as e:
        logger.error(f"Scaffolding execution failed: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

transcribe_video()