import tomllib

def check_update():
    """ !!! WIP !!! """

    # CONFIG
    try:
        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)
        owner = data["owner"]
        repo = data["repo"]
        current_version=data["version"]
    except FileNotFoundError:
        owner: str = "dermif1"
        repo: str = "AppUpdateNotification"
        current_version: str = "0.0.1"

    # CODE
    import requests
    from tkinter import messagebox

    GitHubURL: str = f"https://github.com/{owner}/{repo}/releases/latest"
    headers = {"User-Agent": "MyUniqueRequestCode"}
    response = requests.get(GitHubURL, headers=headers)
    print(response)

    if response.status_code == 200:
        try:
            data = response.json()
            latest_version = data.get("tag_name")
            if latest_version != current_version:
                messagebox.showinfo(f"Update available!\nCurrent: {current_version}, Latest: {latest_version}.\nYou can download it in GitHub by this link:\nhttps://github.com/{owner}/{repo}/releases/latest")
        except requests.exceptions.JSONDecodeError:
            # Handles cases where the response is HTML/text instead of JSON
            print("Error: Server did not return valid JSON data.")
            print(f"Raw response content: {response.text[:200]}")  # Print first 200 chars for debugging
    else:
        messagebox.showerror("Update Error", "Could not get latest version!")
