
import asyncio
import os
import argparse
import sys
import random

# Try to import pixabay_search. 
# Renamed pixabay.py to pixabay_service.py to avoid shadowing the library.
try:
    from pixabay_service import pixabay_search, resource_format
except ImportError:
    pass
except AttributeError:
    pass

from downloader import download_file

async def main():
    parser = argparse.ArgumentParser(description="Auto Media Downloader using Pixabay")
    parser.add_argument("query", nargs='?', help="Search query content")
    parser.add_argument("--type", choices=["image", "video"], default="image", help="Type of media to download")
    parser.add_argument("--search-limit", type=int, default=20, help="Number of items to search/fetch from API")
    parser.add_argument("--download-limit", type=int, default=5, help="Number of items to randomly select and download")
    parser.add_argument("--limit", type=int, help="Alias for --download-limit (for backward compatibility)")
    parser.add_argument("--key", default="53312803-19c141bade8d0b8e930a236ca", help="Pixabay API Key")
    parser.add_argument("--output", default="downloads", help="Directory to save downloads")

    args = parser.parse_args()

    # Handle alias: if --limit is set, it overrides --download-limit
    if args.limit:
        args.download_limit = args.limit
        # Also ensure search_limit is at least equal to limit if not explicitly set higher
        if args.search_limit < args.limit:
            args.search_limit = args.limit

    # Interactive mode if query is missing
    if not args.query:
        print("未检测到命令行参数，进入交互模式 (No arguments detected, entering interactive mode)")
        args.query = input("请输入搜索内容 (Enter search query): ").strip()
        if not args.query:
            print("错误：必须输入搜索内容 (Error: Search query is required)")
            return

        type_input = input("请输入媒体类型 [image/video] (默认为 image): ").strip()
        if type_input in ["image", "video"]:
            args.type = type_input
        
        search_limit_input = input("请输入搜索数量 (Search Limit, 默认为 20): ").strip()
        if search_limit_input.isdigit():
            args.search_limit = int(search_limit_input)

        download_limit_input = input("请输入下载数量 (Download Limit, 默认为 5): ").strip()
        if download_limit_input.isdigit():
            args.download_limit = int(download_limit_input)

    print(f"Searching for top {args.search_limit} '{args.type}' matching query: '{args.query}'")
    
    # Ensure output directory exists
    if not os.path.exists(args.output):
        os.makedirs(args.output)

    try:
        # pixabay_search yields a list of results
        async for results in pixabay_search(query=args.query, key=args.key, resource_type=args.type, resource_limit=args.search_limit):
            if not results:
                print("No results found.")
                break
            
            total_found = len(results)
            print(f"Found {total_found} items.")

            # Randomly select items if we found more than we want to download
            if total_found > args.download_limit:
                print(f"Randomly selecting {args.download_limit} items from {total_found} results...")
                items_to_download = random.sample(results, args.download_limit)
            else:
                print(f"Found fewer items than download limit. Downloading all {total_found} items...")
                items_to_download = results
            
            print("Starting download...")
            
            for item in items_to_download:
                try:
                    url = item.url
                    media_id = item.id
                    media_type = item.type
                    
                    # Determine file extension
                    filename = os.path.basename(url.split('?')[0])
                    if not os.path.splitext(filename)[1]:
                        ext = ".jpg" if args.type == "image" else ".mp4"
                        filename = f"{media_id}_{media_type}{ext}"
                    
                    save_path = os.path.join(args.output, filename)
                    
                    print(f"Downloading: {url} -> {save_path}")
                    success = download_file(url, save_path)
                    
                    if success:
                        print("Download successful.")
                    else:
                        print("Download failed.")
                        
                except Exception as e:
                    print(f"Error processing item {item}: {e}")
                    
    except Exception as e:
        print(f"An error occurred during search: {e}")
        print("Tip: If you see an AttributeError related to 'module pixabay has no attribute core', please rename 'pixabay.py' to 'pixabay_service.py' or similar to avoid shadowing the pixabay library.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
