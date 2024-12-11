import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from models import ProfileData
from typing import List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

# Load environment variables
load_dotenv()

app = FastAPI()

class LinkedInScraper:
    def __init__(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run headlessly
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        # Add proxy settings if needed
        self.driver = webdriver.Chrome(options=chrome_options)
        self.login_to_linkedin()

    def login_to_linkedin(self):
        try:
            self.driver.get('https://www.linkedin.com/login')
            time.sleep(2)
            username_element = self.driver.find_element("name", "session_key")
            password_element = self.driver.find_element("name", "session_password")
            username_element.send_keys(os.getenv("LINKEDIN_EMAIL"))
            password_element.send_keys(os.getenv("LINKEDIN_PASSWORD"))
            password_element.submit()
            time.sleep(5)  # Wait for login to complete
        except Exception as e:
            print(f"Error during LinkedIn login: {e}")
            self.driver.quit()

    def search_profiles(self, criteria):
        try:
            # Construct search URL based on criteria
            keywords = "%20".join(criteria.skills)
            location = criteria.location.replace(" ", "%20")
            experience = "experienced" if criteria.experience_level.lower() == "experienced" else "fresher"
            search_url = f"https://www.linkedin.com/search/results/people/?keywords={keywords}&location={location}&origin=GLOBAL_SEARCH_HEADER"
            self.driver.get(search_url)
            time.sleep(5)  # Wait for search results to load

            profile_links = self.extract_profile_links()

            # Limit the number of profiles to prevent overload
            profile_links = profile_links[:10]

            profiles = []
            for link in profile_links:
                profile = self.extract_profile_data(link)
                if profile:
                    profiles.append(profile)
            return profiles
        except Exception as e:
            print(f"Error during profile search: {e}")
            return []

    def extract_profile_links(self) -> List[str]:
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        links = []
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if "/in/" in href and href not in links:
                links.append(href)
        return links

    def extract_profile_data(self, profile_url: str) -> Optional[ProfileData]:
        try:
            self.driver.get(profile_url)
            time.sleep(3)  # Wait for profile to load
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')

            name_tag = soup.find('h1')
            name = name_tag.get_text(strip=True) if name_tag else "N/A"

            skills = self.extract_skills(soup)

            location_tag = soup.find('span', {'class': 'text-body-small'})
            location = location_tag.get_text(strip=True) if location_tag else "N/A"

            # Placeholder data for education and experience
            education = {}
            experience = []

            profile = ProfileData(
                name=name,
                profile_url=profile_url,
                skills=skills,
                location=location,
                education=education,
                experience=experience,
                contact_info={}
            )
            return profile
        except Exception as e:
            print(f"Error extracting profile data from {profile_url}: {e}")
            return None

    def extract_skills(self, soup: BeautifulSoup) -> List[str]:
        skills = []
        skills_section = soup.find_all('span', {'class': 'pv-skill-category-entity__name-text'})
        for skill in skills_section:
            skills.append(skill.get_text(strip=True))
        return skills

    def __del__(self):
        self.driver.quit()

# Define a Pydantic model for the criteria
class SearchCriteria(BaseModel):
    skills: List[str]
    location: str
    experience_level: str

@app.post("/api/search-profiles", response_model=List[ProfileData])
async def search_profiles_endpoint(criteria: SearchCriteria):
    scraper = LinkedInScraper()
    profiles = scraper.search_profiles(criteria)
    return profiles