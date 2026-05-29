import instaloader
from datetime import datetime
import os
import time
from getpass import getpass

def handle_2fa():
    """Handle two-factor authentication"""
    return input('Enter 2FA code: ')

def extract_instagram_captions(profile_name, output_file, username=None, password=None):
    """
    Extract captions from Instagram posts of a specific profile
    """
    # Create an instance of Instaloader
    L = instaloader.Instaloader()
    
    try:
        # Login to Instagram
        if username and password:
            print("Logging in to Instagram...")
            try:
                L.login(username, password)
            except instaloader.exceptions.TwoFactorAuthRequiredException:
                print("Two-factor authentication required.")
                code = handle_2fa()
                L.two_factor_login(code)
        else:
            print("Warning: Running without authentication might cause rate limiting")
        
        # Get profile
        print(f"Fetching profile {profile_name}...")
        profile = instaloader.Profile.from_username(L.context, profile_name)
        
        # Open file to write captions
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"Captions from {profile_name}\n")
            f.write("=" * 50 + "\n\n")
            
            # Iterate through posts with rate limiting handling
            for post in profile.get_posts():
                try:
                    if post.caption:  # Check if post has caption
                        date = post.date_local.strftime("%Y-%m-%d")
                        f.write(f"Date: {date}\n")
                        f.write(f"URL: https://www.instagram.com/p/{post.shortcode}/\n")
                        f.write("Caption:\n")
                        f.write(f"{post.caption}\n")
                        f.write("-" * 50 + "\n\n")
                        
                    # Add delay between requests to avoid rate limiting
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"Error processing post: {str(e)}")
                    continue
                    
        print(f"Captions have been saved to {output_file}")
                    
    except instaloader.exceptions.ProfileNotExistsException:
        print(f"Error: Profile '{profile_name}' does not exist")
    except instaloader.exceptions.LoginRequiredException:
        print("Error: Login required to access this profile")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    # Instagram credentials
    USERNAME = input("Enter your Instagram username: ")
    PASSWORD = getpass("Enter your Instagram password: ")
    
    # Profile to scrape
    PROFILE_NAME = "hermessf"
    OUTPUT_FILE = f"captions_{PROFILE_NAME}_{datetime.now().strftime('%Y%m%d')}.txt"
    
    extract_instagram_captions(PROFILE_NAME, OUTPUT_FILE, USERNAME, PASSWORD)