class BaseMember:

    name = "base_member"
    skill_score = 1.0

    def can_handle(self, task):
        raise NotImplementedError

    def execute(self, task):
        raise NotImplementedError