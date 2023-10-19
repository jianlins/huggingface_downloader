import requests
from bs4 import BeautifulSoup
from pathlib import Path
import os
import aiohttp
import asyncio
import nest_asyncio
from tqdm import tqdm
import getpass
LOGIN_URL = "https://huggingface.co/login"
# Assuming this is where you would POST your login data. 
# Check the actual form action in the website's HTML source
ACTION_URL = 'https://huggingface.co/login'
async def fetch_content(session, url, filename):
    headers = {}

    # Check if we already have a partial file
    if os.path.exists(filename):
        current_size = os.path.getsize(filename)
        headers = {'Range': f'bytes={current_size}-'}

    async with session.get(url, headers=headers) as response:                
        if response.status == 416:
            progress_bar=tqdm(total=100, unit='%', unit_scale=True, desc=filename)
            progress_bar.update(100)
            progress_bar.close()
            return
        total_size=int(response.headers.get('content-length'), 0)
        progress_bar=tqdm(total=total_size, unit='B', unit_scale=True, desc=filename)
        if response.status == 206:
            mode = 'ab'  # Append mode
        else:
            mode = 'wb'  # Write mode
        # mode='wb'
        # print(f"Downloading: {filename}", end="")
        with open(filename, mode) as fd:
            while True:
                chunk = await response.content.read(8192)  # Read asynchronously in chunks
                if not chunk:
                    break
                fd.write(chunk)
                fd.flush()
                progress_bar.update(len(chunk))
        # print(f"\t\tDone.")
        progress_bar.close()

async def download_file_with_resume(session, url, filename):
    try:        
        await fetch_content(session, url, filename)
        
    except Exception as e:
        print(f"Failed to download {filename}. Error: {e}")

    
        
async def download_model(model_name, models_path, username, password):
    model_path=Path(models_path, model_name)
    if not model_path.exists():
        model_path.mkdir(parents=True)
        
    async with aiohttp.ClientSession() as session:
        # ... (part that fetches the file links remains the same)
        MODEL_URL = f'https://huggingface.co/{model_name}/tree/main' 
        if len(username)>0:
            async with session.get(LOGIN_URL) as response:
                response.raise_for_status()

            # Extract CSRF token or any other required data from the page source if necessary
            # You can use libraries like BeautifulSoup4 for this.
            # csrf_token = ...

            # POST payload
            payload = {
                'username': username,
                'password': password,
                # 'csrf_token': csrf_token  # Include this if the site uses CSRF tokens
            }
            async with session.post(ACTION_URL, data=payload) as response:
                if response.status !=200:
                    raise Exception('Login failed!')
            
        async with session.get(MODEL_URL) as response:
            content= await response.text()
            soup = BeautifulSoup(content, 'html.parser')
            file_links = [a['href'] for a in soup.find_all('a', href=True) if f'{model_name}/resolve/main/' in a['href']]
            print(f'check if files are correct: \n Total {len(file_links)} files.')
            print('\n'.join(file_links))
        
        tasks = []
        for link in file_links:
            file_url = "https://huggingface.co" + link.replace('/blob/', '/raw/')
            filename = os.path.join(str(model_path), link.split('/')[-1])
            tasks.append(download_file_with_resume(session, file_url, filename))

        # Await all tasks to complete
        await asyncio.gather(*tasks)


# Use the function
if __name__=='__main__':
    nest_asyncio.apply()
    print("Please enter your Huggingface credentials. If the model doesn't need login, leave them blank")
    username=input("Username:")
    password=getpass.getpass("Password:")
    model_name=input("Model name(e.g. bert-base-uncased):")
    asyncio.run(download_model(model_name, models_path='models', username=username, password=password))