import re

class PromptParserJunior:

    async def execute(self, input_data: dict) -> dict:

        prompt = input_data.get("prompt", "").strip()

        if not prompt:
            return {
                "status": "error",
                "structured": {},
                "error": "Empty prompt"
            }

        text = prompt.lower()

        structured = {
            "main_topic": prompt,
            "location": "General",
            "year": "Current",
            "format": "article",
            "tone": "informative",
            "length": "medium"
        }

        # -------- Topic Extraction --------
        if " about " in text:
            structured["main_topic"] = text.split(" about ", 1)[1].split(" in ")[0].strip()

        elif " on " in text:
            structured["main_topic"] = text.split(" on ", 1)[1].split(" in ")[0].strip()

        elif text.startswith("build"):
            structured["format"] = "tutorial"
            structured["main_topic"] = prompt

        # -------- Location Detection --------
        locations = ["nairobi", "kenya", "mombasa", "kisumu"]

        for city in locations:
            if city in text:
                structured["location"] = city.capitalize()
                break

        # -------- Year Detection --------
        year_match = re.search(r"\b(20\d{2})\b", text)
        if year_match:
            structured["year"] = year_match.group(1)

        # -------- Tone Detection --------
        if "guide" in text:
            structured["tone"] = "educational"

        if "opinion" in text:
            structured["tone"] = "opinion"

        # -------- Length Detection --------
        if "short" in text:
            structured["length"] = "short"

        if "long" in text:
            structured["length"] = "long"

        return {
            "status": "ok",
            "structured": structured
        }