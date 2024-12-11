import os
import openai
from models import ProfileData
from typing import List
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

class DataProcessor:
    def process_profiles(self, profiles: List[ProfileData]) -> List[ProfileData]:
        processed = []
        for profile in profiles:
            # Example AI enhancement: Summarize skills
            summary = self.summarize_skills(profile.skills)
            profile.contact_info = self.extract_contact_info(profile)
            # You can add more AI-enhanced processing here
            processed.append(profile)
        return processed

    def summarize_skills(self, skills: List[str]) -> str:
        try:
            response = openai.Completion.create(
                engine="text-davinci-003",
                prompt=f"Summarize the following skills: {', '.join(skills)}",
                max_tokens=50
            )
            summary = response.choices[0].text.strip()
            return summary
        except Exception as e:
            print(f"Error summarizing skills: {e}")
            return ", ".join(skills)

    def extract_contact_info(self, profile: ProfileData) -> dict:
        # Placeholder for contact info extraction logic
        return {}
