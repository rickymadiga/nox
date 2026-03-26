class WriterJunior:

    async def execute(self, data: dict) -> dict:

        structured = data.get("structured", {})
        outline = data.get("outline", [])
        topic = data.get("topic", structured.get("main_topic", "Topic"))

        location = structured.get("location", "General")
        year = structured.get("year", "Current")

        if not outline:
            return {
                "status": "error",
                "content": "",
                "error": "No outline provided"
            }

        sections = []

        for heading in outline:
            section_text = f"""
{heading}

{topic} is an important subject that continues to gain attention in {location}. 
As of {year}, it plays a growing role in modern discussions and development.

Understanding this section helps readers gain a clearer view of how {topic}
works and why it matters in practical scenarios.
""".strip()

            sections.append(section_text)

        content = "\n\n".join(sections)

        return {
            "status": "ok",
            "content": content
        }