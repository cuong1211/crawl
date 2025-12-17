"""
Script de kiem tra Chrome profile cua ban
Chay file nay de tim duong dan Chrome profile dung
"""

import os
import sys
from pathlib import Path

# Fix encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def find_chrome_profiles():
    print("=" * 80)
    print("FIND CHROME PROFILE")
    print("=" * 80)
    print()

    # Chrome User Data common paths
    user_data_dirs = [
        Path(os.path.expanduser("~")) / "AppData" / "Local" / "Google" / "Chrome" / "User Data",
        Path(os.path.expanduser("~")) / "AppData" / "Local" / "Google" / "Chrome Beta" / "User Data",
        Path(os.path.expanduser("~")) / "AppData" / "Local" / "Google" / "Chrome Canary" / "User Data",
    ]

    found_profiles = []

    for user_data_dir in user_data_dirs:
        if user_data_dir.exists():
            print(f"[OK] Found Chrome User Data: {user_data_dir}")
            print()

            # Find profiles
            profiles = []

            # Check Default profile
            if (user_data_dir / "Default").exists():
                profiles.append("Default")

            # Check Profile 1, Profile 2, etc.
            for i in range(1, 20):
                profile_name = f"Profile {i}"
                if (user_data_dir / profile_name).exists():
                    profiles.append(profile_name)

            if profiles:
                print(f"  Available profiles:")
                for idx, profile in enumerate(profiles, 1):
                    profile_path = user_data_dir / profile

                    # Check if profile is active (has Preferences file)
                    prefs_file = profile_path / "Preferences"
                    if prefs_file.exists():
                        # Read profile name from Preferences
                        try:
                            import json
                            with open(prefs_file, 'r', encoding='utf-8') as f:
                                prefs = json.load(f)
                                profile_name_in_prefs = prefs.get('profile', {}).get('name', 'N/A')
                                print(f"  {idx}. {profile:<15} - Name: {profile_name_in_prefs}")
                        except:
                            print(f"  {idx}. {profile}")
                    else:
                        print(f"  {idx}. {profile} (not used yet)")

                found_profiles.append({
                    'user_data_dir': str(user_data_dir),
                    'profiles': profiles
                })

            print()

    if found_profiles:
        print("=" * 80)
        print("HOW TO USE:")
        print("=" * 80)
        print()
        print("In crawler_trademarks.py, update:")
        print()
        print(f'user_data_dir = r"{found_profiles[0]["user_data_dir"]}"')
        print(f'profile_directory = "{found_profiles[0]["profiles"][0]}"  # Or choose another profile')
        print()
        print("NOTES:")
        print("- If you use Default profile, set 'Default'")
        print("- If you use another profile, change profile_directory accordingly")
        print("- CLOSE ALL CHROME WINDOWS before running crawler (Chrome only allows 1 process per profile)")
        print()
    else:
        print("[ERROR] No Chrome profile found!")
        print("You can find manually:")
        print("1. Open Chrome")
        print("2. Go to chrome://version/")
        print("3. Find 'Profile Path' line")
        print()

if __name__ == "__main__":
    find_chrome_profiles()
