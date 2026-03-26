class SkillRegistry:

    def __init__(self):
        self.skills = {}

    def register(self, agent_name, description, examples=None):

        self.skills[agent_name] = {
            "description": description,
            "examples": examples or []
        }

    def list_skills(self):
        return self.skills

    def find_relevant(self, prompt):

        prompt = prompt.lower()

        matches = []

        for agent, skill in self.skills.items():

            text = skill["description"].lower()

            if any(word in prompt for word in text.split()):
                matches.append(agent)

        return matches