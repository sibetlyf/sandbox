import requests
import os
from tqdm import tqdm
import argparse

def download_file(url, dest_path):
    """
    Downloads a file from a URL to a specified destination path with a progress bar.
    """
    try:
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)

        # Start the request
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Check for HTTP errors

        # Get the total file size from headers
        total_size = int(response.headers.get('content-length', 0))
        
        # Open the destination file and start writing
        with open(dest_path, 'wb') as file, tqdm(
            desc=os.path.basename(dest_path),
            total=total_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for data in response.iter_content(chunk_size=1024):
                file.write(data)
                bar.update(len(data))
        
        print(f"\nSuccessfully downloaded: {dest_path}")
        return True

    except requests.exceptions.RequestException as e:
        print(f"\nError during download: {e}")
        return False
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download a file from a URL to a specified location.")
    parser.add_argument("url", help="The URL of the file to download")
    parser.add_argument("output", help="The destination path (including filename)")

    args = parser.parse_args()

    download_file(args.url, args.output)
